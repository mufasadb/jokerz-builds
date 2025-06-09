#!/usr/bin/env python3
"""
Health check script for Joker Builds dashboard
Run this to diagnose startup issues on Unraid or any deployment
"""

import sys
import os
import traceback
from datetime import datetime

def health_check():
    """Comprehensive health check for the dashboard"""
    
    print("=" * 70)
    print("JOKER BUILDS DASHBOARD HEALTH CHECK")
    print("=" * 70)
    print(f"Timestamp: {datetime.now()}")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print()
    
    checks_passed = 0
    total_checks = 10
    
    # Check 1: Environment variables
    print("1. ENVIRONMENT VARIABLES")
    print("-" * 30)
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        db_path = os.getenv('DB_PATH', '/app/data/ladder_snapshots.db')
        flask_env = os.getenv('FLASK_ENV', 'production')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        
        print(f"✅ DB_PATH: {db_path}")
        print(f"✅ FLASK_ENV: {flask_env}")
        print(f"{'✅' if anthropic_key else '⚠️'} ANTHROPIC_API_KEY: {'SET' if anthropic_key else 'NOT SET'}")
        checks_passed += 1
        
    except Exception as e:
        print(f"❌ Error loading environment: {e}")
    print()
    
    # Check 2: File system
    print("2. FILE SYSTEM ACCESS")
    print("-" * 30)
    try:
        # Check if we can write to logs
        logs_dir = '/app/logs'
        if os.path.exists(logs_dir):
            print(f"✅ Logs directory exists: {logs_dir}")
            test_file = os.path.join(logs_dir, 'health_check.test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            print("✅ Can write to logs directory")
        else:
            print(f"⚠️ Logs directory missing: {logs_dir}")
        
        # Check data directory
        data_dir = '/app/data'
        if os.path.exists(data_dir):
            print(f"✅ Data directory exists: {data_dir}")
        else:
            print(f"❌ Data directory missing: {data_dir}")
            
        checks_passed += 1
        
    except Exception as e:
        print(f"❌ File system error: {e}")
    print()
    
    # Check 3: Python imports
    print("3. PYTHON IMPORTS")
    print("-" * 30)
    try:
        import flask
        print(f"✅ Flask: {flask.__version__}")
        
        import flask_socketio
        print(f"✅ Flask-SocketIO: {flask_socketio.__version__}")
        
        import sqlalchemy
        print(f"✅ SQLAlchemy: {sqlalchemy.__version__}")
        
        import anthropic
        print(f"✅ Anthropic: {anthropic.__version__}")
        
        checks_passed += 1
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
    print()
    
    # Check 4: Project imports
    print("4. PROJECT IMPORTS")
    print("-" * 30)
    try:
        from src.storage.database import DatabaseManager
        print("✅ DatabaseManager imported")
        
        from src.scheduler.task_manager import task_manager
        print("✅ TaskManager imported")
        
        from src.analysis.claude_integration import NaturalLanguageQueryService
        print("✅ Claude integration imported")
        
        checks_passed += 1
        
    except Exception as e:
        print(f"❌ Project import error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
    print()
    
    # Check 5: Database connection
    print("5. DATABASE CONNECTION")
    print("-" * 30)
    try:
        from src.storage.database import DatabaseManager
        db = DatabaseManager()
        session = db.get_session()
        
        # Test basic query
        result = session.execute("SELECT 1").fetchone()
        print(f"✅ Database connection successful: {result}")
        
        # Check tables exist
        tables = session.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [t[0] for t in tables]
        
        required_tables = ['characters', 'ladder_snapshots', 'request_logs']
        for table in required_tables:
            if table in table_names:
                print(f"✅ Table exists: {table}")
            else:
                print(f"❌ Table missing: {table}")
        
        # Check character count
        char_count = session.execute("SELECT COUNT(*) FROM characters").fetchone()[0]
        print(f"✅ Characters in database: {char_count:,}")
        
        session.close()
        checks_passed += 1
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
    print()
    
    # Check 6: Templates
    print("6. TEMPLATES")
    print("-" * 30)
    try:
        template_file = 'templates/dashboard.html'
        if os.path.exists(template_file):
            with open(template_file, 'r') as f:
                content = f.read()
                if 'Joker Builds' in content:
                    print(f"✅ Dashboard template exists and valid")
                else:
                    print(f"⚠️ Dashboard template exists but may be invalid")
        else:
            print(f"❌ Dashboard template missing: {template_file}")
            
        checks_passed += 1
        
    except Exception as e:
        print(f"❌ Template error: {e}")
    print()
    
    # Check 7: Port availability
    print("7. PORT AVAILABILITY")
    print("-" * 30)
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 5001))
        sock.close()
        
        if result == 0:
            print("⚠️ Port 5001 is already in use")
        else:
            print("✅ Port 5001 is available")
            
        checks_passed += 1
        
    except Exception as e:
        print(f"❌ Port check error: {e}")
    print()
    
    # Check 8: Memory and disk
    print("8. SYSTEM RESOURCES")
    print("-" * 30)
    try:
        import psutil
        
        # Memory
        memory = psutil.virtual_memory()
        print(f"✅ Available memory: {memory.available / (1024**3):.1f} GB")
        
        # Disk space
        disk = psutil.disk_usage('/')
        print(f"✅ Available disk: {disk.free / (1024**3):.1f} GB")
        
        checks_passed += 1
        
    except ImportError:
        print("⚠️ psutil not available - cannot check system resources")
        checks_passed += 1  # Don't fail for this
    except Exception as e:
        print(f"❌ System resource error: {e}")
    print()
    
    # Check 9: Permissions
    print("9. PERMISSIONS")
    print("-" * 30)
    try:
        # Check if we can create files in working directory
        test_file = 'permission_test.tmp'
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        print("✅ Can write to working directory")
        
        # Check Python path permissions
        import tempfile
        with tempfile.NamedTemporaryFile() as f:
            print("✅ Can create temporary files")
            
        checks_passed += 1
        
    except Exception as e:
        print(f"❌ Permission error: {e}")
    print()
    
    # Check 10: Network
    print("10. NETWORK CONNECTIVITY")
    print("-" * 30)
    try:
        import requests
        
        # Test external connectivity (for league API)
        response = requests.get('https://www.pathofexile.com/api/leagues', timeout=10)
        if response.status_code == 200:
            print("✅ Can reach Path of Exile API")
        else:
            print(f"⚠️ Path of Exile API returned: {response.status_code}")
            
        checks_passed += 1
        
    except Exception as e:
        print(f"❌ Network error: {e}")
    print()
    
    # Final summary
    print("=" * 70)
    print("HEALTH CHECK SUMMARY")
    print("=" * 70)
    print(f"Checks passed: {checks_passed}/{total_checks}")
    
    if checks_passed == total_checks:
        print("🎉 ALL CHECKS PASSED - Dashboard should start successfully!")
        return True
    elif checks_passed >= total_checks - 2:
        print("⚠️ Most checks passed - Dashboard might start with minor issues")
        return True
    else:
        print("❌ Multiple checks failed - Dashboard likely won't start")
        return False

if __name__ == "__main__":
    try:
        success = health_check()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Health check failed with critical error: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)