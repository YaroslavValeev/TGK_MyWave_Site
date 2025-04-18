from flask import Blueprint, jsonify, request, current_app, render_template
from app.extensions import csrf  
from app.forms.booking_form import BookingForm
from app.routes.calendar_routes import get_available_slots
from app.modules.booking_utils import is_slot_available, book_slot
import datetime
import logging

booking_bp = Blueprint("booking", __name__, url_prefix="/booking")


# ------------------------------------------------------------
# 1. Страница «/booking/book» — вариант с WTForms (не SPA)
# ------------------------------------------------------------
@booking_bp.route("/book", methods=["GET", "POST"])
def book():
    form = BookingForm()

    if form.validate_on_submit():
        date = form.date.data
        time = form.time.data
        name = form.name.data
        phone = form.phone.data

        ok, msg = is_slot_available(date, time)
        if not ok:
            return jsonify({"message": msg}), 400

        success, calendar_link = book_slot(date, time, name, phone)
        if success:
            return jsonify(
                {"message": "Запись успешно создана!", "calendarLink": calendar_link}
            ), 200
        return jsonify({"message": "Ошибка записи!"}), 500

    return render_template("book.html", form=form)


# ------------------------------------------------------------
# 2. JSON‑API «/booking/book/api»  — используется booking.js
# ------------------------------------------------------------
@booking_bp.route("/book/api", methods=["POST"])
@csrf.exempt
def book_api():
    """
    Ожидает JSON:
        {
          "date":  "YYYY‑MM‑DD",
          "time":  "HH:MM",
          "name":  "Имя",
          "phone": "+79991234567"
        }
    Возвращает всегда JSON, даже при ошибках.
    """
    try:
        # --------------- базовая валидация запроса ---------------
        if not request.is_json:
            return (
                jsonify(
                    {"success": False, "error": "Content‑Type must be application/json"}
                ),
                400,
            )

        data = request.get_json(silent=True) or {}
        current_app.logger.info(f"📩 Получены данные бронирования: {data}")

        required = {"date", "time", "name", "phone"}
        if not required.issubset(data):
            return (
                jsonify({"success": False, "error": "Все поля обязательны"}),
                400,
            )

        booking_date: str = data["date"]
        booking_time: str = data["time"]

        # --------------- проверка форматов даты/времени ---------------
        try:
            datetime.datetime.strptime(booking_date, "%Y-%m-%d")
            datetime.datetime.strptime(booking_time, "%H:%M")
        except ValueError:
            return (
                jsonify({"success": False, "error": "Неверный формат даты или времени"}),
                400,
            )

        # --------------- получаем список доступных слотов ---------------
        slots_by_day = get_available_slots(booking_date)  # {'thursday': [ {...}, ... ]}
        if not slots_by_day:
            return (
                jsonify({"success": False, "error": "В этот день нет тренировок"}),
                400,
            )

        # get_available_slots всегда отдаёт dict, но запасёмся fallback‑ом
        if isinstance(slots_by_day, dict):
            slots_list = next(iter(slots_by_day.values()), [])
        else:  # если функция когда‑то вернёт сразу list
            slots_list = slots_by_day

        if not any(slot.get("time") == booking_time for slot in slots_list):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Нет свободных мест на выбранное время",
                    }
                ),
                400,
            )

        # --------------- финальная проверка / запись ---------------
        ok, msg = is_slot_available(booking_date, booking_time)
        if not ok:
            return jsonify({"success": False, "error": msg}), 400

        success, calendar_link = book_slot(
            booking_date,
            booking_time,
            data["name"].strip(),
            data["phone"].strip(),
        )
        if not success:
            current_app.logger.error(f"❌ Ошибка бронирования: {calendar_link}")
            return jsonify({"success": False, "error": calendar_link}), 500

        current_app.logger.info("✅ Запись успешно создана и добавлена в календарь")
        return (
            jsonify(
                {
                    "success": True,
                    "message": "Тренировка успешно забронирована!",
                    "calendarLink": calendar_link,
                }
            ),
            200,
        )

    # --------------- «catch‑all» — чтобы фронт всегда получал JSON ---------------
    except Exception as e:  # pragma: no cover
        logging.exception("❌ Нераспознанная ошибка в book_api")
        return jsonify({"success": False, "error": str(e)}), 500
