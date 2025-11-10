import logging
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2 import service_account
from flask import current_app

logger = logging.getLogger(__name__)

def _get_calendar_service():
    """Get authenticated Google Calendar service."""
    creds = service_account.Credentials.from_service_account_file(
        current_app.config['GOOGLE_SERVICE_ACCOUNT_FILE'],
        scopes=['https://www.googleapis.com/auth/calendar']
    )
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
    calendar_id = current_app.config['GOOGLE_CALENDAR_ID']

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
        logger.info(f"Created calendar event: {created_event['id']}")
        return created_event
    except Exception as e:
        logger.error(f"Failed to create calendar event: {e}")
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
    calendar_id = current_app.config['GOOGLE_CALENDAR_ID']

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
    calendar_id = current_app.config['GOOGLE_CALENDAR_ID']

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
    calendar_id = current_app.config['GOOGLE_CALENDAR_ID']

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