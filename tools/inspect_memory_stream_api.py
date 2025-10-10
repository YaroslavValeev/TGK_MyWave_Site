import inspect
from mcp.server import stdio as stdio_mod
print('mcp.server.stdio file:', getattr(stdio_mod, '__file__', None))
for name in ('MemoryObjectReceiveStream','MemoryObjectSendStream','SessionMessage'):
    obj = getattr(stdio_mod, name, None)
    print('\n===', name, '===')
    if obj is None:
        print('NOT FOUND')
        continue
    print('type:', type(obj))
    try:
        print('doc:', (obj.__doc__ or '').splitlines()[0])
    except Exception:
        pass
    try:
        for n in dir(obj):
            if n.startswith('_'):
                continue
            attr = getattr(obj, n)
            if callable(attr):
                try:
                    print('fn', n, 'sig=', inspect.signature(attr))
                except Exception:
                    print('fn', n, 'sig=<unknown>')
            else:
                print('attr', n, 'type', type(attr))
    except Exception as e:
        print('inspect error', e)
print('\nDone')
