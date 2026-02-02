"""Inspect mcp.server.lowlevel.server.Server and mcp.stdio to find run APIs."""

import inspect
import json

out = {}
try:
    import mcp.server.lowlevel.server as srvmod

    Server = getattr(srvmod, "Server", None)
    out["server_module"] = srvmod.__name__
    out["Server_repr"] = repr(Server)
    out["Server_dir"] = (
        [n for n in dir(Server) if not n.startswith("__")] if Server else None
    )
    # try instantiate
    try:
        inst = Server("inspect")
        out["instance_dir"] = [n for n in dir(inst) if not n.startswith("__")]
    except Exception as e:
        out["instance_error"] = str(e)
except Exception as e:
    out["server_module_error"] = str(e)

try:
    import mcp.stdio as stdiomod

    out["stdio_members"] = [n for n in dir(stdiomod) if not n.startswith("__")]
    # list callables
    out["stdio_callables"] = [
        n for n, v in inspect.getmembers(stdiomod, inspect.isfunction)
    ]
except Exception as e:
    out["stdio_error"] = str(e)

print(json.dumps(out, indent=2, ensure_ascii=False))
