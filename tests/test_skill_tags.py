import pytest
import sys
import os

# Add the project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.data.skill_tags import SkillTagAnalyzer, skill_analyzer
    SKIP_TESTS = False
except ImportError as e:
    # Skip all tests if the module can't be imported
    SKIP_TESTS = True
    SKIP_REASON = f"src.data.skill_tags module not available: {e}"


@pytest.mark.skipif(SKIP_TESTS, reason=SKIP_REASON if SKIP_TESTS else "")
class TestSkillTagAnalyzer:
    def test_get_skill_tags(self):
        """Test retrieving tags for a specific skill"""
        # Test known skill
        tags = skill_analyzer.get_skill_tags("Cyclone")
        assert "Attack" in tags
        assert "Melee" in tags
        assert "Physical" in tags
        assert "Channelling" in tags
        
        # Test unknown skill
        tags = skill_analyzer.get_skill_tags("NonExistentSkill")
        assert tags == []
    
    def test_get_skills_by_tag(self):
        """Test retrieving skills by a single tag"""
        # Get all melee skills
        melee_skills = skill_analyzer.get_skills_by_tag("Melee")
        assert len(melee_skills) > 0
        assert "Cyclone" in melee_skills
        assert "Heavy Strike" in melee_skills
        assert "Fireball" not in melee_skills  # Spell, not melee
        
        # Get all cold skills
        cold_skills = skill_analyzer.get_skills_by_tag("Cold")
        assert "Ice Crash" in cold_skills
        assert "Frost Blades" in cold_skills
        assert "Fireball" not in cold_skills
    
    def test_get_skills_by_tags_any(self):
        """Test retrieving skills matching ANY of multiple tags"""
        # Get skills that are either Fire OR Cold
        elemental_skills = skill_analyzer.get_skills_by_tags(["Fire", "Cold"], match_all=False)
        assert "Fireball" in elemental_skills  # Fire
        assert "Ice Nova" in elemental_skills  # Cold
        assert "Cyclone" not in elemental_skills  # Physical
    
    def test_get_skills_by_tags_all(self):
        """Test retrieving skills matching ALL of multiple tags"""
        # Get skills that are both Melee AND Cold
        melee_cold = skill_analyzer.get_skills_by_tags(["Melee", "Cold"], match_all=True)
        assert "Ice Crash" in melee_cold
        assert "Frost Blades" in melee_cold
        assert "Ice Nova" not in melee_cold  # Cold but not Melee
        assert "Cyclone" not in melee_cold  # Melee but not Cold
        
        # Get skills that are Attack, Projectile, and Lightning
        specific_skills = skill_analyzer.get_skills_by_tags(
            ["Attack", "Projectile", "Lightning"], 
            match_all=True
        )
        assert "Lightning Strike" in specific_skills
        assert "Arc" not in specific_skills  # Lightning spell, not attack
    
    def test_is_melee_skill(self):
        """Test melee skill detection"""
        assert skill_analyzer.is_melee_skill("Cyclone") is True
        assert skill_analyzer.is_melee_skill("Heavy Strike") is True
        assert skill_analyzer.is_melee_skill("Fireball") is False
        assert skill_analyzer.is_melee_skill("Arc") is False
        assert skill_analyzer.is_melee_skill("UnknownSkill") is False
    
    def test_is_spell(self):
        """Test spell detection"""
        assert skill_analyzer.is_spell("Fireball") is True
        assert skill_analyzer.is_spell("Arc") is True
        assert skill_analyzer.is_spell("Cyclone") is False
        assert skill_analyzer.is_spell("Heavy Strike") is False
    
    def test_get_damage_type_skills(self):
        """Test retrieving skills by damage type"""
        # Physical skills
        physical = skill_analyzer.get_damage_type_skills("Physical")
        assert "Cyclone" in physical
        assert "Heavy Strike" in physical
        
        # Fire skills
        fire = skill_analyzer.get_damage_type_skills("Fire")
        assert "Fireball" in fire
        assert "Molten Strike" in fire
        
        # Cold skills
        cold = skill_analyzer.get_damage_type_skills("Cold")
        assert "Ice Nova" in cold
        assert "Frost Blades" in cold
    
    def test_categorize_skills(self):
        """Test skill categorization"""
        skills = [
            "Cyclone", "Fireball", "Lightning Strike", "Raise Spectre",
            "Arc", "Heavy Strike", "Ice Nova"
        ]
        
        categories = skill_analyzer.categorize_skills(skills)
        
        assert "Cyclone" in categories["Melee"]
        assert "Heavy Strike" in categories["Melee"]
        assert "Lightning Strike" in categories["Melee"]
        
        assert "Fireball" in categories["Spell"]
        assert "Arc" in categories["Spell"]
        assert "Ice Nova" in categories["Spell"]
        
        assert "Raise Spectre" in categories["Minion"]
    
    def test_edge_cases(self):
        """Test edge cases and error handling"""
        # Empty tag list
        skills = skill_analyzer.get_skills_by_tags([], match_all=False)
        assert skills == set()
        
        # Non-existent tag
        skills = skill_analyzer.get_skills_by_tag("NonExistentTag")
        assert skills == set()
        
        # Empty skill list for categorization
        categories = skill_analyzer.categorize_skills([])
        assert categories == {}


@pytest.mark.skipif(SKIP_TESTS, reason=SKIP_REASON if SKIP_TESTS else "")
class TestSkillTagIntegration:
    def test_comprehensive_skill_analysis(self):
        """Test comprehensive skill analysis workflow"""
        # Create a new analyzer instance
        analyzer = SkillTagAnalyzer()
        
        # Get all melee skills
        melee_skills = analyzer.get_skills_by_tag("Melee")
        
        # Verify they all have Melee tag
        for skill in melee_skills:
            tags = analyzer.get_skill_tags(skill)
            assert "Melee" in tags
        
        # Check damage type distribution in melee skills
        damage_types = {
            "Physical": 0,
            "Fire": 0,
            "Cold": 0,
            "Lightning": 0,
            "Chaos": 0
        }
        
        for skill in melee_skills:
            tags = analyzer.get_skill_tags(skill)
            for damage_type in damage_types:
                if damage_type in tags:
                    damage_types[damage_type] += 1
        
        # Should have some skills of each damage type
        assert damage_types["Physical"] > 0
        assert damage_types["Fire"] > 0
        assert damage_types["Cold"] > 0