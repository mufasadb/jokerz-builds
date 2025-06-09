#!/usr/bin/env python3
"""
Joker Builds - Main Application
Fetches and analyzes Path of Exile build data from poe.ninja
"""

import argparse
import sys
from datetime import datetime
from src.scraper.poe_ninja_client import PoeNinjaClient
from src.storage.data_explorer import DataExplorer
from src.analysis.league_progression import LeagueProgressionAnalyzer


def fetch_current_data(league: str):
    """Fetch current build and economy data"""
    print(f"\n=== Fetching Current Data for {league} ===")
    
    client = PoeNinjaClient(league=league)
    
    # Fetch build data
    print("\n1. Fetching current build data...")
    builds = client.get_builds_analysis(overview_type="exp")
    
    if builds:
        print(f"   ✓ Retrieved {builds.total_characters} characters")
        
        # Show top classes
        print("\n   Top 5 Classes:")
        for i, (class_name, count) in enumerate(list(builds.class_distribution.items())[:5], 1):
            percentage = (count / builds.total_characters) * 100
            print(f"   {i}. {class_name}: {count} ({percentage:.1f}%)")
        
        # Show top skills
        print("\n   Top 5 Skills:")
        top_skills = sorted(builds.skill_popularity.items(), key=lambda x: x[1], reverse=True)[:5]
        for i, (skill, count) in enumerate(top_skills, 1):
            percentage = (count / builds.total_characters) * 100
            print(f"   {i}. {skill}: {count} ({percentage:.1f}%)")
    else:
        print("   ✗ Failed to fetch build data")
    
    # Fetch currency data
    print("\n2. Fetching currency exchange rates...")
    currency = client.get_currency_overview()
    
    if currency and "lines" in currency:
        print(f"   ✓ Retrieved {len(currency['lines'])} currency types")
        
        # Show key currency values
        for curr in currency["lines"][:5]:
            name = curr.get("currencyTypeName", "Unknown")
            value = curr.get("chaosEquivalent", 0)
            print(f"   - {name}: {value:.2f} chaos")
    else:
        print("   ✗ Failed to fetch currency data")
    
    # Fetch some item prices
    print("\n3. Fetching unique item prices...")
    items = client.get_item_overview("UniqueWeapon")
    
    if items and "lines" in items:
        print(f"   ✓ Retrieved {len(items['lines'])} unique weapons")
        
        # Show most expensive items
        sorted_items = sorted(items["lines"], key=lambda x: x.get("chaosValue", 0), reverse=True)
        print("\n   Most Expensive Weapons:")
        for item in sorted_items[:5]:
            name = item.get("name", "Unknown")
            chaos = item.get("chaosValue", 0)
            divine = item.get("divineValue", 0)
            print(f"   - {name}: {chaos:.0f}c ({divine:.2f} div)")
    else:
        print("   ✗ Failed to fetch item data")
    
    return builds, currency, items


def analyze_stored_data(league: str):
    """Analyze previously stored data"""
    print(f"\n=== Analyzing Stored Data for {league} ===")
    
    explorer = DataExplorer()
    
    # Show storage summary
    print("\nStorage Summary:")
    summary = explorer.data_manager.get_storage_summary()
    print(f"  Total Size: {summary['total_size_mb']} MB")
    print(f"  Leagues: {', '.join(summary['leagues'])}")
    
    # List available snapshots
    saved_builds = explorer.data_manager.list_saved_builds(league)
    if saved_builds:
        print(f"\n  Available Build Snapshots for {league}:")
        for build_info in saved_builds[:5]:
            print(f"  - {build_info['snapshot']}: {build_info['modified']}")
    
    # Load and analyze latest data
    latest = explorer.load_and_analyze_builds(league, "current")
    if latest:
        print(f"\n  Latest snapshot has {latest.total_characters} characters")
        
        # Skill category distribution
        categories = latest.get_skill_category_distribution()
        print("\n  Build Types:")
        for category, count in categories.items():
            print(f"  - {category}: {count}")


def compare_snapshots(league: str, snapshot1: str, snapshot2: str):
    """Compare two snapshots"""
    explorer = DataExplorer()
    explorer.compare_snapshots(league, snapshot1, snapshot2)


def main():
    parser = argparse.ArgumentParser(description="Joker Builds - PoE Build Analysis")
    parser.add_argument("command", choices=["fetch", "analyze", "compare", "progression"],
                       help="Command to run")
    parser.add_argument("--league", default="Settlers",
                       help="League to analyze (default: current challenge league)")
    parser.add_argument("--snapshot1", help="First snapshot for comparison")
    parser.add_argument("--snapshot2", help="Second snapshot for comparison")
    parser.add_argument("--start-date", help="League start date (YYYY-MM-DD) for progression")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("JOKER BUILDS - Path of Exile Build Analysis")
    print("=" * 80)
    
    if args.command == "fetch":
        fetch_current_data(args.league)
    
    elif args.command == "analyze":
        analyze_stored_data(args.league)
    
    elif args.command == "compare":
        if not args.snapshot1 or not args.snapshot2:
            print("Error: --snapshot1 and --snapshot2 required for compare")
            sys.exit(1)
        compare_snapshots(args.league, args.snapshot1, args.snapshot2)
    
    elif args.command == "progression":
        if not args.start_date:
            print("Error: --start-date required for progression analysis")
            print("Example: --start-date 2024-03-29")
            sys.exit(1)
        
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        except ValueError:
            print("Error: Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
        
        from src.analysis.league_progression import analyze_league_progression
        analyze_league_progression(args.league, args.start_date)
    
    print("\n" + "=" * 80)
    print("Analysis complete!")


if __name__ == "__main__":
    main()