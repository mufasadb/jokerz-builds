#!/usr/bin/env python3
"""
Demo showing league progression analysis with mock data
"""

import responses
from datetime import datetime, timedelta
from src.analysis.league_progression import LeagueProgressionAnalyzer
import random


def create_mock_snapshot_data(week_number: int):
    """Create mock build data for different league stages"""
    
    # Simulate meta shifts throughout the league
    if week_number == 1:
        # Week 1: Starter builds dominate
        skill_weights = {
            "Righteous Fire": 200,
            "Boneshatter": 180,
            "Lightning Strike": 150,
            "Toxic Rain": 120,
            "Essence Drain": 100,
            "Arc": 80,
            "Caustic Arrow": 70,
            "Summon Skeletons": 60,
            "Cyclone": 40,
            "Ice Nova": 30,
        }
        total_chars = 8000
        
    elif week_number == 2:
        # Week 2: Some builds start emerging
        skill_weights = {
            "Lightning Strike": 220,
            "Boneshatter": 200,
            "Righteous Fire": 180,
            "Toxic Rain": 100,
            "Ice Nova": 90,
            "Arc": 85,
            "Spark": 80,
            "Raise Spectre": 75,
            "Cyclone": 70,
            "Essence Drain": 60,
        }
        total_chars = 12000
        
    elif week_number == 6:
        # Mid-league: Meta has settled
        skill_weights = {
            "Lightning Strike": 300,
            "Boneshatter": 250,
            "Ice Nova": 200,
            "Spark": 180,
            "Righteous Fire": 150,
            "Raise Spectre": 140,
            "Molten Strike": 120,
            "Cyclone": 100,
            "Arc": 90,
            "Winter Orb": 80,
        }
        total_chars = 15000
        
    else:  # Late league / current
        # Late league: Min-maxed builds
        skill_weights = {
            "Lightning Strike": 280,
            "Ice Nova": 240,
            "Spark": 220,
            "Boneshatter": 200,
            "Molten Strike": 180,
            "Winter Orb": 160,
            "Raise Spectre": 150,
            "Righteous Fire": 100,
            "Cyclone": 90,
            "Frost Blades": 80,
        }
        total_chars = 10000
    
    # Generate character data
    characters = []
    char_id = 0
    
    # Distribute characters based on weights
    for skill, weight in skill_weights.items():
        num_chars = int((weight / sum(skill_weights.values())) * total_chars)
        
        for _ in range(num_chars):
            # Assign class based on skill type
            if skill in ["Raise Spectre", "Summon Skeletons"]:
                char_class = "Necromancer"
            elif skill in ["Boneshatter", "Molten Strike", "Cyclone"]:
                char_class = random.choice(["Juggernaut", "Champion", "Berserker"])
            elif skill in ["Lightning Strike", "Ice Nova", "Spark"]:
                char_class = random.choice(["Deadeye", "Elementalist", "Assassin"])
            elif skill == "Righteous Fire":
                char_class = random.choice(["Juggernaut", "Chieftain", "Inquisitor"])
            else:
                char_class = random.choice(["Trickster", "Pathfinder", "Raider", "Occultist"])
            
            characters.append({
                "account": f"Player{char_id}",
                "name": f"Char_{char_id}",
                "level": random.randint(90, 100),
                "class": char_class,
                "ascendancy": char_class,
                "experience": random.randint(1000000000, 4250000000),
                "mainSkill": skill,
                "skills": [skill],
                "rank": char_id + 1
            })
            char_id += 1
    
    return {"data": characters}


def create_mock_price_data(week_number: int):
    """Create mock price data showing typical league economy progression"""
    
    # Simulate price changes throughout league
    price_multipliers = {
        1: 1.0,      # Week 1 baseline
        2: 0.8,      # Week 2 prices drop as supply increases
        6: 0.5,      # Mid-league prices stabilize lower
        12: 0.3,     # Late league most items are cheap
        99: 0.25     # Current (end of league)
    }
    
    multiplier = price_multipliers.get(week_number, 0.25)
    
    # Base prices (week 1 values)
    items = {
        "Headhunter": {
            "base_chaos": 15000,
            "divine_ratio": 200,  # chaos per divine
            "rarity_factor": 1.2  # Stays expensive
        },
        "Shavs": {
            "base_chaos": 300,
            "divine_ratio": 200,
            "rarity_factor": 0.8
        },
        "Ashes of the Stars": {
            "base_chaos": 800,
            "divine_ratio": 200,
            "rarity_factor": 0.9
        },
        "The Doctor": {
            "base_chaos": 2000,
            "divine_ratio": 200,
            "rarity_factor": 1.1
        },
        "Melding of the Flesh": {
            "base_chaos": 400,
            "divine_ratio": 200,
            "rarity_factor": 0.7
        }
    }
    
    lines = []
    for item_name, data in items.items():
        # Apply multiplier with some variance
        variance = random.uniform(0.9, 1.1)
        chaos_value = data["base_chaos"] * multiplier * data["rarity_factor"] * variance
        
        # Divine value changes throughout league
        divine_ratio = data["divine_ratio"] * (1 + (week_number - 1) * 0.1)  # Divines get more expensive
        divine_value = chaos_value / divine_ratio
        
        lines.append({
            "name": item_name,
            "chaosValue": round(chaos_value, 1),
            "divineValue": round(divine_value, 2),
            "listingCount": random.randint(10, 200)
        })
    
    return {"lines": lines}


