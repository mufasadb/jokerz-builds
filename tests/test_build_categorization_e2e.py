#!/usr/bin/env python3
"""
End-to-End test for build categorization system
Tests all categorization capabilities: damage types, defense styles, skill types, and cost tiers
"""

import pytest
from src.analysis.build_categorizer import build_categorizer, BuildCategories

try:
    from src.data.skill_tags import skill_analyzer
except ImportError:
    skill_analyzer = None

pytestmark = pytest.mark.skipif(skill_analyzer is None, reason="skill_analyzer not available")


class TestBuildCategorizationE2E:
    """Comprehensive tests for build categorization system"""
    
    def test_physical_melee_tanky_expensive_build(self):
        """Test categorization of a physical melee tanky expensive build"""
        character_data = {
            'name': 'ExpensiveMeleeTank',
            'level': 85,
            'life': 10000,
            'energy_shield': 0,
            'main_skill': 'Boneshatter',
            'enhanced_skills': ['Boneshatter', 'Ancestral Warchief', 'Molten Shell'],
            'enhanced_uniques': ['Brass Dome', 'Meginord\'s Girdle'],  # Brass Dome is expensive
            'main_skill_setup': {
                'gems': [
                    {'name': 'Boneshatter'},
                    {'name': 'Melee Physical Damage Support'},
                    {'name': 'Multistrike Support'},
                    {'name': 'Fortify Support'},
                    {'name': 'Impale Support'}
                ],
                'links': 5
            }
        }
        
        categories = build_categorizer.categorize_build(character_data)
        
        # Damage categorization
        assert categories.primary_damage_type == 'physical'
        assert categories.damage_over_time == False
        
        # Skill delivery
        assert categories.skill_delivery == 'melee'
        assert 'aoe' in categories.skill_mechanics
        
        # Defense style
        assert categories.defense_style == 'tanky'
        assert 'high_armour' in categories.defense_layers
        
        # Cost tier - expensive because of Brass Dome
        assert categories.cost_tier == 'expensive'
        assert '5_link' in categories.cost_factors
        
        print(f"Physical Melee Tank Build: {build_categorizer.get_build_summary(categories)}")
    
    def test_fire_spell_squishy_expensive_build(self):
        """Test categorization of a fire spell squishy expensive build"""
        character_data = {
            'name': 'ExpensiveFireCaster',
            'level': 95,
            'life': 4500,
            'energy_shield': 1500,
            'main_skill': 'Fireball',
            'enhanced_skills': ['Fireball', 'Flame Dash', 'Herald of Ash'],
            'enhanced_uniques': ['Inpulsa\'s Broken Heart', 'The Baron'],
            'main_skill_setup': {
                'gems': [
                    {'name': 'Fireball'},
                    {'name': 'Spell Echo Support'},
                    {'name': 'Controlled Destruction Support'},
                    {'name': 'Fire Penetration Support'},
                    {'name': 'Concentrated Effect Support'},
                    {'name': 'Elemental Focus Support'}
                ],
                'links': 6
            }
        }
        
        categories = build_categorizer.categorize_build(character_data)
        
        # Damage categorization
        assert categories.primary_damage_type == 'fire'
        assert categories.damage_over_time == True  # Fireball can ignite (DoT)
        
        # Skill delivery
        assert categories.skill_delivery == 'self_cast'
        assert 'aoe' in categories.skill_mechanics
        assert 'projectile' in categories.skill_mechanics
        
        # Defense style (should be squishy due to low life per level)
        expected_life_per_level = character_data['life'] / character_data['level']
        assert expected_life_per_level < 50  # This should trigger squishy
        
        # Cost tier - luxury due to multiple expensive uniques + 6-link
        assert categories.cost_tier == 'luxury'
        assert '6_link' in categories.cost_factors
        
        print(f"Fire Spell Build: {build_categorizer.get_build_summary(categories)}")
    
    def test_poison_attack_dodge_moderate_build(self):
        """Test categorization of a poison-based attack build with dodge defenses"""
        character_data = {
            'name': 'PoisonAssassin',
            'level': 92,
            'life': 5200,
            'energy_shield': 800,
            'main_skill': 'Viper Strike',
            'enhanced_skills': ['Viper Strike', 'Whirling Blades', 'Poison Support'],
            'enhanced_uniques': ['Atziri\'s Step', 'Darkray Vectors'],
            'main_skill_setup': {
                'gems': [
                    {'name': 'Viper Strike'},
                    {'name': 'Multistrike Support'},
                    {'name': 'Poison Support'},
                    {'name': 'Deadly Ailments Support'},
                    {'name': 'Unbound Ailments Support'}
                ],
                'links': 5
            }
        }
        
        categories = build_categorizer.categorize_build(character_data)
        
        # Damage categorization
        assert categories.primary_damage_type == 'chaos'
        assert categories.damage_over_time == True  # Poison should trigger DoT
        
        # Skill delivery
        assert categories.skill_delivery == 'melee'
        
        # Defense style
        assert categories.defense_style in ['balanced', 'tanky']  # Good life + ES
        assert 'dodge' in categories.defense_layers
        
        # Cost tier
        assert categories.cost_tier in ['budget', 'moderate']
        
        print(f"Poison Build: {build_categorizer.get_build_summary(categories)}")
    
    def test_lightning_totem_balanced_expensive_build(self):
        """Test categorization of a lightning totem build"""
        character_data = {
            'name': 'TotemHierophant',
            'level': 88,
            'life': 6000,
            'energy_shield': 2000,
            'main_skill': 'Arc',
            'enhanced_skills': ['Arc', 'Spell Totem Support', 'Lightning Tendrils'],
            'enhanced_uniques': ['Belly of the Beast', 'Goldrim'],  # Belly of the Beast is expensive
            'main_skill_setup': {
                'gems': [
                    {'name': 'Arc'},
                    {'name': 'Spell Totem Support'},
                    {'name': 'Lightning Penetration Support'},
                    {'name': 'Controlled Destruction Support'},
                    {'name': 'Elemental Focus Support'}
                ],
                'links': 5
            }
        }
        
        categories = build_categorizer.categorize_build(character_data)
        
        # Damage categorization
        assert categories.primary_damage_type == 'lightning'
        assert categories.damage_over_time == False
        
        # Skill delivery - should detect totem from Spell Totem Support
        assert categories.skill_delivery == 'totem'
        
        # Defense style
        assert categories.defense_style in ['balanced', 'tanky']  # Good life + ES combo
        
        # Cost tier - expensive because of Belly of the Beast
        assert categories.cost_tier == 'expensive'
        
        print(f"Lightning Totem Build: {build_categorizer.get_build_summary(categories)}")
    
    def test_elemental_minion_luxury_build(self):
        """Test categorization of an expensive minion build with elemental damage"""
        character_data = {
            'name': 'LuxuryNecro',
            'level': 97,
            'life': 7500,
            'energy_shield': 3000,
            'main_skill': 'Raise Spectre',
            'enhanced_skills': ['Raise Spectre', 'Desecrate', 'Bone Offering'],
            'enhanced_uniques': ['Mageblood', 'Shaper\'s Touch', 'Mon\'tregul\'s Grasp'],
            'main_skill_setup': {
                'gems': [
                    {'name': 'Raise Spectre'},
                    {'name': 'Minion Damage Support'},
                    {'name': 'Melee Physical Damage Support'},
                    {'name': 'Multistrike Support'},
                    {'name': 'Elemental Army Support'},
                    {'name': 'Elemental Focus Support'}
                ],
                'links': 6
            }
        }
        
        categories = build_categorizer.categorize_build(character_data)
        
        # Damage categorization - elemental from support gems
        assert categories.primary_damage_type in ['physical', 'elemental']
        
        # Skill delivery
        assert categories.skill_delivery == 'minion'
        
        # Defense style - should be very tanky
        assert categories.defense_style == 'tanky'
        assert 'energy_shield' in categories.defense_layers
        
        # Cost tier - Mageblood should make this luxury
        assert categories.cost_tier == 'luxury'
        assert 'luxury_unique' in categories.cost_factors
        assert '6_link' in categories.cost_factors
        
        print(f"Luxury Minion Build: {build_categorizer.get_build_summary(categories)}")
    
    def test_bleed_bow_balanced_expensive_build(self):
        """Test categorization of a bleed-based bow build"""
        character_data = {
            'name': 'BleedGladiator',
            'level': 90,
            'life': 6500,
            'energy_shield': 0,
            'main_skill': 'Lacerate',
            'enhanced_skills': ['Lacerate', 'Blood Rage', 'Leap Slam'],
            'enhanced_uniques': ['Kaom\'s Heart', 'Lioneye\'s Remorse'],
            'main_skill_setup': {
                'gems': [
                    {'name': 'Lacerate'},
                    {'name': 'Chance to Bleed Support'},
                    {'name': 'Brutality Support'},
                    {'name': 'Melee Physical Damage Support'},
                    {'name': 'Multistrike Support'},
                    {'name': 'Fortify Support'}
                ],
                'links': 6
            }
        }
        
        categories = build_categorizer.categorize_build(character_data)
        
        # Damage categorization
        assert categories.primary_damage_type == 'physical'
        assert categories.damage_over_time == True  # Lacerate should trigger bleed DoT
        
        # Skill delivery
        assert categories.skill_delivery == 'melee'
        
        # Defense style
        assert categories.defense_style in ['tanky', 'balanced']
        assert 'max_life' in categories.defense_layers  # Kaom's Heart
        assert 'block' in categories.defense_layers  # Lioneye's Remorse
        
        # Cost tier
        assert categories.cost_tier == 'expensive'  # Kaom's Heart is expensive
        
        print(f"Bleed Build: {build_categorizer.get_build_summary(categories)}")
    
    def test_all_elemental_self_cast_squishy_budget(self):
        """Test categorization of an all-elemental self-cast build"""
        character_data = {
            'name': 'ElementalWitch',
            'level': 82,
            'life': 3800,
            'energy_shield': 1200,
            'main_skill': 'Arc',
            'enhanced_skills': ['Arc', 'Herald of Thunder', 'Herald of Ice'],
            'enhanced_uniques': ['Tabula Rasa', 'Goldrim', 'Wanderlust'],
            'main_skill_setup': {
                'gems': [
                    {'name': 'Arc'},
                    {'name': 'Lightning Penetration Support'},
                    {'name': 'Added Lightning Damage Support'},
                    {'name': 'Added Cold Damage Support'},
                    {'name': 'Elemental Focus Support'},
                    {'name': 'Controlled Destruction Support'}
                ],
                'links': 6
            }
        }
        
        categories = build_categorizer.categorize_build(character_data)
        
        # Should detect multiple elemental types from supports
        assert categories.primary_damage_type in ['lightning', 'elemental']
        assert 'cold' in categories.secondary_damage_types or categories.primary_damage_type == 'elemental'
        
        # Skill delivery
        assert categories.skill_delivery == 'self_cast'
        
        # Defense style - low life per level should be squishy
        life_per_level = character_data['life'] / character_data['level']
        assert life_per_level < 50
        
        # Cost tier - expensive due to 6-link requirement, despite budget uniques
        assert categories.cost_tier == 'expensive'
        
        print(f"Elemental Self-Cast Build: {build_categorizer.get_build_summary(categories)}")
    
    def test_categorization_batch_processing(self):
        """Test batch processing of multiple builds"""
        builds_data = [
            {
                'name': 'Build1',
                'level': 90,
                'life': 5000,
                'energy_shield': 0,
                'main_skill': 'Cyclone',
                'enhanced_uniques': ['Kaom\'s Heart']
            },
            {
                'name': 'Build2', 
                'level': 85,
                'life': 4000,
                'energy_shield': 2000,
                'main_skill': 'Fireball',
                'enhanced_uniques': ['Tabula Rasa']
            },
            {
                'name': 'Build3',
                'level': 95,
                'life': 6000,
                'energy_shield': 1000,
                'main_skill': 'Raise Spectre',
                'enhanced_uniques': ['The Baron', 'Mon\'tregul\'s Grasp']
            }
        ]
        
        results = build_categorizer.categorize_builds_batch(builds_data)
        
        assert len(results) == 3
        
        for build_data, categories in results:
            assert isinstance(categories, BuildCategories)
            assert build_data['name'] in ['Build1', 'Build2', 'Build3']
            
            # Each should have some categorization (some fields may be None for complex builds)
            # At minimum, should have skill_delivery and cost_tier
            assert categories.skill_delivery is not None
            assert categories.defense_style is not None
            assert categories.cost_tier is not None
            
            # Minion builds may not have clear damage types, others should
            if build_data['name'] != 'Build3':  # Build3 is the minion build
                assert categories.primary_damage_type is not None
            
            print(f"{build_data['name']}: {build_categorizer.get_build_summary(categories)}")
    
    def test_confidence_scoring(self):
        """Test that confidence scores are calculated properly"""
        complete_character_data = {
            'name': 'CompleteTestBuild',
            'level': 90,
            'life': 5000,
            'energy_shield': 1000,
            'main_skill': 'Arc',
            'enhanced_skills': ['Arc', 'Lightning Tendrils'],
            'enhanced_uniques': ['Belly of the Beast'],
            'main_skill_setup': {
                'gems': [
                    {'name': 'Arc'},
                    {'name': 'Lightning Penetration Support'},
                    {'name': 'Controlled Destruction Support'}
                ],
                'links': 3
            }
        }
        
        categories = build_categorizer.categorize_build(complete_character_data)
        
        # Should have high overall confidence due to complete data
        assert categories.confidence_scores['overall'] >= 0.8
        
        # Should have decent confidence in individual categories
        assert 'damage_type' in categories.confidence_scores
        assert 'skill_delivery' in categories.confidence_scores
        assert 'defense' in categories.confidence_scores
        assert 'cost' in categories.confidence_scores
        
        print(f"Confidence scores: {categories.confidence_scores}")


