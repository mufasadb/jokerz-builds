# Build Query System Guide

This guide explains how to query builds from the database and stored data to find specific build types like fire-based tanky builds that are budget-friendly.

## Overview

The build query system provides multiple ways to search for builds:

1. **Database Queries** (when data is categorized) - Fast queries using SQL
2. **JSON File Analysis** (fallback) - Real-time categorization of stored build data
3. **Build Categorization** - Automatic analysis of damage types, defense styles, and costs

## Key Files

### Core Query System
- `/Users/danielbeach/Code/joker-builds/query_fire_tanky_builds.py` - Main query system
- `/Users/danielbeach/Code/joker-builds/test_query_system.py` - Test and example usage

### Database Layer
- `/Users/danielbeach/Code/joker-builds/src/storage/database.py` - Database models and queries
- `/Users/danielbeach/Code/joker-builds/src/storage/data_manager.py` - JSON data management
- `/Users/danielbeach/Code/joker-builds/src/storage/data_explorer.py` - Data exploration utilities

### Analysis System
- `/Users/danielbeach/Code/joker-builds/src/analysis/build_categorizer.py` - Build categorization logic
- `/Users/danielbeach/Code/joker-builds/src/data/skill_tags.py` - Skill tag analysis

## Data Structure

### Database Schema
The `characters` table contains:
- Basic info: `name`, `account`, `level`, `class_name`, `ascendancy`
- Stats: `life`, `energy_shield`, `dps`
- Skills: `main_skill`, `skills` (JSON), `unique_items` (JSON)
- Enhanced data: `enhanced_skills`, `enhanced_uniques`, `main_skill_setup`
- Categorization fields (when populated):
  - `primary_damage_type`: fire, cold, lightning, physical, chaos
  - `defense_style`: tanky, balanced, squishy
  - `cost_tier`: budget, moderate, expensive, luxury
  - `skill_delivery`: melee, self_cast, totem, minion, etc.

### JSON Data Files
Located in `/Users/danielbeach/Code/joker-builds/data/builds/`:
- Format: `{league}_{snapshot}.json`
- Examples: `standard_current.json`, `testleague_week-1.json`

## Usage Examples

### Basic Usage

```python
from query_fire_tanky_builds import BuildQuerySystem

# Initialize the query system
query_system = BuildQuerySystem()

# Find fire-based tanky budget builds
fire_tanky_budget = query_system.find_fire_tanky_budget_builds(limit=10)

# Find all fire builds
fire_builds = query_system.find_builds_by_damage_type("fire", limit=20)

# Find all tanky builds
tanky_builds = query_system.find_tanky_builds(limit=20)

# Find all budget builds
budget_builds = query_system.find_budget_builds(limit=20)
```

### Advanced Queries

```python
# Get popularity statistics
stats = query_system.get_build_popularity_stats()
print(f"Damage types: {stats['damage_types']}")
print(f"Defense styles: {stats['defense_styles']}")
print(f"Cost tiers: {stats['cost_tiers']}")

# Search specific league
league_builds = query_system.find_tanky_builds(league="Standard", limit=15)

# Print formatted results
query_system.print_build_results(fire_builds, "Fire Damage Builds")
```

### Database Queries (when categorized)

```python
from src.storage.database import DatabaseManager

db = DatabaseManager("sqlite:///data/ladder_snapshots.db")

# Direct database search (requires categorized data)
results = db.search_builds_by_category(
    damage_type="fire",
    defense_style="tanky", 
    cost_tier="budget",
    league="Standard",
    limit=50
)
```

## Build Categorization System

The system automatically categorizes builds based on:

### Damage Types
- **Fire**: Skills with Fire damage tags
- **Cold**: Skills with Cold damage tags  
- **Lightning**: Skills with Lightning damage tags
- **Physical**: Skills with Physical damage tags
- **Chaos**: Skills with Chaos damage tags

### Defense Styles
- **Tanky**: High life/ES per level (>80), defensive uniques (Kaom's Heart, etc.)
- **Balanced**: Moderate life/ES per level (50-80)
- **Squishy**: Low life/ES per level (<50)

### Cost Tiers
- **Budget**: Common/cheap uniques, basic gear
- **Moderate**: Some expensive items, 5-links
- **Expensive**: Multiple expensive uniques, 6-links
- **Luxury**: Mirror-tier items, Mageblood, etc.

### Skill Delivery
- **Melee**: Direct melee attacks
- **Self Cast**: Direct spell casting
- **Totem**: Totem-supported skills
- **Minion**: Minion-based builds
- **Bow**: Bow attacks
- **Trap/Mine**: Trap or mine skills

## Data Sources

### Current Data Available
- **Standard League**: 20 characters with Lightning Strike, Boneshatter, Arc, etc.
- **Test Leagues**: Additional test data
- **Demo Leagues**: Sample data for testing

### Sample Build Types Found
- **Lightning Tanky Builds**: Lightning Strike Deadeye, Arc Elementalist
- **Physical Tanky Builds**: Boneshatter Juggernaut  
- **Budget Tanky Builds**: Various Arc and Blade Flurry builds

## Performance Notes

1. **Database Queries**: Fast when data is pre-categorized
2. **JSON Analysis**: Slower but works with any stored data
3. **Real-time Categorization**: Analyzes builds on-the-fly using skill tags and items
4. **Caching**: Results can be cached for better performance

## Running the Examples

```bash
# Run the main demo
python query_fire_tanky_builds.py

# Run tests
python test_query_system.py

# Run existing analysis examples
python example_analysis.py
python example_tag_analysis.py
```

## Extending the System

### Adding New Categories
Edit `/Users/danielbeach/Code/joker-builds/src/analysis/build_categorizer.py`:
- Add new damage types to `damage_types` dict
- Add new defensive items to `defensive_uniques` dict
- Add new expensive items to `expensive_uniques` dict

### Custom Query Functions
Add new methods to `BuildQuerySystem` class in `query_fire_tanky_builds.py`:

```python
def find_dot_builds(self, league: str = None, limit: int = 50):
    """Find damage over time builds"""
    return self._analyze_builds_by_criteria(
        lambda cats: cats.damage_over_time == True,
        league, limit
    )
```

### Database Population
To populate the database with categorized data:

```python
from src.storage.database import DatabaseManager
from src.analysis.build_categorizer import build_categorizer

db = DatabaseManager()
characters = db.get_characters_for_categorization(limit=1000)

for char_data in characters:
    categories = build_categorizer.categorize_build(char_data)
    db.update_character_categorization(char_data['id'], categories)
```

## Summary

The build query system provides a comprehensive way to:
1. **Search** for builds by damage type, defense style, and cost
2. **Analyze** build popularity and meta trends  
3. **Categorize** builds automatically using skill and item analysis
4. **Scale** from JSON files to full database queries

The system works with your existing data structure and can be extended for more specific queries as needed.