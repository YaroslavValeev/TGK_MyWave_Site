import json

try:
    from mcp import server as mserver

    Server = getattr(mserver, "Server", None)
    print(
        json.dumps(
            {
                "Server_exists": bool(Server),
                "Server_repr": repr(Server) if Server else None,
                "module_members": [n for n in dir(mserver) if not n.startswith("__")],
            }
        )
    )
except Exception as e:
    print(json.dumps({"error": str(e)}))
