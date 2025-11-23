#!/usr/bin/env python3
"""
Interactive setup script for email alerts (Gmail)
This is easier to run than the bash script
"""

import os
import sys

def setup_email_alerts():
    """Interactive email alert setup"""
    print("=" * 70)
    print("📧 Email Alert Setup (Gmail)")
    print("=" * 70)
    print()
    
    print("To set up email alerts, you need:")
    print("1. A Gmail account")
    print("2. An App Password (not your regular password)")
    print()
    print("📝 Steps to get Gmail App Password:")
    print("   1. Go to: https://myaccount.google.com/security")
    print("   2. Enable 2-Step Verification (if not already enabled)")
    print("   3. Go to: https://myaccount.google.com/apppasswords")
    print("   4. Select 'Mail' and 'Other (Custom name)'")
    print("   5. Enter 'CARE System' as the name")
    print("   6. Click 'Generate'")
    print("   7. Copy the 16-character password (no spaces)")
    print()
    
    gmail_user = input("Enter your Gmail address: ").strip()
    if not gmail_user:
        print("❌ Gmail address is required!")
        return False
    
    gmail_pass = input("Enter your Gmail App Password (16 chars, no spaces): ").strip()
    if not gmail_pass:
        print("❌ App password is required!")
        return False
    
    base_url = input("Enter your base URL (e.g., http://localhost:5000) [optional]: ").strip()
    
    # Read existing .env or create new
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    env_lines = []
    
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            env_lines = f.readlines()
    
    # Remove old SMTP settings
    new_lines = []
    skip_next = False
    in_email_section = False
    
    for line in env_lines:
        stripped = line.strip()
        if stripped.startswith('# Email Alert Configuration'):
            in_email_section = True
            continue
        if in_email_section and (stripped.startswith('#') or stripped == ''):
            if stripped.startswith('#') and not stripped.startswith('# Email'):
                in_email_section = False
                new_lines.append(line)
            continue
        if in_email_section:
            continue
        if any(stripped.startswith(prefix) for prefix in ['ALERT_MODE=', 'SMTP_', 'BASE_URL=']):
            continue
        new_lines.append(line)
    
    # Add new settings
    new_lines.append('\n')
    new_lines.append('# Email Alert Configuration\n')
    new_lines.append('ALERT_MODE=smtp\n')
    new_lines.append('SMTP_SERVER=smtp.gmail.com\n')
    new_lines.append('SMTP_PORT=587\n')
    new_lines.append(f'SMTP_USERNAME={gmail_user}\n')
    new_lines.append(f'SMTP_PASSWORD={gmail_pass}\n')
    new_lines.append(f'SMTP_FROM_EMAIL={gmail_user}\n')
    new_lines.append('SMTP_USE_TLS=true\n')
    if base_url:
        new_lines.append(f'BASE_URL={base_url}\n')
    
    # Write back
    with open(env_path, 'w') as f:
        f.writelines(new_lines)
    
    print()
    print("✅ Email configuration added to .env file!")
    print()
    print("🧪 Testing email configuration...")
    print()
    
    # Test configuration
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from alert_service import alert_service
        
        print(f"Mode: {alert_service.mode}")
        if alert_service.mode == 'smtp':
            print(f"SMTP Server: {alert_service.smtp_server}")
            print(f"SMTP Port: {alert_service.smtp_port}")
            print(f"From Email: {alert_service.smtp_from_email}")
            print("✅ SMTP configured successfully!")
            print()
            print("📧 To test, run:")
            print("   python3 scripts/test_email.py")
        else:
            print("❌ SMTP not configured. Check your .env file.")
    except Exception as e:
        print(f"⚠️  Could not test configuration: {e}")
        print("   But settings were saved to .env file")
    
    print()
    print("=" * 70)
    print("✅ Setup complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Restart your Flask app to load new settings")
    print("2. Test with: python3 scripts/test_email.py")
    print("3. Make sure caretakers/doctors have email addresses in database")
    print()
    
    return True

if __name__ == "__main__":
    setup_email_alerts()

