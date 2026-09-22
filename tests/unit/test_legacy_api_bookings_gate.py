"""P2: legacy POST /api/bookings gated in Club Box mode."""


def test_legacy_bookings_allowed_by_default(client):
    resp = client.post(
        "/api/bookings",
        json={"date": "2026-07-01", "time": "10:00", "name": "T", "phone": "+70000000000"},
    )
    assert resp.status_code != 410


def test_legacy_bookings_blocked_in_club_box_mode(client, monkeypatch):
    monkeypatch.setenv("CLUB_BOX_MODE", "1")
    from app import create_app

    app = create_app("testing")
    with app.test_client() as c:
        resp = c.post(
            "/api/bookings",
            json={"date": "2026-07-01", "time": "10:00", "name": "T", "phone": "+70000000000"},
        )
    assert resp.status_code == 410
    data = resp.get_json()
    assert data.get("error") == "legacy_booking_endpoint_disabled"
