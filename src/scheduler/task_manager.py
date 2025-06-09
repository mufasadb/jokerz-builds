"""
Background task manager for scraping operations
Handles manual scraping triggers and progress tracking
"""

import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import queue

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskProgress:
    """Progress information for a scraping task"""
    task_id: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Progress details
    current_step: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    current_league: str = ""
    current_operation: str = ""
    
    # Results
    characters_collected: int = 0
    characters_enhanced: int = 0
    characters_categorized: int = 0
    leagues_completed: List[str] = field(default_factory=list)
    
    # Error tracking
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    
    @property
    def progress_percentage(self) -> float:
        if self.total_steps == 0:
            return 0.0
        return (self.completed_steps / self.total_steps) * 100
    
    @property
    def elapsed_time(self) -> Optional[float]:
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.utcnow()
        return (end_time - self.started_at).total_seconds()


class TaskManager:
    """Manages background scraping tasks with persistent state"""
    
    def __init__(self):
        self.tasks: Dict[str, TaskProgress] = {}
        self.task_queue = queue.Queue()
        self.worker_thread = None
        self.is_running = False
        self.current_task: Optional[TaskProgress] = None
        self._lock = threading.Lock()
        
        # Initialize database connection for persistence
        from src.storage.database import DatabaseManager
        self.db = DatabaseManager()
        
        # Restore any pending tasks from database on startup
        self._restore_tasks_from_database()
        
    def start_worker(self):
        """Start the background worker thread"""
        if self.worker_thread and self.worker_thread.is_alive():
            return
            
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("Task manager worker started")
    
    def stop_worker(self):
        """Stop the background worker thread"""
        self.is_running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
        logger.info("Task manager worker stopped")
    
    def submit_collection_task(self, leagues: List[str] = None, 
                             enhance_profiles: bool = True,
                             categorize_builds: bool = True,
                             collection_mode: str = "balanced") -> str:
        """
        Submit a new collection task
        
        Args:
            leagues: List of leagues to collect (None for all)
            enhance_profiles: Whether to enhance with profile data
            categorize_builds: Whether to categorize builds
            collection_mode: Collection aggressiveness (conservative/balanced/aggressive)
            
        Returns:
            Task ID
        """
        task_id = f"collection_{int(time.time())}"
        
        task = TaskProgress(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        # Calculate total steps
        from src.scraper.ladder_scraper import LadderScraper
        scraper = LadderScraper()
        
        if leagues is None:
            leagues = scraper.leagues_to_monitor
        
        total_steps = len(leagues)
        if enhance_profiles:
            total_steps += len(leagues)  # Profile enhancement per league
        if categorize_builds:
            total_steps += len(leagues)  # Categorization per league
        
        task.total_steps = total_steps
        task.current_step = "Queued for processing"
        
        with self._lock:
            self.tasks[task_id] = task
        
        # Persist task to database
        self._persist_task_to_database(
            task, collection_mode, leagues, enhance_profiles, categorize_builds
        )
        
        # Add to queue
        task_info = {
            'task_id': task_id,
            'type': 'collection',
            'leagues': leagues,
            'enhance_profiles': enhance_profiles,
            'categorize_builds': categorize_builds,
            'collection_mode': collection_mode
        }
        self.task_queue.put((task_id, task_info))
        
        # Start worker if not running
        if not self.is_running:
            self.start_worker()
        
        logger.info(f"Submitted collection task {task_id} for leagues: {leagues} (mode: {collection_mode})")
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[TaskProgress]:
        """Get status of a specific task"""
        with self._lock:
            return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[TaskProgress]:
        """Get all tasks, sorted by creation time"""
        with self._lock:
            return sorted(self.tasks.values(), key=lambda t: t.created_at, reverse=True)
    
    def get_active_task(self) -> Optional[TaskProgress]:
        """Get currently running task"""
        return self.current_task
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task"""
        with self._lock:
            task = self.tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.utcnow()
                return True
        return False
    
    def _worker_loop(self):
        """Main worker loop"""
        while self.is_running:
            try:
                # Get next task (with timeout to allow checking is_running)
                task_data = self.task_queue.get(timeout=1)
                
                # Handle both old and new queue formats
                if isinstance(task_data, tuple):
                    task_id, task_info = task_data
                else:
                    # Old format compatibility
                    task_info = task_data
                    task_id = task_info['task_id']
                with self._lock:
                    task = self.tasks.get(task_id)
                
                if not task or task.status != TaskStatus.PENDING:
                    continue
                
                # Start task
                self.current_task = task
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.utcnow()
                
                try:
                    if task_info['type'] == 'collection':
                        self._run_collection_task(task, task_info)
                        task.status = TaskStatus.COMPLETED
                    
                except Exception as e:
                    logger.error(f"Task {task_id} failed: {e}")
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                
                finally:
                    task.completed_at = datetime.utcnow()
                    self.current_task = None
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker loop error: {e}")
    
    def _run_collection_task(self, task: TaskProgress, task_info: Dict):
        """Execute a collection task"""
        from src.scraper.ladder_scraper import LadderScraper
        from src.storage.database import DatabaseManager
        
        leagues = task_info['leagues']
        enhance_profiles = task_info['enhance_profiles']
        categorize_builds = task_info['categorize_builds']
        collection_mode = task_info.get('collection_mode', 'balanced')
        
        scraper = LadderScraper(collection_mode=collection_mode)
        db = DatabaseManager()
        
        task.current_step = "Initializing collection"
        
        for i, league in enumerate(leagues):
            if not self.is_running:  # Check for shutdown
                break
                
            task.current_league = league
            task.current_step = f"Collecting ladder data for {league}"
            task.completed_steps = i
            
            try:
                # Collect ladder snapshot
                task.current_operation = f"Fetching ladder data for {league}"
                success = scraper.collect_daily_snapshot(league)
                
                if success:
                    # Get the latest snapshot ID for this league
                    latest_snapshot = db.get_latest_snapshot(league)
                    if latest_snapshot:
                        snapshot_id = latest_snapshot.id
                        
                        # Count characters collected
                        session = db.get_session()
                        try:
                            from src.storage.database import Character
                            char_count = session.query(Character).filter_by(
                                snapshot_id=snapshot_id
                            ).count()
                            task.characters_collected += char_count
                        finally:
                            session.close()
                        
                        # Enhancement step
                        if enhance_profiles:
                            task.current_operation = f"Enhancing profiles for {league}"
                            # Profile enhancement is already done in collect_daily_snapshot
                            
                        # Categorization step
                        if categorize_builds:
                            task.current_operation = f"Categorizing builds for {league}"
                            categorized = db.categorize_snapshot_characters(snapshot_id)
                            task.characters_categorized += categorized
                    
                    task.leagues_completed.append(league)
                    
                else:
                    task.warnings.append(f"Failed to collect data for league: {league}")
                
            except Exception as e:
                logger.error(f"Error processing league {league}: {e}")
                task.warnings.append(f"Error in {league}: {str(e)}")
        
        task.current_step = "Collection completed"
        task.completed_steps = task.total_steps
    
    def _restore_tasks_from_database(self):
        """Restore pending/running tasks from database on startup"""
        try:
            from src.storage.database import TaskState
            session = self.db.get_session()
            
            # Find tasks that were running when the system stopped
            pending_tasks = session.query(TaskState).filter(
                TaskState.status.in_(['pending', 'running'])
            ).all()
            
            for db_task in pending_tasks:
                # Check if task is stale (no heartbeat for 5+ minutes)
                if (db_task.last_heartbeat and 
                    (datetime.utcnow() - db_task.last_heartbeat).total_seconds() > 300):
                    logger.info(f"Marking stale task {db_task.task_id} as failed")
                    db_task.status = 'failed'
                    db_task.error_message = 'Task was interrupted by system restart'
                    db_task.completed_at = datetime.utcnow()
                    continue
                
                # Restore task to memory
                task = self._db_task_to_progress(db_task)
                self.tasks[task.task_id] = task
                
                # Re-queue pending tasks
                if db_task.status == 'pending':
                    task_info = {
                        'type': 'collection',
                        'leagues': db_task.leagues or [],
                        'enhance_profiles': db_task.enhance_profiles,
                        'categorize_builds': db_task.categorize_builds,
                        'collection_mode': db_task.collection_mode
                    }
                    self.task_queue.put((task.task_id, task_info))
                    logger.info(f"Restored pending task {task.task_id}")
            
            session.commit()
            session.close()
            
        except Exception as e:
            logger.error(f"Error restoring tasks from database: {e}")
    
    def _persist_task_to_database(self, task: TaskProgress, 
                                  collection_mode: str = "balanced",
                                  leagues: List[str] = None,
                                  enhance_profiles: bool = True,
                                  categorize_builds: bool = True):
        """Save task state to database"""
        try:
            from src.storage.database import TaskState
            session = self.db.get_session()
            
            # Check if task already exists
            db_task = session.query(TaskState).filter(
                TaskState.task_id == task.task_id
            ).first()
            
            if not db_task:
                db_task = TaskState(task_id=task.task_id)
                session.add(db_task)
            
            # Update task state
            db_task.status = task.status.value
            db_task.started_at = task.started_at
            db_task.completed_at = task.completed_at
            db_task.leagues = leagues or []
            db_task.enhance_profiles = enhance_profiles
            db_task.categorize_builds = categorize_builds
            db_task.collection_mode = collection_mode
            db_task.current_step = task.current_step
            db_task.total_steps = task.total_steps
            db_task.completed_steps = task.completed_steps
            db_task.current_league = task.current_league
            db_task.current_operation = task.current_operation
            db_task.characters_collected = task.characters_collected
            db_task.characters_enhanced = task.characters_enhanced
            db_task.characters_categorized = task.characters_categorized
            db_task.leagues_completed = task.leagues_completed
            db_task.error_message = task.error_message
            db_task.warnings = task.warnings
            db_task.last_heartbeat = datetime.utcnow()
            
            session.commit()
            session.close()
            
        except Exception as e:
            logger.error(f"Error persisting task {task.task_id}: {e}")
    
    def _db_task_to_progress(self, db_task) -> TaskProgress:
        """Convert database task to TaskProgress object"""
        return TaskProgress(
            task_id=db_task.task_id,
            status=TaskStatus(db_task.status),
            created_at=db_task.created_at,
            started_at=db_task.started_at,
            completed_at=db_task.completed_at,
            current_step=db_task.current_step or "",
            total_steps=db_task.total_steps or 0,
            completed_steps=db_task.completed_steps or 0,
            current_league=db_task.current_league or "",
            current_operation=db_task.current_operation or "",
            characters_collected=db_task.characters_collected or 0,
            characters_enhanced=db_task.characters_enhanced or 0,
            characters_categorized=db_task.characters_categorized or 0,
            leagues_completed=db_task.leagues_completed or [],
            error_message=db_task.error_message,
            warnings=db_task.warnings or []
        )


# Global task manager instance
task_manager = TaskManager()