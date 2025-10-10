"""
Inspect installed mcp package and Server implementation.
Prints module members and the Server class API (methods/attributes).
"""
import inspect
import importlib
import sys


def try_import(name: str):
    try:
        return importlib.import_module(name)
    except Exception:
        return None


def main():
    mcp = try_import('mcp')
    if not mcp:
        print('ERROR: package "mcp" is not importable')
        sys.exit(1)

    print('mcp module imported from', getattr(mcp, '__file__', '<built-in>'))
    print('mcp members:', ', '.join([n for n in dir(mcp) if not n.startswith('__')]))

    candidates = [
        'mcp.server.lowlevel.server',
        'mcp.server.server',
        'mcp.server',
    ]

    for cand in candidates:
        mod = try_import(cand)
        if not mod:
            continue
        print('\nImported', cand, 'from', getattr(mod, '__file__', '<unknown>'))
        print('module members:', ', '.join([n for n in dir(mod) if not n.startswith('__')]))
        Server = getattr(mod, 'Server', None)
        print('Server found in', cand, ':', bool(Server))
        if not Server:
            continue

        print('\nServer repr:', repr(Server))
        print('\nPublic Server members:')
        for n in sorted([nm for nm in dir(Server) if not nm.startswith('__')]):
            attr = getattr(Server, n)
            try:
                sig = inspect.signature(attr)
            except Exception:
                sig = None
            print('-', n, '->', 'callable' if callable(attr) else type(attr), 'sig=' + (str(sig) if sig else ''))

        for name in ('run', 'run_stdio', 'run_stdio_async', 'run_async'):
            if hasattr(Server, name):
                fn = getattr(Server, name)
                print('\nServer has attribute', name, 'callable=', callable(fn))
                try:
                    print('  signature:', inspect.signature(fn))
                except Exception:
                    print('  signature: <error>')
                try:
                    print('  iscoroutinefunction:', inspect.iscoroutinefunction(fn))
                except Exception:
                    pass
        break

    # try CLI/stdio candidates
    for cli_mod in ('mcp.cli', 'mcp.server.cli', 'mcp.server.stdio', 'mcp.stdio'):
        cm = try_import(cli_mod)
        if cm:
            print('\nImported CLI/stdio candidate', cli_mod, 'from', getattr(cm, '__file__', '<unknown>'))
            print('members:', ', '.join([n for n in dir(cm) if not n.startswith('__')]))

    print('\nDone')


if __name__ == '__main__':
    main()
