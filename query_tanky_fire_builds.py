"""
Example query: Find tanky fire-based builds with high EHP
"""

from src.storage.database import DatabaseManager
import json


def find_tanky_fire_builds():
    """Find fire-based builds that are extremely tanky"""
    
    db = DatabaseManager()
    
    # Search for fire builds with high tankiness
    results = db.search_builds_by_category(
        damage_type='fire',
        tankiness_rating='Extremely Tanky',
        min_ehp=15000,  # Minimum 15k weighted EHP
        league='Standard',  # Or specify any league
        limit=10
    )
    
    if results:
        print(f"\nFound {len(results)} tanky fire builds:\n")
        
        for i, build in enumerate(results, 1):
            print(f"{i}. {build['character_name']} ({build['account']})")
            print(f"   Level: {build['level']} {build['class']}")
            print(f"   Rank: #{build['rank']}")
            print(f"   Main Skill: {build['main_skill']}")
            print(f"   Build: {build['build_summary']}")
            print(f"   Tankiness: {build['categories']['tankiness_rating']}")
            print(f"   Weighted EHP: {build['ehp']['weighted']:,.0f}")
            print(f"   Physical EHP: {build['ehp']['physical']:,.0f}")
            
            if build['unique_items']:
                print(f"   Key Uniques: {', '.join(build['unique_items'][:3])}")
            
            print()
    else:
        print("No tanky fire builds found matching criteria")


def find_ultra_tanks():
    """Find the tankiest builds regardless of damage type"""
    
    db = DatabaseManager()
    
    # Search for builds with extremely high EHP
    results = db.search_builds_by_category(
        tankiness_rating='Extremely Tanky',
        min_ehp=25000,  # Very high EHP threshold
        limit=10
    )
    
    if results:
        print(f"\nFound {len(results)} ultra-tanky builds:\n")
        
        # Sort by EHP for display
        results.sort(key=lambda x: x['ehp']['weighted'] or 0, reverse=True)
        
        for i, build in enumerate(results, 1):
            print(f"{i}. {build['character_name']} - {build['main_skill'] or 'Unknown'}")
            print(f"   Weighted EHP: {build['ehp']['weighted']:,.0f}")
            print(f"   Damage Type: {build['categories']['damage_type']}")
            print(f"   Skill Delivery: {build['categories']['skill_delivery']}")
            print(f"   Defense Layers: {', '.join(build['categories'].get('defense_layers', []))}")
            print()
    else:
        print("No ultra-tanky builds found")


def analyze_tankiness_distribution():
    """Analyze the distribution of tankiness ratings"""
    
    db = DatabaseManager()
    session = db.get_session()
    
    try:
        from src.storage.database import Character
        from sqlalchemy import func
        
        # Count builds by tankiness rating
        tankiness_counts = session.query(
            Character.tankiness_rating,
            func.count(Character.id).label('count')
        ).filter(
            Character.tankiness_rating.isnot(None)
        ).group_by(
            Character.tankiness_rating
        ).all()
        
        print("\nTankiness Distribution:")
        print("-" * 40)
        
        total = sum(count for _, count in tankiness_counts)
        
        for rating, count in sorted(tankiness_counts, key=lambda x: x[1], reverse=True):
            percentage = (count / total * 100) if total > 0 else 0
            print(f"{rating:20} {count:6} ({percentage:5.1f}%)")
        
        # Average EHP by tankiness rating
        print("\nAverage EHP by Tankiness Rating:")
        print("-" * 40)
        
        ehp_averages = session.query(
            Character.tankiness_rating,
            func.avg(Character.ehp_weighted).label('avg_ehp'),
            func.min(Character.ehp_weighted).label('min_ehp'),
            func.max(Character.ehp_weighted).label('max_ehp')
        ).filter(
            Character.tankiness_rating.isnot(None),
            Character.ehp_weighted.isnot(None)
        ).group_by(
            Character.tankiness_rating
        ).all()
        
        for rating, avg_ehp, min_ehp, max_ehp in ehp_averages:
            print(f"{rating:20} Avg: {avg_ehp:8,.0f} (Min: {min_ehp:,.0f}, Max: {max_ehp:,.0f})")
            
    finally:
        session.close()


if __name__ == "__main__":
    print("=== Tanky Fire Builds Query ===")
    find_tanky_fire_builds()
    
    print("\n\n=== Ultra Tank Builds Query ===")
    find_ultra_tanks()
    
    print("\n\n=== Tankiness Analysis ===")
    analyze_tankiness_distribution()