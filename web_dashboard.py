"""
Flask web dashboard for Joker Builds monitoring
"""

from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
from src.storage.database import DatabaseManager
import os

app = Flask(__name__)
db = DatabaseManager()


@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/api/stats/requests')
def request_stats():
    """Get request statistics"""
    # Get stats for different time periods
    stats_24h = db.get_request_stats(hours=24)
    stats_7d = db.get_request_stats(hours=168)
    
    return jsonify({
        'last_24_hours': stats_24h,
        'last_7_days': stats_7d,
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/api/stats/hourly')
def hourly_stats():
    """Get hourly request counts for charting"""
    hourly_data = db.get_hourly_request_counts(days=7)
    
    # Transform data for Chart.js
    chart_data = {}
    for entry in hourly_data:
        api_type = entry['api_type']
        if api_type not in chart_data:
            chart_data[api_type] = {
                'labels': [],
                'data': []
            }
        chart_data[api_type]['labels'].append(entry['hour'])
        chart_data[api_type]['data'].append(entry['count'])
    
    return jsonify(chart_data)


@app.route('/api/stats/characters')
def character_stats():
    """Get character statistics"""
    stats = db.get_character_stats()
    return jsonify(stats)


@app.route('/api/stats/latest-pulls')
def latest_pulls():
    """Get information about latest successful pulls"""
    stats_24h = db.get_request_stats(hours=24)
    return jsonify({
        'last_successful': stats_24h.get('last_successful', {}),
        'character_links': {
            api_type: f"https://www.pathofexile.com/account/view-profile/{data['account_name']}/characters?characterName={data['character_name']}"
            if data.get('character_name') and data.get('account_name') else None
            for api_type, data in stats_24h.get('last_successful', {}).items()
        }
    })


@app.route('/api/stats/errors')
def recent_errors():
    """Get recent errors"""
    stats_24h = db.get_request_stats(hours=24)
    return jsonify({
        'recent_errors': stats_24h.get('recent_errors', [])
    })


@app.route('/api/stats/discord')
def discord_stats():
    """Get Discord bot request statistics"""
    session = db.get_session()
    try:
        from src.storage.database import RequestLog
        from sqlalchemy import func
        
        # Discord bot requests in last 24h
        cutoff_24h = datetime.utcnow() - timedelta(hours=24)
        discord_24h = session.query(func.count(RequestLog.id)).filter(
            RequestLog.source == 'discord_bot',
            RequestLog.timestamp >= cutoff_24h
        ).scalar()
        
        # Discord bot requests in last 7 days
        cutoff_7d = datetime.utcnow() - timedelta(days=7)
        discord_7d = session.query(func.count(RequestLog.id)).filter(
            RequestLog.source == 'discord_bot',
            RequestLog.timestamp >= cutoff_7d
        ).scalar()
        
        # Last Discord request
        last_discord = session.query(RequestLog).filter(
            RequestLog.source == 'discord_bot'
        ).order_by(RequestLog.timestamp.desc()).first()
        
        # Top Discord users
        top_users = session.query(
            RequestLog.source_user,
            func.count(RequestLog.id).label('count')
        ).filter(
            RequestLog.source == 'discord_bot',
            RequestLog.source_user.isnot(None),
            RequestLog.timestamp >= cutoff_7d
        ).group_by(
            RequestLog.source_user
        ).order_by(
            func.count(RequestLog.id).desc()
        ).limit(10).all()
        
        return jsonify({
            'requests_24h': discord_24h,
            'requests_7d': discord_7d,
            'last_request': {
                'timestamp': last_discord.timestamp.isoformat() if last_discord else None,
                'user': last_discord.source_user if last_discord else None
            },
            'top_users': [
                {'user_id': user, 'count': count}
                for user, count in top_users
            ]
        })
        
    finally:
        session.close()


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Run the dashboard
    app.run(host='0.0.0.0', port=5000, debug=True)