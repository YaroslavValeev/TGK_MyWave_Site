from app import create_app
from app.services.openai_service import ask_with_assistant

app = create_app()
with app.app_context():
    try:
        resp = ask_with_assistant(
            "Привет, представься пожалуйста", client_id="test-client-1"
        )
        print("Assistant response:", resp)
    except Exception as e:
        print("Error calling assistant:", e)
