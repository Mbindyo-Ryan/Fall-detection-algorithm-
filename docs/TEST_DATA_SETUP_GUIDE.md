# Test Data Setup Guide

## 📋 Table of Contents
1. [Overview](#overview)
2. [Getting Test Videos](#getting-test-videos)
3. [Organizing Your Test Data](#organizing-your-test-data)
4. [Creating Ground Truth Annotations](#creating-ground-truth-annotations)
5. [Setting Up for Testing](#setting-up-for-testing)
6. [Setting Up for Training](#setting-up-for-training)
7. [Quick Start Examples](#quick-start-examples)

---

## Overview

This guide explains how to set up test data for the fall detection system. Test data can be used for:
- **Testing/Demonstration**: Testing the system with video files for presentations
- **Model Training**: Preparing labeled data to train machine learning models
- **Evaluation**: Comparing system performance against ground truth

---

## Getting Test Videos

### Option 1: Use Public Datasets

#### UR Fall Detection Dataset
The UR Fall Detection Dataset is a popular benchmark dataset for fall detection.

**Download:**
```bash
# The system includes a downloader script
python scripts/prepare_training_data.py --dataset urfd --output data/feature_logs.csv
```

**Dataset Structure:**
```
urfd/
  adl_01/
    adl_01-1.avi
    adl_01-2.avi
  adl_02/
    ...
  fall_01/
    fall_01-1.avi
    fall_01-2.avi
  ...
```

#### Le2i Fall Detection Dataset
Another commonly used dataset.

**Download:**
- Visit: http://www.le2i.cn/fall-detection-dataset
- Download and extract to `datasets/le2i/`

**Dataset Structure:**
```
le2i/
  Coffee_room_01/
    Coffee_room_01_v1.avi
    Coffee_room_01_v2.avi
  ...
```

### Option 2: Record Your Own Videos

**Requirements:**
- Clear view of person
- Good lighting
- Person visible throughout video
- Duration: 2-10 seconds recommended

**Recording Tips:**
- Use stable camera (tripod recommended)
- Record at 30 FPS if possible
- Ensure person is clearly visible
- Include various scenarios:
  - Forward falls
  - Backward falls
  - Lateral falls
  - Normal activities (walking, sitting, bending)

### Option 3: Use Existing Videos

You can use any video files you have:
- Security camera footage
- Test recordings
- Sample videos from online sources

**Supported Formats:**
- `.mp4` (recommended - H.264 codec)
- `.avi`
- `.mov`
- `.mkv`
- `.flv`
- `.wmv`

---

## Organizing Your Test Data

### Recommended Folder Structure

```
Fall-detection-algorithm-/
├── fall_videos/              # For testing/demonstration
│   ├── falls/
│   │   ├── fall_001.mp4
│   │   ├── fall_002.mp4
│   │   └── ...
│   └── no_falls/
│       ├── walking_001.mp4
│       ├── sitting_001.mp4
│       └── ...
│
├── datasets/                 # For training data
│   ├── urfd/
│   ├── le2i/
│   └── custom/
│
├── annotations/              # Ground truth labels
│   ├── fall_001.csv
│   ├── fall_002.csv
│   └── batch_annotations.csv
│
└── data/                     # Processed data
    ├── feature_logs.csv
    └── feature_logs_combined.csv
```

### Create the Folders

```bash
# Navigate to project root
cd Fall-detection-algorithm-

# Create folder structure
mkdir -p fall_videos/falls
mkdir -p fall_videos/no_falls
mkdir -p datasets/urfd
mkdir -p datasets/le2i
mkdir -p datasets/custom
mkdir -p annotations
mkdir -p data
```

---

## Creating Ground Truth Annotations

Ground truth annotations tell the system which frames contain falls, enabling accuracy evaluation.

### Format 1: Simple CSV (Per Video)

Create a CSV file for each video with frame-by-frame labels:

**File: `annotations/fall_001.csv`**
```csv
frame_number,is_fall
0,0
1,0
2,0
...
45,1
46,1
47,1
...
100,0
```

**Python Script to Create Annotations:**

```python
import csv

# Example: Video has fall from frame 45 to frame 85
video_frames = 200
fall_start = 45
fall_end = 85

with open('annotations/fall_001.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['frame_number', 'is_fall'])
    
    for frame in range(video_frames):
        is_fall = 1 if fall_start <= frame <= fall_end else 0
        writer.writerow([frame, is_fall])
```

### Format 2: Batch Annotations CSV

Single file with all videos:

**File: `annotations/batch_annotations.csv`**
```csv
video_name,start_frame,end_frame,has_fall
fall_001.mp4,45,85,1
fall_002.mp4,30,60,1
walking_001.mp4,,,0
sitting_001.mp4,,,0
```

### Format 3: Simple Binary (For Test Script)

For the test script, you can use a simple binary:
- `1` = Video contains a fall
- `0` = Video does not contain a fall

```bash
# Test with ground truth
python scripts/test_fall_videos.py \
  --video fall_videos/falls/fall_001.mp4 \
  --ground-truth 1
```

### Creating Annotations Manually

**Method 1: Video Player with Frame Numbers**

1. Open video in a player that shows frame numbers (VLC, ffplay)
2. Note the frame numbers where fall starts and ends
3. Create CSV file with those frame ranges

**Method 2: Using Python Script**

```python
import cv2

def annotate_video(video_path, output_csv):
    """Interactive tool to mark fall frames"""
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    fall_frames = []
    
    print("Press 'f' when fall starts, 's' to stop marking")
    print("Press 'q' to quit and save")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        cv2.imshow('Video', frame)
        key = cv2.waitKey(30) & 0xFF
        
        if key == ord('f'):
            fall_frames.append(frame_count)
            print(f"Fall marked at frame {frame_count}")
        elif key == ord('q'):
            break
        
        frame_count += 1
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Save annotations
    with open(output_csv, 'w') as f:
        f.write('frame_number,is_fall\n')
        for i in range(frame_count):
            is_fall = 1 if i in fall_frames else 0
            f.write(f'{i},{is_fall}\n')
    
    print(f"Annotations saved to {output_csv}")

# Usage
annotate_video('fall_videos/falls/fall_001.mp4', 'annotations/fall_001.csv')
```

---

## Setting Up for Testing

### Quick Test Setup

**1. Place videos in folder:**
```bash
# Copy your test videos
cp /path/to/your/videos/*.mp4 fall_videos/falls/
```

**2. Test single video:**
```bash
python scripts/test_fall_videos.py \
  --video fall_videos/falls/fall_001.mp4 \
  --ground-truth 1 \
  --output test_results.json
```

**3. Test all videos in folder:**
```bash
python scripts/test_fall_videos.py \
  --directory fall_videos/falls/ \
  --output batch_results.json
```

### Using Dashboard for Testing

**1. Add video as camera source:**

- Login to dashboard as patient
- Go to "My Cameras" tab
- Click "Add Camera"
- Enter **absolute path** to video:
  ```
  /Users/mbindyoryankyalo/Desktop/FDA/Fall-detection-algorithm-/fall_videos/falls/fall_001.mp4
  ```
- Give it a name: "Test Fall Video 1"
- Click "Add Camera"

**2. Select and test:**

- Select video from camera dropdown
- Video will loop automatically
- Watch for fall detection
- Check "Falls" tab for logged incidents

### Batch Testing with Results

**Run comprehensive test:**
```bash
python scripts/test_fall_videos.py \
  --directory fall_videos/ \
  --output presentation_results.json
```

**View results:**
```bash
# Pretty print JSON
cat presentation_results.json | python -m json.tool

# Or use Python
python -c "
import json
with open('presentation_results.json') as f:
    data = json.load(f)
    print(f'Total Videos: {len(data)}')
    print(f'Falls Detected: {sum(1 for r in data if r[\"fall_detected\"])}')
    print(f'No Falls: {sum(1 for r in data if not r[\"fall_detected\"])}')
"
```

---

## Setting Up for Training

### Step 1: Prepare Video Dataset

**Organize videos:**
```
datasets/custom/
  ├── falls/
  │   ├── fall_001.mp4
  │   ├── fall_002.mp4
  │   └── ...
  └── no_falls/
      ├── walking_001.mp4
      ├── sitting_001.mp4
      └── ...
```

### Step 2: Create Annotations

Create annotation files for each video or a batch annotation file.

### Step 3: Extract Features

**Process videos and extract features:**

```bash
# Process single video
python scripts/prepare_training_data.py \
  --videos datasets/custom/falls/fall_001.mp4 \
  --annotations annotations/fall_001.csv \
  --output data/feature_logs.csv

# Process entire directory
python scripts/prepare_training_data.py \
  --videos datasets/custom/ \
  --annotations annotations/batch_annotations.csv \
  --output data/feature_logs.csv
```

**Process UR Fall Detection dataset:**
```bash
python scripts/prepare_training_data.py \
  --dataset urfd \
  --output data/feature_logs_urfd.csv
```

### Step 4: Combine Datasets

**Combine multiple feature logs:**
```bash
python -c "
import pandas as pd

# Load multiple CSV files
df1 = pd.read_csv('data/feature_logs_urfd.csv')
df2 = pd.read_csv('data/feature_logs_custom.csv')

# Combine
df_combined = pd.concat([df1, df2], ignore_index=True)

# Save
df_combined.to_csv('data/feature_logs_combined.csv', index=False)
print(f'Combined dataset: {len(df_combined)} rows')
"
```

### Step 5: Verify Training Data

**Check your training data:**
```bash
python -c "
import pandas as pd

df = pd.read_csv('data/feature_logs_combined.csv')
labeled = df[df['actual_fall'].notna()]

print('📊 Training Dataset Summary')
print('='*50)
print(f'Total frames: {len(df):,}')
print(f'Labeled frames: {len(labeled):,}')
if len(labeled) > 0:
    print(f'  Falls: {labeled[\"actual_fall\"].sum():,}')
    print(f'  No-falls: {(labeled[\"actual_fall\"] == 0).sum():,}')
print('='*50)
"
```

---

## Quick Start Examples

### Example 1: Quick Test with One Video

```bash
# 1. Place video in folder
cp my_test_video.mp4 fall_videos/falls/

# 2. Test it
python scripts/test_fall_videos.py \
  --video fall_videos/falls/my_test_video.mp4 \
  --ground-truth 1
```

### Example 2: Test Multiple Videos

```bash
# 1. Organize videos
mkdir -p fall_videos/falls
mkdir -p fall_videos/no_falls

# 2. Copy videos to appropriate folders
cp fall_videos/*.mp4 fall_videos/falls/  # Assuming all are falls

# 3. Test all
python scripts/test_fall_videos.py \
  --directory fall_videos/falls/ \
  --output test_results.json
```

### Example 3: Prepare Training Data from URFD

```bash
# 1. Download and process URFD dataset
python scripts/prepare_training_data.py \
  --dataset urfd \
  --output data/feature_logs_urfd.csv

# 2. Check the data
python -c "
import pandas as pd
df = pd.read_csv('data/feature_logs_urfd.csv')
print(f'Processed {len(df)} frames')
print(df['actual_fall'].value_counts())
"
```

### Example 4: Dashboard Testing Setup

```bash
# 1. Prepare videos
mkdir -p fall_videos
cp test_videos/*.mp4 fall_videos/

# 2. Get absolute paths
python -c "
import os
videos = [f for f in os.listdir('fall_videos') if f.endswith('.mp4')]
for v in videos:
    abs_path = os.path.abspath(f'fall_videos/{v}')
    print(f'{v}: {abs_path}')
"

# 3. Use these absolute paths in dashboard when adding cameras
```

---

## Troubleshooting

### Problem: Videos Won't Load

**Solutions:**
- ✅ Use absolute paths (full path from root)
- ✅ Check file format is supported
- ✅ Try converting to H.264 codec: `ffmpeg -i input.avi -c:v libx264 output.mp4`
- ✅ Verify file exists: `ls -la /path/to/video.mp4`

### Problem: No Detections

**Solutions:**
- ✅ Check video has clear view of person
- ✅ Verify person is visible throughout
- ✅ Check lighting is adequate
- ✅ Try videos with obvious falls first

### Problem: Annotations Don't Match

**Solutions:**
- ✅ Verify frame numbers match video FPS
- ✅ Check annotation CSV format is correct
- ✅ Ensure frame numbering starts at 0

### Problem: Training Data Issues

**Solutions:**
- ✅ Check `actual_fall` column has values (0 or 1)
- ✅ Verify feature extraction completed: `wc -l data/feature_logs.csv`
- ✅ Check for missing values: `python -c "import pandas as pd; df = pd.read_csv('data/feature_logs.csv'); print(df.isnull().sum())"`

---

## Best Practices

1. **Organize Early**: Set up folder structure before adding videos
2. **Use Clear Names**: Name videos descriptively (`fall_forward_001.mp4`)
3. **Keep Annotations**: Save annotation files with video names
4. **Test First**: Test videos individually before batch processing
5. **Backup Data**: Keep backups of original videos and annotations
6. **Document**: Note which videos work well for demos
7. **Version Control**: Track which dataset versions you used

---

## Next Steps

After setting up test data:

1. **For Testing**: See `VIDEO_TESTING_GUIDE.md` for testing procedures
2. **For Training**: See model training scripts in `scripts/` directory
3. **For Evaluation**: Use test results to calculate accuracy metrics

---

## Summary Checklist

- [ ] Created folder structure (`fall_videos/`, `datasets/`, `annotations/`)
- [ ] Downloaded or collected test videos
- [ ] Organized videos into falls/no_falls folders
- [ ] Created ground truth annotations (if needed)
- [ ] Tested single video successfully
- [ ] Tested batch of videos
- [ ] Prepared training data (if training models)
- [ ] Verified data quality and completeness

**You're ready to test!** 🎉

