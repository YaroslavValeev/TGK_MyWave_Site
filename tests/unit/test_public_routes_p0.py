"""P0 public routes: robots.txt, privacy, offer."""


def test_robots_txt(client):
    resp = client.get("/robots.txt")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "User-agent: *" in body
    assert "Allow: /" in body
    assert "Sitemap: https://mywavewake.ru/sitemap.xml" in body


def test_privacy_page(client):
    resp = client.get("/privacy")
    assert resp.status_code == 200
    assert "конфиденциальности".encode("utf-8") in resp.data


def test_offer_page(client):
    resp = client.get("/offer")
    assert resp.status_code == 200
    assert "оферта".encode("utf-8") in resp.data.lower()


def test_legal_consent_pages(client):
    for path in (
        "/legal/personal-data-consent",
        "/legal/media-consent",
        "/legal/wake-challenge-consent",
    ):
        resp = client.get(path)
        assert resp.status_code == 200
