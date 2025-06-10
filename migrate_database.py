#!/usr/bin/env python3
"""
Database migration script to add missing columns for build categorization and EHP calculations
"""

import sqlite3
import sys
from datetime import datetime

def migrate_database(db_path):
    """Add missing columns to the characters table"""
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"Migrating database: {db_path}")
    print(f"Started at: {datetime.now()}")
    
    # Check if task_states table exists, create if not
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='task_states'")
    if not cursor.fetchone():
        print("Creating task_states table...")
        cursor.execute("""
            CREATE TABLE task_states (
                id INTEGER NOT NULL,
                task_id VARCHAR(100) NOT NULL,
                status VARCHAR(20) NOT NULL,
                created_at DATETIME,
                started_at DATETIME,
                completed_at DATETIME,
                leagues JSON,
                enhance_profiles BOOLEAN DEFAULT 1,
                categorize_builds BOOLEAN DEFAULT 1,
                collection_mode VARCHAR(20) DEFAULT 'balanced',
                current_step VARCHAR(200) DEFAULT '',
                total_steps INTEGER DEFAULT 0,
                completed_steps INTEGER DEFAULT 0,
                current_league VARCHAR(50) DEFAULT '',
                current_operation VARCHAR(100) DEFAULT '',
                characters_collected INTEGER DEFAULT 0,
                characters_enhanced INTEGER DEFAULT 0,
                characters_categorized INTEGER DEFAULT 0,
                leagues_completed JSON,
                error_message VARCHAR(1000),
                warnings JSON,
                last_heartbeat DATETIME,
                PRIMARY KEY (id)
            )
        """)
        cursor.execute("CREATE UNIQUE INDEX ix_task_states_task_id ON task_states (task_id)")
        print("✅ task_states table created")
    else:
        print("task_states table already exists")
    
    # List of columns to add with their SQL definitions for characters table
    new_columns = [
        # Build categorization data
        ("primary_damage_type", "VARCHAR(50)"),
        ("secondary_damage_types", "JSON"),
        ("damage_over_time", "BOOLEAN DEFAULT 0"),
        
        ("skill_delivery", "VARCHAR(50)"),
        ("skill_mechanics", "JSON"),
        
        ("defense_style", "VARCHAR(50)"),
        ("defense_layers", "JSON"),
        
        ("cost_tier", "VARCHAR(50)"),
        ("cost_factors", "JSON"),
        
        # Defensive stats for EHP calculation
        ("armour", "INTEGER"),
        ("evasion", "INTEGER"),
        ("fire_resistance", "REAL"),
        ("cold_resistance", "REAL"),
        ("lightning_resistance", "REAL"),
        ("chaos_resistance", "REAL"),
        ("block_chance", "REAL"),
        ("spell_block_chance", "REAL"),
        
        # EHP metrics
        ("ehp_physical", "REAL"),
        ("ehp_fire", "REAL"),
        ("ehp_cold", "REAL"),
        ("ehp_lightning", "REAL"),
        ("ehp_chaos", "REAL"),
        ("ehp_weighted", "REAL"),
        ("tankiness_rating", "VARCHAR(50)"),
        
        # Categorization metadata
        ("categorization_confidence", "JSON"),
        ("categorized_at", "DATETIME"),
        
        # URL references for build viewing
        ("profile_url", "VARCHAR(500)"),
        ("pob_url", "VARCHAR(500)"),
        ("ladder_url", "VARCHAR(500)"),
    ]
    
    # Check which columns already exist
    cursor.execute("PRAGMA table_info(characters)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    
    columns_added = 0
    
    # Add missing columns
    for column_name, column_type in new_columns:
        if column_name not in existing_columns:
            try:
                sql = f"ALTER TABLE characters ADD COLUMN {column_name} {column_type}"
                print(f"Adding column: {column_name}")
                cursor.execute(sql)
                columns_added += 1
            except sqlite3.Error as e:
                print(f"Error adding column {column_name}: {e}")
        else:
            print(f"Column {column_name} already exists, skipping")
    
    # Create indexes for the new indexed columns
    indexes_to_create = [
        ("ix_characters_primary_damage_type", "primary_damage_type"),
        ("ix_characters_skill_delivery", "skill_delivery"),
        ("ix_characters_defense_style", "defense_style"),
        ("ix_characters_cost_tier", "cost_tier"),
        ("ix_characters_tankiness_rating", "tankiness_rating"),
    ]
    
    indexes_added = 0
    
    for index_name, column_name in indexes_to_create:
        if column_name in [col[0] for col in new_columns]:
            try:
                # Check if column was actually added (exists now)
                cursor.execute("PRAGMA table_info(characters)")
                current_columns = {row[1] for row in cursor.fetchall()}
                
                if column_name in current_columns:
                    # Check if index already exists
                    cursor.execute("PRAGMA index_list(characters)")
                    existing_indexes = {row[1] for row in cursor.fetchall()}
                    
                    if index_name not in existing_indexes:
                        sql = f"CREATE INDEX {index_name} ON characters ({column_name})"
                        print(f"Creating index: {index_name}")
                        cursor.execute(sql)
                        indexes_added += 1
                    else:
                        print(f"Index {index_name} already exists, skipping")
                        
            except sqlite3.Error as e:
                print(f"Error creating index {index_name}: {e}")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"\nMigration completed:")
    print(f"- {columns_added} columns added")
    print(f"- {indexes_added} indexes created")
    print(f"Finished at: {datetime.now()}")
    
    return columns_added > 0 or indexes_added > 0

if __name__ == "__main__":
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "data/ladder_snapshots.db"
    
    print("=" * 60)
    print("DATABASE MIGRATION SCRIPT")
    print("=" * 60)
    
    try:
        success = migrate_database(db_path)
        if success:
            print("✅ Migration completed successfully!")
        else:
            print("ℹ️ No migration needed - database already up to date")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)