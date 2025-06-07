"""
Data storage manager for PoE Ninja data
Handles saving and loading of fetched data to/from disk
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DataManager:
    """Manages persistent storage of PoE Ninja data"""
    
    def __init__(self, base_path: str = "data"):
        """
        Initialize data manager
        
        Args:
            base_path: Base directory for data storage
        """
        self.base_path = Path(base_path)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directory structure exists"""
        directories = [
            self.base_path,
            self.base_path / "builds",
            self.base_path / "items",
            self.base_path / "currency",
            self.base_path / "raw",
            self.base_path / "analysis"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {directory}")
    
    def _get_filename(self, data_type: str, league: str, 
                     timestamp: Optional[str] = None,
                     suffix: Optional[str] = None) -> str:
        """
        Generate consistent filename for data storage
        
        Args:
            data_type: Type of data (builds, items, currency)
            league: League name
            timestamp: Optional timestamp or snapshot identifier
            suffix: Optional suffix for the filename
        
        Returns:
            Filename string
        """
        parts = [league.lower().replace(" ", "_")]
        
        if timestamp:
            parts.append(timestamp)
        
        if suffix:
            parts.append(suffix)
        
        filename = "_".join(parts) + ".json"
        return filename
    
    def save_build_data(self, data: Dict[str, Any], league: str, 
                       snapshot: str = "current") -> str:
        """
        Save build overview data
        
        Args:
            data: Build data from API
            league: League name
            snapshot: Snapshot identifier (e.g., 'week-1', 'current')
        
        Returns:
            Path to saved file
        """
        filename = self._get_filename("builds", league, snapshot)
        filepath = self.base_path / "builds" / filename
        
        # Add metadata
        wrapped_data = {
            "metadata": {
                "league": league,
                "snapshot": snapshot,
                "fetched_at": datetime.now().isoformat(),
                "total_characters": len(data.get("data", []))
            },
            "data": data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(wrapped_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved build data to {filepath}")
        return str(filepath)
    
    def save_item_data(self, data: Dict[str, Any], league: str, 
                      item_type: str, date: Optional[str] = None) -> str:
        """
        Save item price data
        
        Args:
            data: Item data from API
            league: League name
            item_type: Type of items (e.g., 'UniqueWeapon')
            date: Date of the data (YYYY-MM-DD)
        
        Returns:
            Path to saved file
        """
        date_str = date or datetime.now().strftime("%Y-%m-%d")
        filename = self._get_filename("items", league, date_str, item_type.lower())
        filepath = self.base_path / "items" / filename
        
        # Add metadata
        wrapped_data = {
            "metadata": {
                "league": league,
                "item_type": item_type,
                "date": date_str,
                "fetched_at": datetime.now().isoformat(),
                "total_items": len(data.get("lines", []))
            },
            "data": data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(wrapped_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {item_type} data to {filepath}")
        return str(filepath)
    
    def save_currency_data(self, data: Dict[str, Any], league: str,
                          date: Optional[str] = None) -> str:
        """
        Save currency exchange data
        
        Args:
            data: Currency data from API
            league: League name
            date: Date of the data (YYYY-MM-DD)
        
        Returns:
            Path to saved file
        """
        date_str = date or datetime.now().strftime("%Y-%m-%d")
        filename = self._get_filename("currency", league, date_str)
        filepath = self.base_path / "currency" / filename
        
        # Add metadata
        wrapped_data = {
            "metadata": {
                "league": league,
                "date": date_str,
                "fetched_at": datetime.now().isoformat(),
                "total_currencies": len(data.get("lines", []))
            },
            "data": data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(wrapped_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved currency data to {filepath}")
        return str(filepath)
    
    def load_build_data(self, league: str, snapshot: str = "current") -> Optional[Dict[str, Any]]:
        """
        Load previously saved build data
        
        Args:
            league: League name
            snapshot: Snapshot identifier
        
        Returns:
            Loaded data or None if not found
        """
        filename = self._get_filename("builds", league, snapshot)
        filepath = self.base_path / "builds" / filename
        
        if not filepath.exists():
            logger.warning(f"Build data file not found: {filepath}")
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded build data from {filepath}")
        return data
    
    def load_item_data(self, league: str, item_type: str, 
                      date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Load previously saved item data
        
        Args:
            league: League name
            item_type: Type of items
            date: Date of the data
        
        Returns:
            Loaded data or None if not found
        """
        date_str = date or datetime.now().strftime("%Y-%m-%d")
        filename = self._get_filename("items", league, date_str, item_type.lower())
        filepath = self.base_path / "items" / filename
        
        if not filepath.exists():
            logger.warning(f"Item data file not found: {filepath}")
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded item data from {filepath}")
        return data
    
    def list_saved_builds(self, league: Optional[str] = None) -> List[Dict[str, str]]:
        """
        List all saved build data files
        
        Args:
            league: Optional league filter
        
        Returns:
            List of file information dictionaries
        """
        build_files = []
        builds_dir = self.base_path / "builds"
        
        for filepath in builds_dir.glob("*.json"):
            if league and not filepath.name.startswith(league.lower()):
                continue
            
            # Extract info from filename
            parts = filepath.stem.split("_")
            file_info = {
                "filename": filepath.name,
                "path": str(filepath),
                "league": parts[0] if parts else "unknown",
                "snapshot": parts[1] if len(parts) > 1 else "current",
                "size": filepath.stat().st_size,
                "modified": datetime.fromtimestamp(filepath.stat().st_mtime).isoformat()
            }
            build_files.append(file_info)
        
        return sorted(build_files, key=lambda x: x["modified"], reverse=True)
    
    def save_analysis_result(self, analysis_data: Dict[str, Any], 
                           analysis_type: str, league: str) -> str:
        """
        Save analysis results
        
        Args:
            analysis_data: Analysis results
            analysis_type: Type of analysis performed
            league: League name
        
        Returns:
            Path to saved file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{league}_{analysis_type}_{timestamp}.json"
        filepath = self.base_path / "analysis" / filename
        
        # Add metadata
        wrapped_data = {
            "metadata": {
                "analysis_type": analysis_type,
                "league": league,
                "created_at": datetime.now().isoformat()
            },
            "results": analysis_data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(wrapped_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved analysis to {filepath}")
        return str(filepath)
    
    def get_storage_summary(self) -> Dict[str, Any]:
        """Get summary of stored data"""
        summary = {
            "base_path": str(self.base_path),
            "total_size_mb": 0,
            "file_counts": {},
            "leagues": set(),
            "oldest_file": None,
            "newest_file": None
        }
        
        oldest_time = float('inf')
        newest_time = 0
        
        for subdir in ["builds", "items", "currency", "analysis"]:
            dir_path = self.base_path / subdir
            if not dir_path.exists():
                continue
            
            files = list(dir_path.glob("*.json"))
            summary["file_counts"][subdir] = len(files)
            
            for filepath in files:
                # Get file stats
                stat = filepath.stat()
                summary["total_size_mb"] += stat.st_size / (1024 * 1024)
                
                # Track oldest/newest
                if stat.st_mtime < oldest_time:
                    oldest_time = stat.st_mtime
                    summary["oldest_file"] = str(filepath)
                
                if stat.st_mtime > newest_time:
                    newest_time = stat.st_mtime
                    summary["newest_file"] = str(filepath)
                
                # Extract league from filename
                if "_" in filepath.stem:
                    league = filepath.stem.split("_")[0]
                    summary["leagues"].add(league)
        
        summary["leagues"] = list(summary["leagues"])
        summary["total_size_mb"] = round(summary["total_size_mb"], 2)
        
        return summary