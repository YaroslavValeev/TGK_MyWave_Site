"""
Payment API endpoints for Safari bookings.

Provides REST API for payment creation, status checking, and webhook handling.
Currently using YooKassa payment processor (placeholder implementation).
"""
from flask import request, jsonify, current_app, Blueprint
from flask_restx import Api, Resource, fields, Namespace
import logging
from datetime import datetime

from app.extensions import limiter
from app.config.rate_limit_config import RateLimitConfig
from app.services.rate_limit import limit_by_config

from app.services.payment_service import (
    YooKassaPaymentProcessor, 
    handle_payment_webhook,
    verify_webhook_signature
)

logger = logging.getLogger(__name__)

# Create blueprint
payments_bp = Blueprint('payments', __name__, url_prefix='/api/payments')

# Initialize Flask-RESTX API
api = Api(payments_bp, version='1.0', title='Payment API',
          description='Payment processing for Safari bookings')

# Create namespace
ns = api.namespace('', description='Payment operations')

# Define models
payment_model = api.model('Payment', {
    'status': fields.String(required=True, description='Operation status'),
    'payment_id': fields.String(description='Unique payment ID'),
    'amount': fields.Float(description='Payment amount in rubles'),
    'description': fields.String(description='Payment description'),
    'confirmation_url': fields.String(description='URL for payment confirmation'),
    'created_at': fields.String(description='Creation timestamp'),
    'metadata': fields.Raw(description='Additional payment metadata')
})

payment_status_model = api.model('PaymentStatus', {
    'payment_id': fields.String(required=True),
    'status': fields.String(required=True, description='pending|succeeded|canceled|failed'),
    'amount': fields.Float(),
    'updated_at': fields.String()
})

refund_model = api.model('Refund', {
    'status': fields.String(required=True),
    'refund_id': fields.String(),
    'payment_id': fields.String(),
    'amount': fields.Float(),
    'created_at': fields.String()
})


@ns.route('/create')
class PaymentCreate(Resource):
    """Create a new payment."""
    
    @api.doc('create_payment')
    @api.expect(api.model('PaymentRequest', {
        'amount': fields.Float(required=True, description='Amount in rubles'),
        'description': fields.String(required=True, description='Payment description'),
        'return_url': fields.String(required=True, description='Redirect URL after payment'),
        'booking_id': fields.String(description='Associated booking ID'),
        'user_email': fields.String(description='Customer email'),
        'user_id': fields.Integer(description='Customer user ID')
    }))
    @api.marshal_with(payment_model)
    @limit_by_config(limiter, RateLimitConfig.PAYMENT, methods=["POST"])
    def post(self):
        """Create a payment order in YooKassa."""
        try:
            data = request.get_json()
            
            # Validate required fields
            if not all(k in data for k in ['amount', 'description', 'return_url']):
                api.abort(400, 'Missing required fields: amount, description, return_url')
            
            # Create payment using processor
            processor = YooKassaPaymentProcessor()
            payment = processor.create_payment(
                amount=data['amount'],
                description=data['description'],
                return_url=data['return_url'],
                booking_id=data.get('booking_id'),
                user_email=data.get('user_email'),
                user_id=data.get('user_id')
            )
            
            logger.info(f"Payment created: {payment['payment_id']}")
            return payment, 201
            
        except Exception as e:
            logger.error(f"Payment creation failed: {str(e)}")
            api.abort(500, f"Payment creation failed: {str(e)}")


@ns.route('/status/<string:payment_id>')
class PaymentStatus(Resource):
    """Check payment status."""
    
    @api.doc('get_payment_status')
    @api.marshal_with(payment_status_model)
    def get(self, payment_id):
        """Get payment status from YooKassa."""
        try:
            processor = YooKassaPaymentProcessor()
            status = processor.get_payment_status(payment_id)
            
            logger.info(f"Payment status checked: {payment_id} -> {status['status']}")
            return status, 200
            
        except Exception as e:
            logger.error(f"Status check failed: {str(e)}")
            api.abort(500, f"Status check failed: {str(e)}")


@ns.route('/refund')
class PaymentRefund(Resource):
    """Refund a payment."""
    
    @api.doc('refund_payment')
    @api.expect(api.model('RefundRequest', {
        'payment_id': fields.String(required=True, description='Payment ID to refund'),
        'amount': fields.Float(description='Optional partial refund amount')
    }))
    @api.marshal_with(refund_model)
    @limit_by_config(limiter, RateLimitConfig.PAYMENT, methods=["POST"])
    def post(self):
        """Refund a payment in YooKassa."""
        try:
            data = request.get_json()
            
            if 'payment_id' not in data:
                api.abort(400, 'Missing required field: payment_id')
            
            processor = YooKassaPaymentProcessor()
            refund = processor.refund_payment(
                payment_id=data['payment_id'],
                amount=data.get('amount')
            )
            
            logger.info(f"Refund created: {refund['refund_id']} for payment {data['payment_id']}")
            return refund, 201
            
        except Exception as e:
            logger.error(f"Refund failed: {str(e)}")
            api.abort(500, f"Refund failed: {str(e)}")


@payments_bp.route('/webhook', methods=['POST'])
def handle_webhook():
    """Handle incoming YooKassa webhooks.
    
    YooKassa sends POST requests to this endpoint when:
    - Payment is completed
    - Payment is refunded
    - Payment fails
    """
    try:
        payload = request.get_json()
        signature = request.headers.get('X-Yookassa-Server-Request-Id', '')
        
        # Verify signature (placeholder implementation)
        if not verify_webhook_signature(payload, signature):
            logger.warning("Webhook signature verification failed")
            return jsonify({'status': 'signature_invalid'}), 401
        
        # Process webhook
        result = handle_payment_webhook(payload)
        
        logger.info(f"Webhook processed: {result}")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Webhook handling failed: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


def init_payments_api(app):
    """Initialize payments API with Flask app.
    
    Usage in main app setup:
        from app.routes.payments_api import init_payments_api
        init_payments_api(app)
    """
    app.register_blueprint(payments_bp)
    logger.info("Payments API initialized")
