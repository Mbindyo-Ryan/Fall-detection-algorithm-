# Demo Guide: Email Alert System

## 🎯 Quick Demo for Monday

### Option 1: Mock Mode Demo (Recommended - No Setup Needed)

**Best for:** Live demonstrations, presentations, showing functionality without email setup

1. **Run the demo script:**
   ```bash
   cd /Users/mbindyoryankyalo/Desktop/FDA/Fall-detection-algorithm-
   python3 scripts/demo_email_alerts.py
   ```

2. **What it shows:**
   - Current configuration (mock mode)
   - Email preview (what recipients receive)
   - Simulated alerts for all severity levels
   - Console output showing emails being "sent"

3. **What to say:**
   - "The system is currently in mock mode for demonstration"
   - "In production, these would be real emails sent via SMTP"
   - "Notice the different severity levels and recipient rules"
   - "The emails include HTML formatting and a link to the dashboard"

### Option 2: Live Fall Detection Demo

**Best for:** Showing the complete workflow

1. **Start the Flask app:**
   ```bash
   python3 app_auth.py
   ```

2. **Login and trigger a fall:**
   - Login to the dashboard
   - Stand in front of camera (or use test video)
   - Simulate a fall
   - Watch console for email alert logs

3. **Show the logs:**
   - Point out the email alert messages in console
   - Show that alerts are logged to database
   - Explain the severity-based routing

### Option 3: Real Email Demo (If You Have Time)

**Best for:** Impressive live demonstration with actual emails

1. **Set up Gmail App Password:**
   - Go to Google Account → Security → 2-Step Verification
   - Generate App Password for "Mail"
   - Copy the password

2. **Configure environment:**
   ```bash
   export ALERT_MODE=smtp
   export SMTP_SERVER=smtp.gmail.com
   export SMTP_PORT=587
   export SMTP_USERNAME=your-email@gmail.com
   export SMTP_PASSWORD=your-app-password
   export SMTP_FROM_EMAIL=your-email@gmail.com
   export SMTP_USE_TLS=true
   ```

3. **Test with demo script:**
   ```bash
   python3 scripts/demo_email_alerts.py
   ```

4. **Check your email inbox** - you'll receive the actual email!

## 📋 Demo Checklist

### Before the Demo:
- [ ] Test the demo script: `python3 scripts/demo_email_alerts.py`
- [ ] Verify Flask app starts: `python3 app_auth.py`
- [ ] Check that alert service loads correctly
- [ ] Prepare talking points (see below)

### During the Demo:
- [ ] Show mock mode output (console logs)
- [ ] Explain email format and content
- [ ] Show severity-based routing rules
- [ ] Demonstrate fall detection triggering alerts
- [ ] Show database logging (optional)

### Talking Points:

1. **"Email Notification System"**
   - "We've replaced phone/SMS with email notifications"
   - "Supports both development (mock) and production (SMTP)"
   - "HTML emails with color-coded severity levels"

2. **"Severity-Based Routing"**
   - "Severe falls: Immediate email to all (caretakers, doctors, patient)"
   - "Moderate falls: 30-second delay, to caretakers and doctors"
   - "Mild falls: 60-second delay, to caretakers only"

3. **"Email Features"**
   - "HTML formatted with color-coded headers"
   - "Includes patient name, severity, time, location"
   - "Link to dashboard for detailed review"
   - "Plain text fallback for email clients"

4. **"Production Ready"**
   - "Works with Gmail, Outlook, or any SMTP server"
   - "Secure authentication with app passwords"
   - "Comprehensive logging and error handling"

## 🎬 Demo Script (What to Say)

### Introduction:
"Today I'll demonstrate our email notification system for fall detection alerts."

### Part 1: Configuration
"First, let me show you the current configuration. We're running in mock mode, which means emails are logged to console instead of being sent. This is perfect for development and testing."

*Run: `python3 scripts/demo_email_alerts.py`*

### Part 2: Email Preview
"Here's what recipients receive when a fall is detected. Notice the color-coded severity levels and the professional HTML formatting."

*Show email preview section*

### Part 3: Live Demo
"Now let me show you how it works in practice. When a fall is detected..."

*Trigger fall detection or show console logs*

### Part 4: Production Setup
"For production, we simply configure SMTP settings and the system automatically sends real emails. The code remains the same - just different configuration."

## 📊 What to Show

### Console Output:
```
📧 [MOCK EMAIL] To: doctor@example.com
   Subject: 🚨 Fall Alert - SEVERE for John Doe
   Body: A fall has been detected...
```

### Email Preview:
- Show the HTML email structure
- Explain color coding (red=severe, orange=moderate, blue=mild)
- Point out dashboard link

### Database:
- Show `alert_logs` table (if time permits)
- Show `falls` table with `alert_sent` flag

## 🚀 Quick Setup for Real Email Demo

If you want to show actual emails:

1. **5 minutes to set up:**
   ```bash
   # Get Gmail app password (2 minutes)
   # Add to .env file (1 minute)
   # Restart Flask app (1 minute)
   # Test (1 minute)
   ```

2. **Add to .env:**
   ```env
   ALERT_MODE=smtp
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-16-char-app-password
   SMTP_FROM_EMAIL=your-email@gmail.com
   SMTP_USE_TLS=true
   ```

3. **Test:**
   ```bash
   python3 scripts/demo_email_alerts.py
   ```

## 💡 Pro Tips

1. **Have the demo script ready** - It's the easiest way to show functionality
2. **Show console output** - People can see it working in real-time
3. **Explain mock vs production** - Shows you understand deployment
4. **Mention security** - App passwords, environment variables
5. **Show email preview** - Visual representation is powerful

## ❓ Expected Questions & Answers

**Q: "Why email instead of SMS?"**
A: "Email is more reliable, supports rich formatting, doesn't require third-party services like Twilio, and is easier to set up. Recipients can also forward emails or set up filters."

**Q: "What if someone doesn't check email?"**
A: "Email notifications are one part of the alert system. The dashboard also shows real-time alerts, and we can add push notifications or SMS in the future if needed."

**Q: "How do you handle email failures?"**
A: "All email attempts are logged to the database. Failed attempts are recorded with error details. The system continues to function even if email fails."

**Q: "Can you customize the emails?"**
A: "Yes, the email template is in `alert_service.py` and can be customized. We can add branding, different layouts, or additional information."

## ✅ Success Criteria

Your demo is successful if you can:
- [ ] Show email alerts being triggered
- [ ] Explain severity-based routing
- [ ] Show email format/preview
- [ ] Demonstrate mock vs production modes
- [ ] Answer questions about the system

Good luck! 🎉


