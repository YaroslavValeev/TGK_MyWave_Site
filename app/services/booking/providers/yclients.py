"""YCLIENTS booking provider (scaffold — disabled until credentials)."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config.yclients_config import (
    is_yclients_enabled,
    yclients_api_base_url,
    yclients_company_id,
    yclients_partner_token,
    yclients_user_token,
)
from app.services.booking.providers.base import (
    BookingProvider,
    ProviderBookingResult,
    ProviderSlot,
)

logger = logging.getLogger(__name__)
USER_AGENT = "MyWave-Site-YCLIENTS/1.0"
DEFAULT_TIMEOUT = 20


class YclientsNotConfiguredError(RuntimeError):
    """Raised when YCLIENTS_ENABLED=0 or credentials missing."""


class YclientsProvider(BookingProvider):
    provider_name = "yclients"

    def is_enabled(self) -> bool:
        return is_yclients_enabled()

    def _require_enabled(self) -> None:
        if not self.is_enabled():
            raise YclientsNotConfiguredError("yclients_disabled")
        if not yclients_partner_token() and not yclients_user_token():
            raise YclientsNotConfiguredError("yclients_credentials_missing")

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }
        partner = yclients_partner_token()
        user = yclients_user_token()
        if partner:
            headers["Authorization"] = f"Bearer {partner}"
        if user:
            headers["User"] = user
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self._require_enabled()
        base = yclients_api_base_url().rstrip("/")
        url = f"{base}{path}"
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        req = Request(url, data=data, headers=self._headers(), method=method.upper())
        try:
            with urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            logger.warning(
                "yclients_http_error",
                extra={"status": exc.code, "path": path},
            )
            raise
        except URLError as exc:
            logger.warning("yclients_connection_error", extra={"reason": str(exc.reason)})
            raise
        if not isinstance(payload, dict):
            return {"data": payload}
        return payload

    def fetch_available_slots(self, date_str: str) -> List[ProviderSlot]:
        self._require_enabled()
        company_id = yclients_company_id()
        # Endpoint shape depends on YCLIENTS API contract — placeholder path.
        payload = self._request("GET", f"/book_times/{company_id}/{date_str}")
        slots: List[ProviderSlot] = []
        for item in payload.get("data") or []:
            if not isinstance(item, dict):
                continue
            time_str = str(item.get("time") or item.get("start_time") or "").strip()[:5]
            if not time_str:
                continue
            slots.append(
                ProviderSlot(
                    start_time=time_str,
                    duration_minutes=int(item.get("duration") or 30),
                    available=bool(item.get("available", True)),
                )
            )
        return slots

    def create_booking(
        self,
        *,
        date_str: str,
        time_str: str,
        client_name: str,
        client_phone: str,
        service_id: Optional[str] = None,
    ) -> ProviderBookingResult:
        self._require_enabled()
        company_id = yclients_company_id()
        body = {
            "company_id": company_id,
            "date": date_str,
            "time": time_str,
            "name": client_name,
            "phone": client_phone,
            "service_id": service_id,
        }
        payload = self._request("POST", f"/records/{company_id}", body=body)
        record_id = str(
            (payload.get("data") or {}).get("id")
            or payload.get("record_id")
            or ""
        )
        return ProviderBookingResult(
            external_id=record_id,
            status=str((payload.get("data") or {}).get("status") or "created"),
            raw=payload,
        )

    def cancel_booking(self, external_id: str) -> bool:
        self._require_enabled()
        company_id = yclients_company_id()
        self._request("DELETE", f"/records/{company_id}/{external_id}")
        return True


def get_yclients_provider() -> YclientsProvider:
    return YclientsProvider()
