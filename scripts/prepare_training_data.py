#!/usr/bin/env python3
"""
Dataset Downloader and Feature Extractor for Fall Detection Training

This script:
1. Downloads/processes fall detection datasets (UR Fall Detection, Le2i, etc.)
2. Extracts features using our detection_skeleton components
3. Generates labeled feature_logs.csv for training

Usage:
    # Process UR Fall Detection dataset
    python scripts/prepare_training_data.py --dataset urfd --output data/feature_logs.csv
    
    # Process local videos with manual labeling
    python scripts/prepare_training_data.py --videos path/to/videos --output data/feature_logs.csv
    
    # Process with annotation file
    python scripts/prepare_training_data.py --videos path/to/videos --annotations annotations.csv --output data/feature_logs.csv
"""

import argparse
import os
import sys
import cv2
import csv
import json
import requests
import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional
import time

# Add parent directory to path to import detection_skeleton
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import detection_skeleton
    from detection_skeleton import FallDetector, FEATURE_LOG_PATH
except ImportError:
    print("❌ Error: Could not import detection_skeleton. Make sure you're running from the project root.")
    sys.exit(1)


class DatasetProcessor:
    """Process fall detection datasets and extract features"""
    
    def __init__(self, output_csv: str):
        self.output_csv = output_csv
        self.detector = FallDetector()
        self.detector.set_user_id("dataset_processor")
        self._ensure_csv_header()
    
    def _ensure_csv_header(self):
        """Ensure CSV file has proper header"""
        if not os.path.exists(self.output_csv):
            os.makedirs(os.path.dirname(self.output_csv) or '.', exist_ok=True)
            with open(self.output_csv, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'user_id', 'fall_detected', 'actual_fall',
                    'confidence', 'velocity', 'torso_angle', 'height_ratio',
                    'ground_contact', 'ground_distance', 'velocity_3d_magnitude',
                    'pose_detected', 'video_source', 'frame_number'
                ])
    
    def process_image_sequence(self, image_dir: str, actual_fall_frames: Optional[List[Tuple[int, int]]] = None,
                               video_label: str = "unknown") -> int:
        """
        Process a directory of PNG/JPEG images as a video sequence
        
        Args:
            image_dir: Path to directory containing image sequence
            actual_fall_frames: List of (start_frame, end_frame) tuples indicating fall segments
            video_label: Label for the video (e.g., "fall", "no_fall")
        
        Returns:
            Number of frames processed
        """
        print(f"\n🖼️  Processing image sequence: {image_dir}")
        
        # Get all image files, sorted
        image_files = []
        for ext in ['*.png', '*.jpg', '*.jpeg', '*.PNG', '*.JPG', '*.JPEG']:
            image_files.extend(Path(image_dir).glob(ext))
        
        image_files = sorted(image_files, key=lambda x: int(''.join(filter(str.isdigit, x.name))) if any(c.isdigit() for c in x.name) else 0)
        
        if not image_files:
            print(f"❌ No image files found in {image_dir}")
            return 0
        
        total_frames = len(image_files)
        print(f"   Frames: {total_frames} images")
        
        frame_count = 0
        processed_count = 0
        
        # Determine actual_fall for each frame
        def get_actual_fall(frame_idx: int) -> Optional[int]:
            if actual_fall_frames:
                for start, end in actual_fall_frames:
                    if start <= frame_idx <= end:
                        return 1
                return 0
            elif video_label.lower() in ['fall', 'falls']:
                return 1
            elif video_label.lower() in ['no_fall', 'adl', 'normal']:
                return 0
            return None
        
        try:
            with open(self.output_csv, 'a', newline='') as f:
                writer = csv.writer(f)
                
                for img_path in image_files:
                    frame = cv2.imread(str(img_path))
                    if frame is None:
                        continue
                    
                    # Process frame with detector
                    processed_frame, fall_detected, details = self.detector.detect_fall_enhanced(frame)
                    
                    # Determine actual fall label
                    actual_fall = get_actual_fall(frame_count)
                    
                    # Only log if we have a label or want to log all frames
                    if actual_fall is not None or video_label == "unknown":
                        writer.writerow([
                            datetime.utcnow().isoformat(),
                            "dataset_processor",
                            int(bool(fall_detected)),
                            '' if actual_fall is None else int(bool(actual_fall)),
                            round(details.get('fall_confidence', 0.0), 6),
                            round(details.get('velocity', 0.0), 6),
                            round(details.get('torso_angle', 0.0), 6),
                            round(details.get('height_ratio', 0.0), 6),
                            round(details.get('ground_contact', 0.0), 6),
                            '' if details.get('ground_distance') is None else round(details.get('ground_distance', 0.0), 6),
                            '' if details.get('velocity_3d_magnitude') is None else round(details.get('velocity_3d_magnitude', 0.0), 6),
                            int(bool(details.get('tensor_points_available', False))),
                            video_label,
                            frame_count
                        ])
                        processed_count += 1
                    
                    frame_count += 1
                    
                    # Progress indicator
                    if frame_count % 30 == 0:
                        progress = (frame_count / total_frames) * 100
                        print(f"   Progress: {progress:.1f}% ({frame_count}/{total_frames} frames)", end='\r')
        
        except Exception as e:
            print(f"\n❌ Error processing image sequence: {e}")
        
        print(f"\n   ✅ Processed {processed_count} frames from {total_frames} total")
        return processed_count
    
    def process_video(self, video_path: str, actual_fall_frames: Optional[List[Tuple[int, int]]] = None, 
                     video_label: str = "unknown") -> int:
        """
        Process a video file or image sequence directory and extract features
        
        Args:
            video_path: Path to video file OR directory containing image sequence
            actual_fall_frames: List of (start_frame, end_frame) tuples indicating fall segments
            video_label: Label for the video (e.g., "fall", "no_fall")
        
        Returns:
            Number of frames processed
        """
        # Check if it's a directory (image sequence) or file (video)
        if os.path.isdir(video_path):
            return self.process_image_sequence(video_path, actual_fall_frames, video_label)
        
        print(f"\n📹 Processing: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"❌ Cannot open video: {video_path}")
            return 0
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        print(f"   Frames: {total_frames}, FPS: {fps:.2f}")
        
        frame_count = 0
        processed_count = 0
        
        # Determine actual_fall for each frame
        def get_actual_fall(frame_idx: int) -> Optional[int]:
            if actual_fall_frames:
                for start, end in actual_fall_frames:
                    if start <= frame_idx <= end:
                        return 1
                return 0
            elif video_label.lower() in ['fall', 'falls']:
                return 1
            elif video_label.lower() in ['no_fall', 'adl', 'normal']:
                return 0
            return None
        
        try:
            with open(self.output_csv, 'a', newline='') as f:
                writer = csv.writer(f)
                
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    
                    # Process frame with detector
                    processed_frame, fall_detected, details = self.detector.detect_fall_enhanced(frame)
                    
                    # Determine actual fall label
                    actual_fall = get_actual_fall(frame_count)
                    
                    # Only log if we have a label or want to log all frames
                    if actual_fall is not None or video_label == "unknown":
                        writer.writerow([
                            datetime.utcnow().isoformat(),
                            "dataset_processor",
                            int(bool(fall_detected)),
                            '' if actual_fall is None else int(bool(actual_fall)),
                            round(details.get('fall_confidence', 0.0), 6),
                            round(details.get('velocity', 0.0), 6),
                            round(details.get('torso_angle', 0.0), 6),
                            round(details.get('height_ratio', 0.0), 6),
                            round(details.get('ground_contact', 0.0), 6),
                            '' if details.get('ground_distance') is None else round(details.get('ground_distance', 0.0), 6),
                            '' if details.get('velocity_3d_magnitude') is None else round(details.get('velocity_3d_magnitude', 0.0), 6),
                            int(bool(details.get('tensor_points_available', False))),
                            video_label,
                            frame_count
                        ])
                        processed_count += 1
                    
                    frame_count += 1
                    
                    # Progress indicator
                    if frame_count % 30 == 0:
                        progress = (frame_count / total_frames) * 100
                        print(f"   Progress: {progress:.1f}% ({frame_count}/{total_frames} frames)", end='\r')
        
        except Exception as e:
            print(f"\n❌ Error processing video: {e}")
        finally:
            cap.release()
        
        print(f"\n   ✅ Processed {processed_count} frames from {frame_count} total")
        return processed_count
    
    def process_urfd_dataset(self, dataset_path: str):
        """
        Process UR Fall Detection Dataset
        
        Dataset structure (PNG image sequences in zip files):
        After extracting RGB zip files, you'll have:
        dataset_path/
            falls/
                fall-01-cam0-rgb/  (directory with PNG images)
                    frame_001.png
                    frame_002.png
                    ...
                fall-02-cam0-rgb/
                    ...
            adls/
                adl-01-cam0-rgb/  (directory with PNG images)
                    frame_001.png
                    frame_002.png
                    ...
        
        OR if organized differently:
        dataset_path/
            fall-01-cam0-rgb/  (directories)
            fall-02-cam0-rgb/
            adl-01-cam0-rgb/
            ...
        
        Note: CSV files are optional annotations - we extract features from PNG sequences directly
        """
        print("\n📦 Processing UR Fall Detection Dataset...")
        print("   Using PNG image sequences from extracted RGB zip files")
        
        # Check for organized folders first
        falls_dir = os.path.join(dataset_path, 'falls')
        adls_dir = os.path.join(dataset_path, 'adls')
        
        # If no folders, check for directories directly in dataset_path
        if not os.path.exists(falls_dir) and not os.path.exists(adls_dir):
            print("   No 'falls/' or 'adls/' folders found, checking root directory...")
            falls_dir = dataset_path
            adls_dir = dataset_path
        
        total_processed = 0
        
        # Process fall sequences (look for directories starting with 'fall' or in 'falls' folder)
        fall_dirs = []
        if os.path.exists(falls_dir):
            for item in os.listdir(falls_dir):
                item_path = os.path.join(falls_dir, item)
                # Check if it's a directory (PNG sequence) or a video file
                if os.path.isdir(item_path) and ('fall' in item.lower() or 'rgb' in item.lower()):
                    fall_dirs.append(item_path)
                elif os.path.isfile(item_path) and item.endswith(('.avi', '.mp4', '.mov')):
                    fall_dirs.append(item_path)
        
        if fall_dirs:
            print(f"\n⚠️  Processing {len(fall_dirs)} FALL sequences from {falls_dir}")
            for seq_path in sorted(fall_dirs):
                total_processed += self.process_video(seq_path, video_label="fall")
        
        # Process ADL (no fall) sequences
        adl_dirs = []
        if os.path.exists(adls_dir):
            for item in os.listdir(adls_dir):
                item_path = os.path.join(adls_dir, item)
                # Check if it's a directory (PNG sequence) or a video file
                if os.path.isdir(item_path) and ('adl' in item.lower() or 'rgb' in item.lower()):
                    adl_dirs.append(item_path)
                elif os.path.isfile(item_path) and item.endswith(('.avi', '.mp4', '.mov')):
                    adl_dirs.append(item_path)
        
        if adl_dirs:
            print(f"\n✅ Processing {len(adl_dirs)} ADL (no fall) sequences from {adls_dir}")
            for seq_path in sorted(adl_dirs):
                total_processed += self.process_video(seq_path, video_label="no_fall")
        
        if total_processed == 0:
            print("\n⚠️  No sequences found!")
            print("   Looking for:")
            print("   - Directories containing PNG images (extracted from RGB zip files)")
            print("   - Video files: .avi, .mp4, .mov")
            print("   With names containing: 'fall', 'adl', or 'rgb'")
            print(f"   In directory: {dataset_path}")
            print("\n   Expected structure after extracting RGB zip files:")
            print("     datasets/urfd/falls/fall-01-cam0-rgb/  (PNG images inside)")
            print("     datasets/urfd/adls/adl-01-cam0-rgb/   (PNG images inside)")
        
        print(f"\n🎉 Total frames processed: {total_processed}")
        return total_processed
    
    def parse_le2i_annotation(self, annotation_file: str) -> Optional[Tuple[int, int]]:
        """
        Parse Le2i annotation file to get fall frame range
        
        Format: 'video (i).txt' contains:
        - Frame number of beginning of fall
        - Frame number of end of fall
        - (Plus bounding box info we don't need)
        
        Returns: (start_frame, end_frame) or None if no fall
        """
        try:
            with open(annotation_file, 'r') as f:
                lines = f.readlines()
                if len(lines) >= 2:
                    # First line: start frame, second line: end frame
                    start_frame = int(lines[0].strip())
                    end_frame = int(lines[1].strip())
                    return (start_frame, end_frame)
        except Exception as e:
            print(f"   ⚠️  Could not parse annotation {annotation_file}: {e}")
        return None
    
    def process_le2i_dataset(self, dataset_path: str):
        """
        Process Le2i Fall Detection Dataset
        
        Dataset structure (handles nested folders and archive structure):
        dataset_path/
            archive (1)/  (or directly locations)
                Home_01/
                    Home_01/  (nested)
                        video (1).avi
                        Annotation_files/
                            video (1).txt
                Coffee_room_01/
                    Coffee_room_01/
                        video (1).avi
                        Annotation_files/
                            video (1).txt
                ...
        
        Format: 320x240, 25 FPS
        Logic: If annotation file exists for a video = FALL, otherwise = NO FALL
        Annotation files contain: start_frame, end_frame of fall
        """
        print("\n📦 Processing Le2i Fall Detection Dataset...")
        print("   Format: 320x240, 25 FPS")
        print("   Using annotation files to determine fall vs no-fall")
        print("   (Videos with annotations = FALL, videos without = NO FALL)")
        
        # Check if dataset is in an archive folder
        archive_path = os.path.join(dataset_path, 'archive (1)')
        if os.path.exists(archive_path):
            print(f"   Found archive folder, using: {archive_path}")
            dataset_path = archive_path
        
        # Find all location folders (Home_01, Home_02, Coffee_room_01, etc.)
        location_folders = []
        for item in os.listdir(dataset_path):
            item_path = os.path.join(dataset_path, item)
            if os.path.isdir(item_path) and not item.startswith('.'):
                # Check if it's a location folder (contains videos or has nested structure)
                location_folders.append((item, item_path))
        
        print(f"   Found {len(location_folders)} location folders")
        
        total_processed = 0
        
        for location_name, location_path in location_folders:
            print(f"\n📍 Processing location: {location_name}")
            
            # Handle nested structure (e.g., Home_01/Home_01/)
            actual_location_path = location_path
            nested_path = os.path.join(location_path, location_name)
            if os.path.exists(nested_path):
                actual_location_path = nested_path
                print(f"   Using nested path: {nested_path}")
            
            # Find annotation files for this location
            annotation_dir = os.path.join(actual_location_path, 'Annotation_files')
            annotation_files = {}
            
            if os.path.exists(annotation_dir):
                for ann_file in os.listdir(annotation_dir):
                    if ann_file.endswith('.txt') and 'video' in ann_file.lower():
                        video_num = ''.join(filter(str.isdigit, ann_file))
                        if video_num:
                            annotation_files[video_num] = os.path.join(annotation_dir, ann_file)
                print(f"   Found {len(annotation_files)} annotation files (fall videos)")
            
            # Find all video files in this location
            video_files = []
            for root, dirs, files in os.walk(actual_location_path):
                # Skip Annotation_files directory
                if 'Annotation_files' in root:
                    continue
                for file in files:
                    if file.endswith(('.avi', '.mp4', '.mov')):
                        video_files.append(os.path.join(root, file))
            
            if not video_files:
                print(f"   No videos found in {location_name}")
                continue
            
            print(f"   Found {len(video_files)} videos")
            
            for video_path in sorted(video_files):
                video_file = os.path.basename(video_path)
                
                # Extract video number from filename
                video_num = ''.join(filter(str.isdigit, video_file))
                
                # Determine if this is a fall video (has annotation) or no-fall
                fall_frames = None
                video_label = "unknown"
                
                if video_num and video_num in annotation_files:
                    # This video has an annotation = it's a FALL video
                    annotation_file = annotation_files[video_num]
                    fall_frames = [self.parse_le2i_annotation(annotation_file)]
                    if fall_frames[0]:
                        video_label = "fall"
                        print(f"      {video_file}: FALL (frames {fall_frames[0][0]}-{fall_frames[0][1]})")
                    else:
                        video_label = "fall"  # Still a fall video, just annotation parsing failed
                        fall_frames = None
                else:
                    # No annotation = NO FALL video
                    video_label = "no_fall"
                    print(f"      {video_file}: NO FALL")
                
                total_processed += self.process_video(video_path, fall_frames, video_label)
        
        if total_processed == 0:
            print("\n⚠️  No videos found!")
            print("   Checked structure:")
            print(f"     {dataset_path}/")
            print("     Looked for: Home_01, Coffee_room_01, Office, Lecture_room, etc.")
        
        print(f"\n🎉 Total frames processed: {total_processed}")
        return total_processed
    
    def process_local_videos(self, videos_dir: str, annotations_file: Optional[str] = None):
        """
        Process local video files with optional annotation file
        
        Annotation file format (CSV):
        video_file,label,start_frame,end_frame
        video1.mp4,fall,100,150
        video2.mp4,no_fall,,
        """
        print(f"\n📁 Processing local videos from {videos_dir}")
        
        # Load annotations if provided
        annotations = {}
        if annotations_file and os.path.exists(annotations_file):
            print(f"   Loading annotations from {annotations_file}")
            with open(annotations_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    video_file = row['video_file']
                    label = row.get('label', 'unknown')
                    start = int(row['start_frame']) if row.get('start_frame') else None
                    end = int(row['end_frame']) if row.get('end_frame') else None
                    
                    if start is not None and end is not None:
                        annotations[video_file] = {
                            'label': label,
                            'fall_frames': [(start, end)]
                        }
                    else:
                        annotations[video_file] = {'label': label, 'fall_frames': None}
        
        total_processed = 0
        
        for video_file in sorted(os.listdir(videos_dir)):
            if video_file.endswith(('.avi', '.mp4', '.mov', '.mkv')):
                video_path = os.path.join(videos_dir, video_file)
                
                # Get annotation if available
                ann = annotations.get(video_file, {})
                label = ann.get('label', 'unknown')
                fall_frames = ann.get('fall_frames')
                
                total_processed += self.process_video(video_path, fall_frames, label)
        
        print(f"\n🎉 Total frames processed: {total_processed}")
        return total_processed


def download_urfd_dataset(output_dir: str = "datasets/urfd") -> str:
    """
    Download UR Fall Detection Dataset
    
    Note: This requires manual download as the dataset may require registration.
    Returns the path where dataset should be extracted.
    """
    print("\n📥 UR Fall Detection Dataset Download")
    print("=" * 60)
    print("The UR Fall Detection dataset requires manual download.")
    print("\nSteps:")
    print("1. Visit: https://www.sersc.org/journals/ijsh/vol11/12/5/")
    print("   Or search: 'UR Fall Detection Dataset'")
    print("2. Download the dataset")
    print("3. Extract to:", output_dir)
    print("\nExpected structure:")
    print(f"  {output_dir}/")
    print("    falls/")
    print("      fall-01-cam0-rgb.avi")
    print("      fall-02-cam0-rgb.avi")
    print("      ...")
    print("    adls/")
    print("      adl-01-cam0-rgb.avi")
    print("      adl-02-cam0-rgb.avi")
    print("      ...")
    print("=" * 60)
    
    if os.path.exists(output_dir) and (os.path.exists(os.path.join(output_dir, 'falls')) or 
                                       os.path.exists(os.path.join(output_dir, 'adls'))):
        print(f"\n✅ Dataset found at {output_dir}")
        return output_dir
    else:
        print(f"\n⚠️  Dataset not found at {output_dir}")
        print("   Please download and extract the dataset manually.")
        return None


def create_sample_annotation_template(output_file: str = "annotations_template.csv"):
    """Create a template annotation file for manual labeling"""
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['video_file', 'label', 'start_frame', 'end_frame'])
        writer.writerow(['video1.mp4', 'fall', '100', '150'])
        writer.writerow(['video2.mp4', 'no_fall', '', ''])
        writer.writerow(['video3.mp4', 'fall', '50', '80'])
    
    print(f"✅ Created annotation template: {output_file}")
    print("\nFormat:")
    print("  - video_file: Name of video file")
    print("  - label: 'fall' or 'no_fall'")
    print("  - start_frame: Frame number where fall starts (optional)")
    print("  - end_frame: Frame number where fall ends (optional)")


def main():
    parser = argparse.ArgumentParser(description='Prepare training data from fall detection datasets')
    parser.add_argument('--dataset', choices=['urfd', 'le2i'], help='Dataset to process')
    parser.add_argument('--videos', help='Path to directory containing video files')
    parser.add_argument('--annotations', help='Path to CSV annotation file')
    parser.add_argument('--output', default='data/feature_logs.csv', help='Output CSV file')
    parser.add_argument('--download-dir', default='datasets/urfd', help='Directory for downloaded datasets')
    parser.add_argument('--create-template', action='store_true', help='Create annotation template file')
    
    args = parser.parse_args()
    
    if args.create_template:
        create_sample_annotation_template()
        return
    
    if not args.dataset and not args.videos:
        print("❌ Error: Must specify either --dataset or --videos")
        parser.print_help()
        return
    
    processor = DatasetProcessor(args.output)
    
    if args.dataset == 'urfd':
        dataset_path = download_urfd_dataset(args.download_dir)
        if dataset_path:
            processor.process_urfd_dataset(dataset_path)
        else:
            print("❌ Cannot proceed without dataset. Please download it first.")
    
    elif args.dataset == 'le2i':
        dataset_path = args.download_dir.replace('urfd', 'le2i') if 'urfd' in args.download_dir else 'datasets/le2i'
        if not os.path.exists(dataset_path):
            print(f"❌ Error: Le2i dataset not found at {dataset_path}")
            print("   Please download from Kaggle and extract to this location")
            return
        # Handle archive folder if present
        archive_path = os.path.join(dataset_path, 'archive (1)')
        if os.path.exists(archive_path):
            dataset_path = archive_path
        processor.process_le2i_dataset(dataset_path)
    
    elif args.videos:
        if not os.path.exists(args.videos):
            print(f"❌ Error: Videos directory not found: {args.videos}")
            return
        
        processor.process_local_videos(args.videos, args.annotations)
    
    print(f"\n✅ Feature extraction complete!")
    print(f"   Output: {args.output}")
    print(f"\nNext step: Train the classifier")
    print(f"   python scripts/train_classifier.py --csv {args.output} --model models/fall_classifier.pkl")


if __name__ == '__main__':
    main()

