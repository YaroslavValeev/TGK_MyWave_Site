import os
import threading
from datetime import datetime, timedelta

from flask import (
    Blueprint,
    request,
    jsonify,
    current_app,
    render_template,
    redirect,
    url_for,
    session,
)
from googleapiclient.errors import HttpError
from marshmallow.exceptions import ValidationError

from app.schemas import BookingSchema
from app.services.google import get_google_services, add_event_to_calendar
from app.services.google_sheets_service import append_record, read_records
import secrets
from datetime import datetime as _dt
from app.modules.calendar_integration import create_workout_if_not_exists
from app.services.site_analytics import log_site_booking_event
from app.services.google_sheets_analytics import log_analytics_event

from app.extensions import limiter
from app.config.rate_limit_config import RateLimitConfig
from app.services.rate_limit import limit_by_config


calendar_bp = Blueprint("calendar", __name__)

MAX_PER_SLOT = 2  # Зал: максимум записей на один слот
BOAT_MAX_PER_SLOT = 1  # Катер: один ученик на сет (30 мин)


def _masked_config_id(key: str) -> str:
    raw = str(current_app.config.get(key) or "").strip()
    if not raw:
        return "unset"
    if len(raw) <= 8:
        return "***"
    return f"{raw[:4]}…{raw[-4:]}"


def _log_slots_context(date_str: str, service_type: str | None) -> None:
    current_app.logger.info(
        "slots_request date=%s service=%s spreadsheet=%s calendar=%s sa_file=%s",
        date_str,
        service_type or "-",
        _masked_config_id("SPREADSHEET_ID"),
        _masked_config_id("GOOGLE_CALENDAR_ID"),
        (
            "present"
            if os.path.isfile(
                str(current_app.config.get("GOOGLE_SERVICE_ACCOUNT_FILE") or "")
            )
            else "missing"
        ),
    )


# RLock для защиты одновременного доступа к Google Sheets API (eventlet issue)
# RLock позволяет одному потоку захватить lock несколько раз (переиспользуемый lock)
_google_sheets_lock = threading.RLock()


def normalize_day_of_week(day):
    """Нормализует название дня недели"""
    # Словарь для маппинга русских названий на английские
    ru_to_en = {
        "понедельник": "monday",
        "вторник": "tuesday",
        "среда": "wednesday",
        "четверг": "thursday",
        "пятница": "friday",
        "суббота": "saturday",
        "воскресенье": "sunday",
        # Сокращения
        "пн": "monday",
        "вт": "tuesday",
        "ср": "wednesday",
        "чт": "thursday",
        "пт": "friday",
        "сб": "saturday",
        "вс": "sunday",
    }

    day = str(day).strip().lower()
    # Если день недели на русском, конвертируем в английский
    return ru_to_en.get(day, day)


def validate_schedule_record(record, idx):
    """Проверяет корректность записи расписания"""
    required_fields = ["day_of_week", "time", "max_capacity"]

    # Проверяем наличие обязательных полей
    missing_fields = [field for field in required_fields if not record.get(field)]
    if missing_fields:
        current_app.logger.error(
            f"В записи {idx + 1} отсутствуют обязательные поля: {', '.join(missing_fields)}"
        )
        return False, None

    try:
        # Проверка времени
        if not isinstance(record["time"], str) or not record["time"].strip():
            current_app.logger.warning(
                f"Некорректное время в записи {idx + 1}: {record['time']}"
            )
            return False, None

        # Проверка вместимости
        max_cap = int(record.get("max_capacity", "0"))
        if max_cap <= 0:
            current_app.logger.warning(
                f"Некорректная вместимость в записи {idx + 1}: {max_cap}"
            )
            return False, None

        # Проверка и нормализация дня недели
        day = normalize_day_of_week(record["day_of_week"])
        if not day:
            current_app.logger.warning(
                f"Некорректный день недели в записи {idx + 1}: {record['day_of_week']}"
            )
            return False, None

        # Возвращаем обновленную запись
        record["day_of_week"] = day
        record["max_capacity"] = max_cap
        return True, record

    except (ValueError, TypeError) as e:
        current_app.logger.error(f"Ошибка валидации записи {idx + 1}: {str(e)}")
        return False, None


def get_available_slots(date_str):
    """
    Возвращает список доступных слотов для указанной даты.
    Фильтрует статическое расписание по дню недели и вычитает уже сделанные брони.

    Использует lock для защиты одновременного доступа к Google Sheets API (eventlet issue).
    """
    # Используем lock для защиты от одновременных запросов к Google Sheets API
    with _google_sheets_lock:
        return _get_available_slots_internal(date_str)


