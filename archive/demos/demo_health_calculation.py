#!/usr/bin/env python3
"""
Demonstration of the health calculator system with realistic examples.

This script shows how to use the health calculator and demonstrates its capabilities
with examples that could be compared against PoE Ninja builds.
"""

import sys
sys.path.append('.')

from src.analysis.health_calculator import health_calculator, HealthCalculationResult


def demo_basic_calculation():
    """Demo basic life calculation for a simple character"""
    print("="*60)
    print("DEMO 1: Basic Life Calculation")
    print("="*60)
    
    character_data = {
        'level': 85,
        'class': 'Marauder',
        'attributes': {'strength': 300, 'intelligence': 80},
        'passive_tree': [],
        'equipment': []
    }
    
    result = health_calculator.calculate_health(character_data)
    
    print(f"Character: Level {character_data['level']} {character_data['class']}")
    print(f"Attributes: {character_data['attributes']['strength']} STR, {character_data['attributes']['intelligence']} INT")
    print(f"\nCalculation Results:")
    print(f"  Base Life: {result.base_life}")
    print(f"  Life from Strength: +{result.flat_life_from_strength}")
    print(f"  Final Life: {result.final_life}")
    print(f"  ES from Intelligence: +{result.flat_es_from_intelligence}")
    print(f"  Final ES: {result.final_es}")
    print(f"  Total EHP: {result.total_ehp}")


def demo_passive_tree_life():
    """Demo life calculation with passive tree investments"""
    print("\n" + "="*60)
    print("DEMO 2: Life Build with Passive Tree")
    print("="*60)
    
    # Simulate a life-focused passive tree
    passive_tree = [
        {'id': 1, 'stats': ['+20 to maximum Life']},  # Life wheel start
        {'id': 2, 'stats': ['8% increased maximum Life']},
        {'id': 3, 'stats': ['+25 to maximum Life']},  # Major life node
        {'id': 4, 'stats': ['12% increased maximum Life']},
        {'id': 5, 'stats': ['+15 to maximum Life', '6% increased maximum Life']},  # Notable
        {'id': 6, 'stats': ['10% increased maximum Life']},
        {'id': 7, 'stats': ['+18 to maximum Life']},
    ]
    
    character_data = {
        'level': 90,
        'class': 'Juggernaut', 
        'attributes': {'strength': 450, 'intelligence': 100},
        'passive_tree': passive_tree,
        'equipment': []
    }
    
    result = health_calculator.calculate_health(character_data)
    
    print(f"Character: Level {character_data['level']} {character_data['class']}")
    print(f"Passive Tree Investment: Heavy life focus")
    print(f"\nBreakdown:")
    print(f"  Base Life (level {character_data['level']}): {result.base_life}")
    print(f"  Life from {character_data['attributes']['strength']} Strength: +{result.flat_life_from_strength}")
    print(f"  Flat Life from Tree: +{result.flat_life_from_tree}")
    print(f"  Increased Life from Tree: {result.increased_life_from_tree}%")
    print(f"  Total Flat Life: {result.total_flat_life}")
    print(f"  Final Life: {result.final_life}")
    print(f"  Total EHP: {result.total_ehp}")


def demo_es_hybrid_build():
    """Demo ES/Life hybrid build calculation"""
    print("\n" + "="*60)
    print("DEMO 3: Life/ES Hybrid Build")
    print("="*60)
    
    # ES-focused passive tree
    passive_tree = [
        {'id': 1, 'stats': ['+15 to maximum Energy Shield']},
        {'id': 2, 'stats': ['20% increased maximum Energy Shield']},
        {'id': 3, 'stats': ['+25 to maximum Energy Shield']},
        {'id': 4, 'stats': ['15% increased maximum Energy Shield']},
        {'id': 5, 'stats': ['+20 to maximum Life']},  # Some life
        {'id': 6, 'stats': ['8% increased maximum Life']},
    ]
    
    # Equipment with ES
    equipment = [
        {
            'inventoryId': 'BodyArmour',
            'properties': [{'name': 'Energy Shield', 'values': [['520', 0]]}],
            'explicitMods': ['+35 to maximum Energy Shield', '22% increased maximum Energy Shield']
        },
        {
            'inventoryId': 'Helmet',
            'properties': [{'name': 'Energy Shield', 'values': [['180', 0]]}],
            'explicitMods': ['+25 to maximum Energy Shield']
        },
        {
            'inventoryId': 'Gloves',
            'properties': [{'name': 'Energy Shield', 'values': [['120', 0]]}],
            'explicitMods': ['+18 to maximum Energy Shield']
        },
        {
            'inventoryId': 'Ring',
            'explicitMods': ['+65 to maximum Life']
        },
        {
            'inventoryId': 'Ring2',
            'explicitMods': ['+55 to maximum Life']
        }
    ]
    
    character_data = {
        'level': 88,
        'class': 'Occultist',
        'attributes': {'strength': 150, 'intelligence': 420},
        'passive_tree': passive_tree,
        'equipment': equipment
    }
    
    result = health_calculator.calculate_health(character_data)
    
    print(f"Character: Level {character_data['level']} {character_data['class']}")
    print(f"Build Type: Life/ES Hybrid")
    print(f"\nLife Calculation:")
    print(f"  Base + Strength: {result.base_life + result.flat_life_from_strength}")
    print(f"  Flat from Tree: +{result.flat_life_from_tree}")
    print(f"  Flat from Gear: +{result.flat_life_from_gear}")
    print(f"  Increased from Tree: {result.increased_life_from_tree}%")
    print(f"  Final Life: {result.final_life}")
    
    print(f"\nES Calculation:")
    print(f"  Base ES from Gear: {result.base_es}")
    print(f"  ES from {character_data['attributes']['intelligence']} Intelligence: +{result.flat_es_from_intelligence}")
    print(f"  Flat ES from Tree: +{result.flat_es_from_tree}")
    print(f"  Flat ES from Gear: +{result.flat_es_from_gear}")
    print(f"  Increased ES from Tree: {result.increased_es_from_tree}%")
    print(f"  Increased ES from Gear: {result.increased_es_from_gear}%")
    print(f"  Final ES: {result.final_es}")
    
    print(f"\nTotal EHP: {result.total_ehp} ({result.final_life} life + {result.final_es} ES)")


