#!/usr/bin/env python3
"""
Train a CNN-based fall detection validator.

This CNN works as a secondary validator:
1. Pose-based detector flags potential falls (fast, real-time)
2. CNN validates on video clips (accurate, reduces false positives)

Usage:
  python scripts/train_cnn_validator.py --data-dir data/video_clips --model models/cnn_validator.h5
"""

import argparse
import os
import numpy as np
import cv2
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'


def create_cnn_model(input_shape=(224, 224, 3)):
    """
    Create a lightweight CNN model for fall detection.
    Uses MobileNetV2 as base (transfer learning) for efficiency.
    """
    # Option 1: Lightweight custom CNN (fast, small)
    model = keras.Sequential([
        # Input layer
        layers.Input(shape=input_shape),
        
        # Convolutional layers
        layers.Conv2D(32, (3, 3), activation='relu', padding='same'),
        layers.MaxPooling2D((2, 2)),
        
        layers.Conv2D(64, (3, 3), activation='relu', padding='same'),
        layers.MaxPooling2D((2, 2)),
        
        layers.Conv2D(128, (3, 3), activation='relu', padding='same'),
        layers.MaxPooling2D((2, 2)),
        
        layers.Conv2D(128, (3, 3), activation='relu', padding='same'),
        layers.MaxPooling2D((2, 2)),
        
        # Flatten and dense layers
        layers.Flatten(),
        layers.Dropout(0.5),
        layers.Dense(512, activation='relu'),
        layers.Dropout(0.5),
        layers.Dense(1, activation='sigmoid')  # Binary classification: fall or no-fall
    ])
    
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.0001),
        loss='binary_crossentropy',
        metrics=['accuracy', 'precision', 'recall']
    )
    
    return model


def create_transfer_learning_model(input_shape=(224, 224, 3)):
    """
    Create a model using MobileNetV2 transfer learning (better accuracy, slightly slower).
    """
    # Load pre-trained MobileNetV2 (trained on ImageNet)
    base_model = keras.applications.MobileNetV2(
        input_shape=input_shape,
        include_top=False,
        weights='imagenet'
    )
    
    # Freeze base model initially
    base_model.trainable = False
    
    # Add custom classification head
    model = keras.Sequential([
        base_model,
        layers.GlobalAveragePooling2D(),
        layers.Dropout(0.5),
        layers.Dense(128, activation='relu'),
        layers.Dropout(0.5),
        layers.Dense(1, activation='sigmoid')
    ])
    
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=0.0001),
        loss='binary_crossentropy',
        metrics=['accuracy', 'precision', 'recall']
    )
    
    return model


def load_video_clips(data_dir, clip_length=16, target_size=(224, 224)):
    """
    Load video clips from directory structure:
    data_dir/
      fall/
        video1.mp4
        video2.mp4
      no_fall/
        video1.mp4
        video2.mp4
    """
    X = []
    y = []
    
    fall_dir = os.path.join(data_dir, 'fall')
    no_fall_dir = os.path.join(data_dir, 'no_fall')
    
    print(f"📁 Loading video clips from {data_dir}")
    
    # Load fall videos
    if os.path.exists(fall_dir):
        for video_file in os.listdir(fall_dir):
            if video_file.endswith(('.mp4', '.avi', '.mov', '.mkv')):
                video_path = os.path.join(fall_dir, video_file)
                frames = extract_frames(video_path, clip_length, target_size)
                if frames is not None:
                    X.append(frames)
                    y.append(1)  # Fall = 1
                    print(f"  ✅ Loaded fall clip: {video_file}")
    
    # Load no-fall videos
    if os.path.exists(no_fall_dir):
        for video_file in os.listdir(no_fall_dir):
            if video_file.endswith(('.mp4', '.avi', '.mov', '.mkv')):
                video_path = os.path.join(no_fall_dir, video_file)
                frames = extract_frames(video_path, clip_length, target_size)
                if frames is not None:
                    X.append(frames)
                    y.append(0)  # No-fall = 0
                    print(f"  ✅ Loaded no-fall clip: {video_file}")
    
    if len(X) == 0:
        raise ValueError(f"No video clips found in {data_dir}")
    
    X = np.array(X)
    y = np.array(y)
    
    print(f"\n📊 Dataset: {len(X)} clips")
    print(f"   Falls: {y.sum()}, No-falls: {(y == 0).sum()}")
    
    return X, y


