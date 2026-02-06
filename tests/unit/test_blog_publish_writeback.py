from datetime import datetime


def test_ack_publish_writes_canonical_url_and_site_fields(app, mocker):
    """
    P0: После успешной публикации ack должен:
    - поставить published_posts=TRUE
    - записать published_at
    - очистить publish_error и lock-и
    - записать canonical_url (если есть slug)
    - НЕ трогать status/slug по умолчанию
    """
    from app.services.blog import publish as publish_mod

    mocker.patch(
        "app.services.blog.publish.resolve_parser_source",
        return_value=("sheet1", "raw_feed"),
    )

    headers = [
        "id",
        "row_number",
        "status",
        "published_posts",
        "published_at",
        "publish_attempts",
        "publish_last_try_at",
        "publish_error",
        "canonical_url",
        "publish_lock_by",
        "publish_lock_until",
        "slug",
    ]

    # row_number=2 -> индекс 0 в records
    records = [
        {
            "id": "1013",
            "row_number": "2",
            "status": "READY_TO_PUBLISH",
            "published_posts": "",
            "published_at": "",
            "publish_attempts": "0",
            "publish_last_try_at": "",
            "publish_error": "OLD_ERR",
            "canonical_url": "",
            "publish_lock_by": "site:mywave",
            "publish_lock_until": "2099-01-01T00:00:00Z",
            "slug": "my-post-slug",
        }
    ]

    mocker.patch(
        "app.services.blog.publish.read_sheet", return_value=(records, headers)
    )

    captured = {}

    def _fake_update_sheet_cells(spreadsheet_id, sheet_name, updates):
        captured["spreadsheet_id"] = spreadsheet_id
        captured["sheet_name"] = sheet_name
        captured["updates"] = updates
        return True

    mocker.patch(
        "app.services.blog.publish.update_sheet_cells",
        side_effect=_fake_update_sheet_cells,
    )

    with app.app_context():
        # SERVER_NAME не задан в проекте по умолчанию → fallback на mywavetraining.ru
        ok = publish_mod.ack_publish(
            2, "1013", datetime(2026, 1, 28, 10, 0, 0), slug=None
        )

    assert ok is True
    assert captured["spreadsheet_id"] == "sheet1"
    assert captured["sheet_name"] == "raw_feed"

    ranges = [u["range"] for u in captured["updates"]]
    values = {u["range"]: u["values"][0][0] for u in captured["updates"]}

    # Базовые site-owned поля
    assert "D2" in ranges  # published_posts
    assert values["D2"] == "TRUE"
    assert "E2" in ranges  # published_at
    assert "F2" in ranges  # publish_attempts
    assert "G2" in ranges  # publish_last_try_at
    assert "H2" in ranges  # publish_error cleared
    assert values["H2"] == ""

    # Lock-и очищены
    assert "J2" in ranges  # publish_lock_by cleared
    assert values["J2"] == ""
    assert "K2" in ranges  # publish_lock_until cleared
    assert values["K2"] == ""

    # canonical_url записан из slug
    assert "I2" in ranges
    assert values["I2"].endswith("/blog/my-post-slug")

    # status/slug не пишем
    assert "C2" not in ranges  # status
    assert "L2" not in ranges  # slug


def test_ack_publish_schema_mismatch_sets_publish_error(app, mocker):
    """P0: если нет обязательных колонок (например canonical_url) — publish_error=WP_SCHEMA_MISMATCH, ack=False."""
    from app.services.blog import publish as publish_mod

    mocker.patch(
        "app.services.blog.publish.resolve_parser_source",
        return_value=("sheet1", "raw_feed"),
    )

    # canonical_url отсутствует
    headers = [
        "id",
        "row_number",
        "status",
        "published_posts",
        "published_at",
        "publish_attempts",
        "publish_last_try_at",
        "publish_error",
    ]
    records = [{"id": "1013", "row_number": "2"}]
    mocker.patch(
        "app.services.blog.publish.read_sheet", return_value=(records, headers)
    )

    captured = {"updates": []}

    def _fake_update_sheet_cells(_sid, _sn, updates):
        captured["updates"] = updates
        return True

    mocker.patch(
        "app.services.blog.publish.update_sheet_cells",
        side_effect=_fake_update_sheet_cells,
    )

    with app.app_context():
        ok = publish_mod.ack_publish(
            2, "1013", datetime(2026, 1, 28, 10, 0, 0), slug="x"
        )

    assert ok is False
    # Должны попытаться записать WP_SCHEMA_MISMATCH в publish_error (колонка H -> range H2 в нашем порядке)
    assert captured["updates"]
    assert captured["updates"][0]["values"][0][0] == "WP_SCHEMA_MISMATCH"


def test_record_publish_error_by_id_uses_unique_id_match(app, mocker):
    """P0: если row_number отсутствует — пишем publish_error по уникальному совпадению ID."""
    from app.services.blog import publish as publish_mod

    mocker.patch(
        "app.services.blog.publish.resolve_parser_source",
        return_value=("sheet1", "raw_feed"),
    )

    # Две строки, нужная — вторая (i=1 → row_number=3)
    records = [
        {"id": "aaa"},
        {"id": "target"},
    ]
    headers = ["id"]
    mocker.patch(
        "app.services.blog.publish.read_sheet", return_value=(records, headers)
    )

    called = {}

    def _fake_record_publish_error(
        row_number, error_msg, increment_attempts=True, logger=None
    ):
        called["row_number"] = row_number
        called["error_msg"] = error_msg

    mocker.patch(
        "app.services.blog.publish.record_publish_error",
        side_effect=_fake_record_publish_error,
    )

    with app.app_context():
        ok = publish_mod.record_publish_error_by_id("target", "WP_ROW_NUMBER_MISSING")

    assert ok is True
    assert called["row_number"] == 3
    assert called["error_msg"] == "WP_ROW_NUMBER_MISSING"
