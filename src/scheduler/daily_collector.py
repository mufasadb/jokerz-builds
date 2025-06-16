"""
Daily data collection scheduler for ladder snapshots
"""

import logging
import schedule
import time
import signal
import sys
from datetime import datetime, timedelta
from typing import Optional
import os
from src.scraper.ladder_scraper import LadderScraper

logger = logging.getLogger(__name__)


class DailyCollector:
    """Handles scheduled collection of ladder snapshots"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize daily collector
        
        Args:
            database_url: Database connection string
        """
        self.scraper = LadderScraper(database_url)
        self.running = False
        
        # Configuration from environment variables
        self.collection_time = os.getenv('COLLECTION_TIME', '02:00')  # Default 2 AM UTC
        self.cleanup_days = int(os.getenv('CLEANUP_DAYS', '90'))
        self.cleanup_time = os.getenv('CLEANUP_TIME', '03:00')  # Default 3 AM UTC
        
        logger.info(f"DailyCollector initialized - Collection: {self.collection_time}, Cleanup: {self.cleanup_time}")
    
    def collect_snapshots_job(self):
        """Job function for collecting daily snapshots"""
        logger.info("Starting scheduled snapshot collection")
        start_time = datetime.now()
        
        try:
            # Collect needed snapshots
            results = self.scraper.collect_needed_snapshots()
            
            # Log results
            successful = sum(1 for league_results in results.values() 
                           for success in league_results.values() if success)
            total = sum(len(league_results) for league_results in results.values())
            
            duration = datetime.now() - start_time
            logger.info(f"Snapshot collection completed: {successful}/{total} successful in {duration}")
            
            # Send notification if configured
            self._send_notification(f"Ladder snapshot collection: {successful}/{total} successful")
            
        except Exception as e:
            logger.error(f"Error during scheduled collection: {e}")
            self._send_notification(f"Ladder snapshot collection FAILED: {str(e)}")
    
    def cleanup_job(self):
        """Job function for cleaning up old data"""
        logger.info("Starting scheduled cleanup")
        
        try:
            deleted_count = self.scraper.cleanup_old_data(self.cleanup_days)
            logger.info(f"Cleanup completed: removed {deleted_count} old snapshots")
            
            if deleted_count > 0:
                self._send_notification(f"Cleaned up {deleted_count} old ladder snapshots")
                
        except Exception as e:
            logger.error(f"Error during scheduled cleanup: {e}")
    
    def _send_notification(self, message: str):
        """
        Send notification (webhook, email, etc.)
        Configure via environment variables
        """
        webhook_url = os.getenv('WEBHOOK_URL')
        if webhook_url:
            try:
                import requests
                payload = {
                    "text": f"[Joker Builds] {message}",
                    "timestamp": datetime.now().isoformat()
                }
                requests.post(webhook_url, json=payload, timeout=10)
                logger.info("Notification sent successfully")
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
    
    def setup_schedule(self):
        """Set up the collection and cleanup schedules"""
        # Daily snapshot collection
        schedule.every().day.at(self.collection_time).do(self.collect_snapshots_job)
        logger.info(f"Scheduled daily collection at {self.collection_time} UTC")
        
        # Weekly cleanup (run on Sundays)
        schedule.every().sunday.at(self.cleanup_time).do(self.cleanup_job)
        logger.info(f"Scheduled weekly cleanup on Sundays at {self.cleanup_time} UTC")
        
        # Also run cleanup immediately if it's been more than 7 days since last cleanup
        # (This handles the case where the container was restarted)
        self._check_and_run_overdue_cleanup()
    
    def _check_and_run_overdue_cleanup(self):
        """Check if cleanup is overdue and run it if needed"""
        try:
            # Get latest snapshot to check when we last had activity
            status = self.scraper.get_all_leagues_status()
            
            # Find the oldest "fresh" snapshot across all leagues
            oldest_fresh_hours = 0
            for league_status in status.values():
                if 'hours_since_last_snapshot' in league_status:
                    oldest_fresh_hours = max(oldest_fresh_hours, league_status['hours_since_last_snapshot'])
            
            # If we haven't collected data in over 7 days, run cleanup
            if oldest_fresh_hours > (7 * 24):
                logger.info("Running overdue cleanup check")
                self.cleanup_job()
                
        except Exception as e:
            logger.error(f"Error checking overdue cleanup: {e}")
    
    def run_once(self):
        """Run collection once (for testing or manual execution)"""
        logger.info("Running one-time collection")
        self.collect_snapshots_job()
    
    def start(self):
        """Start the scheduler"""
        self.setup_schedule()
        self.running = True
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("Daily collector started - waiting for scheduled tasks")
        
        # Show next scheduled runs
        for job in schedule.jobs:
            logger.info(f"Next run: {job.next_run} - {job.job_func.__name__}")
        
        # Run scheduler loop
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        logger.info("Daily collector stopped")
    
    def get_status(self) -> dict:
        """Get current status of the collector"""
        next_runs = []
        for job in schedule.jobs:
            next_runs.append({
                "job": job.job_func.__name__,
                "next_run": job.next_run.isoformat() if job.next_run else None,
                "interval": str(job.interval),
                "unit": job.unit
            })
        
        return {
            "running": self.running,
            "collection_time": self.collection_time,
            "cleanup_time": self.cleanup_time,
            "cleanup_days": self.cleanup_days,
            "scheduled_jobs": next_runs,
            "leagues_status": self.scraper.get_all_leagues_status()
        }


