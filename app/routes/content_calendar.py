from flask import Blueprint, render_template, jsonify
import gspread, os
from oauth2client.service_account import ServiceAccountCredentials

bp = Blueprint("content_calendar", __name__, url_prefix="/content")


def get_gsheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    # Используем путь из конфигурации
    from config import Config

    credentials_path = Config.GOOGLE_SERVICE_ACCOUNT_FILE

    if not os.path.exists(credentials_path):
        raise FileNotFoundError(
            f"Файл с учетными данными не найден: {credentials_path}"
        )

    creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_path, scope)
    return gspread.authorize(creds)


def get_events_by_month():
    sheet_name = "events_calendar"
    try:
        ws = get_gsheet().open("MyWave_Parser_News").worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        return {"Июнь": [], "Июль": [], "Август": [], "Сентябрь": [], "Октябрь": []}
    rows = ws.get_all_records()
    months = {"Июнь": [], "Июль": [], "Август": [], "Сентябрь": [], "Октябрь": []}
    for r in rows:
        row = {k.strip().lower(): v for k, v in r.items()}
        month = row.get("month", "").strip().lower()
        for m in months:
            if month == m.lower():
                months[m].append(row)
    return months


@bp.route("/calendar")
def calendar_page():
    return render_template("content_calendar.html")


@bp.route("/events", methods=["GET"])
def events_json():
    ws = get_gsheet().open("MyWave_Parser_News").worksheet("raw_feed")
    rows = ws.get_all_records()
    events = []
    for r in rows:
        row = {k.strip().lower(): v for k, v in r.items()}
        if str(row.get("ingest_status", "")).lower() == "posted":
            events.append(
                {
                    "title": row.get("raw_title", "Без названия"),
                    "start": row.get("created_at"),
                    "color": "#35C0CD",
                }
            )
    return jsonify(events)


@bp.route("/events_list")
def events_list():
    months = get_events_by_month()
    return render_template("events_list.html", months=months)
