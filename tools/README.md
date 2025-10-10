# tools/ README

This folder documents developer helper scripts included in the repository and how to run them safely.

## upload_files.py

Purpose: upload files from `knowledge_base` to the OpenAI Files / Assistant Thread API. Intended as a manual developer utility.

Requirements:
- Python 3.8+
- `pip install -r requirements.txt` (or at minimum `pip install openai python-dotenv`)
- Set `OPENAI_API_KEY` in the environment or in a `.env` file.

Usage:

Dry run (no uploads):

```bash
python upload_files.py --path knowledge_base --folders wakesurfing_tips.txt tricks.txt --dry-run
```

Perform upload (will attempt to talk to OpenAI):

```bash
python upload_files.py --path knowledge_base --folders wakesurfing_tips.txt tricks.txt --upload
```

Notes:
- This script will print the list of files it intends to upload. Use the `--rate` option to increase delays between uploads if you hit rate limits.

## server.js

Purpose: a small Node/Express proxy that demonstrates sending messages to OpenAI Threads / Assistant. This is a standalone Node utility and is NOT used by the Python Flask app.

Requirements:
- Node 16+
- `npm install` (if package.json added). Currently it uses `node-fetch`.
- Environment variables:
  - `OPENAI_API_KEY` - API key for OpenAI
  - `ASSISTANT_ID` - assistant id

Run:

```bash
# Ensure env vars are set, for example in PowerShell
$env:OPENAI_API_KEY = "your_key"
$env:ASSISTANT_ID = "asst_..."
node server.js
```

The script now exits early with a clear error message if required env vars are missing.

### Python server stub (for developers without Node)

If you don't have Node installed or just want a lightweight local stub to test the `/chat` endpoint,
run the Python server stub:

```bash
python tools/server_stub.py
```

The stub listens on `127.0.0.1:5001` by default and accepts `POST /chat` with a JSON body `{ "message": "..." }`.
It responds with a deterministic placeholder reply. This is useful for frontend testing when the Node proxy is unavailable.

## mcp_mywave.py

Purpose: Implements MCP tools for interacting with Google Sheets and Google Calendar (list free slots, book clients, list events). Intended to run with an MCP runner.

Requirements:
- `pip install mcp google-api-python-client google-auth` (see project requirements)
- Environment variables:
  - `GOOGLE_SHEETS_CREDENTIALS` - path to service account JSON
  - `SPREADSHEET_ID` - ID of the sheets document
  - `GOOGLE_CALENDAR_ID` - calendar id

Run with MCP (example):

```bash
# If you have the `mcp` package installed and a runner that reads mcp.config.json
python mcp_mywave.py
```

Or configure your IDE to run with the appropriate env vars (see `mcp.config.json`).

## General recommendations

- Move optional developer tools into `tools/` (done for documentation) so they are clearly separated from runtime web app code.
- Document required environment variables in the repo README.
- Do not commit real credentials (service_account.json) to the repository. Instead reference them via `instance/` or via CI secrets.
