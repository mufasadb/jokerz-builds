import pytest
import responses
from datetime import datetime
from src.scraper.poe_ninja_client import PoeNinjaClient
from src.models.build_models import Character, BuildOverview


class TestBuildAnalysis:
    @pytest.fixture
    def client(self):
        return PoeNinjaClient(league="TestLeague")
    
    @pytest.fixture
    def mock_build_response(self):
        """Mock response mimicking PoE Ninja build overview structure"""
        return {
            "data": [
                {
                    "account": "Player1",
                    "name": "SuperDelver",
                    "level": 100,
                    "class": "Necromancer",
                    "ascendancy": "Necromancer",
                    "experience": 4250334444,
                    "depth": {"default": 1500, "solo": 1200},
                    "life": 5000,
                    "energyShield": 2000,
                    "dps": 5000000.0,
                    "mainSkill": "Raise Spectre",
                    "skills": ["Raise Spectre", "Desecrate", "Bone Offering"],
                    "uniques": ["The Baron", "Mon'tregul's Grasp"],
                    "rank": 1
                },
                {
                    "account": "Player2",
                    "name": "FastMapper",
                    "level": 95,
                    "class": "Deadeye",
                    "ascendancy": "Deadeye",
                    "experience": 2500000000,
                    "depth": {"default": 400, "solo": 350},
                    "life": 4500,
                    "energyShield": 0,
                    "dps": 3000000.0,
                    "mainSkill": "Lightning Strike",
                    "skills": ["Lightning Strike", "Ancestral Protector", "Blood Rage"],
                    "uniques": ["Headhunter", "Inspired Learning"],
                    "rank": 2
                },
                {
                    "account": "Player3",
                    "name": "TankBuild",
                    "level": 98,
                    "class": "Juggernaut",
                    "ascendancy": "Juggernaut",
                    "experience": 3500000000,
                    "depth": {"default": 800, "solo": 750},
                    "life": 8000,
                    "energyShield": 0,
                    "dps": 1500000.0,
                    "mainSkill": "Boneshatter",
                    "skills": ["Boneshatter", "Ancestral Warchief", "Molten Shell"],
                    "uniques": ["Brass Dome", "Nebuloch"],
                    "rank": 3
                }
            ]
        }
    
    @responses.activate
    def test_get_build_overview_raw(self, client, mock_build_response):
        """Test fetching raw build overview data"""
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/0/getbuildoverview",
            json=mock_build_response,
            status=200
        )
        
        result = client.get_build_overview(overview_type="exp")
        assert result is not None
        assert "data" in result
        assert len(result["data"]) == 3
        assert result["data"][0]["name"] == "SuperDelver"
    
    @responses.activate
    def test_get_builds_analysis(self, client, mock_build_response):
        """Test fetching and analyzing build data"""
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/0/getbuildoverview",
            json=mock_build_response,
            status=200
        )
        
        overview = client.get_builds_analysis(overview_type="exp")
        
        # Basic overview checks
        assert overview is not None
        assert overview.league == "TestLeague"
        assert overview.overview_type == "exp"
        assert overview.total_characters == 3
        assert len(overview.characters) == 3
        
        # Character data checks
        first_char = overview.characters[0]
        assert first_char.name == "SuperDelver"
        assert first_char.level == 100
        assert first_char.class_name == "Necromancer"
        assert first_char.delve_solo_depth == 1200
        assert first_char.main_skill == "Raise Spectre"
        assert len(first_char.skills) == 3
        assert len(first_char.unique_items) == 2
        
        # Aggregate statistics checks
        assert overview.class_distribution == {
            "Necromancer": 1,
            "Deadeye": 1,
            "Juggernaut": 1
        }
        
        assert "Raise Spectre" in overview.skill_popularity
        assert "Lightning Strike" in overview.skill_popularity
        assert "Boneshatter" in overview.skill_popularity
        
        assert "Headhunter" in overview.unique_usage
        assert overview.unique_usage["Headhunter"] == 1
    
    @responses.activate
    def test_get_delve_builds(self, client, mock_build_response):
        """Test fetching delve-specific builds"""
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/0/getbuildoverview",
            json=mock_build_response,
            status=200
        )
        
        overview = client.get_builds_analysis(overview_type="depthsolo")
        
        # Test delve-specific methods
        top_delvers = overview.get_top_delvers(2)
        assert len(top_delvers) == 2
        assert top_delvers[0].name == "SuperDelver"
        assert top_delvers[0].delve_solo_depth == 1200
        assert top_delvers[1].name == "TankBuild"
        assert top_delvers[1].delve_solo_depth == 750
    
    @responses.activate
    def test_filter_by_class(self, client, mock_build_response):
        """Test filtering characters by class"""
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/0/getbuildoverview",
            json=mock_build_response,
            status=200
        )
        
        overview = client.get_builds_analysis()
        
        necros = overview.get_characters_by_class("Necromancer")
        assert len(necros) == 1
        assert necros[0].name == "SuperDelver"
        
        deadeyes = overview.get_characters_by_class("Deadeye")
        assert len(deadeyes) == 1
        assert deadeyes[0].name == "FastMapper"
    
    @responses.activate
    def test_filter_by_skill(self, client, mock_build_response):
        """Test filtering characters by skill"""
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/0/getbuildoverview",
            json=mock_build_response,
            status=200
        )
        
        overview = client.get_builds_analysis()
        
        # Filter by specific skill
        raise_spectre_users = overview.get_characters_by_skill("Raise Spectre")
        assert len(raise_spectre_users) == 1
        assert raise_spectre_users[0].name == "SuperDelver"
        
        # Common skill across multiple builds
        ancestral_users = overview.get_characters_by_skill("Ancestral Protector")
        assert len(ancestral_users) == 1
    
    @responses.activate
    def test_level_distribution(self, client, mock_build_response):
        """Test level distribution analysis"""
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/0/getbuildoverview",
            json=mock_build_response,
            status=200
        )
        
        overview = client.get_builds_analysis()
        level_dist = overview.get_level_distribution()
        
        assert level_dist[100] == 1  # One level 100
        assert level_dist[95] == 1   # One level 95
        assert level_dist[98] == 1   # One level 98
        assert sum(level_dist.values()) == 3  # Total characters
    
    @responses.activate
    def test_historical_data(self, client, mock_build_response):
        """Test fetching historical build data"""
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/0/getbuildoverview",
            json=mock_build_response,
            status=200
        )
        
        # Request with time machine parameter
        overview = client.get_builds_analysis(
            overview_type="exp",
            time_machine="week-1"
        )
        
        assert overview is not None
        assert overview.total_characters == 3
        
        # Verify the request included timemachine parameter
        assert len(responses.calls) == 1
        assert "timemachine=week-1" in responses.calls[0].request.url
    
    @responses.activate
    def test_empty_response_handling(self, client):
        """Test handling of empty build data"""
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/0/getbuildoverview",
            json={"data": []},
            status=200
        )
        
        overview = client.get_builds_analysis()
        
        assert overview is not None
        assert overview.total_characters == 0
        assert len(overview.characters) == 0
        assert overview.class_distribution == {}
        assert overview.skill_popularity == {}


