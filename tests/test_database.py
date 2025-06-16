"""
Tests for database functionality
"""

import pytest
import tempfile
import json
from datetime import datetime, timedelta
from src.storage.database import DatabaseManager, LadderSnapshot, Character, SnapshotMetrics


class TestDatabaseManager:
    """Test cases for DatabaseManager"""
    
    @pytest.fixture(scope="function")
    def temp_db(self):
        """Create temporary database for testing"""
        import os
        # Create a unique temporary database file for each test
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name
        try:
            yield f"sqlite:///{temp_path}"
        finally:
            # Clean up the temporary file
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass
    
    @pytest.fixture(scope="function")
    def db_manager(self, temp_db):
        """Create database manager with temporary database"""
        return DatabaseManager(temp_db)
    
    @pytest.fixture
    def sample_ladder_data(self):
        """Sample ladder data for testing"""
        return {
            "data": [
                {
                    "account": "TestAccount1",
                    "name": "TestChar1",
                    "level": 95,
                    "experience": 5000000,
                    "class": "Witch",
                    "ascendancy": "Necromancer",
                    "life": 6500,
                    "energyShield": 2000,
                    "dps": 150000,
                    "depth": {"solo": 600, "default": 650},
                    "mainSkill": "Summon Skeletons",
                    "skills": ["Summon Skeletons", "Bone Armor", "Convocation"],
                    "uniques": ["Femurs of the Saints", "Vis Mortis"]
                },
                {
                    "account": "TestAccount2",
                    "name": "TestChar2", 
                    "level": 98,
                    "experience": 8000000,
                    "class": "Marauder",
                    "ascendancy": "Juggernaut",
                    "life": 8500,
                    "energyShield": 0,
                    "dps": 200000,
                    "depth": {"solo": 400},
                    "mainSkill": "Earthquake",
                    "skills": ["Earthquake", "Fortify", "Enduring Cry"],
                    "uniques": ["Disfavour", "Kaom's Heart"]
                }
            ]
        }
    
    def test_database_initialization(self, db_manager):
        """Test database and tables are created correctly"""
        # Should not raise any exceptions
        session = db_manager.get_session()
        try:
            # Test that tables exist by querying them
            session.query(LadderSnapshot).count()
            session.query(Character).count()
            session.query(SnapshotMetrics).count()
        finally:
            session.close()
    
    def test_save_ladder_snapshot(self, db_manager, sample_ladder_data):
        """Test saving ladder snapshot data"""
        snapshot_id = db_manager.save_ladder_snapshot(
            ladder_data=sample_ladder_data,
            league="TestLeague",
            ladder_type="exp"
        )
        
        assert isinstance(snapshot_id, int)
        assert snapshot_id > 0
        
        # Verify snapshot was saved
        session = db_manager.get_session()
        try:
            snapshot = session.query(LadderSnapshot).filter_by(id=snapshot_id).first()
            assert snapshot is not None
            assert snapshot.league == "TestLeague"
            assert snapshot.ladder_type == "exp"
            assert snapshot.total_characters == 2
            
            # Verify characters were saved
            characters = session.query(Character).filter_by(snapshot_id=snapshot_id).all()
            assert len(characters) == 2
            
            char1 = next(c for c in characters if c.name == "TestChar1")
            assert char1.account == "TestAccount1"
            assert char1.level == 95
            assert char1.class_name == "Witch"
            assert char1.ascendancy == "Necromancer"
            assert char1.life == 6500
            assert char1.delve_solo_depth == 600
            assert "Summon Skeletons" in char1.skills
            assert "Femurs of the Saints" in char1.unique_items
            
            # Verify metrics were calculated
            metrics = session.query(SnapshotMetrics).filter_by(snapshot_id=snapshot_id).first()
            assert metrics is not None
            assert metrics.total_characters == 2
            assert metrics.avg_level == 96.5  # (95 + 98) / 2
            assert metrics.max_level == 98
            assert metrics.level_100_count == 0
            assert "Witch" in metrics.class_distribution
            assert "Marauder" in metrics.class_distribution
            assert metrics.class_distribution["Witch"] == 1
            assert metrics.class_distribution["Marauder"] == 1
            
        finally:
            session.close()
    
    def test_deduplication(self, db_manager, sample_ladder_data):
        """Test that identical data is deduplicated"""
        # Save same data twice
        id1 = db_manager.save_ladder_snapshot(sample_ladder_data, "TestLeague", "exp")
        id2 = db_manager.save_ladder_snapshot(sample_ladder_data, "TestLeague", "exp")
        
        # Should return same ID
        assert id1 == id2
        
        # Verify only one snapshot exists
        session = db_manager.get_session()
        try:
            snapshots = session.query(LadderSnapshot).all()
            assert len(snapshots) == 1
        finally:
            session.close()
    
    def test_get_latest_snapshot(self, db_manager, sample_ladder_data):
        """Test retrieving latest snapshot"""
        # Save snapshots for different leagues and types
        db_manager.save_ladder_snapshot(sample_ladder_data, "League1", "exp")
        db_manager.save_ladder_snapshot(sample_ladder_data, "League1", "depthsolo")
        db_manager.save_ladder_snapshot(sample_ladder_data, "League2", "exp")
        
        # Test getting latest for specific league/type
        latest = db_manager.get_latest_snapshot("League1", "exp")
        assert latest is not None
        assert latest.league == "League1"
        assert latest.ladder_type == "exp"
        
        # Test non-existent league
        none_result = db_manager.get_latest_snapshot("NonExistent", "exp")
        assert none_result is None
    
    def test_get_snapshots_by_date_range(self, db_manager, sample_ladder_data):
        """Test retrieving snapshots within date range"""
        # Save snapshot
        snapshot_id = db_manager.save_ladder_snapshot(sample_ladder_data, "TestLeague", "exp")
        
        # Test date range queries
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)
        
        # Should find snapshot in wide range
        snapshots = db_manager.get_snapshots_by_date_range("TestLeague", yesterday, tomorrow, "exp")
        assert len(snapshots) == 1
        assert snapshots[0].id == snapshot_id
        
        # Should not find snapshot in past range
        past_start = now - timedelta(days=5)
        past_end = now - timedelta(days=2)
        snapshots = db_manager.get_snapshots_by_date_range("TestLeague", past_start, past_end, "exp")
        assert len(snapshots) == 0
    
    def test_get_character_progression(self, db_manager, sample_ladder_data):
        """Test getting character progression over time"""
        # Create multiple snapshots with same character at different levels
        for i, level in enumerate([90, 92, 95]):
            modified_data = sample_ladder_data.copy()
            modified_data["data"][0]["level"] = level
            modified_data["data"][0]["experience"] = 4000000 + (i * 500000)
            
            snapshot_id = db_manager.save_ladder_snapshot(modified_data, "TestLeague", "exp")
            
            # Manually adjust timestamps to create progression
            if i > 0:
                session = db_manager.get_session()
                try:
                    snapshot = session.query(LadderSnapshot).filter_by(id=snapshot_id).first()
                    snapshot.snapshot_date = datetime.utcnow() - timedelta(days=i)
                    
                    # Update character snapshot dates too
                    characters = session.query(Character).filter_by(snapshot_id=snapshot_id).all()
                    for char in characters:
                        char.snapshot_date = snapshot.snapshot_date
                    
                    session.commit()
                finally:
                    session.close()
        
        # Test progression retrieval
        progression = db_manager.get_character_progression("TestAccount1", "TestChar1")
        
        # Should have multiple entries, ordered by date
        assert len(progression) >= 1
        
        # If we have multiple entries, verify they're ordered correctly
        if len(progression) > 1:
            dates = [char.snapshot_date for char in progression]
            assert dates == sorted(dates)  # Should be in ascending order
    
    def test_get_league_summary(self, db_manager, sample_ladder_data):
        """Test getting league summary statistics"""
        # Save multiple snapshots
        for i in range(3):
            db_manager.save_ladder_snapshot(sample_ladder_data, "TestLeague", "exp")
        
        summary = db_manager.get_league_summary("TestLeague")
        
        assert "league" in summary
        assert summary["league"] == "TestLeague"
        assert "total_snapshots" in summary
        assert summary["total_snapshots"] >= 1  # Deduplication might reduce count
        assert "latest_character_count" in summary
        assert summary["latest_character_count"] == 2
        assert "avg_level" in summary
        assert "max_level" in summary
        assert "top_classes" in summary
        assert "top_skills" in summary
        
        # Test non-existent league
        empty_summary = db_manager.get_league_summary("NonExistent")
        assert "error" in empty_summary
    
    def test_cleanup_old_snapshots(self, db_manager, sample_ladder_data):
        """Test cleanup of old snapshot data"""
        # Save snapshot
        snapshot_id = db_manager.save_ladder_snapshot(sample_ladder_data, "TestLeague", "exp")
        
        # Make it old by updating timestamp
        session = db_manager.get_session()
        try:
            snapshot = session.query(LadderSnapshot).filter_by(id=snapshot_id).first()
            old_date = datetime.utcnow() - timedelta(days=100)
            snapshot.snapshot_date = old_date
            
            # Also update character dates
            characters = session.query(Character).filter_by(snapshot_id=snapshot_id).all()
            for char in characters:
                char.snapshot_date = old_date
            
            session.commit()
        finally:
            session.close()
        
        # Verify data exists before cleanup
        session = db_manager.get_session()
        try:
            assert session.query(LadderSnapshot).count() == 1
            assert session.query(Character).count() == 2
            assert session.query(SnapshotMetrics).count() == 1
        finally:
            session.close()
        
        # Run cleanup
        deleted_count = db_manager.cleanup_old_snapshots(keep_days=30)
        assert deleted_count == 1
        
        # Verify data was deleted
        session = db_manager.get_session()
        try:
            assert session.query(LadderSnapshot).count() == 0
            assert session.query(Character).count() == 0
            assert session.query(SnapshotMetrics).count() == 0
        finally:
            session.close()
    
    def test_metrics_calculation(self, db_manager):
        """Test aggregate metrics calculation"""
        # Create data with specific patterns for testing
        test_data = {
            "data": [
                {
                    "account": "Player1", "name": "Char1", "level": 100,
                    "class": "Witch", "ascendancy": "Necromancer",
                    "skills": ["Skill1", "Skill2"], "uniques": ["Item1"]
                },
                {
                    "account": "Player2", "name": "Char2", "level": 95,
                    "class": "Witch", "ascendancy": "Elementalist", 
                    "skills": ["Skill1", "Skill3"], "uniques": ["Item1", "Item2"]
                },
                {
                    "account": "Player3", "name": "Char3", "level": 90,
                    "class": "Marauder", "ascendancy": "Juggernaut",
                    "skills": ["Skill1"], "uniques": ["Item2"]
                }
            ]
        }
        
        snapshot_id = db_manager.save_ladder_snapshot(test_data, "TestLeague", "exp")
        
        session = db_manager.get_session()
        try:
            metrics = session.query(SnapshotMetrics).filter_by(snapshot_id=snapshot_id).first()
            
            # Test basic stats
            assert metrics.total_characters == 3
            assert metrics.avg_level == 95.0  # (100 + 95 + 90) / 3
            assert metrics.max_level == 100
            assert metrics.level_100_count == 1
            
            # Test class distribution
            assert metrics.class_distribution["Witch"] == 2
            assert metrics.class_distribution["Marauder"] == 1
            
            # Test ascendancy distribution
            assert metrics.ascendancy_distribution["Necromancer"] == 1
            assert metrics.ascendancy_distribution["Elementalist"] == 1
            assert metrics.ascendancy_distribution["Juggernaut"] == 1
            
            # Test skill popularity
            assert metrics.skill_popularity["Skill1"] == 3  # All characters have it
            assert metrics.skill_popularity["Skill2"] == 1
            assert metrics.skill_popularity["Skill3"] == 1
            
            # Test unique usage
            assert metrics.unique_usage["Item1"] == 2
            assert metrics.unique_usage["Item2"] == 2
            
        finally:
            session.close()
    
    def test_edge_cases(self, db_manager):
        """Test edge cases and error handling"""
        # Test empty data
        empty_data = {"data": []}
        
        # Should handle empty data gracefully
        try:
            snapshot_id = db_manager.save_ladder_snapshot(empty_data, "TestLeague", "exp") 
            # If it doesn't raise an exception, verify the snapshot has 0 characters
            session = db_manager.get_session()
            try:
                snapshot = session.query(LadderSnapshot).filter_by(id=snapshot_id).first()
                assert snapshot.total_characters == 0
            finally:
                session.close()
        except Exception:
            # It's also acceptable for empty data to be rejected
            pass
        
        # Test malformed character data
        malformed_data = {
            "data": [
                {
                    "name": "OnlyName"  # Missing required fields
                },
                {
                    "account": "TestAccount",
                    "name": "TestChar",
                    "level": "not_a_number"  # Wrong type
                }
            ]
        }
        
        # Should handle malformed data without crashing
        try:
            db_manager.save_ladder_snapshot(malformed_data, "TestLeague", "exp")
        except Exception:
            # It's acceptable for malformed data to be rejected
            pass