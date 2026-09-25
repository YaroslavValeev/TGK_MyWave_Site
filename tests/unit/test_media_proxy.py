"""Внешние обложки через наш домен: allowlist, кэш, редирект на оригинал при сбое."""

from contextlib import contextmanager
from unittest import mock

from app.services import media_proxy
from app.services.media_proxy import is_proxyable_url, proxied_image_url

TOUR_IMG = "https://mywavetour.ru/ingestion-media/tg-x-1-0-image-abc.jpg"
RSS_IMG = "https://www.wakeboardingmag.com/wp-content/uploads/2026/09/WKB926-Axis-t235.jpg"


@contextmanager
def _static_folder(app, path):
    previous = app.static_folder
    app.static_folder = str(path)
    try:
        yield
    finally:
        app.static_folder = previous


def test_allowlisted_hosts_are_proxied():
    assert proxied_image_url(TOUR_IMG).startswith("/media/ext?u=https%3A%2F%2Fmywavetour.ru")
    assert proxied_image_url(RSS_IMG).startswith("/media/ext?u=")


def test_own_and_unknown_urls_unchanged():
    own = "https://mywavewake.ru/static/uploads/review_media/a.jpg"
    assert proxied_image_url(own) == own
    assert proxied_image_url("/static/images/Place1Logo.png") == "/static/images/Place1Logo.png"
    assert proxied_image_url("https://evil.example.com/a.jpg") == "https://evil.example.com/a.jpg"
    assert proxied_image_url("") == ""


def test_rejects_unsafe_urls():
    assert not is_proxyable_url("http://mywavetour.ru/a.jpg")
    assert not is_proxyable_url("https://user:pw@mywavetour.ru/a.jpg")
    assert not is_proxyable_url("https://mywavetour.ru:8443/a.jpg")
    assert not is_proxyable_url("https://mywavetour.ru.evil.com/a.jpg")
    assert not is_proxyable_url("https://127.0.0.1/a.jpg")


def test_route_rejects_non_allowlisted(client):
    assert client.get("/media/ext?u=https://evil.example.com/a.jpg").status_code == 400
    assert client.get("/media/ext").status_code == 400


def test_route_redirects_to_original_when_fetch_fails(client):
    with mock.patch.object(media_proxy.requests, "get", side_effect=media_proxy.requests.ConnectionError()):
        rv = client.get("/media/ext", query_string={"u": TOUR_IMG + "?fail=1"})
    assert rv.status_code == 302
    assert rv.headers["Location"] == TOUR_IMG + "?fail=1"


def test_route_serves_and_caches_image(client, app, tmp_path):
    fake = mock.MagicMock()
    fake.status_code = 200
    fake.headers = {"Content-Type": "image/jpeg"}
    fake.iter_content.return_value = [b"\xff\xd8\xff", b"jpegdata"]
    url = TOUR_IMG + "?cache-test=1"
    with _static_folder(app, tmp_path):
        with mock.patch.object(media_proxy.requests, "get", return_value=fake) as get:
            first = client.get("/media/ext", query_string={"u": url})
            second = client.get("/media/ext", query_string={"u": url})
    assert first.status_code == 200
    assert first.data == b"\xff\xd8\xffjpegdata"
    assert second.status_code == 200
    assert get.call_count == 1


def test_route_refuses_non_image_content(client, app, tmp_path):
    fake = mock.MagicMock()
    fake.status_code = 200
    fake.headers = {"Content-Type": "text/html"}
    url = TOUR_IMG + "?html=1"
    with _static_folder(app, tmp_path):
        with mock.patch.object(media_proxy.requests, "get", return_value=fake):
            rv = client.get("/media/ext", query_string={"u": url})
    assert rv.status_code == 302


def test_camp_card_uses_proxied_cover(app):
    with app.test_request_context():
        from flask import render_template

        html = render_template(
            "camps/partials/card.html",
            c={"id": "tour_x", "title": "Кемп", "cover_image_url": TOUR_IMG, "source_badge": "Из MyWaveTour"},
            cover_fallback="images/Place1Logo.png",
        )
    assert "/media/ext?u=" in html
