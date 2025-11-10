"""
Google configuration and setup
"""
import os

# Google Service Account
GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE', 'instance/service_account.json')

# Spreadsheet settings
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
GOOGLE_SHEET_NAME = os.getenv('GOOGLE_SHEET_NAME', 'Responses')
ANALYTICS_SHEET_NAME = os.getenv('ANALYTICS_SHEET_NAME', 'analytics_statistics')

# Calendar settings
CALENDAR_ID = os.getenv('CALENDAR_ID')
CALENDAR_SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

# Sheets settings
SHEETS_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets'
]