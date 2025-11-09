#!/usr/bin/env python3
"""
Test the trained fall detection model on new videos

Usage:
  python scripts/test_model.py --video path/to/video.mp4 --model models/fall_classifier.pkl
  python scripts/test_model.py --video path/to/video.mp4 --ground-truth annotations.csv
"""

import argparse
import cv2
import sys
import os
import pandas as pd
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import detection_skeleton
    from detection_skeleton import FallDetector, load_ml_model
except ImportError:
    print("❌ Error: Could not import detection_skeleton")
    sys.exit(1)


def test_video(video_path: str, model_path: str = None, ground_truth_file: str = None):
    """Test model on a video file"""
    
    print("\n" + "="*60)
    print("  FALL DETECTION MODEL TEST")
    print("="*60)
    print(f"Video: {video_path}")
    if model_path:
        print(f"Model: {model_path}")
    print("="*60 + "\n")
    
    # Load ML model if provided
    if model_path:
        if not load_ml_model(model_path):
            print("⚠️  Continuing with rule-based detection only")
    
    # Load ground truth if provided
    ground_truth = None
    if ground_truth_file:
        try:
            df = pd.read_csv(ground_truth_file)
            ground_truth = {}
            for _, row in df.iterrows():
                frame_start = int(row.get('start_frame', 0))
                frame_end = int(row.get('end_frame', frame_start))
                for frame_idx in range(frame_start, frame_end + 1):
                    ground_truth[frame_idx] = 1
            print(f"✅ Loaded ground truth: {len(ground_truth)} fall frames")
        except Exception as e:
            print(f"⚠️  Could not load ground truth: {e}")
    
    # Create detector
    detector = FallDetector()
    detector.set_user_id("test_user")
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Cannot open video: {video_path}")
        return
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    print(f"📹 Video info: {total_frames} frames, {fps:.2f} FPS\n")
    
    # Statistics
    stats = {
        'total_frames': 0,
        'falls_detected': 0,
        'true_positives': 0,
        'false_positives': 0,
        'false_negatives': 0,
        'true_negatives': 0,
        'ml_predictions': 0,
        'rule_based_detections': 0
    }
    
    frame_idx = 0
    print("🔄 Processing video... (Press 'q' to quit, 's' to save frame)")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process frame
            processed_frame, fall_detected, details = detector.detect_fall_enhanced(frame)
            
            # Get ground truth for this frame
            actual_fall = ground_truth.get(frame_idx, 0) if ground_truth else None
            
            # Update statistics
            stats['total_frames'] += 1
            if fall_detected:
                stats['falls_detected'] += 1
                if details.get('ml_prediction') is not None:
                    stats['ml_predictions'] += 1
                else:
                    stats['rule_based_detections'] += 1
            
            if actual_fall is not None:
                if actual_fall and fall_detected:
                    stats['true_positives'] += 1
                elif not actual_fall and not fall_detected:
                    stats['true_negatives'] += 1
                elif not actual_fall and fall_detected:
                    stats['false_positives'] += 1
                elif actual_fall and not fall_detected:
                    stats['false_negatives'] += 1
            
            # Display
            display_text = []
            if fall_detected:
                display_text.append("⚠️ FALL DETECTED!")
            if details.get('ml_prediction') is not None:
                ml_conf = details.get('ml_confidence', 0)
                display_text.append(f"ML: {ml_conf:.2f}")
            if details.get('hybrid_confidence'):
                display_text.append(f"Hybrid: {details['hybrid_confidence']:.2f}")
            
            if display_text:
                y_pos = 50
                for text in display_text:
                    cv2.putText(processed_frame, text, (20, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    y_pos += 30
            
            cv2.imshow("Fall Detection Test", processed_frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                cv2.imwrite(f"test_frame_{frame_idx}.jpg", processed_frame)
                print(f"💾 Saved frame {frame_idx}")
            
            frame_idx += 1
            
            # Progress indicator
            if frame_idx % 30 == 0:
                progress = (frame_idx / total_frames) * 100
                print(f"   Progress: {progress:.1f}% ({frame_idx}/{total_frames})", end='\r')
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
    finally:
        cap.release()
        cv2.destroyAllWindows()
    
    # Print results
    print("\n\n" + "="*60)
    print("  TEST RESULTS")
    print("="*60)
    print(f"Total frames: {stats['total_frames']}")
    print(f"Falls detected: {stats['falls_detected']}")
    print(f"  - ML predictions: {stats['ml_predictions']}")
    print(f"  - Rule-based: {stats['rule_based_detections']}")
    
    if ground_truth:
        tp = stats['true_positives']
        tn = stats['true_negatives']
        fp = stats['false_positives']
        fn = stats['false_negatives']
        
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        print(f"\n📊 Performance Metrics:")
        print(f"   Accuracy:  {accuracy:.3f}")
        print(f"   Precision: {precision:.3f}")
        print(f"   Recall:    {recall:.3f}")
        print(f"   F1-Score:  {f1:.3f}")
        print(f"\n📊 Confusion Matrix:")
        print(f"   True Positives:  {tp}")
        print(f"   True Negatives:  {tn}")
        print(f"   False Positives: {fp}")
        print(f"   False Negatives: {fn}")
    
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Test fall detection model on video')
    parser.add_argument('--video', required=True, help='Path to test video')
    parser.add_argument('--model', default='models/fall_classifier.pkl', help='Path to trained model')
    parser.add_argument('--ground-truth', help='CSV file with ground truth annotations')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.video):
        print(f"❌ Video not found: {args.video}")
        return
    
    test_video(args.video, args.model, args.ground_truth)


if __name__ == '__main__':
    main()

