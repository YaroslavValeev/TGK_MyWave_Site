<<<<<<< HEAD
import sys
import os
import io
import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from flask_talisman import Talisman
from flask_admin import Admin
from flask_admin.contrib.fileadmin import FileAdmin
from apscheduler.schedulers.background import BackgroundScheduler
from modules.drive import list_media_files
import openai
import traceback
import sqlite3

# Импорт и инициализация базы данных (SQLAlchemy)
from modules.database import db  # В modules/database.py должна быть создана и инициализирована переменная db

# Добавляем текущую директорию в системный путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импорт GPT-интеграции (функция ask_gpt реализована в gpt_integration.py)
from gpt_integration import ask_gpt

# Загрузка переменных окружения из файла .env
load_dotenv()

# =========================
# Инициализация глобального объекта Flask
# =========================
app = Flask(__name__)
# Задаем секретный ключ приложения (проверяем переменную окружения SECRET_KEY)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mywave.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)  # Инициализируем базу данных

# Настройка кодировки для корректной работы с Unicode (UTF-8)
# =========================
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# =========================
# Настройка безопасности
# =========================
# Flask-Talisman – для установки безопасных HTTP-заголовков (force_https=False для разработки)
from flask_talisman import Talisman

csp = {
    'default-src': ["'self'", 'https://stackpath.bootstrapcdn.com', 'https://fonts.googleapis.com', 'https://fonts.gstatic.com', 'data:'],
    'style-src': ["'self'", "'unsafe-inline'", 'https://stackpath.bootstrapcdn.com'],
    'script-src': ["'self'", "'unsafe-inline'"]
}

Talisman(app, content_security_policy=csp, force_https=False)


# CSRF-защита – для защиты форм
csrf = CSRFProtect(app)

# =========================
# Инициализация APScheduler – планировщика задач
# =========================
scheduler = BackgroundScheduler()
scheduler.start()

# =========================
# Инициализация Flask-Admin для управления статикой
# =========================
admin = Admin(app, name='MyWave Admin', template_mode='bootstrap3')
admin.add_view(FileAdmin(os.path.join(os.path.dirname(__file__), 'static'), '/static/', name='Static Files'))

# =========================
# Инициализация Flask-Login для управления пользователями
# =========================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Простейшая модель пользователя (в production рекомендуется хранить данные в БД)
class User(UserMixin):
    def __init__(self, id, is_admin=False):
        self.id = id
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    # Здесь можно реализовать загрузку пользователя из базы данных
    return User(user_id, is_admin=True)  # Пока что все пользователи считаются администраторами

# =========================
# Маршруты для логина и логаута
# =========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Простейшая проверка учетных данных; в production используйте безопасное хранение паролей
        if username == 'Yakar' and password == '23232323':
            user = User(id=username, is_admin=True)
            login_user(user)
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash('Неверные учетные данные')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# =========================
# Настройка OpenAI для GPT интеграции
# =========================
openai.api_key = os.getenv("OPENAI_API_KEY").strip()
# =========================
# Конфиденциальные данные для интеграций (Telegram, Google API)
# =========================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")

# =========================
# Endpoint для GPT-чата (через OpenAI)
# =========================
# Указываем Fine-tuned модель
MODEL_ID = "ft:gpt-4o-mini-2024-07-18:mywave:mywavesite:Axgy7lSh"  # Обновите на свою Fine-tuned модель

# Отключаем CSRF для этого маршрута
@csrf.exempt
@app.route("/gpt_chat", methods=["POST"])
def gpt_chat():
    try:
        # Получаем данные запроса (поддержка JSON и form)
        data = request.get_json() if request.is_json else request.form
        user_message = data.get("message")
        if not user_message:
            return jsonify({"error": "Сообщение не предоставлено"}), 400

        print("Отправка запроса в OpenAI...")

        # Используем новый API-интерфейс OpenAI для Fine-tuned модели
        response = openai.ChatCompletion.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": "Ты эксперт по вейксерфингу и вейкбордингу."},
                {"role": "user", "content": user_message}
            ]
        )

        # Извлекаем ответ из OpenAI
        reply = response.choices[0].message.content.strip()
        return jsonify({"reply": reply})

    except Exception as e:
        error_message = traceback.format_exc()
        print("Полная ошибка сервера:", error_message)
        return jsonify({"error": error_message}), 500