def main():
    """Main entry point for running the daily collector"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PoE Ladder Daily Collector')
    parser.add_argument('--once', action='store_true', help='Run collection once and exit')
    parser.add_argument('--status', action='store_true', help='Show collector status')
    parser.add_argument('--cleanup', action='store_true', help='Run cleanup and exit')
    
    args = parser.parse_args()
    
    # Set up logging
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # Create logs directory if it doesn't exist
    logs_dir = '/app/logs' if os.path.exists('/app') else './logs'
    os.makedirs(logs_dir, exist_ok=True)
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    # Add file handler for collector logs
    collector_log_path = os.path.join(logs_dir, 'collector.log')
    handlers.append(logging.FileHandler(collector_log_path, mode='a'))
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
    
    logger.info("=" * 60)
    logger.info("JOKER BUILDS COLLECTOR STARTING UP")
    logger.info("=" * 60)
    logger.info(f"Log level: {log_level}")
    logger.info(f"Collector log path: {collector_log_path}")
    logger.info(f"Environment: {os.getenv('FLASK_ENV', 'development')}")
    
    collector = DailyCollector()
    
    if args.status:
        status = collector.get_status()
        print("Daily Collector Status:")
        print("=" * 50)
        print(f"Running: {status['running']}")
        print(f"Collection Time: {status['collection_time']} UTC")
        print(f"Cleanup Time: {status['cleanup_time']} UTC")
        print(f"Cleanup Retention: {status['cleanup_days']} days")
        print("\nScheduled Jobs:")
        for job in status['scheduled_jobs']:
            print(f"  {job['job']}: {job['next_run']}")
        print("\nLeagues Status:")
        for league, data in status['leagues_status'].items():
            if 'error' in data:
                print(f"  {league}: ERROR")
            else:
                hours = data.get('hours_since_last_snapshot', 'N/A')
                fresh = data.get('is_fresh', False)
                print(f"  {league}: {hours} hours ago ({'FRESH' if fresh else 'STALE'})")
    
    elif args.cleanup:
        collector.cleanup_job()
        print("Cleanup completed")
    
    elif args.once:
        collector.run_once()
        print("One-time collection completed")
    
    else:
        # Run the scheduler
        print("Starting daily collector...")
        print("Press Ctrl+C to stop")
        try:
            collector.start()
        except KeyboardInterrupt:
            print("\nShutting down...")
            collector.stop()


if __name__ == "__main__":
    main()