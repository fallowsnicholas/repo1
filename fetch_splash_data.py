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
    Fetches MLB player prop data from the Splash Sports API,
    creates a DataFrame with 'name', 'type', and 'line' columns,
    authenticates with Google Sheets using a service account,
    clears the target sheet, and writes the DataFrame to the sheet.
    """

    # --- Data Fetching ---
    url = "https://api.splashsports.com/props-service/api/props"
    params = {
        'limit': 1000,
        'offset': 0,
        'league': 'mlb'
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Referer': 'https://app.splashsports.com/',
        'Origin': 'https://app.splashsports.com',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site'
    }

    print("="*80)
    print("FETCHING SPLASH SPORTS API DATA")
    print("="*80)
    print(f"URL: {url}")
    print(f"Params: {params}")
    print(f"Timestamp: {datetime.now()}")
    print("="*80)

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        print(f"Status Code: {response.status_code}")
        print("-"*80)

        if response.status_code == 200:
            try:
                data = response.json()
                print("JSON RESPONSE RECEIVED.")
                print("CREATING DATAFRAME...")

                props_list = data.get('data', [])

                # *** KEY CHANGE HERE ***
                # Filter for only 'OPEN' props to ensure data accuracy and avoid old/settled lines.
                active_props = [prop for prop in props_list if prop.get('status') == 'OPEN']
                print(f"Found {len(props_list)} total props, filtering down to {len(active_props)} active ('OPEN') props.")


                # Filter for MLB league from the active props
                mlb_props = [prop for prop in active_props if prop.get('league') == 'mlb']
                print(f"Found {len(mlb_props)} active MLB props.")


                extracted_data = []
                for prop in mlb_props:
                    extracted_data.append({
                        'name': prop.get('entity_name'),
                        'type': prop.get('type'),
                        'line': prop.get('line')
                    })

                df = pd.DataFrame(extracted_data)

                # Rename columns
                df = df.rename(columns={'name': 'Name', 'type': 'Market', 'line': 'Line'})

                print("\n" + "="*80)
                print("DATAFRAME PREVIEW (first 5 rows):")
                print("="*80)
                print(df.head())
                print(f"Total rows: {len(df)}")

            except json.JSONDecodeError:
                print("RESPONSE IS NOT JSON:")
                print(f"First 200 characters: {repr(response.text[:200])}")
                return None

        else:
            print(f"ERROR RESPONSE: Status {response.status_code}, Content: {response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"REQUEST ERROR: {e}")
        return None

    except Exception as e:
        print(f"UNEXPECTED ERROR during data fetching: {e}")
        return None

    # --- Google Sheets Authentication and Writing ---
    if df is not None and not df.empty:
        print("\n" + "="*80)
        print("AUTHENTICATING WITH GOOGLE SHEETS USING SERVICE ACCOUNT")
        print("="*80)
        try:
            # Define the scope
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]

            # Load credentials from environment variable
            service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'])

            # Authenticate using the service account info
            credentials = Credentials.from_service_account_info(
                service_account_info, scopes=scopes)

            client = gspread.authorize(credentials)

            spreadsheet_name = "MLB_Splash_Data"
            worksheet_name = "SPLASH_MLB"

            print(f"Opening spreadsheet: '{spreadsheet_name}'")
            spreadsheet = client.open(spreadsheet_name)
            print(f"Opening worksheet: '{worksheet_name}'")
            worksheet = spreadsheet.worksheet(worksheet_name)

            print(f"Clearing existing data in '{worksheet_name}'")
            worksheet.clear()
            print("Existing data cleared.")

            # Sort the DataFrame by the 'Market' column
            df_sorted = df.sort_values(by='Market').reset_index(drop=True)
            print("DataFrame sorted by 'Market' column.")

            print(f"Writing DataFrame to '{worksheet_name}'")
            set_with_dataframe(worksheet, df_sorted)
            print("DataFrame successfully written to Google Sheet.")

            print("\n" + "="*80)
            print("TASK COMPLETE: SPLASH DATA WRITTEN TO GOOGLE SHEET")
            print("="*80)

        except Exception as e:
            print(f"\n" + "="*80)
            print(f"ERROR during Google Sheets operation: {e}")
            print("="*80)
            raise

    else:
        print("\n" + "="*80)
        print("No data to write to Google Sheet.")
        print("="*80)
        raise Exception("No Splash Sports data retrieved")

if __name__ == "__main__":
    fetch_and_write_splash_data_to_sheet()
