#!/usr/bin/env python3
"""
Quick validator for Google Service Account JSON file.

Checks for required keys and basic formatting of the private key.
Optionally attempts to construct google.oauth2 Credentials if the library is installed.

Usage:
  python tools/validate_service_account.py /path/to/service_account.json
Or rely on environment variable GOOGLE_SERVICE_ACCOUNT_FILE.
"""
import json
import os
import sys

COMMON_PATHS = [
    os.path.join('instance', 'service_account.json'),
    os.path.join('configs', 'service_account.json'),
    os.path.join('config', 'service_account.json'),
    'service_account.json',
]


def find_file(path_arg=None):
    if path_arg and os.path.exists(path_arg):
        return path_arg
    env = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
    if env and os.path.exists(env):
        return env
    for p in COMMON_PATHS:
        if os.path.exists(p):
            return p
    return None


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def basic_checks(info):
    required = ['type', 'project_id', 'private_key', 'client_email', 'private_key_id']
    missing = [k for k in required if k not in info]
    if missing:
        return False, f"Missing keys: {', '.join(missing)}"
    if info.get('type') != 'service_account':
        return False, f"Unexpected credential type: {info.get('type')}. Expected 'service_account'"
    pk = info.get('private_key', '')
    if 'BEGIN PRIVATE KEY' not in pk:
        return False, 'private_key does not look like a PEM block (missing BEGIN PRIVATE KEY)'
    return True, 'Basic checks passed'


def try_construct_credentials(info):
    try:
        from google.oauth2 import service_account
    except Exception as e:
        return False, f"google.oauth2 not available: {e} (install google-auth)"
    try:
        creds = service_account.Credentials.from_service_account_info(info)
        return True, f"Credentials object created (scopes not applied). Service account: {getattr(creds, 'service_account_email', 'unknown')}"
    except Exception as e:
        return False, f"Failed to create Credentials: {e}"


def main():
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    path = find_file(path_arg)
    if not path:
        print('Service account JSON not found. Checked common locations and GOOGLE_SERVICE_ACCOUNT_FILE env var.')
        print('Looked at:', ', '.join(COMMON_PATHS))
        sys.exit(2)

    print(f'Using service account file: {path}')
    try:
        info = load_json(path)
    except Exception as e:
        print('Failed to read/parse JSON:', e)
        sys.exit(3)

    ok, msg = basic_checks(info)
    print('Basic check:', msg)
    if not ok:
        sys.exit(4)

    ok2, msg2 = try_construct_credentials(info)
    print('Credential construction:', msg2)
    if not ok2:
        print('If you intend to use Google APIs, install google-auth (pip install google-auth google-auth-oauthlib google-auth-httplib2)')
        sys.exit(5)

    print('\nService account JSON appears valid for local usage. Next steps:')
    print(' - Ensure the target Spreadsheet is shared with the service account email (client_email).')
    print(' - Set environment variable SPREADSHEET_ID to the target spreadsheet id or add it to app config.')
    print('\nOptional test (requires network & googleapiclient):')
    print('  python -c "from google.oauth2 import service_account; from googleapiclient.discovery import build; creds=service_account.Credentials.from_service_account_file(\'' + path.replace('\\','/') + '\'); svc=build(\'sheets\', \'' + 'v4' + '\', credentials=creds); print(svc.spreadsheets().get(spreadsheetId=\"<SPREADSHEET_ID>\").execute())"')


if __name__ == '__main__':
    main()
