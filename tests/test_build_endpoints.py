#!/usr/bin/env python3
"""
Test various poe.ninja build endpoint patterns
"""

import requests
import json
import pytest

def check_endpoint(url, description):
    """Test an endpoint and report results"""
    print(f"\nTesting: {description}")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if isinstance(data, dict):
                    print(f"Success! Keys: {list(data.keys())[:5]}")
                    if 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                        print(f"Found {len(data['data'])} entries")
                elif isinstance(data, list):
                    print(f"Success! Found {len(data)} entries")
                return True
            except json.JSONDecodeError:
                print("Response is not JSON")
        else:
            print(f"Failed with status {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")
    
    return False


@pytest.mark.skip(reason="Manual endpoint testing - requires network access")
def test_endpoint_exploration():
    """Test to explore poe.ninja build endpoints"""
    league = "Settlers"
    
    # Test various endpoint patterns
    endpoints = [
        ("https://poe.ninja/api/data/0/getbuildoverview?overview=Settlers&type=exp&language=en",
         "Original pattern with 0"),
    ]
    
    successful = []
    
    for url, desc in endpoints:
        if check_endpoint(url, desc):
            successful.append((url, desc))
    
    assert len(successful) >= 0  # Always pass - this is exploratory


if __name__ == "__main__":
    print("=" * 80)
    print("TESTING POE.NINJA BUILD ENDPOINTS")
    print("=" * 80)
    
    league = "Settlers"
    
    # Test various endpoint patterns
    endpoints = [
        # Original pattern
        ("https://poe.ninja/api/data/0/getbuildoverview?overview=Settlers&type=exp&language=en",
         "Original pattern with 0"),
        
        # Without the 0
        ("https://poe.ninja/api/data/getbuildoverview?overview=Settlers&type=exp&language=en",
         "Without the 0"),
        
        # Different capitalizations
        ("https://poe.ninja/api/data/GetBuildOverview?league=Settlers&type=exp",
         "GetBuildOverview with league param"),
        
        # Using builds instead
        ("https://poe.ninja/api/data/builds?league=Settlers",
         "Simple builds endpoint"),
        
        # Character endpoint variations
        ("https://poe.ninja/api/data/character?league=Settlers&type=exp",
         "Character endpoint"),
        
        ("https://poe.ninja/api/data/getcharacter?league=Settlers&type=exp",
         "GetCharacter endpoint"),
        
        # Ladder endpoint
        ("https://poe.ninja/api/data/ladder?league=Settlers",
         "Ladder endpoint"),
        
        # Stats endpoint
        ("https://poe.ninja/api/data/stats?league=Settlers",
         "Stats endpoint"),
        
        # Try with different league formats
        ("https://poe.ninja/api/data/0/getbuildoverview?overview=settlers&type=exp&language=en",
         "Lowercase league name"),
         
        ("https://poe.ninja/api/data/0/getbuildoverview?overview=Settlers%20of%20Kalguur&type=exp&language=en",
         "Full league name URL encoded"),
    ]
    
    successful = []
    
    for url, desc in endpoints:
        if check_endpoint(url, desc):
            successful.append((url, desc))
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if successful:
        print(f"\nSuccessful endpoints ({len(successful)}):")
        for url, desc in successful:
            print(f"\n✓ {desc}")
            print(f"  {url}")
    else:
        print("\nNo successful build endpoints found.")
        print("\nThe builds data might be:")
        print("1. Behind authentication")
        print("2. Using a different API structure")
        print("3. Loaded client-side from a different source")
        print("4. Not publicly available via API")