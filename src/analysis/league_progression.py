"""
League progression analysis - tracks meta and economy changes throughout a league
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from src.scraper.poe_ninja_client import PoeNinjaClient
from src.models.build_models import BuildOverview
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class LeagueProgressionAnalyzer:
    """Analyzes build meta and economy progression throughout a league"""
    
    def __init__(self, league: str, league_start_date: datetime):
        self.client = PoeNinjaClient(league=league)
        self.league = league
        self.league_start = league_start_date
    
    def get_snapshot_dates(self) -> Dict[str, Tuple[str, str]]:
        """
        Get key snapshot dates for analysis
        
        Returns:
            Dict with snapshot names and (timemachine_param, date_string) tuples
        """
        week_1 = self.league_start + timedelta(days=7)
        week_2 = self.league_start + timedelta(days=14)
        week_6 = self.league_start + timedelta(days=42)  # Mid-league
        week_12 = self.league_start + timedelta(days=84)  # End of league
        
        return {
            "week_1": ("week-1", week_1.strftime("%Y-%m-%d")),
            "week_2": ("week-2", week_2.strftime("%Y-%m-%d")),
            "mid_league": ("week-6", week_6.strftime("%Y-%m-%d")),
            "late_league": ("week-12", week_12.strftime("%Y-%m-%d")),
            "current": ("", datetime.now().strftime("%Y-%m-%d"))
        }
    
    def analyze_build_progression(self) -> Dict[str, BuildOverview]:
        """Analyze build meta progression across league snapshots"""
        snapshots = self.get_snapshot_dates()
        results = {}
        
        for snapshot_name, (timemachine, _) in snapshots.items():
            logger.info(f"Fetching {snapshot_name} build data...")
            
            builds = self.client.get_builds_analysis(
                overview_type="exp",
                time_machine=timemachine
            )
            
            if builds:
                results[snapshot_name] = builds
                logger.info(f"  Found {builds.total_characters} characters")
            else:
                logger.warning(f"  No data available for {snapshot_name}")
        
        return results
    
    def analyze_price_progression(self, items: List[Tuple[str, str]]) -> Dict:
        """
        Analyze price progression for specific items
        
        Args:
            items: List of (item_type, item_name) tuples
        
        Returns:
            Dict with price history for each item
        """
        snapshots = self.get_snapshot_dates()
        price_history = {}
        
        for item_type, item_name in items:
            price_history[item_name] = {}
            
            for snapshot_name, (_, date) in snapshots.items():
                logger.info(f"Fetching {item_name} price for {snapshot_name}...")
                
                data = self.client.get_item_overview(item_type, date=date)
                
                if data and "lines" in data:
                    # Find the specific item
                    for item in data["lines"]:
                        if item.get("name") == item_name:
                            price_history[item_name][snapshot_name] = {
                                "chaos_value": item.get("chaosValue", 0),
                                "divine_value": item.get("divineValue", 0),
                                "listing_count": item.get("listingCount", 0)
                            }
                            break
        
        return price_history
    
    def generate_progression_report(self, build_snapshots: Dict[str, BuildOverview], 
                                  price_history: Dict) -> str:
        """Generate a comprehensive progression report"""
        report = []
        report.append("=" * 80)
        report.append(f"LEAGUE PROGRESSION ANALYSIS: {self.league}")
        report.append("=" * 80)
        report.append("")
        
        # Build Meta Evolution
        report.append("BUILD META EVOLUTION")
        report.append("-" * 40)
        
        # Track skill popularity changes
        skill_popularity_over_time = {}
        
        for snapshot_name in ["week_1", "week_2", "mid_league", "late_league", "current"]:
            if snapshot_name not in build_snapshots:
                continue
                
            builds = build_snapshots[snapshot_name]
            report.append(f"\n{snapshot_name.upper().replace('_', ' ')}:")
            report.append(f"  Total Characters: {builds.total_characters}")
            
            # Top 5 skills
            top_skills = sorted(
                builds.skill_popularity.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
            
            report.append("  Top 5 Skills:")
            for i, (skill, count) in enumerate(top_skills, 1):
                percentage = (count / builds.total_characters) * 100
                report.append(f"    {i}. {skill}: {count} ({percentage:.1f}%)")
                
                # Track for trend analysis
                if skill not in skill_popularity_over_time:
                    skill_popularity_over_time[skill] = {}
                skill_popularity_over_time[skill][snapshot_name] = percentage
        
        # Skill trends
        report.append("\n" + "-" * 40)
        report.append("SKILL POPULARITY TRENDS")
        report.append("-" * 40)
        
        # Find skills with biggest changes
        trending_skills = []
        for skill, snapshots in skill_popularity_over_time.items():
            if "week_1" in snapshots and "current" in snapshots:
                change = snapshots["current"] - snapshots["week_1"]
                trending_skills.append((skill, change, snapshots))
        
        trending_skills.sort(key=lambda x: abs(x[1]), reverse=True)
        
        report.append("\nBiggest Gainers:")
        for skill, change, snapshots in trending_skills[:5]:
            if change > 0:
                report.append(f"  {skill}: +{change:.1f}% (Week 1: {snapshots.get('week_1', 0):.1f}% → Current: {snapshots.get('current', 0):.1f}%)")
        
        report.append("\nBiggest Losers:")
        for skill, change, snapshots in trending_skills[:5]:
            if change < 0:
                report.append(f"  {skill}: {change:.1f}% (Week 1: {snapshots.get('week_1', 0):.1f}% → Current: {snapshots.get('current', 0):.1f}%)")
        
        # Class distribution changes
        report.append("\n" + "-" * 40)
        report.append("CLASS DISTRIBUTION CHANGES")
        report.append("-" * 40)
        
        if "week_1" in build_snapshots and "current" in build_snapshots:
            week_1_classes = build_snapshots["week_1"].class_distribution
            current_classes = build_snapshots["current"].class_distribution
            
            class_changes = []
            for class_name in set(week_1_classes.keys()) | set(current_classes.keys()):
                week_1_pct = (week_1_classes.get(class_name, 0) / build_snapshots["week_1"].total_characters) * 100
                current_pct = (current_classes.get(class_name, 0) / build_snapshots["current"].total_characters) * 100
                change = current_pct - week_1_pct
                class_changes.append((class_name, change, week_1_pct, current_pct))
            
            class_changes.sort(key=lambda x: abs(x[1]), reverse=True)
            
            for class_name, change, week_1_pct, current_pct in class_changes[:8]:
                sign = "+" if change > 0 else ""
                report.append(f"  {class_name}: {sign}{change:.1f}% (Week 1: {week_1_pct:.1f}% → Current: {current_pct:.1f}%)")
        
        # Price History
        if price_history:
            report.append("\n" + "-" * 40)
            report.append("ITEM PRICE PROGRESSION")
            report.append("-" * 40)
            
            for item_name, history in price_history.items():
                report.append(f"\n{item_name}:")
                
                for snapshot in ["week_1", "week_2", "mid_league", "late_league", "current"]:
                    if snapshot in history:
                        chaos_value = history[snapshot]["chaos_value"]
                        divine_value = history[snapshot].get("divine_value", 0)
                        
                        price_str = f"{chaos_value:.1f}c"
                        if divine_value > 0:
                            price_str += f" ({divine_value:.2f} div)"
                        
                        report.append(f"  {snapshot.replace('_', ' ').title()}: {price_str}")
                
                # Calculate price change
                if "week_1" in history and "current" in history:
                    week_1_price = history["week_1"]["chaos_value"]
                    current_price = history["current"]["chaos_value"]
                    
                    if week_1_price > 0:
                        change_pct = ((current_price - week_1_price) / week_1_price) * 100
                        report.append(f"  Total Change: {change_pct:+.1f}%")
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)


# Example usage
def analyze_league_progression(league: str, start_date: str):
    """
    Analyze a league's progression
    
    Args:
        league: League name (e.g., "Settlers")
        start_date: League start date in format "YYYY-MM-DD"
    """
    analyzer = LeagueProgressionAnalyzer(
        league=league,
        league_start_date=datetime.strptime(start_date, "%Y-%m-%d")
    )
    
    # Analyze build progression
    print("Fetching build snapshots across the league...")
    build_snapshots = analyzer.analyze_build_progression()
    
    # Key items to track prices
    items_to_track = [
        ("UniqueWeapon", "Headhunter"),  # Chase unique
        ("UniqueArmour", "Shavs"),  # Build-enabling unique
        ("UniqueAccessory", "Ashes of the Stars"),  # Popular unique
        ("DivinationCard", "The Doctor"),  # High-value card
        ("UniqueJewel", "Melding of the Flesh"),  # Meta jewel
    ]
    
    print("\nFetching price history for key items...")
    price_history = analyzer.analyze_price_progression(items_to_track)
    
    # Generate report
    report = analyzer.generate_progression_report(build_snapshots, price_history)
    print("\n" + report)
    
    return build_snapshots, price_history