def extract_frames(video_path, num_frames=16, target_size=(224, 224)):
    """
    Extract frames from video and resize to target size.
    Returns average frame (single image) for simplicity.
    For temporal models, you'd return a sequence of frames.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    
    frames = []
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Sample frames evenly throughout video
    frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
    
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            # Resize and normalize
            frame = cv2.resize(frame, target_size)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = frame.astype('float32') / 255.0
            frames.append(frame)
    
    cap.release()
    
    if len(frames) == 0:
        return None
    
    # For now, return average frame (single image)
    # For temporal CNN, return sequence of frames
    avg_frame = np.mean(frames, axis=0)
    return avg_frame


def main():
    parser = argparse.ArgumentParser(description='Train CNN fall detection validator')
    parser.add_argument('--data-dir', default='data/video_clips',
                       help='Directory with fall/ and no_fall/ subdirectories')
    parser.add_argument('--model', default='models/cnn_validator.h5',
                       help='Output model path')
    parser.add_argument('--architecture', choices=['custom', 'mobilenet'],
                       default='custom', help='CNN architecture')
    parser.add_argument('--epochs', type=int, default=50, help='Training epochs')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size')
    parser.add_argument('--test-size', type=float, default=0.2, help='Test set size')
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("  CNN FALL DETECTION VALIDATOR TRAINING")
    print("="*60)
    print(f"Architecture: {args.architecture}")
    print(f"Epochs: {args.epochs}")
    print("="*60 + "\n")
    
    # Load data
    try:
        X, y = load_video_clips(args.data_dir, clip_length=16, target_size=(224, 224))
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("\n📝 Expected directory structure:")
        print("  data/video_clips/")
        print("    fall/")
        print("      video1.mp4")
        print("      video2.mp4")
        print("    no_fall/")
        print("      video1.mp4")
        print("      video2.mp4")
        return
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=42, stratify=y
    )
    
    print(f"📊 Train set: {len(X_train)} clips")
    print(f"📊 Test set: {len(X_test)} clips")
    
    # Create model
    if args.architecture == 'mobilenet':
        print("\n🔄 Creating MobileNetV2-based model (transfer learning)...")
        model = create_transfer_learning_model(input_shape=(224, 224, 3))
    else:
        print("\n🔄 Creating custom lightweight CNN...")
        model = create_cnn_model(input_shape=(224, 224, 3))
    
    model.summary()
    
    # Data augmentation
    datagen = ImageDataGenerator(
        rotation_range=10,
        width_shift_range=0.1,
        height_shift_range=0.1,
        horizontal_flip=True,
        zoom_range=0.1
    )
    
    # Train
    print(f"\n🔄 Training for {args.epochs} epochs...")
    history = model.fit(
        datagen.flow(X_train, y_train, batch_size=args.batch_size),
        epochs=args.epochs,
        validation_data=(X_test, y_test),
        verbose=1
    )
    
    # Evaluate
    print("\n📊 Evaluation Results:")
    print("="*60)
    y_pred = (model.predict(X_test) > 0.5).astype(int).flatten()
    print(classification_report(y_test, y_pred, target_names=['No Fall', 'Fall']))
    
    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    print("\n📊 Confusion Matrix:")
    print("                Predicted")
    print("              No Fall  Fall")
    print(f"Actual No Fall  {cm[0][0]:5d}  {cm[0][1]:5d}")
    print(f"       Fall      {cm[1][0]:5d}  {cm[1][1]:5d}")
    
    # Save model
    os.makedirs(os.path.dirname(args.model) or '.', exist_ok=True)
    model.save(args.model)
    print(f"\n✅ Model saved to {args.model}")
    
    print("\n" + "="*60)
    print("✅ Training complete!")
    print("="*60)
    print("\n💡 Next steps:")
    print("  1. Integrate CNN validator into detection_skeleton.py")
    print("  2. Use it to validate pose-based detections")
    print("  3. Reduce false positives while maintaining real-time performance")


if __name__ == '__main__':
    main()

