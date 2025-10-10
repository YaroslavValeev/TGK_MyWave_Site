from flask import Blueprint, jsonify, request, current_app, render_template
from flask.templating import render_template
from app.services.openai_service import ask
from app.services.google import get_google_services
from app.modules.sheets import get_available_slots
import datetime
import logging
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from app.services.google import GoogleService
from app.modules.logger import get_logger

services_bp = Blueprint('services', __name__, url_prefix='/services')
logger = get_logger(__name__)

# 🔧 Healthcheck
@services_bp.route("/ping", methods=["GET"])
def ping():
    try:
        return jsonify({"status": "ok", "time": datetime.datetime.now().isoformat()})
    except Exception as e:
        logger.error(f"Ошибка в ping: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}, 500

# 🧠 Вопрос к GPT (OpenAI Assistant API)
@services_bp.route("/ask", methods=["POST"])
def show_services():
    try:
        data = request.get_json()
        prompt = data.get("prompt", "")
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400
        response = ask(prompt)
        return jsonify({"response": response})
    except Exception as e:
        logger.error(f"Ошибка в show_services: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}, 500

# 📅 Слоты расписания (Google Sheets + Calendar)
@services_bp.route("/slots", methods=["GET"])
def slots():
    try:
        date = request.args.get("date")
        if not date:
            return jsonify({"error": "Date is required (YYYY-MM-DD)"}), 400
        calendar_service, _ = get_google_services()
        slots = get_available_slots(calendar_service, date)
        return jsonify(slots)
    except Exception as e:
        logger.error(f"Ошибка в slots: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}, 500

# 📩 Вебхук Telegram
@services_bp.route("/telegram", methods=["POST"])
def telegram_webhook():
    try:
        data = request.get_json()
        logger.info(f"📩 Сообщение от Telegram: {data}")
        # Здесь можно вставить вызов OpenAI и ответ пользователю
        return jsonify({"status": "received"})
    except Exception as e:
        logger.error(f"Ошибка в telegram_webhook: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}, 500

# 📊 Статус ассистента и окружения
@services_bp.route("/status", methods=["GET"])
def status():
    try:
        return {"status": "ok", "time": datetime.datetime.utcnow().isoformat()}, 200
    except Exception as e:
        logger.error(f"Ошибка в status: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}, 500

# 📤 Загрузка файла в Google Drive
@services_bp.route("/upload", methods=["POST"])
def upload():
    try:
        if "file" not in request.files:
            return jsonify({"error": "Файл не предоставлен"}), 400
        file = request.files["file"]
        filename = file.filename
        content = file.read()
        gs = GoogleService()
        result = gs.upload_file_to_drive(content, filename)
        return jsonify({"success": True, **result})
    except Exception as e:
        logger.error(f"Ошибка в upload: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}, 500

@services_bp.route("/services")
def ask():
    try:
        return render_template("services.html")
    except Exception as e:
        logger.error(f"Ошибка в ask: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}, 500

# Новый Telegram webhook endpoint
@services_bp.route('/api/telegram/webhook', methods=['POST'])
def api_telegram_webhook():
    try:
        update = request.get_json()
        # bot.process_new_updates([update])  # Здесь должен быть реальный вызов Telegram-бота
        logger.info("Получен Telegram-Webhook: обновление обработано")
        return '', 200
    except Exception as e:
        logger.error(f"Ошибка в api_telegram_webhook: {e}", exc_info=True)
        return '', 500

