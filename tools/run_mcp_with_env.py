"""
Load variables from .env into os.environ (without printing) and run mcp_mywave.py.
This avoids depending on python-dotenv being installed.
"""

import os
import runpy

ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
ENV_PATH = os.path.abspath(ENV_PATH)

if os.path.exists(ENV_PATH):
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip()
            # Remove surrounding quotes if present
            if (v.startswith('"') and v.endswith('"')) or (
                v.startswith("'") and v.endswith("'")
            ):
                v = v[1:-1]
            os.environ.setdefault(k, v)
# Debug: print a small subset of envs we care about so it's clear the loader worked
print("Loaded env: SPREADSHEET_ID=", os.environ.get("SPREADSHEET_ID"))
print(
    "Loaded env: GOOGLE_SHEETS_CREDENTIALS=",
    os.environ.get("GOOGLE_SHEETS_CREDENTIALS"),
)
print("Loaded env: GOOGLE_CALENDAR_ID=", os.environ.get("GOOGLE_CALENDAR_ID"))

# Run the target script in-process so it sees the env vars
runpy.run_path(
    os.path.join(os.path.dirname(__file__), "..", "mcp_mywave.py"), run_name="__main__"
)
