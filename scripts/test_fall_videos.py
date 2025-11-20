#!/usr/bin/env python3
"""
Test fall detection system with video files.

Usage:
  python scripts/test_fall_videos.py --video path/to/video.mp4
  python scripts/test_fall_videos.py --video path/to/video.mp4 --ground-truth annotations.csv
  python scripts/test_fall_videos.py --directory videos/ --output results.json
"""

import argparse
import cv2
import os
import json
import time
from datetime import datetime
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detection_skeleton import FallDetector, init_db, DB_PATH
import sqlite3


def test_single_video(video_path, detector, ground_truth=None, output_file=None):
    """Test a single video file"""
    print(f"\n{'='*60}")
    print(f"  TESTING VIDEO: {os.path.basename(video_path)}")
    print(f"{'='*60}")
    
    if not os.path.exists(video_path):
        print(f"❌ Video file not found: {video_path}")
        return None
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Cannot open video: {video_path}")
        return None
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total_frames / fps if fps > 0 else 0
    
    print(f"📹 Video Info:")
    print(f"   FPS: {fps:.2f}")
    print(f"   Total Frames: {total_frames}")
    print(f"   Duration: {duration:.2f} seconds")
    
    # Initialize detector
    detector.set_user_id("test_user")
    detector.set_camera_source(video_path)
    
    # Test results
    results = {
        'video_path': video_path,
        'video_name': os.path.basename(video_path),
        'fps': fps,
        'total_frames': total_frames,
        'duration': duration,
        'detections': [],
        'fall_detected': False,
        'first_detection_frame': None,
        'first_detection_time': None,
        'total_detections': 0,
        'ground_truth': ground_truth,
        'correct': None,
        'processing_time': 0
    }
    
    print(f"\n🎬 Processing video...")
    start_time = time.time()
    frame_count = 0
    fall_detected_count = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Process frame
            processed_frame = detector.process_frame_for_fall(frame)
            
            # Check if fall was detected (check fall_counter)
            if detector.fall_counter >= 8:  # FALL_CONFIRM_FRAMES
                if not results['fall_detected']:
                    # First detection
                    results['fall_detected'] = True
                    results['first_detection_frame'] = frame_count
                    results['first_detection_time'] = frame_count / fps
                    print(f"   ⚠️  FALL DETECTED at frame {frame_count} ({results['first_detection_time']:.2f}s)")
                
                fall_detected_count += 1
                results['detections'].append({
                    'frame': frame_count,
                    'time': frame_count / fps,
                    'confidence': detector.fall_counter / 8.0  # Normalized confidence
                })
            
            # Progress indicator
            if frame_count % 30 == 0:
                progress = (frame_count / total_frames * 100) if total_frames > 0 else 0
                print(f"   Processing: {frame_count}/{total_frames} frames ({progress:.1f}%)", end='\r')
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    finally:
        cap.release()
        processing_time = time.time() - start_time
        results['processing_time'] = processing_time
        results['total_detections'] = len(results['detections'])
        
        # Calculate FPS
        processing_fps = frame_count / processing_time if processing_time > 0 else 0
        results['processing_fps'] = processing_fps
    
    # Compare with ground truth
    if ground_truth is not None:
        results['correct'] = (results['fall_detected'] == ground_truth)
        if results['correct']:
            print(f"\n✅ Result: CORRECT (Expected: {ground_truth}, Got: {results['fall_detected']})")
        else:
            print(f"\n❌ Result: INCORRECT (Expected: {ground_truth}, Got: {results['fall_detected']})")
    
    # Print summary
    print(f"\n📊 Test Results:")
    print(f"   Fall Detected: {'✅ YES' if results['fall_detected'] else '❌ NO'}")
    if results['fall_detected']:
        print(f"   First Detection: Frame {results['first_detection_frame']} ({results['first_detection_time']:.2f}s)")
        print(f"   Total Detections: {results['total_detections']}")
    print(f"   Processing Time: {processing_time:.2f}s")
    print(f"   Processing FPS: {processing_fps:.2f}")
    
    return results


def test_directory(directory, output_file=None):
    """Test all videos in a directory"""
    print(f"\n{'='*60}")
    print(f"  TESTING VIDEOS IN DIRECTORY: {directory}")
    print(f"{'='*60}")
    
    if not os.path.exists(directory):
        print(f"❌ Directory not found: {directory}")
        return
    
    # Find video files
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
    video_files = []
    for file in os.listdir(directory):
        if any(file.lower().endswith(ext) for ext in video_extensions):
            video_files.append(os.path.join(directory, file))
    
    if len(video_files) == 0:
        print(f"❌ No video files found in {directory}")
        return
    
    print(f"📁 Found {len(video_files)} video files")
    
    # Initialize detector
    detector = FallDetector()
    init_db(DB_PATH, [])
    
    # Test each video
    all_results = []
    for i, video_path in enumerate(video_files, 1):
        print(f"\n[{i}/{len(video_files)}] Testing: {os.path.basename(video_path)}")
        result = test_single_video(video_path, detector, output_file=output_file)
        if result:
            all_results.append(result)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"Total Videos: {len(all_results)}")
    print(f"Falls Detected: {sum(1 for r in all_results if r['fall_detected'])}")
    print(f"No Falls: {sum(1 for r in all_results if not r['fall_detected'])}")
    
    # Save results
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        print(f"\n✅ Results saved to: {output_file}")
    
    return all_results


def main():
    parser = argparse.ArgumentParser(description='Test fall detection with video files')
    parser.add_argument('--video', help='Path to single video file')
    parser.add_argument('--directory', help='Directory containing video files')
    parser.add_argument('--ground-truth', type=int, choices=[0, 1],
                       help='Ground truth: 1=fall, 0=no fall')
    parser.add_argument('--output', default='test_results.json',
                       help='Output JSON file for results')
    
    args = parser.parse_args()
    
    if not args.video and not args.directory:
        parser.print_help()
        return
    
    # Initialize database
    init_db(DB_PATH, [])
    
    if args.video:
        # Test single video
        detector = FallDetector()
        result = test_single_video(args.video, detector, args.ground_truth, args.output)
        if result:
            with open(args.output, 'w') as f:
                json.dump([result], f, indent=2)
            print(f"\n✅ Results saved to: {args.output}")
    elif args.directory:
        # Test directory
        test_directory(args.directory, args.output)


if __name__ == '__main__':
    main()

