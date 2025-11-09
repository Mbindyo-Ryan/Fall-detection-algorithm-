# Dataset Preparation Guide

This guide explains how to prepare training data for the fall detection classifier.

## Quick Start

### Option 1: Use UR Fall Detection Dataset (Recommended)

1. **Download the dataset:**
   - Visit: https://www.sersc.org/journals/ijsh/vol11/12/5/
   - Or search: "UR Fall Detection Dataset"
   - Download and extract to `datasets/urfd/`

2. **Expected folder structure:**
   ```
   datasets/urfd/
     falls/
       fall-01-cam0-rgb.avi
       fall-02-cam0-rgb.avi
       ...
     adls/
       adl-01-cam0-rgb.avi
       adl-02-cam0-rgb.avi
       ...
   ```

3. **Process the dataset:**
   ```bash
   python scripts/prepare_training_data.py --dataset urfd --output data/feature_logs.csv
   ```

### Option 2: Use Your Own Videos

1. **Create annotation file (optional):**
   ```bash
   python scripts/prepare_training_data.py --create-template
   ```
   This creates `annotations_template.csv` - edit it with your video labels.

2. **Process videos:**
   ```bash
   # Without annotations (labels entire video as fall/no_fall)
   python scripts/prepare_training_data.py --videos path/to/videos --output data/feature_logs.csv
   
   # With annotations (frame-level labels)
   python scripts/prepare_training_data.py --videos path/to/videos --annotations annotations.csv --output data/feature_logs.csv
   ```

### Option 3: Use Other Public Datasets

**Le2i Fall Detection Dataset:**
- Download from: https://sites.google.com/view/fall-detection-dataset
- Structure: Similar to URFD (falls/ and adls/ folders)
- Process with: `--videos` option pointing to the dataset folder

**UP-Fall Detection Dataset:**
- Download from: https://sites.google.com/up.edu.mx/har-up/
- Contains RGB videos with fall annotations
- Process with: `--videos` option

## Annotation File Format

CSV file with columns:
```csv
video_file,label,start_frame,end_frame
video1.mp4,fall,100,150
video2.mp4,no_fall,,
video3.mp4,fall,50,80
```

- `video_file`: Name of video file
- `label`: `fall` or `no_fall`
- `start_frame`: (Optional) Frame where fall starts
- `end_frame`: (Optional) Frame where fall ends

If `start_frame` and `end_frame` are empty, the entire video is labeled.

## Training After Data Preparation

Once you have `data/feature_logs.csv`:

```bash
# Install dependencies
pip install scikit-learn pandas joblib

# Train the classifier
python scripts/train_classifier.py --csv data/feature_logs.csv --model models/fall_classifier.pkl
```

## Dataset Recommendations

1. **UR Fall Detection** - Best for beginners, well-structured
2. **Le2i** - Good variety, multiple environments
3. **UP-Fall** - Large dataset, includes sensor data
4. **Your own videos** - Best for domain-specific scenarios

## Tips

- Process at least 1000+ frames with labeled falls for good results
- Balance your dataset: ~50% falls, ~50% no-falls
- Include diverse scenarios: different lighting, camera angles, environments
- The script automatically extracts features using MediaPipe pose detection

## Troubleshooting

**"Cannot open video"**: Check video codec compatibility (H.264 works best)

**"No pose detected"**: Ensure person is fully visible in frame

**"CSV not found"**: Run the preparation script first to generate feature_logs.csv

