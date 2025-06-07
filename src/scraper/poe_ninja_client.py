import requests
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from urllib.parse import urlencode
# Removed build model imports - PoE Ninja only handles items/currency now
from src.storage.data_manager import DataManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RateLimiter:
    """Rate limiter to ensure respectful API usage"""
    requests_per_minute: int = 30  # Conservative limit
    cache_duration_hours: int = 2  # As recommended by community
    _last_request_time: Optional[datetime] = None
    _request_count: int = 0
    _minute_start: Optional[datetime] = None
    
    def can_make_request(self) -> bool:
        now = datetime.now()
        
        if self._minute_start is None or (now - self._minute_start).seconds >= 60:
            self._minute_start = now
            self._request_count = 0
            
        if self._request_count >= self.requests_per_minute:
            return False
            
        return True
    
    def record_request(self):
        self._request_count += 1
        self._last_request_time = datetime.now()
    
    def wait_if_needed(self):
        if not self.can_make_request():
            wait_time = 60 - (datetime.now() - self._minute_start).seconds
            logger.info(f"Rate limit reached. Waiting {wait_time} seconds...")
            time.sleep(wait_time)


class PoeNinjaClient:
    """Client for safely interacting with poe.ninja API - ITEMS AND CURRENCY ONLY"""
    
    BASE_URL = "https://poe.ninja/api/data"
    
    def __init__(self, league: str = "Standard", save_to_disk: bool = True):
        self.league = league
        self.save_to_disk = save_to_disk
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Joker-Builds/1.0 (https://github.com/your-repo)"
        })
        self.rate_limiter = RateLimiter()
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        
        # Initialize data manager for persistent storage
        if self.save_to_disk:
            self.data_manager = DataManager()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """Get data from cache if still valid"""
        if cache_key in self._cache:
            timestamp = self._cache_timestamps.get(cache_key)
            if timestamp and (datetime.now() - timestamp).total_seconds() < self.rate_limiter.cache_duration_hours * 3600:
                logger.info(f"Returning cached data for {cache_key}")
                return self._cache[cache_key]
        return None
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make a rate-limited request to the API"""
        cache_key = f"{endpoint}_{params}"
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Rate limiting
        self.rate_limiter.wait_if_needed()
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            logger.info(f"Making request to {url} with params {params}")
            response = self.session.get(url, params=params, timeout=30)
            
            self.rate_limiter.record_request()
            
            if response.status_code == 200:
                data = response.json()
                # Cache the response
                self._cache[cache_key] = data
                self._cache_timestamps[cache_key] = datetime.now()
                return data
            else:
                logger.error(f"Request failed with status {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return None
    
    def get_currency_overview(self, date: Optional[str] = None) -> Optional[Dict]:
        """
        Get currency exchange rates
        
        Args:
            date: Optional date in format 'YYYY-MM-DD' for historical data
        """
        params = {"league": self.league}
        if date:
            params["date"] = date
        
        params["type"] = "Currency"  # Currency endpoint requires type
        data = self._make_request("currencyoverview", params)
        
        # Save to disk if enabled
        if data and self.save_to_disk:
            self.data_manager.save_currency_data(data, self.league, date)
        
        return data
    
    def get_item_overview(self, item_type: str, date: Optional[str] = None) -> Optional[Dict]:
        """
        Get item prices for a specific type
        
        Args:
            item_type: Type of item (e.g., 'UniqueWeapon', 'DivinationCard')
            date: Optional date in format 'YYYY-MM-DD' for historical data
        """
        params = {
            "league": self.league,
            "type": item_type
        }
        if date:
            params["date"] = date
        
        data = self._make_request("itemoverview", params)
        
        # Save to disk if enabled
        if data and self.save_to_disk:
            self.data_manager.save_item_data(data, self.league, item_type, date)
        
        return data
    
    # BUILD METHODS REMOVED - Use PoeLadderClient for character/ladder data
    
# Example usage - ITEMS AND CURRENCY ONLY
if __name__ == "__main__":
    client = PoeNinjaClient(league="Standard")
    
    # Get currency data
    print("Fetching currency data...")
    currency_data = client.get_currency_overview()
    if currency_data:
        print(f"Retrieved {len(currency_data.get('lines', []))} currency types")
        
        # Show top 5 currencies by chaos value
        currencies = currency_data.get('lines', [])
        sorted_currencies = sorted(currencies, key=lambda x: x.get('chaosValue', 0), reverse=True)
        print("Top 5 currencies by chaos value:")
        for curr in sorted_currencies[:5]:
            print(f"  {curr.get('currencyTypeName', 'Unknown')}: {curr.get('chaosValue', 0)} chaos")
    
    # Get unique weapon data
    print("\nFetching unique weapon data...")
    weapon_data = client.get_item_overview("UniqueWeapon")
    if weapon_data:
        print(f"Retrieved {len(weapon_data.get('lines', []))} unique weapons")
        
        # Show top 5 weapons by chaos value
        weapons = weapon_data.get('lines', [])
        sorted_weapons = sorted(weapons, key=lambda x: x.get('chaosValue', 0), reverse=True)
        print("Top 5 unique weapons by chaos value:")
        for weapon in sorted_weapons[:5]:
            print(f"  {weapon.get('name', 'Unknown')}: {weapon.get('chaosValue', 0)} chaos")