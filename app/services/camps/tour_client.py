"""HTTP client for MyWaveTour camp feed (CampContract)."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config.camp_features import (
    mywave_tour_camp_api_token,
    mywave_tour_camps_api_url,
    mywave_tour_camps_feed_url,
    mywave_tour_use_api_pagination,
)

DEFAULT_TIMEOUT = 20
USER_AGENT = "MyWave-Site-CampSync/1.0"


class TourCampFetchError(Exception):
    """Raised on auth/server errors from MyWaveTour API."""

    def __init__(self, status_code: int, message: str = "") -> None:
        self.status_code = status_code
        super().__init__(message or f"tour_fetch_{status_code}")


def parse_feed_payload(payload: Any) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """
    Parse MyWaveTour feed shapes:
    - Variant A: {"items": [...], "next_offset": 100}
    - Variant B: plain JSON array
  """
    if isinstance(payload, list):
        return payload, None
    if isinstance(payload, dict):
        items: Optional[List[Dict[str, Any]]] = None
        for key in ("items", "camps", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                items = value
                break
        if items is not None:
            next_offset = payload.get("next_offset")
            if next_offset is not None:
                try:
                    next_offset = int(next_offset)
                except (TypeError, ValueError):
                    next_offset = None
            return items, next_offset
    raise ValueError("unexpected_tour_feed_shape")


def _build_headers(token: Optional[str] = None) -> Dict[str, str]:
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    token = (token if token is not None else mywave_tour_camp_api_token()) or ""
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _request_url(
    *,
    base_url: Optional[str] = None,
    offset: Optional[int] = None,
    updated_since: Optional[datetime] = None,
) -> str:
    url = (base_url or mywave_tour_camps_feed_url()).strip()
    params: Dict[str, str] = {}
    if offset is not None:
        params["offset"] = str(offset)
    if updated_since is not None:
        params["updated_since"] = updated_since.isoformat()
    if params:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{urlencode(params)}"
    return url


def fetch_tour_camps_page(
    *,
    offset: Optional[int] = None,
    updated_since: Optional[datetime] = None,
    base_url: Optional[str] = None,
    token: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """Fetch a single feed page; raises TourCampFetchError on 401/403/5xx."""
    url = _request_url(base_url=base_url, offset=offset, updated_since=updated_since)
    req = Request(url, headers=_build_headers(token))
    try:
        with urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in (401, 403) or exc.code >= 500:
            raise TourCampFetchError(exc.code, str(exc)) from exc
        raise
    except URLError:
        raise
    return parse_feed_payload(payload)


def fetch_all_tour_camps(
    *,
    updated_since: Optional[datetime] = None,
    use_pagination: Optional[bool] = None,
    base_url: Optional[str] = None,
    token: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> List[Dict[str, Any]]:
    """Fetch full camp list; follows next_offset when pagination is enabled."""
    use_pagination = mywave_tour_use_api_pagination() if use_pagination is None else use_pagination
    feed_url = base_url or mywave_tour_camps_feed_url()
    api_url = mywave_tour_camps_api_url()
    primary = feed_url or api_url

    all_items: List[Dict[str, Any]] = []
    offset: Optional[int] = 0 if use_pagination else None
    seen_offsets: set[int] = set()

    while True:
        items, next_offset = fetch_tour_camps_page(
            offset=offset,
            updated_since=updated_since if not all_items else None,
            base_url=primary,
            token=token,
            timeout=timeout,
        )
        all_items.extend(items)
        if not use_pagination or next_offset is None:
            break
        if next_offset in seen_offsets:
            break
        seen_offsets.add(next_offset)
        offset = next_offset

    return all_items
