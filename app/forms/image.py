from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class ImageUploadForm(FlaskForm):
    """Форма для загрузки изображений"""

    image = FileField(
        "Изображение",
        validators=[
            FileRequired(),
            FileAllowed(["jpg", "jpeg", "png", "gif"], "Разрешены только изображения!"),
        ],
    )
    title = StringField("Название", validators=[Length(max=255)])
    alt = StringField("Alt текст", validators=[Length(max=255)])
    caption = TextAreaField("Подпись")
    group = SelectField(
        "Группа",
        choices=[
            ("services", "Услуги"),
            ("blog", "Блог"),
            ("gallery", "Галерея"),
            ("other", "Другое"),
        ],
        validators=[DataRequired()],
    )
    order = StringField("Порядок отображения", validators=[Optional()])


class ImageEditForm(FlaskForm):
    """Форма для редактирования метаданных изображения"""

    title = StringField("Название", validators=[Length(max=255)])
    alt = StringField("Alt текст", validators=[Length(max=255)])
    caption = TextAreaField("Подпись")
    group = SelectField(
        "Группа",
        choices=[
            ("services", "Услуги"),
            ("blog", "Блог"),
            ("gallery", "Галерея"),
            ("other", "Другое"),
        ],
        validators=[DataRequired()],
    )
    order = StringField("Порядок отображения", validators=[Optional()])
