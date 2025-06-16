"""
pytest configuration file to handle project imports.
"""
import sys
import os
import pytest

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Also add the archive/examples directory for query_fire_tanky_builds import
archive_examples = os.path.join(project_root, 'archive', 'examples')
if archive_examples not in sys.path:
    sys.path.insert(0, archive_examples)


@pytest.fixture(autouse=True)
def reset_database_manager():
    """Reset DatabaseManager instances between tests to ensure isolation"""
    # Reset before each test
    try:
        from src.storage.database import DatabaseManager
        DatabaseManager.reset_instances()
    except ImportError:
        pass  # Module may not be available in all tests
    
    yield
    
    # Optionally reset after test as well for cleanup
    try:
        from src.storage.database import DatabaseManager
        DatabaseManager.reset_instances()
    except ImportError:
        pass