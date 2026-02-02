from flask import (
    Blueprint,
    render_template,
    flash,
    redirect,
    url_for,
    request,
    current_app,
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image as PILImage
import os
from datetime import datetime
import uuid

from app.database.models import db, Image
from app.forms.image import ImageUploadForm, ImageEditForm
from app.utils.decorators import admin_required

bp = Blueprint("admin_images", __name__, url_prefix="/admin/images")


def save_image(file, filename):
    """Сохраняет загруженное изображение с оптимизацией"""
    # Создаем директорию, если не существует
    upload_path = os.path.join(current_app.root_path, "static", "uploads", "images")
    os.makedirs(upload_path, exist_ok=True)

    filepath = os.path.join(upload_path, filename)

    # Открываем и оптимизируем изображение
    with PILImage.open(file) as img:
        # Получаем размеры
        width, height = img.size

        # Конвертируем в RGB если нужно
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Сохраняем с оптимизацией
        img.save(filepath, "JPEG", quality=85, optimize=True)

    return width, height


@bp.route("/")
@login_required
@admin_required
def index():
    """Список всех изображений"""
    page = request.args.get("page", 1, type=int)
    per_page = 20

    images = Image.query.order_by(Image.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template("admin/images/index.html", images=images)


@bp.route("/upload", methods=["GET", "POST"])
@login_required
@admin_required
def upload():
    """Загрузка нового изображения"""
    form = ImageUploadForm()

    if form.validate_on_submit():
        file = form.image.data
        # Генерируем уникальное имя файла
        filename = str(uuid.uuid4()) + secure_filename(file.filename)

        try:
            # Сохраняем файл и получаем размеры
            width, height = save_image(file, filename)

            # Создаем запись в БД
            image = Image(
                filename=filename,
                orig_filename=file.filename,
                mime_type=file.content_type,
                size=os.path.getsize(
                    os.path.join(
                        current_app.root_path, "static", "uploads", "images", filename
                    )
                ),
                width=width,
                height=height,
                title=form.title.data,
                alt=form.alt.data,
                caption=form.caption.data,
                group=form.group.data,
                order=form.order.data,
                created_by=current_user.id,
                created_at=datetime.utcnow(),
                optimized=True,
            )

            db.session.add(image)
            db.session.commit()

            flash("Изображение успешно загружено", "success")
            return redirect(url_for(".index"))

        except Exception as e:
            flash(f"Ошибка при загрузке изображения: {str(e)}", "error")

    return render_template("admin/images/upload.html", form=form)


@bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit(id):
    """Редактирование метаданных изображения"""
    image = Image.query.get_or_404(id)
    form = ImageEditForm(obj=image)

    if form.validate_on_submit():
        form.populate_obj(image)
        image.updated_at = datetime.utcnow()
        db.session.commit()

        flash("Изображение успешно обновлено", "success")
        return redirect(url_for(".index"))

    return render_template("admin/images/edit.html", form=form, image=image)


@bp.route("/<int:id>/delete", methods=["POST"])
@login_required
@admin_required
def delete(id):
    """Удаление изображения"""
    image = Image.query.get_or_404(id)

    try:
        # Удаляем файл
        filepath = os.path.join(
            current_app.root_path, "static", "uploads", "images", image.filename
        )
        if os.path.exists(filepath):
            os.remove(filepath)

        # Удаляем запись из БД
        db.session.delete(image)
        db.session.commit()

        flash("Изображение успешно удалено", "success")
    except Exception as e:
        flash(f"Ошибка при удалении изображения: {str(e)}", "error")

    return redirect(url_for(".index"))