# End-to-End test for build analysis
class TestBuildAnalysisE2E:
    @responses.activate
    def test_complete_build_analysis_workflow(self):
        """Test complete workflow for analyzing builds"""
        client = PoeNinjaClient(league="Standard")
        
        # Mock response with diverse build data
        build_response = {
            "data": [
                {
                    "account": f"Player{i}",
                    "name": f"Character{i}",
                    "level": 90 + i,
                    "class": ["Necromancer", "Deadeye", "Juggernaut", "Elementalist", "Assassin"][i % 5],
                    "ascendancy": ["Necromancer", "Deadeye", "Juggernaut", "Elementalist", "Assassin"][i % 5],
                    "experience": 1000000000 + i * 100000000,
                    "depth": {"default": 300 + i * 50, "solo": 250 + i * 50},
                    "life": 4000 + i * 200,
                    "energyShield": i * 500,
                    "dps": 1000000.0 * (i + 1),
                    "mainSkill": ["Raise Spectre", "Lightning Strike", "Boneshatter", "Arc", "Blade Flurry"][i % 5],
                    "skills": [["Raise Spectre", "Desecrate"], ["Lightning Strike"], ["Boneshatter"], ["Arc"], ["Blade Flurry"]][i % 5],
                    "uniques": [["The Baron"], ["Headhunter"], ["Brass Dome"], ["Shavs"], ["Cospri's"]][i % 5],
                    "rank": i + 1
                }
                for i in range(20)
            ]
        }
        
        responses.add(
            responses.GET,
            "https://poe.ninja/api/data/0/getbuildoverview",
            json=build_response,
            status=200
        )
        
        # Fetch and analyze builds
        overview = client.get_builds_analysis(overview_type="exp")
        
        # Comprehensive analysis
        assert overview.total_characters == 20
        
        # Class distribution should show 4 of each class
        assert all(count == 4 for count in overview.class_distribution.values())
        
        # Level distribution
        level_dist = overview.get_level_distribution()
        assert len(level_dist) == 20  # 20 different levels
        
        # Top delvers
        top_delvers = overview.get_top_delvers(3)
        assert len(top_delvers) == 3
        assert top_delvers[0].delve_solo_depth == 1200  # Character19
        assert top_delvers[1].delve_solo_depth == 1150  # Character18
        assert top_delvers[2].delve_solo_depth == 1100  # Character17
        
        # Filter by popular class
        necros = overview.get_characters_by_class("Necromancer")
        assert len(necros) == 4
        
        # Most popular skills
        most_popular_skills = sorted(
            overview.skill_popularity.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        assert len(most_popular_skills) > 0