def _get_available_slots_internal(date_str):
    """Внутренняя функция для получения слотов (вызывается с lock)"""
    current_app.logger.info(f"\n{'='*50}\nЗАПРОС СЛОТОВ\n{'='*50}")
    current_app.logger.info(f"Запрошенная дата: {date_str}")

    # 1) Проверяем наличие необходимых конфигураций
    spreadsheet_id = current_app.config.get("SPREADSHEET_ID")
    if not spreadsheet_id:
        current_app.logger.error("SPREADSHEET_ID не настроен в конфигурации")
        raise ValueError("Ошибка конфигурации: ID таблицы не настроен")

    current_app.logger.info(f"Используется SPREADSHEET_ID: {spreadsheet_id}")

    service_account = current_app.config.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    if not service_account:
        current_app.logger.error("GOOGLE_SERVICE_ACCOUNT_FILE не настроен")
        raise ValueError("Ошибка конфигурации: путь к сервисному аккаунту не настроен")

    if not os.path.exists(service_account):
        current_app.logger.error(
            f"Файл сервисного аккаунта не найден по пути: {service_account}"
        )
        raise FileNotFoundError(
            f"Файл сервисного аккаунта не найден: {service_account}"
        )

    current_app.logger.info(f"Используется сервисный аккаунт: {service_account}")

    # Проверяем подключение к Google API
    # Проверяем подключение к Google API
    drive, sheets, calendar = get_google_services()
    current_app.logger.info("✅ Подключение к Google API установлено")

    # Проверяем наличие файла сервисного аккаунта
    if not current_app.config.get("GOOGLE_SERVICE_ACCOUNT_FILE"):
        current_app.logger.error("GOOGLE_SERVICE_ACCOUNT_FILE не настроен")
        raise ValueError("Ошибка конфигурации: путь к сервисному аккаунту не настроен")

    # 2) Преобразуем строку в дату и определяем день недели
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        day_of_week = date_obj.strftime("%A").lower()
    except ValueError as e:
        current_app.logger.error(f"Ошибка парсинга даты {date_str}: {str(e)}")
        raise ValueError(f"Неверный формат даты: {date_str}")

    current_app.logger.info(f"\n{'='*50}")
    current_app.logger.info(f"ДИАГНОСТИКА СЛОТОВ")
    current_app.logger.info(f"{'='*50}")
    current_app.logger.info(f"Запрошенная дата: {date_str}")
    current_app.logger.info(f"День недели (системный): {day_of_week}")

    # 3) Считываем и валидируем записи из листа Schedule
    try:
        current_app.logger.info("Попытка чтения листа Schedule...")

        # Пробуем получить доступ к таблице сначала
        try:
            sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            current_app.logger.info("✅ Доступ к таблице подтвержден")
        except HttpError as e:
            if e.resp.status == 404:
                current_app.logger.error(
                    f"❌ Таблица не найдена (ID: {spreadsheet_id})"
                )
                raise ValueError(
                    f"Таблица не найдена. Проверьте SPREADSHEET_ID: {spreadsheet_id}"
                )
            elif e.resp.status == 403:
                current_app.logger.error("❌ Нет прав доступа к таблице")
                raise ValueError(
                    "Нет прав доступа к таблице. Проверьте настройки доступа для сервисного аккаунта."
                )
            else:
                raise

        schedule = read_records(current_app.config["SPREADSHEET_ID"], "Schedule")
        current_app.logger.info(
            f"Прочитано записей из Schedule: {len(schedule) if schedule else 0}"
        )

        if not schedule:
            current_app.logger.warning(
                "Таблица расписания пуста или не удалось получить данные"
            )
            return []

        # Валидируем каждую запись
        validated_schedule = []
        invalid_records = []
        for idx, record in enumerate(schedule):
            current_app.logger.debug(f"Валидация записи {idx}: {record}")
            is_valid, validated_record = validate_schedule_record(record, idx)
            if is_valid:
                validated_schedule.append(validated_record)
            else:
                invalid_records.append(record)

        if invalid_records:
            current_app.logger.warning(
                f"Найдено {len(invalid_records)} некорректных записей:"
            )
            for rec in invalid_records:
                current_app.logger.warning(f"- {rec}")

        if not validated_schedule:
            current_app.logger.warning(
                "После валидации не осталось корректных записей в расписании"
            )
            return []

        schedule = validated_schedule
        current_app.logger.info(
            f"Успешно обработано {len(schedule)} записей расписания"
        )

    except HttpError as he:
        current_app.logger.error(f"Ошибка API Google Sheets: {str(he)}")
        raise he
    except Exception as e:
        current_app.logger.error(f"Ошибка чтения или валидации расписания: {str(e)}")
        raise

    from app.config.booking_features import is_phase2_availability_enabled

    if is_phase2_availability_enabled():
        from app.services.booking.availability import build_gym_slots_from_calendar

        slot_rows = [
            {"time": rec["time"], "max_capacity": rec["max_capacity"]}
            for rec in schedule
            if normalize_day_of_week(rec["day_of_week"]) == day_of_week
        ]
        current_app.logger.info(
            "[gym] Phase 2 Calendar availability for %s (%s slots)",
            date_str,
            len(slot_rows),
        )
        return build_gym_slots_from_calendar(date_str, slot_rows)

    # 4) Считываем брони
    try:
        bookings = read_records(current_app.config["SPREADSHEET_ID"], "Client_Workouts")
        current_app.logger.info(f"\nБРОНИРОВАНИЯ на {date_str}")
        relevant_bookings = [b for b in bookings if b.get("date") == date_str]
        current_app.logger.info(f"Найдено {len(relevant_bookings)} броней")
    except Exception as e:
        current_app.logger.error(f"Ошибка чтения броней: {str(e)}")
        bookings = []
        relevant_bookings = []

    # 5) Формируем слоты
    slots = []
    for rec in schedule:
        # Проверяем совпадение дня недели
        if normalize_day_of_week(rec["day_of_week"]) != day_of_week:
            continue

        time_str = rec["time"]
        capacity = int(rec["max_capacity"])
        used = sum(1 for b in relevant_bookings if b.get("time") == time_str)
        remaining = max(0, capacity - used)

        slots.append(
            {"time": time_str, "available": remaining > 0, "remaining": remaining}
        )

    # Сортируем слоты по времени и возвращаем
    return sorted(slots, key=lambda x: x["time"])


