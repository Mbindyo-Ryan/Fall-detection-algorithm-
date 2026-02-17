#!/usr/bin/env python3
"""
Dashboard Performance Test
Tests if dashboard remains responsive while video is streaming
"""

import requests
import time
import threading
from datetime import datetime

BASE_URL = "http://localhost:5000"

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_status(message, status="info"):
    """Print colored status message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    if status == "success":
        print(f"{GREEN}[{timestamp}] ✅ {message}{RESET}")
    elif status == "error":
        print(f"{RED}[{timestamp}] ❌ {message}{RESET}")
    elif status == "warning":
        print(f"{YELLOW}[{timestamp}] ⚠️  {message}{RESET}")
    else:
        print(f"[{timestamp}] ℹ️  {message}")

def test_api_endpoint(endpoint, name, session):
    """Test if an API endpoint responds quickly"""
    try:
        start_time = time.time()
        response = session.get(f"{BASE_URL}{endpoint}", timeout=5)
        elapsed = (time.time() - start_time) * 1000  # Convert to ms
        
        if response.status_code == 200:
            if elapsed < 500:
                print_status(f"{name}: {elapsed:.0f}ms (Excellent)", "success")
                return True, elapsed
            elif elapsed < 1000:
                print_status(f"{name}: {elapsed:.0f}ms (Good)", "warning")
                return True, elapsed
            else:
                print_status(f"{name}: {elapsed:.0f}ms (Slow)", "error")
                return False, elapsed
        else:
            print_status(f"{name}: HTTP {response.status_code}", "error")
            return False, 0
    except requests.exceptions.Timeout:
        print_status(f"{name}: Timeout (>5s)", "error")
        return False, 5000
    except Exception as e:
        print_status(f"{name}: Error - {e}", "error")
        return False, 0

def stream_video(duration=10):
    """Simulate video streaming"""
    try:
        print_status(f"Starting video stream for {duration} seconds...")
        response = requests.get(f"{BASE_URL}/video_feed?source=0", 
                               stream=True, timeout=duration+2)
        
        start_time = time.time()
        frame_count = 0
        
        for chunk in response.iter_content(chunk_size=8192):
            if time.time() - start_time > duration:
                break
            if chunk:
                frame_count += 1
        
        fps = frame_count / duration
        print_status(f"Video stream: {frame_count} frames in {duration}s (~{fps:.1f} FPS)", "success")
        return True
    except Exception as e:
        print_status(f"Video stream error: {e}", "error")
        return False

def test_dashboard_while_streaming():
    """
    Main test: Check if dashboard APIs are responsive while video is streaming
    """
    print("\n" + "="*60)
    print("  DASHBOARD PERFORMANCE TEST")
    print("="*60)
    print("\nThis test will:")
    print("1. Start video streaming in background")
    print("2. Test API endpoints every second")
    print("3. Measure response times")
    print("\n" + "-"*60 + "\n")
    
    # Create session (simulates logged-in user)
    session = requests.Session()
    
    # Test endpoints before streaming
    print("📊 BASELINE TEST (No video streaming)")
    print("-"*60)
    
    endpoints = [
        ("/api/falls", "Falls API"),
        ("/api/users", "Users API"),
        ("/api/performance/metrics", "Metrics API"),
    ]
    
    baseline_times = {}
    for endpoint, name in endpoints:
        success, elapsed = test_api_endpoint(endpoint, name, session)
        baseline_times[endpoint] = elapsed
    
    print("\n⏸️  Waiting 2 seconds...\n")
    time.sleep(2)
    
    # Start video streaming in background thread
    print("🎬 STREAMING TEST (With video running)")
    print("-"*60)
    
    video_thread = threading.Thread(target=stream_video, args=(15,), daemon=True)
    video_thread.start()
    
    time.sleep(1)  # Let stream start
    
    # Test APIs while streaming
    streaming_times = {}
    test_count = 10
    
    for i in range(test_count):
        print(f"\n🔄 Test Round {i+1}/{test_count}")
        for endpoint, name in endpoints:
            success, elapsed = test_api_endpoint(endpoint, name, session)
            if endpoint not in streaming_times:
                streaming_times[endpoint] = []
            streaming_times[endpoint].append(elapsed)
        
        time.sleep(1)
    
    # Wait for video thread to finish
    video_thread.join(timeout=5)
    
    # Calculate results
    print("\n" + "="*60)
    print("  TEST RESULTS")
    print("="*60)
    
    all_good = True
    
    for endpoint, name in endpoints:
        baseline = baseline_times.get(endpoint, 0)
        streaming_avg = sum(streaming_times.get(endpoint, [0])) / len(streaming_times.get(endpoint, [1]))
        
        increase = ((streaming_avg - baseline) / baseline * 100) if baseline > 0 else 0
        
        print(f"\n{name}:")
        print(f"  Baseline:       {baseline:.0f}ms")
        print(f"  While streaming: {streaming_avg:.0f}ms (avg)")
        print(f"  Increase:       {increase:+.1f}%")
        
        # Check if performance is acceptable
        if streaming_avg < 1000 and increase < 100:
            print_status(f"{name}: PASS (Responsive)", "success")
        elif streaming_avg < 2000:
            print_status(f"{name}: WARNING (Slightly slow)", "warning")
            all_good = False
        else:
            print_status(f"{name}: FAIL (Too slow)", "error")
            all_good = False
    
    print("\n" + "="*60)
    if all_good:
        print_status("Dashboard is responsive! ✨", "success")
        print("\nThe dashboard can handle video streaming without blocking.")
    else:
        print_status("Performance issues detected!", "error")
        print("\nRecommendations:")
        print("1. Ensure app is running with threaded=True")
        print("2. Check if generate_frames_async() is being used")
        print("3. Verify time.sleep(0.015) is present in frame loop")
        print("4. Consider reducing video quality or FPS")
    print("="*60 + "\n")
    
    return all_good

def quick_test():
    """Quick connectivity test"""
    print("\n🔍 Quick connectivity test...")
    
    try:
        response = requests.get(f"{BASE_URL}", timeout=5)
        if response.status_code in [200, 302]:  # 302 = redirect to login
            print_status("Flask app is running!", "success")
            return True
        else:
            print_status(f"Unexpected status code: {response.status_code}", "error")
            return False
    except requests.exceptions.ConnectionError:
        print_status("Cannot connect to Flask app", "error")
        print("\nMake sure the Flask app is running:")
        print("  python app_auth.py")
        return False
    except Exception as e:
        print_status(f"Connection error: {e}", "error")
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  CARE SYSTEM - PERFORMANCE TESTER")
    print("="*60)
    
    if not quick_test():
        print("\n❌ Flask app is not running. Start it first:")
        print("   python app_auth.py\n")
        exit(1)
    
    print("\n⚠️  NOTE: You must be logged in for API tests to work")
    print("         This test will check public endpoints only\n")
    
    try:
        input("Press Enter to start performance test (Ctrl+C to cancel)...")
    except KeyboardInterrupt:
        print("\n\nTest cancelled.\n")
        exit(0)
    
    # Run the test
    try:
        success = test_dashboard_while_streaming()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user\n")
        exit(1)