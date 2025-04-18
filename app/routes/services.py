# app/routes/services.py

from flask import Blueprint, jsonify, request, current_app
from flask.templating import render_template
from scripts.gpt_integration import ask_gpt
from app.routes.calendar_routes import get_slots_for_date
import datetime
import logging
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from app.services.google import GoogleService


bp = Blueprint('services', __name__, url_prefix='/services')
logger = logging.getLogger(__name__)

# 🔧 Healthcheck
@bp.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok", "time": datetime.datetime.now().isoformat()})

# 🧠 Вопрос к GPT (OpenAI Assistant API)
@bp.route("/ask", methods=["POST"])
def show_services():
    data = request.get_json()
    prompt = data.get("prompt", "")
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400
    response = ask_gpt(prompt)
    return jsonify({"response": response})

# 📅 Слоты расписания (Google Sheets + Calendar)
@bp.route("/slots", methods=["GET"])
def slots():
    date = request.args.get("date")
    if not date:
        return jsonify({"error": "Date is required (YYYY-MM-DD)"}), 400
    slots = get_slots_for_date(date)
    return jsonify(slots)

# 📩 Вебхук Telegram
@bp.route("/telegram", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    logger.info(f"📩 Сообщение от Telegram: {data}")
    # Здесь можно вставить вызов OpenAI и ответ пользователю
    return jsonify({"status": "received"})

# 📊 Статус ассистента и окружения
@bp.route("/status", methods=["GET"])
def status():
    return jsonify({
        "assistant_id": current_app.config.get("ASSISTANT_ID"),
        "openai_model": current_app.config.get("GPTS_MODEL"),
        "calendar": current_app.config.get("GOOGLE_CALENDAR_ID"),
        "spreadsheet": current_app.config.get("SPREADSHEET_ID"),
        "debug": current_app.debug,
    })

# 📤 Загрузка файла в Google Drive
@bp.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "Файл не предоставлен"}), 400
    file = request.files["file"]
    filename = file.filename
    content = file.read()

    try:
        gs = GoogleService()
        result = gs.upload_file_to_drive(content, filename)
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/services")
def ask():
    return render_template("services.html")

