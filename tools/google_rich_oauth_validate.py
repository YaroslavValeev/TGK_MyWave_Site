#!/usr/bin/env python
"""Validate rendered /events HTML with Google Rich Results Test API using OAuth.

Usage:
 1) Place your OAuth client secret JSON (the one you pasted earlier) somewhere safe, for example: `configs/client_secret.json`.
 2) Ensure the Search Console / Rich Results Test API is enabled in the Google Cloud project tied to the client ID.
 3) Run this script locally (it will open a browser to complete OAuth):

    & "E:/Проекты/MyWave/Site_MyWave/venv/Scripts/Activate.ps1"
    python tools/google_rich_oauth_validate.py --client-secrets configs/client_secret.json

 The script will start a local server to receive the OAuth redirect (default port 52002). After authorization it will POST the rendered HTML to the Rich Results Test API and print the JSON response.

Notes:
- This script is intended to be run on your local machine where you can interactively complete the OAuth consent.
- Do NOT paste client secrets into chat. Keep the file private.
"""
import os
import sys
import json
import argparse
import requests
import socket
from jinja2 import Environment, FileSystemLoader, select_autoescape

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except Exception:
    print(
        "Missing dependency google-auth-oauthlib. Install with: pip install google-auth-oauthlib"
    )
    sys.exit(2)

TEMPLATES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "templates")
)
env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def _url_for(endpoint, **kwargs):
    if endpoint == "static":
        return "/static/" + (kwargs.get("filename") or "")
    if endpoint in ("events", "events_page"):
        return "/events"
    return "/" + endpoint


class _G:
    def __init__(self):
        self.csp_nonce = "VALIDATION_NONCE"


def render_events_html():
    template = env.get_template("events.html")

    def _csrf_token():
        return ""

    return template.render(
        g=_G(), url_for=_url_for, csrf_token=_csrf_token, events=None
    )


