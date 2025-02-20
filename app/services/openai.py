import openai
import logging
from app.utils import log_dialog

logger = logging.getLogger(__name__)

def get_chat_response(message, client_id=None, source="web"):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Ты эксперт по вейксерфингу."},
                {"role": "user", "content": message}
            ]
        )
        reply = response.choices[0].message.content.strip()
        if client_id:
            log_dialog(client_id, source, message, reply)
        return reply
    except Exception as e:
        logger.error(f"OpenAI error: {str(e)}")
        raise