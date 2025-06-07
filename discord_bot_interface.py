"""
Discord bot interface for querying build data
This is a placeholder showing how to integrate request tracking
"""

from src.storage.database import DatabaseManager

class DiscordBotInterface:
    """Interface for Discord bot to query build data"""
    
    def __init__(self):
        self.db = DatabaseManager()
    
    def search_builds(self, damage_type=None, tankiness=None, min_ehp=None, 
                     league=None, user_id=None, limit=10):
        """
        Search for builds and log the request
        
        Args:
            damage_type: Primary damage type filter
            tankiness: Tankiness rating filter
            min_ehp: Minimum EHP filter
            league: League filter
            user_id: Discord user ID making the request
            limit: Maximum results
            
        Returns:
            List of build results
        """
        # Log the Discord bot request
        self.db.log_request(
            api_type='discord_query',
            success=True,
            source='discord_bot',
            source_user=str(user_id) if user_id else None,
            endpoint='search_builds'
        )
        
        # Perform the search
        results = self.db.search_builds_by_category(
            damage_type=damage_type,
            tankiness_rating=tankiness,
            min_ehp=min_ehp,
            league=league,
            limit=limit
        )
        
        return results
    
    def get_character_details(self, account, character, user_id=None):
        """
        Get character details and log the request
        
        Args:
            account: Account name
            character: Character name
            user_id: Discord user ID making the request
            
        Returns:
            Character details or None
        """
        # Log the Discord bot request
        self.db.log_request(
            api_type='discord_query',
            success=True,
            source='discord_bot',
            source_user=str(user_id) if user_id else None,
            endpoint='character_details',
            account_name=account,
            character_name=character
        )
        
        session = self.db.get_session()
        try:
            from src.storage.database import Character
            
            char = session.query(Character).filter_by(
                account=account,
                name=character
            ).first()
            
            if char:
                return {
                    'name': char.name,
                    'account': char.account,
                    'level': char.level,
                    'class': char.class_name,
                    'league': char.league,
                    'main_skill': char.main_skill,
                    'tankiness_rating': char.tankiness_rating,
                    'ehp_weighted': char.ehp_weighted,
                    'primary_damage_type': char.primary_damage_type,
                    'skill_delivery': char.skill_delivery,
                    'cost_tier': char.cost_tier,
                    'unique_items': char.enhanced_uniques or char.unique_items,
                    'profile_url': f"https://www.pathofexile.com/account/view-profile/{account}/characters?characterName={character}"
                }
            
            return None
            
        finally:
            session.close()
    
    def get_top_builds(self, league=None, limit=10, user_id=None):
        """
        Get top builds by rank
        
        Args:
            league: League filter
            limit: Maximum results
            user_id: Discord user ID making the request
            
        Returns:
            List of top builds
        """
        # Log the Discord bot request
        self.db.log_request(
            api_type='discord_query',
            success=True,
            source='discord_bot',
            source_user=str(user_id) if user_id else None,
            endpoint='top_builds',
            league=league
        )
        
        session = self.db.get_session()
        try:
            from src.storage.database import Character
            
            query = session.query(Character)
            
            if league:
                query = query.filter_by(league=league)
            
            characters = query.order_by(Character.rank.asc()).limit(limit).all()
            
            results = []
            for char in characters:
                results.append({
                    'rank': char.rank,
                    'name': char.name,
                    'account': char.account,
                    'level': char.level,
                    'class': char.class_name,
                    'main_skill': char.main_skill,
                    'tankiness_rating': char.tankiness_rating,
                    'ehp_weighted': char.ehp_weighted
                })
            
            return results
            
        finally:
            session.close()


# Example Discord bot command handlers (pseudo-code)
"""
@bot.command()
async def tanky_builds(ctx, damage_type=None):
    # Find tanky builds
    interface = DiscordBotInterface()
    results = interface.search_builds(
        damage_type=damage_type,
        tankiness='Extremely Tanky',
        user_id=ctx.author.id,
        limit=5
    )
    
    # Format and send results
    for build in results:
        embed = discord.Embed(
            title=f"{build['character_name']} - {build['main_skill']}",
            description=build['build_summary']
        )
        embed.add_field(name="Level", value=build['level'])
        embed.add_field(name="Class", value=build['class'])
        embed.add_field(name="EHP", value=f"{build['ehp']['weighted']:,.0f}")
        await ctx.send(embed=embed)

@bot.command()
async def character(ctx, account, character_name):
    # Get character details
    interface = DiscordBotInterface()
    char = interface.get_character_details(
        account=account,
        character=character_name,
        user_id=ctx.author.id
    )
    
    if char:
        embed = discord.Embed(
            title=f"{char['name']} ({char['account']})",
            url=char['profile_url']
        )
        embed.add_field(name="Level", value=f"{char['level']} {char['class']}")
        embed.add_field(name="Main Skill", value=char['main_skill'] or 'Unknown')
        embed.add_field(name="Tankiness", value=char['tankiness_rating'] or 'Unknown')
        embed.add_field(name="EHP", value=f"{char['ehp_weighted']:,.0f}" if char['ehp_weighted'] else 'Unknown')
        
        if char['unique_items']:
            embed.add_field(
                name="Key Uniques", 
                value=", ".join(char['unique_items'][:5]),
                inline=False
            )
        
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"Character {character_name} not found for account {account}")
"""