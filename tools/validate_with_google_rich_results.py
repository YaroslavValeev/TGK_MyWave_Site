import os
import sys
import json
import time
import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Load GOOGLE_API_KEY from environment
from pathlib import Path

# Try to load .env if exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parents[1] / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except Exception:
    pass

API_KEY = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GOOGLE_API_KEY'.lower()) or os.environ.get('GOOGLE_API_KEY'.upper())
if not API_KEY:
    API_KEY = os.environ.get('GOOGLE_API_KEY') or os.environ.get('GOOGLE_API_KEY')

if not API_KEY:
    print('ERROR: GOOGLE_API_KEY environment variable not found. Please set it (or add to .env).')
    sys.exit(2)

# Render events.html using jinja (avoid importing Flask app to prevent external init)
TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=select_autoescape(['html','xml']))

def _url_for(endpoint, **kwargs):
    if endpoint == 'static':
        return '/static/' + (kwargs.get('filename') or '')
    if endpoint == 'events' or endpoint == 'events_page':
        return '/events'
    return '/' + endpoint

class _G:
    def __init__(self):
        self.csp_nonce = 'VALIDATION_NONCE'

def render_events_html():
    template = env.get_template('events.html')
    # Provide csrf_token stub
    def _csrf_token():
        return ''
    return template.render(g=_G(), url_for=_url_for, csrf_token=_csrf_token, events=None)

HTML = render_events_html()

# Google Rich Results Test API endpoint
BASE = 'https://searchconsole.googleapis.com/v1'
ENDPOINT = f'{BASE}/urlTestingTools/richResults:run?key={API_KEY}'

headers = {'Content-Type': 'application/json'}

# Try with 'html' field first (API sometimes accepts 'html' or 'code')
bodies = [
    {"html": HTML, "requestScreenshot": False},
    {"code": HTML, "requestScreenshot": False},
    {"url": "http://example.com/events", "requestScreenshot": False}
]

session = requests.Session()

for body in bodies:
    try:
        print('Posting to Google Rich Results Test API with body keys:', list(body.keys()))
        resp = session.post(ENDPOINT, headers=headers, data=json.dumps(body), timeout=30)
    except Exception as e:
        print('Request error:', e)
        continue

    print('HTTP', resp.status_code)
    try:
        data = resp.json()
    except Exception:
        print('Non-JSON response:')
        print(resp.text[:2000])
        continue

    # Print high-level result
    print(json.dumps(data, ensure_ascii=False, indent=2)[:8000])

    # If it's a valid response with 'testStatus' or 'mobileFriendliness' or 'richResults', show verdict
    if 'testStatus' in data or 'richResults' in data:
        print('\n--- Validation output ---')
        print('Test status:', data.get('testStatus'))
        if 'mobileFriendliness' in data:
            print('Mobile friendliness:', data['mobileFriendliness'].get('status'))
        if 'richResults' in data:
            print('Detected result types:', data['richResults'].get('detectedItems'))
        sys.exit(0)
    else:
        print('No richResults/testStatus in response; trying next body...')

print('All attempts failed; see the last response above.')
sys.exit(1)
