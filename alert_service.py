#!/usr/bin/env python3
"""
Alert Service for Fall Detection System
Handles SMS and phone call alerts to caregivers and doctors when falls are detected.

Supports:
- Twilio (production)
- Mock mode (development/testing)
- Configurable alert rules based on severity
"""

import os
import sqlite3
import logging
from typing import List, Dict, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Twilio (optional)
try:
    from twilio.rest import Client as TwilioClient
    from twilio.base.exceptions import TwilioException
    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("Twilio not installed. Install with: pip install twilio")

# Configuration
DB_PATH = os.environ.get("DB_PATH", "system_config.db")
ALERT_MODE = os.environ.get("ALERT_MODE", "mock")  # 'twilio' or 'mock'
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")  # Your Twilio number

# Alert severity thresholds
ALERT_RULES = {
    'severe': {
        'sms': True,
        'call': True,
        'delay_seconds': 0,  # Immediate
        'recipients': ['caretaker', 'doctor', 'emergency_contact']
    },
    'moderate': {
        'sms': True,
        'call': False,
        'delay_seconds': 30,  # 30 second delay
        'recipients': ['caretaker', 'doctor']
    },
    'mild': {
        'sms': True,
        'call': False,
        'delay_seconds': 60,  # 1 minute delay
        'recipients': ['caretaker']
    }
}


