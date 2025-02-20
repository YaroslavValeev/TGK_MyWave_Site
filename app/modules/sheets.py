from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

def get_sheets_service():
    creds = Credentials.from_service_account_file('credentials.json')
    return build('sheets', 'v4', credentials=creds)

def read_data():
    service = get_sheets_service()
    sheet = service.spreadsheets()
    result = sheet.values().get(
        spreadsheetId='your_spreadsheet_id',
        range='Sheet1!A1:D10'
    ).execute()
    return result.get('values', [])
