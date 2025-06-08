"""
Build categorization system for analyzing PoE builds by damage type, defense style, skill type, and cost
"""

import logging
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field
from src.analysis.ehp_calculator import ehp_calculator, DefensiveStats, EHPResult

# Import skill analyzer with fallback
try:
    from src.data.skill_tags import skill_analyzer
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("Skill analyzer not available, skill categorization will be limited")
    skill_analyzer = None

logger = logging.getLogger(__name__)


@dataclass
class BuildCategories:
    """Contains all categorization results for a build"""
    # Damage categorization
    primary_damage_type: Optional[str] = None
    secondary_damage_types: List[str] = field(default_factory=list)
    damage_over_time: bool = False
    
    # Skill type categorization  
    skill_delivery: Optional[str] = None  # "melee", "self_cast", "totem", "minion", "trap", "bow"
    skill_mechanics: List[str] = field(default_factory=list)  # "channelling", "aoe", "projectile"
    
    # Defensive categorization
    defense_style: Optional[str] = None  # "tanky", "squishy", "balanced"
    defense_layers: List[str] = field(default_factory=list)  # "high_armour", "dodge", "block", "leech"
    
    # EHP and tankiness metrics
    ehp_result: Optional[EHPResult] = None
    tankiness_rating: Optional[str] = None  # "Extremely Tanky", "Very Tanky", etc.
    
    # Cost categorization
    cost_tier: Optional[str] = None  # "budget", "moderate", "expensive", "luxury"
    cost_factors: List[str] = field(default_factory=list)  # "rare_uniques", "6_link", "expensive_gems"
    
    # Confidence scores (0.0 to 1.0)
    confidence_scores: Dict[str, float] = field(default_factory=dict)


