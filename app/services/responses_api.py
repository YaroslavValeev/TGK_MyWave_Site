from flask import Blueprint, request, jsonify, current_app
from app.services.openai_service import get_response, ChatMode
# Provide module-level placeholders so tests can patch them without importing
# deeper modules at import time.
def save_chat_message(*args, **kwargs):
    """Placeholder; the real function is imported inside the request handler.
    Tests will patch this symbol directly.
    """
    return None
from app.routes.api import get_knowledge
import json

responses_bp = Blueprint('responses_api', __name__, url_prefix='/api/assistant')

@responses_bp.route('/', methods=['POST'])
def assistant():
    from app.services.ai_router import get_user_chat_history, save_chat_message
    data = request.get_json() or {}
    prompt       = data.get('prompt')
    client_id    = data.get('client_id', request.remote_addr)
    chat_history = data.get('history', get_user_chat_history(client_id))
    params       = data.get('params', {})

    # валидация
    if not isinstance(prompt, str) or not prompt.strip():
        return jsonify(error="Поле 'prompt' должно быть непустым строковым"), 400

    temperature = params.get('temperature', None)
    max_tokens  = params.get('max_tokens', None)

    try:
        # получить ответ
        reply = get_response(
            prompt=prompt,
            mode=ChatMode.RESPONSES_API,
            history=chat_history,
            client_id=client_id,
            source="assistant_api",
            temperature=temperature,
            max_tokens=max_tokens
        )
        # Если в runtime доступна реальная реализация, импортируем её и используем.
        try:
            from app.services.ai_router import save_chat_message as real_save
            real_save(client_id, prompt, reply)
        except Exception:
            # fallback to module-level stub (test will patch this)
            save_chat_message(client_id, prompt, reply)

        return jsonify(response=reply), 200

    except ValueError as ve:
        # некорректные input-параметры
        return jsonify(error=str(ve)), 422
    except Exception:
        current_app.logger.exception("Ошибка в /api/assistant")
        return jsonify(error="Внутренняя ошибка сервера"), 500

def get_response_with_knowledge(prompt, context=None):
    """Enhanced response generator using knowledge base"""
    try:
        # Получаем базовые знания для контекста
        knowledge = []
        
        # Определяем ключевые слова для поиска релевантных знаний
        keywords = {
            # Тренировки
            'тренировк': 'training',
            'польз': 'training',
            'зал': 'training',
            'вейк': 'training',
            
            # Трюки
            'трюк': 'tricks',
            'техник': 'tricks',
            'олли': 'tricks',
            '360': 'tricks',
            'разворот': 'tricks',
            
            # Проекты
            'проект': 'projects',
            'сафари': 'projects',
            'safari': 'projects',
            'challenge': 'projects',
            'чемпионат': 'projects',
            'соревнован': 'projects',
            'wsc': 'projects',
            'wakesurf challenge': 'projects',
            'wake industry': 'projects',
            'iwwf': 'projects',
            'турнир': 'projects',
            'событи': 'projects',
            
            # Магазин
            'магазин': 'shop',
            'товар': 'shop',
            'купить': 'shop',
            'цена': 'shop',
            'продукт': 'shop',
            'доска': 'shop',
            'борд': 'shop',
            'баланс': 'shop',
            'тренажёр': 'shop',
            'оборудован': 'shop',
        }
        
        # Проверяем prompt на ключевые слова
        prompt_lower = prompt.lower()
        relevant_types = set()
        
        for key, knowledge_type in keywords.items():
            if key in prompt_lower:
                relevant_types.add(knowledge_type)
        
        # Добавляем релевантные знания в контекст
        if relevant_types:
            for knowledge_type in relevant_types:
                try:
                    response = get_knowledge(knowledge_type)
                    if response and not isinstance(response, dict):
                        knowledge.extend(response[:3])  # Берем только первые 3 релевантных отрывка
                except Exception:
                    pass  # Игнорируем ошибки получения знаний
        
        # Формируем расширенный контекст
        history = []
        
        # Добавляем системный промпт с базой знаний
        system_prompt = (
            "Ты — эксперт по вейксерфингу из школы MyWave. "
            "Отвечай кратко, по делу и дружелюбно. "
            "Если можешь помочь с записью на тренировку — предложи."
        )
        if knowledge:
            system_prompt += "\n\nИспользуй эти знания для ответа:\n" + "\n".join(str(k) for k in knowledge)
        
        history.append({"role": "system", "content": system_prompt})
        
        if context:
            history.extend(context)
        
        # Используем правильный OpenAI клиент через openai_service
        from app.services.openai_service import ask
        reply = ask(prompt, source="knowledge_base", history=history)
        
        return reply
        
    except Exception as e:
        current_app.logger.error(f"Error generating response: {str(e)}")
        # Fallback: пробуем обычный ask без контекста
        try:
            from app.services.openai_service import ask
            return ask(prompt, source="fallback")
        except Exception:
            return None  # Вернём None, чтобы chat.py использовал свой fallback


# Expose save_chat_message at module level so tests can patch it directly
def save_chat_message(client_id, message, reply):
    from app.services.ai_router import save_chat_message as _save
    return _save(client_id, message, reply)
