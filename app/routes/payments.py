from flask import Blueprint, request, jsonify, current_app
from app.database.models import Payment
from app import db
import uuid
from app.payments.providers import get_provider

payments_bp = Blueprint('payments', __name__, url_prefix='/api/payments')

@payments_bp.route('/create', methods=['POST'])
def create_payment():
    data = request.get_json() or {}
    amount = data.get('amount')
    provider = data.get('provider', 'sandbox')
    idempotency = data.get('idempotency_key') or str(uuid.uuid4())

    if not amount:
        return jsonify(error='amount required'), 400

    # check idempotency
    existing = Payment.query.filter_by(idempotency_key=idempotency).first()
    if existing:
        return jsonify(payment_id=existing.id, status=existing.status, idempotent=True)

    payment = Payment(
        provider=provider,
        amount_rub=int(amount),
        idempotency_key=idempotency,
        status='created',
        meta=data.get('metadata')
    )
    db.session.add(payment)
    db.session.commit()

    # In real providers we'd call their API and return redirect/payment token
    return jsonify(payment_id=payment.id, status=payment.status, idempotency_key=idempotency)


@payments_bp.route('/callback', methods=['POST'])
def payment_callback():
    # Raw body is needed to verify HMAC signatures
    raw = request.get_data() or b''
    incoming = request.get_json(silent=True) or {}
    provider_name = incoming.get('provider') or request.headers.get('X-Provider') or 'sandbox'

    provider_cls = get_provider(provider_name)
    if not provider_cls.verify_signature(dict(request.headers), raw):
        return jsonify(error='invalid signature'), 403

    provider_payment_id = incoming.get('provider_payment_id')
    status = incoming.get('status')
    idempotency = incoming.get('idempotency_key')

    # Try to find by provider_payment_id or idempotency_key
    payment = None
    if provider_payment_id:
        payment = Payment.query.filter_by(provider_payment_id=provider_payment_id).first()
    if not payment and idempotency:
        payment = Payment.query.filter_by(idempotency_key=idempotency).first()

    if not payment:
        return jsonify(error='payment not found'), 404

    # Update status idempotently
    payment.status = status or payment.status
    payment.provider_payment_id = provider_payment_id or payment.provider_payment_id
    db.session.add(payment)
    db.session.commit()

    return jsonify(payment_id=payment.id, status=payment.status)
