#!/usr/bin/env python3
"""
Discord bot for querying Joker Builds data
Provides slash commands and natural language query interface
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional, List, Dict, Any

import discord
from discord.ext import commands
from discord import app_commands

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from discord_bot_interface import DiscordBotInterface
from src.analysis.claude_integration import NaturalLanguageQueryService
from src.storage.database import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JokerBuildsBot(commands.Bot):
    """Discord bot for Joker Builds data queries"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            description="Query Path of Exile build data from Joker Builds"
        )
        
        self.db_interface = DiscordBotInterface()
        
        # Initialize Claude integration if API key is available
        self.claude = None
        if os.getenv('ANTHROPIC_API_KEY'):
            try:
                db_manager = DatabaseManager()
                self.claude = NaturalLanguageQueryService(
                    claude_api_key=os.getenv('ANTHROPIC_API_KEY'),
                    db_manager=db_manager
                )
                logger.info("Claude integration initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Claude: {e}")
        else:
            logger.warning("ANTHROPIC_API_KEY not set - natural language queries disabled")
    
    async def setup_hook(self):
        """Called when the bot is starting up"""
        logger.info("Bot is starting up...")
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
    
    async def on_ready(self):
        """Called when bot is ready"""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')
        
        # Set activity status
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="PoE build data | /help"
        )
        await self.change_presence(activity=activity)

# Create bot instance
bot = JokerBuildsBot()

@bot.tree.command(name="help", description="Show available commands and usage")
async def help_command(interaction: discord.Interaction):
    """Show help information"""
    embed = discord.Embed(
        title="🃏 Joker Builds Bot Commands",
        description="Query Path of Exile build data from ladder snapshots",
        color=0x7289DA
    )
    
    embed.add_field(
        name="🔍 Search Commands",
        value="""
        `/search` - Search builds with filters
        `/tanky` - Find tankiest builds
        `/top` - Show top ranked builds
        `/character` - Get character details
        """,
        inline=False
    )
    
    embed.add_field(
        name="💬 Natural Language",
        value="""
        `/ask` - Ask questions in plain English
        Example: `/ask What are the best jugg builds?`
        """,
        inline=False
    )
    
    embed.add_field(
        name="📊 Info Commands",
        value="""
        `/leagues` - Show available leagues
        `/stats` - Show database statistics
        """,
        inline=False
    )
    
    embed.set_footer(text="Use slash commands (/) to get started!")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="search", description="Search for builds with optional filters")
