"""
Enhanced ladder scraper with database integration for daily snapshots
Uses PoE Official Ladder API for character data and PoE Ninja for item/currency data
"""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from src.scraper.poe_ladder_client import PoeLadderClient
from src.scraper.poe_ninja_client import PoeNinjaClient
from src.scraper.poe_character_api import PoECharacterClient
from src.storage.database import DatabaseManager
from src.storage.data_manager import DataManager

logger = logging.getLogger(__name__)


class LadderScraper:
    """Enhanced scraper for collecting and storing ladder snapshots from PoE Official API"""
    
    def __init__(self, database_url: Optional[str] = None, 
                 backup_to_files: bool = True, collection_mode: str = "balanced"):
        """
        Initialize ladder scraper
        
        Args:
            database_url: Database connection string
            backup_to_files: Whether to also save data as JSON files
            collection_mode: "conservative", "balanced", or "aggressive"
        """
        self.db = DatabaseManager(database_url)
        self.backup_to_files = backup_to_files
        self.collection_mode = collection_mode
        
        # Initialize clients
        self.ladder_client = PoeLadderClient(save_to_disk=backup_to_files)
        self.ninja_client = PoeNinjaClient(save_to_disk=backup_to_files)
        self.character_client = PoECharacterClient()
        
        if backup_to_files:
            self.data_manager = DataManager()
        
        # Get current active leagues dynamically
        self.update_monitored_leagues()
        
        self.ladder_types = [
            "league",     # Experience ladder  
            "delve-solo"  # Solo delve ladder
        ]
        
        logger.info("LadderScraper initialized")
    
    def update_monitored_leagues(self):
        """Update the list of leagues to monitor based on current active leagues"""
        try:
            leagues = self.ladder_client.get_leagues()
            if not leagues:
                logger.error("No leagues data available, no leagues will be monitored")
                self.leagues_to_monitor = []
                return
            
            self.leagues_to_monitor = []
            challenge_league_base = None
            
            # First, find the base challenge league (no modifiers)
            for league in leagues:
                league_id = league.get("id", "")
                rules = league.get("rules", [])
                rule_names = [rule.get("name", "") for rule in rules]
                
                # Skip permanent leagues
                if league_id in ["Standard", "Hardcore"]:
                    continue
                
                # Look for base challenge league (no modifiers)
                skip_rules = ["Hardcore", "Solo Self-Found", "Solo", "Ruthless"]
                if not any(skip_rule in rule_names for skip_rule in skip_rules):
                    # This should be the base challenge league
                    challenge_league_base = league_id
                    logger.info(f"Found base challenge league: {challenge_league_base}")
                    break
            
            if not challenge_league_base:
                logger.warning("Could not find base challenge league from API")
                # Check if we have recent challenge league data in database
                try:
                    session = self.db.get_session()
                    from src.storage.database import LadderSnapshot
                    recent_leagues = session.query(LadderSnapshot.league).distinct().all()
                    session.close()
                    
                    # Filter out permanent leagues and get recent challenge leagues
                    challenge_leagues = []
                    for (league,) in recent_leagues:
                        if league not in ["Standard", "Hardcore"]:
                            challenge_leagues.append(league)
                    
                    if challenge_leagues:
                        self.leagues_to_monitor = challenge_leagues
                        logger.info(f"Using recent challenge leagues from database: {challenge_leagues}")
                        return
                    else:
                        logger.warning("No challenge leagues found in database either")
                        
                except Exception as e:
                    logger.error(f"Error checking database for leagues: {e}")
                
                self.leagues_to_monitor = []
                return
            
            # Now find all variants of this challenge league
            league_variants = {
                "softcore": None,
                "softcore_ssf": None, 
                "hardcore": None,
                "hardcore_ssf": None
            }
            
            for league in leagues:
                league_id = league.get("id", "")
                rules = league.get("rules", [])
                rule_names = [rule.get("name", "") for rule in rules]
                
                # Skip if not related to our challenge league or is ruthless
                if challenge_league_base.lower() not in league_id.lower():
                    continue
                if "Ruthless" in rule_names:
                    continue
                
                # Categorize the league variant
                is_hardcore = "Hardcore" in rule_names
                is_ssf = any(rule in rule_names for rule in ["Solo Self-Found", "Solo"])
                
                if is_hardcore and is_ssf:
                    league_variants["hardcore_ssf"] = league_id
                elif is_hardcore:
                    league_variants["hardcore"] = league_id
                elif is_ssf:
                    league_variants["softcore_ssf"] = league_id
                else:
                    league_variants["softcore"] = league_id
            
            # Add challenge league variants that exist (no permanent leagues)
            for variant_type, league_id in league_variants.items():
                if league_id:
                    self.leagues_to_monitor.append(league_id)
                    logger.info(f"Added {variant_type} league: {league_id}")
            
            # Store league categorization for analysis (no permanent leagues)
            self.league_categories = {
                "challenge": {}
            }
            
            if challenge_league_base:
                self.league_categories["challenge"] = {
                    "base_name": challenge_league_base,
                    "variants": league_variants
                }
            
            logger.info(f"Monitoring {len(self.leagues_to_monitor)} leagues: {self.leagues_to_monitor}")
            
        except Exception as e:
            logger.error(f"Failed to update monitored leagues: {e}")
            # No fallback - only monitor challenge leagues
            self.leagues_to_monitor = []
    
    def collect_daily_snapshot(self, league: str, ladder_type: str = "league") -> bool:
        """
        Collect a single ladder snapshot from PoE Official API
        
        Args:
            league: League name
            ladder_type: Type of ladder to scrape ("league" for XP, "delve-solo" for delve)
        
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Starting snapshot collection for {league} ({ladder_type})")
        
        try:
            # Get ladder data from official PoE API
            # Scale entries based on collection mode
            max_entries_by_mode = {
                "conservative": 1000,
                "balanced": 2000, 
                "aggressive": 2500  # 15k total / 6 leagues
            }
            max_entries = max_entries_by_mode.get(self.collection_mode, 1000)
            
            ladder_entries = self.ladder_client.get_full_ladder(
                league_id=league, 
                ladder_type=ladder_type, 
                max_entries=max_entries
            )
            
            if not ladder_entries:
                logger.error(f"Failed to fetch ladder data for {league}")
                return False
            
            characters_count = len(ladder_entries)
            logger.info(f"Retrieved {characters_count} characters from {league} {ladder_type} ladder")
            
            if characters_count == 0:
                logger.warning(f"No characters found in {league} ladder")
                return False
            
            # Convert PoE API format to our database format
            converted_data = self._convert_ladder_data(ladder_entries, league, ladder_type)
            
            # Determine league categorization
            league_category, league_variant, challenge_base = self._categorize_league(league)
            
            # Save to database with categorization
            snapshot_id = self.db.save_ladder_snapshot(
                ladder_data=converted_data,
                league=league,
                ladder_type=ladder_type,
                league_category=league_category,
                league_variant=league_variant,
                challenge_league_base=challenge_base
            )
            
            logger.info(f"Successfully saved snapshot {snapshot_id} for {league}")
            
            # Smart enhancement strategy - prioritize important leagues and reduce attempts
            enhancement_config = self._get_enhancement_config(league, league_variant)
            enhanced_count = self._enhance_characters_with_profiles(
                snapshot_id, converted_data, max_attempts=enhancement_config["max_attempts"]
            )
            
            if enhanced_count > 0:
                logger.info(f"Enhanced {enhanced_count}/{enhancement_config['max_attempts']} characters with profile data")
            
            # Run categorization including EHP calculation
            categorized_count = self.db.categorize_snapshot_characters(snapshot_id)
            if categorized_count > 0:
                logger.info(f"Categorized {categorized_count} characters with EHP calculations")
            
            return True
            
        except Exception as e:
            logger.error(f"Error collecting snapshot for {league}: {e}")
            return False
    
    def _convert_ladder_data(self, ladder_entries: List[Dict], league: str, ladder_type: str) -> Dict:
        """
        Convert PoE Official API ladder format to our internal format
        
        Args:
            ladder_entries: Raw ladder entries from PoE API
            league: League name
            ladder_type: Type of ladder
        
        Returns:
            Converted data in our expected format
        """
        converted_characters = []
        
        for rank, entry in enumerate(ladder_entries, 1):
            character = entry.get("character", {})
            account = entry.get("account", {})
            
            # Extract character data
            char_data = {
                "account": account.get("name", ""),
                "name": character.get("name", ""),
                "level": character.get("level", 0),
                "experience": character.get("experience", 0),
                "class": character.get("class", ""),
                "rank": rank,
                "league": league,
                
                # Delve specific data
                "depth": entry.get("depth", 0) if ladder_type == "delve-solo" else None,
                
                # Additional data that might be available
                "online": entry.get("online", False),
                "dead": entry.get("dead", False),
                
                # Store raw entry for future analysis
                "raw_entry": entry
            }
            
            converted_characters.append(char_data)
        
        return {
            "data": converted_characters,
            "league": league,
            "ladder_type": ladder_type,
            "timestamp": datetime.now().isoformat(),
            "total_entries": len(converted_characters)
        }
    
    def _categorize_league(self, league: str) -> tuple[str, str, str]:
        """
        Categorize a league for analysis purposes
        
        Args:
            league: League name
        
        Returns:
            Tuple of (category, variant, challenge_base)
        """
        # Check permanent leagues
        if league in ["Standard", "Hardcore"]:
            variant = "hardcore" if league == "Hardcore" else "softcore"
            return "permanent", variant, None
        
        # Check challenge leagues
        if hasattr(self, 'league_categories') and 'challenge' in self.league_categories:
            challenge_info = self.league_categories['challenge']
            challenge_base = challenge_info.get('base_name')
            variants = challenge_info.get('variants', {})
            
            for variant_type, league_id in variants.items():
                if league_id == league:
                    return "challenge", variant_type, challenge_base
        
        # Fallback: try to guess from league name
        if "SSF" in league or "Solo Self-Found" in league:
            if "Hardcore" in league or "HC" in league:
                return "challenge", "hardcore_ssf", None
            else:
                return "challenge", "softcore_ssf", None
        elif "Hardcore" in league or "HC" in league:
            return "challenge", "hardcore", None
        else:
            return "challenge", "softcore", None
    
    def get_cross_league_analysis(self, challenge_league_base: str = None, 
                                 days: int = 7) -> Dict[str, Any]:
        """
        Analyze trends across all variants of a challenge league
        
        Args:
            challenge_league_base: Base challenge league name (if None, uses current)
            days: Number of days to analyze
        
        Returns:
            Cross-league analysis data
        """
        try:
            if not challenge_league_base and hasattr(self, 'league_categories'):
                challenge_league_base = self.league_categories.get('challenge', {}).get('base_name')
            
            if not challenge_league_base:
                return {"error": "No challenge league specified"}
            
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get snapshots for all variants of this challenge league
            session = self.db.get_session()
            try:
                from src.storage.database import LadderSnapshot, SnapshotMetrics
                
                snapshots = session.query(LadderSnapshot).filter(
                    LadderSnapshot.challenge_league_base == challenge_league_base,
                    LadderSnapshot.snapshot_date >= start_date,
                    LadderSnapshot.snapshot_date <= end_date,
                    LadderSnapshot.ladder_type == "league"
                ).order_by(LadderSnapshot.snapshot_date.desc()).all()
                
                if not snapshots:
                    return {"error": f"No data found for {challenge_league_base}"}
                
                # Group by league variant
                variant_data = {}
                for snapshot in snapshots:
                    variant = snapshot.league_variant or "unknown"
                    if variant not in variant_data:
                        variant_data[variant] = []
                    variant_data[variant].append(snapshot)
                
                # Analyze each variant
                analysis = {
                    "challenge_league": challenge_league_base,
                    "period_days": days,
                    "variants": {},
                    "comparisons": {}
                }
                
                for variant, variant_snapshots in variant_data.items():
                    if not variant_snapshots:
                        continue
                    
                    latest_snapshot = variant_snapshots[0]  # Most recent
                    
                    # Get metrics for latest snapshot
                    latest_metrics = session.query(SnapshotMetrics).filter_by(
                        snapshot_id=latest_snapshot.id
                    ).first()
                    
                    if latest_metrics:
                        analysis["variants"][variant] = {
                            "league_name": latest_snapshot.league,
                            "total_characters": latest_metrics.total_characters,
                            "avg_level": latest_metrics.avg_level,
                            "max_level": latest_metrics.max_level,
                            "level_100_count": latest_metrics.level_100_count,
                            "class_distribution": latest_metrics.class_distribution,
                            "ascendancy_distribution": latest_metrics.ascendancy_distribution,
                            "latest_snapshot_date": latest_snapshot.snapshot_date.isoformat(),
                            "snapshots_count": len(variant_snapshots)
                        }
                
                # Cross-variant comparisons
                if len(analysis["variants"]) > 1:
                    analysis["comparisons"] = self._calculate_cross_variant_comparisons(analysis["variants"])
                
                return analysis
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error in cross-league analysis: {e}")
            return {"error": str(e)}
    
    def _calculate_cross_variant_comparisons(self, variants: Dict) -> Dict:
        """Calculate comparisons between league variants"""
        comparisons = {
            "population_comparison": {},
            "level_progression": {},
            "class_preferences": {}
        }
        
        # Population comparison
        for variant, data in variants.items():
            comparisons["population_comparison"][variant] = data["total_characters"]
        
        # Level progression comparison
        for variant, data in variants.items():
            comparisons["level_progression"][variant] = {
                "avg_level": data["avg_level"],
                "max_level": data["max_level"],
                "level_100_count": data["level_100_count"],
                "level_100_percentage": (data["level_100_count"] / data["total_characters"] * 100) if data["total_characters"] > 0 else 0
            }
        
        # Class preference comparison (top 3 classes per variant)
        for variant, data in variants.items():
            class_dist = data.get("class_distribution", {})
            total_chars = data["total_characters"]
            
            if class_dist and total_chars > 0:
                top_classes = sorted(class_dist.items(), key=lambda x: x[1], reverse=True)[:3]
                comparisons["class_preferences"][variant] = [
                    {
                        "class": class_name,
                        "count": count,
                        "percentage": (count / total_chars * 100)
                    }
                    for class_name, count in top_classes
                ]
        
        return comparisons
    
    def get_league_variant_summary(self) -> Dict[str, Any]:
        """Get summary of all monitored league variants"""
        if not hasattr(self, 'league_categories'):
            return {"error": "League categories not available"}
        
        summary = {
            "permanent_leagues": [],
            "challenge_league": None,
            "monitored_variants": []
        }
        
        # Add permanent leagues
        for league in self.league_categories.get("permanent", []):
            status = self.get_league_status(league)
            summary["permanent_leagues"].append({
                "name": league,
                "status": status
            })
        
        # Add challenge league info
        challenge_info = self.league_categories.get("challenge", {})
        if challenge_info:
            summary["challenge_league"] = {
                "base_name": challenge_info.get("base_name"),
                "variants": {}
            }
            
            for variant_type, league_id in challenge_info.get("variants", {}).items():
                if league_id:
                    status = self.get_league_status(league_id)
                    summary["challenge_league"]["variants"][variant_type] = {
                        "name": league_id,
                        "status": status
                    }
                    summary["monitored_variants"].append(f"{variant_type}: {league_id}")
        
        return summary
    
    def _get_enhancement_config(self, league: str, league_variant: str) -> Dict:
        """
        Get smart enhancement configuration based on league importance
        
        Args:
            league: League name
            league_variant: League variant type
            
        Returns:
            Configuration with max_attempts and other settings
        """
        # Base configuration by league importance
        base_config = {}
        
        if league_variant == "softcore" and "Standard" not in league:
            # Main challenge league - highest priority for meta analysis
            base_config = {"max_attempts": 200, "priority": "high"}
        elif league_variant == "hardcore" and "Standard" not in league:
            # Challenge HC - good build diversity
            base_config = {"max_attempts": 120, "priority": "medium"}
        elif league_variant == "softcore_ssf" and "Standard" not in league:
            # SSF - interesting self-found builds
            base_config = {"max_attempts": 120, "priority": "medium"}
        elif league_variant == "hardcore_ssf" and "Standard" not in league:
            # HC SSF - most hardcore builds
            base_config = {"max_attempts": 80, "priority": "medium"}
        elif league == "Standard":
            # Standard - established builds
            base_config = {"max_attempts": 120, "priority": "medium"}
        elif league == "Hardcore":
            # HC permanent - proven builds
            base_config = {"max_attempts": 160, "priority": "medium"}
        else:
            # Fallback
            base_config = {"max_attempts": 50, "priority": "low"}
        
        # Collection mode now affects the scale differently
        mode_multipliers = {
            "conservative": 0.1,  # 10% for testing
            "balanced": 0.5,      # 50% for regular collection  
            "aggressive": 1.0     # Full scale for comprehensive analysis
        }
        
        multiplier = mode_multipliers.get(self.collection_mode, 1.0)
        base_config["max_attempts"] = max(1, int(base_config["max_attempts"] * multiplier))
        
        return base_config
    
    def _enhance_characters_with_profiles(self, snapshot_id: int, ladder_data: Dict, 
                                         max_attempts: int = 50) -> int:
        """
        Enhance top characters with profile data from public accounts
        
        Args:
            snapshot_id: Database snapshot ID
            ladder_data: Ladder data containing character info
            max_attempts: Maximum number of characters to attempt (top X)
        
        Returns:
            Number of characters successfully enhanced
        """
        enhanced_count = 0
        characters_data = ladder_data.get('data', [])[:max_attempts]
        
        logger.info(f"Attempting to enhance {len(characters_data)} characters with profile data")
        
        session = self.db.get_session()
        try:
            for i, char_data in enumerate(characters_data):
                account_name = char_data.get('account', '')
                character_name = char_data.get('name', '')
                
                if not account_name or not character_name:
                    continue
                
                # Use full account name (API requires discriminator)
                
                logger.info(f"Fetching profile data for {character_name} ({account_name}) [{i+1}/{len(characters_data)}]")
                
                try:
                    # Attempt to get character build data
                    build_data = self.character_client.analyze_character_build(
                        account_name, character_name
                    )
                    
                    # Find the character in database
                    from src.storage.database import Character
                    char_record = session.query(Character).filter_by(
                        snapshot_id=snapshot_id,
                        account=account_name,
                        name=character_name
                    ).first()
                    
                    if char_record:
                        # Update character with profile data
                        if build_data.get('error'):
                            # Profile is private or error occurred
                            char_record.profile_public = False
                            logger.info(f"  ❌ {build_data['error']}")
                        else:
                            # Successfully got profile data
                            char_record.profile_public = True
                            char_record.enhanced_skills = build_data.get('skills', [])
                            char_record.enhanced_uniques = build_data.get('uniques', [])
                            
                            # Store main skill setup
                            if build_data.get('main_skill_links'):
                                char_record.main_skill_setup = build_data['main_skill_links'][0]
                                
                                # Update legacy fields for compatibility
                                main_skills = [g['name'] for g in build_data['main_skill_links'][0].get('gems', []) 
                                             if not g.get('support', True)]
                                if main_skills:
                                    char_record.main_skill = main_skills[0]
                            
                            char_record.skills = build_data.get('skills', [])
                            char_record.unique_items = build_data.get('uniques', [])
                            
                            # Store defensive stats if available
                            if build_data.get('defensive_stats'):
                                def_stats = build_data['defensive_stats']
                                char_record.life = def_stats.get('life', char_record.life)
                                char_record.energy_shield = def_stats.get('energy_shield', char_record.energy_shield)
                                char_record.armour = def_stats.get('armour')
                                char_record.evasion = def_stats.get('evasion')
                                char_record.fire_resistance = def_stats.get('fire_resistance')
                                char_record.cold_resistance = def_stats.get('cold_resistance')
                                char_record.lightning_resistance = def_stats.get('lightning_resistance')
                                char_record.chaos_resistance = def_stats.get('chaos_resistance')
                                char_record.block_chance = def_stats.get('block_chance')
                                char_record.spell_block_chance = def_stats.get('spell_block_chance')
                            
                            enhanced_count += 1
                            logger.info(f"  ✅ Enhanced with {len(build_data.get('skills', []))} skills, {len(build_data.get('uniques', []))} uniques")
                        
                        char_record.profile_fetched_at = datetime.utcnow()
                        session.commit()
                    
                    # Rate limiting is handled by the centralized rate limiter
                    
                except Exception as e:
                    logger.error(f"Error enhancing {character_name}: {e}")
                    continue
            
            logger.info(f"Profile enhancement complete: {enhanced_count}/{len(characters_data)} successful")
            return enhanced_count
            
        except Exception as e:
            logger.error(f"Error during profile enhancement: {e}")
            session.rollback()
            return enhanced_count
        finally:
            session.close()
    
    def get_enhanced_character_analysis(self, league: str, min_enhanced: int = 10) -> Dict[str, Any]:
        """
        Analyze characters with enhanced profile data
        
        Args:
            league: League name
            min_enhanced: Minimum number of enhanced characters needed for analysis
        
        Returns:
            Analysis of enhanced character data
        """
        session = self.db.get_session()
        try:
            from src.storage.database import Character
            
            # Get characters with profile data
            enhanced_chars = session.query(Character).filter(
                Character.league == league,
                Character.profile_public == True,
                Character.enhanced_skills.isnot(None)
            ).order_by(Character.rank).all()
            
            if len(enhanced_chars) < min_enhanced:
                return {
                    "error": f"Only {len(enhanced_chars)} enhanced characters available, need at least {min_enhanced}"
                }
            
            # Analyze skills
            skill_usage = {}
            unique_usage = {}
            main_skill_usage = {}
            
            for char in enhanced_chars:
                # Count skill usage
                for skill in char.enhanced_skills or []:
                    skill_usage[skill] = skill_usage.get(skill, 0) + 1
                
                # Count unique items
                for unique in char.enhanced_uniques or []:
                    if unique and len(unique.strip()) > 0:  # Filter empty names
                        unique_usage[unique] = unique_usage.get(unique, 0) + 1
                
                # Count main skills
                if char.main_skill:
                    main_skill_usage[char.main_skill] = main_skill_usage.get(char.main_skill, 0) + 1
            
            # Build analysis results
            analysis = {
                "league": league,
                "enhanced_characters": len(enhanced_chars),
                "total_characters_in_league": session.query(Character).filter_by(league=league).count(),
                "enhancement_rate": len(enhanced_chars) / session.query(Character).filter_by(league=league).count() * 100,
                
                "skill_analysis": {
                    "total_unique_skills": len(skill_usage),
                    "most_popular_skills": sorted(skill_usage.items(), key=lambda x: x[1], reverse=True)[:10]
                },
                
                "unique_item_analysis": {
                    "total_unique_items": len(unique_usage),
                    "most_popular_uniques": sorted(unique_usage.items(), key=lambda x: x[1], reverse=True)[:10]
                },
                
                "main_skill_analysis": {
                    "total_main_skills": len(main_skill_usage),
                    "most_popular_main_skills": sorted(main_skill_usage.items(), key=lambda x: x[1], reverse=True)[:10]
                },
                
                "sample_builds": []
            }
            
            # Add sample builds (top 5 with most complete data)
            for char in enhanced_chars[:5]:
                build_sample = {
                    "character_name": char.name,
                    "rank": char.rank,
                    "class": char.class_name,
                    "level": char.level,
                    "main_skill": char.main_skill,
                    "skills": char.enhanced_skills[:10],  # Limit for display
                    "unique_items": char.enhanced_uniques[:5],  # Top 5 uniques
                    "main_skill_links": char.main_skill_setup.get('links') if char.main_skill_setup else None
                }
                analysis["sample_builds"].append(build_sample)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in enhanced character analysis: {e}")
            return {"error": str(e)}
        finally:
            session.close()
    
    def collect_all_snapshots(self) -> Dict[str, Dict[str, bool]]:
        """
        Collect snapshots for all configured leagues and ladder types
        
        Returns:
            Dictionary with results for each league/ladder type combination
        """
        results = {}
        total_requests = len(self.leagues_to_monitor) * len(self.ladder_types)
        current_request = 0
        
        logger.info(f"Starting collection of {total_requests} snapshots")
        
        for league in self.leagues_to_monitor:
            results[league] = {}
            
            for ladder_type in self.ladder_types:
                current_request += 1
                logger.info(f"Progress: {current_request}/{total_requests}")
                
                success = self.collect_daily_snapshot(league, ladder_type)
                results[league][ladder_type] = success
                
                # Add delay between requests to be respectful
                if current_request < total_requests:
                    time.sleep(2)
        
        # Summary
        successful = sum(1 for league_results in results.values() 
                        for success in league_results.values() if success)
        logger.info(f"Collection complete: {successful}/{total_requests} successful")
        
        return results
    
    def get_league_status(self, league: str) -> Dict[str, Any]:
        """Get current status for a league"""
        try:
            # Try "league" ladder type first (what scraper uses), then fall back to "exp"
            summary = self.db.get_league_summary(league, "league")
            if "error" in summary:
                summary = self.db.get_league_summary(league, "exp")
            
            # Add freshness information
            if 'latest_snapshot_date' in summary:
                latest_date = datetime.fromisoformat(summary['latest_snapshot_date'])
                hours_since = (datetime.utcnow() - latest_date).total_seconds() / 3600
                summary['hours_since_last_snapshot'] = round(hours_since, 1)
                summary['is_fresh'] = hours_since < 25  # Less than 25 hours old
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting league status for {league}: {e}")
            return {"error": str(e)}
    
    def get_all_leagues_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status for all monitored leagues"""
        status = {}
        for league in self.leagues_to_monitor:
            status[league] = self.get_league_status(league)
        return status
    
    def check_if_snapshot_needed(self, league: str, ladder_type: str = "exp") -> bool:
        """
        Check if a new snapshot is needed for a league
        
        Args:
            league: League name
            ladder_type: Type of ladder
        
        Returns:
            True if snapshot is needed, False otherwise
        """
        try:
            latest_snapshot = self.db.get_latest_snapshot(league, ladder_type)
            
            if not latest_snapshot:
                logger.info(f"No previous snapshot found for {league} ({ladder_type})")
                return True
            
            # Check if last snapshot is older than 23 hours
            hours_since = (datetime.utcnow() - latest_snapshot.snapshot_date).total_seconds() / 3600
            
            if hours_since >= 23:
                logger.info(f"Last snapshot for {league} is {hours_since:.1f} hours old, needs update")
                return True
            else:
                logger.info(f"Recent snapshot exists for {league}, {hours_since:.1f} hours old")
                return False
                
        except Exception as e:
            logger.error(f"Error checking snapshot status for {league}: {e}")
            return True  # Default to collecting if we can't check
    
    def collect_needed_snapshots(self) -> Dict[str, Dict[str, bool]]:
        """
        Collect snapshots only for leagues that need them
        
        Returns:
            Dictionary with results for each league/ladder type that was processed
        """
        results = {}
        
        for league in self.leagues_to_monitor:
            league_results = {}
            
            for ladder_type in self.ladder_types:
                if self.check_if_snapshot_needed(league, ladder_type):
                    success = self.collect_daily_snapshot(league, ladder_type)
                    league_results[ladder_type] = success
                    
                    # Add delay between requests
                    time.sleep(2)
                else:
                    logger.info(f"Skipping {league} ({ladder_type}) - recent snapshot exists")
            
            if league_results:
                results[league] = league_results
        
        return results
    
    def cleanup_old_data(self, keep_days: int = 90) -> int:
        """
        Clean up old snapshots from database
        
        Args:
            keep_days: Number of days of data to keep
        
        Returns:
            Number of snapshots deleted
        """
        logger.info(f"Starting cleanup of snapshots older than {keep_days} days")
        try:
            deleted_count = self.db.cleanup_old_snapshots(keep_days)
            logger.info(f"Cleanup complete: removed {deleted_count} old snapshots")
            return deleted_count
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0
    
    def get_character_tracking(self, account: str, character: str) -> List[Dict[str, Any]]:
        """
        Get progression tracking for a specific character
        
        Args:
            account: Account name
            character: Character name
        
        Returns:
            List of character snapshots over time
        """
        try:
            progression = self.db.get_character_progression(account, character)
            
            result = []
            for char in progression:
                result.append({
                    "date": char.snapshot_date.isoformat(),
                    "level": char.level,
                    "experience": char.experience,
                    "rank": char.rank,
                    "league": char.league,
                    "life": char.life,
                    "energy_shield": char.energy_shield,
                    "dps": char.dps,
                    "delve_depth": char.delve_solo_depth or char.delve_depth,
                    "main_skill": char.main_skill,
                    "skills": char.skills,
                    "unique_items": char.unique_items
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting character tracking: {e}")
            return []
    
    def get_trending_builds(self, league: str, days: int = 7) -> Dict[str, Any]:
        """
        Analyze trending builds over the last N days
        
        Args:
            league: League name
            days: Number of days to analyze
        
        Returns:
            Dictionary with trending analysis
        """
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            snapshots = self.db.get_snapshots_by_date_range(
                league=league,
                start_date=start_date,
                end_date=end_date
            )
            
            if len(snapshots) < 2:
                return {"error": "Not enough data for trend analysis"}
            
            # Get metrics for first and last snapshot
            session = self.db.get_session()
            try:
                from src.storage.database import SnapshotMetrics
                
                first_metrics = session.query(SnapshotMetrics).filter_by(
                    snapshot_id=snapshots[-1].id  # Oldest (end of list after desc order)
                ).first()
                
                latest_metrics = session.query(SnapshotMetrics).filter_by(
                    snapshot_id=snapshots[0].id   # Newest (start of list)
                ).first()
                
                if not first_metrics or not latest_metrics:
                    return {"error": "Metrics not available for trend analysis"}
                
                # Calculate trends
                trends = {
                    "period_days": days,
                    "total_snapshots": len(snapshots),
                    "character_count_change": latest_metrics.total_characters - first_metrics.total_characters,
                    "avg_level_change": latest_metrics.avg_level - first_metrics.avg_level,
                    "class_trends": self._calculate_class_trends(first_metrics, latest_metrics),
                    "skill_trends": self._calculate_skill_trends(first_metrics, latest_metrics)
                }
                
                return trends
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error calculating trends: {e}")
            return {"error": str(e)}
    
    def _calculate_class_trends(self, first_metrics, latest_metrics) -> Dict[str, float]:
        """Calculate class popularity trends"""
        if not first_metrics.class_distribution or not latest_metrics.class_distribution:
            return {}
        
        trends = {}
        all_classes = set(first_metrics.class_distribution.keys()) | set(latest_metrics.class_distribution.keys())
        
        for class_name in all_classes:
            first_count = first_metrics.class_distribution.get(class_name, 0)
            latest_count = latest_metrics.class_distribution.get(class_name, 0)
            
            first_pct = (first_count / first_metrics.total_characters) * 100
            latest_pct = (latest_count / latest_metrics.total_characters) * 100
            
            trends[class_name] = latest_pct - first_pct
        
        return trends
    
    def _calculate_skill_trends(self, first_metrics, latest_metrics) -> Dict[str, float]:
        """Calculate skill popularity trends"""
        if not first_metrics.skill_popularity or not latest_metrics.skill_popularity:
            return {}
        
        trends = {}
        
        # Get top 20 skills from latest snapshot
        top_skills = sorted(latest_metrics.skill_popularity.items(), 
                           key=lambda x: x[1], reverse=True)[:20]
        
        for skill_name, latest_count in top_skills:
            first_count = first_metrics.skill_popularity.get(skill_name, 0)
            
            first_pct = (first_count / first_metrics.total_characters) * 100
            latest_pct = (latest_count / latest_metrics.total_characters) * 100
            
            trends[skill_name] = latest_pct - first_pct
        
        return trends


# Command-line interface for manual execution
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='PoE Ladder Scraper')
    parser.add_argument('--league', type=str, help='Specific league to scrape')
    parser.add_argument('--ladder-type', type=str, default='exp', choices=['exp', 'depthsolo'])
    parser.add_argument('--force', action='store_true', help='Force collection even if recent snapshot exists')
    parser.add_argument('--status', action='store_true', help='Show status of all leagues')
    parser.add_argument('--cleanup', type=int, metavar='DAYS', help='Clean up snapshots older than N days')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scraper = LadderScraper()
    
    if args.status:
        status = scraper.get_all_leagues_status()
        print("\nLeague Status:")
        print("=" * 50)
        for league, data in status.items():
            if 'error' in data:
                print(f"{league}: ERROR - {data['error']}")
            else:
                print(f"{league}:")
                print(f"  Total snapshots: {data.get('total_snapshots', 'N/A')}")
                print(f"  Latest: {data.get('latest_snapshot_date', 'N/A')}")
                print(f"  Hours since last: {data.get('hours_since_last_snapshot', 'N/A')}")
                print(f"  Is fresh: {data.get('is_fresh', 'N/A')}")
                print(f"  Characters: {data.get('latest_character_count', 'N/A')}")
                print()
    
    elif args.cleanup:
        deleted = scraper.cleanup_old_data(args.cleanup)
        print(f"Cleaned up {deleted} old snapshots")
    
    elif args.league:
        if args.force:
            success = scraper.collect_daily_snapshot(args.league, args.ladder_type)
        else:
            success = scraper.collect_needed_snapshots() if args.league in scraper.leagues_to_monitor else False
        print(f"Snapshot collection for {args.league}: {'SUCCESS' if success else 'FAILED'}")
    
    else:
        # Collect all needed snapshots
        results = scraper.collect_needed_snapshots()
        
        print("\nCollection Results:")
        print("=" * 30)
        for league, league_results in results.items():
            for ladder_type, success in league_results.items():
                status = "SUCCESS" if success else "FAILED"
                print(f"{league} ({ladder_type}): {status}")
        
        if not results:
            print("No snapshots needed - all data is fresh")