from urllib.parse import quote


def test_telegram_preview_rejects_arbitrary_url(client):
    rv = client.get("/blog/media/telegram-preview?u=https://example.com/evil")
    assert rv.status_code in (302, 301)
    assert "/static/images/Place1Logo.png" in (rv.headers.get("Location") or "")


def test_telegram_preview_redirects_to_og_image(client, monkeypatch):
    from app.routes import blog as blog_routes

    monkeypatch.setattr(
        blog_routes,
        "fetch_telegram_og_image",
        lambda _url, **_kwargs: "https://cdn4.telesco.pe/file/preview.jpg",
    )
    u = quote("https://t.me/wakedivision/520", safe="")
    rv = client.get(f"/blog/media/telegram-preview?u={u}")
    assert rv.status_code == 302
    assert rv.headers.get("Location") == "https://cdn4.telesco.pe/file/preview.jpg"
