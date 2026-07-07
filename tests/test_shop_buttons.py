from app import create_app


def test_shop_page_and_product_links():
    app = create_app(config_name='testing')
    client = app.test_client()

    resp = client.get('/shop/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'data-product-card-click-buy' in html
    assert 'data-product-buy-trigger' in html
    assert 'data-product-request' in html or '/shop/product/' in html
    assert 'joys-brand.com/aksessuary/nastolnaya-igra-wakesurfopolie1' in html