class AlertService:
    """Service for sending SMS and phone call alerts"""
    
    def __init__(self):
        self.mode = ALERT_MODE
        self.twilio_client = None
        
        if self.mode == 'twilio' and TWILIO_AVAILABLE:
            if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
                logger.warning("Twilio credentials not configured. Falling back to mock mode.")
                self.mode = 'mock'
            else:
                try:
                    self.twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                    logger.info("✅ Twilio client initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize Twilio: {e}. Using mock mode.")
                    self.mode = 'mock'
        else:
            self.mode = 'mock'
            logger.info("📱 Alert service running in MOCK mode (no actual SMS/calls sent)")
    
    def get_recipients(self, patient_id: str, severity: str) -> List[Dict]:
        """Get list of recipients (caretakers, doctors, emergency contacts) for a patient"""
        recipients = []
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        try:
            c = conn.cursor()
            rules = ALERT_RULES.get(severity, ALERT_RULES['mild'])
            
            # Get caretakers
            if 'caretaker' in rules['recipients']:
                c.execute("""
                    SELECT u.id, u.name, u.phone, u.email, 'caretaker' as role
                    FROM users u
                    INNER JOIN patient_caretaker pc ON u.id = pc.caretaker_id
                    WHERE pc.patient_id = ? AND pc.is_active = 1 AND u.phone IS NOT NULL
                """, (patient_id,))
                for row in c.fetchall():
                    recipients.append({
                        'id': row['id'],
                        'name': row['name'],
                        'phone': row['phone'],
                        'email': row['email'],
                        'role': 'caretaker'
                    })
            
            # Get doctors
            if 'doctor' in rules['recipients']:
                c.execute("""
                    SELECT u.id, u.name, u.phone, u.email, 'doctor' as role
                    FROM users u
                    INNER JOIN patient_doctor pd ON u.id = pd.doctor_id
                    WHERE pd.patient_id = ? AND u.phone IS NOT NULL
                """, (patient_id,))
                for row in c.fetchall():
                    recipients.append({
                        'id': row['id'],
                        'name': row['name'],
                        'phone': row['phone'],
                        'email': row['email'],
                        'role': 'doctor'
                    })
            
            # Get patient's own phone (emergency contact)
            if 'emergency_contact' in rules['recipients']:
                c.execute("""
                    SELECT id, name, phone, email, 'patient' as role
                    FROM users
                    WHERE id = ? AND phone IS NOT NULL
                """, (patient_id,))
                row = c.fetchone()
                if row:
                    recipients.append({
                        'id': row['id'],
                        'name': row['name'],
                        'phone': row['phone'],
                        'email': row['email'],
                        'role': 'patient'
                    })
            
        except sqlite3.Error as e:
            logger.error(f"Database error getting recipients: {e}")
        finally:
            conn.close()
        
        return recipients
    
    def send_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS message"""
        if not phone_number or phone_number == "N/A":
            logger.warning(f"Cannot send SMS: invalid phone number")
            return False
        
        if self.mode == 'mock':
            logger.info(f"📱 [MOCK SMS] To: {phone_number}")
            logger.info(f"   Message: {message}")
            return True
        
        # Twilio SMS
        try:
            message_obj = self.twilio_client.messages.create(
                body=message,
                from_=TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            logger.info(f"✅ SMS sent to {phone_number}: {message_obj.sid}")
            return True
        except TwilioException as e:
            logger.error(f"❌ Failed to send SMS to {phone_number}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error sending SMS: {e}")
            return False
    
    def make_call(self, phone_number: str, message: str, fall_id: Optional[int] = None) -> bool:
        """Make phone call with text-to-speech"""
        if not phone_number or phone_number == "N/A":
            logger.warning(f"Cannot make call: invalid phone number")
            return False
        
        if self.mode == 'mock':
            logger.info(f"📞 [MOCK CALL] To: {phone_number}")
            logger.info(f"   Message: {message}")
            return True
        
        # Twilio Call with TTS
        try:
            # Create TwiML for the call
            twiml_url = f"{os.environ.get('BASE_URL', 'http://localhost:5000')}/api/alerts/call/{fall_id}/twiml"
            
            call = self.twilio_client.calls.create(
                twiml=f'<Response><Say voice="alice">{message}</Say><Pause length="2"/><Say voice="alice">Please check the CARE system dashboard for details.</Say></Response>',
                from_=TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            logger.info(f"✅ Call initiated to {phone_number}: {call.sid}")
            return True
        except TwilioException as e:
            logger.error(f"❌ Failed to call {phone_number}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error making call: {e}")
            return False
    
    def send_fall_alert(self, patient_id: str, patient_name: str, severity: str, 
                       location: Optional[str] = None, fall_id: Optional[int] = None) -> Dict:
        """Send alerts for a detected fall"""
        rules = ALERT_RULES.get(severity, ALERT_RULES['mild'])
        recipients = self.get_recipients(patient_id, severity)
        
        if not recipients:
            logger.warning(f"No recipients found for patient {patient_id}")
            return {'sent': False, 'reason': 'no_recipients'}
        
        results = {
            'sent': True,
            'sms_sent': 0,
            'calls_made': 0,
            'recipients': []
        }
        
        # Create alert message
        severity_emoji = {'severe': '🚨', 'moderate': '⚠️', 'mild': 'ℹ️'}.get(severity, '⚠️')
        location_text = f" at {location}" if location else ""
        
        sms_message = (
            f"{severity_emoji} FALL ALERT - {severity.upper()}\n\n"
            f"Patient: {patient_name}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Location: {location or 'Unknown'}\n\n"
            f"Please check the CARE system dashboard immediately."
        )
        
        call_message = (
            f"Fall alert. {severity} severity fall detected for patient {patient_name}"
            f"{location_text}. "
            f"Time: {datetime.now().strftime('%I:%M %p')}. "
            f"Please check the CARE system dashboard immediately."
        )
        
        # Send alerts to each recipient
        for recipient in recipients:
            recipient_result = {'recipient': recipient, 'sms': False, 'call': False}
            
            # Send SMS
            if rules['sms']:
                if self.send_sms(recipient['phone'], sms_message):
                    results['sms_sent'] += 1
                    recipient_result['sms'] = True
            
            # Make call (with delay if specified)
            if rules['call']:
                if self.make_call(recipient['phone'], call_message, fall_id):
                    results['calls_made'] += 1
                    recipient_result['call'] = True
            
            results['recipients'].append(recipient_result)
        
        logger.info(f"✅ Alerts sent: {results['sms_sent']} SMS, {results['calls_made']} calls")
        return results
    
    def log_alert_attempt(self, fall_id: int, recipient_id: str, alert_type: str, 
                         success: bool, details: str = None):
        """Log alert attempt to database"""
        conn = sqlite3.connect(DB_PATH)
        try:
            c = conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS alert_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fall_id INTEGER,
                    recipient_id TEXT,
                    alert_type TEXT,
                    success INTEGER,
                    details TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (fall_id) REFERENCES falls (id)
                )
            """)
            c.execute("""
                INSERT INTO alert_logs (fall_id, recipient_id, alert_type, success, details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (fall_id, recipient_id, alert_type, 1 if success else 0, details,
                  datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error logging alert: {e}")
        finally:
            conn.close()


# Global instance
alert_service = AlertService()


def send_fall_alerts(patient_id: str, patient_name: str, severity: str, 
                     location: Optional[str] = None, fall_id: Optional[int] = None) -> Dict:
    """Convenience function to send fall alerts"""
    return alert_service.send_fall_alert(patient_id, patient_name, severity, location, fall_id)

