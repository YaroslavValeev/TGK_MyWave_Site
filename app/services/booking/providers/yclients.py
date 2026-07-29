"""YCLIENTS booking provider — boat SoT adapter (S5 read / S6 write).

Auth (from YCLIENTS support, Jul 2026):
  Authorization: Bearer <partner_token>, User <user_token>
  Accept: application/vnd.yclients.v2+json

Online booking (partner token enough): book_times / book_record
Journal ops (partner + user): records list/create/update
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config.yclients_config import (
    is_yclients_enabled,
    is_yclients_read_enabled,
    is_yclients_write_enabled,
    yclients_accept_header,
    yclients_api_base_url,
    yclients_company_id,
    yclients_default_service_id,
    yclients_partner_token,
    yclients_rate_limit_rps,
    yclients_service_id_list,
    yclients_slot_duration_minutes,
    yclients_staff_id,
    yclients_user_token,
)
from app.services.booking.providers.base import (
    BookingProvider,
    ProviderBookingResult,
    ProviderSlot,
)

logger = logging.getLogger(__name__)
USER_AGENT = "MyWave-Site-YCLIENTS/1.1"
DEFAULT_TIMEOUT = 20
SOURCE_COMMENT_PREFIX = "mw_source="

# attendance: 2 confirmed, 1 came, 0 waiting, -1 no-show / cancelled-via-status
ATTENDANCE_CANCELLED = -1


class YclientsNotConfiguredError(RuntimeError):
    """Raised when YCLIENTS_ENABLED=0 or credentials missing."""


class YclientsReadOnlyError(RuntimeError):
    """Raised when write is requested while YCLIENTS_WRITE_ENABLED=0."""


class YclientsApiError(RuntimeError):
    def __init__(self, message: str, *, status: int = 0, payload: Any = None):
        super().__init__(message)
        self.status = status
        self.payload = payload


class _RateLimiter:
    """Simple spacing between partner-token requests (≤5 rps)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self) -> None:
        min_interval = 1.0 / yclients_rate_limit_rps()
        with self._lock:
            now = time.monotonic()
            delay = min_interval - (now - self._last)
            if delay > 0:
                time.sleep(delay)
            self._last = time.monotonic()


_rate_limiter = _RateLimiter()


def build_source_comment(
    *,
    source: str,
    internal_id: str = "",
    extra: str = "",
) -> str:
    """Encode channel + internal id in comment (native source field unsupported)."""
    parts = [f"{SOURCE_COMMENT_PREFIX}{source.strip() or 'unknown'}"]
    if internal_id:
        parts.append(f"mw_id={internal_id.strip()}")
    if extra:
        parts.append(extra.strip())
    return " | ".join(parts)


def parse_attendance_status(attendance: Any, *, deleted: bool = False) -> str:
    if deleted:
        return "deleted"
    try:
        value = int(attendance)
    except (TypeError, ValueError):
        return "unknown"
    if value == ATTENDANCE_CANCELLED:
        return "cancelled"
    if value == 1:
        return "completed"
    if value == 2:
        return "confirmed"
    if value == 0:
        return "waiting"
    return f"attendance_{value}"


