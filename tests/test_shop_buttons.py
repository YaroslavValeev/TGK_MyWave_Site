from app import create_app


def test_shop_page_and_product_links():
    app = create_app(config_name='testing')
    client = app.test_client()

    resp = client.get('/shop/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    # Ensure at least one product link to product pages is present
    assert '/shop/product/balance-board' in html
    assert '/shop/product/poncho' in html
