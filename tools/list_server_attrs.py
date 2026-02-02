import json
from mcp.server import Server

s = Server("mywave")
print(
    json.dumps(
        {
            "type": str(type(s)),
            "attrs": sorted([n for n in dir(s) if not n.startswith("__")]),
        },
        indent=2,
    )
)
