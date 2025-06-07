# Effective Health Pool (EHP) Calculation Research

## Overview
EHP represents how much raw damage a character can theoretically take before dying, accounting for damage mitigation from various defensive mechanics.

## Standard EHP Calculation Approaches

### 1. **Basic Formula Structure**
```
EHP = (Life + ES) / (1 - Total Damage Reduction)
```

Where Total Damage Reduction is the combined effect of all mitigation sources.

### 2. **Common "Standard Hit" Scenarios**

Most PoE tools use standardized damage scenarios for EHP calculations:

**Physical Damage Standard:**
- 1000 physical damage hit (most common)
- Sometimes 5000 for endgame scenarios
- Used to test armour effectiveness

**Elemental Damage Standard:**
- 1000 fire/cold/lightning damage
- Tests resistance effectiveness
- Often averaged across all three elements

**Chaos Damage Standard:**
- 1000 chaos damage
- Tests chaos resistance

### 3. **Damage Mitigation Sources**

#### A. **Armour (Physical Damage Reduction)**
```
Damage Reduction % = Armour / (Armour + 10 * Damage)
```

For a 1000 damage hit:
- 5000 armour = 33.3% reduction
- 10000 armour = 50% reduction  
- 20000 armour = 66.7% reduction

#### B. **Resistances (Elemental/Chaos)**
```
Damage Reduction % = Resistance% (capped at 75-90% depending on max res)
```

Standard caps:
- 75% base maximum resistance
- Can be increased via passive tree/items
- Overcapped resistance provides no benefit until penetration

#### C. **Block Chance**
```
Average Damage Reduction = Block Chance% * (1 - Block Recovery%)
```

Note: Block is probabilistic, not guaranteed reduction

#### D. **Evasion**
```
Hit Chance = Accuracy / (Accuracy + Evasion)
Average Damage Reduction = 1 - Hit Chance
```

Note: Also probabilistic, not guaranteed

#### E. **Dodge (Legacy)**
```
Average Damage Reduction = Dodge Chance%
```

### 4. **Multi-Layer Mitigation**

When combining multiple sources:
```
Effective Damage = Base Damage * (1 - Armour%) * (1 - Resistance%) * Hit Chance * (1 - Block Chance)
```

## Common EHP Calculation Methods

### Method 1: **Single Damage Type EHP**
Calculate EHP against one specific damage type:

```python
def calculate_physical_ehp(life, es, armour, block_chance=0):
    base_hp = life + es
    standard_hit = 1000
    
    # Armour reduction
    armour_reduction = armour / (armour + 10 * standard_hit)
    
    # Block average reduction
    block_reduction = block_chance / 100
    
    # Combined reduction
    total_reduction = 1 - ((1 - armour_reduction) * (1 - block_reduction))
    
    return base_hp / (1 - total_reduction)
```

### Method 2: **Averaged EHP**
Average EHP across multiple damage types:

```python
def calculate_average_ehp(life, es, armour, fire_res, cold_res, lightning_res, chaos_res, block_chance=0):
    base_hp = life + es
    
    # Calculate EHP for each damage type
    phys_ehp = calculate_physical_ehp(life, es, armour, block_chance)
    fire_ehp = base_hp / (1 - (fire_res/100 + block_chance/100))
    # ... similar for other elements
    
    # Average across damage types
    return (phys_ehp + fire_ehp + cold_ehp + lightning_ehp + chaos_ehp) / 5
```

### Method 3: **Weighted EHP**
Weight damage types by frequency in endgame content:

```python
# Common endgame damage distribution (approximate)
DAMAGE_WEIGHTS = {
    'physical': 0.25,
    'fire': 0.20,
    'cold': 0.15,
    'lightning': 0.15,
    'chaos': 0.25
}
```

## Path of Building Approach (Estimated)

Based on community knowledge, PoB likely uses:

1. **Multiple Standard Hits**: Tests against various damage amounts
2. **Scenario-Based**: Different calculations for different content types
3. **Conservative Estimates**: Doesn't rely on probabilistic defenses for main EHP
4. **Separate Calculations**: Shows different EHP values for different damage types

## PoE Ninja Approach (Estimated)

PoE Ninja likely uses:

1. **Simplified Model**: Probably uses a single standard hit scenario
2. **Physical Focus**: May prioritize physical EHP for ladder ranking
3. **Resistance Averaging**: Likely averages elemental resistances
4. **Conservative Block/Evasion**: May not fully factor in probabilistic defenses

## Implementation Recommendations

### Phase 1: Basic EHP
Start with simple physical damage EHP:
```python
def basic_ehp(life, es, armour):
    base_hp = life + es
    standard_hit = 1000
    reduction = armour / (armour + 10 * standard_hit)
    return base_hp / (1 - reduction)
```

### Phase 2: Multi-Damage EHP
Add elemental damage calculations:
```python
def multi_damage_ehp(stats):
    # Calculate EHP for each damage type
    # Return dictionary with breakdown
    pass
```

### Phase 3: Advanced EHP
Add probabilistic defenses and complex scenarios:
```python
def advanced_ehp(stats, scenario='standard'):
    # Factor in block, evasion, dodge
    # Support different damage scenarios
    pass
```

## Testing Strategy

1. **Manual Verification**: Compare with known PoB calculations
2. **Community Builds**: Test against published builds with known EHP
3. **Edge Cases**: Test extreme values (0 armour, max resistance, etc.)
4. **Consistency Check**: Ensure results make logical sense

## Notes

- EHP is an approximation, not exact survivability
- Real combat involves burst damage, regeneration, flasks, etc.
- Different content requires different EHP calculations
- Some defenses (like fortify, endurance charges) add complexity
- Damage over time bypasses many defenses and needs separate calculation