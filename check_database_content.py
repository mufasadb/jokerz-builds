#!/usr/bin/env python3
"""Quick script to check what's in your database"""

import sys
from src.storage.database import DatabaseManager
from datetime import datetime, timedelta
from sqlalchemy import func

def check_database(db_path=None):
    """Check database content"""
    print("=" * 60)
    print("DATABASE CONTENT CHECK")
    print("=" * 60)
    
    # Initialize database
    db = DatabaseManager(database_url=f"sqlite:///{db_path}" if db_path else None)
    
    # Get session
    session = db.get_session()
    
    try:
        # Check ladder snapshots
        from src.storage.database import LadderSnapshot
        snapshots = session.query(LadderSnapshot).order_by(LadderSnapshot.created_at.desc()).limit(5).all()
        
        print(f"\nLATEST SNAPSHOTS: {len(snapshots)} found")
        for snap in snapshots:
            time_ago = datetime.utcnow() - snap.created_at
            hours_ago = time_ago.total_seconds() / 3600
            print(f"  - {snap.league}: {snap.total_characters} chars, {hours_ago:.1f} hours ago")
        
        # Check total characters
        from src.storage.database import Character
        total_chars = session.query(Character).count()
        print(f"\nTOTAL CHARACTERS: {total_chars:,}")
        
        # Characters by league
        chars_by_league = session.query(
            Character.league, 
            func.count(Character.id)
        ).group_by(Character.league).all()
        
        if chars_by_league:
            print("\nCHARACTERS BY LEAGUE:")
            for league, count in chars_by_league:
                print(f"  - {league}: {count:,}")
        
        # Check request logs
        from src.storage.database import RequestLog
        total_requests = session.query(RequestLog).count()
        recent_requests = session.query(RequestLog).filter(
            RequestLog.timestamp >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        print(f"\nREQUEST LOGS:")
        print(f"  - Total: {total_requests:,}")
        print(f"  - Last 24h: {recent_requests:,}")
        
        # Check if any characters have been enhanced
        enhanced_chars = session.query(Character).filter(
            Character.enhanced_skills.isnot(None)
        ).count()
        
        categorized_chars = session.query(Character).filter(
            Character.primary_damage_type.isnot(None)
        ).count()
        
        print(f"\nDATA QUALITY:")
        print(f"  - Enhanced (with items): {enhanced_chars:,}")
        print(f"  - Categorized (with build type): {categorized_chars:,}")
        
    finally:
        session.close()
    
    print("\n" + "=" * 60)
    print("To see data in your dashboard:")
    print("1. Your local test database is EMPTY")
    print("2. The data is on your UNRAID server at:")
    print("   /mnt/user/appdata/joker-builds/data/ladder_snapshots.db")
    print("3. To see data locally, either:")
    print("   - Copy the database from Unraid")
    print("   - Run a collection locally")
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_database(sys.argv[1])
    else:
        check_database()