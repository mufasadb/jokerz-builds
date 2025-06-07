#!/usr/bin/env python3
"""
Comprehensive tests for the health calculator system.

These tests verify that our life and ES calculations match PoE mechanics and can be
compared against PoE Ninja build data for validation.
"""

import pytest
from src.analysis.health_calculator import health_calculator, HealthCalculationResult


class TestHealthCalculatorBasics:
    """Test basic health calculation mechanics"""
    
    def test_base_life_calculation(self):
        """Test base life calculation from level and class"""
        # Level 1 character should have base life
        result = health_calculator.calculate_health({
            'level': 1,
            'class': 'Marauder',
            'attributes': {'strength': 0, 'intelligence': 0},
            'passive_tree': [],
            'equipment': []
        })
        
        assert result.base_life == 32  # Base life for Marauder at level 1
        assert result.final_life == 32  # No other modifiers
        
    def test_life_per_level(self):
        """Test life gained per level"""
        result = health_calculator.calculate_health({
            'level': 100,
            'class': 'Witch',
            'attributes': {'strength': 0, 'intelligence': 0},
            'passive_tree': [],
            'equipment': []
        })
        
        expected_base = 32 + (100 - 1) * 12  # 32 + 99*12 = 1220
        assert result.base_life == expected_base
        assert result.final_life == expected_base
    
    def test_strength_life_bonus(self):
        """Test life bonus from strength (0.5 life per strength)"""
        result = health_calculator.calculate_health({
            'level': 80,
            'class': 'Marauder', 
            'attributes': {'strength': 400, 'intelligence': 100},
            'passive_tree': [],
            'equipment': []
        })
        
        expected_strength_life = int(400 * 0.5)  # 200 life from strength
        assert result.flat_life_from_strength == expected_strength_life
        
        # Total should be base + strength bonus
        expected_base = 32 + (80 - 1) * 12  # 980
        expected_total = expected_base + expected_strength_life  # 1180
        assert result.final_life == expected_total
    
    def test_intelligence_es_bonus(self):
        """Test ES bonus from intelligence (0.5 ES per intelligence)"""
        result = health_calculator.calculate_health({
            'level': 85,
            'class': 'Witch',
            'attributes': {'strength': 100, 'intelligence': 500},
            'passive_tree': [],
            'equipment': []
        })
        
        expected_int_es = int(500 * 0.5)  # 250 ES from intelligence
        assert result.flat_es_from_intelligence == expected_int_es


class TestPassiveTreeParsing:
    """Test parsing passive tree nodes for life/ES modifiers"""
    
    def test_flat_life_from_tree(self):
        """Test parsing flat life increases from passive tree"""
        passive_tree = [
            {
                'id': 12345,
                'name': 'Life Node',
                'stats': ['+10 to maximum Life', 'some other stat']
            },
            {
                'id': 23456,
                'name': 'Another Life Node',
                'stats': ['+15 to maximum Life']
            }
        ]
        
        result = health_calculator.calculate_health({
            'level': 70,
            'class': 'Duelist',
            'attributes': {'strength': 200, 'intelligence': 50},
            'passive_tree': passive_tree,
            'equipment': []
        })
        
        assert result.flat_life_from_tree == 25  # 10 + 15
    
    def test_increased_life_from_tree(self):
        """Test parsing percentage life increases from passive tree"""
        passive_tree = [
            {
                'id': 12345,
                'name': 'Life Percentage Node',
                'stats': ['8% increased maximum Life']
            },
            {
                'id': 23456,
                'name': 'Another Percentage Node', 
                'stats': ['12% increased maximum Life', 'Some other effect']
            }
        ]
        
        result = health_calculator.calculate_health({
            'level': 75,
            'class': 'Templar',
            'attributes': {'strength': 150, 'intelligence': 200},
            'passive_tree': passive_tree,
            'equipment': []
        })
        
        assert result.increased_life_from_tree == 20.0  # 8% + 12%
    
    def test_mixed_life_tree_modifiers(self):
        """Test parsing both flat and percentage life from tree"""
        passive_tree = [
            {
                'id': 1,
                'stats': ['+20 to maximum Life']
            },
            {
                'id': 2,
                'stats': ['15% increased maximum Life']
            },
            {
                'id': 3,
                'stats': ['+8 to maximum Life', '6% increased maximum Life']
            }
        ]
        
        result = health_calculator.calculate_health({
            'level': 60,
            'class': 'Shadow',
            'attributes': {'strength': 120, 'intelligence': 180},
            'passive_tree': passive_tree,
            'equipment': []
        })
        
        assert result.flat_life_from_tree == 28  # 20 + 8
        assert result.increased_life_from_tree == 21.0  # 15 + 6


