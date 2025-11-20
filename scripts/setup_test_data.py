#!/usr/bin/env python3
"""
Quick setup script for test data organization

This script helps you:
1. Create folder structure
2. Organize videos into falls/no_falls
3. Generate annotation templates
4. List videos with absolute paths for dashboard

Usage:
    # Create folder structure
    python scripts/setup_test_data.py --setup-folders
    
    # Organize videos (interactive)
    python scripts/setup_test_data.py --organize /path/to/videos
    
    # Generate annotation template
    python scripts/setup_test_data.py --annotation-template fall_videos/falls/fall_001.mp4
    
    # List videos with absolute paths
    python scripts/setup_test_data.py --list-paths fall_videos/
"""

import argparse
import os
import sys
from pathlib import Path
import cv2


def setup_folders():
    """Create recommended folder structure"""
    folders = [
        'fall_videos/falls',
        'fall_videos/no_falls',
        'datasets/urfd',
        'datasets/le2i',
        'datasets/custom',
        'annotations',
        'data'
    ]
    
    print("📁 Creating folder structure...")
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"   ✅ {folder}")
    
    print("\n✅ Folder structure created!")


def organize_videos(source_dir):
    """Interactively organize videos into falls/no_falls"""
    if not os.path.exists(source_dir):
        print(f"❌ Directory not found: {source_dir}")
        return
    
    # Find video files
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
    video_files = []
    for file in os.listdir(source_dir):
        if any(file.lower().endswith(ext) for ext in video_extensions):
            video_files.append(os.path.join(source_dir, file))
    
    if not video_files:
        print(f"❌ No video files found in {source_dir}")
        return
    
    print(f"\n📹 Found {len(video_files)} video files")
    print("Organize videos (f=fall, n=no fall, s=skip, q=quit):\n")
    
    falls_dir = 'fall_videos/falls'
    no_falls_dir = 'fall_videos/no_falls'
    os.makedirs(falls_dir, exist_ok=True)
    os.makedirs(no_falls_dir, exist_ok=True)
    
    for video_path in video_files:
        video_name = os.path.basename(video_path)
        print(f"\n{video_name}")
        
        # Try to open video to show first frame
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                # Resize for display
                height, width = frame.shape[:2]
                if width > 800:
                    scale = 800 / width
                    frame = cv2.resize(frame, (int(width * scale), int(height * scale)))
                cv2.imshow('Video Preview (Press key: f=fall, n=no fall, s=skip)', frame)
                key = cv2.waitKey(0) & 0xFF
                cv2.destroyAllWindows()
                
                if key == ord('f'):
                    dest = os.path.join(falls_dir, video_name)
                    os.rename(video_path, dest)
                    print(f"   ✅ Moved to falls/")
                elif key == ord('n'):
                    dest = os.path.join(no_falls_dir, video_name)
                    os.rename(video_path, dest)
                    print(f"   ✅ Moved to no_falls/")
                elif key == ord('s'):
                    print(f"   ⏭️  Skipped")
                elif key == ord('q'):
                    print(f"   🛑 Quitting")
                    break
            cap.release()
    
    print("\n✅ Organization complete!")


def generate_annotation_template(video_path):
    """Generate annotation CSV template for a video"""
    if not os.path.exists(video_path):
        print(f"❌ Video not found: {video_path}")
        return
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Cannot open video: {video_path}")
        return
    
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    duration = total_frames / fps if fps > 0 else 0
    
    cap.release()
    
    video_name = Path(video_path).stem
    annotation_file = f"annotations/{video_name}.csv"
    
    print(f"\n📝 Generating annotation template for: {video_path}")
    print(f"   Total frames: {total_frames}")
    print(f"   Duration: {duration:.2f} seconds")
    print(f"   FPS: {fps:.2f}")
    
    # Create template with all frames marked as no fall
    with open(annotation_file, 'w') as f:
        f.write('frame_number,is_fall\n')
        for frame in range(total_frames):
            f.write(f'{frame},0\n')
    
    print(f"✅ Template created: {annotation_file}")
    print(f"\n💡 Edit this file to mark fall frames (change 0 to 1)")


def list_video_paths(directory):
    """List all videos with absolute paths for dashboard"""
    if not os.path.exists(directory):
        print(f"❌ Directory not found: {directory}")
        return
    
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
    video_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in video_extensions):
                video_path = os.path.join(root, file)
                video_files.append(video_path)
    
    if not video_files:
        print(f"❌ No video files found in {directory}")
        return
    
    print(f"\n📹 Found {len(video_files)} video files\n")
    print("Absolute paths for dashboard:\n")
    print("="*80)
    
    for video_path in sorted(video_files):
        abs_path = os.path.abspath(video_path)
        video_name = os.path.basename(video_path)
        print(f"{video_name}")
        print(f"  {abs_path}\n")
    
    print("="*80)
    print("\n💡 Copy these paths when adding cameras in the dashboard")


def main():
    parser = argparse.ArgumentParser(description='Setup test data for fall detection system')
    parser.add_argument('--setup-folders', action='store_true',
                       help='Create recommended folder structure')
    parser.add_argument('--organize', metavar='DIR',
                       help='Interactively organize videos from directory')
    parser.add_argument('--annotation-template', metavar='VIDEO',
                       help='Generate annotation template for video')
    parser.add_argument('--list-paths', metavar='DIR',
                       help='List all videos with absolute paths')
    
    args = parser.parse_args()
    
    if args.setup_folders:
        setup_folders()
    elif args.organize:
        organize_videos(args.organize)
    elif args.annotation_template:
        generate_annotation_template(args.annotation_template)
    elif args.list_paths:
        list_video_paths(args.list_paths)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()