class BuildCategorizer:
    """Analyzes and categorizes PoE builds based on skills, items, and stats"""
    
    def __init__(self):
        # Extended damage type mappings
        self.damage_types = {
            "physical": ["Physical"],
            "fire": ["Fire"],
            "cold": ["Cold"], 
            "lightning": ["Lightning"],
            "chaos": ["Chaos"],
            "elemental": ["Fire", "Cold", "Lightning"],  # Combined elemental
        }
        
        # Damage over time skill patterns
        self.dot_skills = {
            "bleed": ["Lacerate", "Gladiator", "Bloodletting"],
            "poison": ["Viper Strike", "Pestilent Strike", "Poison Support", "Assassin"],
            "ignite": ["Fireball", "Flameblast", "Burning Arrow", "Elementalist"],
            "burn": ["Righteous Fire", "Scorching Ray"],
            "chaos_dot": ["Essence Drain", "Contagion", "Bane", "Caustic Arrow"]
        }
        
        # Skill delivery mechanisms
        self.delivery_patterns = {
            "melee": ["Melee", "Strike"],
            "self_cast": ["Spell"],  # Will filter out totems/traps/etc
            "totem": ["Totem"],
            "minion": ["Minion", "Golem"],
            "trap": ["Trap"],
            "mine": ["Mine"],
            "bow": ["Bow"],
            "trigger": ["Trigger", "Cast on Crit", "Cast when"]
        }
        
        # Defensive unique items that indicate tanky builds
        self.defensive_uniques = {
            "high_armour": [
                "Brass Dome", "Belly of the Beast", "Kaom's Heart", "Geofri's Sanctuary",
                "The Baron", "Formless Inferno", "Belly of the Beast"
            ],
            "energy_shield": [
                "Shaper's Touch", "Presence of Chayula", "Shavronne's Wrappings", 
                "Vis Mortis", "The Covenant"
            ],
            "block": [
                "Aegis Aurora", "The Surrender", "Lioneye's Remorse", "Advancing Fortress"
            ],
            "dodge": [
                "Atziri's Step", "Darkray Vectors", "Queen of the Forest", "Hyrri's Ire"
            ],
            "max_life": [
                "Kaom's Heart", "Belly of the Beast", "The Baron", "Geofri's Sanctuary"
            ],
            "recovery": [
                "The Soul Taker", "Bloodseeker", "Slayer", "Trickster"
            ]
        }
        
        # Expensive unique items that indicate high cost builds
        self.expensive_uniques = {
            "luxury": [  # Very expensive, build-enabling
                "Mageblood", "Headhunter", "Mirror of Kalandra", "Oni-Goroshi",
                "Shaper's Touch", "Aegis Aurora", "Shavronne's Wrappings"
            ],
            "expensive": [  # Moderately expensive but accessible
                "Belly of the Beast", "Kaom's Heart", "Inpulsa's Broken Heart",
                "Doryani's Prototype", "The Baron", "Mon'tregul's Grasp", "Brass Dome"
            ],
            "moderate": [  # Common build uniques
                "Tabula Rasa", "Goldrim", "Wanderlust", "Meginord's Girdle",
                "The Princess", "Lycosidae"
            ],
            "budget": [  # Very cheap starter uniques
                "Wanderlust", "Goldrim", "The Princess", "Meginord's Girdle"
            ]
        }
        
    def _get_skill_tags(self, skill_name: str) -> List[str]:
        """Get skill tags with fallback for when skill_analyzer is not available"""
        if skill_analyzer is None:
            return []
        return skill_analyzer.get_skill_tags(skill_name)

    def categorize_build(self, character_data: Dict[str, Any]) -> BuildCategories:
        """
        Fully categorize a build based on character data
        
        Args:
            character_data: Character data including skills, items, stats
            
        Returns:
            BuildCategories with all categorization results
        """
        categories = BuildCategories()
        
        # Extract relevant data
        main_skill = character_data.get('main_skill')
        skills = character_data.get('enhanced_skills') or character_data.get('skills', [])
        unique_items = character_data.get('enhanced_uniques') or character_data.get('unique_items', [])
        main_skill_setup = character_data.get('main_skill_setup', {})
        
        # Character stats for defensive analysis
        life = character_data.get('life', 0) or 0
        energy_shield = character_data.get('energy_shield', 0) or 0
        level = character_data.get('level', 1)
        
        # Damage type analysis
        self._categorize_damage_types(categories, main_skill, skills, main_skill_setup)
        
        # Skill delivery analysis
        self._categorize_skill_delivery(categories, main_skill, skills, main_skill_setup)
        
        # Defensive analysis
        self._categorize_defense_style(categories, character_data, unique_items, life, energy_shield, level)
        
        # Cost analysis
        self._categorize_cost_tier(categories, unique_items, main_skill_setup)
        
        # Calculate confidence scores
        self._calculate_confidence_scores(categories, character_data)
        
        return categories
    
    def _categorize_damage_types(self, categories: BuildCategories, main_skill: str, 
                                skills: List[str], main_skill_setup: Dict) -> None:
        """Determine primary and secondary damage types"""
        if not main_skill:
            return
            
        main_skill_tags = self._get_skill_tags(main_skill)
        damage_type_counts = {}
        
        # Count damage types from main skill
        for damage_type, tags in self.damage_types.items():
            if any(tag in main_skill_tags for tag in tags):
                damage_type_counts[damage_type] = damage_type_counts.get(damage_type, 0) + 3  # Weight main skill heavily
        
        # Count from support gems in main setup
        if main_skill_setup:
            gems = main_skill_setup.get('gems', [])
            for gem in gems:
                gem_name = gem.get('name', '')
                gem_tags = self._get_skill_tags(gem_name)
                for damage_type, tags in self.damage_types.items():
                    if any(tag in gem_tags for tag in tags):
                        damage_type_counts[damage_type] = damage_type_counts.get(damage_type, 0) + 1
        
        # Determine primary damage type
        if damage_type_counts:
            sorted_damages = sorted(damage_type_counts.items(), key=lambda x: x[1], reverse=True)
            categories.primary_damage_type = sorted_damages[0][0]
            
            # Secondary damage types (excluding primary)
            categories.secondary_damage_types = [
                damage_type for damage_type, count in sorted_damages[1:] 
                if count >= 1
            ]
        
        # Check for damage over time
        categories.damage_over_time = self._has_damage_over_time(main_skill, skills)
        categories.confidence_scores['damage_type'] = min(1.0, max(damage_type_counts.values()) / 5.0) if damage_type_counts else 0.0
    
    def _has_damage_over_time(self, main_skill: str, skills: List[str]) -> bool:
        """Check if build uses damage over time mechanics"""
        all_skills = [main_skill] + (skills or [])
        
        for dot_type, dot_skills in self.dot_skills.items():
            for skill in all_skills:
                if skill and any(dot_skill.lower() in skill.lower() for dot_skill in dot_skills):
                    return True
        return False
    
    def _categorize_skill_delivery(self, categories: BuildCategories, main_skill: str,
                                 skills: List[str], main_skill_setup: Dict) -> None:
        """Determine how skills are delivered (melee, self-cast, totem, etc)"""
        if not main_skill:
            return
            
        main_skill_tags = self._get_skill_tags(main_skill)
        delivery_scores = {}
        
        # Check main skill delivery method (exclude Spell for now, handle it specially)
        for delivery, required_tags in self.delivery_patterns.items():
            if delivery != "self_cast" and any(tag in main_skill_tags for tag in required_tags):
                delivery_scores[delivery] = delivery_scores.get(delivery, 0) + 3
        
        # Check support gems that modify delivery method
        if main_skill_setup:
            gems = main_skill_setup.get('gems', [])
            for gem in gems:
                gem_name = gem.get('name', '')
                gem_tags = self._get_skill_tags(gem_name)
                
                # Support gems that change delivery method get highest priority
                if any(tag in gem_tags for tag in ["Totem", "Trap", "Mine"]):
                    for delivery, required_tags in self.delivery_patterns.items():
                        if any(tag in gem_tags for tag in required_tags):
                            delivery_scores[delivery] = delivery_scores.get(delivery, 0) + 10  # Highest weight for delivery-changing supports
                
                # Other support gems get normal weight
                else:
                    for delivery, required_tags in self.delivery_patterns.items():
                        if any(tag in gem_tags for tag in required_tags):
                            delivery_scores[delivery] = delivery_scores.get(delivery, 0) + 3  # Normal weight for other supports
        
        # Special case: self-cast spells (spells that aren't totems/traps/minions)
        if "Spell" in main_skill_tags:
            # Check if any support gems make it indirect
            is_indirect_from_main = any(tag in main_skill_tags for tag in ["Totem", "Trap", "Mine", "Minion"])
            is_indirect_from_supports = False
            
            if main_skill_setup:
                gems = main_skill_setup.get('gems', [])
                for gem in gems:
                    gem_name = gem.get('name', '')
                    gem_tags = self._get_skill_tags(gem_name)
                    if any(tag in gem_tags for tag in ["Totem", "Trap", "Mine", "Minion"]):
                        is_indirect_from_supports = True
                        break
            
            # Only add self_cast score if it's not indirect
            if not is_indirect_from_main and not is_indirect_from_supports:
                delivery_scores["self_cast"] = delivery_scores.get("self_cast", 0) + 4  # Slightly higher than main skill base score
        
        # Check for skill mechanics from gems in main setup
        if main_skill_setup:
            gems = main_skill_setup.get('gems', [])
            mechanics = []
            
            for gem in gems:
                gem_name = gem.get('name', '')
                gem_tags = self._get_skill_tags(gem_name)
                
                if "Channelling" in gem_tags:
                    mechanics.append("channelling")
                if "AoE" in gem_tags:
                    mechanics.append("aoe")
                if "Projectile" in gem_tags:
                    mechanics.append("projectile")
                if "Duration" in gem_tags:
                    mechanics.append("duration")
            
            categories.skill_mechanics = list(set(mechanics))
        
        # Determine primary delivery method
        if delivery_scores:
            categories.skill_delivery = max(delivery_scores.items(), key=lambda x: x[1])[0]
            categories.confidence_scores['skill_delivery'] = min(1.0, max(delivery_scores.values()) / 5.0)
        else:
            categories.confidence_scores['skill_delivery'] = 0.0
    
    def _categorize_defense_style(self, categories: BuildCategories, character_data: Dict[str, Any],
                                unique_items: List[str], life: int, energy_shield: int, level: int) -> None:
        """Determine defensive style and layers using EHP calculator"""
        defense_layers = []
        defensive_score = 0
        
        # Analyze unique items for defensive properties
        for item in unique_items or []:
            for defense_type, items in self.defensive_uniques.items():
                if any(def_item.lower() in item.lower() for def_item in items):
                    if defense_type not in defense_layers:
                        defense_layers.append(defense_type)
                    defensive_score += 2
        
        # Create DefensiveStats from character data
        defensive_stats = DefensiveStats(
            life=life,
            energy_shield=energy_shield,
            armour=character_data.get('armour', 0),
            physical_damage_reduction=character_data.get('physical_damage_reduction', 0),
            fire_resistance=character_data.get('fire_resistance', 0),
            cold_resistance=character_data.get('cold_resistance', 0),
            lightning_resistance=character_data.get('lightning_resistance', 0),
            chaos_resistance=character_data.get('chaos_resistance', 0),
            max_fire_resistance=character_data.get('max_fire_resistance', 75),
            max_cold_resistance=character_data.get('max_cold_resistance', 75),
            max_lightning_resistance=character_data.get('max_lightning_resistance', 75),
            max_chaos_resistance=character_data.get('max_chaos_resistance', 75),
            block_chance=character_data.get('block_chance', 0),
            spell_block_chance=character_data.get('spell_block_chance', 0),
            evasion=character_data.get('evasion', 0),
            fortify=character_data.get('fortify', False),
            endurance_charges=character_data.get('endurance_charges', 0)
        )
        
        # Calculate EHP
        ehp_result = ehp_calculator.calculate_ehp(defensive_stats)
        categories.ehp_result = ehp_result
        
        # Get tankiness rating based on EHP
        tankiness_rating = ehp_calculator.get_ehp_rating(ehp_result, level)
        categories.tankiness_rating = tankiness_rating
        
        # Map tankiness rating to defense style
        if tankiness_rating in ["Extremely Tanky", "Very Tanky"]:
            categories.defense_style = "tanky"
            defensive_score += 3
        elif tankiness_rating in ["Tanky", "Balanced"]:
            categories.defense_style = "balanced"
            defensive_score += 1
        else:  # "Squishy", "Very Squishy"
            categories.defense_style = "squishy"
        
        # Adjust for defensive layers
        if len(defense_layers) >= 3:
            if categories.defense_style == "squishy":
                categories.defense_style = "balanced"
            defensive_score += 2
        elif len(defense_layers) >= 2:
            if categories.defense_style == "squishy":
                categories.defense_style = "balanced"
            defensive_score += 1
        
        categories.defense_layers = defense_layers
        categories.confidence_scores['defense'] = min(1.0, defensive_score / 8.0)
    
    def _categorize_cost_tier(self, categories: BuildCategories, unique_items: List[str],
                            main_skill_setup: Dict) -> None:
        """Determine build cost tier based on required items"""
        cost_factors = []
        cost_score = 0
        
        # Analyze unique items for cost indicators
        for item in unique_items or []:
            for cost_tier, items in self.expensive_uniques.items():
                if any(expensive_item.lower() in item.lower() for expensive_item in items):
                    cost_factors.append(f"{cost_tier}_unique")
                    if cost_tier == "luxury":
                        cost_score += 5
                    elif cost_tier == "expensive":
                        cost_score += 3
                    elif cost_tier == "moderate":
                        cost_score += 1
        
        # Check for 6-link requirement
        if main_skill_setup:
            gems = main_skill_setup.get('gems', [])
            links = main_skill_setup.get('links', 0)
            if links >= 6 or len(gems) >= 6:
                cost_factors.append("6_link")
                cost_score += 2
            elif links >= 5 or len(gems) >= 5:
                cost_factors.append("5_link")
                cost_score += 1
        
        # Determine cost tier
        if cost_score >= 8:
            categories.cost_tier = "luxury"
        elif cost_score >= 4:
            categories.cost_tier = "expensive"
        elif cost_score >= 2:
            categories.cost_tier = "moderate"
        else:
            categories.cost_tier = "budget"
        
        categories.cost_factors = cost_factors
        categories.confidence_scores['cost'] = min(1.0, cost_score / 10.0)
    
    def _calculate_confidence_scores(self, categories: BuildCategories, character_data: Dict) -> None:
        """Calculate overall confidence scores for categorizations"""
        # Overall confidence based on data completeness
        data_completeness = 0
        if character_data.get('main_skill'):
            data_completeness += 0.3
        if character_data.get('enhanced_skills') or character_data.get('skills'):
            data_completeness += 0.3
        if character_data.get('enhanced_uniques') or character_data.get('unique_items'):
            data_completeness += 0.2
        if character_data.get('main_skill_setup'):
            data_completeness += 0.2
        
        categories.confidence_scores['overall'] = data_completeness
    
    def categorize_builds_batch(self, characters_data: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], BuildCategories]]:
        """
        Categorize multiple builds in batch
        
        Args:
            characters_data: List of character data dictionaries
            
        Returns:
            List of tuples (character_data, categories)
        """
        results = []
        for char_data in characters_data:
            try:
                categories = self.categorize_build(char_data)
                results.append((char_data, categories))
            except Exception as e:
                logger.error(f"Error categorizing build {char_data.get('name', 'unknown')}: {e}")
                results.append((char_data, BuildCategories()))
        
        return results
    
    def get_build_summary(self, categories: BuildCategories) -> str:
        """Generate a human-readable summary of build categorization"""
        parts = []
        
        if categories.primary_damage_type:
            damage_desc = categories.primary_damage_type.title()
            if categories.damage_over_time:
                damage_desc += " DoT"
            if categories.secondary_damage_types:
                damage_desc += f" + {'/'.join(categories.secondary_damage_types).title()}"
            parts.append(damage_desc)
        
        if categories.skill_delivery:
            delivery_desc = categories.skill_delivery.replace("_", " ").title()
            if categories.skill_mechanics:
                mechanics = ", ".join(categories.skill_mechanics).title()
                delivery_desc += f" ({mechanics})"
            parts.append(delivery_desc)
        
        if categories.tankiness_rating:
            # Use the EHP-based tankiness rating
            parts.append(categories.tankiness_rating)
            if categories.defense_layers:
                layers = ", ".join(categories.defense_layers).replace("_", " ").title()
                parts.append(f"({layers})")
        elif categories.defense_style:
            # Fallback to old style if no EHP rating
            defense_desc = categories.defense_style.title()
            if categories.defense_layers:
                layers = ", ".join(categories.defense_layers).replace("_", " ").title()
                defense_desc += f" ({layers})"
            parts.append(defense_desc)
        
        if categories.cost_tier:
            parts.append(f"{categories.cost_tier.title()} Cost")
        
        # Add EHP if available
        if categories.ehp_result:
            ehp_desc = f"EHP: {int(categories.ehp_result.weighted_ehp):,}"
            parts.append(ehp_desc)
        
        return " | ".join(parts) if parts else "Uncategorized Build"


# Global categorizer instance
build_categorizer = BuildCategorizer()