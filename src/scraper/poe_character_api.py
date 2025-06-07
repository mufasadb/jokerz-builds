"""
Client for fetching detailed character data from PoE Character API
This can get skills, items, and passive tree data for public characters
"""

import requests
import time
import logging
from typing import Dict, Optional, List
from datetime import datetime
from src.scraper.rate_limit_manager import rate_limiter

logger = logging.getLogger(__name__)


class PoECharacterClient:
    """Client for fetching detailed character information"""
    
    BASE_URL = "https://www.pathofexile.com/character-window"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        })
        self.last_request_time = None
        self.request_delay = 1.0  # Delay between requests in seconds
    
    def _rate_limit(self) -> bool:
        """Use centralized rate limiter"""
        return rate_limiter.wait_for_request("character")
    
    def get_character_items(self, account_name: str, character_name: str) -> Optional[Dict]:
        """
        Get character's equipped items
        
        Args:
            account_name: Account name
            character_name: Character name
            
        Returns:
            Character items data or None if private/error
        """
        if not self._rate_limit():
            logger.error("Character API rate limit exceeded")
            return None
        
        endpoint = f"{self.BASE_URL}/get-items"
        params = {
            "accountName": account_name,
            "character": character_name
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            
            success = response.status_code == 200
            response_time = int(response.elapsed.total_seconds() * 1000)
            rate_limiter.record_request(
                "character", 
                success,
                endpoint=endpoint,
                response_time_ms=response_time,
                character_name=character_name,
                account_name=account_name,
                error_message=f"Status {response.status_code}" if not success else None
            )
            
            if response.status_code == 200:
                data = response.json()
                return data
            elif response.status_code == 403:
                logger.info(f"Character {character_name} is private")
                return None
            else:
                logger.error(f"Failed to get items: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching character items: {e}")
            rate_limiter.record_request("character", False)
            return None
    
    def get_character_passives(self, account_name: str, character_name: str) -> Optional[Dict]:
        """
        Get character's passive tree
        
        Args:
            account_name: Account name
            character_name: Character name
            
        Returns:
            Passive tree data or None if private/error
        """
        self._rate_limit()
        
        endpoint = f"{self.BASE_URL}/get-passive-skills"
        params = {
            "accountName": account_name,
            "character": character_name
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data
            elif response.status_code == 403:
                logger.info(f"Character {character_name} passive tree is private")
                return None
            else:
                logger.error(f"Failed to get passives: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching character passives: {e}")
            return None
    
    def analyze_character_build(self, account_name: str, character_name: str) -> Dict:
        """
        Get and analyze a character's complete build
        
        Args:
            account_name: Account name
            character_name: Character name
            
        Returns:
            Dictionary with build analysis
        """
        build_data = {
            "account": account_name,
            "character": character_name,
            "items": None,
            "skills": [],
            "uniques": [],
            "main_skill_links": [],
            "defensive_stats": {},
            "error": None
        }
        
        # Get items data
        items_data = self.get_character_items(account_name, character_name)
        
        if items_data is None:
            build_data["error"] = "Character profile is private"
            return build_data
        
        if "items" in items_data:
            build_data["items"] = items_data["items"]
            
            # Extract skills from gems
            for item in items_data["items"]:
                # Check sockets for skill gems
                if "socketedItems" in item:
                    for gem in item["socketedItems"]:
                        if gem.get("support") == False:  # Active skill gem
                            skill_name = gem.get("typeLine", "Unknown")
                            if skill_name not in build_data["skills"]:
                                build_data["skills"].append(skill_name)
                
                # Track unique items
                if item.get("frameType") == 3:  # Unique items
                    unique_name = item.get("name", "Unknown")
                    if unique_name and unique_name not in build_data["uniques"]:
                        build_data["uniques"].append(unique_name)
            
            # Find main skill (6-link or most supported)
            build_data["main_skill_links"] = self._find_main_skills(items_data["items"])
            
            # Extract defensive stats from character data
            if "character" in items_data:
                char_stats = items_data["character"]
                build_data["defensive_stats"] = {
                    "life": char_stats.get("life", 0),
                    "energy_shield": char_stats.get("energyShield", 0),
                    "armour": char_stats.get("armour", 0),
                    "evasion": char_stats.get("evasionRating", 0),
                    "level": char_stats.get("level", 1),
                    "class": char_stats.get("class", ""),
                    # These may not be directly available from API
                    "fire_resistance": 0,  # Would need to calculate from items
                    "cold_resistance": 0,
                    "lightning_resistance": 0,
                    "chaos_resistance": 0,
                    "block_chance": 0,
                    "spell_block_chance": 0
                }
        
        return build_data
    
    def _find_main_skills(self, items: List[Dict]) -> List[Dict]:
        """Find main skill setups (5-link or 6-link)"""
        main_skills = []
        
        for item in items:
            if "sockets" in item and len(item["sockets"]) >= 5:
                # Check if sockets are linked
                groups = {}
                for socket in item["sockets"]:
                    group = socket.get("group", 0)
                    if group not in groups:
                        groups[group] = []
                    groups[group].append(socket)
                
                # Find large link groups
                for group_id, sockets in groups.items():
                    if len(sockets) >= 5:
                        # Extract gems in this link
                        skill_setup = {
                            "item": item.get("typeLine", "Unknown"),
                            "links": len(sockets),
                            "gems": []
                        }
                        
                        if "socketedItems" in item:
                            for gem in item["socketedItems"]:
                                gem_socket_index = gem.get("socket", -1)
                                # Check if this gem's socket is in the current link group
                                if (gem_socket_index >= 0 and 
                                    gem_socket_index < len(item["sockets"]) and
                                    item["sockets"][gem_socket_index].get("group") == group_id):
                                    # Extract gem level safely
                                    level = "?"
                                    properties = gem.get("properties", [])
                                    if properties and len(properties) > 0:
                                        values = properties[0].get("values", [])
                                        if values and len(values) > 0 and len(values[0]) > 0:
                                            level = values[0][0]
                                    
                                    gem_info = {
                                        "name": gem.get("typeLine", "Unknown"),
                                        "level": level,
                                        "support": gem.get("support", False)
                                    }
                                    skill_setup["gems"].append(gem_info)
                        
                        if skill_setup["gems"]:
                            main_skills.append(skill_setup)
        
        # Sort by number of links
        return sorted(main_skills, key=lambda x: x["links"], reverse=True)


# Example usage
if __name__ == "__main__":
    client = PoECharacterClient()
    
    # Test with a character
    test_account = "Zizaran"
    test_character = "ZizaranBleeding"
    
    print(f"Analyzing {test_character} from account {test_account}...")
    
    build_data = client.analyze_character_build(test_account, test_character)
    
    if build_data["error"]:
        print(f"Error: {build_data['error']}")
    else:
        print(f"\nSkills found: {build_data['skills']}")
        print(f"Unique items: {build_data['uniques']}")
        print(f"\nMain skill setups:")
        for setup in build_data["main_skill_links"]:
            print(f"  {setup['links']}-link in {setup['item']}:")
            for gem in setup["gems"]:
                gem_type = "Support" if gem["support"] else "Active"
                print(f"    - {gem['name']} (Level {gem['level']}) [{gem_type}]")