def run_oauth_and_validate(client_secrets_path, port=52002, no_auto_port=False):
    # Scopes: Search Console / Webmaster
    scopes = [
        "https://www.googleapis.com/auth/webmasters.readonly",
        "https://www.googleapis.com/auth/webmasters",
    ]

    # Load client secrets and normalize to a config usable by InstalledAppFlow.from_client_config
    with open(client_secrets_path, "r", encoding="utf-8") as fh:
        client_json = json.load(fh)

    # Google client files sometimes have top-level keys 'installed' or 'web'.
    # If it's a 'web' client, copy it to 'installed' for the local flow which avoids
    # needing to create a separate Desktop client in many cases.
    if "installed" in client_json:
        client_config = {"installed": client_json["installed"]}
    elif "web" in client_json:
        client_config = {"installed": client_json["web"].copy()}
        # Ensure redirect_uris contains a localhost entry with the requested port
        redirect_uris = client_config["installed"].get("redirect_uris") or []
        localhost_uri = f"http://localhost:{port}/"
        if localhost_uri not in redirect_uris:
            redirect_uris.append(localhost_uri)
            client_config["installed"]["redirect_uris"] = redirect_uris
    else:
        # Fallback: attempt to pass the file path directly to the library
        client_config = None

    # Create the flow object using a client config when possible so we can run a local server.
    try:
        if client_config is not None:
            flow = InstalledAppFlow.from_client_config(client_config, scopes=scopes)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_path, scopes=scopes
            )

        # Try to open a local server and get credentials. If that fails (access_denied,
        # redirect problems, or environment without browser), fall back to console flow.
        try:
            creds = flow.run_local_server(port=port)
        except Exception as exc:
            print("run_local_server failed:", str(exc))
            if not no_auto_port:
                # Try to find a free port and retry run_local_server there
                try:
                    s = socket.socket()
                    s.bind(("", 0))
                    free_port = s.getsockname()[1]
                    s.close()
                    print(f"Trying run_local_server on free port {free_port}...")
                    creds = flow.run_local_server(port=free_port)
                except Exception as exc2:
                    print("run_local_server on a free port also failed:", str(exc2))
                    print(
                        "Falling back to manual console flow. Follow the printed URL and paste the code here."
                    )
            else:
                print(
                    "Auto port selection is disabled (--no-auto-port). Falling back to manual console flow. Follow the printed URL and paste the code here."
                )
                # Manual console flow: construct auth URL, ask user to visit it and paste code
                auth_url = None
                try:
                    # Flow.authorization_url may return (url, state) or url depending on version
                    maybe = flow.authorization_url(
                        access_type="offline", prompt="consent"
                    )
                    if isinstance(maybe, tuple):
                        auth_url = maybe[0]
                    else:
                        auth_url = maybe
                except Exception:
                    try:
                        maybe = flow.authorization_url()
                        auth_url = maybe[0] if isinstance(maybe, tuple) else maybe
                    except Exception as e_auth:
                        print(
                            "Cannot build authorization URL automatically:", str(e_auth)
                        )

                if not auth_url:
                    raise RuntimeError(
                        "Unable to build authorization URL for manual flow."
                    )

                print(
                    "\nOpen the following URL in your browser, complete the consent, then paste the authorization code here:\n"
                )
                print(auth_url)

                # Read user input and be tolerant to common paste mistakes:
                # - user may paste the full redirect URL (http://localhost:52002/?code=...)
                # - user may paste the literal 'code=...'
                # - user may have accidentally truncated the value and added trailing dots
                raw = input("\nAuthorization code: ").strip()
                # Be tolerant to many copy/paste mistakes. Examples we handle:
                # - full redirect URL: http://localhost:52002/?code=...&scope=...
                # - only 'code=...'
                # - a console line like 'Authorization code: code=...'
                # - accidental extra punctuation or ellipsis appended
                import re
                from urllib.parse import urlparse, parse_qs

                code = raw
                try:
                    # If user pasted a URL, extract query param first
                    if raw.startswith("http://") or raw.startswith("https://"):
                        q = parse_qs(urlparse(raw).query)
                        code = q.get("code", [raw])[0]
                    else:
                        # Try to find a code=... pattern anywhere in the string
                        m = re.search(r"code=([A-Za-z0-9_\-\/.%]+)", raw)
                        if m:
                            code = m.group(1)
                        else:
                            # As a last resort, try to pull a long token-like substring
                            m2 = re.search(r"([A-Za-z0-9_\-\/.]{20,})", raw)
                            if m2:
                                code = m2.group(1)
                            else:
                                code = raw
                except Exception:
                    code = raw

                # Clean up common artifacts: surrounding quotes, trailing dots, whitespace
                code = code.strip().strip("\"'")
                # Remove trailing ellipsis or sequences of dots or stray asterisks
                code = re.sub(r"[\.\*]+$", "", code)
                # Some services percent-encode characters; accept percent-encoded values as-is
                code = code.strip()

                # Sanity check: code should be non-empty
                if not code:
                    raise RuntimeError("No authorization code was provided.")

                # Show a short masked preview so the user can confirm (no full token printed)
                preview = (code[:6] + "..." + code[-4:]) if len(code) > 12 else code
                print(f"Using authorization code (masked): {preview}")

                # Exchange the code for credentials
                try:
                    flow.fetch_token(code=code)
                    creds = flow.credentials
                except Exception as e_fetch:
                    print("Failed to fetch token using the provided code:", e_fetch)
                    raise
    except Exception as exc:
        print("Failed to initialize OAuth flow:", str(exc))
        raise

    # Print brief token info for debugging (masked)
    try:
        masked = (
            (creds.token[:10] + "..." + creds.token[-6:])
            if creds.token and len(creds.token) > 20
            else creds.token
        )
        print("Access token (masked):", masked)
        try:
            ti = requests.get(
                "https://www.googleapis.com/oauth2/v3/tokeninfo",
                params={"access_token": creds.token},
                timeout=10,
            )
            print("Tokeninfo HTTP", ti.status_code)
            try:
                print(ti.json())
            except Exception:
                print(ti.text[:1000])
        except Exception as e_ti:
            print("Tokeninfo request failed:", e_ti)
        # Save full token to a local file for manual curl/testing (file created only locally)
        try:
            token_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "tmp_token.txt")
            )
            with open(token_path, "w", encoding="utf-8") as tf:
                tf.write(creds.token or "")
            print(
                f"Full access token saved to: {token_path} (local file, KEEP PRIVATE)"
            )
            # Print a curl command the user can run locally to reproduce the API call
            curl_cmd = (
                "curl -i -X POST 'https://searchconsole.googleapis.com/v1/urlTestingTools/richResults:run' "
                "-H 'Authorization: Bearer {token}' -H 'Content-Type: application/json' "
                "-d '{"
                "html"
                ": "
                "<html><head></head><body>test</body></html>"
                ", "
                "requestScreenshot"
                ": false}'"
            )
            print("\nExample curl (replace {token} with the token from tmp_token.txt):")
            print(curl_cmd)
        except Exception:
            pass
    except Exception:
        pass

    # Build request to Rich Results Test API
    endpoint = "https://searchconsole.googleapis.com/v1/urlTestingTools/richResults:run"

    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json",
    }

    html = render_events_html()

    body = {"html": html, "requestScreenshot": False}

    print("Posting rendered HTML to Google Rich Results Test API...")
    resp = requests.post(endpoint, headers=headers, json=body, timeout=60)

    print("HTTP", resp.status_code)
    # Print response headers for debugging
    try:
        print("Response headers:")
        for k, v in resp.headers.items():
            print(f"{k}: {v}")
    except Exception:
        pass
    try:
        print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
    except Exception:
        print("Non-JSON response:")
        print(resp.text[:4000])


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--client-secrets",
        required=True,
        help="Path to client_secret.json (OAuth client ID)",
    )
    p.add_argument("--port", type=int, default=52002, help="Local redirect port")
    p.add_argument(
        "--no-auto-port",
        action="store_true",
        help="Do not try a free port if the requested port is busy; use manual flow instead",
    )
    args = p.parse_args()

    if not os.path.exists(args.client_secrets):
        print("Client secrets file not found:", args.client_secrets)
        sys.exit(2)

    try:
        run_oauth_and_validate(
            args.client_secrets, port=args.port, no_auto_port=args.no_auto_port
        )
    except Exception as exc:
        print("Validation failed:", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
