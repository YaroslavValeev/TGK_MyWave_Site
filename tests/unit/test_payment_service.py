"""
Unit tests for payment service and API.

Tests the placeholder YooKassa payment processor and payment API endpoints.
"""
import pytest
import json
from datetime import datetime
from app.services.payment_service import (
    YooKassaPaymentProcessor,
    handle_payment_webhook,
    verify_webhook_signature
)


class TestYooKassaPaymentProcessor:
    """Test suite for YooKassa payment processor placeholder."""
    
    def test_processor_initialization(self):
        """Test processor initialization with defaults."""
        processor = YooKassaPaymentProcessor()
        assert processor.shop_id == "PLACEHOLDER_SHOP_ID"
        assert processor.api_key == "PLACEHOLDER_API_KEY"
        assert processor.base_url == "https://api.yookassa.ru/v3"
    
    def test_processor_initialization_with_credentials(self):
        """Test processor initialization with custom credentials."""
        processor = YooKassaPaymentProcessor(
            shop_id="test_shop_123",
            api_key="test_key_456"
        )
        assert processor.shop_id == "test_shop_123"
        assert processor.api_key == "test_key_456"
    
    def test_create_payment(self):
        """Test payment creation."""
        processor = YooKassaPaymentProcessor()
        
        payment = processor.create_payment(
            amount=1500.00,
            description="Safari booking #123",
            return_url="https://mywave.local/booking/success",
            booking_id="SAFARI-001",
            user_email="test@example.com"
        )
        
        # Validate response structure
        assert 'status' in payment
        assert 'payment_id' in payment
        assert 'confirmation_url' in payment
        assert 'created_at' in payment
        
        # Validate values
        assert payment['status'] == 'success'
        assert payment['amount'] == 1500.00
        assert payment['description'] == "Safari booking #123"
        assert 'confirmation_url' in payment and 'yookassa' in payment['confirmation_url']
        
        # Validate metadata
        assert payment['metadata']['booking_id'] == "SAFARI-001"
        assert payment['metadata']['user_email'] == "test@example.com"
    
    def test_create_payment_minimal(self):
        """Test payment creation with minimal parameters."""
        processor = YooKassaPaymentProcessor()
        
        payment = processor.create_payment(
            amount=500.00,
            description="Test payment",
            return_url="https://example.com/return"
        )
        
        assert payment['status'] == 'success'
        assert payment['amount'] == 500.00
        assert 'payment_id' in payment
    
    def test_get_payment_status(self):
        """Test getting payment status."""
        processor = YooKassaPaymentProcessor()
        
        status = processor.get_payment_status("payment_123")
        
        # Validate response structure
        assert 'payment_id' in status
        assert 'status' in status
        assert 'updated_at' in status
        
        # Placeholder always returns 'pending'
        assert status['status'] == 'pending'
        assert status['payment_id'] == "payment_123"
    
    def test_refund_payment(self):
        """Test payment refund."""
        processor = YooKassaPaymentProcessor()
        
        refund = processor.refund_payment("payment_456", amount=500.00)
        
        # Validate response structure
        assert 'status' in refund
        assert 'refund_id' in refund
        assert 'payment_id' in refund
        
        # Validate values
        assert refund['status'] == 'success'
        assert refund['payment_id'] == "payment_456"
        assert refund['amount'] == 500.00
    
    def test_refund_payment_full(self):
        """Test full refund without specifying amount."""
        processor = YooKassaPaymentProcessor()
        
        refund = processor.refund_payment("payment_789")
        
        assert refund['status'] == 'success'
        assert refund['refund_id'] is not None
        assert refund['amount'] is None  # Full refund


