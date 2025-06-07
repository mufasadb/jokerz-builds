#!/usr/bin/env python3
"""
Tests for the EHP (Effective Health Pool) calculator system.

These tests verify that our EHP calculations follow PoE mechanics and produce
reasonable results for different defensive scenarios.
"""

import sys
sys.path.append('.')

from src.analysis.ehp_calculator import ehp_calculator, DefensiveStats, EHPResult


class TestEHPCalculatorBasics:
    """Test basic EHP calculation mechanics"""
    
    def test_no_mitigation_ehp(self):
        """Test EHP with no damage mitigation (should equal raw HP)"""
        stats = DefensiveStats(
            life=5000,
            energy_shield=2000,
            # All other values default to 0
        )
        
        result = ehp_calculator.calculate_ehp(stats)
        
        assert result.total_hp == 7000
        # With no mitigation, EHP should equal raw HP
        assert abs(result.physical_ehp - 7000) < 1
        assert abs(result.fire_ehp - 7000) < 1
        assert abs(result.chaos_ehp - 7000) < 1
    
    def test_armour_physical_reduction(self):
        """Test physical damage reduction from armour"""
        stats = DefensiveStats(
            life=6000,
            energy_shield=0,
            armour=10000,  # Should give 50% reduction vs 1000 damage
        )
        
        result = ehp_calculator.calculate_ehp(stats)
        
        # Armour formula: 10000 / (10000 + 10*1000) = 10000/20000 = 50%
        expected_reduction = 0.5
        expected_physical_ehp = 6000 / (1 - expected_reduction)  # 12000
        
        assert abs(result.physical_reduction - expected_reduction) < 0.01
        assert abs(result.physical_ehp - expected_physical_ehp) < 10
        
        # Elemental EHP should be unchanged (no elemental mitigation)
        assert abs(result.fire_ehp - 6000) < 1
    
    def test_resistance_elemental_reduction(self):
        """Test elemental damage reduction from resistances"""
        stats = DefensiveStats(
            life=5000,
            energy_shield=1000,
            fire_resistance=75.0,
            cold_resistance=80.0,  # Overcapped
            lightning_resistance=60.0,
            chaos_resistance=-20.0,  # Negative resistance
            max_fire_resistance=75.0,
            max_cold_resistance=75.0,  # Caps overcapped resistance
            max_lightning_resistance=75.0,
            max_chaos_resistance=75.0
        )
        
        result = ehp_calculator.calculate_ehp(stats)
        
        base_hp = 6000
        
        # Fire: 75% resistance = 75% reduction
        expected_fire_ehp = base_hp / (1 - 0.75)  # 24000
        assert abs(result.fire_ehp - expected_fire_ehp) < 10
        
        # Cold: 80% resistance but capped at 75%
        expected_cold_ehp = base_hp / (1 - 0.75)  # 24000
        assert abs(result.cold_ehp - expected_cold_ehp) < 10
        
        # Lightning: 60% resistance
        expected_lightning_ehp = base_hp / (1 - 0.60)  # 15000
        assert abs(result.lightning_ehp - expected_lightning_ehp) < 10
        
        # Chaos: -20% resistance (takes more damage)
        expected_chaos_ehp = base_hp / (1 - (-0.20))  # 5000
        assert abs(result.chaos_ehp - expected_chaos_ehp) < 10
    
    def test_block_chance_mitigation(self):
        """Test average damage reduction from block chance"""
        stats = DefensiveStats(
            life=8000,
            energy_shield=0,
            block_chance=40.0,  # 40% block chance
            spell_block_chance=30.0  # 30% spell block
        )
        
        result = ehp_calculator.calculate_ehp(stats)
        
        # Physical attacks: 40% block = 40% average reduction
        expected_phys_ehp = 8000 / (1 - 0.40)  # 13333
        assert abs(result.physical_ehp - expected_phys_ehp) < 50
        
        # Elemental spells: 30% spell block = 30% average reduction
        expected_ele_ehp = 8000 / (1 - 0.30)  # 11428
        assert abs(result.fire_ehp - expected_ele_ehp) < 50
    
    def test_fortify_mitigation(self):
        """Test damage reduction from fortify"""
        stats = DefensiveStats(
            life=7000,
            energy_shield=0,
            fortify=True,
            fire_resistance=75.0,
            max_fire_resistance=75.0
        )
        
        result = ehp_calculator.calculate_ehp(stats)
        
        # Fortify provides 20% less damage taken (multiplicative)
        # Physical: 20% less damage
        expected_phys_ehp = 7000 / (1 - 0.20)  # 8750
        assert abs(result.physical_ehp - expected_phys_ehp) < 10
        
        # Fire: 75% resistance + 20% fortify = 95% total reduction
        # (1 - 0.75) * (1 - 0.20) = 0.25 * 0.80 = 0.20 damage taken
        expected_fire_ehp = 7000 / 0.20  # 35000
        assert abs(result.fire_ehp - expected_fire_ehp) < 50


