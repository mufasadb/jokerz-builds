#!/usr/bin/env python3
"""
Backfill script to add profile_url and ladder_url to existing characters
"""

import sys
from urllib.parse import quote
from src.storage.database import DatabaseManager, Character

def backfill_character_urls():
    """Add profile and ladder URLs to existing characters that don't have them"""
    
    db = DatabaseManager()
    session = db.get_session()
    
    try:
        # Get characters that don't have profile URLs
        characters = session.query(Character).filter(
            Character.profile_url.is_(None)
        ).all()
        
        print(f"Found {len(characters)} characters without URLs")
        
        updated_count = 0
        for char in characters:
            if char.account and char.name:
                # Generate profile URL
                char.profile_url = f"https://www.pathofexile.com/account/view-profile/{quote(char.account)}/characters?characterName={quote(char.name)}"
                
                # Generate ladder URL based on league
                if char.league:
                    char.ladder_url = f"https://www.pathofexile.com/ladders/league/{quote(char.league)}"
                
                updated_count += 1
                
                if updated_count % 100 == 0:
                    print(f"Updated {updated_count} characters...")
        
        session.commit()
        print(f"✅ Successfully updated URLs for {updated_count} characters")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error updating character URLs: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    print("=" * 60)
    print("BACKFILLING CHARACTER URLs")
    print("=" * 60)
    
    try:
        backfill_character_urls()
        print("✅ Backfill completed successfully!")
    except Exception as e:
        print(f"❌ Backfill failed: {e}")
        sys.exit(1)