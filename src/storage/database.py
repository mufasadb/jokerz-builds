"""
Database models and connection management for ladder snapshots
"""

import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Boolean, JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class LadderSnapshot(Base):
    """Table for storing daily ladder snapshots"""
    __tablename__ = 'ladder_snapshots'
    
    id = Column(Integer, primary_key=True)
    league = Column(String(50), nullable=False, index=True)
    snapshot_date = Column(DateTime, nullable=False, index=True)
    ladder_type = Column(String(20), nullable=False)  # 'league', 'delve-solo', etc.
    total_characters = Column(Integer, nullable=False)
    data_hash = Column(String(64), nullable=False)  # SHA256 hash for deduplication
    raw_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # League categorization for analysis
    league_category = Column(String(20), nullable=True, index=True)  # 'permanent', 'challenge'
    league_variant = Column(String(20), nullable=True, index=True)   # 'softcore', 'hardcore', 'softcore_ssf', 'hardcore_ssf'
    challenge_league_base = Column(String(50), nullable=True, index=True)  # Base challenge league name
    
    def __repr__(self):
        return f"<LadderSnapshot(league='{self.league}', date='{self.snapshot_date}', type='{self.ladder_type}')>"


class RequestLog(Base):
    """Table for tracking API requests"""
    __tablename__ = 'request_logs'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    api_type = Column(String(50), nullable=False, index=True)  # 'ladder', 'character', 'poe_ninja'
    endpoint = Column(String(200), nullable=True)
    success = Column(Boolean, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    error_message = Column(String(500), nullable=True)
    
    # Optional tracking data
    league = Column(String(50), nullable=True)
    character_name = Column(String(100), nullable=True)
    account_name = Column(String(100), nullable=True)
    
    # Request source
    source = Column(String(50), nullable=False, default='system', index=True)  # 'system', 'discord_bot', 'web_ui'
    source_user = Column(String(100), nullable=True)  # Discord user ID or web session


class Character(Base):
    """Table for storing individual character data from ladder"""
    __tablename__ = 'characters'
    
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, nullable=False, index=True)  # Foreign key to LadderSnapshot
    account = Column(String(100), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    level = Column(Integer, nullable=False)
    experience = Column(Integer, nullable=True)
    class_name = Column(String(50), nullable=False, index=True)
    ascendancy = Column(String(50), nullable=True, index=True)
    
    # Combat stats
    life = Column(Integer, nullable=True)
    energy_shield = Column(Integer, nullable=True)
    dps = Column(Integer, nullable=True)
    
    # Delve stats
    delve_depth = Column(Integer, nullable=True)
    delve_solo_depth = Column(Integer, nullable=True)
    
    # Skills and gear
    main_skill = Column(String(100), nullable=True)
    skills = Column(JSON, nullable=True)  # Array of skill names
    unique_items = Column(JSON, nullable=True)  # Array of unique item names
    
    # Meta
    rank = Column(Integer, nullable=True)
    league = Column(String(50), nullable=False, index=True)
    snapshot_date = Column(DateTime, nullable=False, index=True)
    raw_data = Column(JSON, nullable=False)
    
    # Enhanced profile data (for public profiles)
    profile_public = Column(Boolean, nullable=True, default=None)  # True/False/None(unknown)
    enhanced_skills = Column(JSON, nullable=True)  # List of active skills
    enhanced_uniques = Column(JSON, nullable=True)  # List of unique items
    main_skill_setup = Column(JSON, nullable=True)  # Main skill link setup
    profile_fetched_at = Column(DateTime, nullable=True)  # When profile data was fetched
    
    # Build categorization data
    primary_damage_type = Column(String(50), nullable=True, index=True)  # fire, physical, cold, etc
    secondary_damage_types = Column(JSON, nullable=True)  # Array of secondary damage types
    damage_over_time = Column(Boolean, nullable=True, default=False)  # DoT build flag
    
    skill_delivery = Column(String(50), nullable=True, index=True)  # melee, self_cast, totem, etc
    skill_mechanics = Column(JSON, nullable=True)  # Array of mechanics (channelling, aoe, etc)
    
    defense_style = Column(String(50), nullable=True, index=True)  # tanky, squishy, balanced
    defense_layers = Column(JSON, nullable=True)  # Array of defense types
    
    cost_tier = Column(String(50), nullable=True, index=True)  # budget, moderate, expensive, luxury
    cost_factors = Column(JSON, nullable=True)  # Array of cost factors
    
    # Defensive stats for EHP calculation
    armour = Column(Integer, nullable=True)
    evasion = Column(Integer, nullable=True)
    fire_resistance = Column(Float, nullable=True)
    cold_resistance = Column(Float, nullable=True)
    lightning_resistance = Column(Float, nullable=True)
    chaos_resistance = Column(Float, nullable=True)
    block_chance = Column(Float, nullable=True)
    spell_block_chance = Column(Float, nullable=True)
    
    # EHP metrics
    ehp_physical = Column(Float, nullable=True)
    ehp_fire = Column(Float, nullable=True)
    ehp_cold = Column(Float, nullable=True)
    ehp_lightning = Column(Float, nullable=True)
    ehp_chaos = Column(Float, nullable=True)
    ehp_weighted = Column(Float, nullable=True)
    tankiness_rating = Column(String(50), nullable=True, index=True)  # Extremely Tanky, Very Tanky, etc
    
    # URL references for build viewing
    profile_url = Column(String(500), nullable=True)  # Path of Exile profile URL
    pob_url = Column(String(500), nullable=True)  # Path of Building URL if available
    ladder_url = Column(String(500), nullable=True)  # Direct ladder link
    
    # Categorization metadata
    categorization_confidence = Column(JSON, nullable=True)  # Confidence scores for each category
    categorized_at = Column(DateTime, nullable=True)  # When categorization was performed
    
    def __repr__(self):
        return f"<Character(name='{self.name}', account='{self.account}', level={self.level})>"


class SnapshotMetrics(Base):
    """Table for storing aggregate metrics per snapshot"""
    __tablename__ = 'snapshot_metrics'
    
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, nullable=False, index=True)
    league = Column(String(50), nullable=False, index=True)
    snapshot_date = Column(DateTime, nullable=False, index=True)
    
    # Aggregate stats
    total_characters = Column(Integer, nullable=False)
    avg_level = Column(Float, nullable=True)
    max_level = Column(Integer, nullable=True)
    level_100_count = Column(Integer, nullable=False, default=0)
    
    # Class distribution (JSON object)
    class_distribution = Column(JSON, nullable=True)
    
    # Skill popularity (JSON object)
    skill_popularity = Column(JSON, nullable=True)
    
    # Unique item usage (JSON object)
    unique_usage = Column(JSON, nullable=True)
    
    # Ascendancy distribution (JSON object)
    ascendancy_distribution = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class TaskState(Base):
    """Table for persisting task state across restarts"""
    __tablename__ = 'task_states'
    
    id = Column(Integer, primary_key=True)
    task_id = Column(String(100), unique=True, nullable=False, index=True)
    status = Column(String(20), nullable=False)  # pending, running, completed, failed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Task configuration
    leagues = Column(JSON, nullable=True)  # List of leagues to process
    enhance_profiles = Column(Boolean, default=True)
    categorize_builds = Column(Boolean, default=True)
    collection_mode = Column(String(20), default="balanced")  # conservative, balanced, aggressive
    
    # Progress tracking
    current_step = Column(String(200), default="")
    total_steps = Column(Integer, default=0)
    completed_steps = Column(Integer, default=0)
    current_league = Column(String(50), default="")
    current_operation = Column(String(100), default="")
    
    # Results tracking
    characters_collected = Column(Integer, default=0)
    characters_enhanced = Column(Integer, default=0)
    characters_categorized = Column(Integer, default=0)
    leagues_completed = Column(JSON, nullable=True)  # List of completed leagues
    
    # Error tracking
    error_message = Column(String(1000), nullable=True)
    warnings = Column(JSON, nullable=True)  # List of warning messages
    
    # Metadata
    last_heartbeat = Column(DateTime, nullable=True)  # For detecting stalled tasks


