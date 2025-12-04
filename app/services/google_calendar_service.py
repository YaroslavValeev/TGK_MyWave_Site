import logging
import json
import os
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account
from flask import current_app

logger = logging.getLogger(__name__)

def _get_calendar_service():
    """Get authenticated Google Calendar service."""
    sa_path = current_app.config.get('GOOGLE_SERVICE_ACCOUNT_FILE')
    scopes = current_app.config.get('CALENDAR_SCOPES', ['https://www.googleapis.com/auth/calendar'])

    # Load credentials
    try:
        creds = service_account.Credentials.from_service_account_file(
            sa_path,
            scopes=scopes
        )
    except Exception as e:
        logger.exception("Failed to load service account credentials from %s: %s", sa_path, e)
        raise

    # Attempt to read client_email directly from the JSON file for reliable logging
    client_email = None
    try:
        if sa_path and os.path.exists(sa_path):
            with open(sa_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                client_email = data.get('client_email')
        else:
            logger.warning("Google service account file not found at %s", sa_path)
    except Exception as e:
        logger.debug("Could not read service account file (%s) to extract client_email: %s", sa_path, e)

    logger.info("Calendar credentials: client_email=%s scopes=%s", client_email or getattr(creds, 'service_account_email', None), getattr(creds, 'scopes', None))

    return build('calendar', 'v3', credentials=creds)

def create_event(date: str, time: str, duration_minutes: int = 60) -> dict:
    """Create a calendar event for the given date and time.
    
    Args:
        date: Date in YYYY-MM-DD format
        time: Time in HH:MM format
        duration_minutes: Event duration in minutes (default 60)
    
    Returns:
        Created event dict from Google Calendar API
    """
    service = _get_calendar_service()
    # Support both config keys for backwards compatibility
    calendar_id = current_app.config.get('GOOGLE_CALENDAR_ID') or current_app.config.get('CALENDAR_ID')
    logger.debug("Using calendar_id=%s for event creation", calendar_id)

    # Create start and end times
    start_time = datetime.strptime(f"{date}T{time}", "%Y-%m-%dT%H:%M")
    end_time = start_time + timedelta(minutes=duration_minutes)

    # Build event
    event = {
        'summary': 'Wakesurfing Session',
        'description': 'Booked wakesurfing session',
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'Europe/Moscow',
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'Europe/Moscow',
        },
    }

    try:
        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()
        logger.info("Created calendar event: %s", created_event.get('id'))
        return created_event
    except HttpError as e:
        # Google API errors (403 requiredAccessLevel etc.) — log details for diagnosis
        status = None
        try:
            status = getattr(e, 'resp', None) and getattr(e.resp, 'status', None)
        except Exception:
            status = None
        content = None
        try:
            content = getattr(e, 'content', None) or getattr(e, 'error_details', None) or str(e)
        except Exception:
            content = str(e)
        logger.error("Failed to create calendar event: HttpError status=%s content=%s", status, content)
        raise
    except Exception as e:
        logger.exception("Failed to create calendar event: %s", e)
        raise

def get_events(start_date: str, end_date: str = None) -> list:
    """Get calendar events between start_date and optional end_date.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format (defaults to start_date)
        
    Returns:
        List of calendar events
    """
    service = _get_calendar_service()
    calendar_id = current_app.config.get('GOOGLE_CALENDAR_ID') or current_app.config.get('CALENDAR_ID')

    # If no end date, search only on start date
    if not end_date:
        end_date = start_date
        
    # Build time bounds
    time_min = f"{start_date}T00:00:00Z"
    time_max = f"{end_date}T23:59:59Z"

    try:
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=100,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        return events_result.get('items', [])
    except Exception as e:
        logger.error(f"Failed to fetch calendar events: {e}")
        return []

def update_event(event_id: str, **updates) -> dict:
    """Update an existing calendar event.
    
    Args:
        event_id: Google Calendar event ID
        **updates: Fields to update (summary, description, etc)
        
    Returns:
        Updated event dict
    """
    service = _get_calendar_service()
    calendar_id = current_app.config.get('GOOGLE_CALENDAR_ID') or current_app.config.get('CALENDAR_ID')

    try:
        # Get existing event
        event = service.events().get(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()

        # Update fields
        event.update(updates)

        # Send update
        updated_event = service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event
        ).execute()
        
        logger.info(f"Updated calendar event: {event_id}")
        return updated_event
    except Exception as e:
        logger.error(f"Failed to update calendar event: {e}")
        raise

def delete_event(event_id: str) -> bool:
    """Delete a calendar event.
    
    Args:
        event_id: Google Calendar event ID
        
    Returns:
        True if deletion successful, False otherwise
    """
    service = _get_calendar_service()
    calendar_id = current_app.config.get('GOOGLE_CALENDAR_ID') or current_app.config.get('CALENDAR_ID')

    try:
        service.events().delete(
            calendarId=calendar_id,
            eventId=event_id
        ).execute()
        logger.info(f"Deleted calendar event: {event_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete calendar event: {e}")
        return False