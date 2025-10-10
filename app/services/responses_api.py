from flask import Blueprint, request, jsonify, current_app
from app.services.openai_service import get_response, ChatMode
# from app.services.ai_router import get_user_chat_history, save_chat_message  # Удалено из глобального импорта
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
        # сохранить историю
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
            'тренировк': 'training',
            'трюк': 'tricks',
            'польз': 'training',
            'зал': 'training',
            'техник': 'tricks'
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
                response = get_knowledge(knowledge_type)
                if response and not isinstance(response, dict):
                    knowledge.extend(response[:3])  # Берем только первые 3 релевантных отрывка
        
        # Формируем расширенный контекст
        enhanced_context = []
        if knowledge:
            enhanced_context.append({
                "role": "system",
                "content": "Используй эти знания для ответа: " + "\n".join(knowledge)
            })
        
        if context:
            enhanced_context.extend(context)
            
        # Получаем ответ от OpenAI с расширенным контекстом
        response = current_app.openai.ChatCompletion.create(
            model="gpt-4",
            messages=enhanced_context + [{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        return response.choices[0].message['content']
        
    except Exception as e:
        current_app.logger.error(f"Error generating response: {str(e)}")
        return "Извините, произошла ошибка. Попробуйте переформулировать вопрос."
