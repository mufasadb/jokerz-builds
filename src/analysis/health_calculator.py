"""
Health and Energy Shield calculator for Path of Exile characters.

This module calculates life and ES based on:
- Base values from level and class
- Attribute bonuses (Strength for life, Intelligence for ES)
- Passive tree modifiers
- Equipment modifiers
- Percentage increases from all sources
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import re

logger = logging.getLogger(__name__)


@dataclass
class HealthCalculationResult:
    """Results from health/ES calculation"""
    # Base values
    base_life: int = 0
    base_es: int = 0
    
    # Flat additions
    flat_life_from_tree: int = 0
    flat_life_from_gear: int = 0
    flat_life_from_strength: int = 0
    flat_es_from_tree: int = 0
    flat_es_from_gear: int = 0
    flat_es_from_intelligence: int = 0
    
    # Percentage increases
    increased_life_from_tree: float = 0.0
    increased_life_from_gear: float = 0.0
    increased_es_from_tree: float = 0.0
    increased_es_from_gear: float = 0.0
    
    # Final calculated values
    total_flat_life: int = 0
    total_flat_es: int = 0
    total_increased_life: float = 0.0
    total_increased_es: float = 0.0
    final_life: int = 0
    final_es: int = 0
    total_ehp: int = 0
    
    # Debug information
    calculation_steps: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class HealthCalculator:
    """Calculate character life and energy shield from various sources"""
    
    def __init__(self):
        # Base life values per class at level 1
        self.base_life_by_class = {
            "Marauder": 32,
            "Duelist": 32,
            "Ranger": 32,
            "Witch": 32,
            "Templar": 32,
            "Shadow": 32,
            "Scion": 32,
            # Ascendancy classes inherit from base
            "Juggernaut": 32,
            "Berserker": 32,
            "Chieftain": 32,
            "Gladiator": 32,
            "Champion": 32,
            "Slayer": 32,
            "Deadeye": 32,
            "Raider": 32,
            "Pathfinder": 32,
            "Necromancer": 32,
            "Elementalist": 32,
            "Occultist": 32,
            "Hierophant": 32,
            "Guardian": 32,
            "Inquisitor": 32,
            "Assassin": 32,
            "Saboteur": 32,
            "Trickster": 32,
            "Ascendant": 32
        }
        
        # Life per level (same for all classes)
        self.life_per_level = 12
        
        # Strength gives 0.5 life per point
        self.life_per_strength = 0.5
        
        # Intelligence gives 0.5 ES per point  
        self.es_per_intelligence = 0.5
        
        # Common life/ES modifiers patterns
        self.life_patterns = [
            (r'\+(\d+) to maximum Life', 'flat'),
            (r'(\d+)% increased maximum Life', 'increased'),
            (r'\+(\d+) to Life', 'flat'),
            (r'(\d+)% increased Life', 'increased'),
        ]
        
        self.es_patterns = [
            (r'\+(\d+) to maximum Energy Shield', 'flat'),
            (r'(\d+)% increased maximum Energy Shield', 'increased'),
            (r'\+(\d+) to Energy Shield', 'flat'),
            (r'(\d+)% increased Energy Shield', 'increased'),
        ]
        
        # Base ES values for equipment slots
        self.base_es_by_slot = {
            "Body Armour": {"min": 0, "max": 600},
            "Helmet": {"min": 0, "max": 200},
            "Gloves": {"min": 0, "max": 150},
            "Boots": {"min": 0, "max": 150},
            "Shield": {"min": 0, "max": 500}
        }
        
    def calculate_health(self, character_data: Dict[str, Any]) -> HealthCalculationResult:
        """
        Calculate total life and ES for a character
        
        Args:
            character_data: Dictionary containing:
                - level: Character level
                - class: Character class/ascendancy
                - attributes: Dict with strength, intelligence values
                - passive_tree: List of allocated passive nodes
                - equipment: List of equipped items
                
        Returns:
            HealthCalculationResult with detailed breakdown
        """
        result = HealthCalculationResult()
        
        # Extract character info
        level = character_data.get('level', 1)
        char_class = character_data.get('class', 'Scion')
        attributes = character_data.get('attributes', {})
        passive_tree = character_data.get('passive_tree', [])
        equipment = character_data.get('equipment', [])
        
        # 1. Calculate base life
        result.base_life = self._calculate_base_life(level, char_class)
        result.calculation_steps.append(f"Base life (level {level} {char_class}): {result.base_life}")
        
        # 2. Add life from strength
        strength = attributes.get('strength', 0)
        result.flat_life_from_strength = int(strength * self.life_per_strength)
        result.calculation_steps.append(f"Life from {strength} strength: +{result.flat_life_from_strength}")
        
        # 3. Parse passive tree for life modifiers
        tree_life_flat, tree_life_inc = self._parse_passive_tree_life(passive_tree)
        result.flat_life_from_tree = tree_life_flat
        result.increased_life_from_tree = tree_life_inc
        result.calculation_steps.append(f"Life from tree: +{tree_life_flat} flat, {tree_life_inc}% increased")
        
        # 4. Parse equipment for life modifiers
        gear_life_flat, gear_life_inc = self._parse_equipment_life(equipment)
        result.flat_life_from_gear = gear_life_flat
        result.increased_life_from_gear = gear_life_inc
        result.calculation_steps.append(f"Life from gear: +{gear_life_flat} flat, {gear_life_inc}% increased")
        
        # 5. Calculate total flat life
        result.total_flat_life = (
            result.base_life + 
            result.flat_life_from_strength + 
            result.flat_life_from_tree + 
            result.flat_life_from_gear
        )
        
        # 6. Calculate total increased life
        result.total_increased_life = (
            result.increased_life_from_tree + 
            result.increased_life_from_gear
        )
        
        # 7. Calculate final life
        result.final_life = int(result.total_flat_life * (1 + result.total_increased_life / 100))
        result.calculation_steps.append(
            f"Final life: {result.total_flat_life} * {1 + result.total_increased_life/100:.2f} = {result.final_life}"
        )
        
        # 8. Calculate ES (similar process)
        result.base_es = self._calculate_base_es(equipment)
        intelligence = attributes.get('intelligence', 0)
        result.flat_es_from_intelligence = int(intelligence * self.es_per_intelligence)
        
        tree_es_flat, tree_es_inc = self._parse_passive_tree_es(passive_tree)
        result.flat_es_from_tree = tree_es_flat
        result.increased_es_from_tree = tree_es_inc
        
        gear_es_flat, gear_es_inc = self._parse_equipment_es(equipment)
        result.flat_es_from_gear = gear_es_flat
        result.increased_es_from_gear = gear_es_inc
        
        result.total_flat_es = (
            result.base_es + 
            result.flat_es_from_intelligence + 
            result.flat_es_from_tree + 
            result.flat_es_from_gear
        )
        
        result.total_increased_es = (
            result.increased_es_from_tree + 
            result.increased_es_from_gear
        )
        
        result.final_es = int(result.total_flat_es * (1 + result.total_increased_es / 100))
        result.calculation_steps.append(
            f"Final ES: {result.total_flat_es} * {1 + result.total_increased_es/100:.2f} = {result.final_es}"
        )
        
        # 9. Calculate total EHP
        result.total_ehp = result.final_life + result.final_es
        
        return result
    
    def _calculate_base_life(self, level: int, char_class: str) -> int:
        """Calculate base life from level and class"""
        base_at_level_1 = self.base_life_by_class.get(char_class, 32)
        return base_at_level_1 + (level - 1) * self.life_per_level
    
    def _calculate_base_es(self, equipment: List[Dict[str, Any]]) -> int:
        """Calculate base ES from equipment pieces"""
        total_base_es = 0
        
        for item in equipment:
            # Check if item has ES property regardless of slot
            properties = item.get('properties', [])
            for prop in properties:
                if prop.get('name') == 'Energy Shield':
                    values = prop.get('values', [[]])
                    if values and values[0]:
                        try:
                            # Remove any color formatting and extract number
                            es_str = values[0][0] if isinstance(values[0][0], str) else str(values[0][0])
                            es_value = re.sub(r'[^\d]', '', es_str)
                            if es_value:
                                total_base_es += int(es_value)
                        except Exception as e:
                            # Log parsing error but continue
                            pass
        
        return total_base_es
    
    def _parse_passive_tree_life(self, passive_tree: List[Dict[str, Any]]) -> Tuple[int, float]:
        """Parse passive tree nodes for life modifiers"""
        flat_life = 0
        increased_life = 0.0
        
        for node in passive_tree:
            # Node can be either just an ID or a dict with stats
            if isinstance(node, dict):
                stats = node.get('stats', [])
                for stat in stats:
                    # Check for flat life
                    if '+' in stat and 'maximum Life' in stat:
                        match = re.search(r'\+(\d+) to maximum Life', stat)
                        if match:
                            flat_life += int(match.group(1))
                    # Check for increased life
                    elif '%' in stat and 'maximum Life' in stat:
                        match = re.search(r'(\d+)% increased maximum Life', stat)
                        if match:
                            increased_life += float(match.group(1))
        
        return flat_life, increased_life
    
    def _parse_equipment_life(self, equipment: List[Dict[str, Any]]) -> Tuple[int, float]:
        """Parse equipment for life modifiers"""
        flat_life = 0
        increased_life = 0.0
        
        for item in equipment:
            # Check explicit modifiers
            explicit_mods = item.get('explicitMods', [])
            for mod in explicit_mods:
                for pattern, mod_type in self.life_patterns:
                    match = re.search(pattern, mod)
                    if match:
                        value = float(match.group(1))
                        if mod_type == 'flat':
                            flat_life += int(value)
                        else:  # increased
                            increased_life += value
            
            # Check implicit modifiers
            implicit_mods = item.get('implicitMods', [])
            for mod in implicit_mods:
                for pattern, mod_type in self.life_patterns:
                    match = re.search(pattern, mod)
                    if match:
                        value = float(match.group(1))
                        if mod_type == 'flat':
                            flat_life += int(value)
                        else:  # increased
                            increased_life += value
            
            # Check crafted modifiers
            crafted_mods = item.get('craftedMods', [])
            for mod in crafted_mods:
                for pattern, mod_type in self.life_patterns:
                    match = re.search(pattern, mod)
                    if match:
                        value = float(match.group(1))
                        if mod_type == 'flat':
                            flat_life += int(value)
                        else:  # increased
                            increased_life += value
        
        return flat_life, increased_life
    
    def _parse_passive_tree_es(self, passive_tree: List[Dict[str, Any]]) -> Tuple[int, float]:
        """Parse passive tree nodes for ES modifiers"""
        flat_es = 0
        increased_es = 0.0
        
        for node in passive_tree:
            if isinstance(node, dict):
                stats = node.get('stats', [])
                for stat in stats:
                    # Check for flat ES
                    if '+' in stat and 'Energy Shield' in stat:
                        match = re.search(r'\+(\d+) to maximum Energy Shield', stat)
                        if match:
                            flat_es += int(match.group(1))
                    # Check for increased ES
                    elif '%' in stat and 'Energy Shield' in stat:
                        match = re.search(r'(\d+)% increased maximum Energy Shield', stat)
                        if match:
                            increased_es += float(match.group(1))
        
        return flat_es, increased_es
    
    def _parse_equipment_es(self, equipment: List[Dict[str, Any]]) -> Tuple[int, float]:
        """Parse equipment for ES modifiers"""
        flat_es = 0
        increased_es = 0.0
        
        for item in equipment:
            # Check all modifier types
            for mod_type in ['explicitMods', 'implicitMods', 'craftedMods']:
                mods = item.get(mod_type, [])
                for mod in mods:
                    for pattern, mod_type in self.es_patterns:
                        match = re.search(pattern, mod)
                        if match:
                            value = float(match.group(1))
                            if mod_type == 'flat':
                                flat_es += int(value)
                            else:  # increased
                                increased_es += value
        
        return flat_es, increased_es


# Global calculator instance
health_calculator = HealthCalculator()