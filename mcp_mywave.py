#!/usr/bin/env python3
"""
mcp_mywave.py
---------------
MCP (Model Context Protocol) tools for the MyWave project.

This module exposes async tools intended to be run by an external MCP runner.
They require Google service account credentials and spreadsheet/calendar IDs
via environment variables. Running this file directly will start a stdio MCP
server (when the `mcp` package is installed).

See `tools/README.md` for instructions on how to run and configure the MCP server.
"""

import os
import json
import asyncio
import datetime as dt
import inspect
from typing import List, Dict, Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# mcp (Model Context Protocol)
try:
    from mcp.server import Server
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "mcp package is required. Install with: pip install mcp"
    ) from exc


# --- Environment configuration ---
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "credentials.json")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
DEFAULT_TZ = os.getenv("MYWAVE_TZ", "Europe/Moscow")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
]


def _require_env(value: str, name: str) -> str:
    # Backwards compatible helper; kept for callers but we prefer graceful check below
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


def _check_required_envs() -> bool:
    """Check required environment variables and print friendly instructions.

    Returns True if all required envs are present, False otherwise.
    """
    missing = []
    if not SERVICE_ACCOUNT_FILE:
        missing.append("GOOGLE_SHEETS_CREDENTIALS (path to service account JSON)")
    if not SPREADSHEET_ID:
        missing.append("SPREADSHEET_ID")
    if not CALENDAR_ID:
        missing.append("GOOGLE_CALENDAR_ID")

    if missing:
        print("❌ Missing required environment variables for mcp_mywave:")
        for m in missing:
            print("  -", m)
        print("\nSet these variables in your environment or provide a .env file. Example (PowerShell):")
        print("  $env:GOOGLE_SHEETS_CREDENTIALS='instance/service_account.json'")
        print("  $env:SPREADSHEET_ID='your_spreadsheet_id'")
        print("  $env:GOOGLE_CALENDAR_ID='your_calendar_id'")
        return False

    return True


# If required envs are missing, behave gracefully in import-time (tests/imports):
# - If running in a real tool runner (mcp present) we will still fail early at runtime.
# - Otherwise, set up mock minimal services so tools can be imported and inspected.
if not _check_required_envs():
    # If GOOGLE_MOCK or DEBUG is set, provide mock minimal services for imports
    if os.getenv('GOOGLE_MOCK') or os.getenv('DEBUG'):
        class _Mock:
            def spreadsheets(self):
                class S:
                    def values(self):
                        class V:
                            def get(self, *a, **k):
                                class R:
                                    def execute(self):
                                        return {"values": []}
                                return R()
                            def append(self, *a, **k):
                                class R:
                                    def execute(self):
                                        return {"mock": True}
                                return R()
                        return V()
                return S()

        creds = None
        sheets_service = _Mock()
        calendar_service = _Mock()
    else:
        # In normal runs without mocks, we still fail fast to alert the operator
        raise SystemExit(1)
else:
    # --- Google clients ---
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    sheets_service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    calendar_service = build("calendar", "v3", credentials=creds, cache_discovery=False)


# --- MCP server ---
server = Server("mywave")


def register_tool(name: str | None = None):
    """Compatibility decorator to register a tool with the installed MCP Server API.

    Tries several registration APIs in order and falls back to attaching the
    function to server._registered_tools for later inspection.
    """
    def decorator(fn):
        # If server provides the same decorator API used in examples
        try:
            if hasattr(server, "tool"):
                # server.tool may be a decorator factory or a callable
                try:
                    dec = server.tool()
                    return dec(fn)
                except TypeError:
                    # server.tool might itself be the decorator
                    return server.tool(fn)

            # Common alternative names
            if hasattr(server, "register"):
                try:
                    server.register(fn)
                    return fn
                except Exception:
                    pass
            if hasattr(server, "register_tool"):
                try:
                    server.register_tool(fn)
                    return fn
                except Exception:
                    pass
            if hasattr(server, "add_tool"):
                try:
                    server.add_tool(fn)
                    return fn
                except Exception:
                    pass
        except Exception:
            # if introspection itself fails, continue to fallback
            pass

        # fallback: stash on server for manual registration or inspection
        if not hasattr(server, "_registered_tools"):
            server._registered_tools = []
        server._registered_tools.append((name or fn.__name__, fn))
        return fn

    return decorator


def _weekday_name(date_str: str) -> str:
    date_obj = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
    return date_obj.strftime("%A")


def _iso_range_for_date(date_str: str, tz: str) -> Dict[str, str]:
    # Produces RFC3339 timestamps for the entire local date, then convert to UTC with Z suffix
    import pytz

    local = pytz.timezone(tz)
    day = dt.datetime.strptime(date_str, "%Y-%m-%d")
    start_local = local.localize(dt.datetime.combine(day.date(), dt.time.min))
    end_local = local.localize(dt.datetime.combine(day.date(), dt.time.max))
    start_utc = start_local.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")
    end_utc = end_local.astimezone(pytz.utc).isoformat().replace("+00:00", "Z")
    return {"timeMin": start_utc, "timeMax": end_utc}


@register_tool()
async def get_free_slots(date: str) -> Dict[str, Any]:
    """
    Получить список доступных слотов на дату (формат YYYY-MM-DD).
    Сверяется лист Schedule и Client_Workouts.
    """
    try:
        schedule_range = "Schedule!A2:C"
        workouts_range = "Client_Workouts!A2:D"

        schedule_resp = (
            sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range=schedule_range)
            .execute()
        )
        schedule = schedule_resp.get("values", [])

        workouts_resp = (
            sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range=workouts_range)
            .execute()
        )
        workouts = workouts_resp.get("values", [])

        weekday = _weekday_name(date)
        free_slots: List[str] = []
        for row in schedule:
            if not row:
                continue
            # Expect: [weekday, slot, capacity]
            if len(row) < 3:
                continue
            if row[0] != weekday:
                continue
            slot = row[1]
            try:
                capacity = int(row[2])
            except ValueError:
                continue

            booked = 0
            for w in workouts:
                if len(w) < 3:
                    continue
                if w[1] == date and w[2] == slot:
                    booked += 1
            if booked < capacity:
                free_slots.append(slot)

        return {"date": date, "free_slots": free_slots}
    except HttpError as e:  # pragma: no cover
        return {"error": f"Google API error: {e}"}
    except Exception as e:  # pragma: no cover
        return {"error": str(e)}


