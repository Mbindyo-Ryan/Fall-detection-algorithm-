#!/usr/bin/env python3
"""
Demo script for email alert functionality
Perfect for presentations and demonstrations
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alert_service import alert_service, send_fall_alerts
from datetime import datetime

def print_banner():
    print("=" * 70)
    print("📧 EMAIL ALERT SYSTEM DEMONSTRATION")
    print("=" * 70)
    print()

def demo_mock_mode():
    """Demonstrate mock mode (no actual emails sent)"""
    print("🔹 MOCK MODE DEMONSTRATION")
    print("-" * 70)
    print("In mock mode, emails are logged to console instead of being sent.")
    print("This is perfect for development and demonstrations.")
    print()
    
    print("📧 Simulating fall alerts...")
    print()
    
    # Simulate different severity levels
    severities = [
        ('severe', '🚨'),
        ('moderate', '⚠️'),
        ('mild', 'ℹ️')
    ]
    
    for severity, emoji in severities:
        print(f"\n{emoji} {severity.upper()} FALL ALERT")
        print("-" * 70)
        
        result = send_fall_alerts(
            patient_id="demo_patient_1",
            patient_name="John Doe",
            severity=severity,
            location="Living Room",
            fall_id=999
        )
        
        if result.get('sent'):
            print(f"✅ Alert sent successfully!")
            print(f"   Emails sent: {result.get('emails_sent', 0)}")
            print(f"   Recipients: {len(result.get('recipients', []))}")
        else:
            print(f"⚠️  Alert not sent: {result.get('reason', 'unknown')}")
            print("   (This is normal if no recipients are configured)")
        
        print()
    
    print("=" * 70)
    print("✅ Mock mode demonstration complete!")
    print("=" * 70)

def demo_smtp_mode():
    """Demonstrate SMTP mode (actual emails sent)"""
    print("🔹 SMTP MODE DEMONSTRATION")
    print("-" * 70)
    print("In SMTP mode, actual emails are sent via configured SMTP server.")
    print()
    
    if alert_service.mode != 'smtp':
        print("⚠️  Currently in MOCK mode.")
        print("   To test SMTP mode, set environment variables:")
        print("   export ALERT_MODE=smtp")
        print("   export SMTP_SERVER=smtp.gmail.com")
        print("   export SMTP_USERNAME=your-email@gmail.com")
        print("   export SMTP_PASSWORD=your-app-password")
        print()
        return
    
    print("📧 Sending test email...")
    print()
    
    result = send_fall_alerts(
        patient_id="demo_patient_1",
        patient_name="Demo Patient",
        severity="moderate",
        location="Test Location",
        fall_id=999
    )
    
    if result.get('sent'):
        print(f"✅ Email sent successfully!")
        print(f"   Emails sent: {result.get('emails_sent', 0)}")
        print(f"   Check your inbox!")
    else:
        print(f"❌ Email not sent: {result.get('reason', 'unknown')}")

def show_email_preview():
    """Show what the email looks like"""
    print("🔹 EMAIL PREVIEW")
    print("-" * 70)
    print("Here's what recipients will receive:")
    print()
    
    severity = "severe"
    patient_name = "John Doe"
    location = "Living Room"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print("📧 EMAIL SUBJECT:")
    print(f"   🚨 Fall Alert - SEVERE for {patient_name}")
    print()
    
    print("📧 EMAIL BODY (HTML):")
    print("   - Color-coded header (red for severe, orange for moderate, blue for mild)")
    print("   - Patient name and details")
    print("   - Severity level with color coding")
    print("   - Time and location")
    print("   - Fall ID")
    print("   - Button link to dashboard")
    print()
    
    print("📧 EMAIL BODY (Plain Text):")
    print(f"   🚨 FALL ALERT - SEVERE")
    print(f"   ")
    print(f"   A fall has been detected for {patient_name} at {location}.")
    print(f"   ")
    print(f"   Details:")
    print(f"   - Patient: {patient_name}")
    print(f"   - Severity: SEVERE")
    print(f"   - Time: {timestamp}")
    print(f"   - Location: {location}")
    print(f"   - Fall ID: #999")
    print(f"   ")
    print(f"   Please check the CARE system dashboard immediately.")
    print()
    
    print("=" * 70)

def show_configuration():
    """Show current configuration"""
    print("🔹 CURRENT CONFIGURATION")
    print("-" * 70)
    print(f"Mode: {alert_service.mode.upper()}")
    print()
    
    if alert_service.mode == 'smtp':
        print("SMTP Settings:")
        print(f"   Server: {alert_service.smtp_server}")
        print(f"   Port: {alert_service.smtp_port}")
        print(f"   From: {alert_service.smtp_from_email}")
        print(f"   TLS: {SMTP_USE_TLS}")
    else:
        print("Mock Mode: No actual emails will be sent")
        print("All email activity will be logged to console")
    
    print()
    print("Alert Rules:")
    from alert_service import ALERT_RULES
    for severity, rules in ALERT_RULES.items():
        print(f"   {severity.upper()}:")
        print(f"      - Email: {rules['email']}")
        print(f"      - Delay: {rules['delay_seconds']} seconds")
        print(f"      - Recipients: {', '.join(rules['recipients'])}")
    
    print()
    print("=" * 70)

def main():
    print_banner()
    
    # Show configuration
    show_configuration()
    print()
    
    # Show email preview
    show_email_preview()
    print()
    
    # Demo based on mode
    if alert_service.mode == 'mock':
        demo_mock_mode()
    else:
        demo_smtp_mode()
    
    print()
    print("💡 TIPS FOR DEMONSTRATION:")
    print("   1. Run this script to show mock mode in action")
    print("   2. Show the console output (emails logged)")
    print("   3. Explain that in production, these would be real emails")
    print("   4. Show the email preview above")
    print("   5. Optionally set up SMTP to send a real test email")
    print()

if __name__ == "__main__":
    main()


