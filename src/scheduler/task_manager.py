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
    """Manages background scraping tasks"""
    
    def __init__(self):
        self.tasks: Dict[str, TaskProgress] = {}
        self.task_queue = queue.Queue()
        self.worker_thread = None
        self.is_running = False
        self.current_task: Optional[TaskProgress] = None
        self._lock = threading.Lock()
        
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
                             categorize_builds: bool = True) -> str:
        """
        Submit a new collection task
        
        Args:
            leagues: List of leagues to collect (None for all)
            enhance_profiles: Whether to enhance with profile data
            categorize_builds: Whether to categorize builds
            
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
        
        # Add to queue
        self.task_queue.put({
            'task_id': task_id,
            'type': 'collection',
            'leagues': leagues,
            'enhance_profiles': enhance_profiles,
            'categorize_builds': categorize_builds
        })
        
        # Start worker if not running
        if not self.is_running:
            self.start_worker()
        
        logger.info(f"Submitted collection task {task_id} for leagues: {leagues}")
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
                task_info = self.task_queue.get(timeout=1)
                
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
        
        scraper = LadderScraper()
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


# Global task manager instance
task_manager = TaskManager()