Calculator storage format change
================================

Change summary
--------------
The calculator results row format written to Google Sheets was extended to include city and tags.

Old row format:
- ts, phone, inputs, result

New row format:
- ts, phone, city, tags, inputs, result

Sheet name
----------
Calculator results are written to worksheet: `Calculator_Results` (spreadsheet id taken from `app.config['ANALYTICS_SHEET_SPREADSHEET_ID']` or `app.config['SPREADSHEET_ID']`).

Notes for consumers
-------------------
- If you parse existing rows, update parsers to handle the new column positions.
- Tags are saved as a comma-separated string (e.g. "wakesurf, beginner").
- Inputs and result columns contain JSON-encoded strings.

Migration
---------
No DB migration needed (this affects only Google Sheets storage). Update any ETL or downstream parsers accordingly.
