from flask import Blueprint, render_template, abort, url_for

from app.services.images_resolver import resolve_card_images, FALLBACK as FALLBACK_IMG

shop_bp = Blueprint('shop', __name__, url_prefix='/shop')

# P0-2: Финальный список товаров (6+). Маппинг папок — images/Shop/{folder}
PRODUCTS = {
    'balance-board': {
        'title': 'Баланс-борд',
        'price': '7 500 ₽',
        'description': 'Тренировочный баланс-борд для трюков и фитнеса. Улучшает координацию, подходит для всех уровней.',
        'image_folder': 'images/Shop/Balanceboard',
    },
    'balance-board-big': {
        'title': 'Баланс-борд BIG',
        'price': '9 900 ₽',
        'description': 'Увеличенная модель для продвинутых — стабильнее и удобнее для силовых упражнений.',
        'image_folder': 'images/Shop/Balanceboard_BIG',
    },
    'balance-newstyle-15000': {
        'title': 'Баланс-борд NewStyle',
        'price': '15 000 ₽',
        'description': 'Баланс-борд NewStyle — премиум-модель с улучшенной устойчивостью и дизайном.',
        'image_folder': 'images/Shop/Balanceboard_Style',
    },
    'poncho': {
        'title': 'Пончо — Комбез',
        'price': '4 500 ₽',
        'description': 'Удобное сменное пончо — быстро надеть/снять на пляже, сохраняет тепло.',
        'image_folder': 'images/Shop/poncho',
    },
    'sertificate': {
        'title': 'Сертификат (на занятия)',
        'price': '30 000 ₽',
        'description': 'Подарочный сертификат на 10 занятий: тренировки, катание или услуги MyWave.',
        'image_folder': 'images/Shop/Sertificate',
    },
    'wakesurfpolia': {
        'title': 'WakeSurf Polia',
        'price': '5 000 ₽',
        'description': 'Комплект для тренировок на воде: страховочные элементы и аксессуары.',
        'image_folder': 'images/Shop/WakeSurfPolia',
    },
    'wave-cards': {
        'title': 'Wave Cards',
        'price': '1 200 ₽',
        'description': 'Колода карточек с заданиями/вызовами и тематикой вейка. Короткие игры и челленджи.',
        'image_folder': 'images_old/hero-wakesurf.webp',
    },
}


def _products_with_resolved_images():
    """P0-1: Каждому товару images[], cover, fallback из скана папки."""
    out = {}
    for slug, p in PRODUCTS.items():
        folder = p.get('image_folder', p.get('image', ''))
        resolved = resolve_card_images(folder, fallback=FALLBACK_IMG)
        imgs = resolved.get('images') or [resolved['cover']]
        out[slug] = {
            **{k: v for k, v in p.items() if k != 'image_folder'},
            'image': resolved['cover'],
            'images': imgs,
            'cover': resolved['cover'],
            'fallback': resolved['fallback'],
            'image_urls': [url_for('static', filename=path) for path in imgs],
        }
    return out


@shop_bp.route('/', methods=['GET'])
def shop_index():
    return render_template('shop.html', products=_products_with_resolved_images())


@shop_bp.route('/product/<slug>')
def product(slug):
    products = _products_with_resolved_images()
    prod = products.get(slug)
    if not prod:
        abort(404)
    return render_template('shop_product.html', product=prod, slug=slug)
