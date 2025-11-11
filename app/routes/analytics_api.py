from flask import Blueprint, request, jsonify
from app.services.google_sheets_service import log_analytics_event

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/analytics/log', methods=['POST'])
def analytics_log():
    """
    Логирует события аналитики (reco_show, reco_click) в Google Sheets.
    
    Expected JSON payload:
    {
      "event": "reco_show" | "reco_click",
      "context": "index" | "post" | "projects" | "book_success" | ...,
      "label": "link text or item name",
      "timestamp": ISO 8601 datetime,
      "user_key": optional string (falls back to remote_addr)
    }
    """
    try:
        data = request.get_json(force=True) or {}
        event = data.get("event")
        context = data.get("context", "unknown")
        label = data.get("label", "")
        timestamp = data.get("timestamp")
        user_key = data.get("user_key") or request.remote_addr
        
        if not event or not timestamp:
            return jsonify({"error": "event and timestamp required"}), 400
        
        payload = {
            "ts": timestamp,
            "event": event,
            "context": context,
            "rule_id": label,
            "user_key": user_key
        }
        
        # Fire-and-forget: даже если Sheets упадёт, возвращаем 200
        try:
            log_analytics_event(payload)
        except Exception as e:
            print(f"[analytics_log] Sheets write failed: {e}")
        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
