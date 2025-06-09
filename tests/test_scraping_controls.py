"""
Test the scraping controls and task manager functionality
"""

import time
import requests
import json
from src.scheduler.task_manager import task_manager, TaskStatus


def test_task_manager():
    """Test the task manager functionality"""
    print("=== Testing Task Manager ===")
    
    # Start the task manager
    task_manager.start_worker()
    
    # Submit a test task
    task_id = task_manager.submit_collection_task(
        leagues=['Standard'],
        enhance_profiles=False,  # Skip profile enhancement for quick test
        categorize_builds=False  # Skip categorization for quick test
    )
    
    print(f"Submitted task: {task_id}")
    
    # Monitor task progress
    for i in range(10):
        task = task_manager.get_task_status(task_id)
        if task:
            print(f"Task {task_id} status: {task.status.value}")
            print(f"  Progress: {task.progress_percentage:.1f}%")
            print(f"  Current step: {task.current_step}")
            print(f"  Current league: {task.current_league}")
            
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                break
        
        time.sleep(5)
    
    # Get final status
    final_task = task_manager.get_task_status(task_id)
    if final_task:
        print(f"\nFinal status: {final_task.status.value}")
        print(f"Characters collected: {final_task.characters_collected}")
        if final_task.error_message:
            print(f"Error: {final_task.error_message}")
    
    task_manager.stop_worker()


def test_api_endpoints():
    """Test the API endpoints (requires dashboard to be running)"""
    print("\n=== Testing API Endpoints ===")
    
    base_url = "http://localhost:5000"
    
    try:
        # Test scraping status endpoint
        response = requests.get(f"{base_url}/api/scraping/status")
        if response.status_code == 200:
            data = response.json()
            print(f"Available leagues: {data['available_leagues']}")
            print(f"Queue size: {data['queue_size']}")
            
            if data['active_task']:
                print(f"Active task: {data['active_task']['task_id']}")
            else:
                print("No active tasks")
        else:
            print(f"Status endpoint failed: {response.status_code}")
        
        # Test starting a scraping task
        start_data = {
            'leagues': ['Standard'],
            'enhance_profiles': False,
            'categorize_builds': False
        }
        
        response = requests.post(
            f"{base_url}/api/scraping/start",
            headers={'Content-Type': 'application/json'},
            data=json.dumps(start_data)
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Started task: {result['task_id']}")
            
            # Monitor for a few seconds
            for i in range(5):
                time.sleep(2)
                status_response = requests.get(f"{base_url}/api/scraping/status")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data['active_task']:
                        task = status_data['active_task']
                        print(f"  Progress: {task['progress_percentage']:.1f}% - {task['current_step']}")
                
        else:
            result = response.json()
            print(f"Start endpoint failed: {response.status_code} - {result}")
    
    except requests.exceptions.ConnectionError:
        print("Dashboard not running. Start it with: python web_dashboard.py")
    except Exception as e:
        print(f"Error testing API: {e}")


if __name__ == "__main__":
    print("Testing Scraping Controls")
    print("=" * 50)
    
    # Test task manager directly
    test_task_manager()
    
    # Test API endpoints (requires dashboard running)
    test_api_endpoints()
    
    print("\nTests complete!")