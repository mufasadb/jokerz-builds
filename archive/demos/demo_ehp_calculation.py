#!/usr/bin/env python3
"""
Demonstration of the EHP (Effective Health Pool) calculation system.

This shows how our EHP calculator works compared to simple Life+ES calculations
and demonstrates the impact of various defensive mechanics.
"""

import sys
sys.path.append('.')

from src.analysis.ehp_calculator import ehp_calculator, DefensiveStats


def demo_basic_vs_ehp():
    """Show the difference between basic HP and EHP"""
    print("="*80)
    print("DEMO 1: Basic HP vs EHP Comparison")
    print("="*80)
    
    # Same character with different defensive setups
    base_stats = {
        'life': 6000,
        'energy_shield': 2000,  # 8000 total HP
    }
    
    # No defenses
    no_defense = DefensiveStats(**base_stats)
    result1 = ehp_calculator.calculate_ehp(no_defense)
    
    # With defenses
    with_defense = DefensiveStats(
        **base_stats,
        armour=15000,
        fire_resistance=75.0,
        cold_resistance=75.0,
        lightning_resistance=75.0,
        chaos_resistance=0.0,
        block_chance=30.0,
        fortify=True
    )
    result2 = ehp_calculator.calculate_ehp(with_defense)
    
    print(f"Character Stats: {base_stats['life']:,} Life + {base_stats['energy_shield']:,} ES = {sum(base_stats.values()):,} Total HP")
    print(f"\nNo Defenses:")
    print(f"  Physical EHP: {result1.physical_ehp:,.0f}")
    print(f"  Fire EHP: {result1.fire_ehp:,.0f}")
    print(f"  Weighted EHP: {result1.weighted_ehp:,.0f}")
    
    print(f"\nWith Defenses (15k armor, 75% res, 30% block, fortify):")
    print(f"  Physical EHP: {result2.physical_ehp:,.0f}")
    print(f"  Fire EHP: {result2.fire_ehp:,.0f}")
    print(f"  Weighted EHP: {result2.weighted_ehp:,.0f}")
    
    print(f"\nEHP Multiplier:")
    print(f"  Physical: {result2.physical_ehp / result1.physical_ehp:.1f}x")
    print(f"  Fire: {result2.fire_ehp / result1.fire_ehp:.1f}x")
    print(f"  Weighted: {result2.weighted_ehp / result1.weighted_ehp:.1f}x")


def demo_armor_scaling():
    """Show how armor effectiveness scales with different damage amounts"""
    print("\n" + "="*80)
    print("DEMO 2: Armor Scaling vs Different Hit Sizes")
    print("="*80)
    
    base_stats = DefensiveStats(life=7000, energy_shield=0)
    
    armor_values = [5000, 10000, 15000, 20000, 30000]
    hit_sizes = [500, 1000, 2000, 5000]  # Different standard hits
    
    print(f"{'Armor':<8} | {'vs 500':<8} | {'vs 1k':<8} | {'vs 2k':<8} | {'vs 5k':<8}")
    print("-" * 50)
    
    for armor in armor_values:
        reductions = []
        for hit_size in hit_sizes:
            # Calculate armor reduction for this hit size
            reduction = armor / (armor + 10 * hit_size)
            reductions.append(f"{reduction:.1%}")
        
        print(f"{armor:<8} | {reductions[0]:<8} | {reductions[1]:<8} | {reductions[2]:<8} | {reductions[3]:<8}")
    
    print(f"\nNote: Higher damage hits are less affected by armor")
    print(f"This is why PoB/PoE Ninja use standard 1000 damage hits for comparison")


