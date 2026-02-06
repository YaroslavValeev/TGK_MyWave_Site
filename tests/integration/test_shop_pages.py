import pytest
from bs4 import BeautifulSoup

from app import create_app


def test_shop_page_renders_products():
    app = create_app(config_name="testing")
    client = app.test_client()

    resp = client.get("/shop/")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "store-products" in html

    soup = BeautifulSoup(html, "html.parser")
    product_cards = soup.select("#store-products .product-card")
    # There should be at least one product-card
    assert len(product_cards) >= 1

    # Each product card should contain a link to product page
    for card in product_cards:
        a = card.find("a")
        assert a and a.has_attr("href")
        assert "/shop/product/" in a["href"]
