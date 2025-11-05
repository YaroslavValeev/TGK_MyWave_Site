from typing import List, Dict, Any

def get_projects() -> List[Dict[str, Any]]:
    """
    Возвращает список проектов с их метаданными.
    В будущем можно заменить на чтение из БД/Sheets.
    """
    return [
        {
            "slug": "wakesurfsafari",
            "title": "WakeSurf Safari",
            "description": "Экспедиционный формат по Волге с обучением вейксерфингу",
            "image": "images/projects/wakesurfsafari/cover.webp",
            "detail": False,
            "tags": ["вейтревел", "мероприятия", "высокий сезон"]
        },
        {
            "slug": "wsc",
            "title": "Wake School Camp",
            "description": "Интенсивный курс обучения вейксерфингу в формате летнего лагеря",
            "image": "images/projects/wsc/cover.webp",
            "detail": True,
            "tags": ["обучение", "интенсив", "лето"]
        }
    ]