from flask import current_app
import openai
import logging
from app.utils import log_dialog

logger = logging.getLogger(__name__)

def init_openai(app):
    openai.api_key = app.config['OPENAI_API_KEY']

def get_chat_response(message, client_id=None, source="web"):
    try:
        client = openai.OpenAI(api_key=current_app.config['OPENAI_API_KEY'])
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a helpful wakesurfing instructor assistant."},
                {"role": "user", "content": message}
            ]
        )
        reply = response.choices[0].message.content.strip()
        if client_id:
            log_dialog(client_id, source, message, reply)
        return reply
    except Exception as e:
        current_app.logger.error(f"OpenAI API error: {str(e)}")
        raise