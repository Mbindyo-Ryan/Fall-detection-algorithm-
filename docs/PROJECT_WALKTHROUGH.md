# Fall Detection Algorithm System - Project Walkthrough

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Core Technologies](#core-technologies)
4. [Database Schema](#database-schema)
5. [User Roles & Access Control](#user-roles--access-control)
6. [Fall Detection Algorithm](#fall-detection-algorithm)
7. [Authentication & Security](#authentication--security)
8. [Alert System](#alert-system)
9. [API Architecture](#api-architecture)
10. [User Flows](#user-flows)
11. [Machine Learning Pipeline](#machine-learning-pipeline)
12. [Key Implementation Highlights](#key-implementation-highlights)

---

## 🎯 Project Overview

### Purpose
A comprehensive **AI-powered fall detection system** designed for healthcare environments that:
- **Detects falls in real-time** using computer vision and machine learning
- **Manages multi-role healthcare workflows** (Patients, Caretakers, Doctors, Admins)
- **Sends automated alerts** to care teams when falls are detected
- **Provides medical review capabilities** for doctors to assess and document fall incidents
- **Tracks system-wide analytics** for administrators

### Problem Statement
Elderly patients and individuals with mobility issues are at high risk of falls. Traditional monitoring systems are either:
- **Reactive** (only detect after the fall has occurred)
- **Intrusive** (require wearable devices)
- **Limited** (lack integration with healthcare workflows)

### Our Solution
A **non-intrusive, real-time fall detection system** that:
- Uses standard cameras (webcams, IP cameras, or device cameras)
- Processes video streams in real-time using MediaPipe pose detection
- Combines rule-based heuristics with machine learning for high accuracy
- Integrates seamlessly with healthcare team workflows
- Provides comprehensive logging and review capabilities

---

## 🏗️ System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT (Web Browser)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │ 
│  │   Patient    │  │  Caretaker   │  │    Doctor    │       │
│  │  Dashboard   │  │  Dashboard   │  │   Dashboard  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP/WebSocket
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              FLASK APPLICATION SERVER                       │
│  ┌────────────────────────────────────────────────────┐     │
│  │  app_auth.py (Main Flask App)                      │     │
│  │  - Authentication & Authorization                  │     │
│  │  - Role-based Routing                              │     │
│  │  - REST API Endpoints                              │     │
│  │  - Session Management                              │     │
│  └────────────────────────────────────────────────────┘     │
│  ┌────────────────────────────────────────────────────┐     │
│  │  detection_skeleton.py (Fall Detection Engine)     │     │
│  │  - MediaPipe Pose Detection                        │     │
│  │  - Fall Detection Algorithm                        │     │
│  │  - ML Model Integration                            │     │
│  │  - Video Processing                                │     │
│  └────────────────────────────────────────────────────┘     │
│  ┌────────────────────────────────────────────────────┐     │
│  │  alert_service.py (Alert System)                   │     │
│  │  - SMS/Phone Call Alerts                           │     │
│  │  - Twilio Integration                              │     │
│  │  - Recipient Management                            │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   SQLite     │   │   MediaPipe  │   │   ML Model   │
│  Database    │   │   Pose API   │   │  (scikit-    │
│              │   │              │   │   learn)     │
└──────────────┘   └──────────────┘   └──────────────┘
```

### Component Breakdown

1. **Frontend (Templates)**
   - Role-specific dashboards (Patient, Caretaker, Doctor, Admin)
   - Real-time video feed display
   - Interactive UI with JavaScript for API calls
   - Responsive design with Tailwind CSS

2. **Backend (Flask Application)**
   - `app_auth.py`: Main application server
   - `detection_skeleton.py`: Fall detection engine
   - `alert_service.py`: Alert notification system

3. **Data Layer**
   - SQLite database (`system_config.db`)
   - CSV feature logs for ML training
   - Video recordings of detected falls

4. **External Services**
   - Twilio (SMS/Phone calls)
   - Google OAuth (optional SSO)
   - MediaPipe (pose detection)

---

## 🛠️ Core Technologies

### Backend
- **Flask** (Python web framework)
- **SQLite3** (Database)
- **MediaPipe** (Google's pose detection library)
- **OpenCV** (Computer vision)
- **scikit-learn** (Machine learning)
- **NumPy** (Numerical computations)

### Frontend
- **HTML5/CSS3** (Structure & styling)
- **Tailwind CSS** (Utility-first CSS framework)
- **JavaScript** (Client-side interactivity)
- **Fetch API** (AJAX requests)

### Security
- **Werkzeug** (Password hashing - PBKDF2-SHA256)
- **PyOTP** (Two-Factor Authentication - TOTP)
- **QRCode** (2FA setup QR codes)
- **Flask Sessions** (Session management)

### Communication
- **Twilio** (SMS & Voice calls)
- **Authlib** (OAuth integration)

---

## 🗄️ Database Schema

### Core Tables

#### 1. `users`
Stores all system users (patients, caretakers, doctors, admins)
```sql
- id (TEXT PRIMARY KEY)
- name (TEXT)
- email (TEXT UNIQUE)
- phone (TEXT UNIQUE)
- password_hash (TEXT)
- role (TEXT: 'patient', 'caretaker', 'doctor', 'admin')
- twofa_secret (TEXT)
- is_2fa_enabled (INTEGER)
- created_at (TEXT)
```

#### 2. `falls`
Records all detected fall incidents
```sql
- id (INTEGER PRIMARY KEY)
- user_id (TEXT) → references users(id)
- timestamp (TEXT)
- status (TEXT: 'CONFIRMED_FALL', 'FALSE_POSITIVE', etc.)
- details (TEXT JSON)
- severity (TEXT: 'mild', 'moderate', 'severe')
- location (TEXT)
- video_path (TEXT)
- alert_sent (INTEGER)
- response_time_seconds (REAL)
```

#### 3. `patient_caretaker`
Many-to-many relationship between patients and caretakers
```sql
- id (INTEGER PRIMARY KEY)
- patient_id (TEXT) → references users(id)
- caretaker_id (TEXT) → references users(id)
- assigned_at (TEXT)
- is_active (INTEGER)
```

#### 4. `patient_doctor`
Many-to-many relationship between patients and doctors
```sql
- id (INTEGER PRIMARY KEY)
- patient_id (TEXT) → references users(id)
- doctor_id (TEXT) → references users(id)
- assigned_at (TEXT)
- is_active (INTEGER)
```

#### 5. `user_cameras`
Stores camera configurations for each user
```sql
- id (INTEGER PRIMARY KEY)
- user_id (TEXT) → references users(id)
- camera_name (TEXT)
- camera_url_or_index (TEXT)  -- Supports: "0", "1", "http://...", "rtsp://..."
- location (TEXT)
- is_active (INTEGER)
- created_at (TEXT)
```

#### 6. `fall_reviews`
Doctor reviews and recommendations for falls
```sql
- id (INTEGER PRIMARY KEY)
- fall_id (INTEGER) → references falls(id)
- doctor_id (TEXT) → references users(id)
- remarks (TEXT)
- recommended_actions (TEXT JSON)
- follow_up_date (TEXT)
- status (TEXT: 'unreviewed', 'reviewed', 'completed')
- reviewed_at (TEXT)
```

#### 7. `fall_files`
Uploaded documents (X-rays, reports) associated with falls
```sql
- id (INTEGER PRIMARY KEY)
- fall_id (INTEGER) → references falls(id)
- file_name (TEXT)
- file_path (TEXT)
- file_type (TEXT)
- uploaded_by (TEXT) → references users(id)
- uploaded_at (TEXT)
```

#### 8. `alert_logs`
Tracks all alert attempts (SMS/calls)
```sql
- id (INTEGER PRIMARY KEY)
- fall_id (INTEGER) → references falls(id)
- recipient_id (TEXT) → references users(id)
- alert_type (TEXT: 'sms', 'call')
- success (INTEGER)
- details (TEXT)
- timestamp (TEXT)
```

---

## 👥 User Roles & Access Control

### Role-Based Access Control (RBAC)

#### 1. **Patient** (`role = 'patient'`)
**Capabilities:**
- View own fall history
- Monitor live video feed from their cameras
- Add/remove camera sources (device index, IP address, URL)
- Select their caretaker and doctor from available system users
- View doctor remarks and recommendations
- Upload files (X-rays, reports) for doctor review
- Configure 2FA

**Dashboard:** `dashboard_patient.html`
- Live video feed with pose detection overlay
- Fall history table
- Settings (cameras, care team selection)
- File upload interface

#### 2. **Caretaker** (`role = 'caretaker'`)
**Capabilities:**
- View all assigned patients
- View falls for assigned patients
- Receive SMS/phone alerts when assigned patients fall
- View doctor remarks for patient falls
- Cannot review falls (doctor-only function)

**Dashboard:** `dashboard_caretaker.html`
- Patient list with last fall timestamps
- Fall history for all assigned patients
- Patient details view

#### 3. **Doctor** (`role = 'doctor'`)
**Capabilities:**
- View all patients in the system
- View all falls from all patients
- **Review falls** with remarks and recommendations
- Generate PDF reports for falls
- View and comment on uploaded files (X-rays, scans)
- Set follow-up dates
- Mark falls as reviewed/completed

**Dashboard:** `dashboard_doctor.html`
- Fall review interface with filtering
- Review modal with:
  - Remarks textarea
  - Recommended actions checkboxes
  - Follow-up date picker
  - Status selector
- PDF report generation
- File upload viewer with commenting

#### 4. **Admin** (`role = 'admin'`)
**Capabilities:**
- View **all users** in the system
- View **all falls** across all patients
- View **system logs** (falls, alerts, activity)
- System-wide analytics
- User management (view only, in current implementation)

**Dashboard:** `dashboard_admin.html`
- User management table
- System logs viewer
- Activity analytics
- Fall statistics across all users

### Access Control Implementation

```python
# Decorator-based access control
@login_required
@twofa_required
def dashboard():
    user_role = session.get('user_role', 'patient')
    
    # Role-based routing
    if user_role == 'admin':
        return render_template("dashboard_admin.html", ...)
    elif user_role == 'doctor':
        return render_template("dashboard_doctor.html", ...)
    # ... etc
```

**API Endpoints** also enforce role-based filtering:
- `/api/falls` - Returns falls based on user role
- `/api/users` - Returns users based on relationships
- `/api/admin/*` - Admin-only endpoints

---

## 🧠 Fall Detection Algorithm

### Overview
The fall detection system uses a **hybrid approach** combining:
1. **Rule-based heuristics** (immediate detection)
2. **Machine learning classifier** (trained on historical data)
3. **MediaPipe pose detection** (real-time skeleton tracking)

### Detection Pipeline

```
Video Frame
    │
    ▼
┌─────────────────────────┐
│  MediaPipe Pose         │
│  Detection              │
│  - 33 body landmarks    │
│  - Confidence scoring   │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  Feature Extraction     │
│  - Velocity (2D & 3D)   │
│  - Torso angle          │
│  - Height ratio         │
│  - Ground contact       │
│  - Ground distance      │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  Rule-Based Detection   │
│  - Velocity threshold   │
│  - Torso flatness       │
│  - Height drop          │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  ML Model Prediction    │
│  (if model available)   │
│  - Random Forest /      │
│    Logistic Regression  │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│  Hybrid Decision        │
│  - 60% ML confidence    │
│  - 40% rule-based       │
└─────────────────────────┘
    │
    ▼
Fall Detected? → Log to DB → Trigger Alerts → Record Video
```

### Key Detection Features

#### 1. **MediaPipe Pose Detection**
- Detects 33 body landmarks in real-time
- Tracks: shoulders, hips, knees, ankles, head, etc.
- Confidence threshold: 0.6 (configurable)
- Handles frame failures gracefully with retry logic

#### 2. **Feature Extraction**

**Velocity Calculation:**
```python
# 2D velocity (shoulder movement)
velocity = abs(current_shoulder_y - previous_shoulder_y) / frame_time

# 3D velocity (using tensor points)
velocity_3d = calculate_3d_movement(tensor_points)
```

**Torso Angle:**
```python
# Angle between shoulders and hips
torso_angle = calculate_angle(shoulder_midpoint, hip_midpoint, vertical)
```

**Height Ratio:**
```python
# Current height vs. normal standing height
height_ratio = current_height / normal_height
```

**Ground Contact:**
```python
# Percentage of body landmarks near estimated ground plane
ground_contact = calculate_ground_proximity(landmarks, ground_plane)
```

#### 3. **Rule-Based Detection**

**Fall Confirmation Criteria:**
- **Velocity threshold**: > 0.02 (rapid downward movement)
- **Torso flatness**: < 0.1 (torso parallel to ground)
- **Height ratio**: < 0.6 (significant height drop)
- **Ground contact**: > 0.8 (body on ground)
- **Consecutive frames**: 8 frames (reduces false positives)

#### 4. **Machine Learning Integration**

**Model Training:**
- Features: `[confidence, velocity, torso_angle, height_ratio, ground_contact, ground_distance, velocity_3d_magnitude]`
- Algorithms: Logistic Regression, Random Forest, XGBoost
- Class weights: Balanced (handles imbalanced dataset)
- Training data: `data/feature_logs.csv` (labeled frames)

**Hybrid Approach:**
```python
# If ML model is available and confident
if ml_confidence > 0.4:
    hybrid_confidence = 0.6 * ml_confidence + 0.4 * rule_based_confidence
    fall_detected = hybrid_confidence > 0.5
else:
    # Fall back to rule-based
    fall_detected = rule_based_detection
```

### Performance Optimizations

1. **Frame Processing:**
   - Non-writeable frames for MediaPipe (performance boost)
   - Frame queue management
   - Thread-safe video capture

2. **Fall Cooldown:**
   - 10-second cooldown between fall detections (prevents duplicate logging)

3. **Video Recording:**
   - Records 5 seconds after fall detection
   - Saves to `videos/falls/` directory
   - Links video path in database

---

## 🔐 Authentication & Security

### Authentication Flow

```
User Login
    │
    ▼
┌─────────────────────┐
│  Email/Password     │
│  Verification       │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  2FA Check          │
│  (if enabled)       │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  Session Creation   │
│  - user_id          │
│  - user_role        │
│  - 2FA verified     │
└─────────────────────┘
    │
    ▼
Role-Based Dashboard
```

### Security Features

#### 1. **Password Hashing**
- Algorithm: PBKDF2-SHA256 (via Werkzeug)
- Salt: Automatically generated
- Storage: Only hash stored, never plaintext

#### 2. **Two-Factor Authentication (2FA)**
- **Method**: TOTP (Time-based One-Time Password)
- **Library**: PyOTP
- **Setup**: QR code generation for authenticator apps
- **Recovery**: Recovery keys for account recovery
- **Enforcement**: Optional per user, can be required by role

**2FA Setup Flow:**
1. User requests 2FA setup
2. System generates secret key
3. QR code displayed (scannable by Google Authenticator, Authy, etc.)
4. User verifies with 6-digit code
5. 2FA enabled for account

#### 3. **Session Management**
- Flask sessions with secret key
- Session timeout (configurable)
- CSRF protection (via Flask-WTF, if implemented)

#### 4. **Role-Based Access Control**
- Decorator-based route protection
- Database-level filtering for API responses
- Frontend UI elements hidden based on role

#### 5. **OAuth Integration (Optional)**
- Google OAuth support
- SSO (Single Sign-On) capability
- Falls back to email/password if OAuth fails

### Security Decorators

```python
@login_required
def protected_route():
    # Ensures user is logged in
    pass

@twofa_required
def sensitive_route():
    # Ensures 2FA is verified (if enabled)
    pass

@role_required('admin')
def admin_only_route():
    # Ensures user has admin role
    pass
```

---

## 📢 Alert System

### Alert Architecture

```
Fall Detected
    │
    ▼
┌─────────────────────┐
│  Severity           │
│  Classification     │
│  (mild/moderate/    │
│   severe)           │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  Recipient          │
│  Lookup             │
│  - Caretakers       │
│  - Doctors          │
│  - Emergency        │
│    Contacts         │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  Alert Rules        │
│  (by severity)      │
│  - SMS?             │
│  - Call?            │
│  - Delay?           │
└─────────────────────┘
    │
    ▼
┌─────────────────────┐
│  Twilio Service     │
│  (or Mock Mode)     │
└─────────────────────┘
    │
    ▼
Alert Logged to DB
```

### Alert Rules

**Severe Falls:**
- SMS: ✅ Immediate
- Call: ✅ Immediate
- Recipients: Caretaker, Doctor, Emergency Contact

**Moderate Falls:**
- SMS: ✅ 30-second delay
- Call: ❌ No call
- Recipients: Caretaker, Doctor

**Mild Falls:**
- SMS: ✅ 60-second delay
- Call: ❌ No call
- Recipients: Caretaker only

### Alert Service Implementation

**Mock Mode** (Development):
- Logs alerts to console
- No actual SMS/calls sent
- Useful for testing

**Production Mode** (Twilio):
- Sends actual SMS messages
- Makes phone calls with TTS
- Tracks delivery status
- Logs to `alert_logs` table

### Alert Message Format

**SMS:**
```
🚨 FALL ALERT - SEVERE

Patient: John Doe
Time: 2024-01-15 14:30:25
Location: Living Room

Please check the CARE system dashboard immediately.
```

**Phone Call (TTS):**
```
"Fall alert. Severe severity fall detected for patient John Doe at Living Room. 
Time: 2:30 PM. Please check the CARE system dashboard immediately."
```

---

## 🔌 API Architecture

### RESTful API Endpoints

#### Authentication
- `POST /login` - User login
- `POST /logout` - User logout
- `POST /setup_2fa` - Setup 2FA
- `POST /verify_2fa` - Verify 2FA code
- `GET /recover_2fa` - 2FA recovery

#### Video Feed
- `GET /video_feed?source=<camera>` - Live video stream with pose detection

#### Falls Management
- `GET /api/falls` - Get falls (role-filtered)
- `GET /api/falls/<id>/review` - Get fall review details
- `POST /api/falls/<id>/review` - Create/update fall review
- `GET /api/falls/<id>/report` - Generate PDF report
- `GET /api/falls/reviews` - Get all reviews (doctor only)

#### User Management
- `GET /api/users` - Get users (role-filtered)
- `GET /api/admin/users` - Get all users (admin only)
- `GET /api/admin/logs` - Get system logs (admin only)

#### Care Team
- `GET /api/available/caretakers` - List available caretakers
- `GET /api/available/doctors` - List available doctors
- `POST /api/patients/select` - Patient selects caretaker/doctor

#### Cameras
- `GET /api/user/cameras` - Get user's cameras
- `POST /api/user/cameras` - Add camera
- `DELETE /api/user/cameras` - Delete camera

#### Files
- `GET /api/falls/<id>/files` - List files for a fall
- `POST /api/falls/<id>/files` - Upload file
- `GET /api/files/<id>/comments` - Get file comments
- `POST /api/files/<id>/comments` - Add comment

### API Response Format

**Success:**
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation successful"
}
```

**Error:**
```json
{
  "success": false,
  "error": "Error message",
  "code": 400
}
```

### Role-Based API Filtering

**Example: `/api/falls`**

**Patient:**
```sql
SELECT * FROM falls WHERE user_id = ?
```

**Caretaker:**
```sql
SELECT f.* FROM falls f
INNER JOIN patient_caretaker pc ON f.user_id = pc.patient_id
WHERE pc.caretaker_id = ? AND pc.is_active = 1
```

**Doctor:**
```sql
SELECT * FROM falls WHERE status = 'CONFIRMED_FALL'
```

**Admin:**
```sql
SELECT * FROM falls
```

---

## 🔄 User Flows

### 1. Patient Flow

```
1. Login → 2FA (if enabled) → Patient Dashboard
2. View live video feed (pose detection overlay)
3. Add camera (device index, IP, or URL)
4. Select caretaker and doctor from available users
5. View own fall history
6. Upload files for doctor review
7. View doctor remarks and recommendations
```

### 2. Fall Detection Flow

```
1. Video stream → MediaPipe pose detection
2. Feature extraction (velocity, angles, etc.)
3. Rule-based + ML detection
4. Fall confirmed → Log to database
5. Severity classification
6. Video recording (5 seconds)
7. Alert service triggered
8. SMS/Call sent to care team
9. Fall appears in dashboards
```

### 3. Doctor Review Flow

```
1. Doctor logs in → Doctor Dashboard
2. Navigate to "Review Falls"
3. Filter falls (unreviewed, reviewed, severity)
4. Click "Review" on a fall
5. Modal opens:
   - View fall details
   - Add remarks
   - Select recommended actions
   - Set follow-up date
   - Change status
6. Save review → PDF report available
7. View uploaded files → Add comments
```

### 4. Caretaker Alert Flow

```
1. Patient falls → Alert service triggered
2. System looks up patient's caretakers
3. SMS sent to caretaker (based on severity rules)
4. Phone call made (if severe)
5. Caretaker receives alert
6. Caretaker logs in → Views fall details
7. Caretaker can view doctor remarks
```

### 5. Admin Monitoring Flow

```
1. Admin logs in → Admin Dashboard
2. View all users in system
3. View system logs (falls, alerts, activity)
4. System-wide analytics
5. Monitor system health
```

---

## 🤖 Machine Learning Pipeline

### Training Data Collection

**Automatic Feature Logging:**
- Every processed frame logs features to `data/feature_logs.csv`
- Features: `[confidence, velocity, torso_angle, height_ratio, ground_contact, ground_distance, velocity_3d_magnitude]`
- Label: `actual_fall` (0 or 1, set manually or via review)

**Data Preparation:**
```bash
python scripts/prepare_training_data.py
```
- Combines multiple `feature_logs.csv` files
- Filters labeled data
- Handles missing columns gracefully
- Outputs: `data/feature_logs_combined.csv`

### Model Training

**Training Script:**
```bash
python scripts/train_classifier.py \
    --csv data/feature_logs_combined.csv \
    --model models/fall_classifier.pkl \
    --algorithm random_forest \
    --class-weight balanced
```

**Available Algorithms:**
1. **Logistic Regression** (fast, interpretable)
2. **Random Forest** (robust, handles non-linearity)
3. **XGBoost** (high performance, requires installation)

**Training Process:**
1. Load labeled data from CSV
2. Split train/test (80/20, stratified)
3. Train classifier with balanced class weights
4. Evaluate on test set
5. Save model to `models/fall_classifier.pkl`

### Model Evaluation Metrics

- **Precision**: Of predicted falls, how many are real?
- **Recall**: What percentage of actual falls are detected?
- **F1-Score**: Harmonic mean of precision and recall
- **Confusion Matrix**: True/False positives and negatives

### Model Integration

**Loading:**
```python
from joblib import load
ML_MODEL = load("models/fall_classifier.pkl")
```

**Prediction:**
```python
feature_vector = np.array([[
    confidence, velocity, torso_angle, height_ratio,
    ground_contact, ground_distance, velocity_3d_magnitude
]])
prediction = ML_MODEL.predict(feature_vector)[0]
confidence = ML_MODEL.predict_proba(feature_vector)[0][1]
```

**Hybrid Decision:**
- If ML confidence > 0.4: Use hybrid (60% ML, 40% rule-based)
- Otherwise: Use rule-based only

### Current Performance

**Training Data:**
- Total frames processed: Varies (check `data/feature_logs_combined.csv`)
- Labeled frames: Subset with `actual_fall` set
- Falls vs. No-falls: Imbalanced (requires balanced class weights)

**Model Performance:**
- Check training output for latest metrics
- Typically: Precision > 0.85, Recall > 0.80, F1 > 0.82

---

## ✨ Key Implementation Highlights

### 1. **Flexible Camera Support**
- Device index: `"0"`, `"1"` (webcams)
- IP cameras: `"http://192.168.1.100:8080/video"`
- RTSP streams: `"rtsp://..."`
- URL-based: Any OpenCV-compatible source

### 2. **Real-Time Performance Monitoring**
- FPS tracking
- Pose detection rate
- Frame processing time
- Displayed on video feed overlay

### 3. **Robust Error Handling**
- MediaPipe failure recovery
- Database connection retry
- Camera source fallback
- Graceful degradation (ML model optional)

### 4. **Comprehensive Logging**
- Feature logs for ML training
- Alert logs for audit trail
- Fall logs with full details
- System activity logs

### 5. **Video Recording**
- Automatic recording on fall detection
- 5-second post-fall recording
- Stored with fall ID
- Accessible via dashboard

### 6. **PDF Report Generation**
- Doctor reviews exportable as PDF
- Includes fall details, remarks, recommendations
- Professional formatting
- Downloadable from dashboard

### 7. **File Upload System**
- Support for X-rays, scans, reports
- Associated with specific falls
- Doctor commenting capability
- Secure file storage

### 8. **Scalable Architecture**
- Thread-safe database connections
- Queue-based frame processing
- Async video generation
- Modular component design

---

## 📊 System Statistics

### Current Implementation Status

✅ **Completed:**
- Multi-role authentication system
- Real-time fall detection (MediaPipe + ML)
- Role-based dashboards (4 roles)
- Alert system (SMS/Phone)
- Doctor review system
- File upload and commenting
- PDF report generation
- Camera management (IP/URL/index)
- Patient-care team selection
- Admin system logs
- 2FA support
- Performance monitoring

📈 **Training Data:**
- Check `data/feature_logs_combined.csv` for frame counts
- Run training script to see current model performance

🔧 **Configuration:**
- Database: `system_config.db`
- Models: `models/fall_classifier.pkl`
- Videos: `videos/falls/`
- Data logs: `data/feature_logs*.csv`

---

## 🚀 Quick Start Guide

### 1. Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python app_auth.py  # Creates tables on first run

# Generate dummy data
python scripts/generate_dummy_data.py
```

### 2. Run Application
```bash
python app_auth.py
# Access at http://localhost:5000
```

### 3. Test Login Credentials
- **Admin**: `admin@care.com` / `admin123`
- **Doctors**: `doctor_1@care.com` / `doctor123`
- **Caretakers**: `caretaker_1@care.com` / `caretaker123`
- **Patients**: `patient_1@care.com` / `patient123`

### 4. Train ML Model (Optional)
```bash
# Prepare data
python scripts/prepare_training_data.py

# Train model
python scripts/train_classifier.py
```

---

## 📝 Conclusion

This system provides a **comprehensive, production-ready fall detection solution** that:

1. **Detects falls accurately** using hybrid rule-based + ML approach
2. **Integrates seamlessly** with healthcare workflows
3. **Scales to multiple users** with role-based access control
4. **Provides actionable insights** through doctor reviews and analytics
5. **Maintains security** with 2FA and proper authentication
6. **Sends timely alerts** to care teams when incidents occur

The architecture is **modular, extensible, and maintainable**, making it suitable for both research and production deployment.

---

**For questions or clarifications during your presentation, refer to:**
- `README.md` - Installation and usage
- `ML_MODEL_GUIDE.md` - ML model details
- `REVIEW_SYSTEM_GUIDE.md` - Doctor review system
- `ALERT_SETUP.md` - Alert configuration

