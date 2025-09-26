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
import urllib3

# Disable SSL warnings when using proxies
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_brightdata_proxy():
    """Get Bright Data datacenter proxy configuration"""
    # Use datacenter proxy credentials
    proxy_username = "brd-customer-hl_41883af7-zone-datacenter_proxy1"
    proxy_password = "2dg88246f4tn"
    
    print(f"🏢 Using Bright Data datacenter proxy:")
    print(f"   Username: {proxy_username}")
    print(f"   Password: {proxy_password}")
    
    # Datacenter proxy endpoint
    proxy_endpoint = "brd.superproxy.io:33335"
    
    print(f"🌐 Using endpoint: {proxy_endpoint}")
    print(f"📊 Proxy type: Datacenter (no IP allowlisting required)")
    
    # Simple proxy format for datacenter proxies
    proxy_url = f"http://{proxy_username}:{proxy_password}@{proxy_endpoint}"
    
    proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    
    return proxies, proxy_username, proxy_password

def test_proxy_connection_advanced(proxies, username, password):
    """Test proxy connection with advanced authentication methods"""
    test_url = "http://httpbin.org/ip"  # Use HTTP first, not HTTPS
    
    print("🔍 Testing proxy connection with multiple methods...")
    
    # Method 1: Standard proxy format
    try:
        print("   📡 Method 1: Standard proxy format")
        response = requests.get(test_url, proxies=proxies, timeout=30, verify=False)
        
        if response.status_code == 200:
            ip_info = response.json()
            current_ip = ip_info.get('origin', 'Unknown')
            print(f"   ✅ SUCCESS! Current IP: {current_ip}")
            return True
        else:
            print(f"   ❌ Status {response.status_code}: {response.text[:100]}")
    except Exception as e:
        print(f"   ❌ Method 1 failed: {str(e)[:100]}")
    
    # Method 2: Using requests.auth explicitly
    try:
        print("   📡 Method 2: Explicit authentication")
        from requests.auth import HTTPProxyAuth
        
        proxy_auth = HTTPProxyAuth(username, password)
        simple_proxies = {
            'http': f'http://brd.superproxy.io:33335',
            'https': f'http://brd.superproxy.io:33335'
        }
        
        response = requests.get(
            test_url, 
            proxies=simple_proxies, 
            auth=proxy_auth, 
            timeout=30, 
            verify=False
        )
        
        if response.status_code == 200:
            ip_info = response.json()
            current_ip = ip_info.get('origin', 'Unknown')
            print(f"   ✅ SUCCESS with Method 2! Current IP: {current_ip}")
            return True
        else:
            print(f"   ❌ Status {response.status_code}: {response.text[:100]}")
    except Exception as e:
        print(f"   ❌ Method 2 failed: {str(e)[:100]}")
    
    # Method 3: Session-based with explicit headers
    try:
        print("   📡 Method 3: Session with custom headers")
        import base64
        
        # Create basic auth header
        credentials = f"{username}:{password}"
        b64_credentials = base64.b64encode(credentials.encode()).decode()
        
        session = requests.Session()
        session.headers.update({
            'Proxy-Authorization': f'Basic {b64_credentials}'
        })
        
        simple_proxies = {
            'http': f'http://brd.superproxy.io:33335',
            'https': f'http://brd.superproxy.io:33335'
        }
        session.proxies.update(simple_proxies)
        
        response = session.get(test_url, timeout=30, verify=False)
        
        if response.status_code == 200:
            ip_info = response.json()
            current_ip = ip_info.get('origin', 'Unknown')
            print(f"   ✅ SUCCESS with Method 3! Current IP: {current_ip}")
            return True
        else:
            print(f"   ❌ Status {response.status_code}: {response.text[:100]}")
    except Exception as e:
        print(f"   ❌ Method 3 failed: {str(e)[:100]}")
    
    print("   ❌ All authentication methods failed")
    return False

