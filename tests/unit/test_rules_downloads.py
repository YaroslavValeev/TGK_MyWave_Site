"""Карточки официальных правил на странице чек-листа."""
from app.services.rules_downloads import load_rules_downloads, RULES_DIR


def test_load_rules_downloads_resolves_existing_pdfs():
    def fake_url_for(endpoint, filename, **kwargs):
        return f"/static/{filename}"

    items = load_rules_downloads(fake_url_for)
    assert items
    ready = [r for r in items if r["has_download"]]
    assert len(ready) >= 4
    for r in ready:
        assert r["pdf_url"]
        assert r["pdf_url"].startswith("/static/docs/rules/")


def test_iwwf_asia_pdf_exists_on_disk():
    candidates = [
        "iwwf_asia_wakesurf_rules_ru.pdf",
        "wakesurf_rules_ru_updated.pdf",
    ]
    assert any((RULES_DIR / name).is_file() for name in candidates)