class YclientsProvider(BookingProvider):
    provider_name = "yclients"

    def is_enabled(self) -> bool:
        return is_yclients_enabled()

    def _require_enabled(self) -> None:
        if not self.is_enabled():
            raise YclientsNotConfiguredError("yclients_disabled")
        if not yclients_partner_token():
            raise YclientsNotConfiguredError("yclients_partner_token_missing")

    def _require_read(self) -> None:
        self._require_enabled()
        if not is_yclients_read_enabled():
            raise YclientsNotConfiguredError("yclients_read_disabled")

    def _require_write(self) -> None:
        self._require_enabled()
        if not is_yclients_write_enabled():
            raise YclientsReadOnlyError("yclients_write_disabled")
        if not yclients_user_token():
            # Online book_record can work with partner-only; journal needs user.
            # We still require user for writes to keep one auth path for S6.
            raise YclientsNotConfiguredError("yclients_user_token_missing")

    def _headers(self, *, need_user: bool = False) -> Dict[str, str]:
        partner = yclients_partner_token()
        user = yclients_user_token()
        if need_user and not user:
            raise YclientsNotConfiguredError("yclients_user_token_missing")

        auth = f"Bearer {partner}"
        if user:
            auth = f"{auth}, User {user}"

        return {
            "Accept": yclients_accept_header(),
            "Content-Type": "application/json",
            "Authorization": auth,
            "User-Agent": USER_AGENT,
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[Dict[str, Any]] = None,
        query: Optional[Dict[str, Any]] = None,
        need_user: bool = False,
    ) -> Dict[str, Any]:
        self._require_enabled()
        base = yclients_api_base_url().rstrip("/")
        url = f"{base}{path}"
        if query:
            pairs = []
            for key, value in query.items():
                if value is None:
                    continue
                if isinstance(value, (list, tuple)):
                    for item in value:
                        pairs.append((f"{key}[]", str(item)))
                else:
                    pairs.append((key, str(value)))
            if pairs:
                url = f"{url}?{urlencode(pairs)}"

        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")

        _rate_limiter.wait()
        req = Request(
            url,
            data=data,
            headers=self._headers(need_user=need_user),
            method=method.upper(),
        )
        try:
            with urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
                raw = resp.read().decode("utf-8")
                payload = json.loads(raw) if raw else {}
        except HTTPError as exc:
            err_body: Any = None
            try:
                err_body = json.loads(exc.read().decode("utf-8"))
            except Exception:
                err_body = None
            logger.warning(
                "yclients_http_error status=%s path=%s",
                exc.code,
                path,
            )
            raise YclientsApiError(
                f"yclients_http_{exc.code}",
                status=exc.code,
                payload=err_body,
            ) from exc
        except URLError as exc:
            logger.warning("yclients_connection_error reason=%s", exc.reason)
            raise YclientsApiError(
                "yclients_connection_error",
                status=0,
                payload={"reason": str(exc.reason)},
            ) from exc

        if not isinstance(payload, dict):
            return {"data": payload}
        return payload

    # --- Discovery / metadata -------------------------------------------------

    def get_company(self) -> Dict[str, Any]:
        self._require_read()
        company_id = yclients_company_id()
        return self._request("GET", f"/company/{company_id}/", need_user=True)

    def list_staff(self) -> List[Dict[str, Any]]:
        self._require_read()
        company_id = yclients_company_id()
        payload = self._request("GET", f"/staff/{company_id}", need_user=True)
        data = payload.get("data") or []
        return data if isinstance(data, list) else []

    def list_services(self) -> List[Dict[str, Any]]:
        self._require_read()
        company_id = yclients_company_id()
        payload = self._request("GET", f"/services/{company_id}", need_user=True)
        data = payload.get("data") or []
        return data if isinstance(data, list) else []

    def list_book_dates(
        self,
        *,
        staff_id: Optional[str] = None,
        service_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        self._require_read()
        company_id = yclients_company_id()
        sid = staff_id or yclients_staff_id() or "0"
        query: Dict[str, Any] = {"staff_id": sid}
        ids = service_ids or yclients_service_id_list()
        if ids:
            query["service_ids"] = ids
        return self._request("GET", f"/book_dates/{company_id}", query=query)

    # --- Slots ----------------------------------------------------------------

    def fetch_available_slots(
        self,
        date_str: str,
        *,
        staff_id: Optional[str] = None,
        service_ids: Optional[List[int]] = None,
    ) -> List[ProviderSlot]:
        self._require_read()
        company_id = yclients_company_id()
        sid = staff_id or yclients_staff_id()
        if not sid:
            raise YclientsNotConfiguredError("yclients_staff_id_missing")

        query: Dict[str, Any] = {}
        # Для слотов передаём одну (default) услугу: пачка ID из env даёт 422.
        if service_ids is not None:
            ids = service_ids
        else:
            default = yclients_default_service_id()
            ids = [default] if default else []
        if ids:
            query["service_ids"] = ids

        payload = self._request(
            "GET",
            f"/book_times/{company_id}/{sid}/{date_str}",
            query=query or None,
        )
        default_duration = yclients_slot_duration_minutes()
        slots: List[ProviderSlot] = []
        for item in payload.get("data") or []:
            if not isinstance(item, dict):
                continue
            time_str = str(item.get("time") or "").strip()[:5]
            if not time_str:
                continue
            length_sec = item.get("seance_length")
            try:
                duration = int(length_sec) // 60 if length_sec else default_duration
            except (TypeError, ValueError):
                duration = default_duration
            slots.append(
                ProviderSlot(
                    start_time=time_str,
                    duration_minutes=duration,
                    available=True,
                )
            )
        return slots

    def fetch_available_slots_raw(
        self,
        date_str: str,
        *,
        staff_id: Optional[str] = None,
        service_ids: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """Return raw book_times items (includes datetime for create)."""
        self._require_read()
        company_id = yclients_company_id()
        sid = staff_id or yclients_staff_id()
        if not sid:
            raise YclientsNotConfiguredError("yclients_staff_id_missing")
        query: Dict[str, Any] = {}
        if service_ids is not None:
            ids = service_ids
        else:
            default = yclients_default_service_id()
            ids = [default] if default else []
        if ids:
            query["service_ids"] = ids
        payload = self._request(
            "GET",
            f"/book_times/{company_id}/{sid}/{date_str}",
            query=query or None,
        )
        data = payload.get("data") or []
        return data if isinstance(data, list) else []

    # --- Records --------------------------------------------------------------

    def list_records(
        self,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        count: int = 100,
        with_deleted: bool = False,
    ) -> List[Dict[str, Any]]:
        self._require_read()
        company_id = yclients_company_id()
        query: Dict[str, Any] = {"page": page, "count": count}
        if start_date:
            query["start_date"] = start_date
        if end_date:
            query["end_date"] = end_date
        if with_deleted:
            query["with_deleted"] = 1
        staff = yclients_staff_id()
        if staff:
            query["staff_id"] = staff
        payload = self._request(
            "GET",
            f"/records/{company_id}",
            query=query,
            need_user=True,
        )
        data = payload.get("data") or []
        return data if isinstance(data, list) else []

    def get_record(self, record_id: str) -> Dict[str, Any]:
        self._require_read()
        company_id = yclients_company_id()
        payload = self._request(
            "GET",
            f"/record/{company_id}/{record_id}",
            need_user=True,
        )
        data = payload.get("data")
        return data if isinstance(data, dict) else payload

    def create_booking(
        self,
        *,
        date_str: str,
        time_str: str,
        client_name: str,
        client_phone: str,
        service_id: Optional[str] = None,
        client_email: str = "",
        client_surname: str = "",
        set_count: int = 1,
        source: str = "site",
        internal_id: str = "",
        comment_extra: str = "",
        custom_fields: Optional[Dict[str, Any]] = None,
        datetime_iso: Optional[str] = None,
        use_online: bool = True,
    ) -> ProviderBookingResult:
        """Create boat booking.

        Multi-set: one journal record.
        - seance_length = set_count * BOAT_SLOT (30 min = 25 ride + 5 tech) so YC
          blocks the full partner slot, not ride-only 25.
        - services[].amount = set_count so YC shows N× «сет 25 мин» line.
        """
        self._require_write()
        sets = max(1, int(set_count or 1))
        from app.config.yclients_config import yclients_slot_duration_minutes

        duration_sec = sets * yclients_slot_duration_minutes() * 60
        comment = build_source_comment(
            source=source,
            internal_id=internal_id,
            extra=comment_extra,
        )
        svc_id = int(service_id) if service_id else yclients_default_service_id()
        staff = yclients_staff_id()
        if not staff:
            raise YclientsNotConfiguredError("yclients_staff_id_missing")
        if not svc_id:
            raise YclientsNotConfiguredError("yclients_service_id_missing")

        phone = "".join(ch for ch in client_phone if ch.isdigit())
        dt = datetime_iso or f"{date_str} {time_str[:5]}:00"

        # Journal create: full control over seance_length (multi-set in one record).
        if not use_online or sets > 1:
            return self._create_journal_record(
                staff_id=int(staff),
                service_id=int(svc_id),
                datetime_str=dt,
                seance_length=duration_sec,
                service_amount=sets,
                client_name=client_name,
                client_phone=phone,
                client_email=client_email or "noreply@mywavewake.ru",
                client_surname=client_surname,
                comment=comment,
                internal_id=internal_id,
                custom_fields=custom_fields,
            )

        return self._create_online_record(
            staff_id=int(staff),
            service_id=int(svc_id),
            datetime_str=dt,
            client_name=client_name,
            client_phone=phone,
            client_email=client_email or "noreply@mywavewake.ru",
            client_surname=client_surname,
            comment=comment,
            internal_id=internal_id,
            custom_fields=custom_fields,
        )

    def _create_online_record(
        self,
        *,
        staff_id: int,
        service_id: int,
        datetime_str: str,
        client_name: str,
        client_phone: str,
        client_email: str,
        client_surname: str,
        comment: str,
        internal_id: str,
        custom_fields: Optional[Dict[str, Any]],
    ) -> ProviderBookingResult:
        company_id = yclients_company_id()
        appointment: Dict[str, Any] = {
            "id": 1,
            "services": [service_id],
            "staff_id": staff_id,
            "datetime": datetime_str,
        }
        if custom_fields:
            appointment["custom_fields"] = custom_fields

        body: Dict[str, Any] = {
            "phone": client_phone,
            "fullname": client_name,
            "email": client_email,
            "comment": comment,
            "appointments": [appointment],
            "notify_by_sms": 0,
            "notify_by_email": 0,
        }
        if client_surname:
            body["surname"] = client_surname
        if internal_id:
            body["api_id"] = internal_id
        if custom_fields:
            body["custom_fields"] = custom_fields

        # Online booking: partner token is enough per docs.
        payload = self._request(
            "POST",
            f"/book_record/{company_id}",
            body=body,
            need_user=False,
        )
        data = payload.get("data") or []
        first = data[0] if isinstance(data, list) and data else {}
        record_id = str(first.get("record_id") or first.get("id") or "")
        return ProviderBookingResult(
            external_id=record_id,
            status="created",
            raw=payload,
        )

    def _create_journal_record(
        self,
        *,
        staff_id: int,
        service_id: int,
        datetime_str: str,
        seance_length: int,
        client_name: str,
        client_phone: str,
        client_email: str,
        client_surname: str,
        comment: str,
        internal_id: str,
        custom_fields: Optional[Dict[str, Any]],
        service_amount: int = 1,
    ) -> ProviderBookingResult:
        company_id = yclients_company_id()
        amount = max(1, int(service_amount or 1))
        body: Dict[str, Any] = {
            "staff_id": staff_id,
            "services": [{"id": service_id, "amount": amount}],
            "client": {
                "phone": client_phone,
                "name": client_name,
                "surname": client_surname or "",
                "email": client_email,
            },
            "datetime": datetime_str,
            "seance_length": seance_length,
            "save_if_busy": False,
            "send_sms": False,
            "comment": comment,
            "attendance": 0,
        }
        if internal_id:
            body["api_id"] = internal_id
        if custom_fields:
            body["custom_fields"] = custom_fields

        payload = self._request(
            "POST",
            f"/records/{company_id}",
            body=body,
            need_user=True,
        )
        data = payload.get("data")
        record: Dict[str, Any]
        if isinstance(data, list) and data:
            record = data[0] if isinstance(data[0], dict) else {}
        elif isinstance(data, dict):
            record = data
        else:
            record = {}
        record_id = str(record.get("id") or "")
        return ProviderBookingResult(
            external_id=record_id,
            status=parse_attendance_status(record.get("attendance")),
            raw=payload,
        )

    def update_booking(
        self,
        external_id: str,
        *,
        datetime_str: Optional[str] = None,
        seance_length: Optional[int] = None,
        comment: Optional[str] = None,
        attendance: Optional[int] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
        staff_id: Optional[int] = None,
        services: Optional[List[Dict[str, Any]]] = None,
        client: Optional[Dict[str, Any]] = None,
    ) -> ProviderBookingResult:
        self._require_write()
        company_id = yclients_company_id()
        # PUT /record requires full required fields — merge with current record.
        current = self.get_record(external_id)
        body: Dict[str, Any] = {
            "staff_id": staff_id
            if staff_id is not None
            else current.get("staff_id") or int(yclients_staff_id() or 0),
            "services": services
            if services is not None
            else (current.get("services") or []),
            "client": client if client is not None else (current.get("client") or {}),
            "datetime": datetime_str
            if datetime_str is not None
            else (current.get("datetime") or current.get("date")),
            "seance_length": seance_length
            if seance_length is not None
            else current.get("seance_length") or current.get("length"),
        }
        if comment is not None:
            body["comment"] = comment
        elif current.get("comment") is not None:
            body["comment"] = current.get("comment")
        if attendance is not None:
            body["attendance"] = attendance
        elif current.get("attendance") is not None:
            body["attendance"] = current.get("attendance")
        if custom_fields is not None:
            body["custom_fields"] = custom_fields

        # Normalize services; keep amount (qty of ride sets) when present
        norm_services = []
        for svc in body.get("services") or []:
            if isinstance(svc, dict) and svc.get("id") is not None:
                entry: Dict[str, Any] = {"id": svc["id"]}
                if svc.get("amount") is not None:
                    try:
                        entry["amount"] = max(1, int(svc["amount"]))
                    except (TypeError, ValueError):
                        entry["amount"] = 1
                norm_services.append(entry)
            elif isinstance(svc, int):
                norm_services.append({"id": svc})
        if norm_services:
            body["services"] = norm_services

        # Client must include phone/name for PUT
        cli = body.get("client") or {}
        if isinstance(cli, dict):
            body["client"] = {
                "phone": cli.get("phone") or "",
                "name": cli.get("name") or cli.get("display_name") or "",
                "surname": cli.get("surname") or "",
                "email": cli.get("email") or "",
            }

        payload = self._request(
            "PUT",
            f"/record/{company_id}/{external_id}",
            body=body,
            need_user=True,
        )
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        return ProviderBookingResult(
            external_id=str(external_id),
            status=parse_attendance_status(
                (data or {}).get("attendance") if isinstance(data, dict) else None
            ),
            raw=payload,
        )

    def reschedule_booking(
        self,
        external_id: str,
        *,
        datetime_str: str,
        seance_length: Optional[int] = None,
    ) -> ProviderBookingResult:
        """record_id is preserved after move (confirmed by YCLIENTS support)."""
        return self.update_booking(
            external_id,
            datetime_str=datetime_str,
            seance_length=seance_length,
        )

    def cancel_booking(self, external_id: str) -> bool:
        """Mark cancelled via attendance=-1. Already gone/cancelled → success."""
        self._require_write()
        rid = str(external_id).strip()
        try:
            current = self.get_record(rid)
        except YclientsApiError as exc:
            if exc.status == 404:
                logger.info("yclients_cancel_already_missing record_id=%s", rid)
                return True
            raise

        if not current:
            return True
        life = parse_attendance_status(
            current.get("attendance"),
            deleted=bool(current.get("deleted")),
        )
        if life in ("cancelled", "deleted") or bool(current.get("deleted")):
            logger.info(
                "yclients_cancel_idempotent record_id=%s lifecycle=%s",
                rid,
                life,
            )
            return True

        try:
            self.update_booking(rid, attendance=ATTENDANCE_CANCELLED)
        except YclientsApiError as exc:
            if exc.status == 404:
                logger.info("yclients_cancel_race_missing record_id=%s", rid)
                return True
            raise
        return True

    def delete_booking(self, external_id: str) -> bool:
        """Hard delete via journal DELETE (admin). Prefer cancel_booking for SoT."""
        self._require_write()
        company_id = yclients_company_id()
        self._request(
            "DELETE",
            f"/record/{company_id}/{external_id}",
            need_user=True,
        )
        return True


def get_yclients_provider() -> YclientsProvider:
    return YclientsProvider()


def auth_user_token(login: str, password: str) -> str:
    """Exchange YCLIENTS user login/password for User token (partner Bearer)."""
    if not yclients_partner_token():
        raise YclientsNotConfiguredError("yclients_partner_token_missing")
    provider = YclientsProvider()
    # Bypass enable flags for one-shot auth helper
    base = yclients_api_base_url().rstrip("/")
    url = f"{base}/auth"
    body = json.dumps({"login": login, "password": password}).encode("utf-8")
    headers = {
        "Accept": yclients_accept_header(),
        "Content-Type": "application/json",
        "Authorization": f"Bearer {yclients_partner_token()}",
        "User-Agent": USER_AGENT,
    }
    _rate_limiter.wait()
    req = Request(url, data=body, headers=headers, method="POST")
    with urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    data = payload.get("data") or {}
    token = str(data.get("user_token") or data.get("token") or "").strip()
    if not token:
        raise YclientsApiError("yclients_auth_no_token", payload=payload)
    return token
