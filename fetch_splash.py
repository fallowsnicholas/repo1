# enhanced_fetch_splash.py - Improved bot evasion for Splash Sports API
import requests
import json
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import os
import time
import random
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SplashSportsFetcher:
    def __init__(self):
        self.session = None
        self.base_url = "https://api.splashsports.com/props-service/api/props"
        self.proxy_rotation_index = 0
        
    def setup_session_with_retries(self):
        """Setup session with retry strategy and better connection handling"""
        session = requests.Session()
        
        # Retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=2
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    def get_realistic_headers(self):
        """More realistic headers that mimic actual browser behavior"""
        # Rotate between different realistic browser fingerprints
        browsers = [
            {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            },
            {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"'
            },
            {
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Linux"'
            }
        ]
        
        browser = random.choice(browsers)
        
        headers = {
            **browser,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://app.splashsports.com/',
            'Origin': 'https://app.splashsports.com',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'DNT': '1'
        }
        
        # Randomly omit some optional headers
        optional_headers = ['DNT', 'Pragma', 'Cache-Control']
        for header in optional_headers:
            if random.random() < 0.3:  # 30% chance to omit
                headers.pop(header, None)
                
        return headers

    def get_residential_proxies(self):
        """Get multiple residential proxy endpoints for rotation"""
        username = "brd-customer-hl_41883af7-zone-datacenter_proxy1"
        password = "2dg88246f4tn"
        
        # Multiple endpoints for rotation
        endpoints = [
            "brd.superproxy.io:33335",
            "brd.superproxy.io:33336",
            "brd.superproxy.io:33337",
        ]
        
        proxy_configs = []
        for endpoint in endpoints:
            proxy_url = f"http://{username}:{password}@{endpoint}"
            proxy_configs.append({
                'http': proxy_url,
                'https': proxy_url
            })
            
        return proxy_configs

    def human_like_delay(self):
        """More human-like delays with variance"""
        base_delay = random.uniform(8, 25)  # 8-25 second base
        
        # Add occasional longer pauses (like a human taking a break)
        if random.random() < 0.1:  # 10% chance
            base_delay += random.uniform(30, 90)
            
        time.sleep(base_delay)
        return base_delay

    def simulate_browser_behavior(self, session):
        """Simulate realistic browser behavior before making API calls"""
        try:
            # 1. Visit the main site first
            main_site_headers = self.get_realistic_headers()
            main_site_headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            
            print("   🌐 Simulating browser: visiting main site...")
            response = session.get(
                "https://app.splashsports.com/",
                headers=main_site_headers,
                timeout=30,
                verify=False
            )
            
            if response.status_code != 200:
                print(f"   ⚠️ Main site visit failed: {response.status_code}")
                return False
                
            time.sleep(random.uniform(2, 5))
            
            # 2. Make a preflight request or load some static resources
            print("   📡 Simulating browser: loading resources...")
            resource_headers = self.get_realistic_headers()
            resource_headers['Accept'] = '*/*'
            
            # Try to access a common static resource
            try:
                session.get(
                    "https://app.splashsports.com/favicon.ico",
                    headers=resource_headers,
                    timeout=15,
                    verify=False
                )
            except:
                pass  # Don't fail if this doesn't work
                
            time.sleep(random.uniform(1, 3))
            return True
            
        except Exception as e:
            print(f"   ❌ Browser simulation failed: {e}")
            return False

    def fetch_with_advanced_evasion(self):
        """Fetch data with advanced bot evasion techniques"""
        proxy_configs = self.get_residential_proxies()
        
        all_props = []
        offset = 0
        limit = 50  # Even smaller batches
        max_requests = 15
        requests_made = 0
        consecutive_failures = 0
        
        print("🤖 ENHANCED BOT EVASION MODE")
        print("=" * 50)
        
        for request_num in range(max_requests):
            if consecutive_failures >= 3:
                print("❌ Too many consecutive failures, stopping")
                break
                
            # Rotate proxies
            proxy_config = proxy_configs[request_num % len(proxy_configs)]
            
            # Create fresh session for each request
            session = self.setup_session_with_retries()
            session.proxies.update(proxy_config)
            
            print(f"\n🔄 Request {request_num + 1}/{max_requests}")
            print(f"   📡 Using proxy endpoint: ...{list(proxy_config.values())[0][-20:]}")
            
            # Simulate human behavior
            if request_num == 0 or random.random() < 0.3:  # 30% chance
                if not self.simulate_browser_behavior(session):
                    print("   ⚠️ Browser simulation failed, continuing anyway...")
            
            # Human-like delay
            if request_num > 0:
                delay = self.human_like_delay()
                print(f"   ⏱️ Human-like delay: {delay:.1f}s")
            
            # Prepare request
            headers = self.get_realistic_headers()
            params = {
                'limit': limit,
                'offset': offset,
                'league': 'mlb'
            }
            
            try:
                print(f"   🎯 Fetching: offset={offset}, limit={limit}")
                response = session.get(
                    self.base_url,
                    params=params,
                    headers=headers,
                    timeout=45,
                    verify=False
                )
                
                print(f"   📊 Response: {response.status_code}")
                
                if response.status_code == 200:
                    consecutive_failures = 0
                    
                    try:
                        data = response.json()
                        props_batch = data.get('data', [])
                        
                        if not props_batch:
                            print("   ✅ No more data, pagination complete")
                            break
                            
                        print(f"   ✅ Success: {len(props_batch)} props")
                        all_props.extend(props_batch)
                        
                        if len(props_batch) < limit:
                            print("   ✅ End of data reached")
                            break
                            
                        offset += limit
                        
                    except json.JSONDecodeError as e:
                        print(f"   ❌ JSON decode error: {e}")
                        consecutive_failures += 1
                        
                elif response.status_code in [403, 429]:
                    consecutive_failures += 1
                    print(f"   🚫 Rate limited ({response.status_code})")
                    
                    if consecutive_failures < 3:
                        # Exponential backoff
                        backoff_delay = min(300, 30 * (2 ** consecutive_failures))
                        print(f"   ⏳ Exponential backoff: {backoff_delay}s")
                        time.sleep(backoff_delay)
                    
                else:
                    consecutive_failures += 1
                    print(f"   ❌ Unexpected status: {response.status_code}")
                    print(f"       Response: {response.text[:200]}")
                    
            except Exception as e:
                consecutive_failures += 1
                print(f"   ❌ Request failed: {str(e)[:100]}")
                
            finally:
                session.close()
                
            requests_made += 1
            
        print(f"\n📈 FETCH COMPLETE: {len(all_props)} props collected")
        return all_props

def main():
    """Main execution with enhanced bot evasion"""
    fetcher = SplashSportsFetcher()
    
    try:
        all_props = fetcher.fetch_with_advanced_evasion()
        
        if not all_props:
            print("❌ No data retrieved with enhanced methods")
            return
            
        # Process and save data (your existing logic)
        mlb_props = [prop for prop in all_props if prop.get('league') == 'mlb']
        print(f"⚾ Found {len(mlb_props)} MLB props")
        
        # Continue with your existing Google Sheets logic...
        
    except Exception as e:
        print(f"❌ Enhanced fetcher failed: {e}")

if __name__ == "__main__":
    main()
