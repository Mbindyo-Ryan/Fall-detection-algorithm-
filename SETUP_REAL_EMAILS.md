# 📧 Setup Real Email Alerts - Quick Guide

## 🚀 Fast Setup (5 minutes)

### Step 1: Get Gmail App Password

1. Go to: https://myaccount.google.com/security
2. Enable **2-Step Verification** (if not already enabled)
3. Go to: https://myaccount.google.com/apppasswords
4. Select:
   - App: **Mail**
   - Device: **Other (Custom name)**
   - Name: **CARE System**
5. Click **Generate**
6. **Copy the 16-character password** (it looks like: `abcd efgh ijkl mnop`)

### Step 2: Configure Email Settings

**Option A: Use the setup script (Easiest)**
```bash
cd /Users/mbindyoryankyalo/Desktop/FDA/Fall-detection-algorithm-
./scripts/setup_email_alerts.sh
```

**Option B: Manual setup**

Add these lines to your `.env` file:
```env
ALERT_MODE=smtp
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_USE_TLS=true
BASE_URL=http://localhost:5000
```

**Important:** 
- Use your **Gmail address** for `SMTP_USERNAME`
- Use the **16-character app password** (not your regular password)
- Remove spaces from the app password when pasting

### Step 3: Test It

```bash
python3 scripts/test_email.py
```

This will:
- Check your SMTP configuration
- Find a user with an email address
- Send a test email
- Show you if it worked

### Step 4: Restart Flask App

```bash
# Stop current app (Ctrl+C)
python3 app_auth.py
```

Now when falls are detected, **real emails will be sent** to:
- Caretakers (if assigned to patient)
- Doctors (if assigned to patient)
- Patient's own email (for severe falls)

## ✅ Verify It's Working

1. **Check console output:**
   - Should see: `✅ Email sent to ...`
   - NOT: `📧 [MOCK EMAIL]`

2. **Check recipient inbox:**
   - Look for email with subject: `🚨 Fall Alert - SEVERE for [Patient Name]`
   - Check spam folder if not in inbox

3. **Check database:**
   ```bash
   python3 scripts/debug_falls.py
   ```
   - Should show `alert_sent = 1` for recent falls

## 🔍 Troubleshooting

### "Email not sent" errors

1. **Check Gmail App Password:**
   - Make sure it's 16 characters
   - No spaces
   - Generated for "Mail" app

2. **Check 2-Step Verification:**
   - Must be enabled to use app passwords

3. **Check .env file:**
   - All SMTP variables set?
   - No typos in email/password?

4. **Test SMTP connection:**
   ```python
   import smtplib
   server = smtplib.SMTP('smtp.gmail.com', 587)
   server.starttls()
   server.login('your-email@gmail.com', 'your-app-password')
   # Should not raise error
   ```

### "No recipients found"

- Make sure:
- Patient has assigned caretakers/doctors
- Caretakers/doctors have email addresses in database
- Email addresses are valid (not NULL, not empty)

Check database:
```sql
SELECT u.name, u.email, u.role 
FROM users u
WHERE u.email IS NOT NULL AND u.email != '';
```

## 📋 Checklist

Before Monday demo:
- [ ] Gmail app password generated
- [ ] .env file configured with SMTP settings
- [ ] Test email sent successfully
- [ ] Flask app restarted with new settings
- [ ] At least one caretaker/doctor has email in database
- [ ] Test fall detection triggers email

## 💡 Pro Tips

1. **Use a dedicated Gmail account** for the system (not your personal one)
2. **Test with your own email first** to make sure it works
3. **Check spam folder** - Gmail might flag first emails as spam
4. **Keep app password secure** - don't commit to Git

## 🎯 For Monday Demo

1. **Show the setup:**
   - Point to .env file with SMTP config
   - Explain app password security

2. **Show it working:**
   - Trigger a fall
   - Show console: `✅ Email sent to doctor@example.com`
   - Show actual email in inbox (if possible)

3. **Explain the system:**
   - "Emails sent automatically when falls detected"
   - "Severity-based routing"
   - "HTML formatted with dashboard links"

---

**Need help?** Run: `python3 scripts/test_email.py` to diagnose issues


