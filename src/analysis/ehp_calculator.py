"""
Effective Health Pool (EHP) calculator for Path of Exile characters.

This module calculates realistic effective health considering damage mitigation from:
- Armour (physical damage reduction)
- Elemental/Chaos resistances
- Block chance
- Evasion (probabilistic)

Based on standard damage scenarios used by PoB and PoE Ninja.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import math

logger = logging.getLogger(__name__)


@dataclass
class DefensiveStats:
    """Container for all defensive statistics"""
    # Raw HP pools
    life: int = 0
    energy_shield: int = 0
    
    # Physical mitigation
    armour: int = 0
    physical_damage_reduction: float = 0.0  # From other sources
    
    # Resistances (as percentages, e.g., 75.0 for 75%)
    fire_resistance: float = 0.0
    cold_resistance: float = 0.0
    lightning_resistance: float = 0.0
    chaos_resistance: float = 0.0
    
    # Maximum resistances
    max_fire_resistance: float = 75.0
    max_cold_resistance: float = 75.0
    max_lightning_resistance: float = 75.0
    max_chaos_resistance: float = 75.0
    
    # Probabilistic defenses
    block_chance: float = 0.0
    spell_block_chance: float = 0.0
    evasion: int = 0
    enemy_accuracy: int = 1000  # Standard enemy accuracy for calculations
    
    # Other mitigation
    fortify: bool = False
    endurance_charges: int = 0


@dataclass
class EHPResult:
    """Results from EHP calculation"""
    # Basic HP
    total_hp: int = 0
    
    # EHP against specific damage types
    physical_ehp: float = 0.0
    fire_ehp: float = 0.0
    cold_ehp: float = 0.0
    lightning_ehp: float = 0.0
    chaos_ehp: float = 0.0
    
    # Averaged/weighted EHP
    average_ehp: float = 0.0
    weighted_ehp: float = 0.0
    
    # Damage reduction percentages (for standard hits)
    physical_reduction: float = 0.0
    fire_reduction: float = 0.0
    cold_reduction: float = 0.0
    lightning_reduction: float = 0.0
    chaos_reduction: float = 0.0
    
    # Defensive analysis
    mitigation_breakdown: Dict[str, float] = field(default_factory=dict)
    calculation_notes: List[str] = field(default_factory=list)


class EHPCalculator:
    """Calculate effective health pool using standard PoE damage scenarios"""
    
    def __init__(self):
        # Standard damage amounts for testing
        self.standard_physical_hit = 1000
        self.standard_elemental_hit = 1000
        self.standard_chaos_hit = 1000
        
        # Damage type weights for endgame content (estimated)
        self.damage_weights = {
            'physical': 0.25,
            'fire': 0.20,
            'cold': 0.15,
            'lightning': 0.15,
            'chaos': 0.25
        }
        
        # Fortify provides 20% less damage taken
        self.fortify_reduction = 0.20
        
        # Endurance charges provide 4% physical reduction each
        self.endurance_charge_reduction = 0.04
    
    def calculate_ehp(self, defensive_stats: DefensiveStats) -> EHPResult:
        """
        Calculate EHP against various damage types
        
        Args:
            defensive_stats: All defensive statistics for the character
            
        Returns:
            EHPResult with breakdown of EHP against different damage types
        """
        result = EHPResult()
        
        # Basic HP pool
        result.total_hp = defensive_stats.life + defensive_stats.energy_shield
        
        if result.total_hp == 0:
            return result  # Can't have EHP with 0 HP
        
        # Calculate EHP for each damage type
        result.physical_ehp, result.physical_reduction = self._calculate_physical_ehp(
            defensive_stats, result.total_hp
        )
        
        result.fire_ehp, result.fire_reduction = self._calculate_elemental_ehp(
            defensive_stats, result.total_hp, 'fire'
        )
        
        result.cold_ehp, result.cold_reduction = self._calculate_elemental_ehp(
            defensive_stats, result.total_hp, 'cold'
        )
        
        result.lightning_ehp, result.lightning_reduction = self._calculate_elemental_ehp(
            defensive_stats, result.total_hp, 'lightning'
        )
        
        result.chaos_ehp, result.chaos_reduction = self._calculate_chaos_ehp(
            defensive_stats, result.total_hp
        )
        
        # Calculate averaged EHP
        result.average_ehp = (
            result.physical_ehp + result.fire_ehp + result.cold_ehp + 
            result.lightning_ehp + result.chaos_ehp
        ) / 5
        
        # Calculate weighted EHP
        result.weighted_ehp = (
            result.physical_ehp * self.damage_weights['physical'] +
            result.fire_ehp * self.damage_weights['fire'] +
            result.cold_ehp * self.damage_weights['cold'] +
            result.lightning_ehp * self.damage_weights['lightning'] +
            result.chaos_ehp * self.damage_weights['chaos']
        )
        
        # Add calculation breakdown
        result.mitigation_breakdown = {
            'armour_vs_1k': result.physical_reduction,
            'fire_resistance': result.fire_reduction,
            'cold_resistance': result.cold_reduction,
            'lightning_resistance': result.lightning_reduction,
            'chaos_resistance': result.chaos_reduction
        }
        
        # Add calculation notes
        result.calculation_notes = [
            f"Based on {self.standard_physical_hit} physical damage standard hit",
            f"Based on {self.standard_elemental_hit} elemental damage standard hits",
            f"Resistances capped at maximum values",
            f"Block chance provides average damage reduction"
        ]
        
        return result
    
    def _calculate_physical_ehp(self, stats: DefensiveStats, base_hp: int) -> Tuple[float, float]:
        """Calculate EHP against physical damage"""
        # Armour reduction using PoE formula
        armour_reduction = stats.armour / (stats.armour + 10 * self.standard_physical_hit)
        
        # Additional physical damage reduction
        other_phys_reduction = stats.physical_damage_reduction / 100
        
        # Endurance charges
        endurance_reduction = min(stats.endurance_charges * self.endurance_charge_reduction, 1.0)
        
        # Fortify
        fortify_reduction = self.fortify_reduction if stats.fortify else 0.0
        
        # Block chance (average reduction)
        block_reduction = stats.block_chance / 100
        
        # Combine all reductions (multiplicatively for most, additively for some)
        # Armour + other physical reduction are additive (capped at 90%)
        total_phys_reduction = min(armour_reduction + other_phys_reduction + endurance_reduction, 0.90)
        
        # Fortify and block are multiplicative
        damage_multiplier = (1 - total_phys_reduction) * (1 - fortify_reduction) * (1 - block_reduction)
        
        ehp = base_hp / damage_multiplier if damage_multiplier > 0 else float('inf')
        total_reduction = 1 - damage_multiplier
        
        return ehp, total_reduction
    
    def _calculate_elemental_ehp(self, stats: DefensiveStats, base_hp: int, element: str) -> Tuple[float, float]:
        """Calculate EHP against elemental damage (fire, cold, lightning)"""
        # Get resistance and max resistance for the element
        if element == 'fire':
            resistance = min(stats.fire_resistance, stats.max_fire_resistance)
        elif element == 'cold':
            resistance = min(stats.cold_resistance, stats.max_cold_resistance)
        elif element == 'lightning':
            resistance = min(stats.lightning_resistance, stats.max_lightning_resistance)
        else:
            resistance = 0.0
        
        # Resistance reduction
        resistance_reduction = resistance / 100
        
        # Fortify (applies to all damage)
        fortify_reduction = self.fortify_reduction if stats.fortify else 0.0
        
        # Spell block for elemental spells (approximation)
        block_reduction = stats.spell_block_chance / 100
        
        # Combine reductions
        damage_multiplier = (1 - resistance_reduction) * (1 - fortify_reduction) * (1 - block_reduction)
        
        ehp = base_hp / damage_multiplier if damage_multiplier > 0 else float('inf')
        total_reduction = 1 - damage_multiplier
        
        return ehp, total_reduction
    
    def _calculate_chaos_ehp(self, stats: DefensiveStats, base_hp: int) -> Tuple[float, float]:
        """Calculate EHP against chaos damage"""
        # Chaos resistance (can go negative)
        resistance = min(stats.chaos_resistance, stats.max_chaos_resistance)
        resistance_reduction = resistance / 100
        
        # Fortify
        fortify_reduction = self.fortify_reduction if stats.fortify else 0.0
        
        # Spell block (most chaos damage is spells)
        block_reduction = stats.spell_block_chance / 100
        
        # Combine reductions
        damage_multiplier = (1 - resistance_reduction) * (1 - fortify_reduction) * (1 - block_reduction)
        
        ehp = base_hp / damage_multiplier if damage_multiplier > 0 else float('inf')
        total_reduction = 1 - damage_multiplier
        
        return ehp, total_reduction
    
    def calculate_evasion_ehp(self, stats: DefensiveStats, base_hp: int) -> Tuple[float, float]:
        """
        Calculate EHP considering evasion (separate because it's probabilistic)
        
        This is more complex because evasion doesn't provide consistent damage reduction
        """
        if stats.evasion == 0:
            return base_hp, 0.0
        
        # Calculate hit chance using PoE formula
        hit_chance = stats.enemy_accuracy / (stats.enemy_accuracy + stats.evasion)
        
        # Average damage multiplier
        average_damage_multiplier = hit_chance
        
        # EHP based on average hits
        evasion_ehp = base_hp / average_damage_multiplier if average_damage_multiplier > 0 else float('inf')
        evasion_reduction = 1 - average_damage_multiplier
        
        return evasion_ehp, evasion_reduction
    
    def get_ehp_rating(self, ehp_result: EHPResult, character_level: int = 90) -> str:
        """
        Provide a qualitative rating of EHP for the character level
        
        Args:
            ehp_result: Results from EHP calculation
            character_level: Character level for scaling expectations
            
        Returns:
            String rating like "Very Tanky", "Balanced", "Squishy"
        """
        # Use weighted EHP as the primary metric
        ehp = ehp_result.weighted_ehp
        
        # Level-scaled EHP expectations (rough guidelines)
        if character_level >= 90:
            # Endgame expectations
            if ehp >= 15000:
                return "Extremely Tanky"
            elif ehp >= 10000:
                return "Very Tanky"
            elif ehp >= 7000:
                return "Tanky"
            elif ehp >= 5000:
                return "Balanced"
            elif ehp >= 3000:
                return "Squishy"
            else:
                return "Very Squishy"
        else:
            # Scale down expectations for lower levels
            scale_factor = character_level / 90
            if ehp >= 15000 * scale_factor:
                return "Extremely Tanky"
            elif ehp >= 10000 * scale_factor:
                return "Very Tanky"
            elif ehp >= 7000 * scale_factor:
                return "Tanky"
            elif ehp >= 5000 * scale_factor:
                return "Balanced"
            elif ehp >= 3000 * scale_factor:
                return "Squishy"
            else:
                return "Very Squishy"


# Global calculator instance
ehp_calculator = EHPCalculator()