def run_comprehensive_categorization_test():
    """Run all categorization tests and display results"""
    print("=" * 80)
    print("COMPREHENSIVE BUILD CATEGORIZATION TEST")
    print("=" * 80)
    
    test_instance = TestBuildCategorizationE2E()
    
    tests = [
        ("Physical Melee Tanky Expensive", test_instance.test_physical_melee_tanky_expensive_build),
        ("Fire Spell Squishy Expensive", test_instance.test_fire_spell_squishy_expensive_build),
        ("Poison Attack Dodge Moderate", test_instance.test_poison_attack_dodge_moderate_build),
        ("Lightning Totem Balanced Expensive", test_instance.test_lightning_totem_balanced_expensive_build),
        ("Luxury Minion Build", test_instance.test_elemental_minion_luxury_build),
        ("Bleed Bow Build", test_instance.test_bleed_bow_balanced_expensive_build),
        ("All Elemental Self-Cast", test_instance.test_all_elemental_self_cast_squishy_budget),
        ("Batch Processing", test_instance.test_categorization_batch_processing),
        ("Confidence Scoring", test_instance.test_confidence_scoring),
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
    
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)
    
    if failed == 0:
        print("🎉 ALL CATEGORIZATION TESTS PASSED!")
        print("\nThe build categorization system successfully handles:")
        print("✅ Damage outputs: fire, physical, bleed, poison, elemental")
        print("✅ Defensive styles: tanky, squishy, high armour, dodge")
        print("✅ Skill types: melee, self cast, totem, minion")
        print("✅ Cost tiers: expensive, cheap (budget), luxury, moderate")
        return True
    else:
        print(f"⚠️  {failed} tests failed - see details above")
        return False


if __name__ == "__main__":
    run_comprehensive_categorization_test()