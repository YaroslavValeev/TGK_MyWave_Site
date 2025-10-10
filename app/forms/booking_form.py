# app/forms/booking_form.py
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TimeField, SubmitField
from wtforms.validators import DataRequired, Email, Regexp

class BookingForm(FlaskForm):
    name = StringField(
        'Имя',
        validators=[DataRequired()],
        render_kw={"placeholder": "Ваше имя"}
    )
    email = StringField(
        'Email',
        validators=[DataRequired(), Email()],
        render_kw={"placeholder": "example@mail.com"}
    )
    phone = StringField(
        'Телефон',
        validators=[
            DataRequired(message="Введите телефон"),
            Regexp(r'^\+?\d{10,15}$', message="Неверный формат телефонного номера")
        ],
        render_kw={"placeholder": "+7 (___) ___-__-__"}
    )
    date = DateField('Дата', validators=[DataRequired()], format='%Y-%m-%d', render_kw={"placeholder": "2024-01-01"})
    time = TimeField('Время', validators=[DataRequired()], format='%H:%M', render_kw={"placeholder": "10:00"})
    submit = SubmitField('Записаться')
