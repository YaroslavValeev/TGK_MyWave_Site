import openai
from telegram import Bot
from telegram.ext import CommandHandler, MessageHandler, Filters, Updater
from flask import request

# Инициализация бота
TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
bot = Bot(token=TELEGRAM_BOT_TOKEN)

def start(update, context):
    """Команда /start для приветствия пользователя"""
    update.message.reply_text('Привет! Я бот, готов помочь.')

def handle_message(update, context):
    """Обработка текста, отправленного пользователем"""
    user_message = update.message.text
    response = get_gpt_response(user_message)  # Получаем ответ от GPT
    update.message.reply_text(response)

def get_gpt_response(user_message):
    """Получаем ответ от GPT (можно подключить ваш сервер для этого)"""
    response = openai.ChatCompletion.create(
        model="gpt-4",  # Можно использовать вашу модель
        messages=[{"role": "system", "content": "Ты эксперт по вейксерфингу."},
                  {"role": "user", "content": user_message}]
    )
    return response['choices'][0]['message']['content']

def run_telegram_bot():
    """Запуск бота для прослушивания сообщений"""
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()

def handle_media(update, context):
    """Обработка медиафайлов, отправленных пользователем"""
    chat_id = update.message.chat_id
    if update.message.photo:
        file = update.message.photo[-1].get_file()  # Получаем последнее фото
        file.download('photo.jpg')  # Сохраняем фото

        # Здесь можно добавить логику обработки фото (например, отправка его в Google Drive)

        update.message.reply_text("Фото успешно загружено!")
    elif update.message.video:
        file = update.message.video.get_file()
        file.download('video.mp4')  # Сохраняем видео

        update.message.reply_text("Видео успешно загружено!")