class TestComplexEHPScenarios:
    """Test complex scenarios with multiple mitigation sources"""
    
    def test_physical_tank_build(self):
        """Test a physical damage focused tank build"""
        stats = DefensiveStats(
            life=8000,
            energy_shield=1000,
            armour=25000,  # High armour
            physical_damage_reduction=10.0,  # Additional sources
            endurance_charges=3,  # 3 * 4% = 12% more reduction
            fortify=True,
            block_chance=35.0,
            # Low elemental resistances
            fire_resistance=30.0,
            cold_resistance=45.0,
            lightning_resistance=50.0,
            chaos_resistance=-60.0
        )
        
        result = ehp_calculator.calculate_ehp(stats)
        
        # Should have very high physical EHP but low elemental EHP
        assert result.physical_ehp > 100000  # Very tanky vs physical (high armour + endurance + fortify + block)
        assert result.fire_ehp < 20000  # Vulnerable to elemental
        assert result.chaos_ehp < 8000  # Very vulnerable to chaos
        
        # Rating should reflect this is a specialized tank
        rating = ehp_calculator.get_ehp_rating(result, 95)
        assert rating in ["Very Tanky", "Extremely Tanky"]
    
    def test_balanced_hybrid_build(self):
        """Test a balanced life/ES hybrid with good all-around defenses"""
        stats = DefensiveStats(
            life=5500,
            energy_shield=3500,  # 9000 total HP
            armour=8000,  # Moderate armour
            fire_resistance=75.0,
            cold_resistance=75.0,
            lightning_resistance=75.0,
            chaos_resistance=0.0,  # Neutral chaos res
            max_fire_resistance=75.0,
            max_cold_resistance=75.0,
            max_lightning_resistance=75.0,
            block_chance=25.0,
            spell_block_chance=25.0,
            fortify=True
        )
        
        result = ehp_calculator.calculate_ehp(stats)
        
        # Should have good all-around EHP
        assert 25000 < result.physical_ehp < 35000  # Good physical mitigation 
        assert 55000 < result.fire_ehp < 70000      # High due to resistance + fortify + block
        assert 55000 < result.cold_ehp < 70000     
        assert 55000 < result.lightning_ehp < 70000
        assert 14000 < result.chaos_ehp < 18000     # Lower but reasonable
        
        # Average should be quite high
        assert result.average_ehp > 40000
        
        rating = ehp_calculator.get_ehp_rating(result, 90)
        assert rating in ["Very Tanky", "Extremely Tanky"]
    
    def test_glass_cannon_build(self):
        """Test a low defense, high damage build"""
        stats = DefensiveStats(
            life=3500,
            energy_shield=1500,  # 5000 total HP
            armour=2000,  # Low armour
            fire_resistance=75.0,  # Capped resistances but no other defenses
            cold_resistance=75.0,
            lightning_resistance=75.0,
            chaos_resistance=-40.0,  # Negative chaos res
            max_fire_resistance=75.0,
            max_cold_resistance=75.0,
            max_lightning_resistance=75.0,
            # No block, fortify, or other defenses
        )
        
        result = ehp_calculator.calculate_ehp(stats)
        
        # Should have low EHP across the board
        assert result.physical_ehp < 7000    # Low armour, no other mitigation
        assert result.fire_ehp < 25000       # Resistance helps but low base HP
        assert result.chaos_ehp < 4000       # Very vulnerable to chaos
        
        rating = ehp_calculator.get_ehp_rating(result, 90)
        assert rating in ["Very Tanky", "Tanky"]  # Even glass cannon has decent EHP due to resistances
    
    def test_ci_energy_shield_build(self):
        """Test a Chaos Inoculation (CI) pure ES build"""
        stats = DefensiveStats(
            life=1,  # CI sets life to 1
            energy_shield=12000,  # High ES
            armour=0,  # No armour (pure ES)
            fire_resistance=75.0,
            cold_resistance=75.0,
            lightning_resistance=75.0,
            chaos_resistance=100.0,  # CI provides chaos immunity
            max_fire_resistance=75.0,
            max_cold_resistance=75.0,
            max_lightning_resistance=75.0,
            max_chaos_resistance=100.0,
            spell_block_chance=40.0,  # High spell block
        )
        
        result = ehp_calculator.calculate_ehp(stats)
        
        # Should be vulnerable to physical but strong vs everything else
        assert result.physical_ehp < 15000   # No physical mitigation, just spell block
        assert result.fire_ehp > 70000       # Good elemental defenses + spell block
        assert result.chaos_ehp > 100000     # Chaos immune (100% resistance)
        
        rating = ehp_calculator.get_ehp_rating(result, 90)
        assert rating in ["Very Tanky", "Extremely Tanky"]  # CI has very high weighted EHP


