# Health Data (Life & Energy Shield) Pipeline Trace

## Overview
This document traces how health-related data (Life and Energy Shield) flows through the PoE build tracking system from API collection to storage and analysis.

## Data Flow Pipeline

### 1. **API Data Collection**

#### A. Primary Source: PoE Official Ladder API (`poe_ladder_client.py`)
- **Endpoint**: `https://www.pathofexile.com/api/ladders/{league_id}`
- **Raw Data Format**: The official ladder API returns basic character information including:
  ```json
  {
    "rank": 1,
    "character": {
      "name": "CharacterName",
      "level": 100,
      "class": "Ascendant",
      "experience": 4250334444
    },
    "account": {
      "name": "AccountName#1234"
    }
  }
  ```
- **Note**: The official ladder API does NOT include health/ES data directly

#### B. Secondary Source: PoE Character API (`poe_character_api.py`)
- **Endpoint**: `https://www.pathofexile.com/character-window/get-items`
- **Purpose**: Fetches detailed character equipment and stats for public profiles
- **Data Available**: Equipment, gems, sockets - but NOT aggregated health/ES totals
- **Rate Limited**: Uses centralized rate limiter to avoid hitting API limits

### 2. **Data Models** (`build_models.py`)

The `Character` dataclass includes fields for health stats:
```python
@dataclass
class Character:
    # Basic info
    account: str
    name: str
    level: int
    class_name: str
    
    # Build details - these are the health-related fields
    life: Optional[int] = None
    energy_shield: Optional[int] = None
    dps: Optional[float] = None
```

### 3. **Data Transformation** (`ladder_scraper.py`)

In the `_convert_ladder_data` method:
```python
char_data = {
    "account": account.get("name", ""),
    "name": character.get("name", ""),
    "level": character.get("level", 0),
    "life": char_data.get('life'),  # Expecting this from raw data
    "energy_shield": char_data.get('energyShield'),  # Expecting this from raw data
    # ... other fields
}
```

**Important Discovery**: The code expects `life` and `energyShield` fields in the raw API data, but based on the sample JSON files, these fields are NOT provided by the official PoE ladder API.

### 4. **Database Storage** (`database.py`)

The `Character` table schema includes:
```python
class Character(Base):
    __tablename__ = 'characters'
    
    # Combat stats columns
    life = Column(Integer, nullable=True)
    energy_shield = Column(Integer, nullable=True)
    dps = Column(Integer, nullable=True)
```

When saving to database in `save_ladder_snapshot`:
```python
character = Character(
    life=char_data.get('life'),
    energy_shield=char_data.get('energyShield'),
    dps=char_data.get('dps'),
    # ... other fields
)
```

### 5. **Current State Analysis**

#### What's Missing:
1. **No Health Data from Official API**: The PoE official ladder API doesn't provide life/ES values
2. **Character Window API Limitation**: While the character items API provides equipment data, it doesn't give aggregated stats
3. **PoE Ninja Disconnected**: The `poe_ninja_client.py` has been refactored to only handle items/currency, not builds

#### Where Health Data Should Come From:
Previously, PoE Ninja's build API would have provided this data, as they calculate/aggregate these stats from character data. The current codebase has remnants expecting this data but no active collection mechanism.

## Recommendations

### Option 1: Re-integrate PoE Ninja Build API
- PoE Ninja calculates life/ES from character passive trees and equipment
- Would need to restore build-related methods in `poe_ninja_client.py`
- Their API provides aggregated stats like life, ES, DPS

### Option 2: Calculate from Character Data
- Fetch full character passive tree data using `get_character_passives`
- Fetch all equipment data
- Calculate life/ES based on:
  - Base life from level
  - Life from passive tree nodes
  - Life/ES from equipment modifiers
  - Percentage increases from tree/equipment
- This is complex and requires game knowledge databases

### Option 3: Accept Limited Data
- Continue without health/ES data
- Focus on other metrics like level, experience, skills
- Update analysis tools to work without these stats

## Current Data Enhancement Flow

The system does have a character enhancement mechanism:
1. `_enhance_characters_with_profiles` in `ladder_scraper.py`
2. Fetches additional data for top characters
3. Updates with skills, uniques, and build information
4. But still doesn't calculate or fetch health/ES totals

## Conclusion

The health data pipeline is currently **incomplete**. The code expects life/ES data that isn't provided by the current API sources. To properly track health data, the system needs either:
1. Integration with PoE Ninja's build API
2. Complex calculation logic based on full character data
3. A different data source that provides these aggregated stats

## Additional Findings

### Test Data Shows Expected Format
The demo/test files (`demoleague_current.json`) show the expected data format includes:
```json
{
  "life": 5000,
  "energyShield": 2000,
  ...
}
```

### Historical Context
- Comment in `poe_ninja_client.py`: "BUILD METHODS REMOVED - Use PoeLadderClient for character/ladder data"
- This suggests the project previously used PoE Ninja's build API which would have provided these stats
- The refactoring removed this functionality but the database schema and models still expect this data

### Current Impact
1. Database columns for `life` and `energy_shield` exist but remain NULL for real data
2. Build categorization system (`build_categorizer.py`) can analyze defense styles but lacks actual health values
3. Query systems expect these fields but work around their absence