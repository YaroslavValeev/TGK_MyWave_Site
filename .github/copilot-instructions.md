# MyWave Project AI Assistant Guide

## Overview

MyWave is a Flask-based multi-feature sports center platform with integrated AI gateway, booking system, Google services integration, and content management. The architecture uses modular Blueprints, service layer isolation, and app factory pattern for flexible configuration.

## Critical Architecture Patterns

### 1. App Initialization (App Factory)

The app is created via `create_app(config_name="development")` in `app/__init__.py` (line 607+):
```python
from app import create_app
app = create_app()  # Returns configured Flask instance

# In tests/conftest: create_app('testing') disables CSRF and reduces logging
```
**New blueprints are registered inside `create_app()`**, not globally. This ensures proper configuration isolation and prevents import-time side effects.

### 2. Project Structure

```
app/
├── __init__.py              # App factory, blueprint registration, middleware
├── config.py                # Configuration classes (Base, Dev, Test, Prod)
├── database/
│   └── models.py            # SQLAlchemy models (User, Booking, Image, etc.)
├── services/                # Business logic (32+ services)
│   ├── booking_service.py
│   ├── google_sheets_service.py
│   ├── google_calendar_service.py
│   ├── ai_router.py         # Chat message routing
│   └── ...
├── routes/                  # Flask Blueprints (30+ route modules)
│   ├── api.py               # Mixed Flask-RESTX and Blueprint endpoints
│   ├── booking_api.py       # Booking API endpoints
│   ├── ai_concierge_api.py  # AI gateway (tools, responses)
│   └── ...
├── modules/                 # Utilities not fitting service model
│   ├── booking_utils.py
│   ├── calendar_integration.py
│   └── logger.py
├── ai/                      # AI gateway components
│   ├── core_gateway.py      # Main AI concierge orchestrator
│   ├── register_tools.py    # Tool registration for OpenAI
│   └── tools_schema.py      # JSON Schema definitions
└── cli/                     # Flask CLI commands
    └── blog_sync.py         # Blog synchronization tasks
```

### 3. Configuration Source Hierarchy

**Config in `config.py` + environment variables**:
1. Base class `Config` defines defaults
2. Environment-specific subclasses: `DevelopmentConfig`, `TestingConfig`, `ProductionConfig`
3. Selected via `create_app(config_name)` arg
4. **Critical**: For development, Google services are **disabled by default** unless `ENABLE_GOOGLE_SERVICES=1`

Key environment variables:
```bash
OPENAI_API_KEY              # Required for chat
GOOGLE_SERVICE_ACCOUNT_FILE # Or path in configs/service_account.json
SPREADSHEET_ID              # Google Sheets (chat history, analytics)
GOOGLE_CALENDAR_ID          # Google Calendar integration
MYWAVE_AI_MODE              # 'mock' (default, local) or 'real' (OpenAI)
FLASK_DEBUG                 # '1' for development mode
```

### 4. Database Models

Core entities in `app/database/models.py`:
```python
User → has many → Booking
User → has many → Image (metadata)
User.email (unique, indexed)
User.role (admin, user, etc.)
```

**Add new models here, then:**
```bash
flask db migrate -m "Add new model"
flask db upgrade  # Apply migration
```

### 5. Blueprint & Route Registration

**Two styles coexist** (refactoring ongoing):
- **Blueprint-based** (preferred): `app.register_blueprint(bp)` with routes via `@bp.route()`
- **Flask-RESTX** (legacy): Namespace classes with `@api.route()`, registered in `api_ns`

Example Blueprint:
```python
# app/routes/my_feature.py
from flask import Blueprint
my_bp = Blueprint('my_feature', __name__, url_prefix='/my')

@my_bp.route('/list', methods=['GET'])
def list_items():
    return jsonify([...])

# Registered in app/__init__.py:
from app.routes.my_feature import my_bp
app.register_blueprint(my_bp)
```

## Service Layer & Business Logic

### Pattern: Service Functions

Always isolate business logic in `app/services/`:
```python
# app/services/booking_service.py
from app.database.models import db, Booking

def create_booking(user_id: int, date: str) -> dict:
    """Validate, create, and persist booking."""
    try:
        booking = Booking(user_id=user_id, date=date)
        db.session.add(booking)
        db.session.commit()
        return {"success": True, "id": booking.id}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}
```

### Key Services (30+ exist)

- **Google integration**: `google_sheets_service`, `google_calendar_service` — read/write Google APIs
- **AI**: `ai_router` (message routing), `openai_service` (OpenAI API calls)
- **Booking**: `booking_service`, `booking_orchestrator` (complex flows)
- **Analytics**: `google_sheets_analytics`, `site_analytics`
- **Content**: `blog/store.py`, `project_content.py` — markdown/sheet-based content

