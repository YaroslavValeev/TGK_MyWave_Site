from app import create_app
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = create_app()

with app.app_context():
    print("\nПроверка конфигурации:")
    print("-" * 50)
    print(f"SPREADSHEET_ID = {app.config.get('SPREADSHEET_ID')}")
    print(
        f"GOOGLE_SERVICE_ACCOUNT_FILE = {app.config.get('GOOGLE_SERVICE_ACCOUNT_FILE')}"
    )

    print("\nПроверка сервисного аккаунта:")
    print("-" * 50)
    from app.services.google import get_google_services

    try:
        services = get_google_services()
        print("✅ Google сервисы инициализированы успешно")

        # Пробуем получить доступ к таблице
        sheets = services[1]
        result = (
            sheets.spreadsheets()
            .values()
            .get(spreadsheetId=app.config["SPREADSHEET_ID"], range="Schedule!A1:A1")
            .execute()
        )
        print("✅ Доступ к таблице получен успешно")

    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        logger.exception("Подробности ошибки:")
