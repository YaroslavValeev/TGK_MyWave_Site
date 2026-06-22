"""Product lead validation and storage (PR53)."""

import pytest

from app.services.product_leads import (
    build_product_lead_row,
    save_product_lead,
    validate_product_lead,
    ProductLeadResult,
)


def test_validate_product_lead_ok():
    assert not validate_product_lead(
        {
            "name": "Anna",
            "phone": "+7 916 111 22 33",
            "product_id": "balance-board",
            "product_title": "Баланс-борд",
            "quantity": 1,
        }
    )


def test_validate_product_lead_missing_phone():
    errors = validate_product_lead(
        {"name": "Anna", "phone": "123", "product_id": "x", "product_title": "T"}
    )
    assert "invalid:phone" in errors


def test_save_product_lead_with_mock_append(app):
    captured = {}

    def _append(sid, sheet, values):
        captured["values"] = values

    with app.app_context():
        result = save_product_lead(
            {
                "name": "Пётр",
                "phone": "+7 916 000 00 01",
                "telegram": "@petr",
                "email": "p@test.ru",
                "product_id": "wave-cards",
                "product_title": "Wave Cards",
                "quantity": 2,
                "comment": "Нужна доставка",
                "page_url": "https://example/shop",
                "source": "product",
            },
            sheet_append=_append,
        )
    assert isinstance(result, ProductLeadResult)
    assert result.lead_id.startswith("prod_lead_")
    assert captured["values"][5] == "wave-cards"
    assert captured["values"][7] == "2"


def test_build_product_lead_row_headers_order():
    row = build_product_lead_row(
        "prod_lead_test",
        {
            "name": "N",
            "phone": "P",
            "product_id": "id",
            "product_title": "Title",
            "quantity": 1,
        },
    )
    assert row[0] == "prod_lead_test"
    assert row[11] == "new"
