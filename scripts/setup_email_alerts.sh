#!/bin/bash
# Quick setup script for email alerts (Gmail)

echo "=========================================="
echo "📧 Email Alert Setup (Gmail)"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file..."
    touch .env
fi

echo "To set up email alerts, you need:"
echo "1. A Gmail account"
echo "2. An App Password (not your regular password)"
echo ""
echo "📝 Steps to get Gmail App Password:"
echo "   1. Go to: https://myaccount.google.com/security"
echo "   2. Enable 2-Step Verification (if not already enabled)"
echo "   3. Go to: https://myaccount.google.com/apppasswords"
echo "   4. Select 'Mail' and 'Other (Custom name)'"
echo "   5. Enter 'CARE System' as the name"
echo "   6. Click 'Generate'"
echo "   7. Copy the 16-character password (no spaces)"
echo ""

read -p "Enter your Gmail address: " GMAIL_USER
read -p "Enter your Gmail App Password (16 chars, no spaces): " GMAIL_PASS
read -p "Enter your base URL (e.g., http://localhost:5000): " BASE_URL

if [ -z "$GMAIL_USER" ] || [ -z "$GMAIL_PASS" ]; then
    echo "❌ Gmail address and password are required!"
    exit 1
fi

# Remove old SMTP settings
sed -i.bak '/^ALERT_MODE=/d' .env
sed -i.bak '/^SMTP_/d' .env
sed -i.bak '/^BASE_URL=/d' .env

# Add new settings
echo "" >> .env
echo "# Email Alert Configuration" >> .env
echo "ALERT_MODE=smtp" >> .env
echo "SMTP_SERVER=smtp.gmail.com" >> .env
echo "SMTP_PORT=587" >> .env
echo "SMTP_USERNAME=$GMAIL_USER" >> .env
echo "SMTP_PASSWORD=$GMAIL_PASS" >> .env
echo "SMTP_FROM_EMAIL=$GMAIL_USER" >> .env
echo "SMTP_USE_TLS=true" >> .env
if [ ! -z "$BASE_URL" ]; then
    echo "BASE_URL=$BASE_URL" >> .env
fi

echo ""
echo "✅ Email configuration added to .env file!"
echo ""
echo "🧪 Testing email configuration..."
python3 << EOF
import os
from dotenv import load_dotenv
load_dotenv()

from alert_service import alert_service

print(f"Mode: {alert_service.mode}")
if alert_service.mode == 'smtp':
    print(f"SMTP Server: {alert_service.smtp_server}")
    print(f"SMTP Port: {alert_service.smtp_port}")
    print(f"From Email: {alert_service.smtp_from_email}")
    print("✅ SMTP configured successfully!")
    print("")
    print("📧 To test, run:")
    print("   python3 scripts/test_email.py")
else:
    print("❌ SMTP not configured. Check your .env file.")
EOF

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Restart your Flask app to load new settings"
echo "2. Test with: python3 scripts/test_email.py"
echo "3. Make sure caretakers/doctors have email addresses in database"
echo ""