class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager
        
        Args:
            database_url: Database connection string. If None, uses SQLite with default path
        """
        if database_url is None:
            # Use a more portable default path for tests and development
            default_path = os.path.join(os.getcwd(), 'data', 'ladder_snapshots.db')
            db_path = os.getenv('DB_PATH', default_path)
            # Ensure directory exists
            try:
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
            except PermissionError:
                # Fallback to a temporary path if we can't create the directory
                import tempfile
                temp_dir = tempfile.gettempdir()
                db_path = os.path.join(temp_dir, 'ladder_snapshots.db')
                logger.warning(f"Permission denied for {db_path}, using temporary path: {db_path}")
            database_url = f"sqlite:///{db_path}"
        
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)
        logger.info(f"Database initialized at {database_url}")
    
    def get_session(self) -> Session:
        """Get a database session"""
        return self.SessionLocal()
    
    def save_ladder_snapshot(self, ladder_data: Dict[str, Any], league: str, 
                           ladder_type: str = "league", league_category: str = None,
                           league_variant: str = None, challenge_league_base: str = None) -> int:
        """
        Save a complete ladder snapshot
        
        Args:
            ladder_data: Raw ladder data from API
            league: League name
            ladder_type: Type of ladder ('exp', 'depthsolo', etc.)
        
        Returns:
            ID of created snapshot
        """
        import hashlib
        import json
        
        session = self.get_session()
        try:
            # Calculate hash for deduplication
            data_str = json.dumps(ladder_data, sort_keys=True)
            data_hash = hashlib.sha256(data_str.encode()).hexdigest()
            
            # Check if we already have this exact data
            existing = session.query(LadderSnapshot).filter_by(
                league=league,
                ladder_type=ladder_type,
                data_hash=data_hash
            ).first()
            
            if existing:
                logger.info(f"Snapshot already exists with hash {data_hash[:8]}...")
                return existing.id
            
            # Create snapshot record
            snapshot = LadderSnapshot(
                league=league,
                snapshot_date=datetime.utcnow(),
                ladder_type=ladder_type,
                total_characters=len(ladder_data.get('data', [])),
                data_hash=data_hash,
                raw_data=ladder_data,
                league_category=league_category,
                league_variant=league_variant,
                challenge_league_base=challenge_league_base
            )
            
            session.add(snapshot)
            session.flush()  # Get the ID
            
            # Save individual characters
            characters_data = ladder_data.get('data', [])
            characters = []
            
            for rank, char_data in enumerate(characters_data, 1):
                # Generate URLs for the character
                account_name = char_data.get('account', '')
                character_name = char_data.get('name', '')
                
                profile_url = None
                ladder_url = None
                pob_url = None  # PoB URLs need to be manually provided by users
                
                if account_name and character_name:
                    # Path of Exile profile URL
                    from urllib.parse import quote
                    profile_url = f"https://www.pathofexile.com/account/view-profile/{quote(account_name)}/characters?characterName={quote(character_name)}"
                    
                    # Ladder URL based on ladder type
                    if ladder_type == "league":
                        ladder_url = f"https://www.pathofexile.com/ladders/league/{quote(league)}"
                    elif ladder_type == "delve-solo":
                        ladder_url = f"https://www.pathofexile.com/ladders/delve-solo/{quote(league)}"
                
                character = Character(
                    snapshot_id=snapshot.id,
                    account=account_name,
                    name=character_name,
                    level=char_data.get('level', 0),
                    experience=char_data.get('experience'),
                    class_name=char_data.get('class', ''),
                    ascendancy=char_data.get('ascendancy'),
                    life=char_data.get('life'),
                    energy_shield=char_data.get('energyShield'),
                    dps=char_data.get('dps'),
                    delve_depth=char_data.get('depth', {}).get('default') if isinstance(char_data.get('depth'), dict) else None,
                    delve_solo_depth=char_data.get('depth', {}).get('solo') if isinstance(char_data.get('depth'), dict) else char_data.get('depth'),
                    main_skill=char_data.get('mainSkill'),
                    skills=char_data.get('skills', []),
                    unique_items=char_data.get('uniques', []),
                    rank=rank,
                    league=league,
                    snapshot_date=snapshot.snapshot_date,
                    raw_data=char_data,
                    profile_url=profile_url,
                    ladder_url=ladder_url,
                    pob_url=pob_url
                )
                characters.append(character)
            
            session.add_all(characters)
            
            # Calculate and save metrics
            metrics = self._calculate_snapshot_metrics(snapshot.id, characters, session)
            session.add(metrics)
            
            session.commit()
            logger.info(f"Saved ladder snapshot {snapshot.id} with {len(characters)} characters")
            return snapshot.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving ladder snapshot: {e}")
            raise
        finally:
            session.close()
    
    def _calculate_snapshot_metrics(self, snapshot_id: int, characters: List[Character], 
                                  session: Session) -> SnapshotMetrics:
        """Calculate aggregate metrics for a snapshot"""
        
        if not characters:
            return SnapshotMetrics(snapshot_id=snapshot_id, total_characters=0)
        
        # Basic stats
        levels = [c.level for c in characters if c.level]
        avg_level = sum(levels) / len(levels) if levels else 0
        max_level = max(levels) if levels else 0
        level_100_count = sum(1 for level in levels if level == 100)
        
        # Class distribution
        class_dist = {}
        for char in characters:
            if char.class_name:
                class_dist[char.class_name] = class_dist.get(char.class_name, 0) + 1
        
        # Ascendancy distribution
        ascendancy_dist = {}
        for char in characters:
            if char.ascendancy:
                ascendancy_dist[char.ascendancy] = ascendancy_dist.get(char.ascendancy, 0) + 1
        
        # Skill popularity
        skill_pop = {}
        for char in characters:
            if char.skills:
                for skill in char.skills:
                    skill_pop[skill] = skill_pop.get(skill, 0) + 1
        
        # Unique item usage
        unique_usage = {}
        for char in characters:
            if char.unique_items:
                for item in char.unique_items:
                    unique_usage[item] = unique_usage.get(item, 0) + 1
        
        return SnapshotMetrics(
            snapshot_id=snapshot_id,
            league=characters[0].league,
            snapshot_date=characters[0].snapshot_date,
            total_characters=len(characters),
            avg_level=avg_level,
            max_level=max_level,
            level_100_count=level_100_count,
            class_distribution=class_dist,
            skill_popularity=skill_pop,
            unique_usage=unique_usage,
            ascendancy_distribution=ascendancy_dist
        )
    
    def get_latest_snapshot(self, league: str, ladder_type: str = "exp") -> Optional[LadderSnapshot]:
        """Get the most recent snapshot for a league"""
        session = self.get_session()
        try:
            snapshot = session.query(LadderSnapshot).filter_by(
                league=league,
                ladder_type=ladder_type
            ).order_by(LadderSnapshot.snapshot_date.desc()).first()
            return snapshot
        finally:
            session.close()
    
    def get_snapshots_by_date_range(self, league: str, start_date: datetime, 
                                   end_date: datetime, ladder_type: str = "exp") -> List[LadderSnapshot]:
        """Get snapshots within a date range"""
        session = self.get_session()
        try:
            snapshots = session.query(LadderSnapshot).filter(
                LadderSnapshot.league == league,
                LadderSnapshot.ladder_type == ladder_type,
                LadderSnapshot.snapshot_date >= start_date,
                LadderSnapshot.snapshot_date <= end_date
            ).order_by(LadderSnapshot.snapshot_date.desc()).all()
            return snapshots
        finally:
            session.close()
    
    def get_character_progression(self, account: str, character_name: str) -> List[Character]:
        """Get progression history for a specific character"""
        session = self.get_session()
        try:
            characters = session.query(Character).filter_by(
                account=account,
                name=character_name
            ).order_by(Character.snapshot_date.asc()).all()
            return characters
        finally:
            session.close()
    
    def get_league_summary(self, league: str, ladder_type: str = "exp") -> Dict[str, Any]:
        """Get summary statistics for a league"""
        session = self.get_session()
        try:
            # Get latest snapshot using the same session
            latest_snapshot = session.query(LadderSnapshot).filter_by(
                league=league,
                ladder_type=ladder_type
            ).order_by(LadderSnapshot.snapshot_date.desc()).first()
            
            if not latest_snapshot:
                return {"error": "No snapshots found for league"}
            
            # Get metrics for latest snapshot
            metrics = session.query(SnapshotMetrics).filter_by(
                snapshot_id=latest_snapshot.id
            ).first()
            
            # Get total snapshots count
            total_snapshots = session.query(LadderSnapshot).filter_by(league=league).count()
            
            # Get date range
            first_snapshot = session.query(LadderSnapshot).filter_by(
                league=league
            ).order_by(LadderSnapshot.snapshot_date.asc()).first()
            
            summary = {
                "league": league,
                "total_snapshots": total_snapshots,
                "first_snapshot_date": first_snapshot.snapshot_date.isoformat() if first_snapshot else None,
                "latest_snapshot_date": latest_snapshot.snapshot_date.isoformat(),
                "latest_character_count": latest_snapshot.total_characters,
            }
            
            if metrics:
                summary.update({
                    "avg_level": metrics.avg_level,
                    "max_level": metrics.max_level,
                    "level_100_count": metrics.level_100_count,
                    "top_classes": sorted(metrics.class_distribution.items(), 
                                        key=lambda x: x[1], reverse=True)[:5] if metrics.class_distribution else [],
                    "top_skills": sorted(metrics.skill_popularity.items(), 
                                       key=lambda x: x[1], reverse=True)[:5] if metrics.skill_popularity else []
                })
            
            return summary
            
        finally:
            session.close()
    
    def cleanup_old_snapshots(self, keep_days: int = 90) -> int:
        """Remove snapshots older than specified days"""
        from datetime import datetime, timedelta
        
        session = self.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=keep_days)
            
            # Get old snapshot IDs
            old_snapshots = session.query(LadderSnapshot.id).filter(
                LadderSnapshot.snapshot_date < cutoff_date
            ).all()
            old_snapshot_ids = [s.id for s in old_snapshots]
            
            if not old_snapshot_ids:
                return 0
            
            # Delete related records
            session.query(Character).filter(
                Character.snapshot_id.in_(old_snapshot_ids)
            ).delete(synchronize_session=False)
            
            session.query(SnapshotMetrics).filter(
                SnapshotMetrics.snapshot_id.in_(old_snapshot_ids)
            ).delete(synchronize_session=False)
            
            # Delete snapshots
            deleted_count = session.query(LadderSnapshot).filter(
                LadderSnapshot.id.in_(old_snapshot_ids)
            ).delete(synchronize_session=False)
            
            session.commit()
            logger.info(f"Cleaned up {deleted_count} old snapshots")
            return deleted_count
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning up old snapshots: {e}")
            raise
        finally:
            session.close()
    
    def update_character_categorization(self, character_id: int, categories) -> bool:
        """
        Update a character's build categorization data
        
        Args:
            character_id: Character database ID
            categories: BuildCategories object from build_categorizer
            
        Returns:
            True if successful, False otherwise
        """
        from src.analysis.build_categorizer import BuildCategories
        
        session = self.get_session()
        try:
            character = session.query(Character).filter_by(id=character_id).first()
            if not character:
                logger.warning(f"Character {character_id} not found for categorization update")
                return False
            
            # Update categorization fields
            character.primary_damage_type = categories.primary_damage_type
            character.secondary_damage_types = categories.secondary_damage_types
            character.damage_over_time = categories.damage_over_time
            character.skill_delivery = categories.skill_delivery
            character.skill_mechanics = categories.skill_mechanics
            character.defense_style = categories.defense_style
            character.defense_layers = categories.defense_layers
            character.cost_tier = categories.cost_tier
            character.cost_factors = categories.cost_factors
            character.categorization_confidence = categories.confidence_scores
            character.categorized_at = datetime.utcnow()
            
            session.commit()
            logger.debug(f"Updated categorization for character {character.name}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating character categorization: {e}")
            return False
        finally:
            session.close()
    
    def get_characters_for_categorization(self, league: str = None, 
                                        uncategorized_only: bool = True,
                                        limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get characters that need categorization
        
        Args:
            league: Specific league to process (None for all)
            uncategorized_only: Only return characters without categorization
            limit: Maximum number of characters to return
            
        Returns:
            List of character data dictionaries ready for categorization
        """
        session = self.get_session()
        try:
            query = session.query(Character)
            
            if league:
                query = query.filter(Character.league == league)
            
            if uncategorized_only:
                query = query.filter(Character.categorized_at.is_(None))
            
            # Prioritize characters with enhanced profile data
            query = query.order_by(
                Character.profile_public.desc().nullslast(),
                Character.rank.asc()
            ).limit(limit)
            
            characters = query.all()
            
            # Convert to character data format expected by categorizer
            result = []
            for char in characters:
                char_data = {
                    'id': char.id,  # Include ID for updates
                    'account': char.account,
                    'name': char.name,
                    'level': char.level,
                    'class': char.class_name,
                    'ascendancy': char.ascendancy,
                    'life': char.life,
                    'energy_shield': char.energy_shield,
                    'dps': char.dps,
                    'main_skill': char.main_skill,
                    'skills': char.skills,
                    'unique_items': char.unique_items,
                    'enhanced_skills': char.enhanced_skills,
                    'enhanced_uniques': char.enhanced_uniques,
                    'main_skill_setup': char.main_skill_setup,
                    'league': char.league,
                    'rank': char.rank
                }
                result.append(char_data)
            
            logger.info(f"Retrieved {len(result)} characters for categorization")
            return result
            
        except Exception as e:
            logger.error(f"Error getting characters for categorization: {e}")
            return []
        finally:
            session.close()
    
    def get_categorization_stats(self, league: str = None) -> Dict[str, Any]:
        """
        Get statistics about build categorizations
        
        Args:
            league: Specific league to analyze (None for all)
            
        Returns:
            Dictionary with categorization statistics
        """
        session = self.get_session()
        try:
            query = session.query(Character)
            if league:
                query = query.filter(Character.league == league)
            
            total_characters = query.count()
            categorized_characters = query.filter(Character.categorized_at.isnot(None)).count()
            
            # Get distribution by damage type
            damage_type_dist = {}
            damage_results = session.query(Character.primary_damage_type, 
                                         session.query(Character).filter(
                                             Character.primary_damage_type == Character.primary_damage_type
                                         ).count()).group_by(Character.primary_damage_type).all()
            
            for damage_type, count in damage_results:
                if damage_type:
                    damage_type_dist[damage_type] = count
            
            # Get distribution by skill delivery
            delivery_dist = {}
            delivery_results = session.query(Character.skill_delivery).filter(
                Character.skill_delivery.isnot(None)
            ).all()
            
            for result in delivery_results:
                delivery = result[0]
                delivery_dist[delivery] = delivery_dist.get(delivery, 0) + 1
            
            # Get distribution by defense style
            defense_dist = {}
            defense_results = session.query(Character.defense_style).filter(
                Character.defense_style.isnot(None)
            ).all()
            
            for result in defense_results:
                defense = result[0]
                defense_dist[defense] = defense_dist.get(defense, 0) + 1
            
            # Get distribution by cost tier
            cost_dist = {}
            cost_results = session.query(Character.cost_tier).filter(
                Character.cost_tier.isnot(None)
            ).all()
            
            for result in cost_results:
                cost = result[0]
                cost_dist[cost] = cost_dist.get(cost, 0) + 1
            
            return {
                'total_characters': total_characters,
                'categorized_characters': categorized_characters,
                'categorization_rate': (categorized_characters / total_characters * 100) if total_characters > 0 else 0,
                'damage_type_distribution': damage_type_dist,
                'skill_delivery_distribution': delivery_dist,
                'defense_style_distribution': defense_dist,
                'cost_tier_distribution': cost_dist,
                'league': league or 'All Leagues'
            }
            
        except Exception as e:
            logger.error(f"Error getting categorization stats: {e}")
            return {'error': str(e)}
        finally:
            session.close()
    
    def search_builds_by_category(self, damage_type: str = None, skill_delivery: str = None,
                                defense_style: str = None, cost_tier: str = None,
                                tankiness_rating: str = None, min_ehp: float = None,
                                league: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search for builds by categorization criteria
        
        Args:
            damage_type: Primary damage type filter
            skill_delivery: Skill delivery method filter
            defense_style: Defense style filter
            cost_tier: Cost tier filter
            league: League filter
            limit: Maximum results
            
        Returns:
            List of matching character data
        """
        session = self.get_session()
        try:
            query = session.query(Character)
            
            # Apply filters
            if damage_type:
                query = query.filter(Character.primary_damage_type == damage_type)
            if skill_delivery:
                query = query.filter(Character.skill_delivery == skill_delivery)
            if defense_style:
                query = query.filter(Character.defense_style == defense_style)
            if cost_tier:
                query = query.filter(Character.cost_tier == cost_tier)
            if tankiness_rating:
                query = query.filter(Character.tankiness_rating == tankiness_rating)
            if min_ehp:
                query = query.filter(Character.ehp_weighted >= min_ehp)
            if league:
                query = query.filter(Character.league == league)
            
            # Order by rank and limit results
            characters = query.order_by(Character.rank.asc()).limit(limit).all()
            
            # Convert to result format
            results = []
            for char in characters:
                from src.analysis.build_categorizer import BuildCategories
                
                # Reconstruct BuildCategories for summary
                categories = BuildCategories(
                    primary_damage_type=char.primary_damage_type,
                    secondary_damage_types=char.secondary_damage_types or [],
                    damage_over_time=char.damage_over_time or False,
                    skill_delivery=char.skill_delivery,
                    skill_mechanics=char.skill_mechanics or [],
                    defense_style=char.defense_style,
                    defense_layers=char.defense_layers or [],
                    cost_tier=char.cost_tier,
                    cost_factors=char.cost_factors or [],
                    confidence_scores=char.categorization_confidence or {},
                    tankiness_rating=char.tankiness_rating
                )
                
                from src.analysis.build_categorizer import build_categorizer
                build_summary = build_categorizer.get_build_summary(categories)
                
                results.append({
                    'character_name': char.name,
                    'account': char.account,
                    'level': char.level,
                    'class': char.class_name,
                    'ascendancy': char.ascendancy,
                    'rank': char.rank,
                    'league': char.league,
                    'main_skill': char.main_skill,
                    'build_summary': build_summary,
                    'categories': {
                        'damage_type': char.primary_damage_type,
                        'skill_delivery': char.skill_delivery,
                        'defense_style': char.defense_style,
                        'cost_tier': char.cost_tier,
                        'damage_over_time': char.damage_over_time,
                        'tankiness_rating': char.tankiness_rating
                    },
                    'ehp': {
                        'weighted': char.ehp_weighted,
                        'physical': char.ehp_physical,
                        'fire': char.ehp_fire,
                        'cold': char.ehp_cold,
                        'lightning': char.ehp_lightning,
                        'chaos': char.ehp_chaos
                    },
                    'unique_items': char.enhanced_uniques or char.unique_items,
                    'skills': char.enhanced_skills or char.skills
                })
            
            logger.info(f"Found {len(results)} builds matching criteria")
            return results
            
        except Exception as e:
            logger.error(f"Error searching builds by category: {e}")
            return []
        finally:
            session.close()
    
    def categorize_snapshot_characters(self, snapshot_id: int) -> int:
        """
        Categorize all characters in a snapshot including EHP calculation
        
        Args:
            snapshot_id: ID of the snapshot to categorize
            
        Returns:
            Number of characters categorized
        """
        try:
            from src.analysis.build_categorizer import build_categorizer
        except ImportError as e:
            logger.warning(f"Build categorizer not available: {e}. Skipping categorization.")
            return 0
        
        session = self.get_session()
        try:
            # Get all characters from this snapshot
            characters = session.query(Character).filter_by(
                snapshot_id=snapshot_id
            ).all()
            
            categorized_count = 0
            
            for char in characters:
                try:
                    # Prepare character data for categorization
                    char_data = {
                        'name': char.name,
                        'account': char.account,
                        'level': char.level,
                        'life': char.life or 0,
                        'energy_shield': char.energy_shield or 0,
                        'main_skill': char.main_skill,
                        'enhanced_skills': char.enhanced_skills,
                        'skills': char.skills,
                        'enhanced_uniques': char.enhanced_uniques,
                        'unique_items': char.unique_items,
                        'main_skill_setup': char.main_skill_setup,
                        # Defensive stats
                        'armour': char.armour or 0,
                        'evasion': char.evasion or 0,
                        'fire_resistance': char.fire_resistance or 0,
                        'cold_resistance': char.cold_resistance or 0,
                        'lightning_resistance': char.lightning_resistance or 0,
                        'chaos_resistance': char.chaos_resistance or 0,
                        'block_chance': char.block_chance or 0,
                        'spell_block_chance': char.spell_block_chance or 0,
                        'physical_damage_reduction': 0,  # Not stored yet
                        'fortify': False,  # Not stored yet
                        'endurance_charges': 0  # Not stored yet
                    }
                    
                    # Categorize the build
                    categories = build_categorizer.categorize_build(char_data)
                    
                    # Update character record with categorization
                    char.primary_damage_type = categories.primary_damage_type
                    char.secondary_damage_types = categories.secondary_damage_types
                    char.damage_over_time = categories.damage_over_time
                    char.skill_delivery = categories.skill_delivery
                    char.skill_mechanics = categories.skill_mechanics
                    char.defense_style = categories.defense_style
                    char.defense_layers = categories.defense_layers
                    char.cost_tier = categories.cost_tier
                    char.cost_factors = categories.cost_factors
                    char.categorization_confidence = categories.confidence_scores
                    char.categorized_at = datetime.utcnow()
                    
                    # Store EHP data if calculated
                    if categories.ehp_result:
                        char.ehp_physical = categories.ehp_result.physical_ehp
                        char.ehp_fire = categories.ehp_result.fire_ehp
                        char.ehp_cold = categories.ehp_result.cold_ehp
                        char.ehp_lightning = categories.ehp_result.lightning_ehp
                        char.ehp_chaos = categories.ehp_result.chaos_ehp
                        char.ehp_weighted = categories.ehp_result.weighted_ehp
                        char.tankiness_rating = categories.tankiness_rating
                    
                    categorized_count += 1
                    
                except Exception as e:
                    logger.error(f"Error categorizing character {char.name}: {e}")
                    continue
            
            # Commit all changes
            session.commit()
            logger.info(f"Categorized {categorized_count}/{len(characters)} characters in snapshot {snapshot_id}")
            
            return categorized_count
            
        except Exception as e:
            logger.error(f"Error categorizing snapshot: {e}")
            session.rollback()
            return 0
        finally:
            session.close()
    
    def log_request(self, api_type: str, success: bool, endpoint: str = None,
                   response_time_ms: int = None, error_message: str = None,
                   league: str = None, character_name: str = None,
                   account_name: str = None, source: str = 'system',
                   source_user: str = None) -> None:
        """Log an API request"""
        session = self.get_session()
        try:
            log_entry = RequestLog(
                api_type=api_type,
                endpoint=endpoint,
                success=success,
                response_time_ms=response_time_ms,
                error_message=error_message,
                league=league,
                character_name=character_name,
                account_name=account_name,
                source=source,
                source_user=source_user
            )
            session.add(log_entry)
            session.commit()
        except Exception as e:
            logger.error(f"Error logging request: {e}")
            session.rollback()
        finally:
            session.close()
    
    def get_request_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get request statistics for the dashboard"""
        session = self.get_session()
        try:
            from sqlalchemy import func, case
            
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            # Overall stats
            total_requests = session.query(func.count(RequestLog.id)).filter(
                RequestLog.timestamp >= cutoff_time
            ).scalar()
            
            successful_requests = session.query(func.count(RequestLog.id)).filter(
                RequestLog.timestamp >= cutoff_time,
                RequestLog.success == True
            ).scalar()
            
            # By API type
            by_api_type = session.query(
                RequestLog.api_type,
                func.count(RequestLog.id).label('count'),
                func.sum(case([(RequestLog.success == True, 1)], else_=0)).label('successful')
            ).filter(
                RequestLog.timestamp >= cutoff_time
            ).group_by(RequestLog.api_type).all()
            
            # By source
            by_source = session.query(
                RequestLog.source,
                func.count(RequestLog.id).label('count')
            ).filter(
                RequestLog.timestamp >= cutoff_time
            ).group_by(RequestLog.source).all()
            
            # Recent errors
            recent_errors = session.query(RequestLog).filter(
                RequestLog.timestamp >= cutoff_time,
                RequestLog.success == False
            ).order_by(RequestLog.timestamp.desc()).limit(10).all()
            
            # Last successful pull by API type
            last_successful = {}
            for api_type in ['ladder', 'character', 'poe_ninja']:
                last_req = session.query(RequestLog).filter(
                    RequestLog.api_type == api_type,
                    RequestLog.success == True
                ).order_by(RequestLog.timestamp.desc()).first()
                
                if last_req:
                    last_successful[api_type] = {
                        'timestamp': last_req.timestamp.isoformat(),
                        'endpoint': last_req.endpoint,
                        'league': last_req.league,
                        'character_name': last_req.character_name,
                        'account_name': last_req.account_name
                    }
            
            return {
                'total_requests': total_requests,
                'successful_requests': successful_requests,
                'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0,
                'by_api_type': [
                    {
                        'api_type': api_type,
                        'count': count,
                        'successful': successful,
                        'success_rate': (successful / count * 100) if count > 0 else 0
                    }
                    for api_type, count, successful in by_api_type
                ],
                'by_source': [
                    {'source': source, 'count': count}
                    for source, count in by_source
                ],
                'recent_errors': [
                    {
                        'timestamp': err.timestamp.isoformat(),
                        'api_type': err.api_type,
                        'endpoint': err.endpoint,
                        'error_message': err.error_message
                    }
                    for err in recent_errors
                ],
                'last_successful': last_successful
            }
            
        except Exception as e:
            logger.error(f"Error getting request stats: {e}")
            return {}
        finally:
            session.close()
    
    def get_hourly_request_counts(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get hourly request counts for charting"""
        session = self.get_session()
        try:
            from sqlalchemy import func
            
            cutoff_time = datetime.utcnow() - timedelta(days=days)
            
            # SQLite doesn't have date_trunc, so we'll use strftime
            hourly_counts = session.query(
                func.strftime('%Y-%m-%d %H:00:00', RequestLog.timestamp).label('hour'),
                RequestLog.api_type,
                func.count(RequestLog.id).label('count')
            ).filter(
                RequestLog.timestamp >= cutoff_time
            ).group_by(
                'hour',
                RequestLog.api_type
            ).order_by('hour').all()
            
            # Format for charting
            result = []
            for hour, api_type, count in hourly_counts:
                result.append({
                    'hour': hour,
                    'api_type': api_type,
                    'count': count
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting hourly counts: {e}")
            return []
        finally:
            session.close()
    
    def get_character_stats(self) -> Dict[str, Any]:
        """Get character statistics for dashboard"""
        session = self.get_session()
        try:
            total_characters = session.query(func.count(Character.id)).scalar()
            
            # Characters with profiles
            profiles_public = session.query(func.count(Character.id)).filter(
                Character.profile_public == True
            ).scalar()
            
            # Characters by league
            by_league = session.query(
                Character.league,
                func.count(Character.id).label('count')
            ).group_by(Character.league).all()
            
            # Recent snapshots
            recent_snapshots = session.query(
                LadderSnapshot.league,
                LadderSnapshot.snapshot_date,
                LadderSnapshot.total_characters
            ).order_by(LadderSnapshot.snapshot_date.desc()).limit(10).all()
            
            return {
                'total_characters': total_characters,
                'profiles_public': profiles_public,
                'profile_rate': (profiles_public / total_characters * 100) if total_characters > 0 else 0,
                'by_league': [
                    {'league': league, 'count': count}
                    for league, count in by_league
                ],
                'recent_snapshots': [
                    {
                        'league': snap.league,
                        'date': snap.snapshot_date.isoformat(),
                        'characters': snap.total_characters
                    }
                    for snap in recent_snapshots
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting character stats: {e}")
            return {}
        finally:
            session.close()