class TestPaymentWebhooks:
    """Test suite for payment webhook handling."""
    
    def test_verify_webhook_signature(self):
        """Test webhook signature verification (placeholder always returns True)."""
        payload = {
            'event': 'payment.succeeded',
            'object': {'id': 'payment_123'}
        }
        signature = "test_signature"
        
        # Placeholder always returns True for testing
        result = verify_webhook_signature(payload, signature)
        assert result is True
    
    def test_handle_payment_webhook_success(self):
        """Test handling successful payment webhook."""
        payload = {
            'event': 'payment.succeeded',
            'object': {
                'id': 'payment_123',
                'status': 'succeeded',
                'amount': 1500.00
            }
        }
        
        result = handle_payment_webhook(payload)
        
        assert 'status' in result
        assert 'payment_id' in result
        assert 'event' in result
        assert result['payment_id'] == "payment_123"
        assert result['event'] == 'payment.succeeded'
    
    def test_handle_payment_webhook_refund(self):
        """Test handling refund webhook."""
        payload = {
            'event': 'payment.refunded',
            'object': {
                'id': 'payment_456',
                'refund_id': 'refund_789'
            }
        }
        
        result = handle_payment_webhook(payload)
        
        assert result['event'] == 'payment.refunded'
        assert result['payment_id'] == "payment_456"
    
    def test_handle_payment_webhook_unknown(self):
        """Test handling unknown webhook event."""
        payload = {
            'event': 'unknown.event',
            'object': {'id': 'unknown_123'}
        }
        
        result = handle_payment_webhook(payload)
        
        assert result['status'] == 'acknowledged'
        assert result['event'] == 'unknown.event'


class TestPaymentAPI:
    """Test suite for payment API endpoints."""
    
    def test_create_payment_endpoint(self, app):
        """Test POST /api/payments/create endpoint."""
        with app.test_client() as client:
            response = client.post(
                '/api/payments/create',
                json={
                    'amount': 2000.00,
                    'description': 'Test Safari booking',
                    'return_url': 'https://mywave.local/success',
                    'booking_id': 'TEST-001',
                    'user_email': 'test@example.com'
                }
            )
            
            assert response.status_code == 201
            data = response.get_json()
            assert data['status'] == 'success'
            assert data['amount'] == 2000.00
            assert 'payment_id' in data
            assert 'confirmation_url' in data
    
    def test_create_payment_endpoint_missing_required(self, app):
        """Test POST /api/payments/create with missing required fields."""
        with app.test_client() as client:
            response = client.post(
                '/api/payments/create',
                json={'amount': 1000.00}  # Missing description and return_url
            )
            
            # Flask-RESTX returns 400 for validation errors
            assert response.status_code in [400, 500]
    
    def test_get_payment_status_endpoint(self, app):
        """Test GET /api/payments/status/<payment_id> endpoint."""
        with app.test_client() as client:
            response = client.get('/api/payments/status/payment_test_123')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['payment_id'] == 'payment_test_123'
            assert data['status'] == 'pending'
    
    def test_refund_payment_endpoint(self, app):
        """Test POST /api/payments/refund endpoint."""
        with app.test_client() as client:
            response = client.post(
                '/api/payments/refund',
                json={
                    'payment_id': 'payment_to_refund',
                    'amount': 1000.00
                }
            )
            
            assert response.status_code == 201
            data = response.get_json()
            assert data['status'] == 'success'
            assert data['payment_id'] == 'payment_to_refund'
            assert 'refund_id' in data
    
    def test_refund_payment_endpoint_missing_payment_id(self, app):
        """Test POST /api/payments/refund without payment_id."""
        with app.test_client() as client:
            response = client.post(
                '/api/payments/refund',
                json={'amount': 500.00}
            )
            
            # Flask-RESTX returns 400/500 for validation errors
            assert response.status_code in [400, 500]
    
    def test_webhook_endpoint(self, app):
        """Test POST /api/payments/webhook endpoint."""
        with app.test_client() as client:
            response = client.post(
                '/api/payments/webhook',
                json={
                    'event': 'payment.succeeded',
                    'object': {
                        'id': 'payment_webhook_test',
                        'status': 'succeeded'
                    }
                },
                headers={'X-Yookassa-Server-Request-Id': 'webhook_123'}
            )
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'acknowledged'


@pytest.fixture
def app():
    """Create and configure a test app."""
    from app import create_app
    from app.database.models import db
    
    app = create_app(config_name='testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