## AI Integration (Dual Mode)

### Mock Mode (Default, Local)

```bash
export MYWAVE_AI_MODE=mock
python main.py
```
Uses `MockOpenAIClient` — simulates tool calls via request string syntax:
```python
# In test payloads:
"message": "__call_tool__:get_available_slots:{}"  # Simulates tool execution
```

### Real Mode (OpenAI)

```bash
export MYWAVE_AI_MODE=real
export OPENAI_API_KEY="sk-..."
python main.py
```
Routes through `app/ai/core_gateway.py`:
- Accepts user message via `POST /api/concierge/message`
- Calls OpenAI with registered tools from `app/ai/register_tools.py`
- Tools defined via JSON Schema in `app/ai/tools_schema.py`

**Tool registration flow**:
1. Define tool schema in `tools_schema.py`
2. Register in `register_tools.py` (maps to handler functions)
3. Handler functions live in route modules (e.g., `booking_api.py`)

## Google Services Integration

### Service Account Setup

Located at: `configs/service_account.json` (or `instance/service_account.json`)

Resolve via:
```python
# app/config.py finds service account:
def find_service_account_file():  # checks multiple paths
    
# Then in app:
from app.services.google_sheets_service import append_to_sheet
append_to_sheet(spreadsheet_id, sheet_name, values)
```

### Critical: Lazy Client Creation

Services create clients **lazily** (on first use, not import) to avoid startup failures when credentials missing:
```python
def _get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=api_key) if api_key else None
```

### Common Workflows

**Read/append chat history**:
```python
from app.services.google_sheets_service import get_history_by_client_id
history = get_history_by_client_id("user-123")  # Returns list of messages
```

**Add calendar event**:
```python
from app.services.google import add_event_to_calendar
add_event_to_calendar(calendar_id, title, start_time, end_time)
```

## Development & Deployment

### Local Development

```bash
python main.py                 # Runs Flask dev server (port 5000)
docker-compose up --build      # Full stack: Nginx (8080) + Gunicorn + Postgres + Redis
```

**Docker setup**: Gunicorn serves on `127.0.0.1:8000`, Nginx proxies `/api/*` and static files, configurable via `GUNICORN_*` env vars in `docker/gunicorn.conf.py`.

### Testing

```bash
pytest                         # All tests
pytest tests/unit/            # Unit only
pytest --cov                   # With coverage
```

**Test fixtures** in `tests/integration/conftest.py`:
```python
@pytest.fixture
def app():
    return create_app('testing')  # CSRF disabled, minimal logging

@pytest.fixture
def client(app):
    return app.test_client()
```

### Key Commands

```bash
flask db migrate -m "message"  # Generate migration
flask db upgrade              # Apply migrations
flask shell                   # Interactive shell (db, models available)
werkzeug.security.generate_password_hash("pass")  # In shell: hash passwords
```

## Patterns & Conventions

### CSRF Protection

Enabled globally via `CSRFProtect()` (testing mode disables it). Always pass CSRF token in forms/AJAX:
```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}"/>
```

### Error Handling

Errors in routes should:
1. Log via `logger` (auto-configured)
2. Return `jsonify({"error": "message"})` (API) or `render_template()` (pages)

### Logging

Configured in `app/__init__.py` (line 200+):
- **Production**: `INFO` level, noisy libraries throttled
- **Development**: `DEBUG` level

Log via: `import logging; logger = logging.getLogger(__name__)`

## Debugging Checklist

- **Import errors on startup**: Check `app/__init__.py` line 40+ (blueprint imports); ensure file exists
- **Missing credentials**: Set env vars or place `service_account.json` in `configs/`
- **Google 403 errors**: Service account lacks scope permissions; verify in Google Cloud console
- **CSRF errors in tests**: Use `create_app('testing')` or add `WTF_CSRF_ENABLED=False` to test config
- **Docker issues**: Inspect with `docker-compose logs web` for full stack trace; check volume mounts in `docker-compose.yml`

## Specific File References

- **Main entry**: `app/__init__.py` (create_app function at line 607)
- **Config classes**: `config.py` 
- **Models**: `app/database/models.py` — extend `db.Model`
- **Services example**: `app/services/booking_service.py` (business logic)
- **Routes example**: `app/routes/booking_api.py` (API endpoints)
- **AI gateway**: `app/ai/core_gateway.py` (orchestrator) + `register_tools.py` (tool definitions)
