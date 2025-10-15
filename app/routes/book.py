from flask import Blueprint, jsonify, request, current_app, render_template, flash, redirect, url_for
from app.extensions import csrf  
from app.forms.booking_form import BookingForm
from app.database.models import db, Booking
from app.modules.sheets import append_row
from app.modules.calendar_integration import create_calendar_event
from app.modules.sheets import get_all_records
from app.services.google import get_google_services
from config import Config
from datetime import datetime, timedelta
import logging
import re
from app.services.sheets_writer import save_client_to_sheets, save_sales_deal_to_sheets
from app.services import crm
from app.services.booking_orchestrator import process_booking

booking_bp = Blueprint("booking", __name__, url_prefix="/booking")
logger = logging.getLogger(__name__)


# ------------------------------------------------------------
# 1. Страница «/booking/book» — вариант с WTForms (не SPA)
# ------------------------------------------------------------
@booking_bp.route("/book", methods=["GET", "POST"])
def book():
    form = BookingForm()
    if request.method == "POST":
        if form.validate_on_submit():
            date = form.date.data
            time = form.time.data
            name = form.name.data
            phone = form.phone.data
            # Валидация телефона
            if not re.match(r'^\+7\d{10}$', phone):
                flash("Неверный номер телефона. Введите в формате +7XXXXXXXXXX", "danger")
                return render_template("book.html", form=form), 400
            try:
                # Проверка на занятость слота (локальная защита)
                exists = Booking.query.filter_by(date=date, time=time, phone=phone).first()
                if exists:
                    flash("Вы уже записаны на это время", "warning")
                    return render_template("book.html", form=form), 409

                # Делегируем создание брони и побочных эффектов в orchestrator
                success, message = process_booking({"name": name, "phone": phone, "date": date, "time": time})
                if success:
                    flash("Запись успешно создана!", "success")
                    return redirect(url_for("booking.book"))
                else:
                    logger.error(f"Ошибка при бронировании: {message}")
                    flash("Ошибка при бронировании. Попробуйте позже.", "danger")
                    return render_template("book.html", form=form), 500
            except Exception as e:
                logger.error(f"Ошибка при бронировании: {e}")
                flash("Ошибка при бронировании. Попробуйте позже.", "danger")
                return render_template("book.html", form=form), 500
        else:
            flash("Проверьте правильность заполнения формы", "danger")
            return render_template("book.html", form=form), 400
    return render_template("book.html", form=form)


# ------------------------------------------------------------
# 2. JSON‑API «/booking/book/api»  — используется booking.js
# ------------------------------------------------------------
@booking_bp.route("/api/book", methods=["POST"])
@csrf.exempt
def api_book():
    data = request.get_json()
    name = data.get("name")
    phone = data.get("phone")
    date = data.get("date")
    time = data.get("time")
    if not all([name, phone, date, time]):
        return jsonify({"success": False, "error": "Не хватает данных"}), 400
    if not re.match(r'^\+7\d{10}$', phone):
        return jsonify({"success": False, "error": "Неверный формат телефона"}), 400
    try:
        success, message = process_booking({"name": name, "phone": phone, "date": date, "time": time})
        if success:
            return jsonify({"success": True, "message": message}), 200
        else:
            return jsonify({"success": False, "error": message}), 409 if 'Нет свободных мест' in message else 400
    except Exception as e:
        logger.error(f"Ошибка API бронирования: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@booking_bp.route("/my-sessions")
def my_sessions():
    phone = request.args.get("phone")
    if not phone:
        return "Не указан телефон", 400
    all_records = get_all_records("Client_Workouts")
    workouts = [r for r in all_records if r.get("phone") == phone]
    return render_template("client_dashboard.html", workouts=workouts)

def slot_plus_1_hour(slot):
    """Добавляет 1 час к времени слота"""
    time = datetime.strptime(slot, "%H:%M")
    return (time + timedelta(hours=1)).strftime("%H:%M")
