"""PWA manifest and routes."""

from app.services.pwa_manifest import build_pwa_manifest


def test_manifest_webmanifest_ok(client):
    resp = client.get("/manifest.webmanifest")
    assert resp.status_code == 200
    assert resp.mimetype == "application/manifest+json"
    data = resp.get_json()
    assert data.get("display") == "standalone"
    assert "name" in data
    assert data.get("icons")


def test_service_worker_ok(client):
    resp = client.get("/sw.js")
    assert resp.status_code == 200
    assert b"service worker" in resp.data.lower() or b"skipWaiting" in resp.data


def test_manifest_booking_boat_uses_booking_start_url():
    data = build_pwa_manifest(
        club={"modules": {"booking_boat": True}, "branding": {"brand_name": "Demo"}},
        static_icon_url="/static/pwa/icon-512.png",
    )
    assert data["start_url"] == "/#services"


def test_legacy_booking_page_renders(client):
    assert client.get("/booking/?service=boat").status_code == 200


def test_legacy_calendar_redirects_to_home_services(client):
    rv = client.get("/calendar")
    assert rv.status_code == 302
    assert rv.headers["Location"].endswith("/#services")


def test_manifest_uses_club_branding(monkeypatch):
    if not __import__("pathlib").Path(
        __import__("pathlib").Path(__file__).resolve().parents[3]
        / "NEW2026"
        / "Club Box"
        / "club.example.yaml"
    ).is_file():
        return
    from pathlib import Path

    example = Path(__file__).resolve().parents[3] / "NEW2026" / "Club Box" / "club.example.yaml"
    monkeypatch.setenv("CLUB_CONFIG_PATH", str(example))
    from app import create_app

    app = create_app("testing")
    with app.test_client() as c:
        data = c.get("/manifest.webmanifest").get_json()
    assert "Club B Demo" in data.get("name", "")
