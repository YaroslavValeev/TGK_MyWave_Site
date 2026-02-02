from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length


class ContactForm(FlaskForm):
    name = StringField(
        "Имя",
        validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={"placeholder": "Ваше имя"},
    )
    email = StringField(
        "Email",
        validators=[DataRequired(), Email()],
        render_kw={"placeholder": "example@mail.com"},
    )
    message = TextAreaField(
        "Сообщение",
        validators=[DataRequired(), Length(min=5, max=2000)],
        render_kw={"placeholder": "Ваш вопрос или сообщение"},
    )
    submit = SubmitField("Отправить")
