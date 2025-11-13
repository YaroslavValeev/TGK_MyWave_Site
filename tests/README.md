This tests folder contains unit and integration tests for the Site_MyWave project.

Quick start (PowerShell):

```powershell
# 1) Create and activate virtualenv (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Install requirements
pip install -r requirements.txt

# 3) Run tests
pytest -q
```

Notes:
- Integration tests use the Flask test client and may be tolerant to missing Google Sheets credentials.
- Unit tests avoid DB by exercising in-memory cache metrics in `app.services.recommendations_service`.
