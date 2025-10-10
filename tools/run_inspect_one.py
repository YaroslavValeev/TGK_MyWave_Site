import importlib, inspect, sys

candidates = [
    'mcp.server.lowlevel.server',
    'mcp.server.server',
    'mcp.server',
]

for cand in candidates:
    try:
        mod = importlib.import_module(cand)
    except Exception as e:
        print(f'Failed to import {cand}: {e}')
        continue
    print(f'Imported {cand} from', getattr(mod, '__file__', '<unknown>'))
    Server = getattr(mod, 'Server', None)
    print('Server found:', bool(Server))
    if not Server:
        continue
    print('Server repr:', Server)
    attrs = [n for n in dir(Server) if not n.startswith('__')]
    print('Public members count:', len(attrs))
    for name in attrs:
        try:
            a = getattr(Server, name)
            typ = 'callable' if callable(a) else type(a)
            try:
                sig = inspect.signature(a)
            except Exception:
                sig = None
            print('-', name, typ, 'sig=' + (str(sig) if sig else ''))
        except Exception as e:
            print('-', name, 'error reading attr', e)
    # check common run methods
    for rn in ('run', 'run_stdio', 'run_stdio_async', 'run_async'):
        print('has', rn, '=', hasattr(Server, rn))
    break

# also print top-level mcp members
try:
    mcp = importlib.import_module('mcp')
    print('\nmcp module file:', getattr(mcp, '__file__', '<unknown>'))
    print('mcp members sample:', ', '.join([n for n in dir(mcp) if not n.startswith('__')][:80]))
except Exception as e:
    print('Failed to import mcp:', e)

print('\nDone')
