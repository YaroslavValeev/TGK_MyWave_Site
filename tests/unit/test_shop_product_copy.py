"""Тексты и разметка каталога товаров."""
from app.routes.shop import PRODUCTS, PRODUCT_REQUEST_SUCCESS_MESSAGE


def test_wakesurfpolia_description_is_board_game_not_water_kit():
    desc = PRODUCTS["wakesurfpolia"]["description"].lower()
    assert "настольн" in desc or "игра" in desc
    assert "страховочн" not in desc
    assert "комплект для тренировок на воде" not in desc


def test_wave_cards_not_using_hero_image_path():
    folder = PRODUCTS["wave-cards"].get("image_folder", "")
    assert "hero-wakesurf" not in folder


def test_home_shop_product_cards_have_single_description_block(client, mocker):
    mocker.patch(
        "app.routes.shop._products_with_resolved_images",
        return_value={
            "wakesurfpolia": {
                "title": "WakeSurf Polia",
                "price": "10 000 ₽",
                "description": PRODUCTS["wakesurfpolia"]["description"],
                "cover": "images/Shop/WakeSurfPolia/1000055852.jpg",
                "fallback": "images/Place1Logo.png",
                "images": ["images/Shop/WakeSurfPolia/1000055852.jpg"],
                "image_urls": [],
            }
        },
    )
    rv = client.get("/")
    html = rv.get_data(as_text=True)
    assert "product-card__body" in html
    assert html.count(PRODUCTS["wakesurfpolia"]["description"]) >= 1
    products_block = html.split('class="products-carousel"', 1)
    assert len(products_block) > 1, "products carousel section missing"
    products_html = products_block[1].split("</section>", 1)[0]
    assert "card-details__text" not in products_html


def test_shop_product_prices_owner_qa():
    assert PRODUCTS["poncho"]["price"] == "14 500 ₽"
    assert PRODUCTS["wakesurfpolia"]["price"] == "10 000 ₽"
    assert "в зале" in PRODUCTS["sertificate"]["title"].lower()


def test_product_request_success_message_mentions_made_to_order():
    assert "индивидуально" in PRODUCT_REQUEST_SUCCESS_MESSAGE.lower()
    assert "склада нет" in PRODUCT_REQUEST_SUCCESS_MESSAGE.lower()
    assert "7 дней" in PRODUCT_REQUEST_SUCCESS_MESSAGE