@app_commands.describe(
    damage_type="Primary damage type (e.g., Fire, Physical, Cold)",
    tankiness="Tankiness rating (e.g., Extremely Tanky, Very Tanky)",
    min_ehp="Minimum effective health pool",
    league="League name (leave empty for current leagues)",
    limit="Maximum number of results (1-20)"
)
async def search_builds(
    interaction: discord.Interaction,
    damage_type: Optional[str] = None,
    tankiness: Optional[str] = None,
    min_ehp: Optional[int] = None,
    league: Optional[str] = None,
    limit: Optional[int] = 10
):
    """Search for builds with filters"""
    await interaction.response.defer()
    
    try:
        # Validate limit
        limit = max(1, min(limit or 10, 20))
        
        # Search builds
        results = bot.db_interface.search_builds(
            damage_type=damage_type,
            tankiness=tankiness,
            min_ehp=min_ehp,
            league=league,
            user_id=interaction.user.id,
            limit=limit
        )
        
        if not results:
            embed = discord.Embed(
                title="🔍 No Results",
                description="No builds found matching your criteria. Try adjusting your filters.",
                color=0xFF6B6B
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Create embed with results
        embed = discord.Embed(
            title="🔍 Build Search Results",
            description=f"Found {len(results)} builds matching your criteria",
            color=0x4ECDC4
        )
        
        # Add filter summary
        filters = []
        if damage_type:
            filters.append(f"Damage: {damage_type}")
        if tankiness:
            filters.append(f"Tankiness: {tankiness}")
        if min_ehp:
            filters.append(f"Min EHP: {min_ehp:,}")
        if league:
            filters.append(f"League: {league}")
        
        if filters:
            embed.add_field(
                name="🎯 Filters Applied",
                value=" • ".join(filters),
                inline=False
            )
        
        # Add top results
        for i, build in enumerate(results[:5]):  # Show top 5 in embed
            build_info = f"**Level {build['level']} {build['ascendancy'] or build['class']}**\n"
            
            if build.get('main_skill'):
                build_info += f"Main Skill: {build['main_skill']}\n"
            if build.get('primary_damage_type'):
                build_info += f"Damage: {build['primary_damage_type']}\n"
            if build.get('ehp_weighted'):
                build_info += f"EHP: {int(build['ehp_weighted']):,}\n"
            if build.get('tankiness_rating'):
                build_info += f"Tankiness: {build['tankiness_rating']}\n"
            
            build_info += f"League: {build['league']}"
            
            # Add profile link
            profile_url = f"https://www.pathofexile.com/account/view-profile/{build['account']}/characters?characterName={build['name']}"
            
            embed.add_field(
                name=f"#{i+1} {build['name']} ({build['account']})",
                value=f"{build_info}\n[View Profile]({profile_url})",
                inline=True
            )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in search command: {e}")
        embed = discord.Embed(
            title="❌ Search Error",
            description="An error occurred while searching. Please try again.",
            color=0xFF6B6B
        )
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="tanky", description="Find the tankiest builds")
@app_commands.describe(
    damage_type="Filter by damage type (optional)",
    league="League name (leave empty for current leagues)",
    limit="Number of results (1-15)"
)
async def tanky_builds(
    interaction: discord.Interaction,
    damage_type: Optional[str] = None,
    league: Optional[str] = None,
    limit: Optional[int] = 10
):
    """Find tankiest builds"""
    await interaction.response.defer()
    
    try:
        limit = max(1, min(limit or 10, 15))
        
        # Search for extremely tanky builds
        results = bot.db_interface.search_builds(
            damage_type=damage_type,
            tankiness="Extremely Tanky",
            league=league,
            user_id=interaction.user.id,
            limit=limit
        )
        
        if not results:
            # Try "Very Tanky" if no "Extremely Tanky" found
            results = bot.db_interface.search_builds(
                damage_type=damage_type,
                tankiness="Very Tanky",
                league=league,
                user_id=interaction.user.id,
                limit=limit
            )
        
        if not results:
            embed = discord.Embed(
                title="🛡️ No Tanky Builds Found",
                description="No tanky builds found matching your criteria.",
                color=0xFF6B6B
            )
            await interaction.followup.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🛡️ Tankiest Builds",
            description=f"Found {len(results)} tanky builds",
            color=0xF39C12
        )
        
        # Show results
        for i, build in enumerate(results[:10]):
            ehp_text = f"{int(build['ehp_weighted']):,}" if build.get('ehp_weighted') else "Unknown"
            
            build_info = (
                f"**Level {build['level']} {build['ascendancy'] or build['class']}**\n"
                f"EHP: {ehp_text}\n"
                f"Tankiness: {build.get('tankiness_rating', 'Unknown')}\n"
                f"League: {build['league']}"
            )
            
            if build.get('main_skill'):
                build_info = f"Main: {build['main_skill']}\n" + build_info
            
            profile_url = f"https://www.pathofexile.com/account/view-profile/{build['account']}/characters?characterName={build['name']}"
            
            embed.add_field(
                name=f"#{i+1} {build['name']} ({build['account']})",
                value=f"{build_info}\n[View Profile]({profile_url})",
                inline=True
            )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in tanky command: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description="An error occurred while searching for tanky builds.",
            color=0xFF6B6B
        )
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="character", description="Get detailed character information")
@app_commands.describe(
    account="Account name",
    character="Character name"
)
async def character_info(
    interaction: discord.Interaction,
    account: str,
    character: str
):
    """Get character details"""
    await interaction.response.defer()
    
    try:
        char = bot.db_interface.get_character_details(
            account=account,
            character=character,
            user_id=interaction.user.id
        )
        
        if not char:
            embed = discord.Embed(
                title="❌ Character Not Found",
                description=f"Character **{character}** not found for account **{account}**.",
                color=0xFF6B6B
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Create detailed character embed
        embed = discord.Embed(
            title=f"⚔️ {char['name']}",
            description=f"Account: **{char['account']}**",
            color=0x9B59B6,
            url=char['profile_url']
        )
        
        # Basic info
        embed.add_field(
            name="📊 Basic Info",
            value=f"Level {char['level']} {char['class']}\nLeague: {char['league']}",
            inline=True
        )
        
        # Combat info
        combat_info = []
        if char.get('main_skill'):
            combat_info.append(f"Main: {char['main_skill']}")
        if char.get('primary_damage_type'):
            combat_info.append(f"Damage: {char['primary_damage_type']}")
        if char.get('skill_delivery'):
            combat_info.append(f"Delivery: {char['skill_delivery']}")
        
        if combat_info:
            embed.add_field(
                name="⚔️ Combat",
                value="\n".join(combat_info),
                inline=True
            )
        
        # Defensive info
        defensive_info = []
        if char.get('ehp_weighted'):
            defensive_info.append(f"EHP: {int(char['ehp_weighted']):,}")
        if char.get('tankiness_rating'):
            defensive_info.append(f"Tankiness: {char['tankiness_rating']}")
        if char.get('cost_tier'):
            defensive_info.append(f"Cost: {char['cost_tier']}")
        
        if defensive_info:
            embed.add_field(
                name="🛡️ Defense",
                value="\n".join(defensive_info),
                inline=True
            )
        
        # Key items
        if char.get('unique_items'):
            unique_items = char['unique_items'][:5]  # Show top 5
            if unique_items:
                embed.add_field(
                    name="🎯 Key Uniques",
                    value="\n".join([f"• {item}" for item in unique_items]),
                    inline=False
                )
        
        embed.set_footer(text="Click the title to view full profile on pathofexile.com")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in character command: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description="An error occurred while fetching character details.",
            color=0xFF6B6B
        )
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="top", description="Show top ranked builds")
@app_commands.describe(
    league="League name (leave empty for current leagues)",
    limit="Number of results (1-15)"
)
async def top_builds(
    interaction: discord.Interaction,
    league: Optional[str] = None,
    limit: Optional[int] = 10
):
    """Show top ranked builds"""
    await interaction.response.defer()
    
    try:
        limit = max(1, min(limit or 10, 15))
        
        results = bot.db_interface.get_top_builds(
            league=league,
            limit=limit,
            user_id=interaction.user.id
        )
        
        if not results:
            embed = discord.Embed(
                title="📊 No Data Available",
                description="No top builds data available for the specified league.",
                color=0xFF6B6B
            )
            await interaction.followup.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🏆 Top Ranked Builds",
            description=f"Top {len(results)} builds{f' in {league}' if league else ''}",
            color=0xE67E22
        )
        
        for build in results:
            build_info = f"**Level {build['level']} {build['class']}**\n"
            
            if build.get('main_skill'):
                build_info += f"Main: {build['main_skill']}\n"
            if build.get('ehp_weighted'):
                build_info += f"EHP: {int(build['ehp_weighted']):,}\n"
            if build.get('tankiness_rating'):
                build_info += f"Tankiness: {build['tankiness_rating']}\n"
            
            build_info += f"League: {build.get('league', 'Unknown')}"
            
            profile_url = f"https://www.pathofexile.com/account/view-profile/{build['account']}/characters?characterName={build['name']}"
            
            embed.add_field(
                name=f"#{build['rank']} {build['name']} ({build['account']})",
                value=f"{build_info}\n[View Profile]({profile_url})",
                inline=True
            )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in top command: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description="An error occurred while fetching top builds.",
            color=0xFF6B6B
        )
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="ask", description="Ask questions about build data in natural language")
@app_commands.describe(
    question="Your question about builds (e.g., 'What are the best jugg builds?')"
)
async def ask_question(
    interaction: discord.Interaction,
    question: str
):
    """Natural language query interface"""
    await interaction.response.defer()
    
    if not bot.claude:
        embed = discord.Embed(
            title="❌ Feature Unavailable",
            description="Natural language queries are not available. Claude API key not configured.",
            color=0xFF6B6B
        )
        await interaction.followup.send(embed=embed)
        return
    
    try:
        # Generate session ID
        session_id = f"discord_{interaction.user.id}_{int(datetime.now().timestamp())}"
        
        # Query Claude
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            bot.claude.process_query,
            question,
            session_id
        )
        
        if result.get('error'):
            embed = discord.Embed(
                title="❌ Query Error",
                description=f"Error: {result['error']}",
                color=0xFF6B6B
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Create response embed
        embed = discord.Embed(
            title="🤖 Claude's Analysis",
            description=result.get('summary', 'No summary available'),
            color=0x3498DB
        )
        
        # Add results if available
        if result.get('results') and len(result['results']) > 0:
            results_text = ""
            for i, build in enumerate(result['results'][:5]):  # Top 5 results
                profile_url = f"https://www.pathofexile.com/account/view-profile/{build['account']}/characters?characterName={build['name']}"
                
                build_line = f"**{i+1}.** [{build['name']}]({profile_url}) (Lv{build['level']} {build.get('ascendancy', build.get('class', ''))})"
                
                if build.get('main_skill'):
                    build_line += f" - {build['main_skill']}"
                if build.get('ehp_weighted'):
                    build_line += f" - {int(build['ehp_weighted']):,} EHP"
                
                build_line += f" - {build['league']}\n"
                results_text += build_line
            
            embed.add_field(
                name=f"🏆 Top Results ({result.get('count', len(result['results']))} total)",
                value=results_text,
                inline=False
            )
        
        embed.set_footer(text=f"Asked by {interaction.user.display_name}")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in ask command: {e}")
        embed = discord.Embed(
            title="❌ Query Failed",
            description="An error occurred while processing your question. Please try again.",
            color=0xFF6B6B
        )
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="leagues", description="Show available leagues")
async def show_leagues(interaction: discord.Interaction):
    """Show available leagues"""
    await interaction.response.defer()
    
    try:
        # Get available leagues from database
        from src.storage.database import DatabaseManager
        db = DatabaseManager()
        session = db.get_session()
        
        try:
            from src.storage.database import Character
            leagues = session.query(Character.league).distinct().all()
            league_names = [league[0] for league in leagues if league[0]]
            
            # Filter out Standard and Hardcore
            league_names = [l for l in league_names if l not in ["Standard", "Hardcore"]]
            
            if not league_names:
                embed = discord.Embed(
                    title="📊 No League Data",
                    description="No league data available in the database.",
                    color=0xFF6B6B
                )
                await interaction.followup.send(embed=embed)
                return
            
            embed = discord.Embed(
                title="🏁 Available Leagues",
                description="Challenge leagues with build data available:",
                color=0x2ECC71
            )
            
            # Get character counts per league
            league_stats = []
            for league in league_names:
                count = session.query(Character).filter_by(league=league).count()
                league_stats.append((league, count))
            
            # Sort by character count (descending)
            league_stats.sort(key=lambda x: x[1], reverse=True)
            
            league_list = ""
            for league, count in league_stats:
                league_list += f"• **{league}** - {count:,} characters\n"
            
            embed.add_field(
                name="📈 League Statistics",
                value=league_list,
                inline=False
            )
            
            embed.set_footer(text="Use league names in other commands to filter results")
            
        finally:
            session.close()
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in leagues command: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description="An error occurred while fetching league information.",
            color=0xFF6B6B
        )
        await interaction.followup.send(embed=embed)