def test_ehp_rating_system():
    """Test the EHP rating system"""
    # Very tanky build
    high_stats = DefensiveStats(life=8000, energy_shield=4000, armour=20000, 
                               fire_resistance=75, cold_resistance=75, 
                               lightning_resistance=75, fortify=True)
    high_result = ehp_calculator.calculate_ehp(high_stats)
    high_rating = ehp_calculator.get_ehp_rating(high_result, 95)
    assert high_rating in ["Very Tanky", "Extremely Tanky"]
    
    # Squishy build
    low_stats = DefensiveStats(life=3000, energy_shield=0, armour=1000)
    low_result = ehp_calculator.calculate_ehp(low_stats)
    low_rating = ehp_calculator.get_ehp_rating(low_result, 90)
    assert low_rating in ["Squishy", "Very Squishy"]


def run_ehp_calculator_tests():
    """Run all EHP calculator tests and provide summary"""
    print("="*80)
    print("EHP CALCULATOR TEST SUITE")
    print("="*80)
    
    # Create test instances
    basic_tests = TestEHPCalculatorBasics()
    complex_tests = TestComplexEHPScenarios()
    
    tests = [
        ("No Mitigation EHP", basic_tests.test_no_mitigation_ehp),
        ("Armour Physical Reduction", basic_tests.test_armour_physical_reduction),
        ("Resistance Elemental Reduction", basic_tests.test_resistance_elemental_reduction),
        ("Block Chance Mitigation", basic_tests.test_block_chance_mitigation),
        ("Fortify Mitigation", basic_tests.test_fortify_mitigation),
        ("Physical Tank Build", complex_tests.test_physical_tank_build),
        ("Balanced Hybrid Build", complex_tests.test_balanced_hybrid_build),
        ("Glass Cannon Build", complex_tests.test_glass_cannon_build),
        ("CI Energy Shield Build", complex_tests.test_ci_energy_shield_build),
        ("EHP Rating System", test_ehp_rating_system),
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
        print("🎉 ALL EHP CALCULATION TESTS PASSED!")
        print("\nThe EHP calculator successfully handles:")
        print("✅ Armour-based physical damage reduction")
        print("✅ Elemental resistance damage reduction")
        print("✅ Block chance average damage reduction")
        print("✅ Fortify multiplicative damage reduction")
        print("✅ Complex multi-source mitigation")
        print("✅ Different build archetypes (tank, glass cannon, CI)")
        print("✅ EHP rating system for build categorization")
        return True
    else:
        print(f"⚠️  {failed} tests failed - see details above")
        return False


if __name__ == "__main__":
    run_ehp_calculator_tests()