def demo_comprehensive_build():
    """Demo a comprehensive build with all sources of life/ES"""
    print("\n" + "="*60)
    print("DEMO 4: Comprehensive Endgame Build")
    print("="*60)
    
    # Extensive passive tree
    passive_tree = [
        # Life cluster
        {'id': 1, 'stats': ['+25 to maximum Life']},
        {'id': 2, 'stats': ['12% increased maximum Life']},
        {'id': 3, 'stats': ['+30 to maximum Life']},
        {'id': 4, 'stats': ['15% increased maximum Life']},
        {'id': 5, 'stats': ['+20 to maximum Life', '8% increased maximum Life']},
        # ES nodes
        {'id': 6, 'stats': ['+20 to maximum Energy Shield']},
        {'id': 7, 'stats': ['18% increased maximum Energy Shield']},
    ]
    
    # High-end equipment
    equipment = [
        {
            'inventoryId': 'BodyArmour',
            'properties': [{'name': 'Energy Shield', 'values': [['650', 0]]}],
            'explicitMods': [
                '+95 to maximum Life', 
                '+45 to maximum Energy Shield',
                '12% increased maximum Life'
            ]
        },
        {
            'inventoryId': 'Helmet',
            'properties': [{'name': 'Energy Shield', 'values': [['220', 0]]}],
            'explicitMods': ['+75 to maximum Life', '+30 to maximum Energy Shield']
        },
        {
            'inventoryId': 'Gloves',
            'explicitMods': ['+80 to maximum Life']
        },
        {
            'inventoryId': 'Boots',
            'explicitMods': ['+85 to maximum Life']
        },
        {
            'inventoryId': 'Ring',
            'explicitMods': ['+75 to maximum Life']
        },
        {
            'inventoryId': 'Ring2',
            'explicitMods': ['+70 to maximum Life']
        },
        {
            'inventoryId': 'Amulet',
            'explicitMods': ['+90 to maximum Life', '8% increased maximum Life']
        },
        {
            'inventoryId': 'Belt',
            'implicitMods': ['+25 to maximum Life'],
            'explicitMods': ['+85 to maximum Life'],
            'craftedMods': ['10% increased maximum Life']
        }
    ]
    
    character_data = {
        'level': 95,
        'class': 'Guardian',
        'attributes': {'strength': 350, 'intelligence': 380},
        'passive_tree': passive_tree,
        'equipment': equipment
    }
    
    result = health_calculator.calculate_health(character_data)
    
    print(f"Character: Level {character_data['level']} {character_data['class']}")
    print(f"Build Type: Endgame Life/ES Hybrid")
    
    print(f"\nDetailed Breakdown:")
    for step in result.calculation_steps:
        print(f"  {step}")
    
    print(f"\nFinal Results:")
    print(f"  Life: {result.final_life:,}")
    print(f"  Energy Shield: {result.final_es:,}")
    print(f"  Total EHP: {result.total_ehp:,}")
    print(f"  EHP per Level: {result.total_ehp / character_data['level']:.1f}")


def demo_comparison_template():
    """Template for comparing with PoE Ninja builds"""
    print("\n" + "="*60)
    print("POE NINJA COMPARISON TEMPLATE")
    print("="*60)
    
    print("To compare with PoE Ninja builds:")
    print("1. Find a build on poe.ninja/builds")
    print("2. Extract character data (level, class, attributes)")
    print("3. Get passive tree allocation")
    print("4. Get equipment with modifiers")
    print("5. Run through our calculator")
    print("6. Compare results")
    
    print(f"\nExample format for character data:")
    example_data = {
        'level': 92,
        'class': 'Necromancer',
        'attributes': {'strength': 180, 'intelligence': 450},
        'passive_tree': [
            # Extract from PoE Ninja passive tree data
        ],
        'equipment': [
            # Extract from PoE Ninja equipment data
        ]
    }
    
    print("character_data = {")
    for key, value in example_data.items():
        if key in ['passive_tree', 'equipment']:
            print(f"    '{key}': [")
            print(f"        # Extract from PoE Ninja {key} data")
            print(f"    ],")
        else:
            print(f"    '{key}': {value},")
    print("}")
    
    print(f"\nThen run: result = health_calculator.calculate_health(character_data)")
    print(f"Compare result.final_life and result.final_es with PoE Ninja values")


def main():
    """Run all health calculation demos"""
    print("HEALTH CALCULATION SYSTEM DEMONSTRATION")
    print("This shows how our calculator handles different build types")
    
    demo_basic_calculation()
    demo_passive_tree_life()
    demo_es_hybrid_build()
    demo_comprehensive_build()
    demo_comparison_template()
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("✅ Basic life calculation (level + strength)")
    print("✅ Passive tree life modifiers (flat + percentage)")
    print("✅ Equipment life/ES modifiers")
    print("✅ Complex multi-source calculations")
    print("✅ Life/ES hybrid builds")
    print("✅ Ready for PoE Ninja comparison testing")


if __name__ == "__main__":
    main()