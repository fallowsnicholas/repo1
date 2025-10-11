# fetch_splash_json.py - Step 3A: Fetch Splash Sports JSON (Multi-Sport Version)
import requests
import json
import os
import time
from datetime import datetime
import argparse
from sports_config import get_sport_config

class SplashJSONFetcher:
    """Multi-sport JSON fetcher using free API services - no processing, just data collection"""
    
    def __init__(self, sport='MLB'):
        self.sport = sport.upper()
        self.base_url = "https://api.splashsports.com/props-service/api/props"
        self.output_file = f"splash_{sport.lower()}_raw_data.json"
        self.services_used = []
        
        # Load sport-specific configuration
        config = get_sport_config(self.sport)
        self.splash_league = config['splash_league']  # 'mlb', 'nfl', or 'wnba'
        
        print(f"🏈 Initialized {self.sport} Splash Fetcher")
        print(f"   League parameter: {self.splash_league}")
        print(f"   Output file: {self.output_file}")
        
    def fetch_via_scraperapi(self, url, params=None):
        """Primary: ScraperAPI (5000 free requests/month)"""
        api_key = os.environ.get('SCRAPERAPI_KEY')
        
        if not api_key:
            print("❌ SCRAPERAPI_KEY not found in environment")
            return None, None
        
        target_url = self._build_url(url, params)
        
        payload = {
            'api_key': api_key,
            'url': target_url,
            'country_code': 'us',
            'render': 'false'  # JSON doesn't need rendering
        }
        
        try:
            print(f"   📡 ScraperAPI: {target_url}")
            response = requests.get("http://api.scraperapi.com", params=payload, timeout=45)
            
            if response.status_code == 200:
                return response.json(), "ScraperAPI"
            else:
                print(f"   ❌ ScraperAPI HTTP {response.status_code}")
                return None, None
                
        except Exception as e:
            print(f"   ❌ ScraperAPI failed: {e}")
            return None, None
    
    def fetch_via_scrapfly(self, url, params=None):
        """Backup: ScrapFly (1000 free requests/month)"""
        api_key = os.environ.get('SCRAPFLY_KEY')
        
        if not api_key:
            print("❌ SCRAPFLY_KEY not found in environment")
            return None, None
        
        target_url = self._build_url(url, params)
        
        payload = {
            'key': api_key,
            'url': target_url,
            'country': 'US',
            'render_js': False,
            'cache': True,
            'cache_clear': False
        }
        
        try:
            print(f"   📡 ScrapFly: {target_url}")
            response = requests.get("https://api.scrapfly.io/scrape", params=payload, timeout=45)
            
            if response.status_code == 200:
                data = response.json()
                content = data['result']['content']
                return json.loads(content), "ScrapFly"
            else:
                print(f"   ❌ ScrapFly HTTP {response.status_code}")
                return None, None
                
        except Exception as e:
            print(f"   ❌ ScrapFly failed: {e}")
            return None, None
    
    def fetch_via_zenrows(self, url, params=None):
        """Tertiary: ZenRows (1000 free requests/month)"""
        api_key = os.environ.get('ZENROWS_KEY')
        
        if not api_key:
            print("❌ ZENROWS_KEY not found in environment")
            return None, None
        
        target_url = self._build_url(url, params)
        
        payload = {
            'apikey': api_key,
            'url': target_url,
            'js_render': 'false',
            'premium_proxy': 'false'
        }
        
        try:
            print(f"   📡 ZenRows: {target_url}")
            response = requests.get("https://api.zenrows.com/v1/", params=payload, timeout=45)
            
            if response.status_code == 200:
                return response.json(), "ZenRows"
            else:
                print(f"   ❌ ZenRows HTTP {response.status_code}")
                return None, None
                
        except Exception as e:
            print(f"   ❌ ZenRows failed: {e}")
            return None, None
    
    def _build_url(self, base_url, params):
        """Helper to build URL with parameters"""
        if not params:
            return base_url
        
        param_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{param_string}"
    
    def fetch_all_splash_json(self):
        """Main fetching logic - collect raw JSON responses only (NO PROCESSING)"""
        print(f"📥 STEP 3A: FETCHING {self.sport} RAW JSON RESPONSES")
        print("=" * 60)
        print("🎯 Goal: Collect raw API responses only")
        print("🚫 NO data analysis, filtering, or counting")
        print(f"💾 Output: {self.output_file}")
        print()
        
        # API service priority order (best free tier first)
        api_services = [
            ('ScraperAPI', self.fetch_via_scraperapi),
            ('ScrapFly', self.fetch_via_scrapfly), 
            ('ZenRows', self.fetch_via_zenrows)
        ]
        
        all_raw_responses = []
        offset = 0
        
        # Try larger batch sizes first to minimize API calls
        batch_sizes_to_try = [1000, 500, 250, 100]  # Start big, fall back if needed
        max_requests = 10  # Conservative for free tiers
        requests_made = 0
        
        print(f"🔄 Smart fetching: trying large batches first to minimize API calls")
        
        for limit in batch_sizes_to_try:
            print(f"\n🎯 Attempting batch size: {limit}")
            
            while requests_made < max_requests:
                params = {
                    'league': self.splash_league,  # Use sport-specific league parameter
                    'limit': limit,
                    'offset': offset
                }
                
                print(f"📊 Request {requests_made + 1}/{max_requests}: league={self.splash_league}, offset={offset}, limit={limit}")
                
                # Try each API service in priority order
                response_received = False
                service_used = None
                
                for service_name, service_func in api_services:
                    print(f"   🔍 Trying {service_name}...")
                    
                    raw_json_response, used_service = service_func(self.base_url, params)
                    
                    if raw_json_response:
                        print(f"   ✅ Raw JSON received via {used_service}")
                        
                        # Store the COMPLETE raw response with minimal metadata
                        response_info = {
                            'request_number': requests_made + 1,
                            'sport': self.sport,
                            'league': self.splash_league,
                            'offset': offset,
                            'limit': limit,
                            'service_used': used_service,
                            'timestamp': datetime.now().isoformat(),
                            'complete_raw_response': raw_json_response  # Store everything as-is
                        }
                        
                        all_raw_responses.append(response_info)
                        response_received = True
                        service_used = used_service
                        
                        # Track service usage
                        if used_service not in self.services_used:
                            self.services_used.append(used_service)
                        
                        # Check for pagination end WITHOUT analyzing content
                        # Just check if response has data field and if it's empty
                        if isinstance(raw_json_response, dict) and 'data' in raw_json_response:
                            data_length = len(raw_json_response['data']) if raw_json_response['data'] else 0
                            
                            if data_length == 0:  # Empty data array
                                print(f"   🏁 API returned empty data array - pagination complete")
                                return self._save_raw_responses(all_raw_responses)
                            elif data_length < limit:
                                print(f"   🏁 API returned {data_length}/{limit} items - end of data reached")
                                return self._save_raw_responses(all_raw_responses)
                            else:
                                print(f"   📊 Full batch received: {data_length}/{limit} items")
                        
                        break
                    else:
                        print(f"   ❌ {service_name}: No response received")
                
                if not response_received:
                    print(f"   ❌ All API services failed for limit={limit}")
                    print(f"   🔄 Trying smaller batch size...")
                    break  # Try next (smaller) batch size
                
                offset += limit
                requests_made += 1
                
                # Rate limiting for free services
                if requests_made < max_requests:
                    delay = 3 + (requests_made * 0.5)  # Progressive delay
                    print(f"   ⏱️ Rate limiting delay: {delay:.1f}s")
                    time.sleep(delay)
            
            # If we successfully got data with this batch size, we're done
            if all_raw_responses:
                print(f"   ✅ Successfully collected data with batch size: {limit}")
                break
            else:
                print(f"   ❌ Batch size {limit} failed, trying smaller...")
                # Reset for next batch size attempt
                offset = 0
                requests_made = 0
        
        return self._save_raw_responses(all_raw_responses)
    
    def _save_raw_responses(self, all_raw_responses):
        """Save collected raw API responses to JSON file"""
        if not all_raw_responses:
            print("❌ No responses collected to save")
            return False
        
        # Calculate basic totals WITHOUT analyzing content
        total_requests = len(all_raw_responses)
        services_summary = {}
        
        for response in all_raw_responses:
            service = response['service_used']
            services_summary[service] = services_summary.get(service, 0) + 1
        
        # Create final JSON structure - store everything as-is
        output_data = {
            'fetch_metadata': {
                'sport': self.sport,
                'league': self.splash_league,
                'fetch_timestamp': datetime.now().isoformat(),
                'total_requests_made': total_requests,
                'services_used': services_summary,
                'fetch_success': True,
                'note': 'Raw API responses - no content analysis performed'
            },
            'raw_api_responses': all_raw_responses
        }
        
        try:
            # Save to file
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 RAW API RESPONSES SAVED")
            print(f"=" * 40)
            print(f"📁 File: {self.output_file}")
            print(f"🏈 Sport: {self.sport}")
            print(f"⚾ League: {self.splash_league}")
            print(f"🔢 Total API Requests: {total_requests}")
            print(f"🛠️ Services Used: {list(services_summary.keys())}")
            
            for service, count in services_summary.items():
                print(f"   • {service}: {count} requests")
            
            # File size info
            file_size = os.path.getsize(self.output_file) / 1024  # KB
            print(f"📦 File Size: {file_size:.1f} KB")
            print(f"🚫 NO content analysis performed - raw data only")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to save raw responses: {e}")
            return False

def main():
    """Main execution for JSON fetching only"""
    parser = argparse.ArgumentParser(description='Fetch Splash Sports JSON for MLB, NFL, or WNBA')
    parser.add_argument('--sport', default='MLB', choices=['MLB', 'NFL', 'WNBA'],
                       help='Sport to fetch data for (default: MLB)')
    args = parser.parse_args()
    
    print(f"🚀 Starting {args.sport} JSON fetch at: {datetime.now()}")
    
    fetcher = SplashJSONFetcher(sport=args.sport)
    
    try:
        success = fetcher.fetch_all_splash_json()
        
        if success:
            print(f"\n🎉 JSON FETCH COMPLETE!")
            print(f"✅ Raw data saved to: {fetcher.output_file}")
            print(f"🔄 Next: Run process_splash_data.py --sport {args.sport} to process and save to sheets")
        else:
            print(f"\n❌ JSON FETCH FAILED")
            print(f"💡 Check API credentials and service status")
            exit(1)
            
    except Exception as e:
        print(f"\n❌ JSON fetch crashed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