class TestEquipmentParsing:
    """Test parsing equipment for life/ES modifiers"""
    
    def test_explicit_life_mods(self):
        """Test parsing explicit life modifiers from equipment"""
        equipment = [
            {
                'inventoryId': 'BodyArmour',
                'explicitMods': [
                    '+75 to maximum Life',
                    '12% increased maximum Life',
                    'Some other modifier'
                ]
            },
            {
                'inventoryId': 'Ring',
                'explicitMods': [
                    '+45 to maximum Life'
                ]
            }
        ]
        
        result = health_calculator.calculate_health({
            'level': 85,
            'class': 'Ranger',
            'attributes': {'strength': 180, 'intelligence': 120},
            'passive_tree': [],
            'equipment': equipment
        })
        
        assert result.flat_life_from_gear == 120  # 75 + 45
        assert result.increased_life_from_gear == 12.0
    
    def test_implicit_and_crafted_mods(self):
        """Test parsing implicit and crafted modifiers"""
        equipment = [
            {
                'inventoryId': 'Belt',
                'implicitMods': ['+25 to maximum Life'],
                'explicitMods': ['+60 to maximum Life'],
                'craftedMods': ['8% increased maximum Life']
            }
        ]
        
        result = health_calculator.calculate_health({
            'level': 90,
            'class': 'Scion',
            'attributes': {'strength': 250, 'intelligence': 150},
            'passive_tree': [],
            'equipment': equipment
        })
        
        assert result.flat_life_from_gear == 85  # 25 + 60
        assert result.increased_life_from_gear == 8.0