def _generate_service_token(service_name: str, ttl_minutes: int = 15) -> str:
    """Создаёт одноразовый токен и сохраняет его в сессии с ограничением по времени."""
    try:
        token = secrets.token_urlsafe(24)
        tokens = session.get("service_tokens", {})
        tokens[token] = {
            "service": service_name,
            "created_at": _dt.utcnow().isoformat(),
            "ttl_minutes": int(ttl_minutes),
            "used": False,
        }
        session["service_tokens"] = tokens
        current_app.logger.info(
            f"[service_token] Создан token для service={service_name}, token={token}"
        )
        return token
    except Exception as e:
        current_app.logger.error(f"Не удалось создать service token: {e}")
        return ""


def _validate_and_consume_service_token(
    token: str, expected_service: str | None = None
) -> bool:
    """Проверяет, соответствует ли token ожидаемому сервису, не просрочен и не был использован.
    Если валиден — помечает как использованный (consume) и возвращает True.
    """
    try:
        if not token:
            return False
        tokens = session.get("service_tokens", {})
        entry = tokens.get(token)
        if not entry:
            current_app.logger.warning(f"[service_token] Токен не найден: {token}")
            return False
        if entry.get("used"):
            current_app.logger.warning(
                f"[service_token] Токен уже использован: {token}"
            )
            return False
        # Проверяем время жизни
        created = _dt.fromisoformat(entry.get("created_at"))
        ttl = int(entry.get("ttl_minutes", 15))
        if _dt.utcnow() > (created + timedelta(minutes=ttl)):
            current_app.logger.warning(f"[service_token] Токен просрочен: {token}")
            # удалим просроченный
            tokens.pop(token, None)
            session["service_tokens"] = tokens
            return False
        if expected_service and entry.get("service") != expected_service:
            current_app.logger.warning(
                f"[service_token] Ожидался service={expected_service}, но токен для {entry.get('service')}"
            )
            return False
        # Помечаем как использованный
        entry["used"] = True
        tokens[token] = entry
        session["service_tokens"] = tokens
        current_app.logger.info(
            f"[service_token] Токен валидирован и помечен как использованный: {token}"
        )
        return True
    except Exception as e:
        current_app.logger.error(f"Ошибка валидации service token: {e}")
        return False


# === ВСТАВИТЬ СРАЗУ ПОСЛЕ _get_available_slots_internal ===
def get_boat_slots(date_str: str):
    """
    Генерация 30-минутных слотов для услуги 'boat' (катер)
    с 07:00 до 19:30 включительно, с учётом записей из Client_Workouts.

    Вместимость: BOAT_MAX_PER_SLOT (1 ученик на сет).
    В ответ попадают только свободные слоты (занятые не возвращаются).
    Формат: [{ "time": "06:30", "available": True }, ...]
    """
    from app.config.booking_features import is_phase2_availability_enabled

    if is_phase2_availability_enabled():
        from app.services.booking.availability import build_boat_slots_from_calendar

        current_app.logger.info(
            "[boat] Phase 2 Calendar availability for %s", date_str
        )
        return build_boat_slots_from_calendar(date_str)

    current_app.logger.info(f"[boat] Генерация слотов для катера на дату {date_str}")

    spreadsheet_id = current_app.config.get("SPREADSHEET_ID")
    if not spreadsheet_id:
        current_app.logger.error("[boat] SPREADSHEET_ID не настроен в конфигурации")
        raise ValueError("Ошибка конфигурации: ID таблицы не настроен")

    # Читаем все брони и фильтруем по дате
    try:
        bookings = read_records(spreadsheet_id, "Client_Workouts")
        relevant_bookings = [b for b in bookings if b.get("date") == date_str]
    except Exception as e:
        current_app.logger.error(f"[boat] Ошибка чтения листа Client_Workouts: {e}")
        # Если что-то пошло не так — считаем, что броней нет
        bookings = []
        relevant_bookings = []

    # Если в записях есть колонка 'service_type', учитываем только бронь для 'boat'
    if relevant_bookings and any("service_type" in b for b in relevant_bookings):
        filtered_bookings = [
            b
            for b in relevant_bookings
            if (b.get("service_type") or "").strip().lower() == "boat"
        ]
    else:
        # Фоллбек: если колонки нет или нет записей с service_type, считаем все записи
        filtered_bookings = relevant_bookings

    # Считаем активные брони на каждый тайм-слот
    counts_by_time = {}
    for b in filtered_bookings:
        st = (b.get("status") or "").strip().lower()
        if st and st not in ("booked", "new"):
            continue
        t = (b.get("time") or "").strip()
        if not t:
            continue
        counts_by_time[t] = counts_by_time.get(t, 0) + 1

    # Генерируем слоты 07:00–19:30 (canonical, см. app.config.booking_grid)
    from app.config.booking_grid import BOAT_GRID_END, BOAT_GRID_START
    from datetime import datetime as dt, timedelta as td

    start = dt.combine(dt.today(), BOAT_GRID_START)
    end = dt.combine(dt.today(), BOAT_GRID_END)

    slots = []
    cur = start
    while cur <= end:
        time_str = cur.strftime("%H:%M")
        used = counts_by_time.get(time_str, 0)
        if used >= BOAT_MAX_PER_SLOT:
            cur += td(minutes=30)
            continue
        slots.append(
            {
                "time": time_str,
                "available": True,
            }
        )
        cur += td(minutes=30)

    current_app.logger.info(f"[boat] Свободных слотов на {date_str}: {len(slots)}")

    return slots


