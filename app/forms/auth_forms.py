from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Regexp


class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(3, 50)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8),
            Regexp(
                r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$",
                message="Пароль должен содержать буквы и цифры",
            ),
        ],
    )
    submit = SubmitField("Register")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")