def test_proxy_connection(proxies):
    """Test if the proxy connection is working with better error handling"""
    test_url = "http://httpbin.org/ip"
    
    try:
        print("🔍 Testing proxy connection...")
        print(f"🌐 Proxy URL format: http://[username]:[password]@brd.superproxy.io:33335")
        
        # Test with longer timeout and better error handling
        response = requests.get(test_url, proxies=proxies, timeout=30, verify=False)
        
        if response.status_code == 200:
            ip_info = response.json()
            current_ip = ip_info.get('origin', 'Unknown')
            print(f"✅ Proxy working! Current IP: {current_ip}")
            
            # Check if it's actually a different IP (not the original GitHub Actions IP)
            if current_ip != 'Unknown':
                print(f"🏠 Using residential IP: {current_ip}")
                return True
            else:
                print(f"⚠️ IP detection unclear, but connection successful")
                return True
        else:
            print(f"❌ Proxy test failed with status: {response.status_code}")
            print(f"    Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.ProxyError as e:
        print(f"❌ Proxy authentication/configuration error: {e}")
        print("💡 Common causes:")
        print("   • Wrong username or password")
        print("   • Proxy zone not active")
        print("   • IP not whitelisted (if required)")
        return False
        
    except requests.exceptions.Timeout as e:
        print(f"❌ Proxy timeout (30s): {e}")
        print("💡 Common causes:")
        print("   • Proxy server overloaded")
        print("   • Wrong endpoint/port")
        print("   • Network connectivity issues")
        return False
        
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        print("💡 Common causes:")
        print("   • Wrong host or port")
        print("   • Proxy service down")
        print("   • Network firewall blocking connection")
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

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

def random_delay(min_seconds=5, max_seconds=15):
    """Add random delay to mimic human behavior and avoid rate limiting"""
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
        proxies, username, password = get_brightdata_proxy()
        print("🌐 Bright Data residential proxy configured")
    except ValueError as e:
        print(f"❌ {e}")
        return []
    
    # Test proxy connection with advanced methods
    if not test_proxy_connection_advanced(proxies, username, password):
        print("❌ All proxy authentication methods failed")
        print("💡 This may be an Immediate Access mode integration issue")
        return []
    
    # Create session with proxy
    session = requests.Session()
    session.proxies.update(proxies)
    
    all_props = []
    offset = 0
    limit = 100  # Much smaller batches for Immediate Access mode
    max_requests = 20  # Allow more requests with smaller batches
    requests_made = 0
    consecutive_failures = 0
    max_consecutive_failures = 3
    
    print("⚾ STEP 3: FETCHING SPLASH SPORTS DATA (RESIDENTIAL PROXY)")
    print("=" * 60)
    print("🏠 Using Bright Data residential proxy network")
    print("🛡️ IMMEDIATE ACCESS MODE - Rate Limited")
    print("   • SSL verification: disabled (✅)")
    print("   • Request throttling: active")
    print("   • Batch size: reduced to 100")
    print("   • Delays: 5-15 seconds between requests")
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
            # Random delay between requests (longer for Immediate Access)
            delay = random_delay(5, 15)
            print(f"   ⏱️ Delayed {delay:.1f}s (rate limiting compliance)")
            
            # Make request through residential proxy (disable SSL verification for proxy)
            response = session.get(url, params=params, headers=headers, timeout=30, verify=False)
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
                    print("   🔄 503 Service Unavailable - Rate limited by Immediate Access")
                    print("      • This is normal for non-KYC verified accounts")
                    print("      • Increasing delays and reducing batch size...")
                    
                    # Longer delay for 503 errors
                    extended_delay = random.uniform(30, 60)
                    print(f"      • Extended delay: {extended_delay:.1f}s")
                    time.sleep(extended_delay)
                    
                    # Further reduce batch size
                    limit = max(50, limit // 2)
                    print(f"      • Reduced batch size to: {limit}")
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
