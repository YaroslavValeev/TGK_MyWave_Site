from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp, ValidationError
import re


def simple_email_validator(form, field):
    """Lightweight email validator used in tests/environments where
    the 'email_validator' package is not installed. Uses a permissive
    regex to check basic structure only.
    """
    value = (field.data or "").strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
        raise ValidationError('Invalid email address')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(3, 50)])
    email = StringField('Email', validators=[DataRequired(), simple_email_validator])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8),
        Regexp(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$',
               message='Пароль должен содержать буквы и цифры')
    ])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), simple_email_validator])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login') 