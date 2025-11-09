import cv2
import mediapipe as mp
import math
import sqlite3
from datetime import datetime
import time
import numpy as np
import json
from collections import deque
import threading
import queue
import os
import csv

# =========================================================
# CONFIGURATION
# =========================================================
FALL_CONFIRM_FRAMES = 8
FALL_THRESHOLD_VELOCITY = 0.02
TORSO_FLATNESS_THRESHOLD = 0.1
POSE_CONFIDENCE = 0.6
FALL_LOG_COOLDOWN = 10
MOTION_THRESHOLD = 5000

# =========================================================
# GLOBAL STATE & INITIALIZATION
# =========================================================
mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils

# Create pose detector with explicit parameters
pose_detector = mp_pose.Pose(
    static_image_mode=False,  # Video stream mode
    model_complexity=1,  # 0=Lite, 1=Full, 2=Heavy
    smooth_landmarks=True,
    enable_segmentation=False,
    smooth_segmentation=False,
    min_detection_confidence=POSE_CONFIDENCE,
    min_tracking_confidence=POSE_CONFIDENCE
)

DB_CONN = None
DB_PATH = "system_config.db"
DATA_DIR = "data"
FEATURE_LOG_PATH = os.path.join(DATA_DIR, "feature_logs.csv")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# =========================================================
# FEATURE LOGGER (for ML training dataset)
# =========================================================
class FeatureLogger:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self._ensure_header()

    def _ensure_header(self):
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'user_id', 'fall_detected', 'actual_fall',
                    'confidence', 'velocity', 'torso_angle', 'height_ratio',
                    'ground_contact', 'ground_distance', 'velocity_3d_magnitude',
                    'pose_detected'
                ])

    def log(self, user_id: str, fall_detected: bool, actual_fall, pose_detected: bool, details: dict):
        try:
            with open(self.csv_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.utcnow().isoformat(),
                    user_id,
                    int(bool(fall_detected)),
                    '' if actual_fall is None else int(bool(actual_fall)),
                    round(details.get('fall_confidence', 0.0), 6),
                    round(details.get('velocity', 0.0), 6),
                    round(details.get('torso_angle', 0.0), 6),
                    round(details.get('height_ratio', 0.0), 6),
                    round(details.get('ground_contact', 0.0), 6),
                    '' if details.get('ground_distance') is None else round(details.get('ground_distance', 0.0), 6),
                    '' if details.get('velocity_3d_magnitude') is None else round(details.get('velocity_3d_magnitude', 0.0), 6),
                    int(bool(pose_detected))
                ])
        except Exception as e:
            print(f"⚠️ Feature logging error: {e}")

# =========================================================
# MEDIAPIPE FRAME PROCESSOR (Fixes timestamp issues)
# =========================================================
class MediaPipeFrameProcessor:
    """Handles MediaPipe processing with proper frame management"""
    
    def __init__(self):
        self.frame_count = 0
        self.process_every_n_frames = 2  # Process every 2nd frame for stability
        self.last_valid_landmarks = None
        self.consecutive_failures = 0
        self.max_consecutive_failures = 10
        
    def process_frame(self, frame):
        """
        Process frame with MediaPipe, handling timestamp issues gracefully
        Returns: (success, landmarks, processed_frame)
        """
        self.frame_count += 1
        
        # Frame skipping to reduce load and avoid timestamp conflicts
        if self.frame_count % self.process_every_n_frames != 0:
            if self.last_valid_landmarks:
                return True, self.last_valid_landmarks, frame
            return False, None, frame
        
        try:
            # Convert to RGB (MediaPipe requirement)
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # CRITICAL: Make frame non-writeable to improve performance
            # This prevents MediaPipe from trying to modify the frame
            image_rgb.flags.writeable = False
            
            # Process with MediaPipe
            results = pose_detector.process(image_rgb)
            
            # Make frame writeable again for drawing
            image_rgb.flags.writeable = True
            processed_frame = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
            
            if results.pose_landmarks:
                # Success - reset failure counter
                self.consecutive_failures = 0
                self.last_valid_landmarks = results.pose_landmarks
                
                # Draw landmarks on frame
                mp_draw.draw_landmarks(
                    processed_frame,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    mp_draw.DrawingSpec(color=(0, 0, 255), thickness=2)
                )
                
                return True, results.pose_landmarks, processed_frame
            else:
                # No pose detected in frame
                self.consecutive_failures += 1
                return False, None, processed_frame
                
        except Exception as e:
            print(f"⚠️ MediaPipe processing error: {e}")
            self.consecutive_failures += 1
            
            # If too many consecutive failures, try to reset
            if self.consecutive_failures >= self.max_consecutive_failures:
                print("🔄 Attempting to reset MediaPipe detector...")
                self.reset_detector()
            
            return False, None, frame
    
    def reset_detector(self):
        """Reset MediaPipe detector on persistent failures"""
        global pose_detector
        try:
            pose_detector.close()
        except:
            pass
        
        pose_detector = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            min_detection_confidence=POSE_CONFIDENCE,
            min_tracking_confidence=POSE_CONFIDENCE
        )
        self.consecutive_failures = 0
        print("✅ MediaPipe detector reset successfully")

