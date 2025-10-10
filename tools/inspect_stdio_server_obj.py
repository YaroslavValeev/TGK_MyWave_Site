import importlib, inspect
mod = importlib.import_module('mcp.server.stdio')
print('module file:', getattr(mod, '__file__', None))
print('members:', ', '.join([n for n in dir(mod) if not n.startswith('__')]))
stdio_server = getattr(mod, 'stdio_server', None)
print('stdio_server repr:', stdio_server)
if stdio_server:
    print('stdio_server members:', ', '.join([n for n in dir(stdio_server) if not n.startswith('__')]))
    for n in dir(stdio_server):
        if not n.startswith('__'):
            try:
                obj = getattr(stdio_server, n)
                if callable(obj):
                    try:
                        print('fn', n, 'sig=', inspect.signature(obj))
                    except Exception:
                        print('fn', n, 'sig=<unknown>')
                else:
                    print('attr', n, type(obj))
            except Exception as e:
                print('attr', n, 'error', e)
print('done')
