"""
Inspect MCP Server tool registration internals: signatures for
_get_cached_tool_definition and current _tool_cache structure.
"""

import inspect
import json

out = {}
try:
    import mcp.server.lowlevel.server as srvmod

    Server = getattr(srvmod, "Server", None)
    out["Server"] = repr(Server)
    inst = Server("inspect")
    out["tool_cache_type"] = type(inst._tool_cache).__name__
    try:
        out["tool_cache_repr"] = repr(inst._tool_cache)[:1000]
    except Exception as e:
        out["tool_cache_repr"] = f"<repr error: {e}>"
    if hasattr(inst, "_get_cached_tool_definition"):
        out["get_cached_tool_def_sig"] = str(
            inspect.signature(inst._get_cached_tool_definition)
        )
        try:
            src = inspect.getsource(inst._get_cached_tool_definition)
            out["get_cached_tool_def_src"] = src.splitlines()[:20]
        except Exception as e:
            out["get_cached_tool_def_src"] = f"<source not available: {e}>"
    else:
        out["get_cached_tool_def"] = "missing"
    # other helpers
    out["has_tool_cache"] = hasattr(inst, "_tool_cache")
    out["members_sample"] = [n for n in dir(inst) if not n.startswith("__")][:80]
except Exception as e:
    out["error"] = str(e)

print(json.dumps(out, indent=2, ensure_ascii=False))
