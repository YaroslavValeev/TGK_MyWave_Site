# Google integration quick instructions

This project uses a Google Service Account for Sheets/Drive/Calendar integrations.

Quick checklist:

- Create a service account in GCP and download the JSON key file.
- Add the JSON file path to environment variable `GOOGLE_SERVICE_ACCOUNT_FILE`.
- Ensure `SPREADSHEET_ID` and `GOOGLE_CALENDAR_ID` are set in your Flask config or env.
- For local tests you can enable mocks by setting `GOOGLE_MOCK=1`.
- In CI you can set `GOOGLE_SERVICE_ACCOUNT_JSON` to the JSON content (the app will write it to `GOOGLE_SERVICE_ACCOUNT_FILE` during startup).

Usage examples:

PowerShell (local):

```powershell
$env:GOOGLE_SERVICE_ACCOUNT_FILE = "C:\path\to\service_account.json"
$env:SPREADSHEET_ID = "<your-spreadsheet-id>"
python scripts/check_google.py
```

CI (GitHub Actions): set `GOOGLE_SERVICE_ACCOUNT_JSON` as a secret and write it to `GOOGLE_SERVICE_ACCOUNT_FILE` path in workflow before running tests.
