"""HTTP helpers for staging smoke — curl + cookie jar (no requests/eventlet clash)."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from typing import Any

DEFAULT_BASE = os.environ.get("STAGING_BASE_URL", "http://127.0.0.1:5002")
DEFAULT_SLEEP = float(os.environ.get("STAGING_API_SLEEP", "2.5"))


class StagingClient:
    def __init__(self, base_url: str = DEFAULT_BASE, sleep_sec: float = DEFAULT_SLEEP):
        self.base_url = base_url.rstrip("/")
        self.sleep_sec = sleep_sec
        self._cookie_jar = tempfile.NamedTemporaryFile(
            prefix="staging_smoke_cookies_", suffix=".txt", delete=False
        )
        self.cookie_path = self._cookie_jar.name
        self._cookie_jar.close()

    def _pause(self) -> None:
        if self.sleep_sec > 0:
            time.sleep(self.sleep_sec)

    def _curl(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        data: str | None = None,
    ) -> tuple[int, str]:
        cmd = [
            "curl",
            "-sS",
            "-b",
            self.cookie_path,
            "-c",
            self.cookie_path,
            "-X",
            method,
            "-o",
            "-",
            "-w",
            "\n__HTTP_CODE__%{http_code}",
        ]
        for k, v in (headers or {}).items():
            cmd.extend(["-H", f"{k}: {v}"])
        if data is not None:
            cmd.extend(["-d", data])
        cmd.append(url)

        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            raise RuntimeError(f"curl failed rc={proc.returncode}: {proc.stderr[:500]}")
        raw = proc.stdout
        if "\n__HTTP_CODE__" not in raw:
            raise RuntimeError(f"curl unexpected output: {raw[:300]}")
        body, _, code_str = raw.rpartition("\n__HTTP_CODE__")
        return int(code_str.strip()), body

    def csrf_token(self) -> str:
        code, body = self._curl("GET", f"{self.base_url}/api/csrf-token")
        if code != 200:
            raise RuntimeError(f"csrf-token HTTP {code}: {body[:200]}")
        token = json.loads(body).get("csrf_token")
        if not token:
            raise RuntimeError("csrf_token missing in /api/csrf-token response")
        return token

    def get_slots(self, date: str, service: str) -> list[dict]:
        self._pause()
        url = f"{self.base_url}/api/calendar/slots/{date}?service={service}"
        code, body = self._curl("GET", url)
        if code != 200:
            raise RuntimeError(f"slots HTTP {code}: {body[:300]}")
        data = json.loads(body)
        return data if isinstance(data, list) else []

    def slot_map(self, date: str, service: str) -> dict[str, dict]:
        return {s["time"]: s for s in self.get_slots(date, service)}

    def book(
        self,
        *,
        date: str,
        time: str,
        name: str,
        phone: str,
        service_type: str,
        set_count: int = 1,
    ) -> tuple[int, dict]:
        self._pause()
        token = self.csrf_token()
        payload: dict[str, Any] = {
            "date": date,
            "time": time,
            "name": name,
            "phone": phone,
            "service_type": service_type,
            "set_count": set_count,
            "csrf_token": token,
        }
        code, body = self._curl(
            "POST",
            f"{self.base_url}/api/calendar/book",
            headers={
                "Content-Type": "application/json",
                "X-CSRFToken": token,
                "Referer": f"{self.base_url}/",
            },
            data=json.dumps(payload),
        )
        try:
            parsed = json.loads(body) if body.strip() else {}
        except json.JSONDecodeError:
            parsed = {"raw": body[:500]}
        return code, parsed
