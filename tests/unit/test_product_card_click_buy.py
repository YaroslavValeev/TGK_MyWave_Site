"""Product cards trigger existing Buy button on card click."""

from pathlib import Path


def test_index_product_cards_click_buy_markup():
    html = Path("templates/index.html").read_text(encoding="utf-8")
    products = html.split('class="products-carousel"', 1)[1].split("</section>", 1)[0]
    assert "data-product-card-click-buy" in products
    assert "data-product-buy-trigger" in products
    assert "js-expandable-card" not in products


def test_shop_product_cards_click_buy_markup():
    html = Path("templates/shop.html").read_text(encoding="utf-8")
    assert "data-product-card-click-buy" in html
    assert "data-product-buy-trigger" in html
    assert 'class="product-card product-card--unified" data-product-card-click-buy' in html
    assert "js-expandable-card" not in html


def test_product_card_click_js_delegates_to_buy_button():
    js = Path("static/js/product-request-form.js").read_text(encoding="utf-8")
    assert "bindProductCardClickBuy" in js
    assert "data-product-card-click-buy" in js
    assert "buyButton.click()" in js
    card_handler = js.split("function bindProductCardClickBuy", 1)[1].split("function bindProductRequest", 1)[0]
    assert "fetch('/shop/api/product-request'" not in card_handler


def test_services_expand_excludes_product_cards():
    js = Path("static/js/services-expand.js").read_text(encoding="utf-8")
    assert ".product-card" in js


def test_home_product_cards_render_click_buy_attrs(client, mocker):
    mocker.patch(
        "app.routes.shop._products_with_resolved_images",
        return_value={
            "balance-board": {
                "title": "Balance Board",
                "price": "1 000 ₽",
                "description": "Test board",
                "cover": "images/Shop/BalanceBoard/cover.jpg",
                "fallback": "images/Place1Logo.png",
                "images": [],
                "image_urls": [],
            }
        },
    )
    html = client.get("/").get_data(as_text=True)
    assert 'data-product-card-click-buy' in html
    assert 'data-product-buy-trigger' in html
