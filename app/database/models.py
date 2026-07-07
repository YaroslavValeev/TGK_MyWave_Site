from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Index, ForeignKey
from datetime import datetime

# Инициализация db
# (оставляем только здесь, остальные файлы должны импортировать db отсюда)
db = SQLAlchemy()

# --- Пользователь ---
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120))
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(32), nullable=False, default='user')
    bookings = db.relationship('Booking', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# --- Изображения ---
class Image(db.Model):
    """
    Модель для хранения метаданных изображений
    """
    __tablename__ = 'image'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)  # Имя файла с расширением
    orig_filename = db.Column(db.String(255), nullable=False)  # Оригинальное имя файла
    mime_type = db.Column(db.String(128), nullable=False)  # MIME тип
    size = db.Column(db.Integer, nullable=False)  # Размер в байтах
    width = db.Column(db.Integer)  # Ширина в пикселях
    height = db.Column(db.Integer)  # Высота в пикселях
    title = db.Column(db.String(255))  # Название изображения
    alt = db.Column(db.String(255))  # Alt текст
    caption = db.Column(db.Text)  # Подпись к изображению
    group = db.Column(db.String(64), index=True)  # Группа изображений (например, "services", "blog")
    order = db.Column(db.Integer, default=0)  # Порядок в группе
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))  # Кто загрузил
    optimized = db.Column(db.Boolean, default=False)  # Было ли оптимизировано
    format = db.Column(db.String(32))  # Формат изображения
    focal_point = db.Column(db.String(32))  # Точка фокуса для кропа (x,y)
    meta = db.Column(db.JSON)  # Дополнительные метаданные

    def __repr__(self):
        return f'<Image {self.filename}>'

    @property
    def url(self):
        """
        Возвращает URL изображения
        """
        return f'/images/{self.filename}'
        
    @property
    def thumbnail_url(self):
        """
        Возвращает URL миниатюры
        """
        return f'/images/{self.filename}?w=150&h=150'

    @property 
    def srcset(self):
        """
        Возвращает srcset для респонсивных изображений
        """
        sizes = {
            'small': '800w',
            'medium': '1024w',
            'large': '1920w',
            'xlarge': '2560w'
        }
        return ', '.join([
            f'{self.url}?w={int(size)} {desc}'
            for size, desc in sizes.items()
        ])

# --- Аналитика ---
class Analytics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    metric = db.Column(db.String(50), nullable=False)
    value = db.Column(db.Integer, nullable=False)

# --- Календарное событие ---
class CalendarEvent(db.Model):
    __tablename__ = 'calendar_event'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.String(128), unique=True, nullable=False)
    summary = db.Column(db.String(256))
    start = db.Column(db.String(64))
    end = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bookings = db.relationship('Booking', backref='calendar_event', lazy=True)

    @classmethod
    def from_api(cls, api_event):
        return cls(
            event_id=api_event.get('id'),
            summary=api_event.get('summary'),
            start=api_event.get('start', {}).get('dateTime'),
            end=api_event.get('end', {}).get('dateTime')
        )

# --- Бронирование ---
class Booking(db.Model):
    __tablename__ = 'booking'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    date = db.Column(db.String(10), nullable=False, index=True)  # YYYY-MM-DD
    time = db.Column(db.String(5), nullable=False)   # HH:MM
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    event_id = db.Column(db.Integer, db.ForeignKey('calendar_event.id'))
    status = db.Column(db.String(32), nullable=False, default='pending')

# --- Контактная форма ---
class Contact(db.Model):
    __tablename__ = 'contact'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- Блог и чат ---
class BlogPost(db.Model):
    __tablename__ = 'blog_post'
    # Основной ID из Sheets (строка, не Integer)
    id = db.Column(db.String(128), primary_key=True)
    
    # source / идентификация
    source_type = db.Column(db.String(64), nullable=True)
    source_name = db.Column(db.String(128), nullable=True)
    source_url = db.Column(db.Text, nullable=True)
    
    # контент
    title = db.Column(db.String(256), nullable=False)
    slug = db.Column(db.String(320), unique=True, nullable=False, index=True)
    excerpt = db.Column(db.Text, nullable=True)  # lead/teaser
    
    content_md = db.Column(db.Text, nullable=True)  # markdown исходник
    content_html = db.Column(db.Text, nullable=True)  # уже санитайзенный HTML
    # Обратная совместимость: content для старых записей
    content = db.Column(db.Text, nullable=True)
    teaser = db.Column(db.String(500), nullable=True)  # для обратной совместимости
    
    cover_image_url = db.Column(db.Text, nullable=True)
    tags_json = db.Column(db.Text, nullable=True)  # JSON string array
    
    lang = db.Column(db.String(16), nullable=True)
    
    checksum = db.Column(db.String(128), nullable=True, index=True)
    status = db.Column(db.String(64), nullable=True, index=True)
    
    sheet_row_number = db.Column(db.Integer, nullable=True)
    
    published_at = db.Column(db.DateTime, nullable=True, index=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    chat_messages = db.relationship('ChatMessage', backref='blog_post', lazy=True)
    image_id = db.Column(db.Integer, db.ForeignKey('image.id'))  # Обложка поста
    image = db.relationship('Image', backref='blog_posts', lazy=True)

class ChatMessage(db.Model):
    __tablename__ = 'chat_message'
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100), nullable=False, default='bot')
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    blog_post_id = db.Column(db.Integer, db.ForeignKey('blog_post.id'), nullable=True)

# --- Отзывы ---
class Review(db.Model):
    __tablename__ = 'review'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Assistant(db.Model):
    __tablename__ = 'assistant'
    id = db.Column(db.Integer, primary_key=True)
    assistant_id = db.Column(db.String(128), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    model = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# --- Тренировка ---
class Workout(db.Model):
    __tablename__ = 'workout'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.String(10), nullable=False)  # YYYY-MM-DD
    time = db.Column(db.String(5), nullable=False)   # HH:MM
    duration = db.Column(db.Integer, nullable=False, default=60)  # в минутах
    type = db.Column(db.String(50), nullable=False, default='wakesurf')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='workouts')

# --- Документы базы знаний ---
document_tags = db.Table(
    'document_tags',
    db.Column('document_id', db.Integer, db.ForeignKey('documents.id')),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'))
)

class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256), nullable=False)
    content = db.Column(db.Text, nullable=False)
    meta = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    tags = db.relationship('Tag', secondary=document_tags, backref='documents')

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)


# --- Участники и бронирования сафари/маршрутов ---
class Participant(db.Model):
    __tablename__ = 'participant'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(256), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(32))
    level = db.Column(db.String(64))
    route_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bookings = db.relationship('SafariBooking', backref='participant', lazy=True)


class SafariBooking(db.Model):
    __tablename__ = 'safari_booking'
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=False)
    status = db.Column(db.String(32), nullable=False, default='pending')
    start_date = db.Column(db.Date, nullable=False)
    days = db.Column(db.Integer, nullable=False, default=1)
    message = db.Column(db.Text)
    route_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Camp catalog (Projects / Camp) — models in separate module for clarity.
from app.database.camp_models import Camp, CampImportLog, CampLead  # noqa: E402,F401
