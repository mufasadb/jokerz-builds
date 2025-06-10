"""
Claude API integration for natural language data analysis queries
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import anthropic

logger = logging.getLogger(__name__)


@dataclass 
class QueryIntent:
    """Structured representation of user's query intent"""
    query_type: str  # "build_search", "skill_analysis", "meta_analysis", etc.
    filters: Dict[str, Any]  # class, skill, damage_type, cost_tier, etc.
    sort_by: str  # "level", "popularity", "cost", etc. 
    limit: int  # number of results
    aggregation: Optional[str] = None  # "count", "average", etc.


class ClaudeQueryAnalyzer:
    """Analyzes natural language queries using Claude API"""
    
    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        
        # Define available data schema for Claude
        self.data_schema = {
            "characters": {
                "fields": [
                    "name", "account", "level", "class_name", "ascendancy",
                    "life", "energy_shield", "main_skill", "skills", 
                    "unique_items", "league", "primary_damage_type",
                    "secondary_damage_types", "skill_delivery", "defense_style",
                    "cost_tier", "tankiness_rating"
                ],
                "filters": {
                    "class_name": ["Witch", "Templar", "Marauder", "Ranger", "Duelist", "Shadow", "Scion"],
                    "ascendancy": ["Juggernaut", "Berserker", "Chieftain", "Guardian", "Hierophant", "Inquisitor"],
                    "primary_damage_type": ["fire", "cold", "lightning", "physical", "chaos"],
                    "skill_delivery": ["melee", "self_cast", "totem", "trap", "mine", "minion"],
                    "defense_style": ["tanky", "balanced", "squishy"],
                    "cost_tier": ["budget", "moderate", "expensive", "luxury"],
                    "tankiness_rating": ["Extremely Tanky", "Very Tanky", "Tanky", "Moderate", "Squishy"]
                }
            }
        }
    
    def analyze_query(self, user_query: str, context: Dict[str, Any] = None) -> QueryIntent:
        """
        Analyze user's natural language query and return structured intent
        
        Args:
            user_query: User's question in natural language
            context: Additional context (current league, previous queries, etc.)
            
        Returns:
            QueryIntent object with parsed intent
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(user_query, context)
        
        try:
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            # Parse Claude's response as JSON
            intent_data = json.loads(response.content[0].text)
            
            return QueryIntent(
                query_type=intent_data.get("query_type", "build_search"),
                filters=intent_data.get("filters", {}),
                sort_by=intent_data.get("sort_by", "level"),
                limit=intent_data.get("limit", 10),
                aggregation=intent_data.get("aggregation")
            )
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            # Fallback to basic intent
            return self._fallback_intent(user_query)
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with data schema and instructions"""
        return f"""You are a Path of Exile build data analyzer. Users will ask natural language questions about character builds, and you need to convert them into structured database queries.

Available data schema:
{json.dumps(self.data_schema, indent=2)}

Your job is to analyze the user's question and return a JSON object with this structure:
{{
    "query_type": "build_search|skill_analysis|meta_analysis|comparison",
    "filters": {{
        "class_name": "optional class filter",
        "ascendancy": "optional ascendancy filter", 
        "primary_damage_type": "optional damage type",
        "skill_delivery": "optional delivery method",
        "defense_style": "optional defense style",
        "cost_tier": "optional cost filter",
        "main_skill": "optional specific skill",
        "league": "optional league filter",
        "min_level": "optional minimum level",
        "max_level": "optional maximum level"
    }},
    "sort_by": "level|popularity|cost|tankiness",
    "limit": 5-20,
    "aggregation": null|"count"|"average"|"top"
}}

Guidelines:
- "best" usually means highest level builds
- "cheap/budget" maps to cost_tier: "budget" 
- "tanky" maps to defense_style: "tanky" or tankiness_rating filters
- "off-meta" means less popular skills (use aggregation: "count" with low counts)
- "current league" should filter to the most recent challenge league
- Juggernaut/Jugg maps to ascendancy: "Juggernaut"
- DoT/damage over time should look for skills with DoT mechanics
- Cold skills should filter primary_damage_type: "cold"

Always return valid JSON only."""

    def _build_user_prompt(self, user_query: str, context: Dict[str, Any] = None) -> str:
        """Build user prompt with query and context"""
        prompt = f"User query: {user_query}"
        
        if context:
            if "current_league" in context:
                prompt += f"\nCurrent active league: {context['current_league']}"
            if "previous_results" in context:
                prompt += f"\nPrevious query context: {context['previous_results']}"
        
        return prompt
    
    def _fallback_intent(self, user_query: str) -> QueryIntent:
        """Fallback intent parser for when Claude API fails"""
        # Simple keyword-based fallback - only use basic fields that definitely exist
        filters = {}
        
        # Basic keyword detection using only core database fields
        query_lower = user_query.lower()
        
        if "jugg" in query_lower or "juggernaut" in query_lower:
            filters["ascendancy"] = "Juggernaut"
        
        if "witch" in query_lower:
            filters["class_name"] = "Witch"
        elif "templar" in query_lower:
            filters["class_name"] = "Templar"
        elif "marauder" in query_lower:
            filters["class_name"] = "Marauder"
        elif "ranger" in query_lower:
            filters["class_name"] = "Ranger"
        elif "duelist" in query_lower:
            filters["class_name"] = "Duelist"
        elif "shadow" in query_lower:
            filters["class_name"] = "Shadow"
        elif "scion" in query_lower:
            filters["class_name"] = "Scion"
        
        # For advanced categorization terms, skip them in fallback mode
        # The user will get basic results and can try again when categorization is available
        
        return QueryIntent(
            query_type="build_search",
            filters=filters,
            sort_by="level",
            limit=10
        )


