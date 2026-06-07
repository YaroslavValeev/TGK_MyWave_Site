"""HTTP helpers for staging smoke (CSRF session against local gunicorn)."""

from __future__ import annotations

import os
import time
from typing import Any, Optional

import requests

DEFAULT_BASE = os.environ.get("STAGING_BASE_URL", "http://127.0.0.1:5002")
DEFAULT_SLEEP = float(os.environ.get("STAGING_API_SLEEP", "2.5"))


class StagingClient:
    def __init__(self, base_url: str = DEFAULT_BASE, sleep_sec: float = DEFAULT_SLEEP):
        self.base_url = base_url.rstrip("/")
        self.sleep_sec = sleep_sec
        self.session = requests.Session()

    def _pause(self) -> None:
        if self.sleep_sec > 0:
            time.sleep(self.sleep_sec)

    def csrf_token(self) -> str:
        r = self.session.get(f"{self.base_url}/api/csrf-token", timeout=30)
        r.raise_for_status()
        token = r.json().get("csrf_token")
        if not token:
            raise RuntimeError("csrf_token missing in /api/csrf-token response")
        return token

    def get_slots(self, date: str, service: str) -> list[dict]:
        self._pause()
        r = self.session.get(
            f"{self.base_url}/api/calendar/slots/{date}",
            params={"service": service},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
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
        r = self.session.post(
            f"{self.base_url}/api/calendar/book",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-CSRFToken": token,
            },
            timeout=120,
        )
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text[:500]}
        return r.status_code, body
