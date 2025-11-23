#!/usr/bin/env python3
"""
Alert Service for Fall Detection System
Handles email alerts to caregivers and doctors when falls are detected.

Supports:
- SMTP (production) - Gmail, Outlook, custom SMTP servers
- Mock mode (development/testing)
- Configurable alert rules based on severity
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from datetime import datetime

# Database imports
try:
    from db_manager import get_db_connection, close_db_connection
except ImportError:
    import sqlite3
    def get_db_connection():
        DB_PATH = os.environ.get("DB_PATH", "system_config.db")
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    def close_db_connection(conn):
        if conn:
            conn.close()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
ALERT_MODE = os.environ.get("ALERT_MODE", "mock")  # 'smtp' or 'mock'

# SMTP Configuration (for production)
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")  # Your email
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")  # Your email password or app password
SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", SMTP_USERNAME)  # From address
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "true").lower() == "true"

# Alert severity thresholds
ALERT_RULES = {
    'severe': {
        'email': True,
        'delay_seconds': 0,  # Immediate
        'recipients': ['caretaker', 'doctor', 'emergency_contact']  # Both caretakers and doctors for severe falls
    },
    'moderate': {
        'email': True,
        'delay_seconds': 30,  # 30 second delay
        'recipients': ['caretaker']  # Caretakers only for non-serious alerts
    },
    'mild': {
        'email': True,
        'delay_seconds': 60,  # 1 minute delay
        'recipients': ['caretaker']  # Caretakers only for non-serious alerts
    }
}


class AlertService:
    """Service for sending email alerts"""
    
    def __init__(self):
        self.mode = ALERT_MODE
        self.smtp_server = None
        self.smtp_port = None
        self.smtp_username = None
        self.smtp_password = None
        self.smtp_from_email = None
        
        if self.mode == 'smtp':
            if not all([SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD]):
                logger.warning("SMTP credentials not configured. Falling back to mock mode.")
                self.mode = 'mock'
            else:
                self.smtp_server = SMTP_SERVER
                self.smtp_port = SMTP_PORT
                self.smtp_username = SMTP_USERNAME
                self.smtp_password = SMTP_PASSWORD
                self.smtp_from_email = SMTP_FROM_EMAIL or SMTP_USERNAME
                logger.info(f"✅ Email service configured (SMTP: {SMTP_SERVER}:{SMTP_PORT})")
        else:
            self.mode = 'mock'
            logger.info("📧 Alert service running in MOCK mode (no actual emails sent)")
    
    def get_recipients(self, patient_id: str, severity: str) -> List[Dict]:
        """Get list of recipients (caretakers, doctors, emergency contacts) for a patient"""
        recipients = []
        conn = get_db_connection()
        
        if not conn:
            logger.error("Cannot get database connection")
            return recipients
        
        try:
            cursor = conn.cursor()
            rules = ALERT_RULES.get(severity, ALERT_RULES['mild'])
            
            # Get caretakers
            if 'caretaker' in rules['recipients']:
                cursor.execute("""
                    SELECT u.id, u.name, u.phone, u.email, 'caretaker' as role
                    FROM users u
                    INNER JOIN patient_caretaker pc ON u.id = pc.caretaker_id
                    WHERE pc.patient_id = ? AND pc.is_active = 1 AND u.email IS NOT NULL AND u.email != ''
                """, (patient_id,))
                for row in cursor.fetchall():
                    recipients.append({
                        'id': row['id'] if isinstance(row, dict) else row[0],
                        'name': row['name'] if isinstance(row, dict) else row[1],
                        'phone': row['phone'] if isinstance(row, dict) else row[2],
                        'email': row['email'] if isinstance(row, dict) else row[3],
                        'role': 'caretaker'
                    })
            
            # Get doctors
            if 'doctor' in rules['recipients']:
                cursor.execute("""
                    SELECT u.id, u.name, u.phone, u.email, 'doctor' as role
                    FROM users u
                    INNER JOIN patient_doctor pd ON u.id = pd.doctor_id
                    WHERE pd.patient_id = ? AND u.email IS NOT NULL AND u.email != ''
                """, (patient_id,))
                for row in cursor.fetchall():
                    recipients.append({
                        'id': row['id'] if isinstance(row, dict) else row[0],
                        'name': row['name'] if isinstance(row, dict) else row[1],
                        'phone': row['phone'] if isinstance(row, dict) else row[2],
                        'email': row['email'] if isinstance(row, dict) else row[3],
                        'role': 'doctor'
                    })
            
            # Get patient's own email (emergency contact)
            if 'emergency_contact' in rules['recipients']:
                cursor.execute("""
                    SELECT id, name, phone, email, 'patient' as role
                    FROM users
                    WHERE id = ? AND email IS NOT NULL AND email != ''
                """, (patient_id,))
                row = cursor.fetchone()
                if row:
                    recipients.append({
                        'id': row['id'] if isinstance(row, dict) else row[0],
                        'name': row['name'] if isinstance(row, dict) else row[1],
                        'phone': row['phone'] if isinstance(row, dict) else row[2],
                        'email': row['email'] if isinstance(row, dict) else row[3],
                        'role': 'patient'
                    })
            
        except Exception as e:
            logger.error(f"Database error getting recipients: {e}")
        finally:
            close_db_connection(conn)
        
        return recipients
    
    def send_email(self, to_email: str, subject: str, body_html: str, body_text: str = None) -> bool:
        """Send email message"""
        if not to_email or to_email == "N/A" or "@" not in to_email:
            logger.warning(f"Cannot send email: invalid email address: {to_email}")
            return False
        
        if self.mode == 'mock':
            logger.info(f"📧 [MOCK EMAIL] To: {to_email}")
            logger.info(f"   Subject: {subject}")
            logger.info(f"   Body: {body_text or body_html[:200]}...")
            return True
        
        # SMTP Email
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_from_email
            msg['To'] = to_email
            
            # Add both plain text and HTML versions
            if body_text:
                part1 = MIMEText(body_text, 'plain')
                msg.attach(part1)
            
            part2 = MIMEText(body_html, 'html')
            msg.attach(part2)
            
            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if SMTP_USE_TLS:
                    server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"✅ Email sent to {to_email}")
            return True
        except smtplib.SMTPException as e:
            logger.error(f"❌ Failed to send email to {to_email}: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error sending email: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_fall_alert(self, patient_id: str, patient_name: str, severity: str, 
                       location: Optional[str] = None, fall_id: Optional[int] = None) -> Dict:
        """Send email alerts for a detected fall"""
        rules = ALERT_RULES.get(severity, ALERT_RULES['mild'])
        recipients = self.get_recipients(patient_id, severity)
        
        if not recipients:
            logger.warning(f"No recipients found for patient {patient_id}")
            return {'sent': False, 'reason': 'no_recipients', 'emails_sent': 0}
        
        results = {
            'sent': True,
            'emails_sent': 0,
            'recipients': []
        }
        
        # Create alert message
        severity_emoji = {'severe': '🚨', 'moderate': '⚠️', 'mild': 'ℹ️'}.get(severity, '⚠️')
        severity_color = {'severe': '#dc2626', 'moderate': '#f59e0b', 'mild': '#3b82f6'}.get(severity, '#6b7280')
        location_text = f" at {location}" if location else ""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        time_12h = datetime.now().strftime('%I:%M %p')
        
        # HTML email body
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: {severity_color}; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; border-top: none; }}
                .alert-box {{ background-color: white; padding: 15px; border-left: 4px solid {severity_color}; margin: 15px 0; }}
                .info-row {{ margin: 10px 0; }}
                .label {{ font-weight: bold; color: #6b7280; }}
                .value {{ color: #111827; }}
                .button {{ display: inline-block; padding: 12px 24px; background-color: {severity_color}; color: white; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
                .footer {{ text-align: center; margin-top: 20px; padding-top: 20px; border-top: 1px solid #e5e7eb; color: #6b7280; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{severity_emoji} Fall Alert - {severity.upper()}</h1>
                </div>
                <div class="content">
                    <div class="alert-box">
                        <p style="font-size: 18px; margin: 0 0 15px 0;">
                            A fall has been detected for <strong>{patient_name}</strong>
                        </p>
                    </div>
                    
                    <div class="info-row">
                        <span class="label">Patient:</span>
                        <span class="value">{patient_name}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Severity:</span>
                        <span class="value" style="color: {severity_color}; font-weight: bold;">{severity.upper()}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Time:</span>
                        <span class="value">{timestamp}</span>
                    </div>
                    <div class="info-row">
                        <span class="label">Location:</span>
                        <span class="value">{location or 'Unknown'}</span>
                    </div>
                    {f'<div class="info-row"><span class="label">Fall ID:</span><span class="value">#{fall_id}</span></div>' if fall_id else ''}
                    
                    <p style="margin-top: 20px;">
                        Please check the CARE system dashboard immediately for more details and to review the fall incident.
                    </p>
                    
                    <a href="{os.environ.get('BASE_URL', 'http://localhost:5000')}/dashboard" class="button">
                        View Dashboard
                    </a>
                </div>
                <div class="footer">
                    <p>This is an automated alert from the CARE Fall Detection System.</p>
                    <p>Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        text_body = f"""
{severity_emoji} FALL ALERT - {severity.upper()}

