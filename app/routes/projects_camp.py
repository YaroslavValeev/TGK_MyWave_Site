"""
Blueprint для страницы проекта MyWave Camp Ruza — летний детский лагерь на Рузе.
"""

from flask import Blueprint, render_template, url_for

projects_camp_bp = Blueprint("projects_camp", __name__)


@projects_camp_bp.get("/projects/camp-ruza")
def camp_ruza_page():
    """Страница проекта MyWave Camp Ruza."""
    base_url = url_for("projects_camp.camp_ruza_page", _external=True)
    og_image = url_for("static", filename="images/Project/SummerCamp/SummerCampKids1.png", _external=True)
    meta = {
        "title": "MyWave Camp Ruza — летний лагерь на Рузе 10–20 лет",
        "description": "Лагерь на Рузском водохранилище: wakesurf за Wakeflot, проживание на территории отеля, режим и прогресс. 10–20 лет. Август 2026.",
        "og": {
            "type": "website",
            "title": "MyWave Camp Ruza — летний лагерь на Рузе 10–20 лет",
            "description": "Лагерь на Рузском водохранилище: wakesurf за Wakeflot, проживание на территории отеля, режим и прогресс. 10–20 лет. Август 2026.",
            "image": og_image,
            "url": base_url,
        },
        "twitter": {
            "card": "summary_large_image",
            "title": "MyWave Camp Ruza — летний лагерь на Рузе 10–20 лет",
            "description": "Лагерь на Рузском водохранилище: wakesurf за Wakeflot, проживание на территории отеля, режим и прогресс. 10–20 лет. Август 2026.",
            "image": og_image,
        },
    }
    return render_template("projects/camp_ruza.html", meta=meta)
