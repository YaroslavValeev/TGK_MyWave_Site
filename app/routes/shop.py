from flask import Blueprint, render_template, abort, current_app

shop_bp = Blueprint("shop", __name__, url_prefix="/shop")

# Minimal product catalog — enough for product pages
PRODUCTS = {
    "balance-board": {
        "title": "Баланс-борд",
        "price": "7 500 ₽",
        "description": "Тренировочный баланс-борд для трюков и фитнеса.",
        "image": "images/balans_trick_trening1.jpg",
    },
    "balance-board-big": {
        "title": "Баланс-борд Big",
        "price": "9 900 ₽",
        "description": "Увеличенная модель для продвинутых — стабильнее и удобнее для силовых упражнений.",
        "image": "images/balans_trick_trening.jpg",
    },
    "poncho": {
        "title": "Пончо — Комбез (переодевалка)",
        "price": "4 500 ₽",
        "description": "Удобное сменное пончо — быстро надеть/снять на пляже, сохраняет тепло.",
        "image": "images/01.jpg",
    },
    "wakesurfpolia": {
        "title": "WakeSurfPolia",
        "price": "5 000 ₽",
        "description": "Настольная игра про вейк, волны и тактику. Состав: карты, правила, счёт. Подходит для компании и вечеринок.",
        "image": "images/hero-wakesurf.png",
    },
    "wave-cards": {
        "title": "Настольная игра «Wave Cards»",
        "price": "уточняется",
        "description": "В разработке: карточная игра про волны и вейк. Пока только в dev/staging.",
        "image": "images/hero-wakesurf.png",
        "dev_only": True,
    },
    "balance-board-pro": {
        "title": "Баланс-борд Pro",
        "price": "12 500 ₽",
        "description": "Профессиональная доска с улучшенной устойчивостью и долговечностью.",
        "image": "images/02.jpg",
    },
    "balance-board-newstyle": {
        "title": "Баланс-борд NewStyle",
        "price": "8 900 ₽",
        "description": "Стильная модель для тренировок и трюков. Подходит для дома и зала.",
        "image": "images/balans_trick_trening1.jpg",
    },
    "certificate-10": {
        "title": "Сертификат на 10 занятий",
        "price": "30 000 ₽",
        "description": "Идеальный подарок для поклонника вейкбординга или вейксерфинга — путь к уверенному уровню «аматор». Каждое занятие строится на предыдущем опыте: прогресс фиксируется и закрепляется.",
        "image": "images/hero-wakesurf.png",
    },
}

# Порядок slug'ов для витрины на главной (6 обязательных карточек)
PRODUCTS_PREVIEW_SLUGS = [
    "balance-board",  # Баланс-борд MyWave
    "balance-board-big",  # Баланс-борд Big
    "balance-board-newstyle",
    "certificate-10",
    "poncho",  # Пончо — Комбез
    "wakesurfpolia",  # Настольная игра
]


def get_products_preview(limit=6, show_dev=None):
    """Список товаров для блока «Товары» на главной. На production товары с dev_only не включаются."""
    if show_dev is None:
        try:
            show_dev = current_app.config.get("SHOW_DEV_PRODUCTS", False)
        except RuntimeError:
            show_dev = False
    out = []
    for slug in PRODUCTS_PREVIEW_SLUGS[:limit]:
        p = PRODUCTS.get(slug)
        if not p:
            continue
        if p.get("dev_only") and not show_dev:
            continue
        out.append({"slug": slug, **p})
    return out


@shop_bp.route("/", methods=["GET"])
def shop_index():
    # Render main shop page (template already exists)
    return render_template("shop.html")


@shop_bp.route("/product/<slug>")
def product(slug):
    product = PRODUCTS.get(slug)
    if not product:
        abort(404)
    if product.get("dev_only") and not current_app.config.get("SHOW_DEV_PRODUCTS", False):
        abort(404)
    return render_template("shop_product.html", product=product, slug=slug)
