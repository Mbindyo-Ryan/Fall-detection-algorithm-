# CARE SYSTEM: Real-Time Fall Detection Dashboard

The CARE (Continuous Alert and Responsive Engagement) System is a comprehensive web-based monitoring application designed to detect and manage fall incidents in real-time, focusing on elderly care and assisted living environments. Built using Flask and integrated with Google OAuth and Two-Factor Authentication (2FA) for security, it provides a secure, centralized platform for patients, caregivers, doctors, and administrators to monitor video feeds, manage alerts, and coordinate care.

## 🚀 Key Features

### 🔐 Security & Authentication
- **Secure Authentication**: User login via local registration or Google Single Sign-On (SSO)
- **Mandatory Two-Factor Authentication (2FA)**: Enhanced security using TOTP (Time-based One-Time Password) via authenticator apps like Google Authenticator
- **Role-Based Access Control**: Four distinct user roles (Admin, Doctor, Caretaker, Patient) with role-specific dashboards and permissions

### 👥 Multi-Role System
- **Admin Dashboard**: Complete system oversight with user management, activity monitoring, and system logs
- **Doctor Dashboard**: Review patient falls, provide medical assessments, and manage patient care
- **Caretaker Dashboard**: Monitor assigned patients, receive alerts, and coordinate care
- **Patient Dashboard**: View personal fall history, select care team members, and manage settings

### 📹 Real-Time Monitoring
- **Live Video Feed**: Integrates live camera feed with pose detection and fall detection algorithms
- **Real-Time Metrics**: Displays pose detection rate, FPS, and detection confidence in video overlay
- **Fall Detection**: Advanced ML-based fall detection using MediaPipe pose estimation and Random Forest classification

### 📊 Data Management
- **User and Fall Management**: Comprehensive tracking of users, fall incidents, and relationships
- **Patient-Care Team Selection**: Patients can choose their caretakers and doctors from available system users
- **Doctor Reviews**: Doctors can review falls, add remarks, recommendations, and follow-up dates
- **File Uploads**: Patients can upload X-rays, scans, and reports for doctor review
- **System Logs**: Admin can view all system activity including falls and alerts

### 💾 Database
- **SQLite Database**: Embedded SQLite database (system_config.db) managing users, falls, relationships, reviews, and alerts
- **Dummy Data Generator**: Script to populate database with test users and realistic fall data

🛠️ Prerequisites
Before running the application, ensure you have the following installed:

Python 3.8+

pip (Python package installer)

Google OAuth Configuration
This application requires Google API credentials for SSO.

Create a project in the [Google Cloud Console].

Enable the "Google People API" (though minimal scope is used, this ensures all necessary dependencies are met).

Go to "APIs & Services" > "Credentials" and create an OAuth 2.0 Client ID of type "Web application".

Set the Authorized JavaScript origins to:

http://127.0.0.1:5000

http://localhost:5000

Set the Authorized redirect URIs to:

http://127.0.0.1:5000/authorize/google

http://localhost:5000/authorize/google

You will need the generated Client ID and Client Secret for the setup step below.

💻 Installation and Setup
1. Clone the Repository
git clone [YOUR_REPO_URL_HERE]
cd CARE_System

2. Install Python Dependencies
The application relies on Flask, Authlib, Werkzeug, PyOTP, QRCode, MediaPipe, scikit-learn, and other ML libraries.

```bash
pip install flask authlib werkzeug pyotp qrcode mediapipe scikit-learn opencv-python numpy pandas
```

3. Set Environment Variables
You must set the following environment variables. The Flask application is configured to read these automatically.

Variable

Description

FLASK_SECRET

A long, complex, random string for session security.

GOOGLE_CLIENT_ID

Your OAuth Client ID from Google Cloud.

GOOGLE_CLIENT_SECRET

Your OAuth Client Secret from Google Cloud.

Example (Linux/macOS):

export FLASK_SECRET="your_highly_secret_key_here"
export GOOGLE_CLIENT_ID="YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="YOUR_GOOGLE_CLIENT_SECRET"

Example (Windows - Command Prompt):

set FLASK_SECRET="your_highly_secret_key_here"
set GOOGLE_CLIENT_ID="YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com"
set GOOGLE_CLIENT_SECRET="YOUR_GOOGLE_CLIENT_SECRET"

4. Generate Dummy Data (Optional but Recommended)
To populate the database with test users and fall data:

