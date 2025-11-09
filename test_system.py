#!/usr/bin/env python3
"""
CARE System - Comprehensive Testing Script
Tests all components and validates MediaPipe integration
"""

import sys
import cv2
import time
import sqlite3
from datetime import datetime

def print_header(title):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_imports():
    """Test if all required libraries are installed"""
    print_header("Testing Python Imports")
    
    required_packages = {
        'cv2': 'opencv-python',
        'mediapipe': 'mediapipe',
        'flask': 'Flask',
        'pyotp': 'pyotp',
        'qrcode': 'qrcode',
        'authlib': 'Authlib',
        'dotenv': 'python-dotenv',
    }
    
    all_good = True
    for module, package in required_packages.items():
        try:
            __import__(module)
            print(f"✅ {package:20s} - Installed")
        except ImportError:
            print(f"❌ {package:20s} - NOT INSTALLED")
            all_good = False
    
    return all_good

def test_opencv_camera():
    """Test OpenCV camera access"""
    print_header("Testing Camera Access")
    
    print("Attempting to open camera 0...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Camera 0 not accessible")
        print("\nTroubleshooting:")
        print("  1. Check if camera is connected")
        print("  2. Check camera permissions")
        print("  3. Try: ls /dev/video* (Linux)")
        return False
    
    print("✅ Camera opened successfully")
    
    # Try to read a frame
    success, frame = cap.read()
    if success:
        h, w = frame.shape[:2]
        print(f"✅ Frame captured: {w}x{h}")
    else:
        print("❌ Failed to read frame from camera")
        cap.release()
        return False
    
    cap.release()
    return True

def test_mediapipe():
    """Test MediaPipe pose detection"""
    print_header("Testing MediaPipe Pose Detection")
    
    try:
        import mediapipe as mp
        print(f"✅ MediaPipe version: {mp.__version__}")
    except Exception as e:
        print(f"❌ MediaPipe import failed: {e}")
        return False
    
    # Initialize pose detector
    try:
        mp_pose = mp.solutions.pose
        pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        print("✅ Pose detector initialized")
    except Exception as e:
        print(f"❌ Pose detector failed: {e}")
        return False
    
    # Test with camera
    print("\nTesting pose detection with camera (5 seconds)...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Cannot open camera for pose test")
        return False
    
    start_time = time.time()
    frames_processed = 0
    frames_with_pose = 0
    
    while time.time() - start_time < 5:
        success, frame = cap.read()
        if not success:
            continue
        
        frames_processed += 1
        
        # Process with MediaPipe
        try:
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image_rgb.flags.writeable = False
            results = pose.process(image_rgb)
            
            if results.pose_landmarks:
                frames_with_pose += 1
        except Exception as e:
            print(f"⚠️ MediaPipe processing error: {e}")
    
    cap.release()
    pose.close()
    
    if frames_processed == 0:
        print("❌ No frames processed")
        return False
    
    detection_rate = (frames_with_pose / frames_processed) * 100
    print(f"\n📊 Results:")
    print(f"   Frames processed: {frames_processed}")
    print(f"   Frames with pose: {frames_with_pose}")
    print(f"   Detection rate:   {detection_rate:.1f}%")
    
    if detection_rate > 50:
        print(f"✅ MediaPipe working well! ({detection_rate:.1f}% detection)")
        return True
    else:
        print(f"⚠️ Low detection rate ({detection_rate:.1f}%)")
        print("   Tips:")
        print("   - Ensure person is in frame")
        print("   - Check lighting")
        print("   - Full body should be visible")
        return False

def test_database():
    """Test database connectivity"""
    print_header("Testing Database")
    
    db_path = "system_config.db"
    
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        print(f"✅ Connected to database: {db_path}")
        
        # Check tables
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        expected_tables = ['users', 'user_cameras', 'falls']
        found_tables = [t[0] for t in tables]
        
        print("\n📊 Database tables:")
        for table in expected_tables:
            if table in found_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   ✅ {table:15s} ({count} rows)")
            else:
                print(f"   ❌ {table:15s} (missing)")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False

