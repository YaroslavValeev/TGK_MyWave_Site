from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class BlogPost(db.Model):
    __tablename__ = 'blog_post'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    teaser = db.Column(db.String(500), nullable=False)
    content = db.Column(db.Text, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    chat_messages = db.relationship('ChatMessage', backref='blog_post', lazy=True)

class ChatMessage(db.Model):
    __tablename__ = 'chat_message'
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(100), nullable=False, default='bot')
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    blog_post_id = db.Column(db.Integer, db.ForeignKey('blog_post.id'), nullable=True) 