class DataQueryBuilder:
    """Converts QueryIntent into database queries"""
    
    def __init__(self, db_manager):
        self.db = db_manager
    
    def build_query(self, intent: QueryIntent) -> List[Dict[str, Any]]:
        """
        Convert QueryIntent into database query and execute
        
        Args:
            intent: Parsed query intent from Claude
            
        Returns:
            List of results matching the query
        """
        from src.storage.database import Character
        
        session = self.db.get_session()
        try:
            # Start with base query
            query = session.query(Character)
            
            # Apply filters - only use fields that exist in database
            for field, value in intent.filters.items():
                if value is not None:
                    if field in ["min_level", "max_level"]:
                        if field == "min_level":
                            query = query.filter(Character.level >= value)
                        else:
                            query = query.filter(Character.level <= value)
                    elif hasattr(Character, field):
                        # Only filter on fields that actually exist in the database
                        try:
                            query = query.filter(getattr(Character, field) == value)
                        except Exception as e:
                            logger.warning(f"Skipping filter {field}: {e}")
                    else:
                        logger.debug(f"Skipping unknown field: {field}")
            
            # Handle special cases
            if "damage_over_time" in intent.filters and intent.filters["damage_over_time"]:
                # Look for DoT skills in the skills list
                query = query.filter(Character.damage_over_time == True)
            
            # Apply sorting
            if intent.sort_by == "level":
                query = query.order_by(Character.level.desc())
            elif intent.sort_by == "popularity":
                # Count occurrences of main_skill and sort by that
                pass  # Would need subquery
            
            # Apply limit
            query = query.limit(intent.limit)
            
            # Execute and format results
            results = query.all()
            
            return [self._format_character(char) for char in results]
            
        finally:
            session.close()
    
    def _format_character(self, char) -> Dict[str, Any]:
        """Format character object for API response"""
        result = {
            "name": char.name,
            "account": char.account,
            "level": char.level,
            "class": char.class_name,
            "ascendancy": char.ascendancy,
            "life": char.life,
            "energy_shield": char.energy_shield,
            "main_skill": char.main_skill,
            "skills": char.skills or [],
            "unique_items": char.unique_items or [],
            "league": char.league
        }
        
        # Add optional fields if they exist
        for field in ["primary_damage_type", "skill_delivery", "defense_style", "cost_tier", "tankiness_rating", "ehp_weighted"]:
            if hasattr(char, field):
                result[field] = getattr(char, field)
        
        # Add URL fields for clickthrough functionality
        for url_field in ["profile_url", "ladder_url", "pob_url"]:
            if hasattr(char, url_field):
                result[url_field] = getattr(char, url_field)
        
        return result


class NaturalLanguageQueryService:
    """Main service for handling natural language queries"""
    
    def __init__(self, claude_api_key: str, db_manager):
        self.analyzer = ClaudeQueryAnalyzer(claude_api_key)
        self.query_builder = DataQueryBuilder(db_manager)
        self.conversation_context = {}
    
    def process_query(self, user_query: str, session_id: str = "default") -> Dict[str, Any]:
        """
        Process a natural language query and return results
        
        Args:
            user_query: User's question
            session_id: Session identifier for context tracking
            
        Returns:
            Dictionary with results and metadata
        """
        try:
            # Get conversation context
            context = self.conversation_context.get(session_id, {})
            
            # Analyze query intent
            intent = self.analyzer.analyze_query(user_query, context)
            
            # Execute database query
            results = self.query_builder.build_query(intent)
            
            # Update conversation context
            self.conversation_context[session_id] = {
                "last_query": user_query,
                "last_intent": intent,
                "last_results_count": len(results)
            }
            
            # Format response
            response = {
                "query": user_query,
                "intent": {
                    "type": intent.query_type,
                    "filters": intent.filters,
                    "sort_by": intent.sort_by
                },
                "results": results,
                "count": len(results),
                "summary": self._generate_summary(user_query, intent, results)
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Query processing error: {e}")
            return {
                "query": user_query,
                "intent": {
                    "type": "error",
                    "filters": {},
                    "sort_by": "level"
                },
                "error": str(e),
                "results": [],
                "count": 0,
                "summary": f"Error processing query: {str(e)}"
            }
    
    def _generate_summary(self, query: str, intent: QueryIntent, results: List[Dict]) -> str:
        """Generate a human-readable summary of results"""
        if not results:
            return f"No builds found matching your criteria."
        
        count = len(results)
        
        # Extract common patterns from results
        if intent.query_type == "build_search":
            if "ascendancy" in intent.filters:
                ascendancy = intent.filters["ascendancy"]
                if count == 1:
                    return f"Found 1 {ascendancy} build: {results[0]['name']} (level {results[0]['level']})"
                else:
                    avg_level = sum(r['level'] for r in results) / count
                    return f"Found {count} {ascendancy} builds with average level {avg_level:.1f}"
            
            if "primary_damage_type" in intent.filters:
                damage_type = intent.filters["primary_damage_type"]
                if count == 1:
                    return f"Found 1 {damage_type} build: {results[0]['main_skill']} {results[0]['ascendancy']} (level {results[0]['level']})"
                else:
                    return f"Found {count} {damage_type} builds"
        
        return f"Found {count} builds matching your criteria"