def test_detection_module():
    """Test the detection module import"""
    print_header("Testing Detection Module")
    
    try:
        import detection_skeleton
        print("✅ detection_skeleton.py imported successfully")
        
        # Check for key components
        components = [
            'FallDetector',
            'MediaPipeFrameProcessor',
            'AdvancedPerformanceMonitor',
            'generate_frames',
            'detector'
        ]
        
        for comp in components:
            if hasattr(detection_skeleton, comp):
                print(f"   ✅ {comp}")
            else:
                print(f"   ❌ {comp} (missing)")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to import detection_skeleton: {e}")
        return False

def test_flask_app():
    """Test Flask app initialization"""
    print_header("Testing Flask Application")
    
    try:
        import app_auth
        print("✅ app_auth.py imported successfully")
        
        # Check Flask app
        if hasattr(app_auth, 'app'):
            print("✅ Flask app instance found")
            
            # Check routes
            routes = [rule.rule for rule in app_auth.app.url_map.iter_rules()]
            critical_routes = ['/', '/dashboard', '/video_feed', '/api/falls']
            
            print("\n📊 Critical routes:")
            for route in critical_routes:
                if route in routes:
                    print(f"   ✅ {route}")
                else:
                    print(f"   ❌ {route} (missing)")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to import Flask app: {e}")
        return False

def run_live_test():
    """Run a live detection test"""
    print_header("Live Detection Test")
    print("\nThis will open a window showing live fall detection.")
    print("Press 'q' to quit the test.\n")
    
    try:
        input("Press Enter to start live test (or Ctrl+C to skip)...")
    except KeyboardInterrupt:
        print("\nSkipped live test")
        return True
    
    try:
        import detection_skeleton
        
        # Create detector
        test_detector = detection_skeleton.FallDetector()
        test_detector.set_user_id("test_user")
        
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("❌ Cannot open camera for live test")
            return False
        
        print("✅ Live test started - Stand in front of camera")
        print("   Try simulating a fall by slowly lowering to ground")
        
        frame_count = 0
        start_time = time.time()
        
        while True:
            success, frame = cap.read()
            if not success:
                break
            
            frame_count += 1
            processed = test_detector.process_frame_for_fall(frame)
            
            cv2.imshow("CARE System - Live Test (Press 'q' to quit)", processed)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            # Auto-stop after 30 seconds
            if time.time() - start_time > 30:
                print("\n⏱️ 30-second test completed")
                break
        
        cap.release()
        cv2.destroyAllWindows()
        
        # Print metrics
        print("\n📊 Live Test Results:")
        test_detector.performance_monitor.print_real_time_metrics()
        
        return True
        
    except Exception as e:
        print(f"❌ Live test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  CARE SYSTEM - COMPREHENSIVE TEST SUITE")
    print("="*60)
    print(f"  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    tests = [
        ("Python Imports", test_imports),
        ("Camera Access", test_opencv_camera),
        ("MediaPipe", test_mediapipe),
        ("Database", test_database),
        ("Detection Module", test_detection_module),
        ("Flask Application", test_flask_app),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n❌ {test_name} crashed: {e}")
            results[test_name] = False
        
        time.sleep(0.5)  # Brief pause between tests
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10s} - {test_name}")
    
    print("\n" + "-"*60)
    print(f"Results: {passed}/{total} tests passed ({(passed/total)*100:.0f}%)")
    print("-"*60)
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready.")
        print("\nNext steps:")
        print("  1. Start the app: python app_auth.py")
        print("  2. Visit: http://localhost:5000")
        print("  3. Create an account and test fall detection")
        
        # Offer live test
        print("\n" + "="*60)
        try:
            response = input("Run live detection test? (y/n): ").lower()
            if response == 'y':
                run_live_test()
        except KeyboardInterrupt:
            print("\n")
    else:
        print("\n⚠️ Some tests failed. Please fix issues before running the system.")
        print("\nTroubleshooting:")
        print("  - Check requirements.txt is installed: pip install -r requirements.txt")
        print("  - Verify camera is connected and accessible")
        print("  - Ensure database file has proper permissions")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
        sys.exit(1)