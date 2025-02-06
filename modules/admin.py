from flask import Blueprint, request, redirect, url_for, render_template, flash
from flask_login import UserMixin, login_user, logout_user, login_required, current_user

# Регистрируем Blueprint с именем 'admin_panel' и указываем папку шаблонов для админ-панели
admin_bp = Blueprint('admin_panel', __name__, template_folder='../templates/admin')

# Простейшая модель пользователя для админ-панели
class User(UserMixin):
    def __init__(self, id):
        self.id = id
        self.username = id  # В простейшем случае используем id в качестве username

# Страница входа
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Временная проверка учетных данных (в production используйте базу данных и безопасное хранение паролей)
        if username == 'admin' and password == 'password':
            user = User(username)
            login_user(user)
            return redirect(url_for('admin_panel.dashboard'))
        else:
            flash('Неверное имя пользователя или пароль.')
    return render_template('login.html')

# Панель администратора (dashboard)
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', page_title="Панель администратора", user=current_user)

# Логаут
@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('admin_panel.login'))

# Функциональность: Редактирование расписания
@admin_bp.route('/edit_schedule', methods=['GET', 'POST'])
@login_required
def edit_schedule():
    if request.method == 'POST':
        schedule_data = request.form.get('schedule')
        # Здесь должна быть логика сохранения изменений (например, обновление Google Calendar или базы данных)
        flash('Расписание успешно обновлено.', 'success')
        return redirect(url_for('admin_panel.dashboard'))
    return render_template('edit_schedule.html', page_title="Редактирование расписания")

# Функциональность: Управление пользователями
@admin_bp.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if request.method == 'POST':
        new_user = request.form.get('new_user')
        # Здесь можно добавить логику добавления нового пользователя в базу данных
        flash(f'Пользователь {new_user} успешно добавлен.', 'success')
        return redirect(url_for('admin_panel.dashboard'))
    return render_template('manage_users.html', page_title="Управление пользователями")

# Функциональность: Аналитика сайта
@admin_bp.route('/analytics')
@login_required
def analytics():
    # Здесь можно интегрировать реальные данные аналитики (например, через Google Analytics API)
    data = {
        'visits_today': 123,
        'active_users': 45,
        'new_signups': 8
    }
    return render_template('analytics.html', data=data, page_title="Аналитика сайта")
