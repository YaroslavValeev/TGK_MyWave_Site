from app import create_app
from app.routes import calendar_routes

app = create_app()
with app.app_context():
    try:
        print('Config SPREADSHEET_ID=', app.config.get('SPREADSHEET_ID'))
        slots = calendar_routes.get_available_slots('2025-11-06')
        print('SLOTS:', slots)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print('Exception:', str(e))
