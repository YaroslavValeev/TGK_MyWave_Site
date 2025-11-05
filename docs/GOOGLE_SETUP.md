Google Service Account setup and quick test
=========================================

This file describes how to prepare a Service Account JSON for Google Sheets usage and how to test it locally.

1) Create service account and download JSON
------------------------------------------
- Open Google Cloud Console -> IAM & Admin -> Service accounts.
- Create a new service account and note its email (e.g. mywave-sa@project.iam.gserviceaccount.com).
- Grant no specific roles immediately (you can add Editor/Sheets API roles later if needed).
- Create and download a JSON key for the service account. Save it as `service_account.json`.

2) Place the JSON in the project
-------------------------------
- Recommended paths (project will search these):
  - `instance/service_account.json`
  - `configs/service_account.json`
  - `config/service_account.json`
  - or set environment variable `GOOGLE_SERVICE_ACCOUNT_FILE` to the absolute path.

3) Enable Sheets API and share the spreadsheet
---------------------------------------------
- In Cloud Console -> APIs & Services -> Library enable Google Sheets API for your project.
- Create or use an existing Google Spreadsheet and share it with the service account email (give Editor access).
- Note the spreadsheet id (from the URL): `https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/...`

4) Minimal local validation (no network)
----------------------------------------
- Run the quick validator included in the repository:

  python tools/validate_service_account.py /path/to/service_account.json

  This checks the JSON structure and will attempt to construct `google.oauth2` credentials if `google-auth` is installed.

5) Optional: test Sheets access (network)
-----------------------------------------
- Install dependencies:

  pip install google-auth google-auth-httplib2 google-auth-oauthlib google-api-python-client

- Run quick check (replace `<SPREADSHEET_ID>`):

  python -c "from google.oauth2 import service_account; from googleapiclient.discovery import build; creds=service_account.Credentials.from_service_account_file('instance/service_account.json'); svc=build('sheets','v4',credentials=creds); print(svc.spreadsheets().get(spreadsheetId='<SPREADSHEET_ID>').execute())"

6) Enabling in the app
----------------------
- By default Google services are disabled for non-production runs. To explicitly enable them locally set:

  setx ENABLE_GOOGLE_SERVICES 1   # Windows (PowerShell: $env:ENABLE_GOOGLE_SERVICES = '1')

- Also set the `SPREADSHEET_ID` env var (or in app config) so the app knows which sheet to validate/write to.

7) Troubleshooting
-------------------
- Error `invalid_grant` or "Invalid JWT Signature" usually means the private_key in the JSON is malformed or the file was edited/corrupted. Re-download the JSON from Console.
- If you see `insufficient permissions` when accessing Sheets, make sure the spreadsheet is explicitly shared with the service account email.
- If `google.oauth2` import fails, install `google-auth` packages (see step 5).

If you'd like, I can attempt to run the validator in this workspace (it needs the real JSON file). If you'd rather not place secrets into the repo, run the validator locally and paste the non-sensitive output here.
