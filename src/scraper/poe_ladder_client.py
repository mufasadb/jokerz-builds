"""
Client for interacting with Path of Exile Official Ladder API
"""

import requests
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from src.storage.data_manager import DataManager
from src.scraper.rate_limit_manager import rate_limiter

logger = logging.getLogger(__name__)


@dataclass
class RateLimiter:
    """Rate limiter for PoE Official API"""
    requests_per_minute: int = 45  # PoE API allows ~1 request per second
    cache_duration_hours: int = 1  # Cache ladder data for 1 hour
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


class PoeLadderClient:
    """Client for safely interacting with PoE Official Ladder API"""
    
    BASE_URL = "https://www.pathofexile.com/api"
    
    def __init__(self, save_to_disk: bool = True):
        self.save_to_disk = save_to_disk
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json"
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
        
        # Use centralized rate limiter
        if not rate_limiter.wait_for_request("ladder"):
            logger.error("Daily ladder API limit exceeded")
            return None
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            logger.info(f"Making request to {url} with params {params}")
            response = self.session.get(url, params=params, timeout=30)
            
            success = response.status_code == 200
            response_time = int(response.elapsed.total_seconds() * 1000)
            rate_limiter.record_request(
                "ladder", 
                success,
                endpoint=url,
                response_time_ms=response_time,
                league=params.get('league') if params else None,
                error_message=f"Status {response.status_code}: {response.text[:200]}" if not success else None
            )
            
            if success:
                data = response.json()
                # Cache the response
                self._cache[cache_key] = data
                self._cache_timestamps[cache_key] = datetime.now()
                return data
            else:
                logger.error(f"Request failed with status {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            rate_limiter.record_request(
                "ladder", 
                False,
                endpoint=url,
                league=params.get('league') if params else None,
                error_message=str(e)[:200]
            )
            return None
    
    def get_leagues(self) -> Optional[List[Dict]]:
        """
        Get list of available leagues
        
        Returns:
            List of league information dictionaries
        """
        data = self._make_request("leagues")
        
        if data and isinstance(data, list):
            # Filter to get current active leagues (not ended)
            active_leagues = []
            for league in data:
                if not league.get("endAt"):  # No end date means still active
                    active_leagues.append({
                        "id": league.get("id"),
                        "description": league.get("description", ""),
                        "rules": league.get("rules", []),
                        "url": league.get("url", ""),
                        "startAt": league.get("startAt"),
                        "endAt": league.get("endAt")
                    })
            return active_leagues
        
        return data
    
    def get_current_challenge_league(self) -> Optional[str]:
        """
        Get the current challenge league name (not Standard/Hardcore and no modifiers)
        
        Returns:
            League ID string or None
        """
        leagues = self.get_leagues()
        if not leagues:
            return None
        
        # Look for leagues that:
        # 1. Are not Standard/Hardcore
        # 2. Have no special rule modifiers
        # 3. Are currently active
        candidates = []
        
        for league in leagues:
            league_id = league.get("id", "")
            rules = league.get("rules", [])
            rule_names = [rule.get("name", "") for rule in rules]
            
            # Skip Standard and Hardcore
            if league_id.lower() in ["standard", "hardcore"]:
                continue
            
            # Skip leagues with modifiers
            skip_rules = ["Hardcore", "Solo Self-Found", "Ruthless"]
            if any(skip_rule in rule_names for skip_rule in skip_rules):
                continue
            
            # Check if it has actual ladder data
            try:
                test_ladder = self.get_ladder(league_id, "league", 0, 1)
                if test_ladder and test_ladder.get("entries"):
                    candidates.append({
                        "id": league_id,
                        "description": league.get("description", ""),
                        "entry_count": len(test_ladder.get("entries", []))
                    })
            except:
                continue
        
        # Return the candidate with the most entries (likely the main league)
        if candidates:
            best_candidate = max(candidates, key=lambda x: x["entry_count"])
            logger.info(f"Found challenge league: {best_candidate['id']} with {best_candidate['entry_count']} entries")
            return best_candidate["id"]
        
        logger.warning("No challenge league found")
        return None
    
    def get_ladder(self, league_id: str, ladder_type: str = "league", 
                   offset: int = 0, limit: int = 200) -> Optional[Dict]:
        """
        Get ladder data for a specific league
        
        Args:
            league_id: League identifier
            ladder_type: Type of ladder ("league" for XP, "delve-solo" for delve)
            offset: Starting position (0-based)
            limit: Number of entries to return (max 200)
        
        Returns:
            Ladder data dictionary or None
        """
        params = {
            "type": ladder_type,
            "offset": offset,
            "limit": min(limit, 200)  # API max is 200
        }
        
        endpoint = f"ladders/{league_id}"
        data = self._make_request(endpoint, params)
        
        # Save to disk if enabled
        if data and self.save_to_disk:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ladder_{league_id}_{ladder_type}_{timestamp}.json"
            # Save using data manager
            import json
            import os
            filepath = os.path.join("data", "raw", filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved raw ladder data to {filepath}")
        
        return data
    
    def get_full_ladder(self, league_id: str, ladder_type: str = "league", 
                       max_entries: int = 1000) -> Optional[List[Dict]]:
        """
        Get full ladder data by making multiple paginated requests
        
        Args:
            league_id: League identifier
            ladder_type: Type of ladder
            max_entries: Maximum entries to retrieve
        
        Returns:
            List of all ladder entries
        """
        all_entries = []
        offset = 0
        limit = 200  # API maximum per request
        
        while len(all_entries) < max_entries:
            remaining = max_entries - len(all_entries)
            current_limit = min(limit, remaining)
            
            logger.info(f"Fetching ladder entries {offset} to {offset + current_limit - 1}")
            
            data = self.get_ladder(league_id, ladder_type, offset, current_limit)
            
            if not data or "entries" not in data:
                logger.warning("No entries returned from ladder API")
                break
            
            entries = data["entries"]
            if not entries:
                logger.info("No more entries available")
                break
            
            all_entries.extend(entries)
            
            # If we got fewer entries than requested, we've reached the end
            if len(entries) < current_limit:
                logger.info(f"Reached end of ladder at {len(all_entries)} entries")
                break
            
            offset += current_limit
            
            # Add delay between requests to be respectful
            time.sleep(1.5)
        
        logger.info(f"Retrieved {len(all_entries)} total ladder entries")
        return all_entries
    
    def get_character_details(self, account_name: str, character_name: str) -> Optional[Dict]:
        """
        Get detailed character information
        
        Args:
            account_name: Account name
            character_name: Character name
        
        Returns:
            Character details or None
        """
        endpoint = f"character-window/get-characters"
        params = {
            "accountName": account_name,
            "character": character_name
        }
        
        return self._make_request(endpoint, params)


# Example usage and testing
if __name__ == "__main__":
    import logging
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    client = PoeLadderClient()
    
    # Get available leagues
    print("🔍 Fetching available leagues...")
    leagues = client.get_leagues()
    if leagues:
        print(f"Found {len(leagues)} active leagues:")
        for league in leagues[:5]:  # Show first 5
            print(f"  - {league['id']}: {league.get('description', 'No description')}")
    
    # Get current challenge league
    print("\n🎯 Finding current challenge league...")
    challenge_league = client.get_current_challenge_league()
    if challenge_league:
        print(f"Current challenge league: {challenge_league}")
        
        # Get ladder data for challenge league
        print(f"\n📊 Fetching ladder data for {challenge_league}...")
        ladder_data = client.get_ladder(challenge_league, "league", 0, 10)
        if ladder_data and "entries" in ladder_data:
            print(f"Retrieved {len(ladder_data['entries'])} ladder entries")
            
            # Show top 3 characters
            for i, entry in enumerate(ladder_data["entries"][:3], 1):
                char = entry.get("character", {})
                account = entry.get("account", {})
                print(f"  #{i}: {char.get('name', 'Unknown')} "
                      f"(Level {char.get('level', '?')}) - "
                      f"{char.get('class', 'Unknown')} - "
                      f"Account: {account.get('name', 'Unknown')}")
        else:
            print("Failed to retrieve ladder data")
    else:
        print("Could not find current challenge league")