@calendar_bp.route("/schedule")
def get_schedule():
    """
    Возвращает статическое расписание тренировок.
    """
    try:
        # Проверяем конфигурацию
        if not current_app.config.get("SPREADSHEET_ID"):
            current_app.logger.error("SPREADSHEET_ID не настроен")
            return jsonify({"error": "Ошибка конфигурации сервера"}), 500

        # Считываем расписание
        schedule = read_records(current_app.config["SPREADSHEET_ID"], "Schedule")
        if not schedule:
            current_app.logger.warning("Таблица расписания пуста")
            return jsonify([]), 200

        # Валидируем каждую запись
        validated_schedule = []
        for idx, record in enumerate(schedule):
            is_valid, validated_record = validate_schedule_record(record, idx)
            if is_valid:
                validated_schedule.append(validated_record)

        return jsonify(validated_schedule), 200

    except HttpError as he:
        error_msg = str(he)
        current_app.logger.error(f"Ошибка Google Sheets API: {error_msg}")
        if "invalid_grant" in error_msg:
            return jsonify({"error": "Ошибка авторизации сервера"}), 503
        return jsonify({"error": "Ошибка внешнего API"}), 502

    except Exception as e:
        current_app.logger.error(f"Непредвиденная ошибка: {str(e)}", exc_info=True)
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500


@calendar_bp.route("/api/calendar/slots/<date_str>")
def get_slots(date_str):
    try:
        # Проверяем формат даты
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return (
                jsonify({"error": "Неверный формат даты. Используйте YYYY-MM-DD"}),
                400,
            )

        # Проверяем, что дата не в прошлом
        if date_obj < datetime.now().date():
            return jsonify({"error": "Нельзя выбрать дату в прошлом"}), 400

        # Читаем тип услуги (boat, gym, и т.п.)
        service_type = request.args.get("service")
        _log_slots_context(date_str, service_type)

        # Camp (Ruza 2026) — фиксированное окно дат. Для него НЕ применяем лимит +90 дней.
        if service_type == "camp":
            ruza_start = datetime.strptime("2026-08-10", "%Y-%m-%d").date()
            ruza_end = datetime.strptime("2026-08-23", "%Y-%m-%d").date()
            if date_obj < ruza_start or date_obj > ruza_end:
                return (
                    jsonify(
                        {"error": "Для Ruza Camp доступны даты только 10–23.08.2026"}
                    ),
                    400,
                )
        else:
            # Проверяем, что дата не слишком далеко в будущем (например, +3 месяца)
            max_future_date = datetime.now().date() + timedelta(days=90)
            if date_obj > max_future_date:
                return (
                    jsonify(
                        {
                            "error": "Дата слишком далеко в будущем. Максимум 3 месяца вперед"
                        }
                    ),
                    400,
                )

        # Для катера используем отдельный генератор с 30-минутными слотами
        if service_type == "boat":
            slots = get_boat_slots(date_str)
        else:
            slots = get_available_slots(date_str)

        if not slots:
            current_app.logger.info(f"На дату {date_str} слоты не найдены")
            resp = jsonify([])
            return resp, 200

        # Если запрошен service, создаём одноразовый маркер в сессии и возвращаем его в заголовке
        resp = jsonify(slots)
        if service_type:
            try:
                token = _generate_service_token(service_type)
                if token:
                    resp.headers["X-Service-Token"] = token
            except Exception as e:
                current_app.logger.warning(
                    f"Не удалось сгенерировать service token: {e}"
                )

        current_app.logger.info(f"Найдено {len(slots)} слотов на {date_str}")
        return resp, 200

    except ValidationError as ve:
        error_msg = str(ve)
        current_app.logger.warning(f"Ошибка валидации: {error_msg}")
        return jsonify({"error": "Ошибка валидации данных", "details": error_msg}), 400

    except FileNotFoundError as fe:
        current_app.logger.critical(
            "slots_config_error date=%s service=%s detail=%s",
            date_str,
            request.args.get("service"),
            str(fe),
        )
        return (
            jsonify(
                {
                    "error": "Сервис бронирования временно недоступен. Обратитесь к администратору.",
                    "code": "google_credentials_missing",
                }
            ),
            503,
        )

    except HttpError as he:
        error_msg = str(he)
        current_app.logger.error(f"Ошибка Google API: {error_msg}")
        if "invalid_grant" in error_msg:
            return (
                jsonify(
                    {
                        "error": "Ошибка авторизации сервера. Пожалуйста, попробуйте позже."
                    }
                ),
                503,
            )
        return (
            jsonify(
                {"error": "Временная ошибка сервера. Пожалуйста, попробуйте позже."}
            ),
            502,
        )

    except ValueError as ve:
        current_app.logger.warning(
            "slots_config_value_error date=%s service=%s detail=%s",
            date_str,
            request.args.get("service"),
            str(ve),
        )
        return jsonify({"error": str(ve), "code": "configuration_error"}), 503

    except Exception as e:
        current_app.logger.error(
            "slots_unexpected_error date=%s service=%s err=%s",
            date_str,
            request.args.get("service"),
            type(e).__name__,
            exc_info=True,
        )
        try:
            if current_app.config.get("DEBUG"):
                import traceback

                return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
        except Exception:
            pass
        return (
            jsonify(
                {
                    "error": "Произошла ошибка при получении данных. Пожалуйста, попробуйте позже."
                }
            ),
            500,
        )


