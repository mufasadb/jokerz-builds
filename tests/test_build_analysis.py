"""
Tests for build analysis functionality using actual implemented APIs
"""

import pytest
import responses
from datetime import datetime
from src.scraper.poe_ninja_client import PoeNinjaClient


class TestPoeNinjaClient:
    """Test the PoeNinjaClient functionality"""
    
    @pytest.fixture
    def client(self):
        """Create a test client"""
        return PoeNinjaClient(league="TestLeague", save_to_disk=False)
    
    @pytest.fixture
    def mock_currency_response(self):
        """Mock currency API response"""
        return {
            "lines": [
                {
                    "currencyTypeName": "Chaos Orb",
                    "chaosValue": 1.0,
                    "exaltedValue": 0.01
                },
                {
                    "currencyTypeName": "Exalted Orb",
                    "chaosValue": 100.0,
                    "exaltedValue": 1.0
                }
            ]
        }
    
    @pytest.fixture
    def mock_item_response(self):
        """Mock item API response"""
        return {
            "lines": [
                {
                    "name": "Belly of the Beast",
                    "chaosValue": 50.0,
                    "count": 10,
                    "baseType": "Full Dragonscale"
                },
                {
                    "name": "Kaom's Heart",
                    "chaosValue": 75.0,
                    "count": 5,
                    "baseType": "Glorious Plate"
                }
            ]
        }
    
    @responses.activate
    def test_get_currency_overview(self, client, mock_currency_response):
        """Test fetching currency overview data"""
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/currencyoverview",
            json=mock_currency_response,
            status=200
        )
        
        result = client.get_currency_overview()
        assert result is not None
        assert "lines" in result
        assert len(result["lines"]) == 2
        assert result["lines"][0]["currencyTypeName"] == "Chaos Orb"
    
    @responses.activate
    def test_get_item_overview(self, client, mock_item_response):
        """Test fetching item overview data"""
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/itemoverview",
            json=mock_item_response,
            status=200
        )
        
        result = client.get_item_overview("uniquearmour")
        assert result is not None
        assert "lines" in result
        assert len(result["lines"]) == 2
        assert result["lines"][0]["name"] == "Belly of the Beast"
    
    @responses.activate
    def test_currency_api_failure(self, client):
        """Test handling of API failures"""
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/currencyoverview",
            json={"error": "Not found"},
            status=404
        )
        
        result = client.get_currency_overview()
        assert result is None
    
    @responses.activate
    def test_item_api_failure(self, client):
        """Test handling of API failures for items"""
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/itemoverview",
            json={"error": "Not found"},
            status=404
        )
        
        result = client.get_item_overview("uniqueweapon")
        assert result is None
    
    def test_client_initialization(self):
        """Test client initialization"""
        client = PoeNinjaClient(league="Standard", save_to_disk=False)
        assert client.league == "Standard"
        assert client.save_to_disk is False
        assert client.session is not None
    
    def test_caching_mechanism(self, client):
        """Test that caching works correctly"""
        # Test cache miss
        cache_key = "test_key"
        result = client._get_from_cache(cache_key)
        assert result is None
        
        # Test cache hit
        client._cache[cache_key] = {"test": "data"}
        client._cache_timestamps[cache_key] = datetime.now()
        result = client._get_from_cache(cache_key)
        assert result == {"test": "data"}


class TestBuildAnalysisIntegration:
    """Integration tests for build analysis workflows"""
    
    @pytest.mark.skip(reason="Integration test requires database setup")
    def test_complete_build_analysis_workflow(self):
        """Test complete workflow from data collection to analysis"""
        # This would test the complete workflow:
        # 1. Collect ladder data
        # 2. Enhance with profiles 
        # 3. Categorize builds
        # 4. Calculate EHP
        # 5. Query results
        pass


# Legacy tests that are no longer applicable (build overview API removed)
class TestLegacyBuildAnalysis:
    """Tests for build overview functionality that was removed"""
    
    @pytest.mark.skip(reason="Build overview API not implemented - use PoeLadderClient instead")
    def test_get_build_overview_raw(self):
        """Legacy test - build overview removed from PoE Ninja client"""
        pass
    
    @pytest.mark.skip(reason="Build analysis API not implemented - use PoeLadderClient instead")
    def test_get_builds_analysis(self):
        """Legacy test - build analysis moved to ladder scraper"""
        pass
    
    @pytest.mark.skip(reason="Delve builds API not implemented - use PoeLadderClient instead")
    def test_get_delve_builds(self):
        """Legacy test - delve data moved to ladder scraper"""
        pass
    
    @pytest.mark.skip(reason="Build filtering not implemented - use database queries instead")
    def test_filter_by_class(self):
        """Legacy test - filtering moved to database layer"""
        pass
    
    @pytest.mark.skip(reason="Build filtering not implemented - use database queries instead")
    def test_filter_by_skill(self):
        """Legacy test - filtering moved to database layer"""
        pass
    
    @pytest.mark.skip(reason="Level distribution not implemented - use database aggregation instead")
    def test_level_distribution(self):
        """Legacy test - statistics moved to database layer"""
        pass
    
    @pytest.mark.skip(reason="Historical data API not implemented")
    def test_historical_data(self):
        """Legacy test - historical analysis not implemented"""
        pass
    
    @pytest.mark.skip(reason="Empty response handling covered in new tests")
    def test_empty_response_handling(self):
        """Legacy test - error handling covered in new tests"""
        pass