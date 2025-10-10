"""
Synchronously load mcp_mywave (without triggering __main__) and call server.list_tools/get_capabilities.
"""
import os
import runpy
import json
import inspect
import sys
import asyncio
import traceback

# load .env
ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
if os.path.exists(ENV_PATH):
    with open(ENV_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip()
            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            os.environ.setdefault(k, v)

# Execute mcp_mywave but not as __main__ to avoid starting stdio transport
mod = runpy.run_path(os.path.join(os.path.dirname(__file__), '..', 'mcp_mywave.py'), run_name='mcp_mywave')
server = mod.get('server')
if server is None:
    print('server not found')
    raise SystemExit(1)

print('Server object loaded:', server)

def pretty(obj):
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    except Exception:
        return repr(obj)

if hasattr(server, 'list_tools'):
    try:
        tools = server.list_tools()
        print('\nlist_tools raw result type:', type(tools))
        # If result isn't JSON serializable (contains callables), print readable summary
        if isinstance(tools, (list, tuple)):
            print('\nRegistered tools:')
            for i, t in enumerate(tools):
                try:
                    # Tool may be a function, a descriptor, or a dict-like object
                    if callable(t):
                        print(f"- [{i}] callable: {getattr(t, '__name__', repr(t))}")
                        try:
                            print('  signature:', inspect.signature(t))
                        except Exception:
                            pass
                    else:
                        print(f"- [{i}] {type(t)}: {pretty(t)}")
                except Exception as e:
                    print('  error summarizing tool:', repr(e))
        else:
            print('list_tools:', pretty(tools))
    except Exception as e:
        print('list_tools error:', repr(e))
        traceback.print_exc()

if hasattr(server, 'get_capabilities'):
    try:
        # create initialization options if possible
        try:
            init_opts = server.create_initialization_options()
            # Some implementations expect (notification_options, experimental_capabilities)
            notif = getattr(init_opts, 'notification_options', None)
            exp = getattr(init_opts, 'experimental_capabilities', None)
            caps = server.get_capabilities(notif, exp)
        except Exception:
            # fallback: try calling without args
            caps = server.get_capabilities()
        print('\nget_capabilities:')
        print(pretty(caps))
    except Exception as e:
        print('get_capabilities error:', repr(e))
        traceback.print_exc()

# Inspect server internals for registered tools
print('\nInspecting server._registered_tools (if present)')
reg = getattr(server, '_registered_tools', None)
if reg is None:
    print('No _registered_tools attribute on server')
else:
    print('Found', len(reg), 'registered tool entries')
    for name, fn in reg:
        print('-', name, '->', getattr(fn, '__name__', type(fn)))

# Try calling get_free_slots directly if we can locate the function
target_name = 'get_free_slots'
target_fn = None
if reg:
    for name, fn in reg:
        if name == target_name or getattr(fn, '__name__', '') == target_name:
            target_fn = fn
            break

if target_fn is None:
    # fallback: look for attribute on module
    target_fn = getattr(sys.modules.get('mcp_mywave'), target_name, None)

if target_fn is None:
    print(f"Tool '{target_name}' not found for direct call")
else:
    print(f"Found tool function for '{target_name}':", target_fn)
    try:
        if inspect.iscoroutinefunction(target_fn):
            print('Calling async function with asyncio.run...')
            out = asyncio.run(target_fn('2025-10-07'))
        else:
            out = target_fn('2025-10-07')
        print('\nResult of', target_name, ':')
        print(pretty(out))
    except Exception as e:
        print('Error while calling target tool:', repr(e))
        traceback.print_exc()

print('\nDone')
