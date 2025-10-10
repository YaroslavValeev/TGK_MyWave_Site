import os
from flask import Blueprint, request, jsonify, current_app
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from tenacity import retry, stop_after_attempt, wait_fixed
from app.services.openai_service import ask
from app.database.models import ChatMessage
from app import db
import asyncio

telegram_bp = Blueprint('telegram', __name__, url_prefix='/telegram')

# Инициализация приложения Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start для приветствия пользователя"""
    await update.message.reply_text('Привет! Я бот, готов помочь.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    """Регистрация всех хэндлеров"""
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))

@telegram_bp.route('/webhook', methods=['POST'])
def webhook():
    """Принимаем обновления от Telegram по webhook"""
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return jsonify(ok=True)

@telegram_bp.route('/set_webhook')
def set_webhook():
    """Помощник для установки webhook на стороне Telegram"""
    url = os.getenv("WEBHOOK_URL") + "/telegram/webhook"
    success = asyncio.run(application.bot.set_webhook(url))
    return jsonify(webhook_set=success)

# Инициализация хэндлеров при импорте
init_telegram() 