@register_tool()
async def get_client_info(phone: str) -> Dict[str, Any]:
    """
    Найти клиента по номеру телефона в листе Clients.
    """
    try:
        clients_range = "Clients!A2:C"
        clients = (
            sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range=clients_range)
            .execute()
            .get("values", [])
        )

        normalized_phone = phone.strip().replace(" ", "")
        for c in clients:
            if len(c) < 3:
                continue
            row_phone = str(c[2]).strip().replace(" ", "")
            if normalized_phone in row_phone or row_phone in normalized_phone:
                return {"client_id": c[0], "name": c[1], "phone": c[2]}
        return {"error": "Клиент не найден"}
    except HttpError as e:  # pragma: no cover
        return {"error": f"Google API error: {e}"}
    except Exception as e:  # pragma: no cover
        return {"error": str(e)}


@register_tool()
async def book_training(client_id: str, date: str, slot: str) -> Dict[str, Any]:
    """
    Добавить запись клиента на тренировку (лист Client_Workouts).
    """
    try:
        new_row = [[client_id, date, slot, "BOOKED"]]
        (
            sheets_service.spreadsheets()
            .values()
            .append(
                spreadsheetId=SPREADSHEET_ID,
                range="Client_Workouts!A2:D",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": new_row},
            )
            .execute()
        )
        return {"status": "success", "message": f"Запись создана: {date} {slot}"}
    except HttpError as e:  # pragma: no cover
        return {"error": f"Google API error: {e}"}
    except Exception as e:  # pragma: no cover
        return {"error": str(e)}


@register_tool()
async def get_calendar_events(date: str) -> List[Dict[str, Any]]:
    """
    Получить события в календаре Google на дату.
    """
    try:
        range_kwargs = _iso_range_for_date(date, DEFAULT_TZ)
        events_result = (
            calendar_service.events()
            .list(
                calendarId=CALENDAR_ID,
                timeMin=range_kwargs["timeMin"],
                timeMax=range_kwargs["timeMax"],
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])
        simplified = []
        for e in events:
            simplified.append(
                {
                    "id": e.get("id"),
                    "start": e.get("start", {}),
                    "end": e.get("end", {}),
                    "summary": e.get("summary", ""),
                    "location": e.get("location", ""),
                }
            )
        return simplified
    except HttpError as e:  # pragma: no cover
        return [{"error": f"Google API error: {e}"}]
    except Exception as e:  # pragma: no cover
        return [{"error": str(e)}]


if __name__ == "__main__":
    # Prefer stdio runner helper from the installed mcp package when available.
    # Fallbacks (in order): mcp.server.stdio.stdio_server -> Server.run with
    # MemoryObject streams (if available) -> Server.run with sys.stdin/stdout buffers.
    import inspect as _inspect

    def _run_callable(callable_obj, *args, **kwargs):
        if _inspect.iscoroutinefunction(callable_obj):
            asyncio.run(callable_obj(*args, **kwargs))
        else:
            # sync callable
            callable_obj(*args, **kwargs)

    try:
        # 1) Try stdio helper: mcp.server.stdio.stdio_server
        try:
            from mcp.server import stdio as _mcp_stdio
            if hasattr(_mcp_stdio, 'stdio_server'):
                # stdio_server is a convenience transport that uses the current
                # process' stdin/stdout. It will create and run the Server as needed.
                _run_callable(_mcp_stdio.stdio_server)
                raise SystemExit(0)
        except Exception:
            # not available or failed; continue to next fallback
            pass

        # 2) If Server.run accepts MemoryObject streams, try to use them.
        try:
            from mcp.server.stdio import MemoryObjectReceiveStream, MemoryObjectSendStream
            import sys as _sys

            # create stream wrappers around stdio buffers
            recv = MemoryObjectReceiveStream()
            send = MemoryObjectSendStream()

            run_callable = getattr(server, 'run')
            # server.create_initialization_options may or may not exist
            try:
                init_opts = server.create_initialization_options()
            except Exception:
                init_opts = {}

            # If run is coroutine, run it; otherwise call directly.
            if _inspect.iscoroutinefunction(run_callable):
                asyncio.run(run_callable(recv, send, init_opts))
            else:
                run_callable(recv, send, init_opts)
            raise SystemExit(0)
        except Exception:
            # Fallback to last-resort: pass raw stdio buffers to Server.run
            pass

        # 3) Final fallback: call Server.run with sys.stdin.buffer/sys.stdout.buffer
        if hasattr(server, 'run'):
            import sys as _sys
            run_callable = getattr(server, 'run')
            try:
                init_opts = server.create_initialization_options()
            except Exception:
                init_opts = {}
            if _inspect.iscoroutinefunction(run_callable):
                asyncio.run(run_callable(_sys.stdin.buffer, _sys.stdout.buffer, init_opts))
            else:
                run_callable(_sys.stdin.buffer, _sys.stdout.buffer, init_opts)
        else:
            print('No run method found on Server instance (expected stdio_server or run)')
            raise SystemExit(1)
    except SystemExit:
        raise
    except Exception as e:
        print('Error while starting MCP server:', e)
        raise


