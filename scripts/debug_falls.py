#!/usr/bin/env python3
"""
Debug script to check if falls are being logged to the database.
Run this script to verify fall detection and logging is working.
"""

import sqlite3
import sys
import os
import time
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = "system_config.db"

def check_database():
    """Check database connection and table structure"""
    print("=" * 60)
    print("🔍 FALL DETECTION DEBUG SCRIPT")
    print("=" * 60)
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database file not found: {DB_PATH}")
        print("   Make sure you're running this from the project root directory.")
        return False
    
    print(f"✅ Database file found: {DB_PATH}")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Check if falls table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='falls'")
        if not c.fetchone():
            print("❌ 'falls' table does not exist!")
            print("   Run the Flask app once to initialize the database.")
            conn.close()
            return False
        
        print("✅ 'falls' table exists")
        
        # Get table schema
        c.execute("PRAGMA table_info(falls)")
        columns = c.fetchall()
        print(f"\n📋 Falls table columns: {', '.join([col[1] for col in columns])}")
        
        # Count total falls
        c.execute("SELECT COUNT(*) as count FROM falls")
        total_falls = c.fetchone()['count']
        print(f"\n📊 Total falls in database: {total_falls}")
        
        if total_falls == 0:
            print("⚠️  No falls found in database yet.")
            print("   This could mean:")
            print("   1. No falls have been detected yet")
            print("   2. Falls are being detected but not logged (check server console)")
            print("   3. Database connection issue in detection thread")
            conn.close()
            return True
        
        # Get recent falls (last 24 hours)
        one_day_ago = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            SELECT COUNT(*) as count 
            FROM falls 
            WHERE timestamp >= ?
        """, (one_day_ago,))
        recent_falls = c.fetchone()['count']
        print(f"📅 Falls in last 24 hours: {recent_falls}")
        
        # Get falls by status
        c.execute("""
            SELECT status, COUNT(*) as count 
            FROM falls 
            GROUP BY status
        """)
        status_counts = c.fetchall()
        print(f"\n📈 Falls by status:")
        for row in status_counts:
            print(f"   {row['status']}: {row['count']}")
        
        # Get most recent 5 falls
        c.execute("""
            SELECT id, user_id, timestamp, status, severity, location
            FROM falls
            ORDER BY timestamp DESC, id DESC
            LIMIT 5
        """)
        recent = c.fetchall()
        
        print(f"\n🕐 Most recent 5 falls:")
        if recent:
            for fall in recent:
                print(f"   ID: {fall['id']}")
                print(f"      User: {fall['user_id']}")
                print(f"      Time: {fall['timestamp']}")
                print(f"      Status: {fall['status']}")
                print(f"      Severity: {fall['severity']}")
                print(f"      Location: {fall['location'] or 'Unknown'}")
                print()
        else:
            print("   No falls found")
        
        # Check for falls in last hour
        one_hour_ago = (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            SELECT COUNT(*) as count 
            FROM falls 
            WHERE timestamp >= ?
        """, (one_hour_ago,))
        last_hour = c.fetchone()['count']
        print(f"⏰ Falls in last hour: {last_hour}")
        
        if last_hour == 0 and recent_falls > 0:
            print("\n⚠️  WARNING: No falls detected in the last hour!")
            print("   This suggests detection may have stopped working.")
            print("   Check:")
            print("   1. Is the video feed active?")
            print("   2. Is the detector.user_id set correctly?")
            print("   3. Are there any errors in the server console?")
            print("   4. Is the cooldown period blocking new detections?")
        
        # Check for users
        c.execute("SELECT COUNT(*) as count FROM users")
        user_count = c.fetchone()['count']
        print(f"\n👥 Total users in database: {user_count}")
        
        # Check falls by user
        c.execute("""
            SELECT user_id, COUNT(*) as count 
            FROM falls 
            GROUP BY user_id
            ORDER BY count DESC
        """)
        user_falls = c.fetchall()
        if user_falls:
            print(f"\n👤 Falls by user:")
            for row in user_falls:
                print(f"   {row['user_id']}: {row['count']} falls")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_detector_status():
    """Check if detector is initialized and configured"""
    print("\n" + "=" * 60)
    print("🔧 DETECTOR STATUS CHECK")
    print("=" * 60)
    
    try:
        import detection_skeleton
        detector = detection_skeleton.detector
        
        print(f"✅ Detector instance found")
        print(f"   Current user_id: {detector.current_user_id}")
        print(f"   Fall counter: {detector.fall_counter}")
        print(f"   Fall logged flag: {detector.fall_logged}")
        print(f"   Last fall time: {detector.last_fall_time}")
        
        if detector.last_fall_time > 0:
            time_since = time.time() - detector.last_fall_time
            print(f"   Time since last fall: {time_since:.1f} seconds")
        
        # Check configuration
        print(f"\n⚙️  Detection Configuration:")
        print(f"   FALL_CONFIRM_FRAMES: {detection_skeleton.FALL_CONFIRM_FRAMES}")
        print(f"   FALL_THRESHOLD_VELOCITY: {detection_skeleton.FALL_THRESHOLD_VELOCITY}")
        print(f"   FALL_LOG_COOLDOWN: {detection_skeleton.FALL_LOG_COOLDOWN}")
        
        return True
    except ImportError as e:
        print(f"❌ Could not import detection_skeleton: {e}")
        return False
    except Exception as e:
        print(f"❌ Error checking detector: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = check_database()
    if success:
        check_detector_status()
    
    print("\n" + "=" * 60)
    print("✅ Debug check complete!")
    print("=" * 60)
    print("\n💡 Tips:")
    print("   - If no falls are being logged, check the Flask server console")
    print("   - Look for messages like '✅ Logged fall at...'")
    print("   - Check for cooldown messages: '⏸️ Fall logging cooldown active'")
    print("   - Verify the user_id is set correctly in the video feed route")
    print("   - Make sure the video feed is active and processing frames")

