"""
Comprehensive tests for ladder scraper functionality
"""

import pytest
import json
import tempfile
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from src.scraper.ladder_scraper import LadderScraper
from src.storage.database import DatabaseManager, LadderSnapshot, Character


class TestLadderScraper:
    """Test cases for LadderScraper class"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_url = f"sqlite:///{f.name}"
            yield db_url
    
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
    
    @pytest.fixture
    def scraper(self, temp_db):
        """Create scraper instance with temporary database"""
        return LadderScraper(database_url=temp_db, backup_to_files=False)
    
    def test_scraper_initialization(self, temp_db):
        """Test scraper initializes correctly"""
        scraper = LadderScraper(database_url=temp_db)
        
        assert scraper.db is not None
        assert isinstance(scraper.leagues_to_monitor, list)
        assert "Standard" in scraper.leagues_to_monitor
        assert "exp" in scraper.ladder_types
    
    @patch('src.scraper.ladder_scraper.PoeNinjaClient')
    def test_collect_daily_snapshot_success(self, mock_client_class, scraper, sample_ladder_data):
        """Test successful snapshot collection"""
        # Mock the client
        mock_client = Mock()
        mock_client.get_build_overview.return_value = sample_ladder_data
        mock_client_class.return_value = mock_client
        
        # Test collection
        result = scraper.collect_daily_snapshot("TestLeague", "exp")
        
        assert result is True
        mock_client.get_build_overview.assert_called_once_with(overview_type="exp")
        
        # Verify data was saved to database
        session = scraper.db.get_session()
        try:
            snapshots = session.query(LadderSnapshot).all()
            assert len(snapshots) == 1
            assert snapshots[0].league == "TestLeague"
            assert snapshots[0].total_characters == 2
            
            characters = session.query(Character).all()
            assert len(characters) == 2
            assert characters[0].name == "TestChar1"
            assert characters[1].name == "TestChar2"
        finally:
            session.close()
    
    @patch('src.scraper.ladder_scraper.PoeNinjaClient')
    def test_collect_daily_snapshot_api_failure(self, mock_client_class, scraper):
        """Test handling of API failure"""
        # Mock client returning None (API failure)
        mock_client = Mock()
        mock_client.get_build_overview.return_value = None
        mock_client_class.return_value = mock_client
        
        # Test collection
        result = scraper.collect_daily_snapshot("TestLeague", "exp")
        
        assert result is False
    
    @patch('src.scraper.ladder_scraper.PoeNinjaClient')
    def test_collect_daily_snapshot_empty_data(self, mock_client_class, scraper):
        """Test handling of empty data response"""
        # Mock client returning empty data
        mock_client = Mock()
        mock_client.get_build_overview.return_value = {"data": []}
        mock_client_class.return_value = mock_client
        
        # Test collection
        result = scraper.collect_daily_snapshot("TestLeague", "exp")
        
        assert result is False
    
    def test_check_if_snapshot_needed_no_previous(self, scraper):
        """Test snapshot needed when no previous snapshot exists"""
        result = scraper.check_if_snapshot_needed("NewLeague", "exp")
        assert result is True
    
    def test_check_if_snapshot_needed_old_snapshot(self, scraper):
        """Test snapshot needed when previous snapshot is old"""
        # Create old snapshot
        old_data = {"data": [{"account": "test", "name": "test", "level": 90}]}
        scraper.db.save_ladder_snapshot(old_data, "TestLeague", "exp")
        
        # Manually update timestamp to make it old
        session = scraper.db.get_session()
        try:
            snapshot = session.query(LadderSnapshot).first()
            snapshot.snapshot_date = datetime.utcnow() - timedelta(hours=25)
            session.commit()
        finally:
            session.close()
        
        result = scraper.check_if_snapshot_needed("TestLeague", "exp")
        assert result is True
    
    def test_check_if_snapshot_needed_recent_snapshot(self, scraper):
        """Test snapshot not needed when recent snapshot exists"""
        # Create recent snapshot
        recent_data = {"data": [{"account": "test", "name": "test", "level": 90}]}
        scraper.db.save_ladder_snapshot(recent_data, "TestLeague", "exp")
        
        result = scraper.check_if_snapshot_needed("TestLeague", "exp")
        assert result is False
    
    def test_get_league_status(self, scraper, sample_ladder_data):
        """Test getting league status"""
        # Create snapshot
        scraper.db.save_ladder_snapshot(sample_ladder_data, "TestLeague", "exp")
        
        status = scraper.get_league_status("TestLeague")
        
        assert "total_snapshots" in status
        assert status["total_snapshots"] == 1
        assert "latest_character_count" in status
        assert status["latest_character_count"] == 2
        assert "hours_since_last_snapshot" in status
        assert status["is_fresh"] is True
    
    def test_get_character_tracking(self, scraper, sample_ladder_data):
        """Test character progression tracking"""
        # Create multiple snapshots for same character
        for i in range(3):
            modified_data = sample_ladder_data.copy()
            # Modify level to show progression
            modified_data["data"][0]["level"] = 90 + i
            modified_data["data"][0]["experience"] = 4000000 + (i * 500000)
            
            scraper.db.save_ladder_snapshot(modified_data, "TestLeague", "exp")
            
            # Update timestamp manually for different snapshots
            if i > 0:
                session = scraper.db.get_session()
                try:
                    snapshots = session.query(LadderSnapshot).all()
                    snapshots[i].snapshot_date = datetime.utcnow() - timedelta(days=i)
                    session.commit()
                finally:
                    session.close()
        
        # Test tracking
        progression = scraper.get_character_tracking("TestAccount1", "TestChar1")
        
        assert len(progression) >= 1  # Should have at least one entry
        assert all("level" in entry for entry in progression)
        assert all("date" in entry for entry in progression)
    
    def test_cleanup_old_data(self, scraper, sample_ladder_data):
        """Test cleanup of old snapshots"""
        # Create old snapshot
        scraper.db.save_ladder_snapshot(sample_ladder_data, "TestLeague", "exp")
        
        # Make it old
        session = scraper.db.get_session()
        try:
            snapshot = session.query(LadderSnapshot).first()
            snapshot.snapshot_date = datetime.utcnow() - timedelta(days=100)
            session.commit()
        finally:
            session.close()
        
        # Test cleanup
        deleted_count = scraper.cleanup_old_data(keep_days=30)
        
        assert deleted_count == 1
        
        # Verify snapshot was deleted
        session = scraper.db.get_session()
        try:
            snapshots = session.query(LadderSnapshot).all()
            assert len(snapshots) == 0
        finally:
            session.close()
    
    @patch('src.scraper.ladder_scraper.PoeNinjaClient')
    @patch('time.sleep')  # Mock sleep to speed up tests
    def test_collect_all_snapshots(self, mock_sleep, mock_client_class, scraper, sample_ladder_data):
        """Test collecting snapshots for all leagues"""
        # Mock client
        mock_client = Mock()
        mock_client.get_build_overview.return_value = sample_ladder_data
        mock_client_class.return_value = mock_client
        
        # Override leagues for testing
        scraper.leagues_to_monitor = ["League1", "League2"]
        scraper.ladder_types = ["exp"]
        
        results = scraper.collect_all_snapshots()
        
        # Should have results for both leagues
        assert "League1" in results
        assert "League2" in results
        assert results["League1"]["exp"] is True
        assert results["League2"]["exp"] is True
        
        # Verify database has snapshots for both leagues
        session = scraper.db.get_session()
        try:
            snapshots = session.query(LadderSnapshot).all()
            assert len(snapshots) == 2
            leagues = {s.league for s in snapshots}
            assert leagues == {"League1", "League2"}
        finally:
            session.close()
    
    def test_get_trending_builds_insufficient_data(self, scraper):
        """Test trend analysis with insufficient data"""
        trends = scraper.get_trending_builds("TestLeague", days=7)
        assert "error" in trends
    
    def test_database_deduplication(self, scraper, sample_ladder_data):
        """Test that identical data is not duplicated"""
        # Save same data twice
        id1 = scraper.db.save_ladder_snapshot(sample_ladder_data, "TestLeague", "exp")
        id2 = scraper.db.save_ladder_snapshot(sample_ladder_data, "TestLeague", "exp")
        
        # Should return same ID (deduplication)
        assert id1 == id2
        
        # Verify only one snapshot exists
        session = scraper.db.get_session()
        try:
            snapshots = session.query(LadderSnapshot).all()
            assert len(snapshots) == 1
        finally:
            session.close()


class TestLadderScraperIntegration:
    """Integration tests for ladder scraper"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_url = f"sqlite:///{f.name}"
            yield db_url
    
    def test_end_to_end_workflow(self, temp_db):
        """Test complete workflow from initialization to data analysis"""
        scraper = LadderScraper(database_url=temp_db, backup_to_files=False)
        
        # Mock data for multiple time periods
        base_data = {
            "data": [
                {
                    "account": "Player1",
                    "name": "Char1", 
                    "level": 95,
                    "class": "Witch",
                    "ascendancy": "Necromancer",
                    "skills": ["Summon Skeletons"],
                    "uniques": ["Femurs of the Saints"]
                }
            ]
        }
        
        # Simulate data collection over time
        with patch('src.scraper.ladder_scraper.PoeNinjaClient') as mock_client_class:
            mock_client = Mock()
            mock_client.get_build_overview.return_value = base_data
            mock_client_class.return_value = mock_client
            
            # Collect initial snapshot
            success = scraper.collect_daily_snapshot("TestLeague", "exp")
            assert success is True
            
            # Verify we can get status
            status = scraper.get_league_status("TestLeague")
            assert status["total_snapshots"] == 1
            assert status["latest_character_count"] == 1
            
            # Verify character tracking works
            tracking = scraper.get_character_tracking("Player1", "Char1") 
            assert len(tracking) == 1
            assert tracking[0]["level"] == 95
            
            # Test that recent snapshot prevents duplicate collection
            needed = scraper.check_if_snapshot_needed("TestLeague", "exp")
            assert needed is False
            
            # Test cleanup (should not delete recent data)
            deleted = scraper.cleanup_old_data(keep_days=30)
            assert deleted == 0
            
            # Verify data still exists
            final_status = scraper.get_league_status("TestLeague")
            assert final_status["total_snapshots"] == 1
    
    def test_database_schema_integrity(self, temp_db):
        """Test that database schema is created correctly"""
        scraper = LadderScraper(database_url=temp_db, backup_to_files=False)
        
        # Check that all tables exist by querying them
        session = scraper.db.get_session()
        try:
            # Should not raise exceptions
            session.query(LadderSnapshot).count()
            session.query(Character).count()
            
            # Test database file exists and is readable
            import sqlite3
            db_path = temp_db.replace("sqlite:///", "")
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check table structure
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='ladder_snapshots'")
            table_def = cursor.fetchone()[0]
            assert "league" in table_def
            assert "snapshot_date" in table_def
            assert "total_characters" in table_def
            
            conn.close()
            
        finally:
            session.close()