#!/usr/bin/env python3
"""
Example of analyzing PoE Ninja build data in bulk
"""

from src.scraper.poe_ninja_client import PoeNinjaClient
from collections import Counter


def analyze_meta_builds(league: str = "Standard"):
    """Analyze the current meta builds from PoE Ninja"""
    client = PoeNinjaClient(league=league)
    
    print(f"Analyzing builds for {league} league...\n")
    
    # Fetch experience ladder (top builds by level/experience)
    exp_builds = client.get_builds_analysis(overview_type="exp")
    
    if not exp_builds:
        print("Failed to fetch build data")
        return
    
    print(f"=== Experience Ladder Analysis ===")
    print(f"Total characters analyzed: {exp_builds.total_characters}")
    
    # Class distribution
    print("\nClass Distribution:")
    for class_name, count in sorted(exp_builds.class_distribution.items(), 
                                   key=lambda x: x[1], reverse=True):
        percentage = (count / exp_builds.total_characters) * 100
        print(f"  {class_name}: {count} ({percentage:.1f}%)")
    
    # Top skills
    print("\nTop 10 Most Used Skills:")
    top_skills = sorted(exp_builds.skill_popularity.items(), 
                       key=lambda x: x[1], reverse=True)[:10]
    for skill, count in top_skills:
        percentage = (count / exp_builds.total_characters) * 100
        print(f"  {skill}: {count} players ({percentage:.1f}%)")
    
    # Top unique items
    print("\nTop 10 Most Used Unique Items:")
    top_uniques = sorted(exp_builds.unique_usage.items(), 
                        key=lambda x: x[1], reverse=True)[:10]
    for item, count in top_uniques:
        percentage = (count / exp_builds.total_characters) * 100
        print(f"  {item}: {count} players ({percentage:.1f}%)")
    
    # Level distribution
    level_dist = exp_builds.get_level_distribution()
    print(f"\nLevel Distribution:")
    print(f"  Level 100: {level_dist.get(100, 0)} characters")
    print(f"  Level 95+: {sum(count for level, count in level_dist.items() if level >= 95)} characters")
    print(f"  Level 90+: {sum(count for level, count in level_dist.items() if level >= 90)} characters")
    
    # Now analyze delve builds
    print("\n\n=== Delve Ladder Analysis ===")
    delve_builds = client.get_builds_analysis(overview_type="depthsolo")
    
    if delve_builds:
        print(f"Total delve characters: {delve_builds.total_characters}")
        
        # Top delvers
        print("\nTop 10 Deepest Delvers:")
        top_delvers = delve_builds.get_top_delvers(10)
        for i, char in enumerate(top_delvers, 1):
            print(f"  {i}. {char.name} ({char.class_name}) - Depth: {char.delve_solo_depth}")
        
        # Delve meta analysis
        print("\nDelve Meta - Most Common Classes:")
        delve_classes = Counter(char.class_name for char in delve_builds.characters 
                               if char.delve_solo_depth and char.delve_solo_depth > 500)
        for class_name, count in delve_classes.most_common(5):
            print(f"  {class_name}: {count} deep delvers")
    
    # Historical comparison (if desired)
    print("\n\n=== Historical Comparison ===")
    print("Fetching data from 1 week ago...")
    
    historical_builds = client.get_builds_analysis(
        overview_type="exp", 
        time_machine="week-1"
    )
    
    if historical_builds:
        print(f"Characters 1 week ago: {historical_builds.total_characters}")
        print(f"Characters now: {exp_builds.total_characters}")
        print(f"Growth: {exp_builds.total_characters - historical_builds.total_characters} characters")
        
        # Compare skill popularity
        print("\nSkill popularity changes:")
        current_skills = set(exp_builds.skill_popularity.keys())
        old_skills = set(historical_builds.skill_popularity.keys())
        
        new_skills = current_skills - old_skills
        if new_skills:
            print(f"  New skills in meta: {', '.join(list(new_skills)[:5])}")
        
        dropped_skills = old_skills - current_skills
        if dropped_skills:
            print(f"  Skills fallen out of meta: {', '.join(list(dropped_skills)[:5])}")


def analyze_specific_build(league: str, class_filter: str, skill_filter: str):
    """Analyze specific build combinations"""
    client = PoeNinjaClient(league=league)
    
    print(f"\nAnalyzing {class_filter} builds using {skill_filter}...\n")
    
    builds = client.get_builds_analysis(overview_type="exp")
    if not builds:
        return
    
    # Filter to specific class and skill
    matching_chars = [
        char for char in builds.characters
        if char.class_name == class_filter and 
        char.skills and skill_filter in char.skills
    ]
    
    if not matching_chars:
        print(f"No {class_filter} characters using {skill_filter} found")
        return
    
    print(f"Found {len(matching_chars)} {class_filter} characters using {skill_filter}")
    
    # Analyze their stats
    avg_level = sum(char.level for char in matching_chars) / len(matching_chars)
    avg_life = sum(char.life or 0 for char in matching_chars) / len(matching_chars)
    avg_es = sum(char.energy_shield or 0 for char in matching_chars) / len(matching_chars)
    
    print(f"\nAverage Stats:")
    print(f"  Level: {avg_level:.1f}")
    print(f"  Life: {avg_life:.0f}")
    print(f"  Energy Shield: {avg_es:.0f}")
    
    # Common unique items
    all_uniques = []
    for char in matching_chars:
        if char.unique_items:
            all_uniques.extend(char.unique_items)
    
    unique_counts = Counter(all_uniques)
    print(f"\nMost Common Unique Items:")
    for item, count in unique_counts.most_common(5):
        percentage = (count / len(matching_chars)) * 100
        print(f"  {item}: {count} ({percentage:.0f}% of builds)")
    
    # Other common skills
    all_skills = []
    for char in matching_chars:
        if char.skills:
            all_skills.extend([s for s in char.skills if s != skill_filter])
    
    skill_counts = Counter(all_skills)
    print(f"\nCommonly Paired Skills:")
    for skill, count in skill_counts.most_common(5):
        percentage = (count / len(matching_chars)) * 100
        print(f"  {skill}: {count} ({percentage:.0f}% of builds)")


if __name__ == "__main__":
    # Analyze overall meta
    analyze_meta_builds("Standard")
    
    # Analyze specific build archetype
    analyze_specific_build("Standard", "Necromancer", "Raise Spectre")