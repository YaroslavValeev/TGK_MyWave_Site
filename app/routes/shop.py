from flask import Blueprint, render_template, abort, url_for, request, jsonify, current_app

from app.extensions import csrf, limiter
from app.modules.logger import get_logger
from app.services.application_notifications import notify_new_application
from app.services.images_resolver import resolve_card_images, FALLBACK as FALLBACK_IMG
from app.services.product_leads import save_product_lead, validate_product_lead

shop_bp = Blueprint('shop', __name__, url_prefix='/shop')
logger = get_logger(__name__)

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
        'description': 'Подарочный сертификат на 10 занятий MyWave: тренировки в зале, катер или услуги клуба.',
        'image_folder': 'images/Shop/Sertificate',
    },
    'wakesurfpolia': {
        'title': 'WakeSurf Polia',
        'price': '5 000 ₽',
        'description': 'Настольная игра про вейксерфинг: карточки, сценарии и правила для компании. Для дома, лагеря и вечеринок.',
        'image_folder': 'images/Shop/WakeSurfPolia',
        'buy_url': 'https://joys-brand.com/aksessuary/nastolnaya-igra-wakesurfopolie1',
    },
    'wave-cards': {
        'title': 'Wave Cards',
        'price': '1 200 ₽',
        'description': 'Колода карточек с заданиями и челленджами в тематике вейка — короткие игры на воде и на берегу.',
        'image_folder': 'images/Place1Logo.png',
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


def _product_request_rate_limit():
    if limiter is None:
        return lambda f: f
    from flask_limiter.util import get_remote_address
    return limiter.limit("10 per minute", key_func=get_remote_address)


@shop_bp.route('/api/product-request', methods=['POST'])
@csrf.exempt
@_product_request_rate_limit()
def product_request_api():
    """MVP product lead — заявка менеджеру, без онлайн-оплаты."""
    data = request.get_json(silent=True) or {}
    slug = str(data.get('product_id') or '').strip()
    products = _products_with_resolved_images()
    if slug and slug not in products:
        return jsonify(ok=False, error='unknown_product'), 400

    payload = {
        'name': data.get('name'),
        'phone': data.get('phone'),
        'telegram': data.get('telegram'),
        'email': data.get('email'),
        'product_id': slug or data.get('product_id'),
        'product_title': data.get('product_title') or (products.get(slug) or {}).get('title', ''),
        'quantity': data.get('quantity', 1),
        'comment': data.get('comment'),
        'page_url': data.get('page_url') or request.headers.get('Referer', ''),
        'source': 'product',
    }

    validation_errors = validate_product_lead(payload)
    if validation_errors:
        return jsonify(ok=False, error=",".join(validation_errors)), 400

    try:
        result = save_product_lead(payload)
    except ValueError as exc:
        return jsonify(ok=False, error=str(exc)), 400
    except Exception as exc:
        logger.exception('product_lead_save_failed')
        return jsonify(
            ok=False,
            error='Не удалось отправить заявку. Попробуйте ещё раз или напишите нам в Telegram.',
        ), 500

    notify_payload = {
        **payload,
        'status': result.status,
        'created_at': None,
    }
    notify_new_application('product', notify_payload)

    return jsonify(
        ok=True,
        lead_id=result.lead_id,
        message=(
            'Заявка отправлена. Мы уточним наличие товара и свяжемся с вами '
            'для подтверждения заказа.'
        ),
    )
