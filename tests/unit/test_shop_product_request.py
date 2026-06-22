"""Shop product request API (PR53)."""

from unittest.mock import patch

import pytest

from app.services.product_leads import ProductLeadResult


@pytest.fixture
def valid_payload():
    return {
        "name": "Мария",
        "phone": "+7 916 123 45 67",
        "telegram": "@maria",
        "email": "maria@example.com",
        "product_id": "balance-board",
        "product_title": "Баланс-борд",
        "quantity": 1,
        "comment": "Хочу забрать на площадке",
        "page_url": "https://mywavewake.ru/shop/product/balance-board",
    }


class TestShopProductRequestApi:
    @patch("app.routes.shop.notify_new_application")
    @patch("app.routes.shop.save_product_lead")
    def test_product_request_success(self, mock_save, mock_notify, client, valid_payload):
        mock_save.return_value = ProductLeadResult(
            lead_id="prod_lead_abc",
            status="new",
            sheet_name="Product_Leads",
        )
        rv = client.post("/shop/api/product-request", json=valid_payload)
        assert rv.status_code == 200
        body = rv.get_json()
        assert body["ok"] is True
        assert "Заявка отправлена" in body["message"]
        mock_notify.assert_called_once()

    @patch("app.routes.shop.notify_new_application")
    @patch("app.routes.shop.save_product_lead")
    def test_product_request_validation_error(self, mock_save, mock_notify, client):
        rv = client.post(
            "/shop/api/product-request",
            json={"name": "X", "phone": "1", "product_id": "", "product_title": ""},
        )
        assert rv.status_code == 400
        mock_save.assert_not_called()
        mock_notify.assert_not_called()

    @patch("app.routes.shop.notify_new_application")
    @patch("app.routes.shop.save_product_lead")
    def test_telegram_failure_still_returns_ok(self, mock_save, mock_notify, client, valid_payload):
        mock_save.return_value = ProductLeadResult(
            lead_id="prod_lead_xyz",
            status="new",
            sheet_name="Product_Leads",
        )
        mock_notify.return_value = False
        rv = client.post("/shop/api/product-request", json=valid_payload)
        assert rv.status_code == 200
        assert rv.get_json()["ok"] is True

    def test_unknown_product_id(self, client, valid_payload):
        payload = {**valid_payload, "product_id": "nonexistent-slug"}
        rv = client.post("/shop/api/product-request", json=payload)
        assert rv.status_code == 400
