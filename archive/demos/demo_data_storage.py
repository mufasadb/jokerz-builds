#!/usr/bin/env python3
"""
Demo showing data fetching and storage
"""

import responses
from src.scraper.poe_ninja_client import PoeNinjaClient
from src.storage.data_explorer import DataExplorer
from datetime import datetime
import json


def create_mock_data():
    """Create some mock data for demonstration"""
    return {
        "builds": {
            "data": [
                {
                    "account": "TestPlayer1",
                    "name": "SuperBuilder",
                    "level": 100,
                    "class": "Necromancer",
                    "ascendancy": "Necromancer",
                    "experience": 4250334444,
                    "depth": {"default": 1000, "solo": 800},
                    "life": 5000,
                    "energyShield": 2000,
                    "mainSkill": "Raise Spectre",
                    "skills": ["Raise Spectre", "Desecrate", "Bone Offering"],
                    "uniques": ["The Baron", "Mon'tregul's Grasp"],
                    "rank": 1
                },
                {
                    "account": "TestPlayer2",
                    "name": "ZoomZoom",
                    "level": 98,
                    "class": "Deadeye",
                    "ascendancy": "Deadeye",
                    "experience": 3500000000,
                    "mainSkill": "Lightning Strike",
                    "skills": ["Lightning Strike", "Ancestral Protector"],
                    "rank": 2
                }
            ]
        },
        "currency": {
            "lines": [
                {
                    "currencyTypeName": "Chaos Orb",
                    "chaosEquivalent": 1,
                    "pay": {"value": 1},
                    "receive": {"value": 1}
                },
                {
                    "currencyTypeName": "Divine Orb",
                    "chaosEquivalent": 200,
                    "pay": {"value": 0.005},
                    "receive": {"value": 200}
                }
            ]
        },
        "items": {
            "lines": [
                {
                    "name": "Headhunter",
                    "baseType": "Leather Belt",
                    "chaosValue": 15000,
                    "divineValue": 75,
                    "listingCount": 42
                },
                {
                    "name": "Shavs",
                    "baseType": "Occultist's Vestment",
                    "chaosValue": 300,
                    "divineValue": 1.5,
                    "listingCount": 156
                }
            ]
        }
    }


@responses.activate
def demo_data_storage():
    """Demonstrate data fetching and storage"""
    print("=" * 80)
    print("DATA STORAGE DEMO")
    print("=" * 80)
    print()
    
    # Set up mock responses
    mock_data = create_mock_data()
    
    # Mock build data
    responses.add(
        responses.GET,
        "https://poe.ninja/api/data/0/getbuildoverview",
        json=mock_data["builds"],
        status=200
    )
    
    # Mock currency data
    responses.add(
        responses.GET,
        "https://poe.ninja/api/data/currencyoverview",
        json=mock_data["currency"],
        status=200
    )
    
    # Mock item data
    responses.add(
        responses.GET,
        "https://poe.ninja/api/data/itemoverview",
        json=mock_data["items"],
        status=200
    )
    
    # Create client with storage enabled
    print("1. Creating PoE Ninja client with storage enabled...")
    client = PoeNinjaClient(league="DemoLeague", save_to_disk=True)
    
    # Fetch and store build data
    print("\n2. Fetching current build data...")
    builds = client.get_build_overview()
    if builds:
        print(f"   ✓ Fetched {len(builds.get('data', []))} characters")
        print(f"   ✓ Data automatically saved to: data/builds/")
    
    # Fetch historical build data
    print("\n3. Fetching week-1 build data...")
    historical_builds = client.get_build_overview(time_machine="week-1")
    if historical_builds:
        print(f"   ✓ Fetched {len(historical_builds.get('data', []))} characters")
        print(f"   ✓ Data automatically saved with 'week-1' snapshot")
    
    # Fetch currency data
    print("\n4. Fetching currency data...")
    currency = client.get_currency_overview()
    if currency:
        print(f"   ✓ Fetched {len(currency.get('lines', []))} currency types")
        print(f"   ✓ Data automatically saved to: data/currency/")
    
    # Fetch item data
    print("\n5. Fetching item price data...")
    items = client.get_item_overview("UniqueWeapon")
    if items:
        print(f"   ✓ Fetched {len(items.get('lines', []))} unique weapons")
        print(f"   ✓ Data automatically saved to: data/items/")
    
    # Fetch historical item data
    print("\n6. Fetching week-1 item prices...")
    historical_items = client.get_item_overview("UniqueWeapon", date="2024-01-15")
    if historical_items:
        print(f"   ✓ Fetched {len(historical_items.get('lines', []))} items")
        print(f"   ✓ Data automatically saved with date stamp")
    
    print("\n" + "=" * 80)
    print("DATA EXPLORATION")
    print("=" * 80)
    
    # Create data explorer
    explorer = DataExplorer()
    
    # Show storage report
    print("\n7. Storage Report:")
    explorer.print_storage_report()
    
    # Load and analyze stored data
    print("\n8. Loading stored build data...")
    stored_builds = explorer.load_and_analyze_builds("DemoLeague", "current")
    if stored_builds:
        print(f"   ✓ Loaded {stored_builds.total_characters} characters")
        print(f"   ✓ Classes: {list(stored_builds.class_distribution.keys())}")
        print(f"   ✓ Skills: {list(stored_builds.skill_popularity.keys())[:5]}")
    
    # Show file structure
    print("\n9. File Structure Created:")
    print("   data/")
    print("   ├── builds/")
    print("   │   ├── demoleague_current.json")
    print("   │   └── demoleague_week-1.json")
    print("   ├── currency/")
    print("   │   └── demoleague_" + datetime.now().strftime("%Y-%m-%d") + ".json")
    print("   ├── items/")
    print("   │   ├── demoleague_" + datetime.now().strftime("%Y-%m-%d") + "_uniqueweapon.json")
    print("   │   └── demoleague_2024-01-15_uniqueweapon.json")
    print("   └── analysis/")
    
    print("\n10. Sample Stored Data Structure:")
    print("    Each file contains:")
    print("    - metadata: league, date, fetch time, item count")
    print("    - data: the actual API response data")
    
    # Example of direct file access
    print("\n11. Direct File Access Example:")
    try:
        with open("data/builds/demoleague_current.json", 'r') as f:
            stored_data = json.load(f)
            print(f"    Metadata: {json.dumps(stored_data['metadata'], indent=2)}")
    except FileNotFoundError:
        print("    (Files will be created when you run with real API)")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\n✓ All API data is automatically saved to the 'data/' directory")
    print("✓ Files are organized by type: builds/, items/, currency/, analysis/")
    print("✓ Files are named with league, date/snapshot, and type")
    print("✓ Each file includes metadata about when it was fetched")
    print("✓ Data can be loaded and analyzed offline using DataExplorer")
    print("✓ Historical comparisons can be done using stored snapshots")
    print("\nTo disable storage, create client with: save_to_disk=False")


if __name__ == "__main__":
    demo_data_storage()