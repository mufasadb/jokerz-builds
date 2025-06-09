# Joker Builds - Path of Exile Build Analytics

A comprehensive data collection and analysis system for Path of Exile builds, featuring automated ladder tracking, build categorization, EHP calculations, and a web dashboard for monitoring.

![Docker Pulls](https://img.shields.io/docker/pulls/callmebeachy/jokerz-builds)
![Docker Image Size](https://img.shields.io/docker/image-size/callmebeachy/jokerz-builds)
![GitHub Actions](https://github.com/mufasadb/jokerz-builds/workflows/Build%20and%20Push%20Docker%20Image/badge.svg)
![GitHub Stars](https://img.shields.io/github/stars/mufasadb/jokerz-builds)

## Features

- 🔄 **Automated Daily Collection** - Collects ladder snapshots from multiple leagues
- 📊 **Build Categorization** - Categorizes builds by damage type, defense style, and cost
- 🛡️ **EHP Calculation** - Calculates effective health pools against all damage types
- 🌐 **Web Dashboard** - Real-time monitoring with charts and statistics
- 🤖 **Discord Bot Ready** - Interface for Discord bot integration
- 🔍 **Advanced Search** - Query builds by multiple criteria including tankiness
- 🧹 **Auto Cleanup** - Configurable retention of historical data

## Quick Start

### Docker Hub

```bash
docker pull callmebeachy/jokerz-builds:latest
```

### Docker Compose (Recommended)

```bash
# Create directory
mkdir -p /mnt/user/appdata/joker-builds

# Create docker-compose.yml (see below)
cd /mnt/user/appdata/joker-builds

# Start services
docker-compose up -d
```

## Unraid Setup Guide

### Method 1: Community Applications (Coming Soon)

Search for "Joker Builds" in Community Applications

### Method 2: Docker Template

1. Go to Docker tab in Unraid
2. Click "Add Container"
3. Switch to "Advanced View"
4. Fill in the following:

**Container Settings:**
- **Name**: `joker-builds`
- **Repository**: `callmebeachy/jokerz-builds:latest`
- **Docker Hub URL**: `https://hub.docker.com/r/callmebeachy/jokerz-builds`
- **Icon URL**: `https://web.poecdn.com/image/Art/2DItems/Currency/CurrencyRerollRare.png`

**Network Settings:**
- **Network Type**: `bridge`
- **Console shell command**: `Shell`

**Port Mappings (Add Port):**
| Container Port | Host Port | Description |
|----------------|-----------|-------------|
| 5001 | 5001 | Web Dashboard |

**Path Mappings (Add Path):**
| Container Path | Host Path | Access Mode | Description |
|----------------|-----------|-------------|-------------|
| `/app/data` | `/mnt/user/appdata/joker-builds/data` | Read/Write | Database & Data |
| `/app/logs` | `/mnt/user/appdata/joker-builds/logs` | Read/Write | Logs (Optional) |

**Variable Mappings (Add Variable):**
| Name | Key | Value | Description |
|------|-----|-------|-------------|
| Collection Time | `COLLECTION_TIME` | `02:00` | Daily collection time (UTC) |
| Cleanup Time | `CLEANUP_TIME` | `03:00` | Cleanup time (UTC) |
| Cleanup Days | `CLEANUP_DAYS` | `90` | Days to keep data |
| Log Level | `LOG_LEVEL` | `INFO` | Logging level |

**Extra Parameters:**
```
--restart=unless-stopped
```

### Method 3: Docker Compose (Recommended)

Create `/mnt/user/appdata/joker-builds/docker-compose.yml`:

```yaml
version: '3.8'

services:
  joker-builds-collector:
    image: callmebeachy/jokerz-builds:latest
    container_name: joker-builds-collector
    restart: unless-stopped
    
    environment:
      - COLLECTION_TIME=02:00  # 2 AM UTC = 9 PM EST / 6 PM PST
      - CLEANUP_TIME=03:00
      - CLEANUP_DAYS=90
      - LOG_LEVEL=INFO
      
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    
    command: python -m src.scheduler.daily_collector

  dashboard:
    image: callmebeachy/jokerz-builds:latest
    container_name: joker-builds-dashboard
    restart: unless-stopped
    
    environment:
      - FLASK_ENV=production
    
    volumes:
      - ./data:/app/data  # Shared with collector
    
    ports:
      - "5001:5001"
    
    command: python web_dashboard.py
    
    depends_on:
      - joker-builds-collector
```

Then run:
```bash
cd /mnt/user/appdata/joker-builds
docker-compose up -d
```

## Configuration

### Environment Variables

| Variable | Default | Description | Example |
|----------|---------|-------------|---------|
| `COLLECTION_TIME` | `02:00` | Daily collection time (24hr UTC) | `14:00` for 2 PM UTC |
| `CLEANUP_TIME` | `03:00` | Old data cleanup time (24hr UTC) | `03:00` for 3 AM UTC |
| `CLEANUP_DAYS` | `90` | Days of data to keep | `30` for 1 month |
| `LOG_LEVEL` | `INFO` | Logging verbosity | `DEBUG`, `INFO`, `WARNING` |
| `DB_PATH` | `/app/data/ladder_snapshots.db` | Database location | Leave default |

### Time Zone Reference

Collection runs at UTC time. Common conversions:
- **02:00 UTC** = 9 PM EST / 6 PM PST (previous day)
- **14:00 UTC** = 9 AM EST / 6 AM PST

## Web Dashboard

Access at: `http://[UNRAID-IP]:5001`

### Dashboard Features

1. **Overview Cards**
   - Total API requests (24h/7d) with success rates
   - Total characters in database
   - Discord bot usage statistics
   - Last request timestamps

2. **Charts**
   - 7-day request timeline by API type
   - Request distribution pie chart
   - Auto-refreshes every 30 seconds

3. **Activity Feed**
   - Latest successful data pulls
   - Direct links to character profiles
   - Recent errors with timestamps

4. **API Monitoring**
   - Request counts by type
   - Success/failure rates
   - Response times

5. **Manual Data Collection**
   - Start collection on-demand
   - Real-time progress monitoring
   - League selection options
   - Live status updates via WebSocket

## Data Collection

### What Gets Collected

1. **Leagues Monitored** (Auto-detected)
   - Standard & Hardcore (permanent)
   - Current challenge league + all variants (SC/HC/SSF)

2. **Data Per League**
   - Top 2000 characters
   - Character stats, skills, items
   - Build categorization
   - EHP calculations

3. **Collection Schedule**
   - Runs daily at `COLLECTION_TIME`
   - ~800+ character profiles enhanced per day
   - Automatic rate limiting (respectful of GGG's API)

### API Rate Limits

Conservative limits to respect GGG's servers:
- **Ladder API**: 4/min, 15/hour
- **Character API**: 3/min, 12/hour
- Automatic exponential backoff on failures

## Discord Bot Integration

### Basic Setup

```python
from discord_bot_interface import DiscordBotInterface

interface = DiscordBotInterface()

# Search for builds
@bot.command()
async def tanky_fire(ctx):
    results = interface.search_builds(
        damage_type='fire',
        tankiness='Extremely Tanky',
        user_id=ctx.author.id,
        limit=5
    )
    # Format and send results
```

### Available Methods

- `search_builds()` - Search by damage type, tankiness, EHP
- `get_character_details()` - Get specific character info
- `get_top_builds()` - Get leaderboard builds

All Discord queries are automatically logged for dashboard statistics.

## Database Access

### SQLite Database Location
`/mnt/user/appdata/joker-builds/data/ladder_snapshots.db`

### Query Examples

```python
from src.storage.database import DatabaseManager

db = DatabaseManager()

# Find extremely tanky builds
tanky = db.search_builds_by_category(
    tankiness_rating='Extremely Tanky',
    min_ehp=20000
)

# Find budget fire builds
budget_fire = db.search_builds_by_category(
    damage_type='fire',
    cost_tier='budget'
)
```

### Direct SQL Access

```bash
# Enter container
docker exec -it joker-builds-collector /bin/bash

# Query database
sqlite3 /app/data/ladder_snapshots.db

# Example queries
SELECT COUNT(*) FROM characters;
SELECT league, COUNT(*) FROM characters GROUP BY league;
SELECT tankiness_rating, COUNT(*) FROM characters 
  WHERE tankiness_rating IS NOT NULL 
  GROUP BY tankiness_rating;
```

## Maintenance

### Manual Operations

**Via Web Dashboard (Recommended):**
- Navigate to `http://[UNRAID-IP]:5001`
- Use the "Data Collection Control" panel
- Select leagues and options
- Click "Start Collection"
- Monitor real-time progress

**Via Command Line:**
```bash
# Check collection status
docker exec joker-builds-collector python -m src.scheduler.daily_collector --status

# Force immediate collection
docker exec joker-builds-collector python -m src.scheduler.daily_collector --once

# Manual cleanup
docker exec joker-builds-collector python -m src.scheduler.daily_collector --cleanup
```

### Monitoring

```bash
# View logs
docker logs joker-builds-collector -f
docker logs joker-builds-dashboard -f

# Check health
docker ps | grep joker-builds
```

### Backup

Database is stored at:
`/mnt/user/appdata/joker-builds/data/ladder_snapshots.db`

Backup regularly or use Unraid's appdata backup.

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs joker-builds-collector

# Verify permissions
ls -la /mnt/user/appdata/joker-builds/

# Recreate directories
mkdir -p /mnt/user/appdata/joker-builds/{data,logs}
chmod -R 755 /mnt/user/appdata/joker-builds
```

### No Data Appearing
- Wait for `COLLECTION_TIME` to pass
- Check logs for API errors
- Verify internet connectivity
- Ensure correct time zone understanding (UTC)

### Dashboard Not Loading
- Check port 5001 is free: `netstat -tulpn | grep 5001`
- Verify dashboard container is running
- Check firewall settings
- Try `http://localhost:5001` from Unraid terminal

### High Memory Usage
- Reduce `CLEANUP_DAYS` to store less history
- Check for runaway collection processes
- Restart containers

## Development

### Local Setup
```bash
git clone https://github.com/mufasadb/jokerz-builds.git
cd jokerz-builds
pip install -r requirements.txt
python -m pytest tests/
```

### Building Locally
```bash
docker build -t jokerz-builds:local .
```

## Support

- **Issues**: [GitHub Issues](https://github.com/mufasadb/jokerz-builds/issues)
- **Docker Hub**: [callmebeachy/jokerz-builds](https://hub.docker.com/r/callmebeachy/jokerz-builds)

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Path of Exile API by Grinding Gear Games
- PoE Ninja for data insights
- The PoE community for build diversity