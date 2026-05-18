from flask import Blueprint, jsonify, request, current_app, render_template, url_for
from app.services.openai_service import ask
from app.services.google import get_google_services
from app.services.images_service import get_image_url, save_image
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
def ask_assistant():
    try:
        data = request.get_json()
        prompt = data.get("prompt", "")
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400
        response = ask(prompt)
        return jsonify({"response": response})
    except Exception as e:
        logger.error(f"Ошибка в ask_assistant: {e}", exc_info=True)
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

# P0-1: Маппинг услуг из configs/services.yaml (fallback — встроенный список)
# Алиас для обратной совместимости (legacy import)
def _load_services_config():
    """Загружает конфиг услуг из YAML. При ошибке — встроенный список."""
    try:
        import yaml
        from pathlib import Path
        cfg_path = Path(__file__).resolve().parents[2] / 'configs' / 'services.yaml'
        if cfg_path.exists():
            with cfg_path.open('r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                return data.get('services', [])
    except Exception as e:
        logger.warning("Не удалось загрузить configs/services.yaml: %s", e)
    return [
        {'service_id': 'gym', 'name': 'Запись на тренировку (Зал)', 'description': '...', 'price': '3500 рублей', 'image_folder': 'images/Services/Gym', 'modal_id': 'modalCalendar', 'button_text': 'Подробнее / Записаться'},
        {'service_id': 'boat', 'name': 'Запись на катер', 'description': '...', 'price': '10 000 рублей', 'image_folder': 'images/Services/Boat', 'modal_id': 'modalCalendar', 'button_text': 'Подробнее / Записаться'},
        {'service_id': 'camp', 'name': 'Camp', 'description': '...', 'price': 'от 15 000 рублей', 'image_folder': 'images/Services/Camp', 'modal_id': 'modalCamp', 'button_text': 'Подробнее / Записаться'},
        {'service_id': 'coach_triper', 'name': 'Тренер на выезде', 'description': '...', 'price': 'по запросу', 'image_folder': 'images/Services/CoachTriper', 'modal_id': 'modalCoachTriper', 'button_text': 'Подробнее / Оставить заявку'},
        {'service_id': 'consulting', 'name': 'Консалтинг', 'description': '...', 'price': 'по запросу', 'image_folder': 'images/Services/Consalting', 'modal_id': 'modalConsulting', 'button_text': 'Подробнее / Получить консультацию'},
    ]


# Обратная совместимость: старый код мог импортировать _SERVICES_RAW
_SERVICES_RAW = _load_services_config


@services_bp.route("/")
def services_list():
    """Страница списка всех услуг. P0-1: images[]/cover/fallback из скана папки."""
    try:
        from app.services.service_cards import build_services_list

        services = build_services_list(_load_services_config(), url_for)
        for s in services:
            s['image_url'] = s.get('cover')
        return render_template("services.html", services=services)
    except Exception as e:
        logger.error(f"Ошибка в services_list: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}, 500


# --- Страницы отдельных услуг ---
@services_bp.route('/wake-challenge')
def wake_challenge():
    """Страница Wake Challenge"""
    try:
        return render_template('services/wake_challenge.html')
    except Exception as e:
        logger.error(f"Ошибка в wake_challenge: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}, 500


@services_bp.route('/wakesurf-safari')
def wakesurf_safari():
    """Страница WakeSurf Safari"""
    try:
        return render_template('services/wakesurf_safari.html')
    except Exception as e:
        logger.error(f"Ошибка в wakesurf_safari: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}, 500


@services_bp.route('/wake-camp')
def wake_camp():
    """Страница Wake Camp"""
    try:
        return render_template('services/wake_camp.html')
    except Exception as e:
        logger.error(f"Ошибка в wake_camp: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}, 500

# Эндпоинт бронирования
@services_bp.route('/book', methods=['GET', 'POST'])
def book_service():
    """Endpoint для бронирования услуги"""
    try:
        data = request.get_json()
        
        # Валидация входных данных
        required_fields = ['service_id', 'date', 'time', 'name', 'phone']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Логирование запроса
        logger.info(f"Получен запрос на бронирование: {data}")

        # Получаем user_id из сессии если пользователь авторизован
        from flask_login import current_user
        user_id = current_user.id if not current_user.is_anonymous else None

        # Используем сервис для создания бронирования
        from app.services.booking_service import create_booking
        
        result = create_booking(
            data={
                'name': data['name'],
                'phone': data['phone'],
                'date': data['date'],
                'time': data['time'],
                'service_id': data['service_id']
            },
            user_id=user_id
        )

        if result['success']:
            return jsonify({
                "status": "success",
                "message": "Бронирование успешно создано",
                "booking_id": result['booking_id']
            })
        else:
            error = result.get('error', 'unknown_error')
            if error in ['invalid_date', 'invalid_time', 'date_in_past', 'invalid_phone', 'duplicate_booking']:
                return jsonify({
                    "status": "error",
                    "error": error
                }), 400
            else:
                logger.error(f"Ошибка при бронировании: {error}")
                return jsonify({
                    "status": "error",
                    "error": "Произошла внутренняя ошибка сервера"
                }), 500
            
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса бронирования: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

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

