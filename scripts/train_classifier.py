#!/usr/bin/env python3
"""
Train a lightweight classifier on logged features (feature_logs.csv).

Usage:
  python scripts/train_classifier.py --csv data/feature_logs.csv --model models/fall_classifier.pkl
  python scripts/train_classifier.py --csv data/feature_logs.csv --model models/fall_classifier.pkl --algorithm xgboost --class-weight balanced

Requires:
  pip install scikit-learn pandas joblib
  pip install xgboost  # Optional, for XGBoost algorithm
"""

import argparse
import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from joblib import dump

# XGBoost will be imported conditionally when needed
XGBOOST_AVAILABLE = False


def load_dataset(csv_path: str):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    df = pd.read_csv(csv_path)
    # Use only rows with labels (actual_fall 0/1)
    df = df[df['actual_fall'].isin([0, 1])]
    print(f"📊 Loaded {len(df)} labeled samples")
    print(f"   Falls: {df['actual_fall'].sum()}, No-falls: {(df['actual_fall'] == 0).sum()}")
    
    features = [
        'confidence', 'velocity', 'torso_angle', 'height_ratio',
        'ground_contact', 'ground_distance', 'velocity_3d_magnitude'
    ]
    # Replace NaNs with 0 for distance/3d magnitude if missing
    X = df[features].fillna(0.0)
    y = df['actual_fall'].astype(int)
    return X, y


def create_classifier(algorithm: str, class_weight: str = None):
    """Create classifier with specified algorithm and class weights"""
    
    if algorithm == 'logistic':
        if class_weight == 'balanced':
            clf = LogisticRegression(max_iter=2000, class_weight='balanced', random_state=42)
        elif class_weight:
            # Custom weights: format "0:1.0,1:5.0" means class 0 weight 1.0, class 1 weight 5.0
            weights = {}
            for pair in class_weight.split(','):
                cls, w = pair.split(':')
                weights[int(cls)] = float(w)
            clf = LogisticRegression(max_iter=2000, class_weight=weights, random_state=42)
        else:
            clf = LogisticRegression(max_iter=2000, random_state=42)
    
    elif algorithm == 'random_forest':
        if class_weight == 'balanced':
            clf = RandomForestClassifier(n_estimators=100, class_weight='balanced', 
                                       random_state=42, n_jobs=-1)
        else:
            clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    
    elif algorithm == 'xgboost':
        # Try to import XGBoost only when needed
        try:
            import xgboost as xgb
        except ImportError:
            raise ImportError("XGBoost not installed. Run: pip install xgboost")
        except Exception as e:
            raise ImportError(f"XGBoost installation issue: {e}. On macOS, try: brew install libomp")
        
        # XGBoost uses scale_pos_weight instead of class_weight
        if class_weight == 'balanced':
            # Calculate scale_pos_weight from data (will be set in fit)
            clf = xgb.XGBClassifier(n_estimators=100, random_state=42, eval_metric='logloss')
        else:
            clf = xgb.XGBClassifier(n_estimators=100, random_state=42, eval_metric='logloss')
    
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")
    
    return clf


def main():
    parser = argparse.ArgumentParser(description='Train fall detection classifier')
    parser.add_argument('--csv', default='data/feature_logs.csv', help='Path to feature logs CSV')
    parser.add_argument('--model', default='models/fall_classifier.pkl', help='Output model path')
    parser.add_argument('--algorithm', choices=['logistic', 'random_forest', 'xgboost'], 
                       default='logistic', help='Algorithm to use')
    parser.add_argument('--class-weight', default='balanced', 
                       help='Class weight: "balanced" or "0:1.0,1:5.0" format')
    parser.add_argument('--test-size', type=float, default=0.2, help='Test set size (0.0-1.0)')
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("  FALL DETECTION CLASSIFIER TRAINING")
    print("="*60)
    print(f"Algorithm: {args.algorithm}")
    print(f"Class weight: {args.class_weight}")
    print("="*60 + "\n")
    
    # Load data
    X, y = load_dataset(args.csv)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=42, stratify=y
    )
    
    print(f"📊 Train set: {len(X_train)} samples")
    print(f"📊 Test set: {len(X_test)} samples")
    
    # Create classifier
    clf = create_classifier(args.algorithm, args.class_weight)
    
    # For XGBoost with balanced, calculate scale_pos_weight
    if args.algorithm == 'xgboost' and args.class_weight == 'balanced':
        n_negative = (y_train == 0).sum()
        n_positive = (y_train == 1).sum()
        scale_pos_weight = n_negative / n_positive if n_positive > 0 else 1.0
        clf.set_params(scale_pos_weight=scale_pos_weight)
        print(f"   XGBoost scale_pos_weight: {scale_pos_weight:.2f}")
    
    # Train
    print(f"\n🔄 Training {args.algorithm} classifier...")
    clf.fit(X_train, y_train)
    
    # Evaluate
    print("\n📊 Evaluation Results:")
    print("="*60)
    y_pred = clf.predict(X_test)
    print(classification_report(y_test, y_pred, digits=3, target_names=['No Fall', 'Fall']))
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    print("\n📊 Confusion Matrix:")
    print("                Predicted")
    print("              No Fall  Fall")
    print(f"Actual No Fall  {cm[0][0]:5d}  {cm[0][1]:5d}")
    print(f"       Fall      {cm[1][0]:5d}  {cm[1][1]:5d}")
    
    # Calculate key metrics
    tn, fp, fn, tp = cm.ravel()
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall > 0) else 0
    
    print(f"\n🎯 Key Metrics:")
    print(f"   Fall Precision: {precision:.3f} (of predicted falls, {precision*100:.1f}% are real)")
    print(f"   Fall Recall:    {recall:.3f} (detects {recall*100:.1f}% of actual falls)")
    print(f"   Fall F1-Score:  {f1:.3f}")
    
    # Save model
    os.makedirs(os.path.dirname(args.model) or '.', exist_ok=True)
    dump(clf, args.model)
    print(f"\n✅ Model saved to {args.model}")
    
    # Feature importance (if available)
    if hasattr(clf, 'feature_importances_'):
        print("\n📊 Feature Importance:")
        feature_names = ['confidence', 'velocity', 'torso_angle', 'height_ratio',
                        'ground_contact', 'ground_distance', 'velocity_3d_magnitude']
        importances = clf.feature_importances_
        for name, imp in sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True):
            print(f"   {name:20s}: {imp:.4f}")
    
    print("\n" + "="*60)
    print("✅ Training complete!")
    print("="*60)


if __name__ == '__main__':
    main()


