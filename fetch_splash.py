# fetch_splash.py - Step 3: Fetch Splash Sports data with Bright Data residential proxies
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

def get_brightdata_proxy():
    """Get Bright Data proxy configuration from environment variables"""
    proxy_username = os.environ.get('PROXY_USERNAME')
    proxy_password = os.environ.get('PROXY_PASSWORD')
    
    if not all([proxy_username, proxy_password]):
        raise ValueError("Missing Bright Data proxy credentials. Please set PROXY_USERNAME and PROXY_PASSWORD environment variables.")
    
    # Extract endpoint from username (newer Bright Data format)
    # Username format: brd-customer-hl_41883af7-zone-residential_proxy1
    # Endpoint format: brd-customer-hl_41883af7-zone-residential_proxy1:22225
    
    # Standard Bright Data residential proxy port
    proxy_endpoint = f"{proxy_username}:22225"
    
    # Bright Data proxy URL
    proxy_url = f"http://{proxy_username}:{proxy_password}@{proxy_endpoint}"
    
    proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    
    print(f"🌐 Proxy endpoint: {proxy_endpoint}")
    
    return proxies

def get_random_headers():
    """Generate randomized headers for residential proxy requests"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0'
    ]
    
    accept_languages = [
        'en-US,en;q=0.9',
        'en-US,en;q=0.8,es;q=0.7',
        'en-GB,en;q=0.9',
        'en-US,en;q=0.9,fr;q=0.8'
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
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }

def random_delay(min_seconds=2, max_seconds=6):
    """Add random delay to mimic human behavior"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)
    return delay

def test_proxy_connection(proxies):
    """Test if the proxy connection is working"""
    test_url = "http://httpbin.org/ip"
    
    try:
        print("🔍 Testing proxy connection...")
        response = requests.get(test_url, proxies=proxies, timeout=10)
        
        if response.status_code == 200:
            ip_info = response.json()
            print(f"✅ Proxy working! Current IP: {ip_info.get('origin', 'Unknown')}")
            return True
        else:
            print(f"❌ Proxy test failed with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Proxy test failed: {e}")
        return False