```bash
python scripts/generate_dummy_data.py
```

This creates:
- 1 Admin user
- 4 Doctor users
- 4 Caretaker users
- 12 Patient users (one with multiple falls for testing)
- Fall incidents and doctor reviews

**Test Login Credentials:**
- **Admin**: `admin@care.com` / `admin123`
- **Doctors**: `sarah.thompson@care.com` / `doctor123` (and 3 others)
- **Caretakers**: `alice.cooper@care.com` / `caretaker123` (and 3 others)
- **Patients**: `john.smith@patient.com` / `patient123` (and 11 others)

5. Run the Application
Execute the main authentication file to start the Flask server:

```bash
python app_auth.py
```

The application will now be running at http://127.0.0.1:5000/.

## 📄 Project File Structure

| File/Directory | Description |
|---------------|-------------|
| `app_auth.py` | Core Flask App. Handles all routing, local/Google authentication, 2FA logic, session management, role-based dashboards, and API endpoints |
| `detection_skeleton.py` | Fall Detection Module. Contains MediaPipe pose detection, ML-based fall classification, video frame processing, and database interaction for logging falls |
| `system_config.db` | SQLite Database. Automatically created on first run, storing users, falls, relationships, reviews, files, and alerts |
| `scripts/generate_dummy_data.py` | Dummy data generator script to populate database with test users and realistic fall data |
| `templates/login.html` | User interface for local login, registration, and Google SSO |
| `templates/dashboard_admin.html` | Admin dashboard with user management, system logs, and activity monitoring |
| `templates/dashboard_doctor.html` | Doctor dashboard for reviewing falls and managing patients |
| `templates/dashboard_caretaker.html` | Caretaker dashboard for monitoring assigned patients |
| `templates/dashboard_patient.html` | Patient dashboard with personal stats, fall history, and care team selection |
| `templates/twofa_setup.html` | Page for new users to scan the QR code and enable 2FA |
| `templates/verify_2fa.html` | Page to prompt users for the TOTP code upon login |

## 🔑 User Roles & Permissions

### Admin
- View all users and their activity
- Access system logs (falls and alerts)
- Monitor system-wide metrics
- Full system oversight

### Doctor
- View all patient falls
- Review falls and add medical assessments
- Provide recommendations and follow-up dates
- View patient-uploaded files (X-rays, scans)
- Comment on uploaded files

### Caretaker
- View assigned patients only
- Receive alerts for assigned patients' falls
- Monitor patient activity
- View doctor reviews for assigned patients

### Patient
- View personal fall history
- Select caretakers and doctors from system
- Upload files (X-rays, scans, reports)
- View doctor reviews and comments
- Manage personal settings and detection sensitivity

## 🔌 API Endpoints

### Public Endpoints
- `GET /` - Login/Registration page
- `POST /register` - User registration
- `POST /login` - User login
- `GET /authorize/google` - Google OAuth callback

### Authenticated Endpoints
- `GET /dashboard` - Role-based dashboard
- `GET /video_feed` - Live video stream with fall detection
- `GET /api/falls` - Get falls (role-filtered)
- `GET /api/users` - Get users (role-filtered)
- `POST /api/patients/select` - Patient selects caretaker/doctor
- `GET /api/available/caretakers` - List available caretakers
- `GET /api/available/doctors` - List available doctors
- `GET /api/admin/users` - Admin: view all users
- `GET /api/admin/logs` - Admin: view system logs
- `POST /api/falls/<id>/files` - Upload file for fall
- `GET /api/falls/<id>/remarks` - Get doctor review for fall
- `POST /api/falls/<id>/review` - Doctor reviews a fall

## 🎯 Quick Start Guide

1. **Set up environment variables** (see Installation section)
2. **Install dependencies**: `pip install flask authlib werkzeug pyotp qrcode mediapipe scikit-learn opencv-python numpy pandas`
3. **Generate dummy data**: `python scripts/generate_dummy_data.py`
4. **Run the application**: `python app_auth.py`
5. **Login as admin**: `admin@care.com` / `admin123`
6. **Explore different roles**: Try logging in as doctor, caretaker, or patient

## 📝 Notes

- The fall detection system uses MediaPipe for pose estimation and scikit-learn Random Forest for classification
- All passwords in dummy data are simple for testing (change in production!)
- Camera feed requires a connected webcam or camera device
- System logs are viewable by admin users in the admin dashboard