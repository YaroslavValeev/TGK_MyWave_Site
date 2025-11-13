from flask import Blueprint, request, jsonify, current_app
from app.ai.core_gateway import create_default_gateway
from app.ai.security import get_limiter

concierge_bp = Blueprint('concierge', __name__)


@concierge_bp.route('/message', methods=['POST'])
def concierge_message():
    """Concierge chat endpoint with basic validation and optional rate limiting.

    Expects JSON: {"message": "...", "user_id": "optional"}
    Returns structured JSON produced by the CoreAIGateway.
    """
    data = request.get_json(silent=True) or {}
    msg = data.get('message')
    user_id = data.get('user_id')

    # Basic validation
    if not msg or not isinstance(msg, str):
        return jsonify({'error': 'message required'}), 400
    if len(msg) > 4000:
        return jsonify({'error': 'message too long', 'max': 4000}), 400

    # Optional rate limiting (controlled via app config)
    try:
        enable_rl = current_app.config.get('AI_GATEWAY_ENABLE_RATE_LIMIT', False)
        if enable_rl:
            limiter = get_limiter()
            bucket = user_id or request.remote_addr or 'anon'
            allowed = limiter.allow(bucket)
            if not allowed:
                return jsonify({'error': 'rate_limit_exceeded'}), 429
    except Exception:
        # Fail open on limiter errors but log for diagnostics
        current_app.logger.exception('Rate limiter check failed; allowing request')

    try:
        gw = create_default_gateway()
        resp = gw.handle_message(msg, user_id=user_id)
        return jsonify(resp)
    except Exception as e:
        current_app.logger.exception('Concierge endpoint error')
        return jsonify({'error': str(e)}), 500
