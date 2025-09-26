# fetch_splash_json.py - Step 3A: Dedicated script for fetching JSON data only
import requests
import json
import os
import time
from datetime import datetime

class SplashJSONFetcher:
    """Dedicated JSON fetcher using free API services - no processing, just data collection"""
    
    def __init__(self):
        self.base_url = "https://api.splashsports.com/props-service/api/props"
        self.output_file = "splash_raw_data.json"
        self.services_used = []
        
    def fetch_via_scraperapi(self, url, params=None):
        """Primary: ScraperAPI (5000 free requests/month)"""
        api_key = os.environ.get('SCRAPERAPI_KEY')
        
        if not api_key:
            print("❌ SCRAPERAPI_KEY not found in environment")
            return None
        
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
        """Main fetching logic - collect all JSON data without processing"""
        print("📥 STEP 3A: FETCHING SPLASH SPORTS JSON DATA")
        print("=" * 60)
        print("🎯 Goal: Collect raw JSON data only (no processing)")
        print("💾 Output: splash_raw_data.json")
        print()
        
        # API service priority order (best free tier first)
        api_services = [
            ('ScraperAPI', self.fetch_via_scraperapi),
            ('ScrapFly', self.fetch_via_scrapfly), 
            ('ZenRows', self.fetch_via_zenrows)
        ]
        
        all_raw_data = []
        offset = 0
        limit = 100
        max_requests = 25  # Conservative for free tiers
        requests_made = 0
        
        print(f"🔄 Starting pagination fetch (max {max_requests} requests)")
        
        while requests_made < max_requests:
            params = {
                'league': 'mlb',
                'limit': limit,
                'offset': offset
            }
            
            print(f"\n📊 Request {requests_made + 1}/{max_requests}: offset={offset}, limit={limit}")
            
            # Try each API service in priority order
            data_fetched = False
            service_used = None
            
            for service_name, service_func in api_services:
                print(f"   🔍 Trying {service_name}...")
                
                json_data, used_service = service_func(self.base_url, params)
                
                if json_data and 'data' in json_data:
                    props_batch = json_data['data']
                    
                    if props_batch:
                        print(f"   ✅ Success! {len(props_batch)} props via {used_service}")
                        
                        # Store raw response with metadata
                        batch_info = {
                            'request_number': requests_made + 1,
                            'offset': offset,
                            'limit': limit,
                            'service_used': used_service,
                            'timestamp': datetime.now().isoformat(),
                            'props_count': len(props_batch),
                            'raw_data': props_batch
                        }
                        
                        all_raw_data.append(batch_info)
                        data_fetched = True
                        service_used = used_service
                        
                        # Track service usage
                        if used_service not in self.services_used:
                            self.services_used.append(used_service)
                        
                        break
                    else:
                        print(f"   ℹ️ {service_name}: Empty data array (end of pagination)")
                        print("   🏁 Pagination complete - no more data available")
                        return self._save_raw_data(all_raw_data)
                else:
                    print(f"   ❌ {service_name}: Invalid response format")
            
            if not data_fetched:
                print(f"   ❌ All API services failed for request {requests_made + 1}")
                print("   🛑 Stopping fetch due to service failures")
                break
            
            # Check if we got less than limit (end of pagination)
            if len(props_batch) < limit:
                print(f"   🏁 End of data: Got {len(props_batch)} < {limit} (limit)")
                break
            
            offset += limit
            requests_made += 1
            
            # Rate limiting for free services
            if requests_made < max_requests:
                delay = 3 + (requests_made * 0.5)  # Progressive delay
                print(f"   ⏱️ Rate limiting delay: {delay:.1f}s")
                time.sleep(delay)
        
        return self._save_raw_data(all_raw_data)
    
    def _save_raw_data(self, all_raw_data):
        """Save collected data to JSON file"""
        if not all_raw_data:
            print("❌ No data collected to save")
            return False
        
        # Calculate totals
        total_props = sum(batch['props_count'] for batch in all_raw_data)
        total_requests = len(all_raw_data)
        services_summary = {}
        
        for batch in all_raw_data:
            service = batch['service_used']
            services_summary[service] = services_summary.get(service, 0) + 1
        
        # Create final JSON structure
        output_data = {
            'fetch_metadata': {
                'fetch_timestamp': datetime.now().isoformat(),
                'total_requests_made': total_requests,
                'total_props_collected': total_props,
                'services_used': services_summary,
                'fetch_success': True
            },
            'raw_batches': all_raw_data
        }
        
        try:
            # Save to file
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 RAW DATA SAVED SUCCESSFULLY")
            print(f"=" * 40)
            print(f"📁 File: {self.output_file}")
            print(f"📊 Total Props: {total_props}")
            print(f"🔢 Total Requests: {total_requests}")
            print(f"🛠️ Services Used: {list(services_summary.keys())}")
            
            for service, count in services_summary.items():
                print(f"   • {service}: {count} requests")
            
            # File size info
            file_size = os.path.getsize(self.output_file) / 1024  # KB
            print(f"📦 File Size: {file_size:.1f} KB")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to save raw data: {e}")
            return False

def main():
    """Main execution for JSON fetching only"""
    print(f"🚀 Starting JSON fetch at: {datetime.now()}")
    
    fetcher = SplashJSONFetcher()
    
    try:
        success = fetcher.fetch_all_splash_json()
        
        if success:
            print(f"\n🎉 JSON FETCH COMPLETE!")
            print(f"✅ Raw data saved to: {fetcher.output_file}")
            print(f"🔄 Next: Run process_splash_data.py to process and save to sheets")
        else:
            print(f"\n❌ JSON FETCH FAILED")
            print(f"💡 Check API credentials and service status")
            exit(1)
            
    except Exception as e:
        print(f"\n❌ JSON fetch crashed: {e}")
        exit(1)

if __name__ == "__main__":
    main()
