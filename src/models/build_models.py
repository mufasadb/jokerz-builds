from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Set
from datetime import datetime
from src.data.skill_tags import skill_analyzer


@dataclass
class Character:
    """Character/Build data from PoE Ninja"""
    account: str
    name: str
    level: int
    class_name: str
    ascendancy: Optional[str]
    
    # Performance metrics
    experience: Optional[int] = None
    delve_depth: Optional[int] = None
    delve_solo_depth: Optional[int] = None
    
    # Build details
    life: Optional[int] = None
    energy_shield: Optional[int] = None
    dps: Optional[float] = None
    
    # Skills
    main_skill: Optional[str] = None
    skills: Optional[List[str]] = None
    
    # Items/Equipment
    unique_items: Optional[List[str]] = None
    
    # League info
    league: Optional[str] = None
    rank: Optional[int] = None
    
    # Raw data for additional processing
    raw_data: Optional[Dict[str, Any]] = None


@dataclass
class BuildOverview:
    """Aggregated build statistics from PoE Ninja"""
    league: str
    overview_type: str  # 'exp' or 'depthsolo'
    timestamp: datetime
    total_characters: int
    characters: List[Character]
    
    # Aggregate stats
    class_distribution: Optional[Dict[str, int]] = None
    skill_popularity: Optional[Dict[str, int]] = None
    unique_usage: Optional[Dict[str, int]] = None
    
    def get_characters_by_class(self, class_name: str) -> List[Character]:
        """Filter characters by class name"""
        return [c for c in self.characters if c.class_name == class_name]
    
    def get_characters_by_skill(self, skill_name: str) -> List[Character]:
        """Filter characters using a specific skill"""
        return [c for c in self.characters if c.skills and skill_name in c.skills]
    
    def get_top_delvers(self, limit: int = 10) -> List[Character]:
        """Get top characters by delve depth"""
        delvers = [c for c in self.characters if c.delve_solo_depth is not None]
        return sorted(delvers, key=lambda x: x.delve_solo_depth, reverse=True)[:limit]
    
    def get_level_distribution(self) -> Dict[int, int]:
        """Get distribution of character levels"""
        distribution = {}
        for char in self.characters:
            level = char.level
            distribution[level] = distribution.get(level, 0) + 1
        return distribution
    
    def get_melee_builds(self) -> List[Character]:
        """Get all characters using melee skills"""
        melee_chars = []
        for char in self.characters:
            if char.main_skill and skill_analyzer.is_melee_skill(char.main_skill):
                melee_chars.append(char)
        return melee_chars
    
    def get_spell_builds(self) -> List[Character]:
        """Get all characters using spell skills"""
        spell_chars = []
        for char in self.characters:
            if char.main_skill and skill_analyzer.is_spell(char.main_skill):
                spell_chars.append(char)
        return spell_chars
    
    def get_builds_by_damage_type(self, damage_type: str) -> List[Character]:
        """Get all characters using skills of a specific damage type (Fire, Cold, Lightning, etc)"""
        damage_skills = skill_analyzer.get_damage_type_skills(damage_type)
        return [
            char for char in self.characters
            if char.main_skill and char.main_skill in damage_skills
        ]
    
    def get_skill_category_distribution(self) -> Dict[str, int]:
        """Get distribution of builds by skill categories"""
        all_skills = [char.main_skill for char in self.characters if char.main_skill]
        categorized = skill_analyzer.categorize_skills(all_skills)
        
        return {
            category: len(skills)
            for category, skills in categorized.items()
        }
    
    def analyze_damage_types(self) -> Dict[str, int]:
        """Analyze distribution of damage types across builds"""
        damage_types = ["Physical", "Fire", "Cold", "Lightning", "Chaos"]
        distribution = {}
        
        for damage_type in damage_types:
            count = len(self.get_builds_by_damage_type(damage_type))
            if count > 0:
                distribution[damage_type] = count
        
        return distribution