# =========================================================
# ADVANCED PERFORMANCE MONITORING CLASS
# =========================================================
class AdvancedPerformanceMonitor:
    def __init__(self):
        self.reset_metrics()
        self.detection_history = []
        self.start_time = time.time()
        
    def reset_metrics(self):
        self.metrics = {
            'true_positives': 0,
            'false_positives': 0,
            'true_negatives': 0,
            'false_negatives': 0,
            'total_frames': 0,
            'frames_with_detection': 0,
            'frames_without_pose': 0,
            'detection_times': [],
            'confidence_scores': [],
            'fall_indicators_triggered': {
                'velocity': 0, 'torso_angle': 0, 'height_ratio': 0, 'ground_contact': 0
            }
        }
    
    def update_detection(self, fall_detected, actual_fall=None, confidence=0.0, 
                        indicators=None, detection_time=0, pose_detected=True):
        """Update metrics for each frame processed"""
        self.metrics['total_frames'] += 1
        self.metrics['detection_times'].append(detection_time)
        
        if pose_detected:
            self.metrics['frames_with_detection'] += 1
            self.metrics['confidence_scores'].append(confidence)
            
            # Track which indicators triggered
            if indicators:
                for indicator, triggered in indicators.items():
                    if triggered:
                        self.metrics['fall_indicators_triggered'][indicator] += 1
        else:
            self.metrics['frames_without_pose'] += 1
        
        # Update accuracy metrics if ground truth is available
        if actual_fall is not None:
            if actual_fall and fall_detected:
                self.metrics['true_positives'] += 1
            elif not actual_fall and not fall_detected:
                self.metrics['true_negatives'] += 1
            elif not actual_fall and fall_detected:
                self.metrics['false_positives'] += 1
            elif actual_fall and not fall_detected:
                self.metrics['false_negatives'] += 1
        
        # Store detailed history (keep last 1000)
        self.detection_history.append({
            'timestamp': datetime.now().isoformat(),
            'fall_detected': fall_detected,
            'confidence': confidence,
            'detection_time': detection_time,
            'actual_fall': actual_fall,
            'pose_detected': pose_detected
        })
        if len(self.detection_history) > 1000:
            self.detection_history.pop(0)
    
    def calculate_comprehensive_metrics(self):
        """Calculate all performance metrics"""
        tp = self.metrics['true_positives']
        tn = self.metrics['true_negatives']
        fp = self.metrics['false_positives']
        fn = self.metrics['false_negatives']
        
        total_detections = tp + tn + fp + fn
        
        # Basic metrics
        accuracy = (tp + tn) / total_detections if total_detections > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        # Additional metrics
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        false_positive_rate = fp / (fp + tn) if (fp + tn) > 0 else 0
        false_negative_rate = fn / (fn + tp) if (fn + tp) > 0 else 0
        
        # System performance
        avg_detection_time = np.mean(self.metrics['detection_times']) if self.metrics['detection_times'] else 0
        fps = self.metrics['total_frames'] / (time.time() - self.start_time) if (time.time() - self.start_time) > 0 else 0
        avg_confidence = np.mean(self.metrics['confidence_scores']) if self.metrics['confidence_scores'] else 0
        
        # Pose detection rate
        pose_detection_rate = self.metrics['frames_with_detection'] / self.metrics['total_frames'] if self.metrics['total_frames'] > 0 else 0
        
        # Indicator effectiveness
        total_indicators = sum(self.metrics['fall_indicators_triggered'].values())
        indicator_effectiveness = {
            indicator: count / total_indicators if total_indicators > 0 else 0
            for indicator, count in self.metrics['fall_indicators_triggered'].items()
        }
        
        return {
            # Core Classification Metrics
            'accuracy': round(accuracy, 4),
            'precision': round(precision, 4),
            'recall': round(recall, 4),
            'f1_score': round(f1_score, 4),
            'specificity': round(specificity, 4),
            'false_positive_rate': round(false_positive_rate, 4),
            'false_negative_rate': round(false_negative_rate, 4),
            
            # System Performance
            'total_frames_processed': self.metrics['total_frames'],
            'frames_with_pose': self.metrics['frames_with_detection'],
            'frames_without_pose': self.metrics['frames_without_pose'],
            'pose_detection_rate': round(pose_detection_rate, 4),
            'average_detection_time_ms': round(avg_detection_time * 1000, 2),
            'frames_per_second': round(fps, 2),
            'average_confidence': round(avg_confidence, 4),
            
            # Detection Details
            'true_positives': tp,
            'false_positives': fp,
            'true_negatives': tn,
            'false_negatives': fn,
            'total_detections': total_detections,
            
            # Indicator Analysis
            'indicator_effectiveness': indicator_effectiveness,
            'fall_indicators_triggered': self.metrics['fall_indicators_triggered'],
            
            # Timestamps
            'session_duration_seconds': round(time.time() - self.start_time, 2),
            'report_generated_at': datetime.now().isoformat()
        }
    
    def generate_detailed_report(self):
        """Generate comprehensive performance report"""
        metrics = self.calculate_comprehensive_metrics()
        
        confusion_matrix = {
            'actual_fall_detected_fall': metrics['true_positives'],
            'actual_fall_detected_normal': metrics['false_negatives'],
            'actual_normal_detected_fall': metrics['false_positives'],
            'actual_normal_detected_normal': metrics['true_negatives']
        };
        
        report = {
            'summary_metrics': metrics,
            'confusion_matrix': confusion_matrix,
            'detection_history_sample': self.detection_history[-100:],
            'performance_grade': self._calculate_performance_grade(metrics)
        }
        
        return report
    
    def _calculate_performance_grade(self, metrics):
        """Calculate overall performance grade"""
        # If no ground truth available, grade based on system performance
        if metrics['total_detections'] == 0:
            pose_rate = metrics['pose_detection_rate']
            if pose_rate >= 0.8:
                return "A (System Running Well - No Test Data)"
            elif pose_rate >= 0.6:
                return "B (System Running - No Test Data)"
            else:
                return "C (Low Pose Detection - Check Camera)"
        
        score = (metrics['f1_score'] + metrics['accuracy'] + metrics['recall']) / 3
        
        if score >= 0.9:
            return "A+ (Excellent)"
        elif score >= 0.8:
            return "A (Very Good)"
        elif score >= 0.7:
            return "B (Good)"
        elif score >= 0.6:
            return "C (Fair)"
        else:
            return "D (Needs Improvement)"
    
    def save_report_to_file(self, filename=None):
        """Save detailed report to JSON file"""
        if filename is None:
            filename = f"fall_detection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = self.generate_detailed_report()
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"✅ Performance report saved to: {filename}")
        return filename
    
    def print_real_time_metrics(self):
        """Print current metrics to console"""
        metrics = self.calculate_comprehensive_metrics()
        
        print("\n" + "="*60)
        print("📊 REAL-TIME FALL DETECTION METRICS")
        print("="*60)
        print(f"🎯 Pose Detection: {metrics['pose_detection_rate']:.1%}")
        print(f"📈 Frames/sec:     {metrics['frames_per_second']:.1f}")
        print(f"⏱️  Avg Time:      {metrics['average_detection_time_ms']:.1f}ms")
        print("-"*60)
        print(f"📊 Total Frames:   {metrics['total_frames_processed']}")
        print(f"✅ With Pose:      {metrics['frames_with_pose']}")
        print(f"❌ Without Pose:   {metrics['frames_without_pose']}")
        print("="*60)

