from google.oauth2 import service_account
from google.auth.transport.requests import Request
import sys

p = 'configs/service_account.json'
print('Using credential file:', p)
try:
    creds = service_account.Credentials.from_service_account_file(p, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    print('Loaded credentials; service_account_email:', getattr(creds, 'service_account_email', None))
    try:
        creds.refresh(Request())
        print('REFRESH OK. token length:', len(creds.token or ''))
    except Exception as e:
        print('REFRESH ERROR:', repr(e))
        raise
except Exception as e:
    print('LOAD ERROR:', repr(e))
    sys.exit(1)
