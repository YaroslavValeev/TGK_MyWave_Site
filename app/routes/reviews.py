from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.forms.review_form import ReviewForm
from app.modules.sheets import append_row, get_all_records
from datetime import datetime
import uuid

reviews_bp = Blueprint("reviews", __name__, url_prefix="/reviews")


@reviews_bp.route("/", methods=["GET", "POST"])
def reviews():
    form = ReviewForm()
    if form.validate_on_submit():
        # Генерируем уникальный review_id
        review_id = f"rev-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:8]}"
        # Для сайта client_id можно оставить пустым
        client_id = ""
        rating = form.rating.data
        comment = form.text.data
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        platform = "site"
        is_resolved = "false"
        recommended = "false"
        review_type = ""
        row = [
            review_id,
            client_id,
            rating,
            comment,
            created_at,
            platform,
            is_resolved,
            recommended,
            review_type,
        ]
        try:
            append_row("Feedback_Reviews", row)
            flash("Спасибо за ваш отзыв!", "success")
            return redirect(url_for("reviews.reviews"))
        except Exception as e:
            flash(f"Ошибка при сохранении отзыва: {e}", "danger")
    # Получаем все отзывы для отображения
    reviews_list = get_all_records("Feedback_Reviews")
    return render_template("reviews.html", form=form, reviews=reviews_list)
