"""API endpoints for Safari CMS sync and queries."""
from flask import Blueprint, jsonify, request, current_app
from app.services.safari_cms_service import SafariCMSService

safari_cms_bp = Blueprint('safari_cms', __name__, url_prefix='/api/safari')


@safari_cms_bp.route('/routes', methods=['GET'])
def get_routes():
    try:
        data = SafariCMSService.get_routes()
        return jsonify({'ok': True, 'routes': data})
    except Exception as e:
        current_app.logger.exception('Failed to fetch safari routes')
        return jsonify({'ok': False, 'error': str(e)}), 500


@safari_cms_bp.route('/faq', methods=['GET'])
def get_faq():
    category = request.args.get('category')
    try:
        data = SafariCMSService.get_faq(category)
        return jsonify({'ok': True, 'faq': data})
    except Exception as e:
        current_app.logger.exception('Failed to fetch safari faq')
        return jsonify({'ok': False, 'error': str(e)}), 500


# Admin endpoint: trigger sync (POST)
@safari_cms_bp.route('/sync', methods=['POST'])
def trigger_sync():
    # Protect the sync endpoint with a simple API key.
    key = request.headers.get('X-SAFARI-SYNC-KEY') or request.args.get('key')
    configured = current_app.config.get('SAFARI_SYNC_KEY')
    if not configured or not key or key != configured:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401

    try:
        result = SafariCMSService.sync_all()
        return jsonify({'ok': True, 'result': result})
    except Exception as e:
        current_app.logger.exception('Failed to sync safari content')
        return jsonify({'ok': False, 'error': str(e)}), 500
