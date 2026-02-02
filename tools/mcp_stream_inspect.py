import inspect
import importlib

low = importlib.import_module("mcp.server.lowlevel.server")
stdio = (
    importlib.import_module("mcp.server.stdio")
    if importlib.util.find_spec("mcp.server.stdio")
    else None
)

print("low module:", getattr(low, "__file__", None))
print("members:", ", ".join([n for n in dir(low) if not n.startswith("__")]))

MOSR = getattr(low, "MemoryObjectReceiveStream", None)
MOSS = getattr(low, "MemoryObjectSendStream", None)
SessionMessage = getattr(low, "SessionMessage", None) or getattr(
    stdio, "SessionMessage", None
)

print("\nMemoryObjectReceiveStream:", MOSR)
if MOSR:
    print("dir(MOSR):", ", ".join([n for n in dir(MOSR) if not n.startswith("__")]))
    for n in dir(MOSR):
        if not n.startswith("__"):
            attr = getattr(MOSR, n)
            if callable(attr):
                try:
                    print("  method", n, inspect.signature(attr))
                except Exception:
                    pass

print("\nMemoryObjectSendStream:", MOSS)
if MOSS:
    print("dir(MOSS):", ", ".join([n for n in dir(MOSS) if not n.startswith("__")]))
    for n in dir(MOSS):
        if not n.startswith("__"):
            attr = getattr(MOSS, n)
            if callable(attr):
                try:
                    print("  method", n, inspect.signature(attr))
                except Exception:
                    pass

print("\nSessionMessage type:", SessionMessage)
if SessionMessage:
    try:
        print("SessionMessage fields / signature:", inspect.signature(SessionMessage))
    except Exception:
        print("SessionMessage signature not available (likely a typing alias)")

print(
    "\nstdio module members:",
    getattr(stdio, "__file__", None) if stdio else "stdio not present",
)
if stdio:
    print(", ".join([n for n in dir(stdio) if not n.startswith("__")]))

print("\nDone")
