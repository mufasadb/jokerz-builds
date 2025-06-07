"""
Test the end-to-end integration of tankiness/EHP system with build categorization
"""

import logging
from src.storage.database import DatabaseManager, Character
from src.analysis.build_categorizer import build_categorizer
from src.analysis.ehp_calculator import ehp_calculator, DefensiveStats

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_ehp_categorization():
    """Test that EHP calculation is properly integrated into categorization"""
    
    # Test character data with defensive stats
    test_character = {
        'name': 'TestTank',
        'account': 'TestAccount',
        'level': 90,
        'life': 5500,
        'energy_shield': 1000,
        'main_skill': 'Earthquake',
        'enhanced_skills': ['Earthquake', 'Molten Shell', 'Ancestral Warchief'],
        'enhanced_uniques': ['Brass Dome', 'Kaom\'s Heart'],
        'main_skill_setup': {
            'links': 6,
            'gems': [
                {'name': 'Earthquake', 'support': False},
                {'name': 'Melee Physical Damage Support', 'support': True}
            ]
        },
        # Defensive stats
        'armour': 25000,
        'evasion': 500,
        'fire_resistance': 76,
        'cold_resistance': 75,
        'lightning_resistance': 75,
        'chaos_resistance': 30,
        'block_chance': 25,
        'spell_block_chance': 10,
        'physical_damage_reduction': 0,
        'fortify': True,
        'endurance_charges': 3
    }
    
    print("\n=== Testing EHP Categorization ===")
    print(f"Character: {test_character['name']} (Level {test_character['level']})")
    print(f"Life: {test_character['life']}, ES: {test_character['energy_shield']}")
    print(f"Armour: {test_character['armour']}")
    
    # Categorize the build
    categories = build_categorizer.categorize_build(test_character)
    
    # Check categorization results
    print("\n=== Categorization Results ===")
    print(f"Primary Damage: {categories.primary_damage_type}")
    print(f"Skill Delivery: {categories.skill_delivery}")
    print(f"Defense Style: {categories.defense_style}")
    print(f"Defense Layers: {categories.defense_layers}")
    print(f"Tankiness Rating: {categories.tankiness_rating}")
    
    # Check EHP results
    if categories.ehp_result:
        print("\n=== EHP Results ===")
        print(f"Total HP: {categories.ehp_result.total_hp}")
        print(f"Physical EHP: {categories.ehp_result.physical_ehp:.0f}")
        print(f"Fire EHP: {categories.ehp_result.fire_ehp:.0f}")
        print(f"Cold EHP: {categories.ehp_result.cold_ehp:.0f}")
        print(f"Lightning EHP: {categories.ehp_result.lightning_ehp:.0f}")
        print(f"Chaos EHP: {categories.ehp_result.chaos_ehp:.0f}")
        print(f"Weighted EHP: {categories.ehp_result.weighted_ehp:.0f}")
    
    # Get build summary
    summary = build_categorizer.get_build_summary(categories)
    print(f"\n=== Build Summary ===")
    print(summary)
    
    # Test different tankiness levels
    print("\n\n=== Testing Different Tankiness Levels ===")
    
    test_cases = [
        {
            'name': 'Glass Cannon',
            'life': 3000,
            'energy_shield': 0,
            'armour': 1000,
            'resistances': 75
        },
        {
            'name': 'Balanced Build',
            'life': 5000,
            'energy_shield': 500,
            'armour': 10000,
            'resistances': 75
        },
        {
            'name': 'Ultra Tank',
            'life': 7000,
            'energy_shield': 2000,
            'armour': 50000,
            'resistances': 80
        }
    ]
    
    for test_case in test_cases:
        char_data = {
            'name': test_case['name'],
            'level': 90,
            'life': test_case['life'],
            'energy_shield': test_case['energy_shield'],
            'armour': test_case['armour'],
            'fire_resistance': test_case['resistances'],
            'cold_resistance': test_case['resistances'],
            'lightning_resistance': test_case['resistances'],
            'chaos_resistance': 0,
            'main_skill': 'Cyclone',
            'enhanced_skills': ['Cyclone'],
            'enhanced_uniques': []
        }
        
        categories = build_categorizer.categorize_build(char_data)
        print(f"\n{test_case['name']}:")
        print(f"  Tankiness: {categories.tankiness_rating}")
        print(f"  Defense Style: {categories.defense_style}")
        if categories.ehp_result:
            print(f"  Weighted EHP: {categories.ehp_result.weighted_ehp:.0f}")


def test_database_integration():
    """Test database storage of EHP data"""
    print("\n\n=== Testing Database Integration ===")
    
    # Create test database
    db = DatabaseManager("sqlite:///test_tankiness.db")
    
    # Create a test snapshot
    test_snapshot_data = {
        'data': [{
            'account': 'TestAccount',
            'name': 'TestCharacter',
            'level': 90,
            'experience': 1000000000,
            'class': 'Marauder',
            'rank': 1,
            'league': 'TestLeague'
        }],
        'league': 'TestLeague',
        'ladder_type': 'league'
    }
    
    snapshot_id = db.save_ladder_snapshot(
        ladder_data=test_snapshot_data,
        league='TestLeague',
        ladder_type='league'
    )
    
    print(f"Created snapshot {snapshot_id}")
    
    # Update character with defensive stats
    session = db.get_session()
    try:
        char = session.query(Character).filter_by(
            snapshot_id=snapshot_id,
            name='TestCharacter'
        ).first()
        
        if char:
            # Add defensive stats
            char.life = 6000
            char.energy_shield = 1500
            char.armour = 30000
            char.evasion = 1000
            char.fire_resistance = 78
            char.cold_resistance = 76
            char.lightning_resistance = 76
            char.chaos_resistance = 40
            char.block_chance = 30
            char.spell_block_chance = 15
            char.main_skill = 'Lacerate'
            char.enhanced_skills = ['Lacerate', 'Blood Rage', 'Ancestral Protector']
            char.enhanced_uniques = ['Aegis Aurora', 'The Surrender']
            
            session.commit()
            print("Updated character with defensive stats")
            
            # Run categorization
            categorized = db.categorize_snapshot_characters(snapshot_id)
            print(f"Categorized {categorized} characters")
            
            # Check results
            session.refresh(char)
            print(f"\nCharacter after categorization:")
            print(f"  Defense Style: {char.defense_style}")
            print(f"  Tankiness Rating: {char.tankiness_rating}")
            print(f"  Weighted EHP: {char.ehp_weighted}")
            print(f"  Physical EHP: {char.ehp_physical}")
            
    finally:
        session.close()
    
    print("\n=== Database Integration Test Complete ===")


if __name__ == "__main__":
    print("Testing Tankiness/EHP Integration")
    print("=" * 50)
    
    # Run tests
    test_ehp_categorization()
    test_database_integration()
    
    print("\n\nAll tests complete!")