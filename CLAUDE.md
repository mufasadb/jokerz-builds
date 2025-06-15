# CLAUDE.md

## Project Overview

Joker Builds - Data scraping from PoE Ninja, data interpretation, grouping, and then chat based interface on the data for build decision based on meta analysis, and tagging

## Key Information

- **Language/Framework**: Python 3.11+ with SQLAlchemy, SQLite, Docker
- **Build Command**: docker build -t joker-builds .
- **Test Command**: python -m pytest tests/ -v
- **Lint Command**: python -m flake8 src/ (if configured)

## Project Structure

```
joker-builds/
├── CLAUDE.md        # This file - project context for Claude
└── [Your project files here]
```

## Important Notes

Utilise TDD, always create a test to confirm behaviour is working before returning work to the instructor. 
Keep most individual tests aside, but maintain a End-To-End standard workflow test and run it on each occasion
Ensure that any case that might involve polling external websites does not make too many requests
Do not leave To dos, complete all work relevant to a task, do not mock data, except for tests, where data schemas have already been confirmed
Do not stray from task, touching on unrelated or even only partially related tasks
Where utilising libraries pick those that are most popular and recently updated to avoid deprecation

## Discord Bot Setup

### Prerequisites
- Python 3.11+ environment with project dependencies installed
- Discord account with server admin permissions
- Anthropic API key (optional, for natural language queries)

### 1. Create Discord Application
1. Go to https://discord.com/developers/applications
2. Click "New Application" and give it a name (e.g., "Joker Builds")
3. Go to the "Bot" section in the left sidebar
4. Click "Add Bot" and confirm
5. Under "Token", click "Copy" to copy your bot token
6. Save this token securely - you'll need it for the environment variable

### 2. Configure Bot Permissions
In the Discord Developer Portal:
1. Go to "OAuth2" → "URL Generator"
2. Select scopes: `bot` and `applications.commands`
3. Select bot permissions:
   - Send Messages
   - Use Slash Commands
   - Embed Links
   - Read Message History
4. Copy the generated URL

### 3. Set Environment Variables
Add to your `.env` file:
```
DISCORD_BOT_TOKEN=your_bot_token_here
ANTHROPIC_API_KEY=your_anthropic_key_here  # Optional, for /ask command
```

### 4. Install Discord.py
```bash
pip install discord.py
```

### 5. Invite Bot to Server
1. Use the URL from step 2 to invite the bot to your Discord server
2. Grant the requested permissions

### 6. Run the Bot
```bash
python discord_bot.py
```

### Available Commands
- `/help` - Show all available commands
- `/search` - Search builds with filters (damage type, tankiness, etc.)
- `/tanky` - Find the tankiest builds  
- `/top` - Show top ranked builds
- `/character` - Get detailed character information
- `/ask` - Natural language queries (requires Anthropic API key)
- `/leagues` - Show available leagues
- `/stats` - Show database statistics

### Troubleshooting
- Ensure the bot has proper permissions in your Discord server
- Check that environment variables are set correctly
- Verify the database contains character data before using commands
- For `/ask` command, ensure ANTHROPIC_API_KEY is configured

## Cloudflare Access for Remote Debugging

The application is hosted at https://jokers-builds.beachysapp.com/ behind Cloudflare Access authentication.

### Service Token Configuration
For automated access (e.g., Claude debugging), service tokens are configured in `.env`:
```
CF_ACCESS_CLIENT_ID=8566de2f6aa3e27f29862d6ac7cda19e.access
CF_ACCESS_CLIENT_SECRET=4da273b33d39db31ba1ca3764c1dcbefeea7209b0a3888df5746fea0390f1e84
```

### Using Service Token
When accessing the site programmatically, include headers:
```bash
curl -H "CF-Access-Client-Id: 8566de2f6aa3e27f29862d6ac7cda19e.access" \
     -H "CF-Access-Client-Secret: 4da273b33d39db31ba1ca3764c1dcbefeea7209b0a3888df5746fea0390f1e84" \
     https://jokers-builds.beachysapp.com/
```

### Cloudflare Configuration
- Service token "claude" created in Zero Trust dashboard
- Policy order: Service tokens evaluated first, then email auth
- Both policies set to "Allow" action

## Git Workflow

ALWAYS commit changes after completing and testing each task.
ALWAYS push to remote repository after completing a feature or major fix.
Use descriptive commit messages that explain what was implemented.
We can always roll back if needed, so commit frequently to save progress.
This ensures work is preserved and allows for easy rollbacks if needed.
Push regularly to keep remote repository up to date with completed work.