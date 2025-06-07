"""
Flask web dashboard for Joker Builds monitoring
"""

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from datetime import datetime, timedelta
from src.storage.database import DatabaseManager
from src.scheduler.task_manager import task_manager, TaskStatus
import os
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'joker-builds-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")
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


@app.route('/api/scraping/start', methods=['POST'])
def start_scraping():
    """Start a manual scraping task"""
    data = request.get_json() or {}
    
    leagues = data.get('leagues')  # None means all leagues
    enhance_profiles = data.get('enhance_profiles', True)
    categorize_builds = data.get('categorize_builds', True)
    
    # Check if already running
    active_task = task_manager.get_active_task()
    if active_task:
        return jsonify({
            'error': 'Scraping task already running',
            'active_task_id': active_task.task_id
        }), 400
    
    # Submit new task
    task_id = task_manager.submit_collection_task(
        leagues=leagues,
        enhance_profiles=enhance_profiles,
        categorize_builds=categorize_builds
    )
    
    return jsonify({
        'task_id': task_id,
        'status': 'started'
    })


@app.route('/api/scraping/status')
def scraping_status():
    """Get current scraping status"""
    active_task = task_manager.get_active_task()
    recent_tasks = task_manager.get_all_tasks()[:5]  # Last 5 tasks
    
    # Get available leagues
    from src.scraper.ladder_scraper import LadderScraper
    scraper = LadderScraper()
    available_leagues = scraper.leagues_to_monitor
    
    return jsonify({
        'active_task': {
            'task_id': active_task.task_id,
            'status': active_task.status.value,
            'current_step': active_task.current_step,
            'current_league': active_task.current_league,
            'current_operation': active_task.current_operation,
            'progress_percentage': active_task.progress_percentage,
            'completed_steps': active_task.completed_steps,
            'total_steps': active_task.total_steps,
            'characters_collected': active_task.characters_collected,
            'characters_enhanced': active_task.characters_enhanced,
            'characters_categorized': active_task.characters_categorized,
            'leagues_completed': active_task.leagues_completed,
            'elapsed_time': active_task.elapsed_time,
            'warnings': active_task.warnings
        } if active_task else None,
        'recent_tasks': [
            {
                'task_id': task.task_id,
                'status': task.status.value,
                'created_at': task.created_at.isoformat(),
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'characters_collected': task.characters_collected,
                'leagues_completed': task.leagues_completed,
                'error_message': task.error_message
            }
            for task in recent_tasks
        ],
        'available_leagues': available_leagues,
        'queue_size': task_manager.task_queue.qsize()
    })


@app.route('/api/scraping/cancel/<task_id>', methods=['POST'])
def cancel_scraping(task_id):
    """Cancel a pending scraping task"""
    success = task_manager.cancel_task(task_id)
    
    if success:
        return jsonify({'status': 'cancelled'})
    else:
        return jsonify({'error': 'Cannot cancel task'}), 400


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    # Send current status immediately
    emit('scraping_update', get_scraping_status_dict())


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')


def get_scraping_status_dict():
    """Get scraping status as dictionary for WebSocket"""
    active_task = task_manager.get_active_task()
    return {
        'active_task': {
            'task_id': active_task.task_id,
            'status': active_task.status.value,
            'current_step': active_task.current_step,
            'current_league': active_task.current_league,
            'current_operation': active_task.current_operation,
            'progress_percentage': active_task.progress_percentage,
            'completed_steps': active_task.completed_steps,
            'total_steps': active_task.total_steps,
            'characters_collected': active_task.characters_collected,
            'characters_enhanced': active_task.characters_enhanced,
            'characters_categorized': active_task.characters_categorized,
            'elapsed_time': active_task.elapsed_time
        } if active_task else None,
        'timestamp': datetime.utcnow().isoformat()
    }


def broadcast_scraping_updates():
    """Background thread to broadcast scraping updates"""
    last_status = None
    
    while True:
        try:
            current_status = get_scraping_status_dict()
            
            # Only broadcast if status changed
            if current_status != last_status:
                socketio.emit('scraping_update', current_status)
                last_status = current_status
            
            time.sleep(2)  # Update every 2 seconds
            
        except Exception as e:
            print(f"Error broadcasting updates: {e}")
            time.sleep(5)


# Start the task manager and background broadcaster
task_manager.start_worker()
broadcast_thread = threading.Thread(target=broadcast_scraping_updates, daemon=True)
broadcast_thread.start()


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    
    # Run the dashboard with SocketIO
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)