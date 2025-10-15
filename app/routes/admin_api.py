from flask import Blueprint, jsonify

admin_api_bp = Blueprint('admin_api', __name__)


@admin_api_bp.route('/admin/api/analytics', methods=['GET'])
def analytics():
    # Minimal endpoint used by tests; in prod this would require admin auth
    return jsonify(metrics=[]), 200
