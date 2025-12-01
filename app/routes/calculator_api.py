from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
import json
from app.services.google_sheets_analytics import log_analytics_event

calculator_api = Blueprint("calculator_api", __name__)


@calculator_api.route("/api/calculator/save", methods=["POST"])
def calc_save():
    data = request.get_json(silent=True) or {}
    phone = data.get("phone", "")
    city = data.get("city", "")
    tags = data.get("tags", [])  # ожидаем список строк
    inputs = data.get("inputs", {})
    result = data.get("result", {})
    ts = datetime.utcnow().isoformat()

    sheet_id = current_app.config.get("ANALYTICS_SHEET_SPREADSHEET_ID") or current_app.config.get('SPREADSHEET_ID')
    sheet_name = "Calculator_Results"
    try:
        from app.services.google_sheets_service import append_record
        row = [
            ts,
            phone,
            city,
            ", ".join(tags) if isinstance(tags, list) else str(tags),
            json.dumps(inputs, ensure_ascii=False),
            json.dumps(result, ensure_ascii=False)
        ]
        if sheet_id:
            append_record(sheet_id, sheet_name, row)
            current_app.logger.info(f"Calculator result saved to sheet {sheet_name}")
        else:
            current_app.logger.warning("No sheet_id configured for calculator results; skipping write")
    except Exception as e:
        current_app.logger.error(f"Failed to save calculator result to sheet: {e}")
    
    # Логируем событие в аналитику (best-effort)
    try:
        analytics_payload = {
            "event": "calculator_use",
            "context": "site_calculator",
            "user_key": phone or "",
            "type": "calculator",
            "rule_id": "",
            "item_id": "",
            "meta": {
                "city": city,
                "tags": tags if isinstance(tags, list) else [tags],
                "inputs": inputs,
                "result": result,
                "source": "site_web",
            },
            "ip": request.remote_addr or "",
            "user_agent": request.headers.get("User-Agent", "")
        }
        log_analytics_event(analytics_payload)
    except Exception as e:
        current_app.logger.warning(f"Не удалось записать событие аналитики calculator_use: {e}")
    
    return jsonify({"ok": True})


@calculator_api.route("/api/calculator/history", methods=["GET"])
def calc_history():
    phone = request.args.get("phone", "")
    history = []
    try:
        from app.services.google_sheets_service import read_records
        sheet_id = current_app.config.get("ANALYTICS_SHEET_SPREADSHEET_ID") or current_app.config.get('SPREADSHEET_ID')
        sheet_name = "Calculator_Results"
        if sheet_id:
            records = read_records(sheet_id, sheet_name)
            # records is list of dicts with headers as keys; try to filter by phone column if exists
            for r in records:
                # permissive matching: any value in row equals phone
                if phone:
                    if any((str(v) == phone) for v in r.values()):
                        history.append(r)
                else:
                    history.append(r)
        else:
            current_app.logger.warning("No sheet_id configured for calculator history; returning empty history")
    except Exception as e:
        current_app.logger.error(f"Failed to read calculator history from sheet: {e}")
    return jsonify({"ok": True, "history": history})
