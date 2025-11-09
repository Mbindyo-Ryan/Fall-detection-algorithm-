#!/usr/bin/env python3
"""
Generate dummy data for testing the fall detection system
Creates users, relationships, falls, and reviews
"""

import sqlite3
import random
from datetime import datetime, timedelta
import json
import os
import sys

# Get the parent directory (project root)
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
DB_PATH = os.path.join(project_root, "system_config.db")

# Import password hashing
sys.path.insert(0, project_root)
try:
    from werkzeug.security import generate_password_hash
except ImportError:
    print("⚠️  werkzeug not found. Install with: pip install werkzeug")
    sys.exit(1)

# Dummy data templates
PATIENT_NAMES = [
    "John Smith", "Mary Johnson", "Robert Williams", "Patricia Brown",
    "Michael Jones", "Jennifer Garcia", "William Miller", "Linda Davis",
    "David Rodriguez", "Elizabeth Martinez", "Richard Anderson", "Susan Taylor"
]

DOCTOR_NAMES = [
    "Dr. Sarah Thompson", "Dr. James Wilson", "Dr. Emily Chen", "Dr. Michael Brown"
]

CARETAKER_NAMES = [
    "Alice Cooper", "Bob Martin", "Carol White", "Daniel Lee"
]

LOCATIONS = [
    "Living Room", "Bedroom", "Kitchen", "Bathroom", "Hallway", 
    "Garden", "Stairs", "Front Door"
]

RECOMMENDATIONS = [
    ["xray", "physiotherapy"],
    ["consultation", "medication_review"],
    ["xray"],
    ["physiotherapy", "follow_up"],
    ["consultation"],
    ["xray", "consultation", "physiotherapy"]
]

REMARKS_TEMPLATES = [
    "Patient fell with significant impact. Recommend immediate X-ray to rule out fractures.",
    "Moderate fall, patient appears stable. Suggest physiotherapy for mobility assessment.",
    "Minor fall incident. Monitor for any delayed symptoms. Follow-up recommended.",
    "Fall occurred during transition. Consider mobility aids and home safety assessment.",
    "Patient experienced fall with potential head impact. Recommend consultation with neurologist.",
    "Fall severity moderate. Patient should be evaluated for balance and coordination issues."
]