# =========================================================
# OPTICAL FLOW ANALYZER
# =========================================================
class OpticalFlowAnalyzer:
    def __init__(self):
        self.prev_gray = None
        self.flow_threshold = MOTION_THRESHOLD
    
    def calculate_optical_flow(self, frame):
        """Calculate optical flow magnitude for motion detection"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if self.prev_gray is not None:
                flow = cv2.calcOpticalFlowFarneback(
                    self.prev_gray, gray, None, 
                    pyr_scale=0.5, levels=3, winsize=15, 
                    iterations=3, poly_n=5, poly_sigma=1.2, flags=0
                )
                magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
                total_motion = np.sum(magnitude)
                self.prev_gray = gray
                return total_motion
            else:
                self.prev_gray = gray
                return 0
        except Exception as e:
            print(f"⚠️ Optical flow error: {e}")
            return 0

# =========================================================
# GROUND PLANE ESTIMATOR
# =========================================================
class GroundPlaneEstimator:
    """Estimate ground plane using ankle and foot positions"""
    
    def __init__(self):
        self.ground_points_history = deque(maxlen=30)  # Store last 30 frames
        self.estimated_ground_y = None
        self.ground_plane_stable = False
        
    def update_ground_estimation(self, landmarks, frame_height):
        """Update ground plane estimation from current pose"""
        if not landmarks:
            return
            
        lm = landmarks.landmark
        ankle_points = []
        
        # Use both ankles as ground reference points
        left_ankle = lm[mp_pose.PoseLandmark.LEFT_ANKLE.value]
        right_ankle = lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value]
        
        # Only use visible points
        if left_ankle.visibility > 0.5:
            ankle_points.append(left_ankle.y * frame_height)
        if right_ankle.visibility > 0.5:
            ankle_points.append(right_ankle.y * frame_height)
            
        if ankle_points:
            # Use average of ankle positions as ground estimate
            avg_ground_y = sum(ankle_points) / len(ankle_points)
            self.ground_points_history.append(avg_ground_y)
            
            # Calculate stable ground plane (median of recent points)
            if len(self.ground_points_history) >= 10:
                sorted_points = sorted(self.ground_points_history)
                median_idx = len(sorted_points) // 2
                self.estimated_ground_y = sorted_points[median_idx]
                self.ground_plane_stable = True
                
        return self.estimated_ground_y
    
    def get_ground_distance(self, y_position, frame_height):
        """Calculate distance from a point to estimated ground"""
        if self.estimated_ground_y is None:
            return None
        y_pixel = y_position * frame_height
        return abs(y_pixel - self.estimated_ground_y)

# =========================================================
# TENSOR POINTS CALCULATOR (3D Position Estimation)
# =========================================================
class TensorPointsCalculator:
    """Calculate 3D tensor points from 2D MediaPipe landmarks"""
    
    def __init__(self):
        self.pose_history_3d = deque(maxlen=10)
        
    def calculate_tensor_points(self, landmarks, frame_shape):
        """
        Convert 2D landmarks to 3D tensor points with depth estimation
        Returns: Dictionary of key points with 3D coordinates
        """
        if not landmarks:
            return None
            
        height, width = frame_shape[:2]
        lm = landmarks.landmark
        
        tensor_points = {}
        
        # Key body points for fall detection
        key_points = {
            'head': mp_pose.PoseLandmark.NOSE.value,
            'neck': mp_pose.PoseLandmark.SHOULDER_CENTER.value if hasattr(mp_pose.PoseLandmark, 'SHOULDER_CENTER') else None,
            'left_shoulder': mp_pose.PoseLandmark.LEFT_SHOULDER.value,
            'right_shoulder': mp_pose.PoseLandmark.RIGHT_SHOULDER.value,
            'left_hip': mp_pose.PoseLandmark.LEFT_HIP.value,
            'right_hip': mp_pose.PoseLandmark.RIGHT_HIP.value,
            'left_knee': mp_pose.PoseLandmark.LEFT_KNEE.value,
            'right_knee': mp_pose.PoseLandmark.RIGHT_KNEE.value,
            'left_ankle': mp_pose.PoseLandmark.LEFT_ANKLE.value,
            'right_ankle': mp_pose.PoseLandmark.RIGHT_ANKLE.value,
        }
        
        # Calculate center of mass (COM) as weighted average
        com_x, com_y, com_z = 0.0, 0.0, 0.0
        total_weight = 0.0
        
        for point_name, point_idx in key_points.items():
            if point_idx is None:
                continue
                
            point = lm[point_idx]
            if point.visibility > 0.5:
                # Convert normalized coordinates to pixel coordinates
                x = point.x * width
                y = point.y * height
                
                # Estimate depth (Z) using visibility and body part size assumptions
                # Head is typically closer (smaller Z), feet are farther (larger Z)
                if 'head' in point_name or 'nose' in point_name:
                    z_estimate = -0.5  # Closer
                elif 'shoulder' in point_name or 'hip' in point_name:
                    z_estimate = 0.0  # Mid-depth
                elif 'ankle' in point_name or 'knee' in point_name:
                    z_estimate = 0.5  # Farther
                else:
                    z_estimate = 0.0
                
                # Weight by visibility
                weight = point.visibility
                com_x += x * weight
                com_y += y * weight
                com_z += z_estimate * weight
                total_weight += weight
                
                tensor_points[point_name] = {
                    'x': x,
                    'y': y,
                    'z': z_estimate,
                    'visibility': point.visibility,
                    'normalized': (point.x, point.y, point.z if hasattr(point, 'z') else 0.0)
                }
        
        # Calculate center of mass
        if total_weight > 0:
            tensor_points['center_of_mass'] = {
                'x': com_x / total_weight,
                'y': com_y / total_weight,
                'z': com_z / total_weight
            }
        
        # Calculate body orientation tensor
        if 'left_shoulder' in tensor_points and 'right_shoulder' in tensor_points:
            left_shoulder = tensor_points['left_shoulder']
            right_shoulder = tensor_points['right_shoulder']
            
            # Vector from left to right shoulder
            shoulder_vector = (
                right_shoulder['x'] - left_shoulder['x'],
                right_shoulder['y'] - left_shoulder['y'],
                right_shoulder['z'] - left_shoulder['z']
            )
            
            tensor_points['shoulder_orientation'] = shoulder_vector
        
        # Calculate body height (from head to average ankle)
        if 'head' in tensor_points and ('left_ankle' in tensor_points or 'right_ankle' in tensor_points):
            head = tensor_points['head']
            ankle_y = []
            if 'left_ankle' in tensor_points:
                ankle_y.append(tensor_points['left_ankle']['y'])
            if 'right_ankle' in tensor_points:
                ankle_y.append(tensor_points['right_ankle']['y'])
            
            if ankle_y:
                avg_ankle_y = sum(ankle_y) / len(ankle_y)
                body_height = abs(head['y'] - avg_ankle_y)
                tensor_points['body_height'] = body_height
        
        return tensor_points
    
    def calculate_fall_velocity_3d(self, current_tensors, prev_tensors):
        """Calculate 3D velocity vector from tensor points"""
        if not current_tensors or not prev_tensors:
            return None
            
        if 'center_of_mass' not in current_tensors or 'center_of_mass' not in prev_tensors:
            return None
            
        current_com = current_tensors['center_of_mass']
        prev_com = prev_tensors['center_of_mass']
        
        # Calculate velocity vector
        velocity_3d = {
            'x': current_com['x'] - prev_com['x'],
            'y': current_com['y'] - prev_com['y'],
            'z': current_com['z'] - prev_com['z']
        }
        
        # Calculate magnitude
        velocity_magnitude = math.sqrt(
            velocity_3d['x']**2 + 
            velocity_3d['y']**2 + 
            velocity_3d['z']**2
        )
        
        velocity_3d['magnitude'] = velocity_magnitude
        
        return velocity_3d

# =========================================================
# FALL VIDEO RECORDER
# =========================================================
class FallVideoRecorder:
    """Records video clips when falls are detected"""
    
    def __init__(self):
        self.recording = False
        self.video_writer = None
        self.frames_buffer = deque(maxlen=90)  # Store last 3 seconds at 30fps
        self.output_dir = "fall_videos"
        self.current_fall_id = None
        os.makedirs(self.output_dir, exist_ok=True)
    
    def add_frame(self, frame):
        """Add frame to buffer (always recording to buffer)"""
        self.frames_buffer.append(frame.copy())
    
    def start_recording(self, fall_id, user_id):
        """Start recording video for a fall event"""
        if self.recording:
            return  # Already recording
        
        self.recording = True
        self.current_fall_id = fall_id
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"fall_{user_id}_{timestamp}_{fall_id}.mp4"
        video_path = os.path.join(self.output_dir, filename)
        
        # Get frame dimensions from buffer
        if len(self.frames_buffer) > 0:
            frame = self.frames_buffer[0]
            height, width = frame.shape[:2]
            
            # Create video writer (MP4 with H.264 codec)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = 30.0
            self.video_writer = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
            
            # Write all buffered frames first
            for buffered_frame in self.frames_buffer:
                self.video_writer.write(buffered_frame)
            
            print(f"🎥 Started recording fall video: {video_path}")
            return video_path
        
        return None
    
    def record_frame(self, frame):
        """Record a single frame"""
        if self.recording and self.video_writer:
            self.video_writer.write(frame)
    
    def stop_recording(self, duration_seconds=5):
        """Stop recording after specified duration"""
        if not self.recording:
            return None
        
        # Continue recording for additional duration
        return self.video_writer
    
    def finish_recording(self):
        """Finish and save video"""
        if self.recording and self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            self.recording = False
            print(f"✅ Finished recording fall video for fall ID: {self.current_fall_id}")
            return True
        return False

# =========================================================
# ENHANCED FALL DETECTOR
# =========================================================
class FallDetector:
    def __init__(self):
        self.prev_shoulder_y = None
        self.fall_counter = 0
        self.fall_logged = False
        self.last_fall_time = 0.0
        self.current_user_id = "unknown_user"
        self.camera_source = "0"
        self.is_running = True
        self.normal_height = None
        
        # Enhanced detection parameters
        self.fall_indicators = {
            'velocity_threshold': FALL_THRESHOLD_VELOCITY,
            'torso_angle_threshold': 25,
            'height_ratio_threshold': 0.6,
            'ground_contact_threshold': 0.8,
        }
        
        self.performance_monitor = AdvancedPerformanceMonitor()
        self.optical_flow_analyzer = OpticalFlowAnalyzer()
        self.mediapipe_processor = MediaPipeFrameProcessor()
        self.pose_history = deque(maxlen=10)
        
        # NEW: Tensor points and ground mapping
        self.tensor_calculator = TensorPointsCalculator()
        self.ground_estimator = GroundPlaneEstimator()
        self.prev_tensor_points = None
        
        # NEW: Video recording
        self.video_recorder = FallVideoRecorder()
        self.recording_fall_id = None
        self.recording_start_time = None
        self.recording_duration = 5  # Record for 5 seconds after fall detection

        # Feature logger
        self.feature_logger = FeatureLogger(FEATURE_LOG_PATH)

    def set_user_id(self, user_id):
        self.current_user_id = user_id

    def set_camera_source(self, source):
        self.camera_source = source
        print(f"🎥 Detector camera source set to: {source}")

    def calculate_fall_severity(self, details):
        """Calculate fall severity based on detection metrics"""
        confidence = details.get('fall_confidence', 0)
        velocity = details.get('velocity', 0)
        ground_distance = details.get('ground_distance')
        velocity_3d = details.get('velocity_3d_magnitude')
        
        severity_score = 0
        
        # Confidence factor
        severity_score += confidence * 0.4
        
        # Velocity factor
        if velocity > 0.05:
            severity_score += 0.3
        elif velocity > 0.03:
            severity_score += 0.2
        
        # Ground distance factor (closer to ground = more severe)
        if ground_distance is not None:
            if ground_distance < 30:
                severity_score += 0.2
            elif ground_distance < 80:
                severity_score += 0.1
        
        # 3D velocity factor
        if velocity_3d and velocity_3d > 150:
            severity_score += 0.1
        
        # Classify severity
        if severity_score >= 0.7:
            return 'severe'
        elif severity_score >= 0.4:
            return 'moderate'
        else:
            return 'mild'
    
    def log_fall_to_db(self, status, details, video_path=None, location=None):
        global DB_CONN
        if not DB_CONN:
            print("❌ Error logging fall: Database connection not established.")
            return

        current_time = time.time()
        if current_time < self.last_fall_time + FALL_LOG_COOLDOWN:
            return

        self.last_fall_time = current_time

        try:
            ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            severity = self.calculate_fall_severity(details)
            
            c = DB_CONN.cursor()
            c.execute(
                """INSERT INTO falls (user_id, timestamp, status, details, alert_sent, 
                   video_path, severity, location) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (self.current_user_id, ts, status, details, 0, video_path, severity, location)
            )
            DB_CONN.commit()
            fall_id = c.lastrowid
            
            print(f"✅ Logged fall at {ts} for user {self.current_user_id}: {status} | Severity: {severity} | {details}")
            self.fall_logged = True
            
            # Send alerts to caregivers and doctors
            try:
                from alert_service import send_fall_alerts
                # Get patient name
                c.execute("SELECT name FROM users WHERE id = ?", (self.current_user_id,))
                user_row = c.fetchone()
                patient_name = user_row[0] if user_row else "Patient"
                
                alert_result = send_fall_alerts(
                    patient_id=self.current_user_id,
                    patient_name=patient_name,
                    severity=severity,
                    location=location,
                    fall_id=fall_id
                )
                
                # Update alert_sent flag
                if alert_result.get('sent'):
                    c.execute("UPDATE falls SET alert_sent = 1 WHERE id = ?", (fall_id,))
                    DB_CONN.commit()
                    print(f"📱 Alerts sent: {alert_result.get('sms_sent', 0)} SMS, {alert_result.get('calls_made', 0)} calls")
                else:
                    print(f"⚠️  No alerts sent: {alert_result.get('reason', 'unknown')}")
            except ImportError:
                print("⚠️  Alert service not available. Install alert_service.py")
            except Exception as e:
                print(f"⚠️  Error sending alerts: {e}")
            
            return fall_id  # Return fall ID for video association
        except sqlite3.Error as e:
            print(f"❌ Error logging fall to DB: {e}")
            return None

    def calculate_torso_angle(self, landmarks):
        """Calculate torso angle relative to vertical"""
        lm = landmarks.landmark
        left_shoulder = lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        right_shoulder = lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        left_hip = lm[mp_pose.PoseLandmark.LEFT_HIP.value]
        right_hip = lm[mp_pose.PoseLandmark.RIGHT_HIP.value]

        mid_shoulder = ((left_shoulder.x + right_shoulder.x) / 2, 
                        (left_shoulder.y + right_shoulder.y) / 2)
        mid_hip = ((left_hip.x + right_hip.x) / 2, 
                  (left_hip.y + right_hip.y) / 2)

        dx = mid_hip[0] - mid_shoulder[0]
        dy = mid_hip[1] - mid_shoulder[1]
        angle = math.degrees(math.atan2(dx, dy))
        
        return abs(angle)

    def check_ground_contact(self, landmarks):
        """Check if body parts are near the bottom of frame"""
        lm = landmarks.landmark
        ground_contact_points = 0
        ground_threshold = 0.8
        
        ground_points = [
            mp_pose.PoseLandmark.LEFT_ANKLE.value,
            mp_pose.PoseLandmark.RIGHT_ANKLE.value,
            mp_pose.PoseLandmark.LEFT_KNEE.value,
            mp_pose.PoseLandmark.RIGHT_KNEE.value
        ]
        
        for point_idx in ground_points:
            if lm[point_idx].y > ground_threshold and lm[point_idx].visibility > 0.5:
                ground_contact_points += 1
        
        return ground_contact_points / len(ground_points)

    def detect_fall_enhanced(self, frame):
        """Enhanced fall detection with tensor points and ground mapping"""
        start_time = time.time()
        
        # Process frame with MediaPipe (handles timestamp issues)
        pose_detected, landmarks, processed_frame = self.mediapipe_processor.process_frame(frame)
        
        # Initialize default values
        fall_detected = False
        fall_confidence = 0.0
        detection_details = {}
        velocity = 0.0
        torso_angle = 90.0
        height_ratio = 1.0
        ground_contact = 0.0
        ground_distance = None
        velocity_3d = None
        tensor_points = None

        if pose_detected and landmarks:
            lm = landmarks.landmark
            frame_height, frame_width = frame.shape[:2]
            
            # NEW: Calculate tensor points (3D position estimation)
            tensor_points = self.tensor_calculator.calculate_tensor_points(landmarks, frame.shape)
            
            # NEW: Update ground plane estimation
            ground_y = self.ground_estimator.update_ground_estimation(landmarks, frame_height)
            
            # NEW: Calculate 3D velocity from tensor points
            if tensor_points and self.prev_tensor_points:
                velocity_3d = self.tensor_calculator.calculate_fall_velocity_3d(
                    tensor_points, self.prev_tensor_points
                )
                if velocity_3d:
                    # Use Y-component for downward velocity (most relevant for falls)
                    velocity = abs(velocity_3d['y']) / frame_height  # Normalize
            else:
                # Fallback to 2D velocity calculation
                mid_shoulder_y = (lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y + 
                                 lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y) / 2
                if self.prev_shoulder_y is not None:
                    velocity = abs(mid_shoulder_y - self.prev_shoulder_y)
                self.prev_shoulder_y = mid_shoulder_y
            
            # Store current tensor points for next frame
            self.prev_tensor_points = tensor_points

            # Calculate fall indicators
            torso_angle = self.calculate_torso_angle(landmarks)
            ground_contact = self.check_ground_contact(landmarks)
            
            # NEW: Calculate distance to ground using tensor points
            if tensor_points and 'center_of_mass' in tensor_points and ground_y is not None:
                com_y_pixel = tensor_points['center_of_mass']['y']
                ground_distance = self.ground_estimator.get_ground_distance(
                    tensor_points['center_of_mass']['y'] / frame_height, frame_height
                )
            
            if self.normal_height is None and tensor_points:
                if 'center_of_mass' in tensor_points:
                    self.normal_height = tensor_points['center_of_mass']['y'] / frame_height
            elif not tensor_points:
                # Fallback to 2D calculation
                mid_shoulder_y = (lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y + 
                                 lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y) / 2
                if self.normal_height is None:
                    self.normal_height = mid_shoulder_y
                height_ratio = mid_shoulder_y / self.normal_height if self.normal_height else 1.0
            else:
                # Use tensor points for height ratio
                if 'center_of_mass' in tensor_points:
                    current_height = tensor_points['center_of_mass']['y'] / frame_height
                    height_ratio = current_height / self.normal_height if self.normal_height else 1.0

            # ENHANCED: Weighted scoring with tensor points and ground mapping
            # Higher weight for ground distance and 3D velocity
            ground_distance_factor = 0.0
            if ground_distance is not None:
                # If center of mass is very close to ground, high fall probability
                ground_distance_factor = 1.0 if ground_distance < 50 else (1.0 - min(ground_distance / 200, 1.0))
            
            velocity_factor = 1.0 if velocity > self.fall_indicators['velocity_threshold'] else 0.0
            if velocity_3d and velocity_3d['magnitude'] > 0:
                # Use 3D velocity magnitude for better detection
                velocity_factor = min(velocity_3d['magnitude'] / 100.0, 1.0)  # Normalize
            
            fall_score = (
                0.25 * velocity_factor +
                0.20 * (torso_angle < self.fall_indicators['torso_angle_threshold']) +
                0.20 * (height_ratio < self.fall_indicators['height_ratio_threshold']) + 
                0.15 * (ground_contact > self.fall_indicators['ground_contact_threshold']) +
                0.20 * ground_distance_factor  # NEW: Ground distance indicator
            )

            fall_confidence = fall_score
            fall_detected = fall_score > 0.6
            
            # Create detection details dictionary
            detection_details = {
                'velocity': velocity,
                'torso_angle': torso_angle,
                'height_ratio': height_ratio,
                'ground_contact': ground_contact,
                'fall_confidence': fall_confidence,
                'ground_distance': ground_distance,  # NEW
                'velocity_3d_magnitude': velocity_3d['magnitude'] if velocity_3d else None,  # NEW
                'tensor_points_available': tensor_points is not None,  # NEW
                'ground_plane_stable': self.ground_estimator.ground_plane_stable,  # NEW
            }
            
            # ML MODEL PREDICTION (if available)
            ml_prediction = None
            ml_confidence = None
            if ML_MODEL is not None:
                try:
                    # Prepare features for ML model
                    feature_vector = np.array([[
                        fall_confidence,
                        velocity,
                        torso_angle,
                        height_ratio,
                        ground_contact,
                        ground_distance if ground_distance is not None else 0.0,
                        velocity_3d['magnitude'] if velocity_3d and velocity_3d.get('magnitude') else 0.0
                    ]])
                    
                    # Get ML prediction
                    ml_prediction = ML_MODEL.predict(feature_vector)[0]
                    ml_proba = ML_MODEL.predict_proba(feature_vector)[0]
                    ml_confidence = ml_proba[1] if len(ml_proba) > 1 else ml_proba[0]  # Probability of fall
                    
                    # Hybrid approach: Combine rule-based and ML
                    # Weight: 60% ML, 40% rule-based (ML is trained on real data)
                    hybrid_confidence = 0.6 * ml_confidence + 0.4 * fall_confidence
                    hybrid_detected = hybrid_confidence > 0.5 or (ml_prediction == 1 and ml_confidence > 0.3)
                    
                    # Use hybrid if ML model is confident, otherwise use rule-based
                    if ml_confidence > 0.4:  # ML is confident
                        fall_detected = hybrid_detected
                        fall_confidence = hybrid_confidence
                        detection_details['fall_confidence'] = hybrid_confidence
                    # else: keep rule-based detection
                    
                    detection_details['ml_prediction'] = int(ml_prediction)
                    detection_details['ml_confidence'] = round(ml_confidence, 4)
                    detection_details['hybrid_confidence'] = round(hybrid_confidence, 4)
                except Exception as e:
                    print(f"⚠️  ML prediction error: {e}")
                    detection_details['ml_prediction'] = None
                    detection_details['ml_confidence'] = None

            # Update display with tensor and ground info
            self.update_display(processed_frame, detection_details, fall_detected, tensor_points, ground_y)
        else:
            # No pose detected - show message
            processed_frame = frame.copy()
            cv2.putText(processed_frame, "No Person Detected", (20, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        detection_time = time.time() - start_time

        # Update performance monitor
        self.performance_monitor.update_detection(
            fall_detected=fall_detected,
            actual_fall=None,
            confidence=fall_confidence,
            indicators={
                'velocity': velocity > self.fall_indicators['velocity_threshold'],
                'torso_angle': torso_angle < self.fall_indicators['torso_angle_threshold'],
                'height_ratio': height_ratio < self.fall_indicators['height_ratio_threshold'],
                'ground_contact': ground_contact > self.fall_indicators['ground_contact_threshold']
            },
            detection_time=detection_time,
            pose_detected=pose_detected
        )

        # Log features for ML dataset (label unknown at runtime -> None)
        try:
            self.feature_logger.log(
                user_id=self.current_user_id,
                fall_detected=fall_detected,
                actual_fall=None,
                pose_detected=pose_detected,
                details=detection_details
            )
        except Exception as e:
            print(f"⚠️ Feature log error: {e}")

        return processed_frame, fall_detected, detection_details

    def update_display(self, frame, details, fall_detected, tensor_points=None, ground_y=None):
        """Update frame with detection information including tensor points and ground mapping"""
        height, width, _ = frame.shape
        
        # Status
        status_text = "⚠️ FALL DETECTED!" if fall_detected else "✅ Normal"
        color = (0, 0, 255) if fall_detected else (0, 255, 0)
        cv2.putText(frame, status_text, (20, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        # Metrics
        y_offset = 60
        cv2.putText(frame, f"Confidence: {details.get('fall_confidence', 0):.2f}", (20, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y_offset += 20
        cv2.putText(frame, f"Velocity: {details.get('velocity', 0):.4f}", (20, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y_offset += 20
        cv2.putText(frame, f"Torso: {details.get('torso_angle', 0):.1f}°", (20, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # NEW: Display tensor and ground mapping info
        if details.get('tensor_points_available'):
            y_offset += 20
            if details.get('velocity_3d_magnitude') is not None:
                cv2.putText(frame, f"3D Vel: {details.get('velocity_3d_magnitude', 0):.1f}", (20, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
            y_offset += 20
            if details.get('ground_distance') is not None:
                cv2.putText(frame, f"Ground Dist: {details.get('ground_distance', 0):.1f}px", (20, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # NEW: Draw ground plane line
        if ground_y is not None:
            ground_y_int = int(ground_y)
            cv2.line(frame, (0, ground_y_int), (width, ground_y_int), (0, 255, 255), 2)
            cv2.putText(frame, "Ground Plane", (width - 150, ground_y_int - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        
        # NEW: Draw center of mass if available
        if tensor_points and 'center_of_mass' in tensor_points:
            com = tensor_points['center_of_mass']
            com_x = int(com['x'])
            com_y = int(com['y'])
            cv2.circle(frame, (com_x, com_y), 8, (255, 0, 255), -1)
            cv2.putText(frame, "COM", (com_x + 10, com_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)
        
        # User
        cv2.putText(frame, f"User: {self.current_user_id}", (width - 250, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

    def process_frame_for_fall(self, frame):
        """Main processing method with video recording"""
        processed_frame, fall_detected, details = self.detect_fall_enhanced(frame)
        
        # Always add frame to video buffer (for pre-fall recording)
        self.video_recorder.add_frame(processed_frame)
        
        # Get location from camera (if available)
        location = None
        global DB_CONN
        if DB_CONN:
            try:
                c = DB_CONN.cursor()
                c.execute("SELECT location FROM user_cameras WHERE user_id = ? AND is_active = 1 LIMIT 1",
                         (self.current_user_id,))
                cam_result = c.fetchone()
                if cam_result:
                    location = cam_result['location']
            except:
                pass
        
        # Fall confirmation logic
        if fall_detected:
            self.fall_counter += 1
            if self.fall_counter >= FALL_CONFIRM_FRAMES:
                # Start video recording if not already recording
                if not self.recording_fall_id:
                    fall_details = f"vel={details.get('velocity', 0):.4f}, angle={details.get('torso_angle', 0):.1f}, conf={details.get('fall_confidence', 0):.2f}"
                    
                    # Log fall to DB first (get fall ID)
                    fall_id = self.log_fall_to_db("CONFIRMED_FALL", fall_details, video_path=None, location=location)
                    
                    if fall_id:
                        # Start video recording
                        video_path = self.video_recorder.start_recording(fall_id, self.current_user_id)
                        if video_path:
                            # Update fall record with video path
                            try:
                                c = DB_CONN.cursor()
                                c.execute("UPDATE falls SET video_path = ? WHERE id = ?", (video_path, fall_id))
                                DB_CONN.commit()
                                self.recording_fall_id = fall_id
                                self.recording_start_time = time.time()
                                print(f"🎥 Recording video for fall ID {fall_id}: {video_path}")
                            except sqlite3.Error as e:
                                print(f"❌ Error updating video path: {e}")
                else:
                    # Continue recording current fall
                    self.video_recorder.record_frame(processed_frame)
                    
                    # Check if recording duration exceeded
                    if time.time() - self.recording_start_time >= self.recording_duration:
                        self.video_recorder.finish_recording()
                        self.recording_fall_id = None
                        self.recording_start_time = None
        else:
            # If no fall detected but we're recording, continue recording for a bit longer
            if self.recording_fall_id:
                self.video_recorder.record_frame(processed_frame)
                # Stop recording after duration
                if time.time() - self.recording_start_time >= self.recording_duration:
                    self.video_recorder.finish_recording()
                    self.recording_fall_id = None
                    self.recording_start_time = None
            else:
                self.fall_counter = 0
                if time.time() > self.last_fall_time + FALL_LOG_COOLDOWN:
                    self.fall_logged = False

        return processed_frame

# =========================================================
# ML MODEL INTEGRATION
# =========================================================
ML_MODEL = None
ML_MODEL_PATH = "models/fall_classifier.pkl"

def load_ml_model(model_path: str = None):
    """Load trained ML classifier model"""
    global ML_MODEL
    if model_path is None:
        model_path = ML_MODEL_PATH
    
    if not os.path.exists(model_path):
        print(f"⚠️  ML model not found at {model_path}. Using rule-based detection only.")
        return False
    
    try:
        from joblib import load
        ML_MODEL = load(model_path)
        print(f"✅ ML model loaded from {model_path}")
        return True
    except Exception as e:
        print(f"⚠️  Failed to load ML model: {e}. Using rule-based detection only.")
        return False

# Try to load ML model on startup
load_ml_model()

# Create global detector instance
detector = FallDetector()

# =========================================================
# VIDEO STREAM GENERATOR (FIXED VERSION)
# =========================================================
def generate_frames():
    """Generator with proper MediaPipe handling"""
    global detector

    print(f"🎬 Opening camera source: {detector.camera_source}")
    
    try:
        camera_index = int(detector.camera_source)
        cap = cv2.VideoCapture(camera_index)
        print(f"📷 Using camera index: {camera_index}")
    except ValueError:
        cap = cv2.VideoCapture(detector.camera_source)
        print(f"📷 Using camera URL: {detector.camera_source}")

    if not cap.isOpened():
        print(f"❌ Cannot open camera: {detector.camera_source}")
        while True:
            img = np.zeros((480, 640, 3), dtype='uint8')
            cv2.putText(img, f"Camera Error: {detector.camera_source}", (30, 240), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', img)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(2)

    # Camera settings
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 15)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer
    
    print(f"✅ Video stream started successfully")
    detector.is_running = True
    frame_count = 0

    try:
        while detector.is_running:
            success, frame = cap.read()
            frame_count += 1
            
            if not success:
                print("⚠️ Failed to read frame")
                time.sleep(0.1)
                continue

            try:
                # Process frame with fall detection
                processed_frame = detector.process_frame_for_fall(frame)

                # Encode as JPEG
                ret, buffer = cv2.imencode('.jpg', processed_frame, 
                                          [cv2.IMWRITE_JPEG_QUALITY, 85])
                if not ret:
                    continue

                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

                # Print metrics every 100 frames
                if frame_count % 100 == 0:
                    detector.performance_monitor.print_real_time_metrics()

                time.sleep(1/30)  # Target ~30fps

            except Exception as e:
                print(f"⚠️ Frame processing error: {e}")
                continue

    except Exception as e:
        print(f"❌ Stream error: {e}")
    finally:
        print("🛑 Releasing camera...")
        cap.release()
        detector.is_running = False
        print("🛑 Stream stopped")
        
        # Final report
        print("\n🎯 FINAL PERFORMANCE REPORT")
        detector.performance_monitor.print_real_time_metrics()

# =========================================================
# DATABASE INITIALIZATION
# =========================================================
def init_db(db_path, user_list_from_app=None):
    global DB_CONN, DB_PATH
    DB_PATH = db_path
    
    try:
        DB_CONN = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
        DB_CONN.row_factory = sqlite3.Row
        c = DB_CONN.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS falls (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        status TEXT NOT NULL,
                        details TEXT,
                        alert_sent INTEGER DEFAULT 0,
                        video_path TEXT,
                        severity TEXT DEFAULT 'moderate',
                        location TEXT,
                        response_time_seconds REAL,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )''')
        
        # Add new columns if they don't exist (migration)
        try:
            c.execute("ALTER TABLE falls ADD COLUMN video_path TEXT")
            print("✅ Added video_path column to falls table")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            c.execute("ALTER TABLE falls ADD COLUMN severity TEXT DEFAULT 'moderate'")
            print("✅ Added severity column to falls table")
        except sqlite3.OperationalError:
            pass
        
        try:
            c.execute("ALTER TABLE falls ADD COLUMN location TEXT")
            print("✅ Added location column to falls table")
        except sqlite3.OperationalError:
            pass
        
        try:
            c.execute("ALTER TABLE falls ADD COLUMN response_time_seconds REAL")
            print("✅ Added response_time_seconds column to falls table")
        except sqlite3.OperationalError:
            pass
        
        DB_CONN.commit()
        print(f"✅ Falls table initialized in {DB_PATH}")
        
    except sqlite3.Error as e:
        print(f"❌ Database init error: {e}")
        DB_CONN = None

def get_performance_report():
    """Get current performance metrics"""
    if hasattr(detector, 'performance_monitor'):
        return detector.performance_monitor.calculate_comprehensive_metrics()
    return {}

# =========================================================
# THREADED CAMERA (Non-Blocking Capture)
# =========================================================
class ThreadedCamera:
    """Captures frames in background thread"""
    
    def __init__(self, source=0):
        self.source = source
        self.capture = None
        self.frame_queue = queue.Queue(maxsize=2)
        self.stopped = False
        self.thread = None
        self.fps = 0
        self.last_frame_time = time.time()
        
    def start(self):
        """Start camera in background thread"""
        print(f"🎬 Starting threaded camera: {self.source}")
        
        try:
            camera_index = int(self.source)
            self.capture = cv2.VideoCapture(camera_index)
        except ValueError:
            self.capture = cv2.VideoCapture(self.source)
        
        if not self.capture.isOpened():
            print(f"❌ Camera failed: {self.source}")
            return False
        
        # Optimize settings
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.capture.set(cv2.CAP_PROP_FPS, 30)
        self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        self.stopped = False
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        
        print("✅ Threaded camera started")
        return True
    
    def _capture_loop(self):
        """Background capture loop"""
        while not self.stopped:
            if not self.capture or not self.capture.isOpened():
                break
            
            success, frame = self.capture.read()
            
            if success:
                # Calculate FPS
                current_time = time.time()
                self.fps = 1.0 / (current_time - self.last_frame_time + 0.001)
                self.last_frame_time = current_time
                
                # Update queue (drop old frames if full)
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except queue.Empty:
                        pass
                self.frame_queue.put(frame)
            
            time.sleep(0.001)  # Prevent CPU hogging
    
    def read(self):
        """Get latest frame (non-blocking)"""
        try:
            return True, self.frame_queue.get(timeout=1.0)
        except queue.Empty:
            return False, None
    
    def stop(self):
        """Stop camera thread"""
        self.stopped = True
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.capture:
            self.capture.release()
        print("✅ Camera stopped")
    
    def is_opened(self):
        return self.capture and self.capture.isOpened() and not self.stopped


# =========================================================
# ASYNC FRAME GENERATOR (Non-Blocking)
# =========================================================
def generate_frames_async():
    """
    Non-blocking frame generator using threaded camera
    This allows other Flask routes to remain responsive
    """
    global detector
    
    if not detector:
        print("❌ Detector not initialized")
        while True:
            error_frame = np.zeros((480, 640, 3), dtype='uint8')
            cv2.putText(error_frame, "Detector Not Available", (100, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', error_frame)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(1)
    
    # Start threaded camera
    camera = ThreadedCamera(detector.camera_source)
    
    if not camera.start():
        while True:
            error_frame = np.zeros((480, 640, 3), dtype='uint8')
            cv2.putText(error_frame, f"Camera Error: {detector.camera_source}", (50, 240),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', error_frame)
            if ret:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(2)
    
    print("✅ Async video stream started")
    
    frame_count = 0
    last_frame = None
    fps_display = 0
    fps_update_time = time.time()
    skip_count = 0
    
    try:
        while detector.is_running:
            # Get frame from threaded camera
            success, frame = camera.read()
            
            if not success or frame is None:
                if last_frame is not None:
                    frame = last_frame.copy()
                else:
                    time.sleep(0.01)
                    continue
            else:
                last_frame = frame.copy()
            
            frame_count += 1
            skip_count += 1
            
            # Process every 2nd frame to reduce load (KEY OPTIMIZATION)
            if skip_count % 2 == 0:
                try:
                    processed_frame = detector.process_frame_for_fall(frame)
                    
                    # Update FPS display
                    if time.time() - fps_update_time > 1.0:
                        fps_display = camera.fps
                        fps_update_time = time.time()
                    
                    # Add FPS indicator
                    cv2.putText(processed_frame, f"FPS: {fps_display:.1f}", 
                               (10, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                except Exception as e:
                    print(f"⚠️ Processing error: {e}")
                    processed_frame = frame
            else:
                # Use last processed frame (reduces CPU load significantly)
                processed_frame = last_frame
            
            # Encode with lower quality for speed (KEY OPTIMIZATION)
            try:
                ret, buffer = cv2.imencode('.jpg', processed_frame, 
                                          [cv2.IMWRITE_JPEG_QUALITY, 70])  # Lower quality = faster
                if not ret:
                    continue
                
                # Yield to Flask
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                
            except Exception as e:
                print(f"⚠️ Encoding error: {e}")
                continue
            
            # CRITICAL: Small sleep to allow other requests (KEY OPTIMIZATION)
            time.sleep(0.015)  # 15ms = allows dashboard to be responsive
            
            # Metrics every 300 frames
            if frame_count % 300 == 0:
                detector.performance_monitor.print_real_time_metrics()
    
    except GeneratorExit:
        print("🔌 Client disconnected")
    except Exception as e:
        print(f"❌ Stream error: {e}")
    finally:
        camera.stop()
        print("🛑 Async stream stopped")


# =========================================================
# STANDALONE TESTING
# =========================================================
if __name__ == "__main__":
    print("🧪 Running standalone test mode")
    
    DB_CONN = sqlite3.connect(DB_PATH, check_same_thread=False)
    init_db(DB_PATH, [])
    
    test_detector = FallDetector()
    test_detector.set_user_id("test_user")

    # Only define and use video_path here
    video_path = "fall_videos/test_fall.mov"  # Change to your video filename
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Cannot open video file: {video_path}")
        exit()

    # === Ground truth labels: 1 for fall, 0 for no fall, per frame ===
    # Example: [0, 0, 0, 1, 1, 1, 0, ...]
    # You should load this from a CSV or define it manually for your test video
    ground_truth_labels = [0]*80 + [1]*41 + [0]*79

    print("🎬 Starting test - Press 'q' to quit")
    frame_idx = 0
    try:
        while True:
            success, frame = cap.read()
            if not success:
                break

            # Get ground truth for this frame, or None if not available
            actual_fall = ground_truth_labels[frame_idx] if frame_idx < len(ground_truth_labels) else None

            # Patch: pass actual_fall to update_detection
            processed_frame, fall_detected, details = test_detector.detect_fall_enhanced(frame)
            test_detector.performance_monitor.update_detection(
                fall_detected=fall_detected,
                actual_fall=actual_fall,
                confidence=details.get('fall_confidence', 0.0),
                indicators={
                    'velocity': details.get('velocity', 0) > test_detector.fall_indicators['velocity_threshold'],
                    'torso_angle': details.get('torso_angle', 90) < test_detector.fall_indicators['torso_angle_threshold'],
                    'height_ratio': details.get('height_ratio', 1.0) < test_detector.fall_indicators['height_ratio_threshold'],
                    'ground_contact': details.get('ground_contact', 0) > test_detector.fall_indicators['ground_contact_threshold']
                },
                detection_time=0,  # Optionally measure time
                pose_detected=True  # Or set based on detection
            )

            # Also log features with ground truth label when available
            try:
                test_detector.feature_logger.log(
                    user_id="test_user",
                    fall_detected=fall_detected,
                    actual_fall=actual_fall,
                    pose_detected=True,
                    details=details
                )
            except Exception as e:
                print(f"⚠️ Test feature log error: {e}")

            print(f"Frame {frame_idx}: fall_detected={fall_detected}, actual_fall={actual_fall}")

            cv2.imshow("Fall Detection Test", processed_frame)
            frame_idx += 1

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if DB_CONN:
            DB_CONN.close()
        print("\n🎯 FINAL TEST REPORT")
        test_detector.performance_monitor.print_real_time_metrics()
        print(test_detector.performance_monitor.calculate_comprehensive_metrics())

print("\n🚀 ASYNC VIDEO COMPONENTS LOADED")
print("   - Threaded camera capture")
print("   - Non-blocking frame generation")
print("   - Optimized for dashboard responsiveness\n")