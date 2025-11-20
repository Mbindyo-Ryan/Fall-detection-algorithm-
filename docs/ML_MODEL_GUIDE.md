# ML Model Integration Guide

This guide explains how to improve, train, and integrate the machine learning model for fall detection.

## 📊 Current Model Performance

### With Balanced Class Weights (Logistic Regression)
- **Fall Recall: 87.0%** ✅ (detects 87% of actual falls)
- **Fall Precision: 20.5%** (20.5% of predicted falls are real)
- **Overall Accuracy: 69.2%**

**Trade-off**: Higher recall means fewer missed falls, but more false positives. This is often acceptable for safety-critical applications.

## 🚀 Quick Start

### 1. Train a Model

```bash
# Basic training with balanced class weights (recommended)
python scripts/train_classifier.py \
  --csv data/feature_logs_combined.csv \
  --model models/fall_classifier.pkl \
  --algorithm logistic \
  --class-weight balanced

# Try XGBoost for potentially better performance
python scripts/train_classifier.py \
  --csv data/feature_logs_combined.csv \
  --model models/fall_classifier.pkl \
  --algorithm xgboost \
  --class-weight balanced

# Try Random Forest
python scripts/train_classifier.py \
  --csv data/feature_logs_combined.csv \
  --model models/fall_classifier.pkl \
  --algorithm random_forest \
  --class-weight balanced
```

### 2. Test the Model

```bash
# Test on a video file
python scripts/test_model.py \
  --video path/to/test_video.mp4 \
  --model models/fall_classifier.pkl

# Test with ground truth annotations
python scripts/test_model.py \
  --video path/to/test_video.mp4 \
  --model models/fall_classifier.pkl \
  --ground-truth annotations.csv
```

### 3. Use in Live Detection

The model is **automatically loaded** when you start the Flask app if it exists at `models/fall_classifier.pkl`.

The system uses a **hybrid approach**:
- **60% ML model** + **40% rule-based** when ML is confident
- Falls back to rule-based if ML model is unavailable

## 🎯 Improving Model Performance

### Option 1: Adjust Class Weights

If you want even higher recall (fewer missed falls):

```bash
# Give falls 5x more weight than no-falls
python scripts/train_classifier.py \
  --csv data/feature_logs_combined.csv \
  --model models/fall_classifier.pkl \
  --algorithm logistic \
  --class-weight "0:1.0,1:5.0"
```

If you want higher precision (fewer false alarms):

```bash
# Give falls 2x weight (less aggressive)
python scripts/train_classifier.py \
  --csv data/feature_logs_combined.csv \
  --model models/fall_classifier.pkl \
  --algorithm logistic \
  --class-weight "0:1.0,1:2.0"
```

### Option 2: Try Different Algorithms

**XGBoost** (often best performance):
```bash
pip install xgboost
python scripts/train_classifier.py \
  --csv data/feature_logs_combined.csv \
  --model models/fall_classifier.pkl \
  --algorithm xgboost \
  --class-weight balanced
```

**Random Forest** (good balance):
```bash
python scripts/train_classifier.py \
  --csv data/feature_logs_combined.csv \
  --model models/fall_classifier.pkl \
  --algorithm random_forest \
  --class-weight balanced
```

### Option 3: Collect More Training Data

More fall examples will improve both precision and recall:
1. Process additional fall detection datasets
2. Use the live system to collect real-world examples
3. Manually label ambiguous cases

## 🔧 Model Integration Details

### How It Works

1. **Feature Extraction**: For each frame, the system extracts:
   - `confidence`: Rule-based fall confidence score
   - `velocity`: Vertical velocity of person
   - `torso_angle`: Angle of torso relative to vertical
   - `height_ratio`: Current height vs. initial height
   - `ground_contact`: Percentage of body parts near ground
   - `ground_distance`: Estimated distance to ground
   - `velocity_3d_magnitude`: 3D velocity magnitude

2. **ML Prediction**: The model predicts fall probability (0-1)

3. **Hybrid Decision**: 
   - If ML confidence > 0.4: Use hybrid (60% ML + 40% rule-based)
   - Otherwise: Use rule-based only

### Model Location

- **Default**: `models/fall_classifier.pkl`
- **Auto-loads**: On Flask app startup
- **Fallback**: If model not found, uses rule-based only

## 📈 Performance Metrics Explained

- **Recall (Sensitivity)**: % of actual falls that are detected
  - Higher = fewer missed falls (good for safety)
  - Current: 87% ✅

- **Precision**: % of predicted falls that are real
  - Higher = fewer false alarms
  - Current: 20.5% (many false positives, but safer)

- **F1-Score**: Balance between precision and recall
  - Current: 0.332

- **Accuracy**: Overall correctness
  - Current: 69.2%

## 🧪 Testing Your Model

### Test on New Videos

```bash
python scripts/test_model.py --video test_video.mp4 --model models/fall_classifier.pkl
```

**Controls**:
- `q`: Quit
- `s`: Save current frame

### Test with Ground Truth

Create a CSV file with annotations:
```csv
start_frame,end_frame
150,180
450,480
```

Then test:
```bash
python scripts/test_model.py \
  --video test_video.mp4 \
  --model models/fall_classifier.pkl \
  --ground-truth annotations.csv
```

## 🔄 Updating the Model

1. **Retrain** with new data:
   ```bash
   python scripts/train_classifier.py --csv data/feature_logs_combined.csv --model models/fall_classifier.pkl
   ```

2. **Restart Flask app** to load new model:
   ```bash
   python app_auth.py
   ```

The model is loaded once at startup, so you need to restart to use a new model.

## 💡 Tips

1. **For Safety-Critical Applications**: Prioritize recall (fewer missed falls)
   - Use `--class-weight balanced` or higher fall weights
   - Accept more false positives

2. **For Low False Alarm Requirements**: Prioritize precision
   - Use lower fall weights: `--class-weight "0:1.0,1:2.0"`
   - May miss some falls

3. **Best of Both Worlds**: 
   - Use XGBoost with balanced weights
   - Often achieves better precision while maintaining high recall

4. **Monitor Performance**: 
   - Check the performance dashboard in the web UI
   - Review false positives/negatives
   - Retrain with more data if needed

## 🐛 Troubleshooting

**Model not loading?**
- Check file exists: `ls models/fall_classifier.pkl`
- Check Flask app logs for error messages
- Model will fall back to rule-based if unavailable

**Poor performance?**
- Try different algorithms (XGBoost often best)
- Adjust class weights
- Collect more training data
- Check feature quality in CSV logs

**ML predictions not showing?**
- Verify model file exists
- Check Flask app logs for ML loading messages
- ML only activates when confidence > 0.4