def generate_dummy_data():
    """Generate comprehensive dummy data"""
    print(f"📂 Database path: {DB_PATH}")
    print(f"📂 Database exists: {os.path.exists(DB_PATH)}")
    
    if not os.path.exists(DB_PATH):
        print(f"⚠️  Database not found at {DB_PATH}")
        print("   Creating database...")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    print("🔄 Generating dummy data...")
    
    # Clear existing data (optional - comment out if you want to keep existing)
    # c.execute("DELETE FROM fall_reviews")
    # c.execute("DELETE FROM fall_files")
    # c.execute("DELETE FROM file_comments")
    # c.execute("DELETE FROM falls")
    # c.execute("DELETE FROM patient_caretaker")
    # c.execute("DELETE FROM patient_doctor")
    # c.execute("DELETE FROM users WHERE role != 'patient'")
    
    # Create admin user
    admin_id = "admin_1"
    admin_password = generate_password_hash("admin123", method='pbkdf2:sha256')
    try:
        c.execute("""
            INSERT OR REPLACE INTO users (id, name, email, phone, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?, 'admin', ?)
        """, (admin_id, "System Admin", "admin@care.com", "+1555000", admin_password, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        print(f"  ✅ Created admin: System Admin (email: admin@care.com, password: admin123)")
    except Exception as e:
        print(f"  ⚠️  Admin creation: {e}")
    
    # Create doctors
    doctors = []
    for i, name in enumerate(DOCTOR_NAMES):
        doctor_id = f"doctor_{i+1}"
        email = name.lower().replace(" ", ".").replace("dr.", "") + "@care.com"
        phone = f"+1555{1000+i}"
        password = generate_password_hash("doctor123", method='pbkdf2:sha256')
        
        try:
            c.execute("""
                INSERT OR REPLACE INTO users (id, name, email, phone, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, ?, 'doctor', ?)
            """, (doctor_id, name, email, phone, password, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            doctors.append(doctor_id)
            print(f"  ✅ Created doctor: {name} (email: {email}, password: doctor123)")
        except Exception as e:
            print(f"  ⚠️  Doctor creation error: {e}")
            doctors.append(doctor_id)
    
    # Create caretakers
    caretakers = []
    for i, name in enumerate(CARETAKER_NAMES):
        caretaker_id = f"caretaker_{i+1}"
        email = name.lower().replace(" ", ".") + "@care.com"
        phone = f"+1555{2000+i}"
        password = generate_password_hash("caretaker123", method='pbkdf2:sha256')
        
        try:
            c.execute("""
                INSERT OR REPLACE INTO users (id, name, email, phone, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, ?, 'caretaker', ?)
            """, (caretaker_id, name, email, phone, password, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            caretakers.append(caretaker_id)
            print(f"  ✅ Created caretaker: {name} (email: {email}, password: caretaker123)")
        except Exception as e:
            print(f"  ⚠️  Caretaker creation error: {e}")
            caretakers.append(caretaker_id)
    
    # Create patients
    patients = []
    for i, name in enumerate(PATIENT_NAMES):
        patient_id = f"patient_{i+1}"
        email = name.lower().replace(" ", ".") + "@patient.com"
        phone = f"+1555{3000+i}"
        password = generate_password_hash("patient123", method='pbkdf2:sha256')
        
        try:
            c.execute("""
                INSERT OR REPLACE INTO users (id, name, email, phone, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, ?, 'patient', ?)
            """, (patient_id, name, email, phone, password, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            patients.append(patient_id)
            print(f"  ✅ Created patient: {name} (email: {email}, password: patient123)")
        except Exception as e:
            print(f"  ⚠️  Patient creation error: {e}")
            patients.append(patient_id)
    
    # Assign patients to doctors and caretakers
    print("\n📋 Assigning relationships...")
    
    # Create one caretaker with 4-5 patients
    main_caretaker = caretakers[0]
    main_caretaker_patients = patients[:5]  # First 5 patients
    for patient_id in main_caretaker_patients:
        c.execute("""
            INSERT OR REPLACE INTO patient_caretaker (patient_id, caretaker_id, is_active, assigned_at)
            VALUES (?, ?, 1, ?)
        """, (patient_id, main_caretaker, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    print(f"  ✅ Assigned {len(main_caretaker_patients)} patients to caretaker {main_caretaker}")
    
    # Assign remaining patients to other caretakers
    for i, patient_id in enumerate(patients[5:], start=5):
        caretaker_id = caretakers[i % len(caretakers)]
        c.execute("""
            INSERT OR REPLACE INTO patient_caretaker (patient_id, caretaker_id, is_active, assigned_at)
            VALUES (?, ?, 1, ?)
        """, (patient_id, caretaker_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    # Assign patients to doctors (distribute evenly)
    for i, patient_id in enumerate(patients):
        doctor_id = doctors[i % len(doctors)]
        c.execute("""
            INSERT OR REPLACE INTO patient_doctor (patient_id, doctor_id, is_active)
            VALUES (?, ?, 1)
        """, (patient_id, doctor_id))
    
    print(f"  ✅ Assigned {len(patients)} patients to doctors and caretakers")
    
    # Generate falls
    print("\n⚠️  Generating fall incidents...")
    fall_ids = []
    severities = ['mild', 'moderate', 'severe']
    statuses = ['SUSPECTED_FALL', 'CONFIRMED_FALL', 'FALSE_ALARM']
    
    # Create one patient with several falls (patient_1)
    test_patient = patients[0]
    print(f"  📍 Creating multiple falls for test patient: {test_patient}")
    for i in range(8):  # 8 falls for test patient
        severity = random.choice(severities)
        status = random.choice(['CONFIRMED_FALL', 'SUSPECTED_FALL'])
        location = random.choice(LOCATIONS)
        days_ago = random.randint(0, 14)
        hours_ago = random.randint(0, 23)
        timestamp = (datetime.now() - timedelta(days=days_ago, hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")
        details = f"Fall detected: {severity} severity, {location}"
        
        c.execute("""
            INSERT INTO falls (user_id, timestamp, status, details, severity, location, alert_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (test_patient, timestamp, status, details, severity, location, random.randint(0, 1)))
        fall_ids.append(c.lastrowid)
    
    # Generate falls for other patients (distribute among doctors' patients)
    for i in range(25):  # 25 more falls
        # Distribute falls among different patients
        patient_id = random.choice(patients)
        severity = random.choice(severities)
        status = random.choice(statuses)
        location = random.choice(LOCATIONS)
        
        # Generate timestamp within last 30 days
        days_ago = random.randint(0, 30)
        hours_ago = random.randint(0, 23)
        timestamp = (datetime.now() - timedelta(days=days_ago, hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")
        
        details = f"Fall detected: {severity} severity, {location}"
        
        c.execute("""
            INSERT INTO falls (user_id, timestamp, status, details, severity, location, alert_sent)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (patient_id, timestamp, status, details, severity, location, random.randint(0, 1)))
        
        fall_id = c.lastrowid
        fall_ids.append(fall_id)
    
    print(f"  ✅ Generated {len(fall_ids)} fall incidents (8 for test patient {test_patient})")
    
    # Generate doctor reviews
    print("\n📝 Generating doctor reviews...")
    review_ids = []
    
    for fall_id in fall_ids[:20]:  # Review 20 falls
        # Get patient's doctor
        c.execute("""
            SELECT doctor_id FROM patient_doctor pd
            INNER JOIN falls f ON pd.patient_id = f.user_id
            WHERE f.id = ? AND pd.is_active = 1
            LIMIT 1
        """, (fall_id,))
        result = c.fetchone()
        
        if result:
            doctor_id = result['doctor_id']
            recommendations = random.choice(RECOMMENDATIONS)
            remarks = random.choice(REMARKS_TEMPLATES)
            
            # Review date is after fall date
            c.execute("SELECT timestamp FROM falls WHERE id = ?", (fall_id,))
            fall_time = datetime.strptime(c.fetchone()['timestamp'], "%Y-%m-%d %H:%M:%S")
            review_date = (fall_time + timedelta(hours=random.randint(1, 48))).strftime("%Y-%m-%d %H:%M:%S")
            
            status = random.choice(['pending', 'reviewed', 'completed'])
            
            c.execute("""
                INSERT INTO fall_reviews (fall_id, doctor_id, review_date, remarks, 
                                       recommendations, recommended_actions, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (fall_id, doctor_id, review_date, remarks, 
                  f"Recommended: {', '.join(recommendations)}",
                  json.dumps(recommendations), status))
            
            review_id = c.lastrowid
            review_ids.append(review_id)
    
    print(f"  ✅ Generated {len(review_ids)} doctor reviews")
    
    # Generate some file uploads (X-rays, scans)
    print("\n📎 Generating file uploads...")
    file_types = ['xray', 'scan', 'report', 'other']
    
    for i in range(10):  # 10 file uploads
        fall_id = random.choice(fall_ids)
        review_id = random.choice(review_ids) if review_ids else None
        
        # Get patient for this fall
        c.execute("SELECT user_id FROM falls WHERE id = ?", (fall_id,))
        patient_id = c.fetchone()['user_id']
        
        file_type = random.choice(file_types)
        file_name = f"{file_type}_{fall_id}_{i+1}.pdf"
        file_path = f"uploads/{file_name}"
        
        # Create uploads directory if it doesn't exist
        os.makedirs("../uploads", exist_ok=True)
        
        c.execute("""
            INSERT INTO fall_files (fall_id, review_id, uploaded_by, file_name, 
                                  file_path, file_type, file_size)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (fall_id, review_id, patient_id, file_name, file_path, file_type, random.randint(100000, 5000000)))
        
        # Some files have doctor comments
        if random.random() > 0.5 and review_id:
            c.execute("SELECT doctor_id FROM fall_reviews WHERE id = ?", (review_id,))
            doctor_id = c.fetchone()['doctor_id']
            
            comments = [
                "X-ray shows no fractures. Patient cleared for normal activity.",
                "Scan indicates minor soft tissue injury. Recommend rest and physiotherapy.",
                "Report reviewed. Patient should follow up in 2 weeks.",
                "No abnormalities detected. Continue monitoring."
            ]
            
            c.execute("""
                INSERT INTO file_comments (file_id, doctor_id, comment)
                VALUES (?, ?, ?)
            """, (c.lastrowid, doctor_id, random.choice(comments)))
    
    print(f"  ✅ Generated file uploads with comments")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Dummy data generation complete!")
    print(f"   - 1 admin (admin@care.com / admin123)")
    print(f"   - {len(doctors)} doctors (all use password: doctor123)")
    print(f"   - {len(caretakers)} caretakers (all use password: caretaker123)")
    print(f"   - {len(patients)} patients (all use password: patient123)")
    print(f"   - {len(fall_ids)} falls (8 for test patient: {patients[0]})")
    print(f"   - {len(review_ids)} reviews")
    print(f"   - File uploads and comments")
    print(f"\n📋 Test Accounts:")
    print(f"   - Admin: admin@care.com / admin123")
    print(f"   - Test Patient (with multiple falls): {patients[0]} / patient123")
    print(f"   - Caretaker with 5 patients: {caretakers[0]} / caretaker123")
    print(f"   - Doctor: {doctors[0]} / doctor123")
    print("\n💡 You can now test the review system!")


if __name__ == "__main__":
    generate_dummy_data()

