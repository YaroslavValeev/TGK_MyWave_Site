import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
import re, sys, json

# Render the template using Jinja directly to avoid importing the Flask app
TEMPLATES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "templates")
)
env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


# Provide minimal helpers used by the template: url_for and a fake g with csp_nonce
class _G:
    def __init__(self, nonce="TEST_NONCE"):
        self.csp_nonce = nonce


def _url_for(endpoint, **kwargs):
    # Minimal emulation: static files and 'events' route
    if endpoint == "static":
        return "/static/" + (kwargs.get("filename") or "")
    if endpoint == "events":
        return "/events"
    # fallback: return the endpoint name
    return "/" + endpoint


template = env.get_template("events.html")


def _csrf_token():
    return ""


rendered = template.render(g=_G(), url_for=_url_for, csrf_token=_csrf_token)

m = re.search(
    r'<script\s+type="application/ld\+json"[^>]*>(.*?)</script>', rendered, re.S
)
if not m:
    print("NO_JSON_LD_FOUND")
    sys.exit(2)

js = m.group(1).strip()
print("--- JSON-LD START ---")
print(js)
print("--- JSON-LD END ---")

# validate JSON
try:
    obj = json.loads(js)
    print("JSON parsed OK; items:", len(obj) if isinstance(obj, list) else 1)
    sys.exit(0)
except Exception as e:
    print("JSON parse error:", e)
    sys.exit(3)
