"""P5/P6: club.yaml loader and module gating on Site."""

from pathlib import Path

import pytest

from app.config.club_config import (
    filter_services_config,
    path_blocked_by_disabled_module,
)

CLUB_BOX_ROOT = Path(__file__).resolve().parents[3] / "NEW2026" / "Club Box"
EXAMPLE = CLUB_BOX_ROOT / "club.example.yaml"


def test_load_club_example_when_configured(app, monkeypatch):
    if not EXAMPLE.is_file():
        pytest.skip("club.example.yaml not found")
    monkeypatch.setenv("CLUB_CONFIG_PATH", str(EXAMPLE))
    from app import create_app

    app2 = create_app("testing")
    with app2.app_context():
        club = app2.config.get("CLUB")
        assert club is not None
        assert club["club"]["name"] == "Club B Demo"


def test_no_club_yaml_leaves_club_none(app, monkeypatch):
    monkeypatch.delenv("CLUB_CONFIG_PATH", raising=False)
    from app import create_app

    app2 = create_app("testing")
    with app2.app_context():
        assert app2.config.get("CLUB") is None


def test_filter_services_hides_gym_when_modules_active():
    club = {"modules": {"booking_boat": True, "shop": False, "blog": False, "reviews": False, "contacts": False}}
    services = [
        {"service_id": "boat", "name": "Boat"},
        {"service_id": "gym", "name": "Gym"},
    ]
    out = filter_services_config(services, club)
    assert len(out) == 1
    assert out[0]["service_id"] == "boat"


def test_path_blocked_covers_booking_and_blog_api():
    club = {
        "modules": {
            "booking_boat": False,
            "shop": True,
            "blog": False,
            "reviews": True,
            "contacts": True,
        }
    }
    assert path_blocked_by_disabled_module("/booking/book", club)
    assert path_blocked_by_disabled_module("/calendar", club)
    assert path_blocked_by_disabled_module("/schedule", club)
    assert path_blocked_by_disabled_module("/api/calendar/book", club)
    assert path_blocked_by_disabled_module("/api/booking", club)
    assert path_blocked_by_disabled_module("/api/bookings", club)
    assert path_blocked_by_disabled_module("/services/book", club)
    assert path_blocked_by_disabled_module("/blog", club)
    assert path_blocked_by_disabled_module("/api/blog/posts", club)
    assert path_blocked_by_disabled_module("/api/blog/diagnostics", club)
    assert not path_blocked_by_disabled_module("/shop/", club)
    assert not path_blocked_by_disabled_module("/", club)


def test_shop_404_when_module_disabled(monkeypatch):
    if not EXAMPLE.is_file():
        pytest.skip("club.example.yaml not found")
    monkeypatch.setenv("CLUB_CONFIG_PATH", str(EXAMPLE))
    from app import create_app

    app = create_app("testing")
    club = app.config.get("CLUB") or {}
    club = {**club, "modules": {**club.get("modules", {}), "shop": False}}
    app.config["CLUB"] = club
    client = app.test_client()
    assert client.get("/shop/").status_code == 404


def test_booking_and_blog_api_404_when_modules_disabled(client, app):
    # Session-scoped app: always restore CLUB so later tests are not polluted.
    previous = app.config.get("CLUB")
    try:
        app.config["CLUB"] = {
            "modules": {
                "booking_boat": False,
                "shop": True,
                "blog": False,
                "reviews": True,
                "contacts": True,
            }
        }
        assert client.get("/calendar").status_code == 404
        assert client.get("/schedule").status_code == 404
        assert client.get("/api/blog/posts").status_code == 404
        assert client.post("/api/calendar/book", json={}).status_code == 404
    finally:
        if previous is None:
            app.config.pop("CLUB", None)
        else:
            app.config["CLUB"] = previous


def test_explicit_missing_club_yaml_fail_closed(monkeypatch, tmp_path):
    missing = tmp_path / "no-such-club.yaml"
    monkeypatch.setenv("CLUB_CONFIG_PATH", str(missing))
    from app import create_app

    app = create_app("testing")
    club = app.config.get("CLUB") or {}
    assert club.get("modules", {}).get("blog") is False
    assert club.get("modules", {}).get("booking_boat") is False
    assert app.config.get("CLUB_CONFIG_ERROR") == "missing_file"
    client = app.test_client()
    assert client.get("/blog").status_code == 404
    assert client.get("/api/blog/posts").status_code == 404
