"""Regression tests for Camp sync configuration and canonical card media."""

from pathlib import Path

from scripts import run_camp_sync


def test_camp_sync_uses_environment_flask_config(monkeypatch):
    monkeypatch.setenv("FLASK_CONFIG", "production")
    monkeypatch.setenv("FLASK_ENV", "development")
    assert run_camp_sync._config_name() == "production"


def test_camp_sync_supports_short_config_aliases(monkeypatch):
    monkeypatch.delenv("FLASK_CONFIG", raising=False)
    monkeypatch.setenv("FLASK_ENV", "prod")
    assert run_camp_sync._config_name() == "production"


def test_camp_card_uses_reusable_media_frame():
    template = Path("templates/projects/camp/index.html").read_text(encoding="utf-8")
    assert 'class="card-media-frame"' in template
    assert "data-card-media-fit" in template


def test_card_media_frame_is_16_by_9_and_supports_video_iframe():
    css = Path("static/css/services-carousel.css").read_text(encoding="utf-8")
    assert ".card-media-frame" in css
    assert "aspect-ratio: 16/9" in css
    assert ".card-media-frame > video" in css
    assert ".card-media-frame > iframe" in css


def test_media_fit_script_scans_opt_in_images():
    js = Path("static/js/card-media-fit.js").read_text(encoding="utf-8")
    assert "[data-card-media-fit]" in js


def test_card_media_assets_have_cache_bust_versions():
    base = Path("templates/base.html").read_text(encoding="utf-8")
    assert "services-carousel.css') }}?v=card-media-frame1" in base
    assert "card-media-fit.js') }}?v=2" in base
