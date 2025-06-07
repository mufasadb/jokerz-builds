"""
Configurable timing profiles for different collection strategies
"""

TIMING_PROFILES = {
    "conservative_fast": {
        "description": "Conservative limits with fast collection (2 hours)",
        "duration_hours": 2,
        "ladder_delay": 4.0,
        "character_delay": 8.0,
        "use_case": "Testing or urgent data needs"
    },
    
    "balanced_extended": {
        "description": "Balanced approach with extended timing (8 hours)", 
        "duration_hours": 8,
        "ladder_delay": 15.0,
        "character_delay": 20.0,
        "use_case": "Recommended for daily production use"
    },
    
    "stealth_mode": {
        "description": "Maximum stealth with very slow collection (16 hours)",
        "duration_hours": 16, 
        "ladder_delay": 30.0,
        "character_delay": 45.0,
        "use_case": "Maximum server respect and sustainability"
    },
    
    "maintenance_safe": {
        "description": "Safe collection avoiding peak hours (12 hours)",
        "duration_hours": 12,
        "ladder_delay": 20.0, 
        "character_delay": 30.0,
        "use_case": "During league launches or high server load"
    }
}

def get_timing_config(profile_name: str = "balanced_extended"):
    """Get timing configuration for a specific profile"""
    return TIMING_PROFILES.get(profile_name, TIMING_PROFILES["balanced_extended"])

def calculate_collection_time(profile_name: str, ladder_calls: int = 72, character_calls: int = 800):
    """Calculate actual collection time for a profile"""
    config = get_timing_config(profile_name)
    
    ladder_time_hours = (ladder_calls * config["ladder_delay"]) / 3600
    character_time_hours = (character_calls * config["character_delay"]) / 3600
    total_time = ladder_time_hours + character_time_hours
    
    return {
        "profile": profile_name,
        "ladder_time_hours": ladder_time_hours,
        "character_time_hours": character_time_hours, 
        "total_time_hours": total_time,
        "planned_duration": config["duration_hours"],
        "buffer_hours": config["duration_hours"] - total_time,
        "description": config["description"]
    }

if __name__ == "__main__":
    print("📅 Available Timing Profiles:")
    print("=" * 40)
    
    for name, profile in TIMING_PROFILES.items():
        result = calculate_collection_time(name)
        print(f"\n{name.upper()}:")
        print(f"  {profile['description']}")
        print(f"  Duration: {result['total_time_hours']:.1f}h actual / {result['planned_duration']}h planned")
        print(f"  Buffer: {result['buffer_hours']:.1f} hours")
        print(f"  Delays: {profile['ladder_delay']}s ladder, {profile['character_delay']}s character")
        print(f"  Use case: {profile['use_case']}")