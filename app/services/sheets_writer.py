import datetime
from app.services.google import append_to_sheet
from flask import current_app
from app.modules.sheets_access import append_dict_to_sheet

def save_client_to_sheets(
    name=None,
    phone=None,
    email=None,
    telegram_user_id=None,
    level=None,
    created_at=None,
    source=None,
    status=None,
    ref_code=None
):
    """
    Сохраняет клиента в Google Sheets (лист Clients) по заданной структуре.
    Если данных нет — оставляет поле пустым.
    """
    spreadsheet_id = current_app.config["SPREADSHEET_ID"]
    sheet_name = "Clients"
    now = created_at or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [
        "",  # client_id (пусть Google Sheets или бот сгенерирует при необходимости)
        telegram_user_id or "",
        name or "",
        phone or "",
        email or "",
        level or "",
        now,
        source or "web",
        status or "",
        ref_code or "",
        now  # last_active
    ]
    append_to_sheet(spreadsheet_id, sheet_name, [row])

def save_workout_to_sheets(
    workout_id=None, date_time=None, duration=None, location=None, workout_type=None, max_capacity=None, coach_name=None
):
    data = {
        "workout_id": workout_id or "",
        "date_time": date_time or "",
        "duration": duration or "",
        "location": location or "",
        "workout_type": workout_type or "",
        "max_capacity": max_capacity or "",
        "coach_name": coach_name or ""
    }
    append_dict_to_sheet("Workouts", data)

def save_client_workout_to_sheets(
    id=None, client_id=None, workout_id=None, performance=None, feedback=None, payment_type=None, status=None, created_at=None
):
    spreadsheet_id = current_app.config["SPREADSHEET_ID"]
    sheet_name = "Client_Workouts"
    now = created_at or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [
        id or "", client_id or "", workout_id or "", performance or "", feedback or "", payment_type or "", status or "", now
    ]
    append_to_sheet(spreadsheet_id, sheet_name, [row])

def save_subscription_to_sheets(
    subscription_id=None, client_id=None, package_type=None, total_sessions=None, used_sessions=None, purchase_date=None, expiry_date=None, status=None
):
    data = {
        "subscription_id": subscription_id or "",
        "client_id": client_id or "",
        "package_type": package_type or "",
        "total_sessions": total_sessions or "",
        "used_sessions": used_sessions or "",
        "purchase_date": purchase_date or "",
        "expiry_date": expiry_date or "",
        "status": status or ""
    }
    append_dict_to_sheet("Subscriptions", data)

def save_sales_deal_to_sheets(
    deal_id=None, client_id=None, amount=None, deal_type=None, payment_method=None, date_closed=None, remark=None
):
    data = {
        "deal_id": deal_id or "",
        "client_id": client_id or "",
        "amount": amount or "",
        "deal_type": deal_type or "",
        "payment_method": payment_method or "",
        "date_closed": date_closed or "",
        "remark": remark or ""
    }
    append_dict_to_sheet("Sales_Deals", data)

def save_inventory_item_to_sheets(
    item_id=None, item_name=None, condition=None, last_check=None, remarks=None
):
    data = {
        "item_id": item_id or "",
        "item_name": item_name or "",
        "condition": condition or "",
        "last_check": last_check or "",
        "remarks": remarks or ""
    }
    append_dict_to_sheet("Inventory", data)

def save_marketing_campaign_to_sheets(
    campaign_id=None, campaign_name=None, start_date=None, end_date=None, details=None, results=None
):
    data = {
        "campaign_id": campaign_id or "",
        "campaign_name": campaign_name or "",
        "start_date": start_date or "",
        "end_date": end_date or "",
        "details": details or "",
        "results": results or ""
    }
    append_dict_to_sheet("Marketing_Campaigns", data)

def save_bot_event_to_sheets(
    event_id=None, client_id=None, event_type=None, timestamp=None, metadata=None, bot_response=None
):
    data = {
        "event_id": event_id or "",
        "client_id": client_id or "",
        "event_type": event_type or "",
        "timestamp": timestamp or "",
        "metadata": metadata or "",
        "bot_response": bot_response or ""
    }
    append_dict_to_sheet("Bot_Events", data)

def save_script_to_sheets(
    script_id=None, script_name=None, script_type=None, script_text=None, tags=None, last_update=None
):
    data = {
        "script_id": script_id or "",
        "script_name": script_name or "",
        "script_type": script_type or "",
        "script_text": script_text or "",
        "tags": tags or "",
        "last_update": last_update or ""
    }
    append_dict_to_sheet("Scripts_Library", data)

def save_feedback_review_to_sheets(
    review_id=None, client_id=None, rating=None, comment=None, created_at=None, platform=None, is_resolved=None
):
    data = {
        "review_id": review_id or "",
        "client_id": client_id or "",
        "rating": rating or "",
        "comment": comment or "",
        "created_at": created_at or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "platform": platform or "",
        "is_resolved": is_resolved or ""
    }
    append_dict_to_sheet("Feedback_Reviews", data)

def save_schedule_slot_to_sheets(
    day_of_week=None, time=None, max_capacity=None
):
    spreadsheet_id = current_app.config["SPREADSHEET_ID"]
    sheet_name = "Schedule"
    row = [
        day_of_week or "", time or "", max_capacity or ""
    ]
    append_to_sheet(spreadsheet_id, sheet_name, [row]) 