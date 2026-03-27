"""
Blueprint для страницы «Чек-лист для организатора соревнований».
Канонический URL: /projects/contest-org-checklist.
"""

from flask import Blueprint, render_template, url_for, request, Response
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

contest_org_checklist_bp = Blueprint("contest_org_checklist", __name__)

try:
    from weasyprint import HTML as WeasyHTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    logger.warning("WeasyPrint не установлен. PDF генерация будет недоступна.")


@contest_org_checklist_bp.get("/projects/contest-org-checklist")
def checklist_page():
    """Страница чек-листа организатора соревнований (эталонный контент)."""
    return render_template(
        "projects/contest_org_checklist/checklist.html",
        page_title="Чек-лист организатора соревнований",
        page_heading="Чек-лист организатора соревнований",
        page_subheading="Условия для соревнований по вейксерфингу",
        download_pdf_url=url_for("contest_org_checklist.download_checklist_pdf"),
    )


@contest_org_checklist_bp.get("/projects/contest-org-checklist/download")
def download_checklist_pdf():
    """Генерация и скачивание PDF версии чек-листа."""
    if not WEASYPRINT_AVAILABLE:
        # Возвращаем понятную HTML-страницу вместо 500 ошибки
        return render_template(
            "projects/contest_org_checklist/pdf_unavailable.html",
            page_title="PDF временно недоступен",
        ), 503

    try:
        # Формируем base_url для корректного резолвинга статики в PDF
        base_url = request.url_root.rstrip('/') if request else ""
        
        html_content = render_template(
            "projects/contest_org_checklist/checklist_pdf.html",
            base_url=base_url,
        )

        pdf_file = BytesIO()
        WeasyHTML(
            string=html_content, 
            base_url=base_url or None
        ).write_pdf(pdf_file)
        pdf_file.seek(0)

        return Response(
            pdf_file.getvalue(),
            mimetype="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=chek-list-organizatora-sorevnovanij.pdf",
                "Cache-Control": "public, max-age=3600",  # Кэшируем на 1 час
            },
        )
    except Exception as e:
        logger.error("Ошибка генерации PDF: %s", e, exc_info=True)
        # Возвращаем понятную страницу об ошибке вместо JSON с 500
        return render_template(
            "projects/contest_org_checklist/pdf_error.html",
            page_title="Ошибка генерации PDF",
            error_message=str(e),
        ), 500
