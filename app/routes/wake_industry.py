"""
Blueprint для страницы "Индустрия вейка" с чеклистом условий для соревнований.
"""

from flask import Blueprint, render_template, Response, jsonify
from io import BytesIO

wake_industry_bp = Blueprint("wake_industry", __name__)

# Опциональный импорт weasyprint
try:
    from weasyprint import HTML

    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False


@wake_industry_bp.get("/wake-industry")
def wake_industry_page():
    """Страница с чеклистом условий для достижения высоких показателей."""
    return render_template("wake_industry/checklist.html")


@wake_industry_bp.get("/wake-industry/download")
def download_checklist_pdf():
    """Генерация и скачивание PDF версии чеклиста."""
    if not WEASYPRINT_AVAILABLE:
        return (
            jsonify(
                {
                    "error": "PDF генерация недоступна. Установите weasyprint: pip install weasyprint"
                }
            ),
            500,
        )

    try:
        # Рендерим HTML для PDF
        html_content = render_template("wake_industry/checklist_pdf.html")

        # Генерируем PDF
        pdf_file = BytesIO()
        HTML(string=html_content).write_pdf(pdf_file)
        pdf_file.seek(0)

        # Возвращаем PDF как ответ
        return Response(
            pdf_file.getvalue(),
            mimetype="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=wake-industry-checklist.pdf"
            },
        )
    except Exception as e:
        from app.modules.logger import get_logger

        logger = get_logger(__name__)
        logger.error(f"Ошибка генерации PDF: {e}", exc_info=True)
        return jsonify({"error": f"Ошибка генерации PDF: {str(e)}"}), 500
