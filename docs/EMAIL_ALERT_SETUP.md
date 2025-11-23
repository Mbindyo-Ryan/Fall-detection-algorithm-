# Email Alert System Setup Guide

## 📧 Overview

The alert system automatically sends **email alerts** to caregivers and doctors when falls are detected. It supports both **SMTP** (production) and **Mock mode** (development/testing).

## 🚀 Quick Start

### Development/Testing (Mock Mode)

The system runs in **mock mode by default** - no actual emails are sent, but all functionality is logged:

```bash
# No setup required! Just run the app
python app_auth.py
```

You'll see alert logs in the console:
```
📧 [MOCK EMAIL] To: doctor@example.com
   Subject: 🚨 Fall Alert - SEVERE for John Doe
   Body: A fall has been detected...
```

### Production (SMTP)

1. **Choose Your Email Provider**

   **Option A: Gmail**
   - Use your Gmail account
   - Enable "App Passwords" (not your regular password)
   - Go to: Google Account → Security → 2-Step Verification → App Passwords
   - Generate an app password for "Mail"

   **Option B: Outlook/Office 365**
   - Use your Outlook account
   - May need to enable "Less secure app access" or use app password

   **Option C: Custom SMTP Server**
   - Use your organization's SMTP server
   - Get server address, port, and credentials

2. **Set Environment Variables**

   ```bash
   export ALERT_MODE="smtp"
   export SMTP_SERVER="smtp.gmail.com"  # or smtp.office365.com, etc.
   export SMTP_PORT="587"  # Usually 587 for TLS, 465 for SSL
   export SMTP_USERNAME="your-email@gmail.com"
   export SMTP_PASSWORD="your-app-password"  # App password for Gmail
   export SMTP_FROM_EMAIL="your-email@gmail.com"  # Optional, defaults to SMTP_USERNAME
   export SMTP_USE_TLS="true"  # true for TLS, false for SSL
   ```

3. **Update .env file** (recommended)

   ```env
   ALERT_MODE=smtp
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   SMTP_FROM_EMAIL=your-email@gmail.com
   SMTP_USE_TLS=true
   BASE_URL=http://your-domain.com  # For email links
   ```

## ⚙️ Configuration

### Alert Rules

Alerts are sent based on fall severity:

| Severity | Email | Delay | Recipients |
|----------|-------|-------|------------|
| **Severe** | ✅ | Immediate | Caretakers, Doctors, Patient |
| **Moderate** | ✅ | 30 seconds | Caretakers, Doctors |
| **Mild** | ✅ | 60 seconds | Caretakers only |

### Customizing Alert Rules

Edit `alert_service.py`:

```python
ALERT_RULES = {
    'severe': {
        'email': True,
        'delay_seconds': 0,
        'recipients': ['caretaker', 'doctor', 'emergency_contact']
    },
    # ... customize as needed
}
```

## 🔧 How It Works

### 1. Fall Detection
When a fall is detected:
- System logs fall to database
- Alert service is triggered
- Recipients are determined based on severity

### 2. Recipient Selection
The system finds:
- **Caretakers**: Users assigned to the patient
- **Doctors**: Doctors assigned to the patient
- **Emergency Contacts**: Patient's own email (for severe falls)

**Important**: Recipients must have a valid email address in the database.

### 3. Email Sending
- HTML email with formatted alert
- Plain text fallback
- Includes fall details, severity, location, timestamp
- Link to dashboard for more information

## 📧 Email Format

### Subject Line
```
🚨 Fall Alert - SEVERE for John Doe
```

### Email Body (HTML)
- Color-coded header based on severity
- Patient name and details
- Severity level
- Time and location
- Fall ID (if available)
- Button link to dashboard

### Plain Text Version
Also includes a plain text version for email clients that don't support HTML.

## 🛠️ Troubleshooting

### Emails Not Sending?

1. **Check Mode**
   ```python
   # In alert_service.py, check:
   print(alert_service.mode)  # Should be 'smtp' or 'mock'
   ```

2. **Check Recipients**
   - Ensure patient has assigned caretakers/doctors
   - Verify email addresses are in database
   - Check `patient_caretaker` and `patient_doctor` tables
   - Emails must be valid (not NULL, not empty)

3. **Check SMTP Credentials**
   - Verify environment variables are set
   - Test SMTP connection:
     ```python
     import smtplib
     server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
     server.starttls()
     server.login(SMTP_USERNAME, SMTP_PASSWORD)
     # Should not raise error
     ```

4. **Check Logs**
   - View console output for error messages
   - Check `alert_logs` table for failed attempts
   - Look for SMTP authentication errors

### Gmail Issues

**"Less secure app access" error:**
- Gmail no longer supports less secure apps
- **Solution**: Use App Passwords instead
  1. Enable 2-Step Verification
  2. Generate App Password
  3. Use app password (not your regular password)

**"Username and Password not accepted":**
- Make sure you're using an App Password, not your regular password
- Check that 2-Step Verification is enabled

### Mock Mode Still Sending?

- Ensure `ALERT_MODE` is not set to 'smtp'
- Check that SMTP credentials are missing
- System will auto-fallback to mock if SMTP unavailable

## 📋 SMTP Server Settings

### Common Providers

**Gmail:**
- Server: `smtp.gmail.com`
- Port: `587` (TLS) or `465` (SSL)
- TLS: `true`
- Requires: App Password

**Outlook/Office 365:**
- Server: `smtp.office365.com`
- Port: `587`
- TLS: `true`
- Requires: App Password or OAuth

**Yahoo:**
- Server: `smtp.mail.yahoo.com`
- Port: `587` or `465`
- TLS: `true`
- Requires: App Password

**Custom SMTP:**
- Check with your IT department
- Usually port 587 (TLS) or 465 (SSL)
- May require authentication

## 🔒 Security Considerations

1. **Email Password Security**: 
   - Use App Passwords (not regular passwords)
   - Store in environment variables (not in code)
   - Never commit credentials to Git

2. **Rate Limiting**: 
   - Implement rate limits to prevent abuse
   - Monitor email sending frequency

3. **Email Verification**: 
   - Verify email addresses before sending
   - Handle bounce-backs and invalid addresses

4. **Audit Logs**: 
   - Keep detailed logs for compliance
   - Track all email sending attempts

5. **SPAM Prevention**:
   - Use proper "From" address
   - Include unsubscribe option (future enhancement)
   - Follow email best practices

## 📧 Email Template Customization

To customize the email template, edit `alert_service.py`:

```python
# In send_fall_alert method, modify html_body and text_body
html_body = """
<!DOCTYPE html>
<html>
... your custom HTML ...
</html>
"""
```

## 🚀 Future Enhancements

- [ ] Email templates customization
- [ ] Multi-language support
- [ ] Email scheduling (quiet hours)
- [ ] Email escalation (if no response)
- [ ] Email attachments (fall video/images)
- [ ] Unsubscribe functionality
- [ ] Email delivery tracking
- [ ] Batch email sending

## 📞 Support

For email issues:
- Check SMTP server documentation
- Verify credentials and settings
- Review server logs

For system issues:
- Check console logs
- Review `alert_logs` table
- Run diagnostic scripts

## ✅ Quick Checklist

- [ ] Environment variables set
- [ ] SMTP credentials configured
- [ ] Test email sent successfully
- [ ] Recipients have valid email addresses
- [ ] Patient has assigned caretakers/doctors
- [ ] Alert mode set correctly (smtp/mock)
- [ ] BASE_URL set for email links