def fetch_splash_data_with_residential_proxy():
    """
    Fetch data using Bright Data residential proxies to avoid bot detection
    """
    url = "https://api.splashsports.com/props-service/api/props"
    
    # Get proxy configuration
    try:
        proxies = get_brightdata_proxy()
        print("🌐 Bright Data residential proxy configured")
    except ValueError as e:
        print(f"❌ {e}")
        return []
    
    # Test proxy connection
    if not test_proxy_connection(proxies):
        print("❌ Proxy connection failed, aborting...")
        return []
    
    # Create session with proxy
    session = requests.Session()
    session.proxies.update(proxies)
    
    all_props = []
    offset = 0
    limit = 500  # Can be more aggressive with residential proxies
    max_requests = 10
    requests_made = 0
    consecutive_failures = 0
    max_consecutive_failures = 3
    
    print("⚾ STEP 3: FETCHING SPLASH SPORTS DATA (RESIDENTIAL PROXY)")
    print("=" * 60)
    print("🏠 Using Bright Data residential proxy network")
    print("🛡️ Anti-bot measures:")
    print("   • Residential IP addresses")
    print("   • Randomized headers")
    print("   • Human-like delays")
    print()
    
    while requests_made < max_requests and consecutive_failures < max_consecutive_failures:
        headers = get_random_headers()
        
        params = {
            'limit': limit,
            'offset': offset,
            'league': 'mlb'
        }
        
        print(f"🔄 Request {requests_made + 1}: offset={offset}, limit={limit}")
        
        try:
            # Random delay between requests
            delay = random_delay(2, 6)
            print(f"   ⏱️ Delayed {delay:.1f}s")
            
            # Make request through residential proxy
            response = session.get(url, params=params, headers=headers, timeout=30)
            print(f"   📡 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                consecutive_failures = 0
                
                try:
                    data = response.json()
                    props_batch = data.get('data', [])
                    
                    if not props_batch:
                        print("   ✅ No more data returned, stopping pagination")
                        break
                    
                    print(f"   ✅ Received {len(props_batch)} props")
                    all_props.extend(props_batch)
                    
                    if len(props_batch) < limit:
                        print("   ✅ End of data reached")
                        break
                    
                    offset += limit
                    
                except json.JSONDecodeError as e:
                    print(f"   ❌ JSON decode error: {e}")
                    consecutive_failures += 1
                    
            elif response.status_code == 403:
                consecutive_failures += 1
                print(f"   🚫 403 Forbidden (attempt {consecutive_failures}/{max_consecutive_failures})")
                
                if consecutive_failures < max_consecutive_failures:
                    print("   🔄 Residential IP may be flagged, trying new session...")
                    # Close and recreate session to potentially get new residential IP
                    session.close()
                    session = requests.Session()
                    session.proxies.update(proxies)
                    
                    # Longer delay
                    extended_delay = random.uniform(15, 25)
                    print(f"      • Extended delay: {extended_delay:.1f}s")
                    time.sleep(extended_delay)
                else:
                    print("   ❌ Multiple 403 errors even with residential proxy")
                    
            elif response.status_code == 429:
                print(f"   ⏳ 429 Rate Limited")
                backoff_delay = random.uniform(20, 35)
                print(f"      • Backoff delay: {backoff_delay:.1f}s")
                time.sleep(backoff_delay)
                continue
                
            else:
                consecutive_failures += 1
                print(f"   ❌ Unexpected status: {response.status_code}")
                print(f"      Response: {response.text[:200]}...")
                
                if consecutive_failures < max_consecutive_failures:
                    time.sleep(random.uniform(10, 15))
                
        except requests.exceptions.ProxyError as e:
            consecutive_failures += 1
            print(f"   🌐 Proxy error: {e}")
            if consecutive_failures < max_consecutive_failures:
                time.sleep(random.uniform(10, 20))
                
        except requests.exceptions.Timeout:
            consecutive_failures += 1
            print(f"   ⏰ Request timed out")
            if consecutive_failures < max_consecutive_failures:
                time.sleep(random.uniform(5, 10))
                
        except requests.exceptions.RequestException as e:
            consecutive_failures += 1
            print(f"   ❌ Request error: {e}")
            if consecutive_failures < max_consecutive_failures:
                time.sleep(random.uniform(5, 10))
        
        requests_made += 1
    
    session.close()
    
    print(f"\n📊 FETCH COMPLETE:")
    print(f"   Total props collected: {len(all_props)}")
    print(f"   Requests made: {requests_made}")
    
    if consecutive_failures >= max_consecutive_failures:
        print(f"   ⚠️ Stopped due to persistent errors")
        print(f"   💡 Consider contacting Bright Data support if issues persist")
    
    return all_props

def fetch_and_write_splash_data_to_sheet():
    """
    Main function: Fetch data with residential proxy and write to Google Sheets
    """
    print(f"🕐 Starting fetch at: {datetime.now()}")
    
    # Fetch data using residential proxy
    all_props = fetch_splash_data_with_residential_proxy()
    
    if not all_props:
        print("❌ No props data retrieved")
        print("💡 Troubleshooting:")
        print("   • Check Bright Data proxy credentials")
        print("   • Verify proxy quota/balance")
        print("   • Contact Bright Data support if needed")
        return None
    
    print(f"🔍 Processing {len(all_props)} total props")
    
    # Filter for MLB
    mlb_props = [prop for prop in all_props if prop.get('league') == 'mlb']
    print(f"⚾ Found {len(mlb_props)} MLB props")
    
    # Market breakdown
    if mlb_props:
        market_breakdown = {}
        for prop in mlb_props:
            market = prop.get('type', 'unknown')
            market_breakdown[market] = market_breakdown.get(market, 0) + 1
        print(f"📊 Market breakdown: {market_breakdown}")
    
    # Create DataFrame
    extracted_data = []
    for prop in mlb_props:
        extracted_data.append({
            'name': prop.get('entity_name'),
            'type': prop.get('type'),
            'line': prop.get('line')
        })

    df = pd.DataFrame(extracted_data)
    df = df.rename(columns={'name': 'Name', 'type': 'Market', 'line': 'Line'})
    
    print(f"📋 DataFrame: {len(df)} rows, {df['Name'].nunique()} unique players")
    
    # Write to Google Sheets
    if not df.empty:
        print("\n" + "="*60)
        print("📝 WRITING TO GOOGLE SHEETS")
        print("="*60)
        
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]

            service_account_info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_CREDENTIALS'])
            credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
            client = gspread.authorize(credentials)

            spreadsheet = client.open("MLB_Splash_Data")
            worksheet = spreadsheet.worksheet("SPLASH_MLB")

            print("🧹 Clearing existing data...")
            worksheet.clear()

            df_sorted = df.sort_values(by='Market').reset_index(drop=True)
            
            print("💾 Writing data to sheet...")
            set_with_dataframe(worksheet, df_sorted)
            
            print("✅ Successfully wrote to Google Sheets!")
            print(f"📊 {len(df)} MLB props saved")

        except Exception as e:
            print(f"❌ Google Sheets error: {e}")
            raise
    else:
        print("❌ No data to write")

if __name__ == "__main__":
    fetch_and_write_splash_data_to_sheet()
