from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from app.database.models import User
from app.database.models import db
from app.forms.auth_forms import RegistrationForm, LoginForm
from app.modules.sheets import append_row
from datetime import datetime

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        # Проверка уникальности email
        if User.query.filter_by(email=form.email.data).first():
            flash("Email уже используется", "danger")
        else:
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            # Дублирование в Google Sheets
            try:
                append_row(
                    "Users", [user.id, user.email, datetime.utcnow().isoformat()]
                )
            except Exception as e:
                flash(f"Ошибка при записи в Google Sheets: {e}", "warning")
            flash("Регистрация успешна!", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Вы вошли в систему", "success")
            next_page = request.args.get("next") or url_for("index")
            return redirect(next_page)
        flash("Неверные учетные данные", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли", "info")
    return redirect(url_for("auth.login"))
