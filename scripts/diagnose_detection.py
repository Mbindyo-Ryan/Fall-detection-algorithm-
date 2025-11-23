#!/usr/bin/env python3
"""
Diagnostic script to check why fall detection might not be working
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detection_skeleton import detector, FALL_CONFIRM_FRAMES, FALL_THRESHOLD_VELOCITY
import cv2
import time

def check_detector_status():
    """Check detector configuration and status"""
    print("=" * 60)
    print("🔍 FALL DETECTION DIAGNOSTICS")
    print("=" * 60)
    print()
    
    print("📊 Detector Configuration:")
    print(f"   FALL_CONFIRM_FRAMES: {FALL_CONFIRM_FRAMES}")
    print(f"   FALL_THRESHOLD_VELOCITY: {FALL_THRESHOLD_VELOCITY}")
    print(f"   Current user_id: {detector.current_user_id}")
    print(f"   Camera source: {detector.camera_source}")
    print(f"   Is running: {detector.is_running}")
    print(f"   Fall counter: {detector.fall_counter}")
    print(f"   Fall logged: {detector.fall_logged}")
    print(f"   Last fall time: {detector.last_fall_time}")
    print()
    
    print("🎯 Detection Thresholds:")
    print(f"   Velocity threshold: {detector.fall_indicators['velocity_threshold']}")
    print(f"   Torso angle threshold: {detector.fall_indicators['torso_angle_threshold']}°")
    print(f"   Height ratio threshold: {detector.fall_indicators['height_ratio_threshold']}")
    print(f"   Ground contact threshold: {detector.fall_indicators['ground_contact_threshold']}")
    print()
    
    print("🤖 Models Status:")
    try:
        from detection_skeleton import ML_MODEL, CNN_ENABLED, CNN_VALIDATOR
        print(f"   ML Model: {'✅ Loaded' if ML_MODEL else '❌ Not loaded'}")
        print(f"   CNN Enabled: {CNN_ENABLED}")
        print(f"   CNN Validator: {'✅ Loaded' if CNN_VALIDATOR else '❌ Not loaded'}")
    except:
        print("   ⚠️  Could not check models")
    print()
    
    print("📹 Testing Camera Feed:")
    try:
        cap = cv2.VideoCapture(detector.camera_source if detector.camera_source.isdigit() else int(detector.camera_source))
        if not cap.isOpened():
            print(f"   ❌ Cannot open camera source: {detector.camera_source}")
            return False
        
        ret, frame = cap.read()
        if not ret:
            print(f"   ❌ Cannot read frame from camera: {detector.camera_source}")
            cap.release()
            return False
        
        print(f"   ✅ Camera working - Frame size: {frame.shape}")
        cap.release()
    except Exception as e:
        print(f"   ❌ Camera error: {e}")
        return False
    print()
    
    print("🧪 Testing Detection on Sample Frame:")
    try:
        cap = cv2.VideoCapture(detector.camera_source if detector.camera_source.isdigit() else int(detector.camera_source))
        ret, frame = cap.read()
        if ret:
            processed_frame, fall_detected, details = detector.detect_fall_enhanced(frame)
            
            print(f"   Pose detected: {details.get('pose_detected', False)}")
            if details.get('pose_detected'):
                print(f"   Velocity: {details.get('velocity', 0):.4f} (threshold: {FALL_THRESHOLD_VELOCITY})")
                print(f"   Torso angle: {details.get('torso_angle', 0):.1f}° (threshold: {detector.fall_indicators['torso_angle_threshold']}°)")
                print(f"   Height ratio: {details.get('height_ratio', 0):.2f} (threshold: {detector.fall_indicators['height_ratio_threshold']})")
                print(f"   Ground contact: {details.get('ground_contact', 0):.2f} (threshold: {detector.fall_indicators['ground_contact_threshold']})")
                print(f"   Fall confidence: {details.get('fall_confidence', 0):.2f} (threshold: 0.5)")
                print(f"   Fall detected: {fall_detected}")
                print(f"   ML prediction: {details.get('ml_prediction', 'N/A')}")
                print(f"   ML confidence: {details.get('ml_confidence', 'N/A')}")
            else:
                print("   ⚠️  No person detected in frame!")
                print("   💡 Make sure:")
                print("      - Camera is pointing at a person")
                print("      - Person is fully visible in frame")
                print("      - Lighting is adequate")
                print("      - Camera is not blocked")
            cap.release()
        else:
            print("   ❌ Could not read frame for testing")
            cap.release()
    except Exception as e:
        print(f"   ❌ Detection test error: {e}")
        import traceback
        traceback.print_exc()
    print()
    
    print("💡 Troubleshooting Tips:")
    print("   1. Check if user_id is set correctly (should match logged-in user)")
    print("   2. Verify camera/video feed is active and showing a person")
    print("   3. Check if MediaPipe is detecting poses (look for pose landmarks)")
    print("   4. Try lowering thresholds if detection is too strict:")
    print("      - FALL_THRESHOLD_VELOCITY (currently: {})".format(FALL_THRESHOLD_VELOCITY))
    print("      - fall_score threshold (currently: 0.5)")
    print("   5. Check server console for detection messages")
    print("   6. Verify database connection is working")
    print()
    
    print("=" * 60)
    return True

if __name__ == "__main__":
    check_detector_status()

