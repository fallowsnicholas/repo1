# fetch_splash_data.py
import requests
import json
import pandas as pd
from datetime import datetime
import gspread
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials
import os
import time

def fetch_splash_data_with_pagination():
    """
    Fetch data with pagination to ensure we get all results
    """
    url = "https://api.splashsports.com/props-service/api/props"
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
    
    all_props = []
    offset = 0
    limit = 500  # Smaller chunks
    max_requests = 5  # Prevent infinite loops
    requests_made = 0
    
    print("="*80)
    print("FETCHING SPLASH SPORTS API DATA WITH PAGINATION")
    print("="*80)
    
    while requests_made < max_requests:
        params = {
            'limit': limit,
            'offset': offset,
            'league': 'mlb'
        }
        
        print(f"Request {requests_made + 1}: offset={offset}, limit={limit}")
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                props_batch = data.get('data', [])
                
                if not props_batch:
                    print("No more data returned, stopping pagination")
                    break
                
                print(f"Received {len(props_batch)} props in this batch")
                all_props.extend(props_batch)
                
                # If we got less than the limit, we've probably reached the end
                if len(props_batch) < limit:
                    print("Received fewer props than limit, assuming end of data")
                    break
                
                offset += limit
                requests_made += 1
                
                # Rate limiting
                time.sleep(0.5)
                
            else:
                print(f"Error response: {response.status_code}")
                break
                
        except Exception as e:
            print(f"Error in pagination request: {e}")
            break
    
    print(f"Total props collected: {len(all_props)}")
    return all_props

def fetch_and_write_splash_data_to_sheet():
    """
    Fetches MLB player prop data from the Splash Sports API,
    creates a DataFrame with 'name', 'type', and 'line' columns,
    authenticates with Google Sheets using a service account,
    clears the target sheet, and writes the DataFrame to the sheet.
    """
    
    print(f"Starting fetch at: {datetime.now()}")
    
    # Fetch data using pagination approach
    print("Fetching data with pagination...")
    all_props = fetch_splash_data_with_pagination()
    
    if not all_props:
        print("No props data retrieved")
        return None
    
    print(f"Processing {len(all_props)} total props")
    
    # Filter for MLB league (should already be filtered, but double-check)
    mlb_props = [prop for prop in all_props if prop.get('league') == 'mlb']
    print(f"Found {len(mlb_props)} MLB props out of {len(all_props)} total props")
    
    # Show market breakdown for MLB props
    if mlb_props:
        market_breakdown = {}
        for prop in mlb_props:
            market = prop.get('type', 'unknown')
            market_breakdown[market] = market_breakdown.get(market, 0) + 1
        print(f"MLB Market breakdown: {market_breakdown}")
        
    # Extract data for DataFrame
    extracted_data = []
    for prop in mlb_props:
        extracted_data.append({
            'name': prop.get('entity_name'),
            'type': prop.get('type'),
            'line': prop.get('line')
        })

    df = pd.DataFrame(extracted_data)
    df = df.rename(columns={'name': 'Name', 'type': 'Market', 'line': 'Line'})
    
    print(f"DataFrame created with {len(df)} rows")
    print(f"Unique players: {df['Name'].nunique()}")
    print(f"Unique markets: {sorted(df['Market'].unique())}")
    
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

            # Load credentials from environment variable (GitHub Actions)
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
            print("TASK COMPLETE: DATA WRITTEN TO GOOGLE SHEET")
            print(f"Successfully processed {len(df)} MLB props")
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

if __name__ == "__main__":
    fetch_and_write_splash_data_to_sheet()
