"""
pytest configuration file to handle project imports.
"""
import sys
import os

# Add the project root directory to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Also add the archive/examples directory for query_fire_tanky_builds import
archive_examples = os.path.join(project_root, 'archive', 'examples')
if archive_examples not in sys.path:
    sys.path.insert(0, archive_examples)