import runpy, inspect, os
mod = runpy.run_path(os.path.join(os.path.dirname(__file__), '..', 'mcp_mywave.py'), run_name='mcp_mywave')
server = mod.get('server')
if server is None:
    print('No server')
    raise SystemExit(1)
for n in ['list_tools','get_capabilities','call_tool','call','create_initialization_options']:
    obj = getattr(server, n, None)
    print('\n==', n, '==')
    if obj is None:
        print('NOT FOUND')
        continue
    print('callable:', callable(obj))
    try:
        print('sig:', inspect.signature(obj))
    except Exception as e:
        print('sig: <unknown>', e)
