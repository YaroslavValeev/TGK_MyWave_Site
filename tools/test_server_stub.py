"""Start server_stub in a thread, send POST /chat and print response."""
import subprocess
import time
import requests
import signal
import sys


def run_stub_subprocess():
    # Start the server_stub.py as a subprocess
    proc = subprocess.Popen([sys.executable, 'tools/server_stub.py'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc


if __name__ == '__main__':
    proc = run_stub_subprocess()
    try:
        # give it a moment to start
        time.sleep(0.5)
        r = requests.post('http://127.0.0.1:5001/chat', json={'message': 'hello from test script'})
        print('status', r.status_code)
        print('body', r.json())
    except Exception as e:
        print('error', e)
    finally:
        # terminate subprocess
        try:
            proc.send_signal(signal.SIGINT)
        except Exception:
            proc.terminate()