# Страница чата (HTML)
@app.route("/chat", methods=["GET"])
def chat_page():
    return render_template("chat.html", page_title="Чат с экспертом по вейку")

# Endpoint для обработки чата (например, для отправки сообщений через AJAX)
@app.route("/chat", methods=["POST"])
def chat_handler():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Сообщение не найдено"}), 400
    reply = ask_gpt(data["message"])
    return jsonify({"reply": reply})

# =========================
# Функции для работы с Google API (Sheets и Calendar)
# =========================
def get_sheets_service():
    creds = Credentials.from_service_account_file(
        os.getenv("GOOGLE_SHEETS_CREDENTIALS"),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds)

def get_calendar_service():
    creds = Credentials.from_service_account_file(
        os.getenv("GOOGLE_SHEETS_CREDENTIALS"),
        scopes=["https://www.googleapis.com/auth/calendar"]
    )
    return build("calendar", "v3", credentials=creds)

# =========================
# Функция отправки уведомления через Telegram
# =========================
def send_telegram_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    response = requests.post(url, data=data)
    return response

# =========================
# Планирование напоминаний через APScheduler
# =========================
def schedule_reminders(training_datetime, client_id, workout_id, client_notify=False, client_chat_id=None):
    reminder_24h = training_datetime - timedelta(hours=24)
    reminder_1h = training_datetime - timedelta(hours=1)
    now = datetime.utcnow()
    trainer_token = os.getenv("NOTIFICATION_BOT_TOKEN")
    trainer_chat_id = os.getenv("TRAINER_CHAT_ID")
    
    if reminder_24h > now:
        scheduler.add_job(
            lambda: send_telegram_message(
                trainer_token,
                trainer_chat_id,
                f"Напоминание: через 24 часа тренировка клиента {client_id} (Workout ID: {workout_id}) начнется в {training_datetime.strftime('%Y-%m-%d %H:%M')}"
            ),
            'date',
            run_date=reminder_24h
        )
    if reminder_1h > now:
        scheduler.add_job(
            lambda: send_telegram_message(
                trainer_token,
                trainer_chat_id,
                f"Напоминание: через 1 час тренировка клиента {client_id} (Workout ID: {workout_id}) начнется в {training_datetime.strftime('%Y-%m-%d %H:%M')}"
            ),
            'date',
            run_date=reminder_1h
        )
    
    if client_notify and client_chat_id:
        client_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if reminder_24h > now:
            scheduler.add_job(
                lambda: send_telegram_message(
                    client_token,
                    client_chat_id,
                    f"Напоминание: через 24 часа ваша тренировка (Workout ID: {workout_id}) начнется в {training_datetime.strftime('%Y-%m-%d %H:%M')}"
                ),
                'date',
                run_date=reminder_24h
            )
        if reminder_1h > now:
            scheduler.add_job(
                lambda: send_telegram_message(
                    client_token,
                    client_chat_id,
                    f"Напоминание: через 1 час ваша тренировка (Workout ID: {workout_id}) начнется в {training_datetime.strftime('%Y-%m-%d %H:%M')}"
                ),
                'date',
                run_date=reminder_1h
            )

