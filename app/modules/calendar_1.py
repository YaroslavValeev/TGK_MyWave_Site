def create_event(calendar_service, event_data):
    try:
        event = calendar_service.events().insert(calendarId='primary', body=event_data).execute()
        return event
    except Exception as e:
        return {"error": str(e)}