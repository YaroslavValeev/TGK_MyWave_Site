"""HTTP client for MyWaveTour camp API (MVP contract v1)."""

from __future__ import annotations

import json
import socket
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from app.config.camp_features import (
    mywave_tour_camp_api_token,
    mywave_tour_camps_api_url,
    mywave_tour_camps_feed_url,
    mywave_tour_use_api_pagination,
)

DEFAULT_TIMEOUT = 20
USER_AGENT = "MyWave-Site-CampSync/1.0"
# Tour prod probe: limit=5 returns items, limit=100 can return [] — keep pages small.
DEFAULT_PAGE_LIMIT = 25
# Tour API historically returned empty for sports=/audience=/status= query params.
# Prefer minimal query; filter published/wakesurf/ru client-side in showcase.
DEFAULT_LIST_QUERY = {
    "limit": str(DEFAULT_PAGE_LIMIT),
}


class TourCampFetchError(Exception):
    """Raised on auth/server/timeout errors from MyWaveTour API."""

    def __init__(self, status_code: int, message: str = "", *, kind: str = "") -> None:
        self.status_code = status_code
        self.kind = kind or _error_kind(status_code, message)
        super().__init__(message or f"tour_fetch_{status_code}")


def _error_kind(status_code: int, message: str = "") -> str:
    if status_code in (401, 403):
        return "auth"
    if status_code >= 500:
        return "server"
    if status_code in (408, 0) or "timeout" in (message or "").lower():
        return "timeout"
    return "client"


def parse_feed_payload(payload: Any) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """
    Canonical envelope:
      {"items": [], "next_offset": null}
    Legacy fallbacks: plain array or camps/data/results keys.
    """
    if isinstance(payload, list):
        return payload, None
    if isinstance(payload, dict):
        if "items" in payload and isinstance(payload.get("items"), list):
            items = payload["items"]
        else:
            items = None
            for key in ("camps", "data", "results"):
                value = payload.get(key)
                if isinstance(value, list):
                    items = value
                    break
        if items is not None:
            next_offset = payload.get("next_offset")
            if next_offset is None:
                return items, None
            try:
                return items, int(next_offset)
            except (TypeError, ValueError):
                return items, None
        if payload.get("id") or payload.get("title"):
            return [payload], None
    raise ValueError("unexpected_tour_feed_shape")


def _build_headers(token: Optional[str] = None) -> Dict[str, str]:
    token = (token if token is not None else mywave_tour_camp_api_token()) or ""
    if not token.strip():
        raise TourCampFetchError(401, "missing MYWAVE_TOUR_CAMP_API_TOKEN", kind="auth")
    return {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
        "Authorization": f"Bearer {token.strip()}",
    }


def _build_list_url(
    *,
    base_url: Optional[str] = None,
    offset: Optional[int] = None,
    updated_since: Optional[datetime] = None,
    limit: int = DEFAULT_PAGE_LIMIT,
) -> str:
    url = (base_url or mywave_tour_camps_api_url()).strip().rstrip("/")
    params = dict(DEFAULT_LIST_QUERY)
    params["limit"] = str(limit)
    params["offset"] = str(0 if offset is None else offset)
    if updated_since is not None:
        params["updated_since"] = updated_since.isoformat()
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{urlencode(params)}"


def _read_json_response(req: Request, *, timeout: int) -> Any:
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        if exc.code in (401, 403) or exc.code >= 500:
            raise TourCampFetchError(exc.code, body or str(exc), kind=_error_kind(exc.code)) from exc
        raise TourCampFetchError(exc.code, body or str(exc)) from exc
    except socket.timeout as exc:
        raise TourCampFetchError(408, "tour_request_timeout", kind="timeout") from exc
    except URLError as exc:
        reason = str(getattr(exc, "reason", exc))
        if "timed out" in reason.lower():
            raise TourCampFetchError(408, reason, kind="timeout") from exc
        raise TourCampFetchError(0, reason, kind="timeout") from exc


def fetch_tour_camps_page(
    *,
    offset: Optional[int] = None,
    updated_since: Optional[datetime] = None,
    base_url: Optional[str] = None,
    token: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
    limit: int = DEFAULT_PAGE_LIMIT,
) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """Fetch one list page from Tour API; raises TourCampFetchError on auth/server/timeout."""
    url = _build_list_url(
        base_url=base_url,
        offset=offset,
        updated_since=updated_since,
        limit=limit,
    )
    req = Request(url, headers=_build_headers(token))
    payload = _read_json_response(req, timeout=timeout)
    return parse_feed_payload(payload)


def fetch_tour_camp_detail(
    camp_id: str,
    *,
    base_url: Optional[str] = None,
    token: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """GET /api/v1/camps/{id} — single camp object."""
    root = (base_url or mywave_tour_camps_api_url()).strip().rstrip("/")
    url = urljoin(f"{root}/", str(camp_id).strip())
    req = Request(url, headers=_build_headers(token))
    payload = _read_json_response(req, timeout=timeout)
    if isinstance(payload, dict) and (payload.get("id") or payload.get("title")):
        return payload
    raise ValueError("unexpected_tour_camp_detail_shape")


def fetch_tour_camps(
    *,
    updated_since: Optional[datetime] = None,
    use_pagination: Optional[bool] = None,
    base_url: Optional[str] = None,
    feed_url: Optional[str] = None,
    token: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> List[Dict[str, Any]]:
    """
    Fetch camps from Tour list API (primary) or legacy feed URL (fallback envelope).
    Follows next_offset until null when pagination enabled.
    """
    use_pagination = mywave_tour_use_api_pagination() if use_pagination is None else use_pagination
    primary = (base_url or mywave_tour_camps_api_url()).strip()
    legacy_feed = (feed_url if feed_url is not None else mywave_tour_camps_feed_url()).strip()

    all_items: List[Dict[str, Any]] = []
    offset: Optional[int] = 0
    seen_offsets: set[int] = set()

    while True:
        try:
            items, next_offset = fetch_tour_camps_page(
                offset=offset,
                updated_since=updated_since if not all_items else None,
                base_url=primary,
                token=token,
                timeout=timeout,
            )
        except TourCampFetchError:
            if not all_items and legacy_feed and legacy_feed != primary:
                items, next_offset = _fetch_legacy_feed_page(
                    legacy_feed,
                    offset=offset,
                    updated_since=updated_since if not all_items else None,
                    token=token,
                    timeout=timeout,
                )
            else:
                raise

        all_items.extend(items)
        if not use_pagination or next_offset is None:
            break
        if next_offset in seen_offsets:
            break
        seen_offsets.add(next_offset)
        offset = next_offset

    return all_items


def _fetch_legacy_feed_page(
    feed_url: str,
    *,
    offset: Optional[int],
    updated_since: Optional[datetime],
    token: Optional[str],
    timeout: int,
) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    params: Dict[str, str] = {}
    if offset is not None:
        params["offset"] = str(offset)
    if updated_since is not None:
        params["updated_since"] = updated_since.isoformat()
    url = feed_url
    if params:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{urlencode(params)}"
    req = Request(url, headers=_build_headers(token))
    payload = _read_json_response(req, timeout=timeout)
    return parse_feed_payload(payload)


# Backward-compatible alias used by import_service
fetch_all_tour_camps = fetch_tour_camps
