"""
Формы для регистрации в WakeSurf Challenge 2025.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, TextAreaField, BooleanField, EmailField, TelField
from wtforms.validators import DataRequired, Length, Email, NumberRange, Optional, ValidationError
from app.services.projects.validation import (
    validate_phone, validate_email, validate_birth_year,
    normalize_phone, check_duplicate_email, check_duplicate_phone
)


class ParticipantRegistrationForm(FlaskForm):
    """Форма регистрации участника."""
    
    full_name = StringField(
        'ФИО',
        validators=[
            DataRequired(message="ФИО обязательно для заполнения"),
            Length(min=2, max=100, message="ФИО должно быть от 2 до 100 символов")
        ],
        render_kw={"placeholder": "Иванов Иван Иванович"}
    )
    
    birth_year = IntegerField(
        'Год рождения',
        validators=[
            DataRequired(message="Год рождения обязателен"),
            NumberRange(min=1930, max=2016, message="Год рождения должен быть от 1930 до 2016")
        ],
        render_kw={"placeholder": "1990"}
    )
    
    phone = TelField(
        'Телефон',
        validators=[DataRequired(message="Телефон обязателен")],
        render_kw={"placeholder": "+7 (916) 011-71-79"}
    )
    
    email = EmailField(
        'Email',
        validators=[
            DataRequired(message="Email обязателен"),
            Email(message="Неверный формат email")
        ],
        render_kw={"placeholder": "example@mail.com"}
    )
    
    level = SelectField(
        'Уровень',
        choices=[
            ('', 'Выберите уровень'),
            ('Новичок', 'Новичок'),
            ('Средний', 'Средний'),
            ('Продвинутый', 'Продвинутый')
        ],
        validators=[DataRequired(message="Выберите уровень")],
        render_kw={"class": "form-select"}
    )
    
    city = StringField(
        'Город',
        validators=[
            DataRequired(message="Город обязателен"),
            Length(min=2, max=50, message="Название города должно быть от 2 до 50 символов")
        ],
        default="Москва",
        render_kw={"placeholder": "Москва"}
    )
    
    goals = TextAreaField(
        'Цели участия',
        validators=[
            Optional(),
            Length(max=500, message="Цели участия не должны превышать 500 символов")
        ],
        render_kw={"placeholder": "Опишите ваши цели участия в проекте", "rows": 4}
    )
    
    consent_participation = BooleanField(
        'Согласен(на) с условиями участия',
        validators=[DataRequired(message="Необходимо согласие с условиями участия")]
    )
    
    consent_media = BooleanField(
        'Разрешаю использование фото/видео в медиаматериалах проекта',
        validators=[DataRequired(message="Необходимо согласие на использование медиа")]
    )
    
    def validate_phone(self, field):
        """Кастомная валидация телефона."""
        is_valid, error = validate_phone(field.data)
        if not is_valid:
            raise ValidationError(error)
        
        # Проверка дубликата
        from flask import current_app
        if check_duplicate_phone(field.data, current_app.config.get('WSC2025_PARTICIPANTS_SHEET', 'WSC2025_Participants')):
            raise ValidationError("Участник с таким телефоном уже зарегистрирован")
    
    def validate_email(self, field):
        """Кастомная валидация email."""
        is_valid, error = validate_email(field.data)
        if not is_valid:
            raise ValidationError(error)
        
        # Проверка дубликата
        from flask import current_app
        if check_duplicate_email(field.data, current_app.config.get('WSC2025_PARTICIPANTS_SHEET', 'WSC2025_Participants')):
            raise ValidationError("Участник с таким email уже зарегистрирован")
    
    def validate_birth_year(self, field):
        """Кастомная валидация года рождения."""
        if field.data:
            is_valid, error = validate_birth_year(field.data)
            if not is_valid:
                raise ValidationError(error)


class CoachRegistrationForm(FlaskForm):
    """Форма регистрации тренера."""
    
    full_name = StringField(
        'ФИО',
        validators=[
            DataRequired(message="ФИО обязательно для заполнения"),
            Length(min=2, max=100, message="ФИО должно быть от 2 до 100 символов")
        ],
        render_kw={"placeholder": "Иванов Иван Иванович"}
    )
    
    phone = TelField(
        'Телефон',
        validators=[DataRequired(message="Телефон обязателен")],
        render_kw={"placeholder": "+7 (916) 011-71-79"}
    )
    
    email = EmailField(
        'Email',
        validators=[
            DataRequired(message="Email обязателен"),
            Email(message="Неверный формат email")
        ],
        render_kw={"placeholder": "example@mail.com"}
    )
    
    club = StringField(
        'Клуб/школа',
        validators=[
            Optional(),
            Length(max=100, message="Название клуба/школы не должно превышать 100 символов")
        ],
        render_kw={"placeholder": "Название клуба или школы (необязательно)"}
    )
    
    experience_years = IntegerField(
        'Опыт (лет)',
        validators=[
            DataRequired(message="Опыт обязателен"),
            NumberRange(min=0, max=40, message="Опыт должен быть от 0 до 40 лет")
        ],
        render_kw={"placeholder": "5"}
    )
    
    portfolio_url = StringField(
        'Ссылка на видео/портфолио',
        validators=[
            Optional(),
            Length(max=500, message="Ссылка не должна превышать 500 символов")
        ],
        render_kw={"placeholder": "https://youtube.com/..."}
    )
    
    consent_participation = BooleanField(
        'Согласен(на) с условиями участия',
        validators=[DataRequired(message="Необходимо согласие с условиями участия")]
    )
    
    consent_media = BooleanField(
        'Разрешаю использование фото/видео в медиаматериалах проекта',
        validators=[DataRequired(message="Необходимо согласие на использование медиа")]
    )
    
    def validate_phone(self, field):
        """Кастомная валидация телефона."""
        is_valid, error = validate_phone(field.data)
        if not is_valid:
            raise ValidationError(error)
        
        # Проверка дубликата
        from flask import current_app
        if check_duplicate_phone(field.data, current_app.config.get('WSC2025_COACHES_SHEET', 'WSC2025_Coaches')):
            raise ValidationError("Тренер с таким телефоном уже зарегистрирован")
    
    def validate_email(self, field):
        """Кастомная валидация email."""
        is_valid, error = validate_email(field.data)
        if not is_valid:
            raise ValidationError(error)
        
        # Проверка дубликата
        from flask import current_app
        if check_duplicate_email(field.data, current_app.config.get('WSC2025_COACHES_SHEET', 'WSC2025_Coaches')):
            raise ValidationError("Тренер с таким email уже зарегистрирован")

