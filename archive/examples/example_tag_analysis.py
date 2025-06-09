#!/usr/bin/env python3
"""
Example of analyzing builds by skill tags (melee, spell, damage types, etc.)
"""

from src.scraper.poe_ninja_client import PoeNinjaClient
from src.data.skill_tags import skill_analyzer
from collections import Counter


def analyze_by_skill_types(league: str = "Standard"):
    """Analyze builds by skill types and damage categories"""
    client = PoeNinjaClient(league=league)
    
    print(f"Analyzing {league} builds by skill types...\n")
    
    # Fetch build data
    builds = client.get_builds_analysis(overview_type="exp")
    
    if not builds:
        print("Failed to fetch build data")
        return
    
    # Basic skill type distribution
    print("=== Skill Type Distribution ===")
    skill_categories = builds.get_skill_category_distribution()
    total_categorized = sum(skill_categories.values())
    
    for category, count in sorted(skill_categories.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_categorized * 100) if total_categorized > 0 else 0
        print(f"{category}: {count} ({percentage:.1f}%)")
    
    # Melee vs Spell analysis
    print("\n=== Melee vs Spell Builds ===")
    melee_builds = builds.get_melee_builds()
    spell_builds = builds.get_spell_builds()
    
    print(f"Melee builds: {len(melee_builds)} ({len(melee_builds)/builds.total_characters*100:.1f}%)")
    print(f"Spell builds: {len(spell_builds)} ({len(spell_builds)/builds.total_characters*100:.1f}%)")
    
    # Top melee skills
    print("\nTop 5 Melee Skills:")
    melee_skills = Counter(char.main_skill for char in melee_builds if char.main_skill)
    for skill, count in melee_skills.most_common(5):
        print(f"  {skill}: {count} players")
    
    # Top spell skills
    print("\nTop 5 Spell Skills:")
    spell_skills = Counter(char.main_skill for char in spell_builds if char.main_skill)
    for skill, count in spell_skills.most_common(5):
        print(f"  {skill}: {count} players")
    
    # Damage type analysis
    print("\n=== Damage Type Distribution ===")
    damage_distribution = builds.analyze_damage_types()
    
    for damage_type, count in sorted(damage_distribution.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / builds.total_characters * 100)
        print(f"{damage_type}: {count} builds ({percentage:.1f}%)")
    
    # Cold/Ice build analysis
    print("\n=== Cold Damage Build Analysis ===")
    cold_builds = builds.get_builds_by_damage_type("Cold")
    print(f"Total cold damage builds: {len(cold_builds)}")
    
    if cold_builds:
        # Class distribution for cold builds
        cold_classes = Counter(char.class_name for char in cold_builds)
        print("\nTop classes using cold skills:")
        for class_name, count in cold_classes.most_common(5):
            print(f"  {class_name}: {count}")
        
        # Popular cold skills
        cold_skills = Counter(char.main_skill for char in cold_builds if char.main_skill)
        print("\nMost popular cold skills:")
        for skill, count in cold_skills.most_common(5):
            tags = skill_analyzer.get_skill_tags(skill)
            tag_str = ", ".join(tags[:3]) if tags else "Unknown"
            print(f"  {skill}: {count} players [{tag_str}]")
    
    # Fire build analysis
    print("\n=== Fire Damage Build Analysis ===")
    fire_builds = builds.get_builds_by_damage_type("Fire")
    print(f"Total fire damage builds: {len(fire_builds)}")
    
    if fire_builds:
        fire_skills = Counter(char.main_skill for char in fire_builds if char.main_skill)
        print("\nMost popular fire skills:")
        for skill, count in fire_skills.most_common(5):
            tags = skill_analyzer.get_skill_tags(skill)
            tag_str = ", ".join(tags[:3]) if tags else "Unknown"
            print(f"  {skill}: {count} players [{tag_str}]")
    
    # Hybrid analysis - Melee Cold skills
    print("\n=== Hybrid Analysis: Melee Cold Skills ===")
    melee_cold_skills = skill_analyzer.get_skills_by_tags(["Melee", "Cold"], match_all=True)
    print(f"Available melee cold skills: {', '.join(melee_cold_skills)}")
    
    melee_cold_chars = [
        char for char in builds.characters
        if char.main_skill in melee_cold_skills
    ]
    print(f"Characters using melee cold skills: {len(melee_cold_chars)}")
    
    if melee_cold_chars:
        for char in melee_cold_chars[:5]:
            print(f"  {char.name} ({char.class_name}) - {char.main_skill}")


def analyze_skill_combinations():
    """Demonstrate skill tag analysis capabilities"""
    print("\n=== Skill Tag Analysis Examples ===\n")
    
    # Show all melee skills
    melee_skills = skill_analyzer.get_skills_by_tag("Melee")
    print(f"Total melee skills in database: {len(melee_skills)}")
    print(f"Examples: {', '.join(list(melee_skills)[:10])}")
    
    # Show all cold skills
    cold_skills = skill_analyzer.get_skills_by_tag("Cold")
    print(f"\nTotal cold skills in database: {len(cold_skills)}")
    print(f"Examples: {', '.join(list(cold_skills)[:10])}")
    
    # Complex queries
    print("\n=== Complex Tag Queries ===")
    
    # Channelling melee skills
    channelling_melee = skill_analyzer.get_skills_by_tags(["Channelling", "Melee"], match_all=True)
    print(f"\nChannelling Melee skills: {', '.join(channelling_melee)}")
    
    # AoE Fire or Cold skills
    elemental_aoe = skill_analyzer.get_skills_by_tags(["AoE", "Fire"], match_all=True)
    elemental_aoe.update(skill_analyzer.get_skills_by_tags(["AoE", "Cold"], match_all=True))
    print(f"\nAoE Fire/Cold skills: {', '.join(list(elemental_aoe)[:10])}")
    
    # Movement skills
    movement_skills = skill_analyzer.get_skills_by_tag("Movement")
    print(f"\nMovement skills: {', '.join(movement_skills)}")


if __name__ == "__main__":
    # Analyze builds by skill types
    analyze_by_skill_types("Standard")
    
    # Show skill tag analysis capabilities
    analyze_skill_combinations()