@responses.activate
def run_progression_demo():
    """Run the league progression analysis demo"""
    
    # Mock league start date (3 months ago)
    league_start = datetime.now() - timedelta(days=90)
    
    # Set up mock responses for different snapshots
    base_url = "https://poe.ninja/api/data"
    
    # Build data mocks
    week_configs = [
        ("", 99),       # Current
        ("week-1", 1),
        ("week-2", 2),
        ("week-6", 6),
        ("week-12", 12),
    ]
    
    for timemachine, week_num in week_configs:
        url = f"{base_url}/0/getbuildoverview"
        responses.add(
            responses.GET,
            url,
            json=create_mock_snapshot_data(week_num),
            status=200
        )
    
    # Price data mocks for each date
    dates_and_weeks = [
        ((league_start + timedelta(days=7)).strftime("%Y-%m-%d"), 1),
        ((league_start + timedelta(days=14)).strftime("%Y-%m-%d"), 2),
        ((league_start + timedelta(days=42)).strftime("%Y-%m-%d"), 6),
        ((league_start + timedelta(days=84)).strftime("%Y-%m-%d"), 12),
        (datetime.now().strftime("%Y-%m-%d"), 99),
    ]
    
    for date, week_num in dates_and_weeks:
        # Mock for each item type
        for item_type in ["UniqueWeapon", "UniqueArmour", "UniqueAccessory", "DivinationCard", "UniqueJewel"]:
            responses.add(
                responses.GET,
                f"{base_url}/itemoverview",
                json=create_mock_price_data(week_num),
                status=200
            )
    
    # Run the analysis
    print("=" * 80)
    print("LEAGUE PROGRESSION ANALYSIS DEMO")
    print("=" * 80)
    print()
    
    analyzer = LeagueProgressionAnalyzer(
        league="Settlers",
        league_start_date=league_start
    )
    
    # Analyze build progression
    print("Fetching build snapshots across the league...")
    build_snapshots = analyzer.analyze_build_progression()
    
    # Key items to track
    items_to_track = [
        ("UniqueWeapon", "Headhunter"),
        ("UniqueArmour", "Shavs"),
        ("UniqueAccessory", "Ashes of the Stars"),
        ("DivinationCard", "The Doctor"),
        ("UniqueJewel", "Melding of the Flesh"),
    ]
    
    print("\nFetching price history for key items...")
    price_history = analyzer.analyze_price_progression(items_to_track)
    
    # Generate and print report
    report = analyzer.generate_progression_report(build_snapshots, price_history)
    print("\n" + report)
    
    # Additional analysis
    print("\n" + "=" * 80)
    print("ADDITIONAL INSIGHTS")
    print("=" * 80)
    
    if "week_1" in build_snapshots and "current" in build_snapshots:
        week_1 = build_snapshots["week_1"]
        current = build_snapshots["current"]
        
        print("\nBuild Diversity Analysis:")
        print(f"  Week 1: {len(week_1.skill_popularity)} different skills used")
        print(f"  Current: {len(current.skill_popularity)} different skills used")
        
        # Find new skills that emerged
        week_1_skills = set(week_1.skill_popularity.keys())
        current_skills = set(current.skill_popularity.keys())
        
        new_skills = current_skills - week_1_skills
        if new_skills:
            print(f"\nSkills that emerged after week 1:")
            for skill in list(new_skills)[:5]:
                count = current.skill_popularity[skill]
                print(f"  - {skill}: {count} players")
        
        abandoned_skills = week_1_skills - current_skills
        if abandoned_skills:
            print(f"\nSkills abandoned since week 1:")
            for skill in list(abandoned_skills)[:5]:
                count = week_1.skill_popularity[skill]
                print(f"  - {skill}: was used by {count} players")


if __name__ == "__main__":
    run_progression_demo()