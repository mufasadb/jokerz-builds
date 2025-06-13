#!/usr/bin/env python3
"""
Test script to debug CI import issues
"""
import sys
import os

print("Python version:", sys.version)
print("Current working directory:", os.getcwd())
print("Python path:")
for p in sys.path:
    print(f"  {p}")

print("\nTesting imports...")

try:
    from src.data.skill_tags import skill_analyzer
    print("✓ src.data.skill_tags import successful")
except ImportError as e:
    print(f"✗ src.data.skill_tags import failed: {e}")

try:
    from query_fire_tanky_builds import BuildQuerySystem
    print("✓ query_fire_tanky_builds import successful")
except ImportError as e:
    print(f"✗ query_fire_tanky_builds import failed: {e}")

# Check if directories exist
print(f"\nsrc/ exists: {os.path.exists('src')}")
print(f"src/data/ exists: {os.path.exists('src/data')}")
print(f"src/data/skill_tags.py exists: {os.path.exists('src/data/skill_tags.py')}")
print(f"archive/examples/ exists: {os.path.exists('archive/examples')}")
print(f"archive/examples/query_fire_tanky_builds.py exists: {os.path.exists('archive/examples/query_fire_tanky_builds.py')}")