@bot.tree.command(name="stats", description="Show database statistics")
async def show_stats(interaction: discord.Interaction):
    """Show database statistics"""
    await interaction.response.defer()
    
    try:
        from src.storage.database import DatabaseManager
        db = DatabaseManager()
        session = db.get_session()
        
        try:
            from src.storage.database import Character, LadderSnapshot, RequestLog
            
            # Get basic stats
            total_chars = session.query(Character).count()
            total_snapshots = session.query(LadderSnapshot).count()
            public_profiles = session.query(Character).filter_by(profile_public=True).count()
            
            # Get recent activity (last 24 hours)
            from datetime import datetime, timedelta
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_requests = session.query(RequestLog).filter(
                RequestLog.timestamp >= yesterday
            ).count()
            
            embed = discord.Embed(
                title="📊 Joker Builds Statistics",
                description="Current database statistics",
                color=0x9B59B6
            )
            
            embed.add_field(
                name="👥 Characters",
                value=f"**{total_chars:,}** total\n**{public_profiles:,}** public profiles",
                inline=True
            )
            
            embed.add_field(
                name="📸 Snapshots",
                value=f"**{total_snapshots:,}** ladder snapshots",
                inline=True
            )
            
            embed.add_field(
                name="🔄 Activity (24h)",
                value=f"**{recent_requests:,}** API requests",
                inline=True
            )
            
            # Calculate enhancement rate
            if total_chars > 0:
                enhancement_rate = (public_profiles / total_chars) * 100
                embed.add_field(
                    name="📈 Enhancement Rate",
                    value=f"**{enhancement_rate:.1f}%** profiles enhanced",
                    inline=True
                )
            
            # Get latest snapshot info
            latest_snapshot = session.query(LadderSnapshot).order_by(
                LadderSnapshot.snapshot_date.desc()
            ).first()
            
            if latest_snapshot:
                hours_ago = (datetime.utcnow() - latest_snapshot.snapshot_date).total_seconds() / 3600
                embed.add_field(
                    name="⏰ Latest Data",
                    value=f"**{hours_ago:.1f}** hours ago\n({latest_snapshot.league})",
                    inline=True
                )
            
            embed.set_footer(text="Data updated in real-time from PoE ladder API")
            
        finally:
            session.close()
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description="An error occurred while fetching statistics.",
            color=0xFF6B6B
        )
        await interaction.followup.send(embed=embed)

def main():
    """Main function to run the bot"""
    # Check for Discord token
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("DISCORD_BOT_TOKEN environment variable not set")
        print("Error: DISCORD_BOT_TOKEN environment variable not set")
        print("\nTo set up the Discord bot:")
        print("1. Go to https://discord.com/developers/applications")
        print("2. Create a new application and bot")
        print("3. Copy the bot token and set DISCORD_BOT_TOKEN environment variable")
        print("4. Invite the bot to your server with appropriate permissions")
        return
    
    # Run the bot
    try:
        bot.run(token)
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print(f"Error starting bot: {e}")

if __name__ == "__main__":
    main()