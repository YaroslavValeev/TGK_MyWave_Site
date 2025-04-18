from flask import Blueprint, render_template, request, redirect, url_for, flash

bp = Blueprint('auth', __name__)  # 🔐 Blueprint для авторизации

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # 🔒 Простая заглушка: можно заменить на проверку через БД или Google Sheets
        if username == "admin" and password == "password":
            flash("Вы успешно вошли!", "success")
            return redirect(url_for('index'))  # Перенаправление на главную страницу
        else:
            flash("Неверное имя пользователя или пароль", "danger")

    return render_template('auth/login.html')
