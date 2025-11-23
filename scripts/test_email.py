#!/usr/bin/env python3
"""
Test script to send a real email alert
Use this to verify your SMTP configuration works
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alert_service import alert_service, send_fall_alerts
from db_manager import get_db_connection, close_db_connection

def test_email_configuration():
    """Test SMTP configuration"""
    print("=" * 70)
    print("📧 EMAIL ALERT TEST")
    print("=" * 70)
    print()
    
    print(f"Current mode: {alert_service.mode}")
    print()
    
    if alert_service.mode != 'smtp':
        print("❌ Not in SMTP mode!")
        print("   Run: python3 scripts/setup_email_alerts.sh")
        print("   Or set ALERT_MODE=smtp in .env file")
        return False
    
    print("✅ SMTP mode enabled")
    print(f"   Server: {alert_service.smtp_server}")
    print(f"   Port: {alert_service.smtp_port}")
    print(f"   From: {alert_service.smtp_from_email}")
    print()
    
    # Get a patient with assigned caretakers/doctors
    conn = get_db_connection()
    if not conn:
        print("❌ Cannot connect to database")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Find a patient with assigned caretakers or doctors
        cursor.execute("""
            SELECT DISTINCT u.id, u.name, u.email, u.role
            FROM users u
            WHERE u.role = 'patient'
            AND (
                EXISTS (
                    SELECT 1 FROM patient_caretaker pc 
                    WHERE pc.patient_id = u.id 
                    AND pc.is_active = 1
                    AND EXISTS (
                        SELECT 1 FROM users cu 
                        WHERE cu.id = pc.caretaker_id 
                        AND cu.email IS NOT NULL 
                        AND cu.email != ''
                    )
                )
                OR EXISTS (
                    SELECT 1 FROM patient_doctor pd 
                    WHERE pd.patient_id = u.id
                    AND EXISTS (
                        SELECT 1 FROM users du 
                        WHERE du.id = pd.doctor_id 
                        AND du.email IS NOT NULL 
                        AND du.email != ''
                    )
                )
            )
            LIMIT 1
        """)
        patient = cursor.fetchone()
        
        if not patient:
            print("❌ No patients with assigned caretakers/doctors found")
            print("   Please assign caretakers/doctors to patients first")
            return False
        
        patient_id = patient['id'] if isinstance(patient, dict) else patient[0]
        patient_name = patient['name'] if isinstance(patient, dict) else patient[1]
        patient_email = patient['email'] if isinstance(patient, dict) else patient[2]
        
        # Get assigned recipients
        cursor.execute("""
            SELECT u.name, u.email, u.role
            FROM users u
            INNER JOIN patient_caretaker pc ON u.id = pc.caretaker_id
            WHERE pc.patient_id = ? AND pc.is_active = 1 
            AND u.email IS NOT NULL AND u.email != ''
        """, (patient_id,))
        caretakers = cursor.fetchall()
        
        cursor.execute("""
            SELECT u.name, u.email, u.role
            FROM users u
            INNER JOIN patient_doctor pd ON u.id = pd.doctor_id
            WHERE pd.patient_id = ?
            AND u.email IS NOT NULL AND u.email != ''
        """, (patient_id,))
        doctors = cursor.fetchall()
        
        print(f"📧 Test Patient: {patient_name} (ID: {patient_id})")
        print()
        print("Recipients who will receive email:")
        for c in caretakers:
            name = c['name'] if isinstance(c, dict) else c[0]
            email = c['email'] if isinstance(c, dict) else c[1]
            print(f"  📧 {name} ({email}) - Caretaker")
        for d in doctors:
            name = d['name'] if isinstance(d, dict) else d[0]
            email = d['email'] if isinstance(d, dict) else d[1]
            print(f"  📧 {name} ({email}) - Doctor")
        print()
        
        # Ask for confirmation
        response = input("Send test email alert? (yes/no): ").lower()
        if response != 'yes':
            print("Cancelled.")
            return False
        
        print()
        print("📧 Sending test email alerts...")
        print()
        
        # Send test alert
        result = send_fall_alerts(
            patient_id=patient_id,
            patient_name=patient_name,
            severity="moderate",
            location="Test Location",
            fall_id=None
        )
        
        if result.get('sent'):
            emails_sent = result.get('emails_sent', 0)
            print(f"✅ Emails sent successfully!")
            print(f"   Total emails sent: {emails_sent}")
            print()
            print("📬 Check inboxes:")
            for c in caretakers:
                email = c['email'] if isinstance(c, dict) else c[1]
                print(f"   → {email}")
            for d in doctors:
                email = d['email'] if isinstance(d, dict) else d[1]
                print(f"   → {email}")
            print()
            print("💡 Note: If no emails received, check:")
            print("   1. Spam/junk folder")
            print("   2. SMTP credentials are correct")
            print("   3. Gmail app password is valid")
            return True
        else:
            print(f"❌ Email not sent: {result.get('reason', 'unknown')}")
            print()
            print("💡 Troubleshooting:")
            print("   1. Check SMTP credentials in .env file")
            print("   2. Verify Gmail app password is correct")
            print("   3. Check console for error messages")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        close_db_connection(conn)

if __name__ == "__main__":
    test_email_configuration()


