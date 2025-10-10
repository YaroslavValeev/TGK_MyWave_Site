import sys, os
proj = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if proj not in sys.path:
    sys.path.insert(0, proj)
from app import create_app
from app.services.openai_service import ask_with_assistant

app = create_app()
with app.app_context():
    try:
        resp = ask_with_assistant('Привет, представься пожалуйста', client_id='test-client-1')
        print('\n--- Assistant response start ---\n')
        print(resp)
        print('\n--- Assistant response end ---\n')
    except Exception as e:
        print('Error calling assistant:', e)
