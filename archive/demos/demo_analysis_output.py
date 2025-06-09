#!/usr/bin/env python3
"""
Demo of what the analysis output looks like with simulated data
"""

import responses
from src.scraper.poe_ninja_client import PoeNinjaClient
from src.data.skill_tags import skill_analyzer
from collections import Counter
import random


def create_mock_build_data():
    """Create realistic mock build data for demonstration"""
    # Popular skills with their typical usage rates
    skill_distribution = {
        # Melee skills
        "Boneshatter": 120,
        "Lightning Strike": 110,
        "Cyclone": 80,
        "Ice Crash": 45,
        "Molten Strike": 35,
        "Heavy Strike": 15,
        "Lacerate": 25,
        "Frost Blades": 40,
        
        # Spell skills
        "Righteous Fire": 150,
        "Arc": 85,
        "Spark": 75,
        "Ice Nova": 60,
        "Essence Drain": 55,
        "Fireball": 30,
        "Winter Orb": 25,
        "Freezing Pulse": 20,
        
        # Minion skills
        "Raise Spectre": 95,
        "Raise Zombie": 40,
        "Summon Skeletons": 35,
        
        # Other
        "Toxic Rain": 65,
        "Caustic Arrow": 25,
    }
    
    # Popular classes
    classes = {
        "Juggernaut": 180,
        "Necromancer": 170,
        "Deadeye": 140,
        "Elementalist": 130,
        "Champion": 120,
        "Assassin": 100,
        "Trickster": 90,
        "Chieftain": 70,
    }
    
    # Generate character data
    characters = []
    char_id = 0
    
    for skill, count in skill_distribution.items():
        for _ in range(count):
            # Assign appropriate class based on skill
            if skill in ["Raise Spectre", "Raise Zombie", "Summon Skeletons"]:
                char_class = "Necromancer"
            elif skill in ["Boneshatter", "Heavy Strike", "Molten Strike"]:
                char_class = random.choice(["Juggernaut", "Champion", "Chieftain"])
            elif skill in ["Lightning Strike", "Ice Crash", "Frost Blades"]:
                char_class = random.choice(["Deadeye", "Champion", "Raider"])
            elif skill in ["Arc", "Spark", "Winter Orb"]:
                char_class = random.choice(["Elementalist", "Assassin", "Trickster"])
            else:
                char_class = random.choice(list(classes.keys()))
            
            level = random.choices(
                [100, 99, 98, 97, 96, 95, 94, 93, 92, 91, 90],
                weights=[15, 10, 10, 8, 8, 20, 10, 5, 5, 5, 4]
            )[0]
            
            characters.append({
                "account": f"Player{char_id}",
                "name": f"Character_{char_id}",
                "level": level,
                "class": char_class,
                "ascendancy": char_class,
                "experience": 1000000000 + char_id * 1000000,
                "depth": {
                    "default": random.randint(200, 1500),
                    "solo": random.randint(150, 1200)
                },
                "life": random.randint(3500, 8000),
                "energyShield": random.randint(0, 3000),
                "dps": random.randint(500000, 10000000),
                "mainSkill": skill,
                "skills": [skill] + random.sample([
                    "Ancestral Warchief", "Ancestral Protector", "Blood Rage",
                    "Molten Shell", "Determination", "Grace", "Hatred"
                ], k=random.randint(2, 4)),
                "uniques": random.sample([
                    "Headhunter", "Mageblood", "The Squire", "Aegis Aurora",
                    "Ashes of the Stars", "Melding of the Flesh", "The Brass Dome",
                    "Shavs", "The Baron", "Mon'tregul's Grasp"
                ], k=random.randint(1, 3)),
                "rank": char_id + 1
            })
            char_id += 1
    
    return {"data": characters}