A fall has been detected for {patient_name}{location_text}.

Details:
- Patient: {patient_name}
- Severity: {severity.upper()}
- Time: {timestamp}
- Location: {location or 'Unknown'}
{f'- Fall ID: #{fall_id}' if fall_id else ''}

Please check the CARE system dashboard immediately for more details.

Dashboard: {os.environ.get('BASE_URL', 'http://localhost:5000')}/dashboard

---
This is an automated alert from the CARE Fall Detection System.
Please do not reply to this email.
        """
        
        # Send emails to each recipient
        for recipient in recipients:
            recipient_result = {'recipient': recipient, 'email': False}
            
            # Send email
            if rules['email']:
                if self.send_email(
                    recipient['email'],
                    f"{severity_emoji} Fall Alert - {severity.upper()} for {patient_name}",
                    html_body,
                    text_body
                ):
                    results['emails_sent'] += 1
                    recipient_result['email'] = True
                    # Log alert attempt
                    if fall_id:
                        self.log_alert_attempt(fall_id, recipient['id'], 'email', True)
            
            results['recipients'].append(recipient_result)
        
        logger.info(f"✅ Alerts sent: {results['emails_sent']} emails")
        return results
    
    def log_alert_attempt(self, fall_id: int, recipient_id: str, alert_type: str, 
                         success: bool, details: str = None):
        """Log alert attempt to database"""
        conn = get_db_connection()
        if not conn:
            return
        
        try:
            cursor = conn.cursor()
            # Ensure table exists
            cursor.execute("""
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
            conn.commit()
            
            cursor.execute("""
                INSERT INTO alert_logs (fall_id, recipient_id, alert_type, success, details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (fall_id, recipient_id, alert_type, 1 if success else 0, details,
                  datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
        except Exception as e:
            logger.error(f"Error logging alert: {e}")
            if conn:
                conn.rollback()
        finally:
            close_db_connection(conn)


# Global instance
alert_service = AlertService()


def send_fall_alerts(patient_id: str, patient_name: str, severity: str, 
                     location: Optional[str] = None, fall_id: Optional[int] = None) -> Dict:
    """Convenience function to send fall alerts"""
    return alert_service.send_fall_alert(patient_id, patient_name, severity, location, fall_id)
