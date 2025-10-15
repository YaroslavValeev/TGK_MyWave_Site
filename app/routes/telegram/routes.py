import os
from flask import Blueprint, request, jsonify, current_app
from telegram import Update
from typing import Any
try:
    # Import telegram extension classes but avoid building Application at import time
    from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes
except Exception:
    # If telegram libs are not available during scripts or dev, continue with placeholders
    CommandHandler = None
    MessageHandler = None
    filters = None
    ContextTypes = None
from tenacity import retry, stop_after_attempt, wait_fixed
from app.services.openai_service import ask
from app.database.models import ChatMessage
from app import db
import asyncio

telegram_bp = Blueprint('telegram', __name__, url_prefix='/telegram')

# Lazy telegram Application to avoid side-effects on import (scripts, linters)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
application = None

def get_application():
    """Return a lazily-initialized telegram Application or a lightweight dummy.

    This avoids constructing the real Application during module import, which can
    trigger network clients and fail in scripts.
    """
    global application
    if application is not None:
        return application

    token = TELEGRAM_BOT_TOKEN
    if not token:
        # Create a dummy minimal application with expected attributes
        class _DummyApp:
            bot = None
            async def process_update(self, u):
                return None
            def add_handler(self, *args, **kwargs):
                return None

        application = _DummyApp()
        return application

    try:
        # Import Application builder lazily to reduce import-time work
        from telegram.ext import Application
        application = Application.builder().token(token).build()
    except Exception as e:
        import logging
        logging.exception('Failed to initialize Telegram Application: %s', e)
        class _DummyApp:
            bot = None
            async def process_update(self, u):
                return None
            def add_handler(self, *args, **kwargs):
                return None
        application = _DummyApp()

    return application

async def start(update: Update, context: Any):
    """Команда /start для приветствия пользователя"""
    await update.message.reply_text('Привет! Я бот, готов помочь.')

async def handle_message(update: Update, context: Any):
    """Обработка текста, отправленного пользователем"""
    user_message = update.message.text
    chat_id = update.effective_chat.id
    
    # Получаем ответ от GPT через централизованный сервис
    response_text = ask(
        prompt=user_message,
        client_id=str(chat_id),
        source="telegram"
    )
    
    # Отправляем ответ пользователю
    await update.message.reply_text(response_text)
    
    # Сохраняем сообщение в базу данных
    msg = ChatMessage(
        user=update.effective_user.username or str(update.effective_user.id),
        message=user_message,
        reply=response_text,
        blog_post_id=None
    )
    db.session.add(msg)
    db.session.commit()

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def download_file(file, path):
    """Загрузка файла с автоматическими повторными попытками"""
    file.download(path)

async def handle_media(update: Update, context: Any):
    """Обработка медиафайлов, отправленных пользователем"""
    chat_id = update.message.chat_id
    if update.message.photo:
        file = await update.message.photo[-1].get_file()
        download_file(file, 'uploads/photo.jpg')
        await update.message.reply_text("Фото успешно загружено!")
    elif update.message.video:
        file = await update.message.video.get_file()
        download_file(file, 'uploads/video.mp4')
        await update.message.reply_text("Видео успешно загружено!")

def init_telegram():
    """Регистрация всех хэндлеров. Safe to call from application factory."""
    app = get_application()
    try:
        if hasattr(app, 'add_handler') and CommandHandler is not None:
            app.add_handler(CommandHandler("start", start))
        if hasattr(app, 'add_handler') and MessageHandler is not None and filters is not None:
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    except Exception:
        # Don't raise during app init; handlers are optional
        import logging
        logging.exception('Failed to register telegram handlers')

@telegram_bp.route('/webhook', methods=['POST'])
def webhook():
    """Принимаем обновления от Telegram по webhook"""
    app = get_application()
    bot = getattr(app, 'bot', None)
    if bot is None:
        return jsonify(ok=False, error='Telegram bot not initialized'), 503
    update = Update.de_json(request.get_json(force=True), bot)
    asyncio.run(app.process_update(update))
    return jsonify(ok=True)

@telegram_bp.route('/set_webhook')
def set_webhook():
    """Помощник для установки webhook на стороне Telegram"""
    app = get_application()
    bot = getattr(app, 'bot', None)
    if bot is None:
        return jsonify(webhook_set=False, error='Telegram bot not initialized'), 503
    url = os.getenv("WEBHOOK_URL") + "/telegram/webhook"
    success = asyncio.run(bot.set_webhook(url))
    return jsonify(webhook_set=success)

# Handlers should be initialized from the application factory to avoid import side-effects.