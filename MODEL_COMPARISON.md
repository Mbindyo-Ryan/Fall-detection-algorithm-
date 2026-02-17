# Model Performance Comparison

## 📊 Results Summary

### 1. Logistic Regression (Balanced Class Weights) ✅ CURRENT
- **Fall Recall: 87.0%** (detects 87% of actual falls)
- **Fall Precision: 20.5%** (20.5% of predicted falls are real)
- **Overall Accuracy: 69.2%**
- **F1-Score: 0.332**

**Best for**: Maximum safety (fewest missed falls)
**Trade-off**: Many false positives

### 2. Random Forest (Balanced Class Weights) ⭐ RECOMMENDED
- **Fall Recall: 76.4%** (detects 76% of actual falls)
- **Fall Precision: 47.8%** (48% of predicted falls are real)
- **Overall Accuracy: 90.6%**
- **F1-Score: 0.588**

**Best for**: Balanced performance (good recall + better precision)
**Trade-off**: Slightly lower recall, but much better precision

### 3. Logistic Regression (No Class Weights) - Original
- **Fall Recall: 24.0%** (detects only 24% of actual falls)
- **Fall Precision: 65.6%** (66% of predicted falls are real)
- **Overall Accuracy: 92.2%**
- **F1-Score: 0.351**

**Best for**: Low false positives
**Trade-off**: Misses most falls (not recommended for safety)

## 🎯 Recommendation

**Use Random Forest** (`models/fall_classifier_rf.pkl`) for the best balance:
- Still detects 76% of falls (good for safety)
- Only 52% false positives (vs 80% with logistic)
- Much higher overall accuracy (90.6%)

## 📈 Feature Importance (Random Forest)

The model shows which features matter most:
1. **height_ratio** (27.8%) - How much person has shrunk
2. **confidence** (21.4%) - Rule-based confidence score
3. **torso_angle** (19.6%) - Angle of torso
4. **ground_distance** (16.5%) - Distance to ground
5. **velocity_3d_magnitude** (6.1%) - 3D velocity
6. **ground_contact** (4.3%) - Body parts near ground
7. **velocity** (4.3%) - Vertical velocity

## 🔄 Switching Models

To use Random Forest instead of Logistic:

```bash
# Copy Random Forest model to default location
cp models/fall_classifier_rf.pkl models/fall_classifier.pkl

# Or update detection_skeleton.py ML_MODEL_PATH to:
# ML_MODEL_PATH = "models/fall_classifier_rf.pkl"
```

Then restart your Flask app.

