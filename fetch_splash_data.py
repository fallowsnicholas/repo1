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
import random

def fetch_and_write_splash_data_to_sheet():
    """
    Fetches MLB player prop data from the Splash Sports API by first finding
    active gamesets and then extracting props from them. This ensures data is
    current and accurate.
    """

    # --- ENHANCED: Anti-caching measures ---
    url = "https://api.splashsports.com/props-service/api/gamesets"
    
    # Add timestamp and random parameter to bust cache
    current_timestamp = int(time.time() * 1000)  # milliseconds
    random_param = random.randint(10000, 99999)
    
    params = {
        'league': 'mlb',
        'status': 'active',
        'limit': 5,
        'offset': 0,
        '_t': current_timestamp,  # Cache busting timestamp
        '_r': random_param        # Additional randomization
    }
    
    # Enhanced headers with cache control
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://app.splashsports.com/',
        'Origin': 'https://app.splashsports.com',
        'Cache-Control': 'no-cache, no-store, must-revalidate',  # Force fresh data
        'Pragma': 'no-cache',  # HTTP/1.0 cache control
        'Expires': '0',  # Expire immediately
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'cross-site'
    }

    print("="*80)
    print("STEP 1: FETCHING ACTIVE MLB GAMESETS (ENHANCED VERSION)")
    print("="*80)
    print(f"URL: {url}")
    print(f"Params: {params}")
    print(f"Timestamp: {datetime.now()}")
    print(f"Cache-busting timestamp: {current_timestamp}")
    print("="*80)

    props_list = []
    df = pd.DataFrame()

    # Create a session for better connection handling
    session = requests.Session()
    session.headers.update(headers)

    try:
        # Make the request with enhanced parameters
        response = session.get(url, params=params, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers - Cache-Control: {response.headers.get('Cache-Control', 'Not Set')}")
        print(f"Response Headers - Date: {response.headers.get('Date', 'Not Set')}")
        print(f"Response Headers - ETag: {response.headers.get('ETag', 'Not Set')}")
        print("-"*80)

        if response.status_code == 200:
            gamesets_data = response.json()
            active_gamesets = gamesets_data.get('data', [])

            if not active_gamesets:
                print("No active MLB gamesets found at the moment.")
                
                # If no active gamesets, try a fallback approach
                print("\nTrying fallback: Direct props endpoint...")
                fallback_url = "https://api.splashsports.com/props-service/api/props"
                fallback_params = {
                    'league': 'mlb',
                    'status': 'OPEN',
                    'limit': 1000,
                    '_t': current_timestamp + 1000,  # Different timestamp
                    '_r': random_param + 1
                }
                
                fallback_response = session.get(fallback_url, params=fallback_params, timeout=30)
                if fallback_response.status_code == 200:
                    fallback_data = fallback_response.json()
                    props_list = fallback_data.get('data', [])
                    print(f"Fallback found {len(props_list)} props directly")
                else:
                    print(f"Fallback also failed with status: {fallback_response.status_code}")
            else:
                print(f"Found {len(active_gamesets)} active gameset(s). Extracting props...")
                for i, gameset in enumerate(active_gamesets):
                    gameset_props = gameset.get('props', [])
                    gameset_title = gameset.get('title', f'Gameset #{i+1}')
                    gameset_id = gameset.get('id', 'Unknown ID')
                    print(f"  - Gameset: '{gameset_title}' (ID: {gameset_id})")
                    print(f"    Props found: {len(gameset_props)}")
                    
                    if gameset_props:
                        props_list.extend(gameset_props)
                
                print(f"\nTotal props extracted from all active gamesets: {len(props_list)}")

                # --- Enhanced Data Processing with more validation ---
                print("\nCREATING DATAFRAME WITH ENHANCED VALIDATION...")
                extracted_data = []
                current_time = datetime.now()
                
                for prop in props_list:
                    # More comprehensive status checking
                    prop_status = prop.get('status', '').upper()
                    if prop_status in ['OPEN', 'SCHEDULED', 'ACTIVE']:
                        
                        # Additional data validation
                        entity_name = prop.get('entity_name', '').strip()
                        prop_type = prop.get('type', '').strip()
                        line_value = prop.get('line')
                        
                        # Only include props with valid data
                        if entity_name and prop_type and line_value is not None:
                            extracted_data.append({
                                'name': entity_name,
                                'type': prop_type,
                                'line': line_value,
                                'status': prop_status,
                                'prop_id': prop.get('id', ''),
                                'updated_at': prop.get('updated_at', ''),
                                'fetch_time': current_time.strftime('%Y-%m-%d %H:%M:%S')
                            })

                if extracted_data:
                    df = pd.DataFrame(extracted_data)
                    # Keep the original column names for compatibility, but add extra info
                    df_display = df[['name', 'type', 'line']].rename(columns={
                        'name': 'Name', 
                        'type': 'Market', 
                        'line': 'Line'
                    })
                    
                    print("\n" + "="*80)
                    print("DATAFRAME PREVIEW (first 10 rows):")
                    print("="*80)
                    print(df_display.head(10))
                    print(f"Total rows: {len(df_display)}")
                    print(f"Data fetched at: {current_time}")
                    
                    # Show some additional validation info
                    if len(df) > 0:
                        print(f"Status breakdown: {df['status'].value_counts().to_dict()}")
                        print(f"Market types: {len(df['type'].unique())} unique types")
                        print(f"Players: {len(df['name'].unique())} unique players")
                else:
                    print("No valid props found after filtering and validation")
                    df_display = pd.DataFrame()

        else:
            print(f"Request failed with status code: {response.status_code}")
            print(f"Response text: {response.text[:500]}...")

    except requests.exceptions.RequestException as e:
        print(f"REQUEST ERROR: {e}")
    except Exception as e:
        print(f"UNEXPECTED ERROR during data fetching: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
    finally:
        session.close()

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
            
            # Use the display dataframe for sheets (original 3 columns)
            df_sorted = df_display.sort_values(by='Market').reset_index(drop=True)
            
            # Add a timestamp header row
            timestamp_row = [f"Last Updated: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}", "", ""]
            
            print(f"Writing {len(df_sorted)} rows to Google Sheet...")
            
            # Write timestamp first
            worksheet.append_row(timestamp_row)
            worksheet.append_row(["", "", ""])  # Empty row
            
            # Write the data
            set_with_dataframe(worksheet, df_sorted, row=3, include_index=False)
            print("DataFrame successfully written to Google Sheet with timestamp.")

            print("\n" + "="*80)
            print("TASK COMPLETE")
            print("="*80)

        except Exception as e:
            print(f"\nERROR during Google Sheets operation: {e}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            raise
    else:
        print("\n" + "="*80)
        print("No active props found to write to Google Sheet.")
        print("This could indicate no games today or API issues.")
        print("="*80)

if __name__ == "__main__":
    fetch_and_write_splash_data_to_sheet()