# =========================
# Функции работы с Google Calendar (слоты, отмена событий)
# =========================
def get_available_slots():
    service = get_calendar_service()
    now = datetime.utcnow().isoformat() + "Z"
    end = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"
    events_result = service.events().list(
        calendarId=os.getenv("GOOGLE_CALENDAR_ID"),
        timeMin=now,
        timeMax=end,
        maxResults=50,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    events = events_result.get("items", [])
    slots = []
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        slots.append({"id": event["id"], "start": start})
    return slots

def get_nearest_available_slot():
    slots = get_available_slots()
    now = datetime.utcnow()
    future_slots = []
    for slot in slots:
        try:
            slot_dt = datetime.fromisoformat(slot["start"])
            if slot_dt > now:
                future_slots.append(slot_dt)
        except Exception:
            continue
    if future_slots:
        future_slots.sort()
        return future_slots[0].isoformat()
    return None

def get_slots_by_date(date_str):
    slots = get_available_slots()
    matching_slots = []
    for slot in slots:
        try:
            slot_dt = datetime.fromisoformat(slot["start"])
            if slot_dt.strftime("%Y-%m-%d") == date_str:
                matching_slots.append(slot)
        except Exception:
            continue
    return matching_slots

def cancel_event(event_id):
    service = get_calendar_service()
    event = service.events().get(calendarId=os.getenv("GOOGLE_CALENDAR_ID"), eventId=event_id).execute()
    start = event["start"].get("dateTime", event["start"].get("date"))
    event_start = datetime.fromisoformat(start)
    if (event_start - datetime.utcnow()) < timedelta(hours=12):
        raise Exception("Отмена невозможна за 12 часов до начала занятия")
    service.events().delete(calendarId=os.getenv("GOOGLE_CALENDAR_ID"), eventId=event_id).execute()

# =========================
# Основные маршруты сайта
# =========================
@app.route("/")
def home():
    return render_template("index.html", page_title="Главная")

@app.route("/schedule")
def schedule():
    slots = get_available_slots()
    return render_template("schedule.html", slots=slots, page_title="Расписание")

@app.route("/enter_contact", methods=["GET", "POST"])
def enter_contact():
    if request.method == "POST":
        user_name = request.form.get("user_name")
        user_contact = request.form.get("user_contact")
        if not user_name or not user_contact:
            return jsonify({"error": "Введите имя и контакт"}), 400
        session["user_name"] = user_name
        session["user_contact"] = user_contact
        return redirect(url_for("select_date"))
    return render_template("enter_contact.html", page_title="Введите контактные данные")

@app.route("/select_date")
def select_date():
    slots = get_available_slots()
    dates = sorted({datetime.fromisoformat(slot["start"]).strftime("%Y-%m-%d") for slot in slots})
    return render_template("select_date.html", dates=dates, page_title="Выберите дату")

@app.route("/select_time/<selected_date>")
def select_time(selected_date):
    slots_for_date = get_slots_by_date(selected_date)
    if not slots_for_date:
        return jsonify({"error": "На этот день нет свободных слотов", "suggested_slot": get_nearest_available_slot()}), 400
    return render_template("select_time.html", slots=slots_for_date, selected_date=selected_date, page_title="Выберите время")

@app.route("/available_slots")
def available_slots():
    slots = get_available_slots()
    return jsonify({"available_slots": slots})

@app.route("/services")
def services():
    return render_template("services.html", page_title="Услуги")

@app.route("/shop")
def shop():
    return render_template("shop.html", page_title="Магазин")

@app.route("/events")
def events():
    return render_template("events.html", page_title="Мероприятия")

@app.route("/blog")
def blog():
    return render_template("blog.html", page_title="Блог")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        user_name = request.form.get("user_name")
        user_contact = request.form.get("user_contact")
        user_message = request.form.get("user_message")
        send_telegram_message_contact(user_name, user_contact, user_message)
        append_contact_to_Clients_sheet(user_name, user_contact, user_message)
        return redirect(url_for("thank_you"))
    return render_template("contact.html", page_title="Контакты")

@app.route("/thankyou")
def thank_you():
    return render_template("thank_you.html", page_title="Спасибо!")

@app.route("/about")
def about():
    return render_template("about.html", page_title="О тренере")

@app.route("/cancel_session", methods=["POST"])
def cancel_session():
    data = request.get_json()
    event_id = data.get("event_id")
    if not event_id:
        return jsonify({"error": "event_id не передан"}), 400
    try:
        cancel_event(event_id)
        return jsonify({"message": "Занятие успешно отменено"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# =========================
# Функции для работы с Telegram и Google Sheets
# =========================
def send_telegram_message_contact(name, contact, message):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        text_msg = (
            f"Новая заявка через контактную форму:\n"
            f"Имя: {name}\n"
            f"Контакт: {contact}\n"
            f"Сообщение: {message}"
        )
        url_req = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": text_msg}
        requests.post(url_req, data=data)

def append_contact_to_Clients_sheet(name, contact, message):
    service = get_sheets_service()
    sheet = service.spreadsheets()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    values = [[name, contact, message, now_str]]
    body = {"values": values}
    sheet.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Clients!A:J",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()

def send_telegram_message_session(client_id, workout_id, created_at):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        text_msg = (
            f"Запись на тренировку:\n"
            f"Client ID: {client_id}\n"
            f"Workout ID: {workout_id}\n"
            f"Дата/Время: {created_at}"
        )
        url_req = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": text_msg}
        requests.post(url_req, data=data)

def append_to_Client_Workouts(data):
    service = get_sheets_service()
    sheet = service.spreadsheets()
    values = [[
        "",  # id (оставляем пустым для автоинкремента)
        data["client_id"],
        data["workout_id"],
        "",  # performance
        "",  # feedback
        data["payment_type"],
        data["status"],
        data["created_at"],
        ""   # client_rating
    ]]
    body = {"values": values}
    sheet.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Client_Workouts!A:H",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()

    @app.route("/media_files_drive", methods=["GET"])
    def media_files_drive():
        try:
            files = list_media_files()
            return jsonify({"files": files})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# Регистрация Blueprint для админ-панели
from modules.admin import admin_bp
app.register_blueprint(admin_bp, url_prefix='/admin')

# Если вы хотите использовать фабричный паттерн, можно создать функцию create_app(), но здесь мы используем глобальный объект.
if __name__ == "__main__":
=======
import sys
import os
import io
import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from flask_talisman import Talisman
from flask_admin import Admin
from flask_admin.contrib.fileadmin import FileAdmin
from apscheduler.schedulers.background import BackgroundScheduler
from modules.drive import list_media_files
import openai
import traceback
import sqlite3

# Импорт и инициализация базы данных (SQLAlchemy)
from modules.database import db  # В modules/database.py должна быть создана и инициализирована переменная db

# Добавляем текущую директорию в системный путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импорт GPT-интеграции (функция ask_gpt реализована в gpt_integration.py)
from gpt_integration import ask_gpt

# Загрузка переменных окружения из файла .env
load_dotenv()

# =========================
# Инициализация глобального объекта Flask
# =========================
app = Flask(__name__)
# Задаем секретный ключ приложения (проверяем переменную окружения SECRET_KEY)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mywave.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)  # Инициализируем базу данных

# Настройка кодировки для корректной работы с Unicode (UTF-8)
# =========================
sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8')

# =========================
# Настройка безопасности
# =========================
# Flask-Talisman – для установки безопасных HTTP-заголовков (force_https=False для разработки)
from flask_talisman import Talisman

csp = {
    'default-src': ["'self'", 'https://stackpath.bootstrapcdn.com', 'https://fonts.googleapis.com', 'https://fonts.gstatic.com', 'data:'],
    'style-src': ["'self'", "'unsafe-inline'", 'https://stackpath.bootstrapcdn.com'],
    'script-src': ["'self'", "'unsafe-inline'"]
}

Talisman(app, content_security_policy=csp, force_https=False)


# CSRF-защита – для защиты форм
csrf = CSRFProtect(app)

# =========================
# Инициализация APScheduler – планировщика задач
# =========================
scheduler = BackgroundScheduler()
scheduler.start()

# =========================
# Инициализация Flask-Admin для управления статикой
# =========================
admin = Admin(app, name='MyWave Admin', template_mode='bootstrap3')
admin.add_view(FileAdmin(os.path.join(os.path.dirname(__file__), 'static'), '/static/', name='Static Files'))

# =========================
# Инициализация Flask-Login для управления пользователями
# =========================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Простейшая модель пользователя (в production рекомендуется хранить данные в БД)
class User(UserMixin):
    def __init__(self, id, is_admin=False):
        self.id = id
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    # Здесь можно реализовать загрузку пользователя из базы данных
    return User(user_id, is_admin=True)  # Пока что все пользователи считаются администраторами

# =========================
# Маршруты для логина и логаута
# =========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Простейшая проверка учетных данных; в production используйте безопасное хранение паролей
        if username == 'Yakar' and password == '23232323':
            user = User(id=username, is_admin=True)
            login_user(user)
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash('Неверные учетные данные')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# =========================
# Настройка OpenAI для GPT интеграции
# =========================
openai.api_key = os.getenv("OPENAI_API_KEY").strip()
# =========================
# Конфиденциальные данные для интеграций (Telegram, Google API)
# =========================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")

# =========================
# Endpoint для GPT-чата (через OpenAI)
# =========================
# Указываем Fine-tuned модель
MODEL_ID = "ft:gpt-4o-mini-2024-07-18:mywave:mywavesite:Axgy7lSh"  # Обновите на свою Fine-tuned модель

# Отключаем CSRF для этого маршрута
@csrf.exempt
@app.route("/gpt_chat", methods=["POST"])
def gpt_chat():
    try:
        # Получаем данные запроса (поддержка JSON и form)
        data = request.get_json() if request.is_json else request.form
        user_message = data.get("message")
        if not user_message:
            return jsonify({"error": "Сообщение не предоставлено"}), 400

        print("Отправка запроса в OpenAI...")

        # Используем новый API-интерфейс OpenAI для Fine-tuned модели
        response = openai.ChatCompletion.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": "Ты эксперт по вейксерфингу и вейкбордингу."},
                {"role": "user", "content": user_message}
            ]
        )

        # Извлекаем ответ из OpenAI
        reply = response.choices[0].message.content.strip()
        return jsonify({"reply": reply})

    except Exception as e:
        error_message = traceback.format_exc()
        print("Полная ошибка сервера:", error_message)
        return jsonify({"error": error_message}), 500

# Страница чата (HTML)
@app.route("/chat", methods=["GET"])
def chat_page():
    return render_template("chat.html", page_title="Чат с экспертом по вейку")

# Endpoint для обработки чата (например, для отправки сообщений через AJAX)
@app.route("/chat", methods=["POST"])
def chat_handler():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Сообщение не найдено"}), 400
    reply = ask_gpt(data["message"])
    return jsonify({"reply": reply})

# =========================
# Функции для работы с Google API (Sheets и Calendar)
# =========================
def get_sheets_service():
    creds = Credentials.from_service_account_file(
        os.getenv("GOOGLE_SHEETS_CREDENTIALS"),
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds)

def get_calendar_service():
    creds = Credentials.from_service_account_file(
        os.getenv("GOOGLE_SHEETS_CREDENTIALS"),
        scopes=["https://www.googleapis.com/auth/calendar"]
    )
    return build("calendar", "v3", credentials=creds)

# =========================
# Функция отправки уведомления через Telegram
# =========================
def send_telegram_message(token, chat_id, text):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": text}
    response = requests.post(url, data=data)
    return response

# =========================
# Планирование напоминаний через APScheduler
# =========================
def schedule_reminders(training_datetime, client_id, workout_id, client_notify=False, client_chat_id=None):
    reminder_24h = training_datetime - timedelta(hours=24)
    reminder_1h = training_datetime - timedelta(hours=1)
    now = datetime.utcnow()
    trainer_token = os.getenv("NOTIFICATION_BOT_TOKEN")
    trainer_chat_id = os.getenv("TRAINER_CHAT_ID")
    
    if reminder_24h > now:
        scheduler.add_job(
            lambda: send_telegram_message(
                trainer_token,
                trainer_chat_id,
                f"Напоминание: через 24 часа тренировка клиента {client_id} (Workout ID: {workout_id}) начнется в {training_datetime.strftime('%Y-%m-%d %H:%M')}"
            ),
            'date',
            run_date=reminder_24h
        )
    if reminder_1h > now:
        scheduler.add_job(
            lambda: send_telegram_message(
                trainer_token,
                trainer_chat_id,
                f"Напоминание: через 1 час тренировка клиента {client_id} (Workout ID: {workout_id}) начнется в {training_datetime.strftime('%Y-%m-%d %H:%M')}"
            ),
            'date',
            run_date=reminder_1h
        )
    
    if client_notify and client_chat_id:
        client_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if reminder_24h > now:
            scheduler.add_job(
                lambda: send_telegram_message(
                    client_token,
                    client_chat_id,
                    f"Напоминание: через 24 часа ваша тренировка (Workout ID: {workout_id}) начнется в {training_datetime.strftime('%Y-%m-%d %H:%M')}"
                ),
                'date',
                run_date=reminder_24h
            )
        if reminder_1h > now:
            scheduler.add_job(
                lambda: send_telegram_message(
                    client_token,
                    client_chat_id,
                    f"Напоминание: через 1 час ваша тренировка (Workout ID: {workout_id}) начнется в {training_datetime.strftime('%Y-%m-%d %H:%M')}"
                ),
                'date',
                run_date=reminder_1h
            )

# =========================
# Функции работы с Google Calendar (слоты, отмена событий)
# =========================
def get_available_slots():
    service = get_calendar_service()
    now = datetime.utcnow().isoformat() + "Z"
    end = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"
    events_result = service.events().list(
        calendarId=os.getenv("GOOGLE_CALENDAR_ID"),
        timeMin=now,
        timeMax=end,
        maxResults=50,
        singleEvents=True,
        orderBy="startTime"
    ).execute()
    events = events_result.get("items", [])
    slots = []
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        slots.append({"id": event["id"], "start": start})
    return slots

def get_nearest_available_slot():
    slots = get_available_slots()
    now = datetime.utcnow()
    future_slots = []
    for slot in slots:
        try:
            slot_dt = datetime.fromisoformat(slot["start"])
            if slot_dt > now:
                future_slots.append(slot_dt)
        except Exception:
            continue
    if future_slots:
        future_slots.sort()
        return future_slots[0].isoformat()
    return None

def get_slots_by_date(date_str):
    slots = get_available_slots()
    matching_slots = []
    for slot in slots:
        try:
            slot_dt = datetime.fromisoformat(slot["start"])
            if slot_dt.strftime("%Y-%m-%d") == date_str:
                matching_slots.append(slot)
        except Exception:
            continue
    return matching_slots

def cancel_event(event_id):
    service = get_calendar_service()
    event = service.events().get(calendarId=os.getenv("GOOGLE_CALENDAR_ID"), eventId=event_id).execute()
    start = event["start"].get("dateTime", event["start"].get("date"))
    event_start = datetime.fromisoformat(start)
    if (event_start - datetime.utcnow()) < timedelta(hours=12):
        raise Exception("Отмена невозможна за 12 часов до начала занятия")
    service.events().delete(calendarId=os.getenv("GOOGLE_CALENDAR_ID"), eventId=event_id).execute()

# =========================
# Основные маршруты сайта
# =========================
@app.route("/")
def home():
    return render_template("index.html", page_title="Главная")

@app.route("/schedule")
def schedule():
    slots = get_available_slots()
    return render_template("schedule.html", slots=slots, page_title="Расписание")

@app.route("/enter_contact", methods=["GET", "POST"])
def enter_contact():
    if request.method == "POST":
        user_name = request.form.get("user_name")
        user_contact = request.form.get("user_contact")
        if not user_name or not user_contact:
            return jsonify({"error": "Введите имя и контакт"}), 400
        session["user_name"] = user_name
        session["user_contact"] = user_contact
        return redirect(url_for("select_date"))
    return render_template("enter_contact.html", page_title="Введите контактные данные")

@app.route("/select_date")
def select_date():
    slots = get_available_slots()
    dates = sorted({datetime.fromisoformat(slot["start"]).strftime("%Y-%m-%d") for slot in slots})
    return render_template("select_date.html", dates=dates, page_title="Выберите дату")

@app.route("/select_time/<selected_date>")
def select_time(selected_date):
    slots_for_date = get_slots_by_date(selected_date)
    if not slots_for_date:
        return jsonify({"error": "На этот день нет свободных слотов", "suggested_slot": get_nearest_available_slot()}), 400
    return render_template("select_time.html", slots=slots_for_date, selected_date=selected_date, page_title="Выберите время")

@app.route("/available_slots")
def available_slots():
    slots = get_available_slots()
    return jsonify({"available_slots": slots})

@app.route("/services")
def services():
    return render_template("services.html", page_title="Услуги")

@app.route("/shop")
def shop():
    return render_template("shop.html", page_title="Магазин")

@app.route("/events")
def events():
    return render_template("events.html", page_title="Мероприятия")

@app.route("/blog")
def blog():
    return render_template("blog.html", page_title="Блог")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        user_name = request.form.get("user_name")
        user_contact = request.form.get("user_contact")
        user_message = request.form.get("user_message")
        send_telegram_message_contact(user_name, user_contact, user_message)
        append_contact_to_Clients_sheet(user_name, user_contact, user_message)
        return redirect(url_for("thank_you"))
    return render_template("contact.html", page_title="Контакты")

@app.route("/thankyou")
def thank_you():
    return render_template("thank_you.html", page_title="Спасибо!")

@app.route("/about")
def about():
    return render_template("about.html", page_title="О тренере")

@app.route("/cancel_session", methods=["POST"])
def cancel_session():
    data = request.get_json()
    event_id = data.get("event_id")
    if not event_id:
        return jsonify({"error": "event_id не передан"}), 400
    try:
        cancel_event(event_id)
        return jsonify({"message": "Занятие успешно отменено"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# =========================
# Функции для работы с Telegram и Google Sheets
# =========================
def send_telegram_message_contact(name, contact, message):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        text_msg = (
            f"Новая заявка через контактную форму:\n"
            f"Имя: {name}\n"
            f"Контакт: {contact}\n"
            f"Сообщение: {message}"
        )
        url_req = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": text_msg}
        requests.post(url_req, data=data)

def append_contact_to_Clients_sheet(name, contact, message):
    service = get_sheets_service()
    sheet = service.spreadsheets()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    values = [[name, contact, message, now_str]]
    body = {"values": values}
    sheet.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Clients!A:J",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()

def send_telegram_message_session(client_id, workout_id, created_at):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        text_msg = (
            f"Запись на тренировку:\n"
            f"Client ID: {client_id}\n"
            f"Workout ID: {workout_id}\n"
            f"Дата/Время: {created_at}"
        )
        url_req = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": text_msg}
        requests.post(url_req, data=data)

def append_to_Client_Workouts(data):
    service = get_sheets_service()
    sheet = service.spreadsheets()
    values = [[
        "",  # id (оставляем пустым для автоинкремента)
        data["client_id"],
        data["workout_id"],
        "",  # performance
        "",  # feedback
        data["payment_type"],
        data["status"],
        data["created_at"],
        ""   # client_rating
    ]]
    body = {"values": values}
    sheet.values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Client_Workouts!A:H",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()

    @app.route("/media_files_drive", methods=["GET"])
    def media_files_drive():
        try:
            files = list_media_files()
            return jsonify({"files": files})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# Регистрация Blueprint для админ-панели
from modules.admin import admin_bp
app.register_blueprint(admin_bp, url_prefix='/admin')

# Если вы хотите использовать фабричный паттерн, можно создать функцию create_app(), но здесь мы используем глобальный объект.
if __name__ == "__main__":
>>>>>>> 1a630d3 (Добавлен код сайта)
    app.run(debug=True)