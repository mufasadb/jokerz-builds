import pytest
import responses
from datetime import datetime, timedelta
from src.scraper.poe_ninja_client import PoeNinjaClient, RateLimiter
import time


class TestRateLimiter:
    def test_initial_request_allowed(self):
        limiter = RateLimiter(requests_per_minute=30)
        assert limiter.can_make_request() is True
    
    def test_rate_limit_enforcement(self):
        limiter = RateLimiter(requests_per_minute=2)
        
        # First two requests should be allowed
        assert limiter.can_make_request() is True
        limiter.record_request()
        assert limiter.can_make_request() is True
        limiter.record_request()
        
        # Third request should be blocked
        assert limiter.can_make_request() is False
    
    def test_rate_limit_reset_after_minute(self):
        limiter = RateLimiter(requests_per_minute=1)
        
        # First request allowed
        assert limiter.can_make_request() is True
        limiter.record_request()
        
        # Second request blocked
        assert limiter.can_make_request() is False
        
        # Simulate time passing (monkey patch for testing)
        limiter._minute_start = datetime.now() - timedelta(seconds=61)
        
        # Should allow request again
        assert limiter.can_make_request() is True


class TestPoeNinjaClient:
    @pytest.fixture
    def client(self):
        return PoeNinjaClient(league="TestLeague")
    
    @responses.activate
    def test_get_currency_overview_success(self, client):
        mock_response = {
            "lines": [
                {"currencyTypeName": "Chaos Orb", "chaosEquivalent": 1},
                {"currencyTypeName": "Exalted Orb", "chaosEquivalent": 150}
            ]
        }
        
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/currencyoverview",
            json=mock_response,
            status=200,
            match_querystring=False
        )
        
        result = client.get_currency_overview()
        assert result is not None
        assert len(result["lines"]) == 2
        assert result["lines"][0]["currencyTypeName"] == "Chaos Orb"
    
    @responses.activate
    def test_get_item_overview_success(self, client):
        mock_response = {
            "lines": [
                {"name": "Headhunter", "baseType": "Leather Belt", "chaosValue": 15000},
                {"name": "Mageblood", "baseType": "Heavy Belt", "chaosValue": 25000}
            ]
        }
        
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/itemoverview",
            json=mock_response,
            status=200,
            match_querystring=False
        )
        
        result = client.get_item_overview("UniqueBelt")
        assert result is not None
        assert len(result["lines"]) == 2
        assert result["lines"][0]["name"] == "Headhunter"
    
    @responses.activate
    def test_failed_request_returns_none(self, client):
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/currencyoverview",
            status=404,
            match_querystring=False
        )
        
        result = client.get_currency_overview()
        assert result is None
    
    def test_cache_functionality(self, client):
        mock_data = {"lines": [{"test": "data"}], "currencyDetails": []}
        
        # Manually add to cache with correct key format
        cache_key = "currencyoverview_{'league': 'TestLeague', 'type': 'Currency'}"
        client._cache[cache_key] = mock_data
        client._cache_timestamps[cache_key] = datetime.now()
        
        # Should return cached data without making request
        result = client.get_currency_overview()
        assert result == mock_data
    
    def test_cache_expiration(self, client):
        mock_data = {"lines": [{"test": "old_data"}]}
        
        # Add expired cache entry with correct key format
        cache_key = "currencyoverview_{'league': 'TestLeague', 'type': 'Currency'}"
        client._cache[cache_key] = mock_data
        client._cache_timestamps[cache_key] = datetime.now() - timedelta(hours=3)
        
        # Should return None as cache is expired and no mock response set
        result = client._get_from_cache(cache_key)
        assert result is None
    
    @responses.activate
    def test_rate_limiting_delays_requests(self, client):
        # Set very low rate limit for testing
        client.rate_limiter.requests_per_minute = 1
        
        mock_response = {"lines": []}
        
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/currencyoverview",
            json=mock_response,
            status=200,
            match_querystring=False
        )
        
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/itemoverview",
            json=mock_response,
            status=200,
            match_querystring=False
        )
        
        # First request should succeed
        start_time = time.time()
        result1 = client.get_currency_overview()
        assert result1 is not None
        
        # Second request should be delayed (but we'll bypass wait for test)
        # Just verify rate limiter state
        assert client.rate_limiter.can_make_request() is False
    
    def test_user_agent_header(self, client):
        assert "User-Agent" in client.session.headers
        assert "Joker-Builds" in client.session.headers["User-Agent"]


# End-to-End test
class TestEndToEnd:
    @responses.activate
    def test_complete_workflow(self):
        # Create client
        client = PoeNinjaClient(league="Standard")
        
        # Mock multiple API responses
        currency_response = {
            "lines": [
                {"currencyTypeName": "Chaos Orb", "chaosEquivalent": 1}
            ]
        }
        
        item_response = {
            "lines": [
                {"name": "Tabula Rasa", "chaosValue": 10}
            ]
        }
        
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/currencyoverview",
            json=currency_response,
            status=200,
            match_querystring=False
        )
        
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/itemoverview",
            json=item_response,
            status=200,
            match_querystring=False
        )
        
        # Fetch currency data
        currency_data = client.get_currency_overview()
        assert currency_data is not None
        assert len(currency_data["lines"]) == 1
        
        # Fetch item data
        item_data = client.get_item_overview("UniqueArmour")
        assert item_data is not None
        assert len(item_data["lines"]) == 1
        
        # Second call to currency should use cache
        currency_data_cached = client.get_currency_overview()
        assert currency_data_cached == currency_data
        
        # Verify only 2 actual API calls were made (not 3)
        assert len(responses.calls) == 2