#!/usr/bin/env python3
"""
Check the deployed version to see if it's collecting new league data
"""

import requests
import json
import sys
from datetime import datetime

def check_deployment():
    """Check if the deployed version is collecting new league data"""
    
    # Cloudflare Access headers
    headers = {
        'CF-Access-Client-Id': '8566de2f6aa3e27f29862d6ac7cda19e.access',
        'CF-Access-Client-Secret': '4da273b33d39db31ba1ca3764c1dcbefeea7209b0a3888df5746fea0390f1e84',
        'User-Agent': 'Joker-Builds-Check/1.0'
    }
    
    base_url = 'https://jokers-builds.beachysapp.com'
    
    print("🔍 Checking deployed version status...")
    print(f"URL: {base_url}")
    print()
    
    # Try different endpoints
    endpoints = [
        '/api/stats',
        '/api/leagues', 
        '/api/recent',
        '/health',
        '/',
    ]
    
    for endpoint in endpoints:
        try:
            print(f"Testing {endpoint}...")
            response = requests.get(
                f"{base_url}{endpoint}", 
                headers=headers,
                timeout=10,
                allow_redirects=False
            )
            
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"  ✅ JSON Response: {len(str(data))} chars")
                    if isinstance(data, dict):
                        for key in list(data.keys())[:5]:  # Show first 5 keys
                            print(f"    - {key}: {type(data[key])}")
                except:
                    print(f"  📄 Text Response: {len(response.text)} chars")
                    print(f"    Preview: {response.text[:100]}...")
                    
            elif response.status_code == 302:
                print(f"  🔄 Redirect to: {response.headers.get('Location', 'Unknown')}")
            else:
                print(f"  ❌ Error: {response.text[:100]}")
                
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Request failed: {e}")
        
        print()
    
    # Try using different authentication methods
    print("🔐 Trying alternative access methods...")
    
    # Try without auth headers
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        print(f"No auth - Status: {response.status_code}")
        if response.status_code == 200:
            print(f"  Content: {response.text[:200]}")
    except Exception as e:
        print(f"No auth failed: {e}")
    
    # Try with basic auth or other methods if needed
    print()
    print("💡 Suggestions:")
    print("1. Check if the service is running on UNRAID")
    print("2. Verify Cloudflare Access configuration")
    print("3. Check if the service is listening on the correct port")
    print("4. Try accessing from the UNRAID console directly")

if __name__ == "__main__":
    check_deployment()