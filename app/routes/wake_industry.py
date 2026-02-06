"""
Blueprint «Индустрия вейка»: редиректы на канонический URL чек-листа.
Каноническая страница чек-листа: /projects/contest-org-checklist.
"""

from flask import Blueprint, redirect, url_for

wake_industry_bp = Blueprint("wake_industry", __name__)


@wake_industry_bp.get("/wake-industry")
def wake_industry_page():
    """Редирект на каноническую страницу чек-листа организатора (301)."""
    return redirect(url_for("contest_org_checklist.checklist_page"), code=301)


@wake_industry_bp.get("/wake-industry/download")
def download_checklist_pdf():
    """Редирект на каноническое скачивание PDF (301)."""
    return redirect(url_for("contest_org_checklist.download_checklist_pdf"), code=301)
