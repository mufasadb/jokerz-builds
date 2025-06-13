#!/usr/bin/env python3
"""
Test script for the build query system
"""

import pytest
import sys
import os

# Add src and archive to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'archive', 'examples'))

from query_fire_tanky_builds import BuildQuerySystem
from src.storage.database import DatabaseManager
from src.analysis.build_categorizer import build_categorizer, BuildCategories


def test_build_query_system_initialization():
    """Test that BuildQuerySystem initializes correctly"""
    db_path = "sqlite:///data/ladder_snapshots.db"
    query_system = BuildQuerySystem(db_path)
    
    assert query_system.db_manager is not None
    assert query_system.data_manager is not None
    assert query_system.data_explorer is not None


def test_build_categorization():
    """Test build categorization with sample data"""
    
    # Sample fire tanky budget build
    sample_char = {
        'name': 'TestFireTank',
        'account': 'TestAccount',
        'level': 85,
        'class': 'Marauder',
        'ascendancy': 'Juggernaut',
        'life': 10000,
        'energy_shield': 0,
        'main_skill': 'Molten Strike',
        'skills': ['Molten Strike', 'Fortify', 'Melee Physical Damage'],
        'unique_items': ['Kaom\'s Heart', 'The Baron'],  # Tanky items but not super expensive
    }
    
    categories = build_categorizer.categorize_build(sample_char)
    
    # Should be categorized as fire damage
    assert categories.primary_damage_type == 'fire'
    
    # Should be tanky due to high life and Kaom's Heart
    assert categories.defense_style == 'tanky'
    
    # Should have reasonable confidence scores
    assert categories.confidence_scores.get('damage_type', 0) > 0
    
    print(f"Sample build categorized as: {build_categorizer.get_build_summary(categories)}")


def test_query_system_with_mock_data():
    """Test the query system with available data"""
    db_path = "sqlite:///data/ladder_snapshots.db"
    query_system = BuildQuerySystem(db_path)
    
    # Test finding builds by damage type
    fire_builds = query_system.find_builds_by_damage_type("fire", limit=5)
    print(f"Found {len(fire_builds)} fire builds")
    
    # Test finding tanky builds
    tanky_builds = query_system.find_tanky_builds(limit=5)
    print(f"Found {len(tanky_builds)} tanky builds")
    
    # Test finding budget builds
    budget_builds = query_system.find_budget_builds(limit=5)
    print(f"Found {len(budget_builds)} budget builds")
    
    # Test the specific query we want
    fire_tanky_budget = query_system.find_fire_tanky_budget_builds(limit=3)
    print(f"Found {len(fire_tanky_budget)} fire tanky budget builds")
    
    if fire_tanky_budget:
        print("Example fire tanky budget build:")
        build = fire_tanky_budget[0]
        print(f"  {build['character_name']} ({build['class']})")
        print(f"  Main Skill: {build.get('main_skill', 'Unknown')}")
        print(f"  Build Summary: {build.get('build_summary', 'N/A')}")


def test_popularity_stats():
    """Test build popularity statistics"""
    db_path = "sqlite:///data/ladder_snapshots.db"
    query_system = BuildQuerySystem(db_path)
    
    stats = query_system.get_build_popularity_stats()
    
    assert 'damage_types' in stats
    assert 'defense_styles' in stats
    assert 'cost_tiers' in stats
    assert 'total_analyzed' in stats
    
    print(f"Analyzed {stats['total_analyzed']} builds")
    print(f"Damage types found: {list(stats['damage_types'].keys())}")
    print(f"Defense styles found: {list(stats['defense_styles'].keys())}")
    print(f"Cost tiers found: {list(stats['cost_tiers'].keys())}")


if __name__ == "__main__":
    print("Testing Build Query System...")
    print("=" * 50)
    
    try:
        test_build_query_system_initialization()
        print("✓ Initialization test passed")
        
        test_build_categorization()
        print("✓ Build categorization test passed")
        
        test_query_system_with_mock_data()
        print("✓ Query system test completed")
        
        test_popularity_stats()
        print("✓ Popularity stats test passed")
        
        print("\nAll tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()