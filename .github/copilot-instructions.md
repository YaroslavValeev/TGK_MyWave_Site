# MyWave Project AI Assistant Guide

## Project Overview

MyWave is a Flask-based sports center management system with key features:
- User and booking management
- Event scheduling via Google Calendar integration
- Blog system with AI-powered chat
- Sports analytics and workout tracking
- RESTful API with Swagger documentation

## Architecture Patterns

### 1. Project Structure

- Core application: `app/` using Flask Blueprint architecture
- Database models: `app/database/` using SQLAlchemy ORM
- Business logic: `app/services/` for service layer separation
- Forms: `app/forms/` using WTForms
- API routes: `app/routes/api.py` using Flask-RESTX
- Templates: `templates/` using Jinja2

### 2. Key Integration Points

- Google Services (Calendar, Sheets, Drive):
  ```python
  # Configured via service account JSON at:
  # - instance/service_account.json (preferred)
  # - GOOGLE_SERVICE_ACCOUNT_FILE env var
  ```
- OpenAI Integration:
  ```python
  # Configuration in config/ai_config.py
  # Required env vars: OPENAI_API_KEY, ASSISTANT_ID
  ```

### 3. Database Schema

- Core relationships:
  - `User` ←1:N→ `Booking`
  - `User` ←1:N→ `Workout`
  - `CalendarEvent` ←1:N→ `Booking`
  - `BlogPost` ←1:N→ `ChatMessage`

## Development Workflow

### 1. Local Setup

```bash
# 1. Environment setup
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 2. Configuration
cp .env.sample .env  # Then edit .env with your settings

# 3. Run options
python main.py       # Direct Flask run
docker-compose up    # Docker environment
```

### 2. Testing

```bash
pytest --cov        # Run tests with coverage
pytest tests/unit/  # Unit tests only
```

## Common Patterns

### 1. Service Layer Usage

Always implement business logic in `app/services/` modules:

```python
# Example from app/services/booking_service.py
def create_booking(user_id: int, event_id: str) -> Booking:
    # Business logic here
    pass
```

### 2. API Endpoint Structure

Use Flask-RESTX for new API endpoints:

```python
# Pattern in app/routes/api.py
@api.route('/resource')
class ResourceAPI(Resource):
    @api.doc('list_resources')
    @api.marshal_list_with(resource_model)
    def get(self):
        pass
```

### 3. AI Integration

Use the standard chat prompt structure:

```python
# See config/ai_config.py for MYWAVE_CHAT_PROMPT
prompt = f"{MYWAVE_CHAT_PROMPT}\n\nВопрос клиента: {user_message}"
response = get_response(prompt, client_id=None)
```

## Common Tasks

### 1. Adding New Models

1. Create model in `app/database/models.py`
2. Generate migration: `flask db migrate -m "Add new model"`
3. Apply migration: `flask db upgrade`

### 2. Google Calendar Integration

Always use the service layer:

```python
from app.services.calendar_service import create_event
# Instead of direct Google API calls
```

### 3. Form Handling

Use WTForms with CSRF protection:

```python
# Pattern in app/forms/
from flask_wtf import FlaskForm
class MyForm(FlaskForm):
    # Form fields here
```

## Debugging Tips

- Check `instance/` for configuration issues
- Verify Google service account permissions for Calendar/Drive issues
- Use `debug_config.py` for local debug configuration
- Docker logs: `docker-compose logs -f web`
