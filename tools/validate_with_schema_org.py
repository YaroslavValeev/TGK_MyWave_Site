import os
import sys
import json
import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=select_autoescape(['html','xml']))

def _url_for(endpoint, **kwargs):
    if endpoint == 'static':
        return '/static/' + (kwargs.get('filename') or '')
    if endpoint in ('events', 'events_page'):
        return '/events'
    return '/' + endpoint

class _G:
    def __init__(self):
        self.csp_nonce = 'VALIDATION_NONCE'


def render_events_html():
    template = env.get_template('events.html')
    def _csrf_token():
        return ''
    return template.render(g=_G(), url_for=_url_for, csrf_token=_csrf_token, events=None)

HTML = render_events_html()

ENDPOINT = 'https://validator.schema.org/validate'

print('Posting to schema.org validator...')

# Try JSON body
try:
    resp = requests.post(ENDPOINT, json={'content': HTML}, timeout=30)
    print('HTTP', resp.status_code)
    try:
        data = resp.json()
        print(json.dumps(data, ensure_ascii=False, indent=2)[:8000])
    except Exception:
        print('Non-JSON response (first attempt):')
        print(resp.text[:4000])
except Exception as e:
    print('Request error (first attempt):', e)

# Try form-encoded 'doc'
try:
    resp = requests.post(ENDPOINT, data={'doc': HTML}, timeout=30)
    print('\nHTTP (form) ', resp.status_code)
    try:
        data = resp.json()
        print(json.dumps(data, ensure_ascii=False, indent=2)[:8000])
    except Exception:
        print('Non-JSON response (form attempt):')
        print(resp.text[:4000])
except Exception as e:
    print('Request error (form attempt):', e)

# As fallback, try the web UI via GET with content not possible; print suggestion
print('\nDone. If validator returned HTML, check its output above. If both attempts failed, use web UI at https://validator.schema.org/ or run the Google Rich Results Test web UI at https://search.google.com/test/rich-results')