def demo_resistance_caps():
    """Show the impact of resistance caps and overcapping"""
    print("\n" + "="*80)
    print("DEMO 3: Resistance Caps and Overcapping")
    print("="*80)
    
    base_stats = {'life': 6000, 'energy_shield': 1000}
    
    scenarios = [
        ("Uncapped", {'fire_resistance': 50.0}),
        ("Capped", {'fire_resistance': 75.0}),
        ("Overcapped", {'fire_resistance': 85.0, 'max_fire_resistance': 75.0}),
        ("Raised Max", {'fire_resistance': 85.0, 'max_fire_resistance': 85.0}),
        ("Negative", {'fire_resistance': -20.0}),
    ]
    
    print(f"{'Scenario':<12} | {'Effective Res':<12} | {'Fire EHP':<10} | {'Rating'}")
    print("-" * 50)
    
    for name, res_data in scenarios:
        stats = DefensiveStats(**base_stats, **res_data)
        result = ehp_calculator.calculate_ehp(stats)
        effective_res = min(res_data.get('fire_resistance', 0), 
                           res_data.get('max_fire_resistance', 75))
        
        print(f"{name:<12} | {effective_res:>6.0f}%      | {result.fire_ehp:>8.0f} | {result.fire_reduction:.1%}")


def demo_build_archetypes():
    """Show EHP for different common build archetypes"""
    print("\n" + "="*80)
    print("DEMO 4: Common Build Archetypes")
    print("="*80)
    
    archetypes = {
        "Pure Life Tank": DefensiveStats(
            life=8500, energy_shield=0, armour=25000,
            fire_resistance=75, cold_resistance=75, lightning_resistance=75,
            chaos_resistance=20, fortify=True, block_chance=40,
            endurance_charges=3
        ),
        
        "Life/ES Hybrid": DefensiveStats(
            life=5500, energy_shield=4000, armour=8000,
            fire_resistance=75, cold_resistance=75, lightning_resistance=75,
            chaos_resistance=0, fortify=True, block_chance=25,
            spell_block_chance=25
        ),
        
        "CI Pure ES": DefensiveStats(
            life=1, energy_shield=12000, armour=0,
            fire_resistance=75, cold_resistance=75, lightning_resistance=75,
            chaos_resistance=100, max_chaos_resistance=100,
            spell_block_chance=35
        ),
        
        "Evasion Hybrid": DefensiveStats(
            life=5000, energy_shield=2500, armour=2000, evasion=15000,
            fire_resistance=75, cold_resistance=75, lightning_resistance=75,
            chaos_resistance=-30, fortify=False
        ),
        
        "Glass Cannon": DefensiveStats(
            life=4000, energy_shield=1500, armour=1500,
            fire_resistance=75, cold_resistance=75, lightning_resistance=75,
            chaos_resistance=-40
        )
    }
    
    print(f"{'Build Type':<16} | {'Total HP':<8} | {'Phys EHP':<9} | {'Fire EHP':<9} | {'Weighted':<9} | {'Rating'}")
    print("-" * 80)
    
    for name, stats in archetypes.items():
        result = ehp_calculator.calculate_ehp(stats)
        rating = ehp_calculator.get_ehp_rating(result, 90)
        
        print(f"{name:<16} | {result.total_hp:>7,} | {result.physical_ehp:>8.0f} | "
              f"{result.fire_ehp:>8.0f} | {result.weighted_ehp:>8.0f} | {rating}")