class TestComplexCalculations:
    """Test complex scenarios with multiple modifier sources"""
    
    def test_comprehensive_life_calculation(self):
        """Test a realistic character with all modifier sources"""
        passive_tree = [
            {'id': 1, 'stats': ['+30 to maximum Life']},
            {'id': 2, 'stats': ['25% increased maximum Life']},
            {'id': 3, 'stats': ['+15 to maximum Life', '8% increased maximum Life']}
        ]
        
        equipment = [
            {
                'inventoryId': 'BodyArmour',
                'explicitMods': ['+85 to maximum Life', '10% increased maximum Life']
            },
            {
                'inventoryId': 'Helmet',
                'explicitMods': ['+70 to maximum Life']
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
        
        result = health_calculator.calculate_health({
            'level': 95,
            'class': 'Marauder',
            'attributes': {'strength': 400, 'intelligence': 100},
            'passive_tree': passive_tree,
            'equipment': equipment
        })
        
        # Calculate expected values
        expected_base = 32 + (95 - 1) * 12  # 1160
        expected_strength = int(400 * 0.5)  # 200
        expected_tree_flat = 30 + 15  # 45
        expected_gear_flat = 85 + 70 + 65 + 55  # 275
        expected_total_flat = expected_base + expected_strength + expected_tree_flat + expected_gear_flat  # 1680
        
        expected_tree_inc = 25 + 8  # 33%
        expected_gear_inc = 10  # 10%
        expected_total_inc = expected_tree_inc + expected_gear_inc  # 43%
        
        expected_final = int(expected_total_flat * (1 + expected_total_inc / 100))  # 1680 * 1.43 = 2402
        
        assert result.base_life == expected_base
        assert result.flat_life_from_strength == expected_strength
        assert result.flat_life_from_tree == expected_tree_flat
        assert result.flat_life_from_gear == expected_gear_flat
        assert result.total_flat_life == expected_total_flat
        assert result.increased_life_from_tree == expected_tree_inc
        assert result.increased_life_from_gear == expected_gear_inc
        assert result.total_increased_life == expected_total_inc
        assert result.final_life == expected_final
    
    def test_energy_shield_calculation(self):
        """Test ES calculation with multiple sources"""
        # Equipment with base ES
        equipment = [
            {
                'inventoryId': 'BodyArmour',
                'properties': [
                    {'name': 'Energy Shield', 'values': [['450', 0]]}
                ],
                'explicitMods': ['+25 to maximum Energy Shield', '18% increased maximum Energy Shield']
            },
            {
                'inventoryId': 'Helmet',
                'properties': [
                    {'name': 'Energy Shield', 'values': [['150', 0]]}
                ],
                'explicitMods': ['+15 to maximum Energy Shield']
            }
        ]
        
        passive_tree = [
            {'id': 1, 'stats': ['+20 to maximum Energy Shield']},
            {'id': 2, 'stats': ['25% increased maximum Energy Shield']}
        ]
        
        result = health_calculator.calculate_health({
            'level': 88,
            'class': 'Witch',
            'attributes': {'strength': 100, 'intelligence': 350},
            'passive_tree': passive_tree,
            'equipment': equipment
        })
        
        # Expected calculations
        expected_base_es = 450 + 150  # 600 from equipment base
        expected_int_es = int(350 * 0.5)  # 175 from intelligence
        expected_tree_flat = 20
        expected_gear_flat = 25 + 15  # 40
        expected_total_flat = expected_base_es + expected_int_es + expected_tree_flat + expected_gear_flat  # 835
        
        expected_tree_inc = 25
        expected_gear_inc = 18
        expected_total_inc = expected_tree_inc + expected_gear_inc  # 43%
        
        expected_final_es = int(expected_total_flat * (1 + expected_total_inc / 100))  # 835 * 1.43 = 1194
        
        assert result.base_es == expected_base_es
        assert result.flat_es_from_intelligence == expected_int_es
        assert result.flat_es_from_tree == expected_tree_flat
        assert result.flat_es_from_gear == expected_gear_flat
        assert result.total_flat_es == expected_total_flat
        assert result.increased_es_from_tree == expected_tree_inc
        assert result.increased_es_from_gear == expected_gear_inc
        assert result.total_increased_es == expected_total_inc
        assert result.final_es == expected_final_es


class TestPoeNinjaComparison:
    """Tests designed to validate against PoE Ninja build data"""
    
    @pytest.mark.skip(reason="Requires manual PoE Ninja data - implement after basic validation")
    def test_compare_with_poe_ninja_build_1(self):
        """Compare calculation with known PoE Ninja build #1"""
        # This will be filled in with actual build data from PoE Ninja
        # Format: Take a build from PoE Ninja, extract the character data,
        # run our calculation, and compare results
        pass
    
    @pytest.mark.skip(reason="Requires manual PoE Ninja data - implement after basic validation")
    def test_compare_with_poe_ninja_build_2(self):
        """Compare calculation with known PoE Ninja build #2"""
        pass
    
    def test_calculation_result_structure(self):
        """Test that calculation results have all expected fields"""
        result = health_calculator.calculate_health({
            'level': 80,
            'class': 'Necromancer',
            'attributes': {'strength': 200, 'intelligence': 300},
            'passive_tree': [],
            'equipment': []
        })
        
        # Check all fields are present
        assert hasattr(result, 'base_life')
        assert hasattr(result, 'base_es')
        assert hasattr(result, 'final_life')
        assert hasattr(result, 'final_es')
        assert hasattr(result, 'total_ehp')
        assert hasattr(result, 'calculation_steps')
        assert hasattr(result, 'warnings')
        
        # Check calculation steps are populated
        assert len(result.calculation_steps) > 0
        
        # Check total EHP is sum of life and ES
        assert result.total_ehp == result.final_life + result.final_es


def run_health_calculator_tests():
    """Run all health calculator tests and provide summary"""
    print("="*80)
    print("HEALTH CALCULATOR TEST SUITE")
    print("="*80)
    
    # Create test instances
    basic_tests = TestHealthCalculatorBasics()
    tree_tests = TestPassiveTreeParsing()
    equipment_tests = TestEquipmentParsing()
    complex_tests = TestComplexCalculations()
    ninja_tests = TestPoeNinjaComparison()
    
    tests = [
        ("Base Life Calculation", basic_tests.test_base_life_calculation),
        ("Life Per Level", basic_tests.test_life_per_level),
        ("Strength Life Bonus", basic_tests.test_strength_life_bonus),
        ("Intelligence ES Bonus", basic_tests.test_intelligence_es_bonus),
        ("Flat Life from Tree", tree_tests.test_flat_life_from_tree),
        ("Increased Life from Tree", tree_tests.test_increased_life_from_tree),
        ("Mixed Tree Modifiers", tree_tests.test_mixed_life_tree_modifiers),
        ("Explicit Life Mods", equipment_tests.test_explicit_life_mods),
        ("Implicit/Crafted Mods", equipment_tests.test_implicit_and_crafted_mods),
        ("Comprehensive Life Calc", complex_tests.test_comprehensive_life_calculation),
        ("Energy Shield Calculation", complex_tests.test_energy_shield_calculation),
        ("Result Structure", ninja_tests.test_calculation_result_structure),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n--- Testing: {test_name} ---")
            test_func()
            print(f"✅ PASSED: {test_name}")
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {test_name} - {e}")
            failed += 1
    
    print(f"\n{'='*80}")
    print(f"RESULTS: {passed} passed, {failed} failed")
    print(f"{'='*80}")
    
    if failed == 0:
        print("🎉 ALL HEALTH CALCULATION TESTS PASSED!")
        print("\nThe health calculator successfully handles:")
        print("✅ Base life calculation from level and class")
        print("✅ Attribute bonuses (Strength → Life, Intelligence → ES)")
        print("✅ Passive tree parsing (flat and percentage modifiers)")
        print("✅ Equipment modifier parsing (explicit, implicit, crafted)")
        print("✅ Complex multi-source calculations with proper math")
        print("✅ Energy Shield calculation with base values")
        return True
    else:
        print(f"⚠️  {failed} tests failed - see details above")
        return False


if __name__ == "__main__":
    run_health_calculator_tests()