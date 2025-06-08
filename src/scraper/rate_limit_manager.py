"""
Centralized rate limiting manager for all PoE API calls
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass
import random

logger = logging.getLogger(__name__)


@dataclass
class APILimits:
    """API rate limit configuration"""
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    base_delay: float  # Base delay between requests in seconds
    max_delay: float   # Maximum delay for backoff


class RateLimitManager:
    """Centralized rate limiting for all PoE API endpoints"""
    
    def __init__(self):
        # Scaled limits for comprehensive data collection
        self.limits = {
            "ladder": APILimits(
                requests_per_minute=4,     # Very respectful rate
                requests_per_hour=15,      # Spread over 8+ hours
                requests_per_day=500,      # Ample for 72 needed calls
                base_delay=15.0,           # Respectful 15s delay
                max_delay=60.0
            ),
            "character": APILimits(
                requests_per_minute=3,     # Gentle rate for profiles
                requests_per_hour=12,      # 8+ hours available
                requests_per_day=1200,     # Target: 800+ enhanced profiles
                base_delay=20.0,           # Very respectful 20s delay
                max_delay=120.0
            ),
            "ninja": APILimits(
                requests_per_minute=15,    # PoE Ninja is more lenient
                requests_per_hour=60,
                requests_per_day=300,
                base_delay=4.0,
                max_delay=30.0
            )
        }
        
        # Track request history
        self.request_history: Dict[str, list] = {
            "ladder": [],
            "character": [],
            "ninja": []
        }
        
        # Track failures for exponential backoff
        self.failure_counts: Dict[str, int] = {
            "ladder": 0,
            "character": 0,
            "ninja": 0
        }
        
        self.last_request_times: Dict[str, Optional[datetime]] = {
            "ladder": None,
            "character": None,
            "ninja": None
        }
    
    def wait_for_request(self, api_type: str) -> bool:
        """
        Wait until it's safe to make a request
        
        Args:
            api_type: 'ladder', 'character', or 'ninja'
            
        Returns:
            True if request is allowed, False if daily limit exceeded
        """
        if api_type not in self.limits:
            raise ValueError(f"Unknown API type: {api_type}")
        
        limits = self.limits[api_type]
        max_wait_cycles = 10  # Prevent infinite loops
        cycles = 0
        
        while cycles < max_wait_cycles:
            now = datetime.now()
            
            # Clean old requests from history
            self._clean_request_history(api_type, now)
            
            # Check daily limit
            today_requests = [req for req in self.request_history[api_type] 
                             if (now - req).total_seconds() < 86400]  # 24 hours
            
            if len(today_requests) >= limits.requests_per_day:
                logger.warning(f"{api_type} API daily limit ({limits.requests_per_day}) reached")
                return False
            
            # Check hourly limit
            hour_requests = [req for req in self.request_history[api_type]
                            if (now - req).total_seconds() < 3600]  # 1 hour
            
            if len(hour_requests) >= limits.requests_per_hour:
                wait_time = 3600 - (now - min(hour_requests)).total_seconds()
                logger.info(f"{api_type} API hourly limit reached. Waiting {wait_time:.1f} seconds")
                time.sleep(min(wait_time, 60))  # Cap wait time to 60 seconds per cycle
                cycles += 1
                continue
            
            # Check minute limit
            minute_requests = [req for req in self.request_history[api_type]
                              if (now - req).total_seconds() < 60]  # 1 minute
            
            if len(minute_requests) >= limits.requests_per_minute:
                wait_time = 60 - (now - min(minute_requests)).total_seconds()
                logger.info(f"{api_type} API minute limit reached. Waiting {wait_time:.1f} seconds")
                time.sleep(min(wait_time + 1, 61))  # Cap wait time and add safety margin
                cycles += 1
                continue
            
            # If we reach here, no rate limits are hit
            break
        
        if cycles >= max_wait_cycles:
            logger.error(f"{api_type} API rate limiting exceeded max wait cycles, proceeding anyway")
            return True
        
        # Calculate delay based on base delay + failure backoff
        base_delay = limits.base_delay
        failure_count = self.failure_counts[api_type]
        
        # Exponential backoff for failures
        if failure_count > 0:
            backoff_delay = min(base_delay * (2 ** failure_count), limits.max_delay)
            delay = backoff_delay
            logger.info(f"Applying failure backoff: {delay:.1f}s (failure count: {failure_count})")
        else:
            delay = base_delay
        
        # Add some jitter to avoid synchronized requests
        jitter = random.uniform(0.5, 1.5)
        delay *= jitter
        
        # Ensure minimum time between requests
        if self.last_request_times[api_type]:
            elapsed = (now - self.last_request_times[api_type]).total_seconds()
            if elapsed < delay:
                sleep_time = delay - elapsed
                logger.debug(f"Rate limiting {api_type}: sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
        else:
            # First request, still apply initial delay
            logger.debug(f"Initial {api_type} request: sleeping {delay:.1f}s")
            time.sleep(delay)
        
        return True
    
    def record_request(self, api_type: str, success: bool = True, endpoint: str = None,
                      response_time_ms: int = None, error_message: str = None,
                      league: str = None, character_name: str = None,
                      account_name: str = None, source: str = 'system',
                      source_user: str = None):
        """Record a request and its outcome"""
        now = datetime.now()
        self.request_history[api_type].append(now)
        self.last_request_times[api_type] = now
        
        if success:
            # Reset failure count on success
            self.failure_counts[api_type] = 0
        else:
            # Increment failure count
            self.failure_counts[api_type] += 1
            logger.warning(f"{api_type} API request failed. Failure count: {self.failure_counts[api_type]}")
        
        # Log to database
        try:
            from src.storage.database import DatabaseManager
            db = DatabaseManager()
            db.log_request(
                api_type=api_type,
                success=success,
                endpoint=endpoint,
                response_time_ms=response_time_ms,
                error_message=error_message,
                league=league,
                character_name=character_name,
                account_name=account_name,
                source=source,
                source_user=source_user
            )
        except Exception as e:
            logger.error(f"Failed to log request to database: {e}")
    
    def _clean_request_history(self, api_type: str, now: datetime):
        """Remove old requests from history to keep memory usage low"""
        cutoff = now - timedelta(days=1)  # Keep 24 hours of history
        self.request_history[api_type] = [
            req for req in self.request_history[api_type] 
            if req > cutoff
        ]
    
    def get_status(self) -> Dict:
        """Get current rate limiting status"""
        now = datetime.now()
        status = {}
        
        for api_type, limits in self.limits.items():
            history = self.request_history[api_type]
            
            # Count requests in different time windows
            minute_requests = len([req for req in history if (now - req).total_seconds() < 60])
            hour_requests = len([req for req in history if (now - req).total_seconds() < 3600])
            day_requests = len([req for req in history if (now - req).total_seconds() < 86400])
            
            status[api_type] = {
                "limits": {
                    "per_minute": limits.requests_per_minute,
                    "per_hour": limits.requests_per_hour,
                    "per_day": limits.requests_per_day
                },
                "current": {
                    "last_minute": minute_requests,
                    "last_hour": hour_requests, 
                    "last_day": day_requests
                },
                "remaining": {
                    "minute": max(0, limits.requests_per_minute - minute_requests),
                    "hour": max(0, limits.requests_per_hour - hour_requests),
                    "day": max(0, limits.requests_per_day - day_requests)
                },
                "failure_count": self.failure_counts[api_type],
                "last_request": self.last_request_times[api_type].isoformat() if self.last_request_times[api_type] else None
            }
        
        return status
    
    def estimate_collection_time(self, leagues: list, chars_per_league: int = 1000, 
                                enhance_per_league: int = 10) -> Dict:
        """Estimate time for a full collection"""
        ladder_requests = len(leagues) * (chars_per_league // 200)  # 200 chars per request
        character_requests = len(leagues) * enhance_per_league
        
        ladder_time = ladder_requests * self.limits["ladder"].base_delay
        character_time = character_requests * self.limits["character"].base_delay
        
        return {
            "leagues": len(leagues),
            "ladder_requests": ladder_requests,
            "character_requests": character_requests,
            "estimated_time_minutes": (ladder_time + character_time) / 60,
            "ladder_time_minutes": ladder_time / 60,
            "character_time_minutes": character_time / 60,
            "total_requests": ladder_requests + character_requests
        }


# Global rate limit manager instance
rate_limiter = RateLimitManager()


# Example usage
if __name__ == "__main__":
    manager = RateLimitManager()
    
    # Show current limits
    print("📊 Rate Limiting Configuration")
    print("=" * 40)
    
    for api_type, limits in manager.limits.items():
        print(f"\n{api_type.upper()} API:")
        print(f"  - Per minute: {limits.requests_per_minute}")
        print(f"  - Per hour: {limits.requests_per_hour}")
        print(f"  - Per day: {limits.requests_per_day}")
        print(f"  - Base delay: {limits.base_delay}s")
    
    # Estimate collection time
    leagues = ["Standard", "Hardcore", "Settlers", "SSF Settlers", "Hardcore Settlers", "HC SSF Settlers"]
    estimate = manager.estimate_collection_time(leagues, enhance_per_league=10)
    
    print(f"\n🕐 Collection Time Estimate:")
    print(f"  - Total requests: {estimate['total_requests']}")
    print(f"  - Estimated time: {estimate['estimated_time_minutes']:.1f} minutes")
    print(f"  - Ladder collection: {estimate['ladder_time_minutes']:.1f} minutes")
    print(f"  - Character enhancement: {estimate['character_time_minutes']:.1f} minutes")