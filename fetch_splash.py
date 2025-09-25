# fetch_splash.py - Step 3: Fetch Splash Sports data with anti-bot detection measures
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

def get_random_headers():
    """Generate randomized headers to avoid bot detection"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/119.0.0.0 Safari/537.36'
    ]
    
    accept_languages = [
        'en-US,en;q=0.9',
        'en-US,en;q=0.8,es;q=0.7',
        'en-GB,en;q=0.9',
        'en-US,en;q=0.9,fr;q=0.8',
        'en-CA,en;q=0.9'
    ]
    
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': random.choice(accept_languages),
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://app.splashsports.com/',
        'Origin': 'https://app.splashsports.com',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Sec-Ch-Ua': f'"Google Chrome";v="{random.randint(110, 120)}", "Chromium";v="{random.randint(110, 120)}", ";Not A Brand";v="99"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': random.choice(['"Windows"', '"macOS"', '"Linux"']),
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'DNT': '1'
    }

def random_delay(min_seconds=1, max_seconds=4):
    """Add random delay to mimic human behavior"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)
    return delay

def fetch_splash_data_with_anti_bot():
    """
    Fetch data with anti-bot detection measures including:
    - Randomized headers and user agents
    - Random delays between requests
    - Session persistence
    - Multiple retry attempts with different strategies
    """
    url = "https://api.splashsports.com/props-service/api/props"
    
    # Create a session to maintain cookies/connection
    session = requests.Session()
    
    all_props = []
    offset = 0
    limit = 300  # Smaller chunks to be less suspicious
    max_requests = 8  # Increased attempts
    requests_made = 0
    consecutive_failures = 0
    max_consecutive_failures = 3
    
    print("⚾ STEP 3: FETCHING SPLASH SPORTS DATA (ANTI-BOT MODE)")
    print("=" * 60)
    print("🛡️ Anti-bot measures active:")
    print("   • Randomized headers and user agents")
    print("   • Random delays between requests (1-4s)")
    print("   • Session persistence")
    print("   • Smaller batch sizes")
    print()
    
    while requests_made < max_requests and consecutive_failures < max_consecutive_failures:
        # Generate fresh headers for each request
        headers = get_random_headers()
        
        params = {
            'limit': limit,
            'offset': offset,
            'league': 'mlb'
        }
        
        print(f"🔄 Request {requests_made + 1}: offset={offset}, limit={limit}")
        print(f"   User-Agent: {headers['User-Agent'][:50]}...")
        
        try:
            # Add random delay before request
            delay = random_delay(1, 4)
            print(f"   ⏱️ Delayed {delay:.1f}s to mimic human behavior")
            
            response = session.get(url, params=params, headers=headers, timeout=30)
            print(f"   📡 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                consecutive_failures = 0  # Reset failure counter on success
                
                try:
                    data = response.json()
                    props_batch = data.get('data', [])
                    
                    if not props_batch:
                        print("   ✅ No more data returned, stopping pagination")
                        break
                    
                    print(f"   ✅ Received {len(props_batch)} props in this batch")
                    all_props.extend(props_batch)
                    
                    # If we got less than the limit, we've probably reached the end
                    if len(props_batch) < limit:
                        print("   ✅ Received fewer props than limit, assuming end of data")
                        break
                    
                    offset += limit
                    
                except json.JSONDecodeError as e:
                    print(f"   ❌ JSON decode error: {e}")
                    consecutive_failures += 1
                    
            elif response.status_code == 403:
                consecutive_failures += 1
                print(f"   🚫 403 Forbidden - Bot detection triggered (attempt {consecutive_failures}/{max_consecutive_failures})")
                
                if consecutive_failures < max_consecutive_failures:
                    # Try different strategies for 403 errors
                    print("   🔄 Trying recovery strategies...")
                    
                    # Strategy 1: Longer delay
                    recovery_delay = random.uniform(10, 20)
                    print(f"      • Extended delay: {recovery_delay:.1f}s")
                    time.sleep(recovery_delay)
                    
                    # Strategy 2: Clear session and start fresh
                    session.close()
                    session = requests.Session()
                    print("      • Created new session")
                    
                    # Strategy 3: Reduce batch size
                    limit = max(100, limit // 2)
                    print(f"      • Reduced batch size to: {limit}")
                    
                else:
                    print(f"   ❌ Maximum consecutive 403 errors reached, stopping")
                    break
                    
            elif response.status_code == 429:
                consecutive_failures += 1
                print(f"   ⏳ 429 Rate Limited - Backing off")
                backoff_delay = random.uniform(15, 30)
                print(f"      • Backoff delay: {backoff_delay:.1f}s")
                time.sleep(backoff_delay)
                continue  # Don't increment requests_made for rate limits
                
            else:
                consecutive_failures += 1
                print(f"   ❌ Error response: {response.status_code}")
                print(f"      Response text: {response.text[:200]}...")
                
                if consecutive_failures < max_consecutive_failures:
                    # Wait before retry
                    retry_delay = random.uniform(5, 10)
                    print(f"      • Retry delay: {retry_delay:.1f}s")
                    time.sleep(retry_delay)
                
        except requests.exceptions.Timeout:
            consecutive_failures += 1
            print(f"   ⏰ Request timed out (attempt {consecutive_failures}/{max_consecutive_failures})")
            if consecutive_failures < max_consecutive_failures:
                time.sleep(random.uniform(5, 10))
                
        except requests.exceptions.RequestException as e:
            consecutive_failures += 1
            print(f"   ❌ Request error: {e} (attempt {consecutive_failures}/{max_consecutive_failures})")
            if consecutive_failures < max_consecutive_failures:
                time.sleep(random.uniform(5, 10))
        
        requests_made += 1
    
    # Close session
    session.close()
    
    print(f"\n📊 FETCH COMPLETE:")
    print(f"   Total props collected: {len(all_props)}")
    print(f"   Requests made: {requests_made}")
    print(f"   Consecutive failures: {consecutive_failures}")
    
    if consecutive_failures >= max_consecutive_failures:
        print(f"   ⚠️ Stopped due to persistent bot detection")
    
    return all_props

def fetch_and_write_splash_data_to_sheet():
    """
    Main function: Fetch MLB player prop data with anti-bot measures and write to Google Sheets
    """
    print(f"🕐 Starting fetch at: {datetime.now()}")
    
    # Fetch data using anti-bot approach
    print("🛡️ Fetching data with anti-bot measures...")
    all_props = fetch_splash_data_with_anti_bot()
    
    if not all_props:
        print("❌ No props data retrieved")
        print("💡 Possible solutions:")
        print("   • Try running again later (IP may be temporarily blocked)")
        print("   • Run from different environment (local machine, different cloud)")
        print("   • Consider using proxy services")
        return None
    
    print(f"🔍 Processing {len(all_props)} total props")
    
    # Filter for MLB league (should already be filtered, but double-check)
    mlb_props = [prop for prop in all_props if prop.get('league') == 'mlb']
    print(f"⚾ Found {len(mlb_props)} MLB props out of {len(all_props)} total props")
    
    # Show market breakdown for MLB props
    if mlb_props:
        market_breakdown = {}
        for prop in mlb_props:
            market = prop.get('type', 'unknown')
            market_breakdown[market] = market_breakdown.get(market, 0) + 1
        print(f"📊 MLB Market breakdown: {market_breakdown}")
        
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
    
    print(f"📋 DataFrame created with {len(df)} rows")
    if not df.empty:
        print(f"👥 Unique players: {df['Name'].nunique()}")
        print(f"🏪 Unique markets: {sorted(df['Market'].unique())}")
    
    # --- Google Sheets Authentication and Writing ---
    if df is not None and not df.empty:
        print("\n" + "="*60)
        print("📝 WRITING TO GOOGLE SHEETS")
        print("="*60)
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

            print(f"📊 Opening spreadsheet: '{spreadsheet_name}'")
            spreadsheet = client.open(spreadsheet_name)
            print(f"📋 Opening worksheet: '{worksheet_name}'")
            worksheet = spreadsheet.worksheet(worksheet_name)

            print(f"🧹 Clearing existing data in '{worksheet_name}'")
            worksheet.clear()
            print("✅ Existing data cleared.")

            # Sort the DataFrame by the 'Market' column
            df_sorted = df.sort_values(by='Market').reset_index(drop=True)
            print("📈 DataFrame sorted by 'Market' column.")

            print(f"💾 Writing DataFrame to '{worksheet_name}'")
            set_with_dataframe(worksheet, df_sorted)
            print("✅ DataFrame successfully written to Google Sheet.")

            print("\n" + "="*60)
            print("🎉 TASK COMPLETE: DATA WRITTEN TO GOOGLE SHEET")
            print(f"✅ Successfully processed {len(df)} MLB props")
            print("="*60)

        except Exception as e:
            print(f"\n" + "="*60)
            print(f"❌ ERROR during Google Sheets operation: {e}")
            print("="*60)
            raise

    else:
        print("\n" + "="*60)
        print("❌ No data to write to Google Sheet.")
        print("💡 This could mean:")
        print("   • API access was blocked before getting data")
        print("   • No MLB props available currently")
        print("   • Data format has changed")
        print("="*60)

if __name__ == "__main__":
    fetch_and_write_splash_data_to_sheet()
