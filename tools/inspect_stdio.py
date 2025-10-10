import importlib, inspect

mods = ['mcp.stdio_server', 'mcp.stdio', 'mcp.server.stdio', 'mcp.stdio_client']
for m in mods:
    try:
        mod = importlib.import_module(m)
    except Exception as e:
        print(f'no {m}: {e}')
        continue
    print(f'Imported {m} from', getattr(mod, '__file__', '<built-in>'))
    names = [n for n in dir(mod) if not n.startswith('__')]
    print('members:', ', '.join(names))
    for name in ['run_stdio', 'serve_stdio', 'serve', 'start_stdio', 'run']:
        if hasattr(mod, name):
            print('has', name, '->', getattr(mod, name))
            try:
                print(' sig=', inspect.signature(getattr(mod, name)))
            except Exception:
                pass
    print('---')
print('done')
