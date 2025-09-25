# brightdata_test.py - Simple connection test script
import requests
import os
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_brightdata_connection():
    """Simple test to verify Bright Data connection"""
    
    proxy_username = os.environ.get('PROXY_USERNAME')
    proxy_password = os.environ.get('PROXY_PASSWORD')
    
    if not proxy_username or not proxy_password:
        print("❌ Missing proxy credentials")
        return
    
    print(f"🔑 Testing with username: {proxy_username[:30]}...")
    print(f"🔑 Password length: {len(proxy_password)} characters")
    
    # Try different endpoint formats
    endpoints = [
        "brd.superproxy.io:33335",
        "brd.superproxy.io:22225", 
        "brd-customer-hl_41883af7-zone-residential_proxy1.brd.superproxy.io:33335",
        f"{proxy_username}.brd.superproxy.io:33335"
    ]
    
    test_url = "http://httpbin.org/ip"
    
    for i, endpoint in enumerate(endpoints, 1):
        print(f"\n🔍 Test {i}/{len(endpoints)}: {endpoint}")
        
        proxy_url = f"http://{proxy_username}:{proxy_password}@{endpoint}"
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        try:
            response = requests.get(
                test_url, 
                proxies=proxies, 
                timeout=30,
                verify=False
            )
            
            if response.status_code == 200:
                ip_info = response.json()
                current_ip = ip_info.get('origin', 'Unknown')
                print(f"✅ SUCCESS! Current IP: {current_ip}")
                print(f"🎉 Working endpoint: {endpoint}")
                return endpoint
            else:
                print(f"❌ HTTP {response.status_code}: {response.text[:100]}")
                
        except requests.exceptions.ProxyError as e:
            print(f"❌ Proxy Error: {str(e)[:100]}")
            
        except requests.exceptions.Timeout as e:
            print(f"❌ Timeout: Connection took >30 seconds")
            
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection Error: {str(e)[:100]}")
            
        except Exception as e:
            print(f"❌ Other Error: {str(e)[:100]}")
    
    print(f"\n❌ All endpoints failed")
    print(f"💡 Next steps:")
    print(f"   • Check Bright Data dashboard for zone status")
    print(f"   • Verify account has sufficient balance")
    print(f"   • Check if IP whitelisting is required")
    print(f"   • Contact Bright Data support")

if __name__ == "__main__":
    test_brightdata_connection()
