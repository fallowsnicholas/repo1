# fetch_splash_data.py
import requests
import json
import pandas as pd
from datetime import datetime
import gspread
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials
import os

def fetch_and_write_splash_data_to_sheet():
    """
    Fetches MLB player prop data from the Splash Sports API by first finding
    active gamesets and then extracting props from them. This ensures data is
    current and accurate.
    """

    # --- NEW: More targeted data fetching logic ---
    # Instead of hitting the generic /props endpoint, we first find the active "gamesets"
    # for the day, ensuring we only get the most current and relevant props.
    url = "https://api.splashsports.com/props-service/api/gamesets"
    params = {
        'league': 'mlb',
        'status': 'active', # Explicitly ask for active contests
        'limit': 5, # Usually only one or two active gamesets per day
        'offset': 0
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': 'https://app.splashsports.com/',
        'Origin': 'https://app.splashsports.com',
    }

    print("="*80)
    print("STEP 1: FETCHING ACTIVE MLB GAMESETS")
    print("="*80)
    print(f"URL: {url}")
    print(f"Params: {params}")
    print(f"Timestamp: {datetime.now()}")
    print("="*80)

    props_list = []
    df = pd.DataFrame()

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        print("-"*80)

        if response.status_code == 200:
            gamesets_data = response.json()
            active_gamesets = gamesets_data.get('data', [])

            if not active_gamesets:
                print("No active MLB gamesets found at the moment.")
            else:
                # Usually the first gameset is the main one for the day
                # We will aggregate props from all found active gamesets
                print(f"Found {len(active_gamesets)} active gameset(s). Extracting props...")
                for gameset in active_gamesets:
                    # The props are nested inside the gameset object
                    props_from_set = gameset.get('props', [])
                    if props_from_set:
                        print(f"  - Extracted {len(props_from_set)} props from gameset '{gameset.get('title', 'Untitled')}'")
                        props_list.extend(props_from_set)
                
                print(f"\nTotal props extracted from all active gamesets: {len(props_list)}")

                # --- Data Processing ---
                print("CREATING DATAFRAME...")
                extracted_data = []
                for prop in props_list:
                    # We can still add a status check for extra safety
                    if prop.get('status') in ['OPEN', 'SCHEDULED']:
                        extracted_data.append({
                            'name': prop.get('entity_name'),
                            'type': prop.get('type'),
                            'line': prop.get('line')
                        })

                df = pd.DataFrame(extracted_data)
                df = df.rename(columns={'name': 'Name', 'type': 'Market', 'line': 'Line'})

                print("\n" + "="*80)
                print("DATAFRAME PREVIEW (first 5 rows):")
                print("="*80)
                print(df.head())
                print(f"Total rows: {len(df)}")

    except requests.exceptions.RequestException as e:
        print(f"REQUEST ERROR: {e}")
    except Exception as e:
        print(f"UNEXPECTED ERROR during data fetching: {e}")


    # --- Google Sheets Authentication and Writing ---
    if not df.empty:
        print("\n" + "="*80)
        print("STEP 2: WRITING DATA TO GOOGLE SHEETS")
        print("="*80)
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'])
            credentials = Credentials.from_service_account_info(
                service_account_info, scopes=scopes)
            client = gspread.authorize(credentials)

            spreadsheet = client.open("MLB_Splash_Data")
            worksheet = spreadsheet.worksheet("SPLASH_MLB")

            print("Clearing existing data...")
            worksheet.clear()
            
            df_sorted = df.sort_values(by='Market').reset_index(drop=True)
            
            print(f"Writing {len(df_sorted)} rows to Google Sheet...")
            set_with_dataframe(worksheet, df_sorted)
            print("DataFrame successfully written to Google Sheet.")

            print("\n" + "="*80)
            print("TASK COMPLETE")
            print("="*80)

        except Exception as e:
            print(f"\nERROR during Google Sheets operation: {e}")
            raise
    else:
        print("\n" + "="*80)
        print("No active props found to write to Google Sheet. This is not an error.")
        print("Exiting gracefully.")
        print("="*80)

if __name__ == "__main__":
    fetch_and_write_splash_data_to_sheet()

