# debug_sheets_data.py - Debug script to check what's in Google Sheets
"""
Quick diagnostic script to see what data is actually in Google Sheets
Helps debug issues like:
- Dashboard not loading new data
- Old data persisting
- Missing sheets

Usage: python debug_sheets_data.py --sport MLB
"""
import gspread
from google.oauth2.service_account import Credentials
import json
import os
import argparse
from sports_config import get_sport_config

def connect_to_sheets():
    """Connect to Google Sheets"""
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'])
    credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    client = gspread.authorize(credentials)
    return client

def check_sheet_data(client, spreadsheet_name, sheet_name):
    """Check what data is in a specific sheet"""
    try:
        print(f"\n📋 Checking {sheet_name} in {spreadsheet_name}...")

        spreadsheet = client.open(spreadsheet_name)
        worksheet = spreadsheet.worksheet(sheet_name)

        # Get all data
        all_data = worksheet.get_all_values()

        if not all_data:
            print(f"   ❌ EMPTY - No data in {sheet_name}")
            return

        print(f"   ✅ Found {len(all_data)} total rows")

        # Find header row
        header_row = -1
        for i, row in enumerate(all_data):
            if row and any(cell for cell in row if cell and len(str(cell)) > 2):
                # Check if this looks like a header
                if any(indicator in row for indicator in ['Name', 'Player', 'Market', 'Game_ID', 'Away_Team']):
                    header_row = i
                    print(f"   📊 Header row at index {i}: {row[:5]}...")
                    break

        if header_row >= 0:
            data_rows = all_data[header_row + 1:]
            non_empty_rows = [row for row in data_rows if any(cell for cell in row if cell)]
            print(f"   📈 Data rows: {len(non_empty_rows)}")

            if non_empty_rows:
                print(f"   📝 First row sample: {non_empty_rows[0][:3]}...")
                print(f"   📝 Last row sample: {non_empty_rows[-1][:3]}...")

                # Check for timestamps
                for row in all_data[:20]:
                    for cell in row:
                        if 'Fetched' in str(cell) or 'Calculated' in str(cell) or '2025' in str(cell):
                            print(f"   ⏰ Timestamp found: {cell}")
                            break
        else:
            print(f"   ⚠️ Could not identify header row")

    except Exception as e:
        print(f"   ❌ Error checking {sheet_name}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Debug Google Sheets data')
    parser.add_argument('--sport', default='MLB', choices=['MLB', 'NFL', 'WNBA'],
                       help='Sport to check (default: MLB)')
    args = parser.parse_args()

    print(f"🔍 GOOGLE SHEETS DEBUG TOOL")
    print(f"=" * 60)
    print(f"Sport: {args.sport}\n")

    try:
        # Load config
        config = get_sport_config(args.sport)
        spreadsheet_name = config['spreadsheet_name']

        # Connect
        client = connect_to_sheets()
        print(f"✅ Connected to Google Sheets")

        # Check each important sheet
        sheets_to_check = [
            'MATCHUPS',
            f'SPLASH_{args.sport}',
            'ODDS_API',
            'MATCHED_LINES',
            'EV_RESULTS',
            'CORRELATION_PARLAYS'
        ]

        for sheet in sheets_to_check:
            check_sheet_data(client, spreadsheet_name, sheet)

        print(f"\n" + "=" * 60)
        print(f"✅ DEBUG COMPLETE")
        print(f"\nLook for:")
        print(f"   - Empty sheets (should have data after workflow runs)")
        print(f"   - Old timestamps (indicates stale data)")
        print(f"   - Missing sheets (indicates workflow failure)")

    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    main()
