"""
Configuration settings for the PoE ladder scraper
"""

import os

# Collection settings
COLLECTION_MODE = os.getenv('COLLECTION_MODE', 'conservative')  # conservative/balanced/aggressive
COLLECTION_TIME = os.getenv('COLLECTION_TIME', '02:00')  # UTC time for daily collection
CLEANUP_TIME = os.getenv('CLEANUP_TIME', '03:00')  # UTC time for weekly cleanup
CLEANUP_DAYS = int(os.getenv('CLEANUP_DAYS', '90'))  # Days to retain data

# Database settings
DB_PATH = os.getenv('DB_PATH', '/app/data/ladder_snapshots.db')

# API Rate limiting (very conservative defaults)
RATE_LIMITS = {
    'ladder': {
        'requests_per_minute': int(os.getenv('LADDER_RPM', '20')),
        'requests_per_hour': int(os.getenv('LADDER_RPH', '100')),
        'requests_per_day': int(os.getenv('LADDER_RPD', '500')),
        'base_delay': float(os.getenv('LADDER_DELAY', '3.0'))
    },
    'character': {
        'requests_per_minute': int(os.getenv('CHARACTER_RPM', '10')),
        'requests_per_hour': int(os.getenv('CHARACTER_RPH', '50')),
        'requests_per_day': int(os.getenv('CHARACTER_RPD', '200')),
        'base_delay': float(os.getenv('CHARACTER_DELAY', '6.0'))
    },
    'ninja': {
        'requests_per_minute': int(os.getenv('NINJA_RPM', '15')),
        'requests_per_hour': int(os.getenv('NINJA_RPH', '60')),
        'requests_per_day': int(os.getenv('NINJA_RPD', '300')),
        'base_delay': float(os.getenv('NINJA_DELAY', '4.0'))
    }
}

# Collection mode configurations
COLLECTION_CONFIGS = {
    'conservative': {
        'description': 'Minimal API usage, focuses on core data',
        'total_daily_calls': '~55',
        'estimated_time': '~4 minutes',
        'recommended_for': 'Daily automated collection'
    },
    'balanced': {
        'description': 'Moderate API usage, good data coverage',
        'total_daily_calls': '~83', 
        'estimated_time': '~7 minutes',
        'recommended_for': 'Manual collection or testing'
    },
    'aggressive': {
        'description': 'Higher API usage, maximum data collection',
        'total_daily_calls': '~108',
        'estimated_time': '~9 minutes', 
        'recommended_for': 'One-off deep collection'
    }
}

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Notifications
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')  # Optional webhook for notifications

# Data backup
BACKUP_TO_FILES = os.getenv('BACKUP_TO_FILES', 'true').lower() == 'true'