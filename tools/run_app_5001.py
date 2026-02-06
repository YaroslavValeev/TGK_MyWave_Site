import sys, os
# Ensure workspace root is on sys.path
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# Ensure prometheus multiproc dir exists (app expects this env var)
prom_dir = os.path.join(ROOT, 'prometheus_multiproc')
os.makedirs(prom_dir, exist_ok=True)
os.environ['PROMETHEUS_MULTIPROC_DIR'] = prom_dir

# Enable Google services similarly to main.py to keep behavior consistent
os.environ['ENABLE_GOOGLE_SERVICES'] = os.environ.get('ENABLE_GOOGLE_SERVICES', 'False')

from app import create_app

app = create_app()
if __name__ == '__main__':
    pass

if __name__ == '__main__':
    # Run plain Flask app on 127.0.0.1:5001 to avoid socket conflicts
    app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False)
