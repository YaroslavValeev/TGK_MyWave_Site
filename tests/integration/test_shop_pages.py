import pytest
from bs4 import BeautifulSoup

from app import create_app


def test_shop_page_renders_products():
    app = create_app(config_name='testing')
    client = app.test_client()

    resp = client.get('/shop/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'store-products' in html

    soup = BeautifulSoup(html, 'html.parser')
    product_cards = soup.select('#store-products .product-card')
    # There should be at least one product-card
    assert len(product_cards) >= 1

    # Кнопка заявки: страница товара на сайте или внешний URL
    for card in product_cards:
        a = card.find('a')
        if a and a.has_attr('href'):
            href = a['href']
            assert '/shop/product/' in href or href.startswith('https://')
