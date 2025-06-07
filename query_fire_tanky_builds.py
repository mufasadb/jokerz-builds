#!/usr/bin/env python3
"""
Query system for finding fire-based tanky builds that are budget-friendly.

This script demonstrates how to:
1. Query builds from the database
2. Use the build categorization system
3. Filter for specific criteria (fire damage, tanky defense, budget cost)
4. Find popular builds matching these criteria
"""

import logging
from typing import List, Dict, Any, Optional
from src.storage.database import DatabaseManager
from src.analysis.build_categorizer import build_categorizer, BuildCategories
from src.storage.data_manager import DataManager
from src.storage.data_explorer import DataExplorer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BuildQuerySystem:
    """System for querying and filtering builds based on criteria"""
    
    def __init__(self, db_path: str = None):
        """Initialize the query system"""
        if db_path is None:
            db_path = "sqlite:///data/ladder_snapshots.db"
        self.db_manager = DatabaseManager(db_path)
        self.data_manager = DataManager()
        self.data_explorer = DataExplorer()
    
    def find_fire_tanky_budget_builds(self, league: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Find fire-based tanky builds that are budget-friendly
        
        Args:
            league: Specific league to search in (None for all leagues)
            limit: Maximum number of results to return
            
        Returns:
            List of builds matching the criteria
        """
        logger.info("Searching for fire tanky budget builds...")
        
        # Method 1: Query from database if data is categorized
        categorized_builds = self._query_categorized_builds(
            damage_type="fire",
            defense_style="tanky", 
            cost_tier="budget",
            league=league,
            limit=limit
        )
        
        if categorized_builds:
            logger.info(f"Found {len(categorized_builds)} categorized builds")
            return categorized_builds
        
        # Method 2: Load from JSON files and categorize on-the-fly
        logger.info("No categorized data found, analyzing JSON data...")
        return self._analyze_json_builds(league, limit)
    
    def _query_categorized_builds(self, damage_type: str, defense_style: str, 
                                cost_tier: str, league: str = None, 
                                limit: int = 50) -> List[Dict[str, Any]]:
        """Query builds that have already been categorized in the database"""
        try:
            results = self.db_manager.search_builds_by_category(
                damage_type=damage_type,
                defense_style=defense_style,
                cost_tier=cost_tier,
                league=league,
                limit=limit
            )
            return results
        except Exception as e:
            logger.warning(f"Could not query categorized builds: {e}")
            return []
    
    def _analyze_json_builds(self, league: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Analyze builds from JSON files and categorize them"""
        results = []
        
        # Get available leagues from stored data
        available_files = self.data_manager.list_saved_builds(league)
        
        if not available_files:
            logger.warning("No build data files found")
            return results
        
        for file_info in available_files:
            if league and file_info['league'] != league.lower():
                continue
                
            logger.info(f"Analyzing builds from {file_info['filename']}")
            
            # Load build data
            build_overview = self.data_explorer.load_and_analyze_builds(
                file_info['league'], 
                file_info['snapshot']
            )
            
            if not build_overview:
                continue
            
            # Analyze each character
            for character in build_overview.characters:
                if len(results) >= limit:
                    break
                    
                # Convert to format expected by categorizer
                char_data = {
                    'account': character.account,
                    'name': character.name,
                    'level': character.level,
                    'class': character.class_name,
                    'ascendancy': character.ascendancy,
                    'life': character.life,
                    'energy_shield': character.energy_shield,
                    'dps': character.dps,
                    'main_skill': character.main_skill,
                    'skills': character.skills,
                    'unique_items': character.unique_items,
                    'league': character.league,
                    'rank': character.rank
                }
                
                # Categorize the build
                categories = build_categorizer.categorize_build(char_data)
                
                # Check if it matches our criteria
                if self._matches_criteria(categories, "fire", "tanky", "budget"):
                    build_summary = build_categorizer.get_build_summary(categories)
                    
                    results.append({
                        'character_name': character.name,
                        'account': character.account,
                        'level': character.level,
                        'class': character.class_name,
                        'ascendancy': character.ascendancy,
                        'rank': character.rank,
                        'league': character.league,
                        'main_skill': character.main_skill,
                        'life': character.life,
                        'energy_shield': character.energy_shield,
                        'dps': character.dps,
                        'build_summary': build_summary,
                        'categories': {
                            'damage_type': categories.primary_damage_type,
                            'skill_delivery': categories.skill_delivery,
                            'defense_style': categories.defense_style,
                            'cost_tier': categories.cost_tier,
                            'damage_over_time': categories.damage_over_time,
                            'defense_layers': categories.defense_layers,
                            'cost_factors': categories.cost_factors
                        },
                        'unique_items': character.unique_items,
                        'skills': character.skills,
                        'confidence_scores': categories.confidence_scores
                    })
            
            if len(results) >= limit:
                break
        
        return results
    
    def _matches_criteria(self, categories: BuildCategories, damage_type: str, 
                         defense_style: str, cost_tier: str) -> bool:
        """Check if build categories match our search criteria"""
        return (
            categories.primary_damage_type == damage_type and
            categories.defense_style == defense_style and
            categories.cost_tier == cost_tier
        )
    
    def find_builds_by_damage_type(self, damage_type: str, league: str = None, 
                                 limit: int = 50) -> List[Dict[str, Any]]:
        """Find builds by primary damage type"""
        logger.info(f"Searching for {damage_type} damage builds...")
        
        # Try categorized database first
        categorized = self.db_manager.search_builds_by_category(
            damage_type=damage_type,
            league=league,
            limit=limit
        )
        
        if categorized:
            return categorized
        
        # Fall back to JSON analysis
        return self._analyze_builds_by_criteria(
            lambda cats: cats.primary_damage_type == damage_type,
            league, limit
        )
    
    def find_tanky_builds(self, league: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Find tanky/defensive builds"""
        logger.info("Searching for tanky builds...")
        
        return self._analyze_builds_by_criteria(
            lambda cats: cats.defense_style == "tanky",
            league, limit
        )
    
    def find_budget_builds(self, league: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Find budget-friendly builds"""
        logger.info("Searching for budget builds...")
        
        return self._analyze_builds_by_criteria(
            lambda cats: cats.cost_tier == "budget",
            league, limit
        )
    
    def _analyze_builds_by_criteria(self, criteria_func, league: str = None, 
                                  limit: int = 50) -> List[Dict[str, Any]]:
        """Generic method to analyze builds by custom criteria function"""
        results = []
        available_files = self.data_manager.list_saved_builds(league)
        
        for file_info in available_files[:3]:  # Limit to first 3 files for performance
            build_overview = self.data_explorer.load_and_analyze_builds(
                file_info['league'], 
                file_info['snapshot']
            )
            
            if not build_overview:
                continue
            
            for character in build_overview.characters:
                if len(results) >= limit:
                    break
                
                char_data = {
                    'account': character.account,
                    'name': character.name,
                    'level': character.level,
                    'class': character.class_name,
                    'ascendancy': character.ascendancy,
                    'life': character.life,
                    'energy_shield': character.energy_shield,
                    'dps': character.dps,
                    'main_skill': character.main_skill,
                    'skills': character.skills,
                    'unique_items': character.unique_items,
                    'league': character.league,
                    'rank': character.rank
                }
                
                categories = build_categorizer.categorize_build(char_data)
                
                if criteria_func(categories):
                    build_summary = build_categorizer.get_build_summary(categories)
                    
                    results.append({
                        'character_name': character.name,
                        'account': character.account,
                        'level': character.level,
                        'class': character.class_name,
                        'ascendancy': character.ascendancy,
                        'rank': character.rank,
                        'league': character.league,
                        'main_skill': character.main_skill,
                        'life': character.life,
                        'energy_shield': character.energy_shield,
                        'build_summary': build_summary,
                        'categories': {
                            'damage_type': categories.primary_damage_type,
                            'defense_style': categories.defense_style,
                            'cost_tier': categories.cost_tier
                        }
                    })
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_build_popularity_stats(self, league: str = None) -> Dict[str, Any]:
        """Get popularity statistics for different build categories"""
        logger.info("Analyzing build popularity statistics...")
        
        stats = {
            'damage_types': {},
            'defense_styles': {},
            'cost_tiers': {},
            'skill_deliveries': {},
            'total_analyzed': 0
        }
        
        available_files = self.data_manager.list_saved_builds(league)
        
        for file_info in available_files[:2]:  # Analyze recent files
            build_overview = self.data_explorer.load_and_analyze_builds(
                file_info['league'], 
                file_info['snapshot']
            )
            
            if not build_overview:
                continue
            
            for character in build_overview.characters:
                char_data = {
                    'account': character.account,
                    'name': character.name,
                    'level': character.level,
                    'class': character.class_name,
                    'ascendancy': character.ascendancy,
                    'life': character.life,
                    'energy_shield': character.energy_shield,
                    'main_skill': character.main_skill,
                    'skills': character.skills,
                    'unique_items': character.unique_items,
                }
                
                categories = build_categorizer.categorize_build(char_data)
                stats['total_analyzed'] += 1
                
                # Count damage types
                if categories.primary_damage_type:
                    stats['damage_types'][categories.primary_damage_type] = \
                        stats['damage_types'].get(categories.primary_damage_type, 0) + 1
                
                # Count defense styles
                if categories.defense_style:
                    stats['defense_styles'][categories.defense_style] = \
                        stats['defense_styles'].get(categories.defense_style, 0) + 1
                
                # Count cost tiers
                if categories.cost_tier:
                    stats['cost_tiers'][categories.cost_tier] = \
                        stats['cost_tiers'].get(categories.cost_tier, 0) + 1
                
                # Count skill deliveries
                if categories.skill_delivery:
                    stats['skill_deliveries'][categories.skill_delivery] = \
                        stats['skill_deliveries'].get(categories.skill_delivery, 0) + 1
        
        return stats
    
    def print_build_results(self, builds: List[Dict[str, Any]], title: str = "Build Results"):
        """Print build results in a formatted way"""
        print(f"\n{'=' * 80}")
        print(f"{title.upper()}")
        print(f"{'=' * 80}")
        print(f"Found {len(builds)} matching builds:\n")
        
        for i, build in enumerate(builds, 1):
            print(f"{i}. {build['character_name']} ({build['account']})")
            print(f"   Class: {build['class']} ({build.get('ascendancy', 'N/A')})")
            print(f"   Level: {build['level']} | Rank: {build.get('rank', 'N/A')}")
            print(f"   League: {build['league']}")
            print(f"   Main Skill: {build.get('main_skill', 'Unknown')}")
            
            if 'life' in build and build['life']:
                life_es = f"Life: {build['life']}"
                if build.get('energy_shield'):
                    life_es += f" | ES: {build['energy_shield']}"
                print(f"   {life_es}")
            
            if 'build_summary' in build:
                print(f"   Build Type: {build['build_summary']}")
            
            if 'categories' in build:
                cats = build['categories']
                print(f"   Categories: {cats.get('damage_type', 'Unknown')} | "
                      f"{cats.get('defense_style', 'Unknown')} | "
                      f"{cats.get('cost_tier', 'Unknown')}")
            
            if 'unique_items' in build and build['unique_items']:
                items = ', '.join(build['unique_items'][:3])
                if len(build['unique_items']) > 3:
                    items += "..."
                print(f"   Key Items: {items}")
            
            print()


def main():
    """Demonstrate the build query system"""
    query_system = BuildQuerySystem()
    
    print("Build Query System Demo")
    print("=" * 50)
    
    # 1. Find fire-based tanky budget builds
    fire_tanky_budget = query_system.find_fire_tanky_budget_builds(limit=10)
    query_system.print_build_results(fire_tanky_budget, "Fire Tanky Budget Builds")
    
    # 2. Find all fire builds
    fire_builds = query_system.find_builds_by_damage_type("fire", limit=15)
    query_system.print_build_results(fire_builds, "Fire Damage Builds")
    
    # 3. Find all tanky builds
    tanky_builds = query_system.find_tanky_builds(limit=15)
    query_system.print_build_results(tanky_builds, "Tanky Builds")
    
    # 4. Find all budget builds
    budget_builds = query_system.find_budget_builds(limit=15)
    query_system.print_build_results(budget_builds, "Budget Builds")
    
    # 5. Show popularity statistics
    stats = query_system.get_build_popularity_stats()
    
    print(f"\n{'=' * 80}")
    print("BUILD POPULARITY STATISTICS")
    print(f"{'=' * 80}")
    print(f"Total builds analyzed: {stats['total_analyzed']}\n")
    
    print("Damage Type Distribution:")
    for damage_type, count in sorted(stats['damage_types'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / stats['total_analyzed'] * 100) if stats['total_analyzed'] > 0 else 0
        print(f"  {damage_type}: {count} ({percentage:.1f}%)")
    
    print("\nDefense Style Distribution:")
    for defense_style, count in sorted(stats['defense_styles'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / stats['total_analyzed'] * 100) if stats['total_analyzed'] > 0 else 0
        print(f"  {defense_style}: {count} ({percentage:.1f}%)")
    
    print("\nCost Tier Distribution:")
    for cost_tier, count in sorted(stats['cost_tiers'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / stats['total_analyzed'] * 100) if stats['total_analyzed'] > 0 else 0
        print(f"  {cost_tier}: {count} ({percentage:.1f}%)")


if __name__ == "__main__":
    main()