@calendar_bp.route("/api/calendar/slots", methods=["GET"])
def get_slots_range():
    try:
        start_date = request.args.get("start")
        end_date = request.args.get("end")
        if not start_date or not end_date:
            return jsonify({"error": "Не указаны даты"}), 400

        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        records = read_records(current_app.config["SPREADSHEET_ID"], "Schedule")
        events = []
        for rec in records:
            # Если в Schedule добавлены записи с полями date/time/status
            if "date" in rec and "time" in rec:
                event_dt = datetime.strptime(
                    f"{rec['date']} {rec['time']}", "%Y-%m-%d %H:%M"
                )
                if start <= event_dt <= end:
                    events.append(
                        {
                            "title": (
                                "Занято"
                                if rec.get("status") == "booked"
                                else "Свободно"
                            ),
                            "start": event_dt.isoformat(),
                            "end": (event_dt + timedelta(hours=1)).isoformat(),
                            "color": (
                                "#ff0000"
                                if rec.get("status") == "booked"
                                else "#00ff00"
                            ),
                        }
                    )

        return jsonify(events)
    except Exception as e:
        current_app.logger.error(f"Error in get_slots_range: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@calendar_bp.route("/api/calendar/sync", methods=["POST"])
def calendar_sync():
    """
    Stub endpoint for calendar synchronization.
    Tests only require the endpoint to exist and return 200/401/403.
    This handler currently acts as a safe stub that always returns 200.
    """
    try:
        # Future: add auth/permission checks and real sync logic here.
        return jsonify({"message": "Calendar sync endpoint (stub)"}), 200
    except Exception as e:
        current_app.logger.exception("Error in calendar_sync endpoint")
        return jsonify({"error": "Internal server error"}), 500


@calendar_bp.route("/api/book", methods=["POST"])
def deprecated_redirect():
    # Устаревший маршрут — перенаправляем на новый
    return redirect("/api/calendar/book", code=307)


@calendar_bp.route("/calendar")
def calendar_page():
    return render_template("calendar.html")


def find_or_create_client(phone, name):
    """Ищет клиента по телефону, если нет — добавляет и возвращает client_id"""
    spreadsheet_id = current_app.config["SPREADSHEET_ID"]
    clients = read_records(spreadsheet_id, "Clients")
    for client in clients:
        if client.get("phone") == phone:
            return client.get("client_id")
    # Если не найден — создаём
    new_id = f"client_{int(datetime.utcnow().timestamp())}"
    created_at = datetime.utcnow().isoformat()
    client_data = {
        "client_id": new_id,
        "telegram_user_id": "",
        "name": name,
        "phone": phone,
        "email": "",
        "level": "beginner",
        "created_at": created_at,
        "source": "web",
        "status": "new",
        "ref_code": "",
        "last_active": created_at,
    }
    from app.modules.sheets_access import append_dict_to_sheet

    append_dict_to_sheet("Clients", client_data)
    return new_id


def find_workout(date, time):
    """Ищет тренировку по дате и времени, возвращает workout_id и текущий current_capacity"""
    spreadsheet_id = current_app.config["SPREADSHEET_ID"]
    workouts = read_records(spreadsheet_id, "Workouts")
    for idx, workout in enumerate(workouts):
        if workout.get("date") == date and workout.get("time") == time:
            return (
                workout.get("workout_id"),
                idx,
                int(workout.get("current_capacity", "0")),
            )
    return None, None, None


def update_workout_capacity(row_idx, new_capacity):
    """Обновляет current_capacity в листе Workouts по индексу строки (начиная с 0 после заголовка)"""
    spreadsheet_id = current_app.config["SPREADSHEET_ID"]
    # current_capacity — это колонка J (10-я, индекс 9), но может быть сдвиг
    # Найдём заголовки
    workouts = read_records(spreadsheet_id, "Workouts")
    headers = list(workouts[0].keys()) if workouts else []
    if "current_capacity" in headers:
        col_idx = headers.index("current_capacity")
        col_letter = chr(ord("A") + col_idx)
        cell = f"{col_letter}{row_idx+2}"  # +2: 1 — заголовок, 1 — индексация с 1
        from app.services.google_sheets_service import update_record

        update_record(spreadsheet_id, "Workouts", cell, [str(new_capacity)])


@calendar_bp.route("/api/calendar/book", methods=["POST"])
@limit_by_config(limiter, RateLimitConfig.BOOKING_CREATE, methods=["POST"])
def book_slot():
    """
    Бронирование слота тренировки.

    Единая точка для:
    - фронтенда (booking.js),
    - /booking/book (через тонкий прокси),
    - будущих интеграций (боты / AI gateway), которые могут вызывать этот endpoint.
    """
    # Используем lock для защиты от одновременных запросов к Google Sheets API
    with _google_sheets_lock:
        return _book_slot_internal()


def _book_slot_internal():
    """Внутренняя функция бронирования (вызывается с lock)"""
    try:
        current_app.logger.info("🔵 НАЧАЛО БРОНИРОВАНИЯ - _book_slot_internal()")

        # 1. Проверяем формат входных данных
        current_app.logger.info("  1️⃣ Проверяем формат JSON...")
        if not request.is_json:
            current_app.logger.error("    ❌ Не JSON")
            return jsonify({"status": "error", "error": "Ожидается JSON"}), 400
        current_app.logger.info("    ✅ JSON OK")

        # 2. Проверяем CSRF токен
        current_app.logger.info("  2️⃣ Проверяем CSRF токен...")
        from app.services.csrf import check_csrf

        if not check_csrf():
            current_app.logger.warning("    ❌ Неверный CSRF токен")
            return (
                jsonify(
                    {
                        "status": "error",
                        "error": "Ошибка безопасности: неверный CSRF токен",
                    }
                ),
                403,
            )
        current_app.logger.info("    ✅ CSRF OK")

        # 3. Валидация данных через схему
        current_app.logger.info("  3️⃣ Валидирую данные...")
        raw_payload = request.get_json()
        # Сохраняем опциональный тип сервиса (если его прислал фронтенд)
        service_type_from_payload = None
        try:
            service_type_from_payload = raw_payload.get("service_type") or None
        except Exception:
            service_type_from_payload = None

        # Дополнительно: проверим наличие одноразового service token в заголовках
        service_token = None
        try:
            service_token = request.headers.get("X-Service-Token") or (
                request.get_json() and request.get_json().get("service_token")
            )
        except Exception:
            service_token = None

        # Если пришёл service_token — валидация и потребление токена (one-time)
        if service_token:
            token_ok = _validate_and_consume_service_token(
                service_token, expected_service=None
            )
            if not token_ok:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "error": "Неверный или просроченный service token",
                        }
                    ),
                    400,
                )
            # Если токен валиден — узнаем сервис из сессии (entry уже помечен как used, но мы можем прочитать service)
            try:
                tokens_map = session.get("service_tokens", {})
                # token may have been marked used; try to read from tokens_map (it still contains entry)
                svc = tokens_map.get(service_token, {})
                if svc:
                    # override payload service type
                    service_type_from_payload = (
                        svc.get("service") or service_type_from_payload
                    )
            except Exception:
                pass

        data = BookingSchema().load(raw_payload)

        current_app.logger.info(
            f"  ✅ Данные валидированы: "
            f"name={data.get('name')} phone={data.get('phone')} "
            f"date={data.get('date')} time={data.get('time')}"
        )

        # 3.25 Camp policy (Ruza 2026): только окно 10–23.08.2026 и общий лимит мест
        if service_type_from_payload == "camp":
            try:
                ruza_start = datetime.strptime("2026-08-10", "%Y-%m-%d").date()
                ruza_end = datetime.strptime("2026-08-23", "%Y-%m-%d").date()
                req_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
                if req_date < ruza_start or req_date > ruza_end:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "error": "Для Ruza Camp доступны даты только 10–23.08.2026",
                            }
                        ),
                        400,
                    )
            except Exception:
                return (
                    jsonify(
                        {"status": "error", "error": "Некорректная дата для Ruza Camp"}
                    ),
                    400,
                )

        # 3.5. Проверка дубликата: тот же phone на тот же date+time
        spreadsheet_id = current_app.config["SPREADSHEET_ID"]
        clients = read_records(spreadsheet_id, "Clients")
        client_id_for_phone = next(
            (c.get("client_id") for c in clients if c.get("phone") == data["phone"]),
            None,
        )
        if client_id_for_phone:
            bookings = read_records(spreadsheet_id, "Client_Workouts")
            slot_times_check = data.get("slot_times") or [data["time"]]
            duplicate = any(
                b.get("client_id") == client_id_for_phone
                and b.get("date") == data["date"]
                and b.get("time") in slot_times_check
                for b in bookings
            )
            if duplicate:
                current_app.logger.warning(
                    f"    ❌ Дубликат брони: phone={data['phone']} date={data['date']} time={data['time']}"
                )
                # Ruza Camp: повторная отправка той же анкеты — не ошибка для пользователя
                if (service_type_from_payload or "").strip().lower() == "camp":
                    return (
                        jsonify(
                            {
                                "status": "success",
                                "message": "Заявка уже была получена ранее. Мы свяжемся с вами.",
                                "idempotent": True,
                            }
                        ),
                        200,
                    )
                return (
                    jsonify(
                        {
                            "status": "error",
                            "error": "Вы уже записаны на это время. Один слот — одна запись.",
                        }
                    ),
                    400,
                )

        # 4. Проверяем доступность слота / capacity (учитываем опциональный service_type)
        current_app.logger.info(
            f"  4️⃣ Проверяю слот {data['date']} {data['time']}... (service={service_type_from_payload})"
        )
        if service_type_from_payload == "camp":
            # Camp — без почасовых слотов, считаем общую вместимость смены.
            try:
                ruza_cap = 16
                bookings = read_records(spreadsheet_id, "Client_Workouts")
                ruza_start_s = "2026-08-10"
                ruza_end_s = "2026-08-23"
                used = 0
                for b in bookings:
                    svc = (b.get("service_type") or "").strip().lower()
                    if svc != "camp":
                        continue
                    d = (b.get("date") or "").strip()
                    if not d:
                        continue
                    if d < ruza_start_s or d > ruza_end_s:
                        continue
                    st = (b.get("status") or "").strip().lower()
                    if st and st not in ("booked", "new"):
                        continue
                    used += 1
                if used >= ruza_cap:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "error": "Мест больше нет. Смена заполнена.",
                            }
                        ),
                        400,
                    )
            except Exception as e:
                current_app.logger.warning(f"[camp] capacity check failed: {e!r}")
            current_app.logger.info("    ✅ Camp: capacity OK")
        else:
            from app.config.booking_features import is_phase2_availability_enabled

            if not is_phase2_availability_enabled():
                if service_type_from_payload == "boat":
                    slots = get_boat_slots(data["date"])
                else:
                    slots = get_available_slots(data["date"])

                available_slot = next(
                    (
                        slot
                        for slot in slots
                        if slot["time"] == data["time"] and slot["available"]
                    ),
                    None,
                )
                if not available_slot:
                    current_app.logger.warning(f"    ❌ Слот недоступен")
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "error": "Слот недоступен или уже занят",
                            }
                        ),
                        400,
                    )
                current_app.logger.info(f"    ✅ Слот доступен")
            else:
                current_app.logger.info(
                    "    ⏭️ Legacy slot precheck skipped (Phase 2 Calendar recheck on POST)"
                )

        # 5–9. Calendar-first pipeline (gym / boat / default). Camp — отдельная ветка ниже.
        if (service_type_from_payload or "").strip().lower() != "camp":
            from app.services.booking import (
                CalendarBookingError,
                DuplicateBookingError,
                SheetsBookingError,
                SlotUnavailableError,
                execute_web_booking,
            )

            svc = (service_type_from_payload or "gym").strip().lower()
            slot_times_raw = data.get("slot_times")
            booking_runs: list[tuple[str, int]] = []

            if svc == "boat" and slot_times_raw:
                from app.services.booking.boat_slot_selection import (
                    normalize_boat_slot_booking,
                )

                try:
                    normalized = normalize_boat_slot_booking(list(slot_times_raw))
                except ValueError:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "error": "Не выбраны слоты для записи на катер",
                            }
                        ),
                        400,
                    )
                if isinstance(normalized, tuple):
                    booking_runs = [normalized]
                else:
                    booking_runs = [(t, 1) for t in normalized]
            else:
                booking_runs = [
                    (data["time"], int(data.get("set_count") or 1)),
                ]

            booking_result = None
            try:
                for time_str, set_count in booking_runs:
                    booking_result = execute_web_booking(
                        date=data["date"],
                        time=time_str,
                        name=data["name"],
                        phone=data["phone"],
                        service_type=svc,
                        set_count=set_count,
                    )
                if booking_result is None:
                    raise CalendarBookingError("booking_result_missing")
                workout_id = booking_result.workout_id
                client_id = booking_result.client_id
                current_app.logger.info(
                    "booking_pipeline_ok workout_id_tail=%s client_id_tail=%s",
                    str(workout_id)[-8:],
                    str(client_id)[-8:],
                )
            except DuplicateBookingError:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "error": "Вы уже записаны на это время. Один слот — одна запись.",
                        }
                    ),
                    400,
                )
            except SlotUnavailableError as exc:
                reason = str(exc)
                if reason == "gym_capacity_full":
                    msg = "В этой группе нет свободных мест. Выберите другое время."
                elif svc == "boat":
                    msg = "Этот слот на катере уже занят. Обновите расписание и выберите другое время."
                else:
                    msg = "Слот недоступен. Выберите другое время."
                return jsonify({"status": "error", "error": msg}), 409
            except CalendarBookingError:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "error": "Не удалось создать запись в календаре. Попробуйте позже.",
                        }
                    ),
                    500,
                )
            except SheetsBookingError:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "error": "Не удалось завершить запись. Попробуйте позже.",
                        }
                    ),
                    500,
                )

            try:
                analytics_payload = {
                    "event": "booking_created",
                    "context": "site_booking",
                    "user_key": client_id or "",
                    "type": svc,
                    "meta": {
                        "date": data["date"],
                        "time": data["time"],
                        "workout_id": workout_id,
                        "booking_id": booking_result.booking_id,
                    },
                    "ip": request.remote_addr or "",
                    "user_agent": request.headers.get("User-Agent", ""),
                }
                log_analytics_event(analytics_payload)
            except Exception as e:
                current_app.logger.warning(f"analytics booking_created: {e}")

            try:
                success_view = url_for("booking.booking_success_view", _external=False)
            except Exception:
                success_view = "/booking/success-view"

            return (
                jsonify(
                    {
                        "status": "success",
                        "message": "Успешно забронировано",
                        "success_view_url": success_view,
                        "workout_id": workout_id,
                    }
                ),
                201,
            )

        # --- Camp: legacy Sheets flow (без Calendar-first в Phase 1) ---
        current_app.logger.info(f"  5️⃣ Создаю/ищу клиента {data['phone']}...")
        try:
            client_id = find_or_create_client(data["phone"], data["name"])
            if not client_id:
                current_app.logger.error("    ❌ find_or_create_client вернул None")
                return (
                    jsonify(
                        {
                            "status": "error",
                            "error": "Не удалось создать профиль клиента",
                        }
                    ),
                    500,
                )
            current_app.logger.info(f"    ✅ Клиент создан/найден: {client_id}")
        except Exception as e:
            current_app.logger.error(
                f"    ❌ Ошибка создания клиента: {str(e)}", exc_info=True
            )
            return (
                jsonify(
                    {"status": "error", "error": "Ошибка при создании профиля клиента"}
                ),
                500,
            )

        # 6. Поиск/создание тренировки
        try:
            workout_id, workout_row_idx, current_capacity = find_workout(
                data["date"], data["time"]
            )
            if not workout_id:
                current_app.logger.info(
                    f"Тренировка не найдена, создаём новую для {data['date']} {data['time']}"
                )
                workout_id = create_workout_if_not_exists(data["date"], data["time"])
                if not workout_id:
                    current_app.logger.error(
                        f"create_workout_if_not_exists вернул None для {data['date']} {data['time']}"
                    )
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "error": "Не удалось создать тренировку (create_workout вернул None)",
                            }
                        ),
                        500,
                    )
                # После создания ищем её снова
                workout_id, workout_row_idx, current_capacity = find_workout(
                    data["date"], data["time"]
                )
                if not workout_id:
                    current_app.logger.error(
                        f"После создания тренировка всё ещё не найдена! ID: {workout_id}"
                    )
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "error": "Не удалось найти тренировку после создания",
                            }
                        ),
                        500,
                    )
        except Exception as e:
            current_app.logger.error(
                f"Ошибка при работе с тренировкой: {str(e)}", exc_info=True
            )
            return (
                jsonify(
                    {
                        "status": "error",
                        "error": f"Ошибка при создании тренировки: {str(e)}",
                    }
                ),
                500,
            )

        # 7. Запись бронирования в Client_Workouts
        created_at = datetime.utcnow().isoformat()
        # Формируем словарь для записи, чтобы корректно заполнить новую колонку service_type (если есть)
        new_record = {
            "client_id": client_id,
            "workout_id": workout_id,
            "date": data["date"],
            "time": data["time"],
            "performance": "",
            "feedback": "",
            "payment_type": "single",
            "status": "booked",
            "created_at": created_at,
            "client_rating": "",
            "service_type": service_type_from_payload or "",
        }

        try:
            # Используем append_dict_to_sheet, чтобы значения были расположены по текущим заголовкам листа
            from app.modules.sheets_access import append_dict_to_sheet

            append_dict_to_sheet("Client_Workouts", new_record)
        except Exception as e:
            current_app.logger.error(f"Ошибка записи бронирования: {str(e)}")
            return (
                jsonify(
                    {"status": "error", "error": "Не удалось сохранить бронирование"}
                ),
                500,
            )

        # 8. Обновление счетчика мест в Workouts
        try:
            if workout_row_idx is not None:
                update_workout_capacity(workout_row_idx, current_capacity + 1)
        except Exception as e:
            current_app.logger.error(f"Ошибка обновления счетчика мест: {str(e)}")
            # Не прерываем процесс, так как бронь уже создана

        # 9. Camp: Calendar best-effort (legacy, не Calendar-first)
        try:
            service = get_google_services()
            add_event_to_calendar(
                service,
                data["date"],
                data["time"],
                data["name"],
                data["phone"],
            )
        except Exception as e:
            current_app.logger.error("Camp calendar best-effort failed: %s", e)

        try:
            analytics_payload = {
                "event": "booking_created",
                "context": "site_booking",
                "user_key": client_id or "",
                "type": data.get("service_type", ""),
                "rule_id": "",
                "item_id": "",
                "meta": {
                    "date": data["date"],
                    "time": data["time"],
                    "name": data["name"],
                    "phone": data["phone"],
                    "source": data.get("source", "site"),
                    "booking_type": data.get("booking_type", "client"),
                    "workout_id": workout_id,
                },
                "ip": request.remote_addr or "",
                "user_agent": request.headers.get("User-Agent", ""),
            }
            log_analytics_event(analytics_payload)
        except Exception as e:
            # Аналитика не должна ломать пользовательский сценарий
            current_app.logger.warning(
                f"Не удалось записать событие аналитики booking_created: {e}"
            )

        # 10. Ссылка на success-view для фронтенда
        try:
            success_view = url_for("booking.booking_success_view", _external=False)
        except Exception:
            success_view = "/booking/success-view"

        return (
            jsonify(
                {
                    "status": "success",
                    "message": "Успешно забронировано",
                    "success_view_url": success_view,
                }
            ),
            201,
        )

    except ValidationError as ve:
        return (
            jsonify(
                {
                    "status": "error",
                    "error": "Ошибка валидации данных",
                    "details": ve.messages,
                }
            ),
            400,
        )

    except FileNotFoundError as fe:
        current_app.logger.critical("booking_credentials_missing detail=%s", str(fe))
        return (
            jsonify(
                {
                    "status": "error",
                    "error": "Сервис записи временно недоступен. Обратитесь к администратору.",
                    "code": "google_credentials_missing",
                }
            ),
            503,
        )

    except HttpError as he:
        error_msg = str(he)
        current_app.logger.error(f"Ошибка Google API: {error_msg}")
        if "invalid_grant" in error_msg:
            return (
                jsonify(
                    {
                        "status": "error",
                        "error": "Ошибка авторизации сервера. Пожалуйста, попробуйте позже",
                    }
                ),
                503,
            )
        return (
            jsonify(
                {
                    "status": "error",
                    "error": "Временная ошибка сервера. Пожалуйста, попробуйте позже",
                }
            ),
            502,
        )

    except Exception as e:
        current_app.logger.exception("Неожиданная ошибка при бронировании слота")
        return (
            jsonify(
                {
                    "status": "error",
                    "error": "Внутренняя ошибка сервера. Пожалуйста, попробуйте позже",
                }
            ),
            500,
        )
