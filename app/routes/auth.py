from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from app.services.google import append_to_sheet, get_google_services
import datetime

bp = Blueprint('auth', __name__)  # ✅ Здесь создается Blueprint

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Простая логика проверки
        if username == "admin" and password == "password":
            flash("Вы успешно вошли!", "success")
            return redirect(url_for('index'))  # Перенаправление на главную страницу
        else:
            flash("Неверное имя пользователя или пароль", "danger")

    return render_template('auth/login.html')

@bp.route('/register', methods=['POST'])
def register():
    """Обрабатывает регистрацию клиентов и запись в Google Sheets"""
    data = request.form
    name = data.get("name")
    phone = data.get("phone")
    telegram_id = data.get("telegram_id", "")
    source = "telegram" if telegram_id else "web"
    
    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    drive_service, sheets_service, calendar_service = get_google_services()
    spreadsheet_id = current_app.config["SPREADSHEET_ID"]
    
    # Проверяем, существует ли клиент уже в базе
    clients_result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="Clients!B2:G"
    ).execute()
    
    client_id = None
    if "values" in clients_result:
        for row in clients_result["values"]:
            if len(row) >= 3 and (row[1] == name or row[2] == phone):
                client_id = row[0]
                break
    
    if not client_id:
        # Генерируем новый client_id, если клиент новый
        client_id = f"client_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        new_client = [[client_id, telegram_id, name, phone, "", "beginner", created_at, source, created_at]]
        append_to_sheet(sheets_service, spreadsheet_id, "Clients!A2:H", new_client)
    
    return redirect(url_for('index'))

