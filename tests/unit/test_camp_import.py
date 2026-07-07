"""Unit tests for Camp import normalization, validation, and Tour client."""

from datetime import date
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from app.services.camps.import_service import sync_camps_from_tour
from app.services.camps.normalize import normalize_tour_camp, normalized_title_key
from app.services.camps.tour_client import (
    TourCampFetchError,
    _build_list_url,
    fetch_tour_camps,
    parse_feed_payload,
)
from app.services.camps.validate import validate_camp


def test_normalize_tour_camp_basic():
    raw = {
        "id": "tour-42",
        "title": "Вейксерф кемп в Сочи",
        "discipline": "вейксерф",
        "start_date": "2026-08-10",
        "end_date": "2026-08-17",
        "country": "Россия",
        "city": "Сочи",
        "price": 85000,
        "url": "https://www.mywavetour.ru/camp/sochi",
        "publication_status": "published",
        "availability_status": "available",
        "content_rights_status": "partner_allowed",
    }
    camp = normalize_tour_camp(raw)
    assert camp["source_system"] == "mywavetour"
    assert camp["external_id"] == "tour-42"
    assert camp["sport"] == "wakesurf"
    assert camp["start_date"] == date(2026, 8, 10)
    assert camp["price_from"] == 85000
    assert camp["slug"]
    assert camp["content_rights_status"] == "partner_allowed"
    assert camp["availability_status"] == "available"
    assert camp["tour_publication_status"] == "published"


def test_normalize_tour_camp_defaults_content_rights_unknown():
    camp = normalize_tour_camp({"id": "1", "title": "Test", "start_date": "2026-08-01"})
    assert camp["content_rights_status"] == "unknown"
    assert camp["availability_status"] == "unknown"


def test_normalize_tour_camp_sport_array_and_tour_prefix():
    raw = {
        "id": "99",
        "title": "Mixed camp",
        "sport": ["wakesurf", "wakeboard"],
        "start_date": "2026-09-01",
    }
    camp = normalize_tour_camp(raw)
    assert camp["external_id"] == "tour_99"
    assert camp["sport"] == "mixed"


def test_validate_camp_requires_title_and_slug():
    ok, errs = validate_camp({"source_system": "mywavetour", "sport": "wakesurf", "level": "all_levels"})
    assert not ok
    assert "title_required" in errs
    assert "slug_required" in errs


def test_normalized_title_key_collapses_spaces():
    assert normalized_title_key("  Вейк   Кемп  ") == normalized_title_key("вейк кемп")


def test_parse_feed_variant_b_array():
    items, next_offset = parse_feed_payload([{"id": "tour_1", "title": "A"}])
    assert len(items) == 1
    assert next_offset is None


def test_parse_feed_variant_a_items_next_offset():
    items, next_offset = parse_feed_payload({"items": [{"id": "tour_2"}], "next_offset": 100})
    assert len(items) == 1
    assert next_offset == 100


def test_parse_feed_empty_envelope():
    items, next_offset = parse_feed_payload({"items": [], "next_offset": None})
    assert items == []
    assert next_offset is None


def test_tour_camp_fetch_error_attrs():
    err = TourCampFetchError(403, "forbidden")
    assert err.status_code == 403
    assert err.kind == "auth"
    assert "forbidden" in str(err)


def test_build_list_url_includes_mvp_query_params():
    url = _build_list_url(base_url="https://api.mywavetour.ru/api/v1/camps", offset=0)
    assert "status=published" in url
    assert "sports=wakesurf" in url
    assert "audience=ru" in url
    assert "limit=100" in url
    assert "offset=0" in url


@patch("app.services.camps.tour_client.mywave_tour_camp_api_token", return_value="secret-token")
@patch("app.services.camps.tour_client.urlopen")
def test_fetch_tour_camps_sends_bearer_and_paginates(mock_urlopen, _mock_token):
    page1 = BytesIO(b'{"items":[{"id":"1","title":"A"}],"next_offset":100}')
    page2 = BytesIO(b'{"items":[{"id":"2","title":"B"}],"next_offset":null}')

    mock_resp1 = MagicMock()
    mock_resp1.read.return_value = page1.getvalue()
    mock_resp1.__enter__ = lambda s: s
    mock_resp1.__exit__ = MagicMock(return_value=False)

    mock_resp2 = MagicMock()
    mock_resp2.read.return_value = page2.getvalue()
    mock_resp2.__enter__ = lambda s: s
    mock_resp2.__exit__ = MagicMock(return_value=False)

    mock_urlopen.side_effect = [mock_resp1, mock_resp2]

    items = fetch_tour_camps(
        use_pagination=True,
        base_url="https://api.mywavetour.ru/api/v1/camps",
        token="secret-token",
    )
    assert len(items) == 2
    first_req = mock_urlopen.call_args_list[0][0][0]
    assert first_req.get_header("Authorization") == "Bearer secret-token"
    second_url = mock_urlopen.call_args_list[1][0][0].full_url
    assert "offset=100" in second_url


@patch("app.services.camps.tour_client.mywave_tour_camp_api_token", return_value="")
def test_fetch_tour_camps_missing_token_raises_auth_error(_mock_token):
    with pytest.raises(TourCampFetchError) as exc_info:
        fetch_tour_camps(base_url="https://api.mywavetour.ru/api/v1/camps")
    assert exc_info.value.status_code == 401
    assert exc_info.value.kind == "auth"


@patch("app.services.camps.import_service.fetch_all_tour_camps")
def test_sync_camps_auth_error_logs_and_reraises(mock_fetch, app):
    mock_fetch.side_effect = TourCampFetchError(403, "forbidden", kind="auth")
    from app.database.camp_models import CampImportLog
    from app.database.models import db

    with app.app_context():
        db.create_all()
        with pytest.raises(TourCampFetchError):
            sync_camps_from_tour()
        log = db.session.query(CampImportLog).order_by(CampImportLog.id.desc()).first()
        assert log is not None
        assert log.status == "failed"
        assert "tour_auth_error_403" in (log.message or "")