@responses.activate
def run_analysis_demo():
    """Run the analysis with mock data to show output"""
    # Set up mock response
    mock_data = create_mock_build_data()
    
    responses.add(
        responses.GET,
        "https://poe.ninja/api/data/0/getbuildoverview",
        json=mock_data,
        status=200
    )
    
    # Create client and run analysis
    client = PoeNinjaClient(league="Standard")
    
    print("=" * 80)
    print("POE NINJA BUILD ANALYSIS OUTPUT DEMO")
    print("=" * 80)
    print()
    
    # Fetch and analyze builds
    builds = client.get_builds_analysis(overview_type="exp")
    
    if not builds:
        print("Failed to fetch build data")
        return
    
    print(f"=== Experience Ladder Analysis ===")
    print(f"Total characters analyzed: {builds.total_characters}")
    print()
    
    # Class distribution
    print("Class Distribution:")
    for class_name, count in sorted(builds.class_distribution.items(), 
                                   key=lambda x: x[1], reverse=True):
        percentage = (count / builds.total_characters) * 100
        bar = "█" * int(percentage / 2)
        print(f"  {class_name:<15} {count:>4} ({percentage:>5.1f}%) {bar}")
    
    print("\n" + "-" * 60 + "\n")
    
    # Skill type distribution
    print("Skill Type Distribution:")
    skill_categories = builds.get_skill_category_distribution()
    total_categorized = sum(skill_categories.values())
    
    for category, count in sorted(skill_categories.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_categorized * 100) if total_categorized > 0 else 0
        bar = "█" * int(percentage / 2)
        print(f"  {category:<10} {count:>4} ({percentage:>5.1f}%) {bar}")
    
    print("\n" + "-" * 60 + "\n")
    
    # Top skills overall
    print("Top 10 Most Used Skills:")
    top_skills = sorted(builds.skill_popularity.items(), 
                       key=lambda x: x[1], reverse=True)[:10]
    for i, (skill, count) in enumerate(top_skills, 1):
        percentage = (count / builds.total_characters) * 100
        tags = skill_analyzer.get_skill_tags(skill)
        tag_str = f"[{', '.join(tags[:3])}]" if tags else "[Unknown]"
        print(f"  {i:>2}. {skill:<20} {count:>4} players ({percentage:>5.1f}%) {tag_str}")
    
    print("\n" + "-" * 60 + "\n")
    
    # Damage type analysis
    print("Damage Type Distribution:")
    damage_distribution = builds.analyze_damage_types()
    
    for damage_type, count in sorted(damage_distribution.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / builds.total_characters * 100)
        bar = "█" * int(percentage / 2)
        print(f"  {damage_type:<10} {count:>4} builds ({percentage:>5.1f}%) {bar}")
    
    print("\n" + "-" * 60 + "\n")
    
    # Melee vs Spell breakdown
    print("Combat Style Analysis:")
    melee_builds = builds.get_melee_builds()
    spell_builds = builds.get_spell_builds()
    
    print(f"  Melee builds: {len(melee_builds)} ({len(melee_builds)/builds.total_characters*100:.1f}%)")
    print(f"  Spell builds: {len(spell_builds)} ({len(spell_builds)/builds.total_characters*100:.1f}%)")
    
    # Top melee skills
    print("\n  Top 5 Melee Skills:")
    melee_skills = Counter(char.main_skill for char in melee_builds if char.main_skill)
    for skill, count in melee_skills.most_common(5):
        print(f"    - {skill}: {count} players")
    
    # Top spell skills
    print("\n  Top 5 Spell Skills:")
    spell_skills = Counter(char.main_skill for char in spell_builds if char.main_skill)
    for skill, count in spell_skills.most_common(5):
        print(f"    - {skill}: {count} players")
    
    print("\n" + "-" * 60 + "\n")
    
    # Cold damage specific analysis
    print("=== Cold Damage Build Deep Dive ===")
    cold_builds = builds.get_builds_by_damage_type("Cold")
    print(f"Total cold damage builds: {len(cold_builds)}")
    
    if cold_builds:
        # Class distribution for cold builds
        cold_classes = Counter(char.class_name for char in cold_builds)
        print("\nClasses using cold skills:")
        for class_name, count in cold_classes.most_common():
            percentage = (count / len(cold_builds)) * 100
            print(f"  {class_name:<15} {count:>3} ({percentage:>5.1f}%)")
        
        # Popular cold skills
        cold_skills = Counter(char.main_skill for char in cold_builds if char.main_skill)
        print("\nMost popular cold skills:")
        for skill, count in cold_skills.most_common():
            tags = skill_analyzer.get_skill_tags(skill)
            melee_tag = "Melee" if "Melee" in tags else "Spell"
            print(f"  {skill:<20} {count:>3} players ({melee_tag})")
    
    print("\n" + "-" * 60 + "\n")
    
    # Level distribution
    level_dist = builds.get_level_distribution()
    print("Level Distribution:")
    print(f"  Level 100: {level_dist.get(100, 0)} characters")
    print(f"  Level 99:  {level_dist.get(99, 0)} characters")
    print(f"  Level 98:  {level_dist.get(98, 0)} characters")
    print(f"  Level 95+: {sum(count for level, count in level_dist.items() if level >= 95)} characters")
    print(f"  Level 90+: {sum(count for level, count in level_dist.items() if level >= 90)} characters")
    
    print("\n" + "-" * 60 + "\n")
    
    # Top unique items
    print("Top 10 Most Used Unique Items:")
    top_uniques = sorted(builds.unique_usage.items(), 
                        key=lambda x: x[1], reverse=True)[:10]
    for i, (item, count) in enumerate(top_uniques, 1):
        percentage = (count / builds.total_characters) * 100
        print(f"  {i:>2}. {item:<25} {count:>4} players ({percentage:>5.1f}%)")
    
    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    run_analysis_demo()