def demo_mitigation_breakdown():
    """Show detailed mitigation breakdown for a complex build"""
    print("\n" + "="*80)
    print("DEMO 5: Detailed Mitigation Breakdown")
    print("="*80)
    
    complex_build = DefensiveStats(
        life=7000,
        energy_shield=2500,
        armour=18000,
        physical_damage_reduction=8.0,  # From tree/other sources
        fire_resistance=75.0,
        cold_resistance=80.0,  # Overcapped
        lightning_resistance=75.0,
        chaos_resistance=-10.0,
        max_fire_resistance=75.0,
        max_cold_resistance=75.0,  # Caps the overcapped
        max_lightning_resistance=75.0,
        block_chance=35.0,
        spell_block_chance=25.0,
        fortify=True,
        endurance_charges=2
    )
    
    result = ehp_calculator.calculate_ehp(complex_build)
    
    print(f"Complex Endgame Build Analysis:")
    print(f"Base HP: {result.total_hp:,} ({complex_build.life:,} life + {complex_build.energy_shield:,} ES)")
    print(f"\nDamage Reduction Breakdown:")
    
    # Physical breakdown
    armour_reduction = complex_build.armour / (complex_build.armour + 10 * 1000)
    print(f"  Physical vs 1000 hit:")
    print(f"    Armour: {armour_reduction:.1%}")
    print(f"    Other sources: {complex_build.physical_damage_reduction:.1%}")
    print(f"    Endurance charges: {complex_build.endurance_charges * 4:.1%}")
    print(f"    Fortify: 20.0% (multiplicative)")
    print(f"    Block: {complex_build.block_chance:.1%} (average)")
    print(f"    Total: {result.physical_reduction:.1%}")
    print(f"    EHP: {result.physical_ehp:,.0f}")
    
    print(f"  Fire:")
    print(f"    Resistance: {min(complex_build.fire_resistance, complex_build.max_fire_resistance):.1%}")
    print(f"    Fortify: 20.0% (multiplicative)")
    print(f"    Spell Block: {complex_build.spell_block_chance:.1%} (average)")
    print(f"    Total: {result.fire_reduction:.1%}")
    print(f"    EHP: {result.fire_ehp:,.0f}")
    
    print(f"\nOverall Assessment:")
    print(f"  Average EHP: {result.average_ehp:,.0f}")
    print(f"  Weighted EHP: {result.weighted_ehp:,.0f}")
    print(f"  Build Rating: {ehp_calculator.get_ehp_rating(result, 92)}")


def demo_poe_ninja_comparison():
    """Template for comparing with PoE Ninja builds"""
    print("\n" + "="*80)
    print("DEMO 6: PoE Ninja Comparison Workflow")
    print("="*80)
    
    print("To compare our EHP calculations with PoE Ninja:")
    print("1. Find a build on poe.ninja/builds")
    print("2. Extract defensive stats from the build page")
    print("3. Input into our calculator")
    print("4. Compare results")
    
    print(f"\nExample PoE Ninja build extraction:")
    print(f"# From PoE Ninja build page:")
    print(f"# Life: 6,234")
    print(f"# ES: 1,829") 
    print(f"# Armour: 12,456")
    print(f"# Fire Res: 75%")
    print(f"# etc...")
    
    example_stats = DefensiveStats(
        life=6234,
        energy_shield=1829,
        armour=12456,
        fire_resistance=75.0,
        cold_resistance=75.0,
        lightning_resistance=75.0,
        chaos_resistance=-15.0,
        # Extract other stats from build...
    )
    
    result = ehp_calculator.calculate_ehp(example_stats)
    
    print(f"\nOur calculated EHP:")
    print(f"  Total HP: {result.total_hp:,}")
    print(f"  Physical EHP: {result.physical_ehp:,.0f}")
    print(f"  Average EHP: {result.average_ehp:,.0f}")
    print(f"  Weighted EHP: {result.weighted_ehp:,.0f}")
    print(f"\nCompare these values with what PoE Ninja displays!")


def main():
    """Run all EHP calculation demos"""
    print("EHP (EFFECTIVE HEALTH POOL) CALCULATION SYSTEM")
    print("This demonstrates real PoE defensive mechanics beyond simple Life+ES")
    
    demo_basic_vs_ehp()
    demo_armor_scaling()
    demo_resistance_caps()
    demo_build_archetypes()
    demo_mitigation_breakdown()
    demo_poe_ninja_comparison()
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("✅ EHP provides realistic survivability estimates")
    print("✅ Accounts for armor, resistances, block, fortify")
    print("✅ Uses standard 1000 damage hits like PoB/PoE Ninja")
    print("✅ Provides build ratings and comparisons")
    print("✅ Ready for integration with build categorization")
    print("✅ Can be validated against PoE Ninja builds")


if __name__ == "__main__":
    main()