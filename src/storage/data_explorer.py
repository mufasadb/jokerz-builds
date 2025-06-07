"""
Data explorer utility for browsing and analyzing stored PoE Ninja data
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from src.storage.data_manager import DataManager
from src.models.build_models import Character, BuildOverview
from collections import Counter
import pandas as pd


class DataExplorer:
    """Explore and analyze stored PoE Ninja data"""
    
    def __init__(self, data_path: str = "data"):
        self.data_manager = DataManager(data_path)
        self.data_path = Path(data_path)
    
    def list_all_data(self) -> Dict[str, List[Dict]]:
        """List all stored data organized by type"""
        data_types = ["builds", "items", "currency", "analysis"]
        all_data = {}
        
        for data_type in data_types:
            type_path = self.data_path / data_type
            if not type_path.exists():
                continue
            
            files = []
            for filepath in type_path.glob("*.json"):
                stat = filepath.stat()
                files.append({
                    "name": filepath.name,
                    "path": str(filepath),
                    "size_kb": round(stat.st_size / 1024, 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
            
            all_data[data_type] = sorted(files, key=lambda x: x["modified"], reverse=True)
        
        return all_data
    
    def print_storage_report(self):
        """Print a formatted report of stored data"""
        summary = self.data_manager.get_storage_summary()
        all_data = self.list_all_data()
        
        print("=" * 80)
        print("POE NINJA DATA STORAGE REPORT")
        print("=" * 80)
        print(f"\nStorage Location: {summary['base_path']}")
        print(f"Total Size: {summary['total_size_mb']} MB")
        print(f"Leagues: {', '.join(summary['leagues'])}")
        print()
        
        for data_type, files in all_data.items():
            if not files:
                continue
                
            print(f"\n{data_type.upper()} ({len(files)} files)")
            print("-" * 40)
            
            # Show recent files
            for file_info in files[:5]:  # Show top 5 most recent
                print(f"  {file_info['name']:<40} {file_info['size_kb']:>8.1f} KB  {file_info['modified']}")
            
            if len(files) > 5:
                print(f"  ... and {len(files) - 5} more files")
    
    def load_and_analyze_builds(self, league: str, snapshot: str = "current") -> Optional[BuildOverview]:
        """Load build data and convert to BuildOverview object"""
        data = self.data_manager.load_build_data(league, snapshot)
        
        if not data:
            return None
        
        # Extract the actual data
        build_data = data.get("data", {})
        metadata = data.get("metadata", {})
        
        # Convert to Character objects
        characters = []
        for char_data in build_data.get("data", []):
            character = Character(
                account=char_data.get("account", ""),
                name=char_data.get("name", ""),
                level=char_data.get("level", 0),
                class_name=char_data.get("class", ""),
                ascendancy=char_data.get("ascendancy"),
                experience=char_data.get("experience"),
                delve_depth=char_data.get("depth", {}).get("default"),
                delve_solo_depth=char_data.get("depth", {}).get("solo"),
                life=char_data.get("life"),
                energy_shield=char_data.get("energyShield"),
                dps=char_data.get("dps"),
                main_skill=char_data.get("mainSkill"),
                skills=char_data.get("skills", []),
                unique_items=char_data.get("uniques", []),
                league=league,
                rank=char_data.get("rank"),
                raw_data=char_data
            )
            characters.append(character)
        
        # Create BuildOverview
        overview = BuildOverview(
            league=league,
            overview_type="exp",
            timestamp=datetime.fromisoformat(metadata.get("fetched_at", datetime.now().isoformat())),
            total_characters=len(characters),
            characters=characters
        )
        
        return overview
    
    def compare_snapshots(self, league: str, snapshot1: str, snapshot2: str):
        """Compare two build snapshots"""
        print(f"\nComparing {snapshot1} vs {snapshot2} for {league}")
        print("=" * 60)
        
        build1 = self.load_and_analyze_builds(league, snapshot1)
        build2 = self.load_and_analyze_builds(league, snapshot2)
        
        if not build1 or not build2:
            print("Could not load both snapshots")
            return
        
        # Character count change
        print(f"\nCharacter Count:")
        print(f"  {snapshot1}: {build1.total_characters}")
        print(f"  {snapshot2}: {build2.total_characters}")
        print(f"  Change: {build2.total_characters - build1.total_characters:+d}")
        
        # Skill popularity changes
        skills1 = set(build1.skill_popularity.keys())
        skills2 = set(build2.skill_popularity.keys())
        
        print(f"\nNew Skills in {snapshot2}:")
        new_skills = skills2 - skills1
        for skill in list(new_skills)[:10]:
            count = build2.skill_popularity[skill]
            print(f"  - {skill}: {count} players")
        
        print(f"\nDropped Skills from {snapshot1}:")
        dropped_skills = skills1 - skills2
        for skill in list(dropped_skills)[:10]:
            count = build1.skill_popularity[skill]
            print(f"  - {skill}: was {count} players")
        
        # Top skill changes
        print("\nTop Skill Usage Changes:")
        common_skills = skills1 & skills2
        
        skill_changes = []
        for skill in common_skills:
            count1 = build1.skill_popularity[skill]
            count2 = build2.skill_popularity[skill]
            pct1 = (count1 / build1.total_characters) * 100
            pct2 = (count2 / build2.total_characters) * 100
            change = pct2 - pct1
            
            if abs(change) > 0.5:  # Only show significant changes
                skill_changes.append((skill, pct1, pct2, change))
        
        skill_changes.sort(key=lambda x: abs(x[3]), reverse=True)
        
        for skill, pct1, pct2, change in skill_changes[:10]:
            sign = "+" if change > 0 else ""
            print(f"  {skill}: {pct1:.1f}% → {pct2:.1f}% ({sign}{change:.1f}%)")
    
    def export_to_csv(self, league: str, output_dir: str = "exports"):
        """Export stored data to CSV files for external analysis"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Export builds
        builds_data = []
        for file_info in self.data_manager.list_saved_builds(league):
            snapshot = file_info["snapshot"]
            overview = self.load_and_analyze_builds(league, snapshot)
            
            if overview:
                for char in overview.characters:
                    builds_data.append({
                        "snapshot": snapshot,
                        "name": char.name,
                        "account": char.account,
                        "level": char.level,
                        "class": char.class_name,
                        "main_skill": char.main_skill,
                        "life": char.life,
                        "es": char.energy_shield,
                        "delve_depth": char.delve_solo_depth,
                        "rank": char.rank
                    })
        
        if builds_data:
            df = pd.DataFrame(builds_data)
            csv_path = output_path / f"{league}_builds.csv"
            df.to_csv(csv_path, index=False)
            print(f"Exported {len(builds_data)} build records to {csv_path}")
        
        return output_path


# Example usage
if __name__ == "__main__":
    explorer = DataExplorer()
    
    # Show storage report
    explorer.print_storage_report()
    
    # Example: Compare snapshots
    # explorer.compare_snapshots("Standard", "week-1", "current")