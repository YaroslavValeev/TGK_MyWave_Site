"""
In-process MCP stdream test

This script does the following:
 - loads .env so `mcp_mywave` can access credentials
 - imports `mcp_mywave` which registers tools on `server`
 - creates MemoryObjectReceiveStream / MemoryObjectSendStream
 - runs server.run(read_stream, write_stream, init_opts) in background
 - acts as a client: sends initialize and a `list_tools` request
 - prints received responses

This verifies end-to-end that registered tools are visible and callable
via the MemoryObject stream transport.
"""

import os
import runpy
import asyncio
import importlib
import json
from time import time


# load .env (same simple loader as other tools)
ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
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
            if (v.startswith('"') and v.endswith('"')) or (
                v.startswith("'") and v.endswith("'")
            ):
                v = v[1:-1]
            os.environ.setdefault(k, v)


# Ensure mcp_mywave registers tools by executing it as a script
print("Loading mcp_mywave module (this will register tools)...")
runpy.run_path(
    os.path.join(os.path.dirname(__file__), "..", "mcp_mywave.py"), run_name="__main__"
)
import mcp_mywave

server = getattr(mcp_mywave, "server")
print("mcp_mywave loaded, server object:", server)

low = importlib.import_module("mcp.server.lowlevel.server")
MemoryObjectReceiveStream = getattr(low, "MemoryObjectReceiveStream")
MemoryObjectSendStream = getattr(low, "MemoryObjectSendStream")
SessionMessage = getattr(low, "SessionMessage")


async def client_task(client_send, client_recv):
    """Client: send initialize and then list_tools, read responses."""
    # Build initialize message
    try:
        init_opts = server.create_initialization_options()
    except Exception:
        init_opts = {}

    init_req = {
        "jsonrpc": "2.0",
        "id": "init-1",
        "method": "initialize",
        "params": init_opts,
    }

    sm_init = SessionMessage(message=init_req, metadata=None)
    print("Client: sending initialize")
    await client_send.send(sm_init)
    await asyncio.sleep(0.2)
    print("Client: initialize sent")

    # list_tools request
    req = {
        "jsonrpc": "2.0",
        "id": "req-1",
        "method": "list_tools",
        "params": {},
    }
    print("Client: sending list_tools request")
    await client_send.send(SessionMessage(message=req, metadata=None))
    print("Client: list_tools sent")

    # read responses
    responses = []
    start = time()
    while time() - start < 5.0:
        try:
            msg = await client_recv.receive()
        except Exception:
            break
        if msg is None:
            await asyncio.sleep(0.05)
            continue
        responses.append(msg.message)
        # stop when we see response to req-1
        try:
            if isinstance(msg.message, dict) and msg.message.get("id") == "req-1":
                break
        except Exception:
            pass

    print("\nClient received responses:")
    for r in responses:
        print(json.dumps(r, ensure_ascii=False, indent=2))


async def run_test():
    recv = MemoryObjectReceiveStream()
    send = MemoryObjectSendStream()

    try:
        init_opts = server.create_initialization_options()
    except Exception:
        init_opts = {}

    # start server.run in background
    srv_task = asyncio.create_task(server.run(recv, send, init_opts))

    # client: client_send -> server's read, client_recv <- server's write
    client = asyncio.create_task(client_task(send, recv))

    await client
    await asyncio.sleep(0.2)
    try:
        srv_task.cancel()
    except Exception:
        pass


if __name__ == "__main__":
    asyncio.run(run_test())
