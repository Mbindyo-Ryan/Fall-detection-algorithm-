# Alert System Setup Guide

## 📱 Overview

The alert system automatically sends SMS and phone call alerts to caregivers and doctors when falls are detected. It supports both **Twilio** (production) and **Mock mode** (development/testing).

## 🚀 Quick Start

### Development/Testing (Mock Mode)

The system runs in **mock mode by default** - no actual SMS/calls are sent, but all functionality is logged:

```bash
# No setup required! Just run the app
python app_auth.py
```

You'll see alert logs in the console:
```
📱 [MOCK SMS] To: +1234567890
   Message: 🚨 FALL ALERT - SEVERE...
```

### Production (Twilio)

1. **Get Twilio Account**
   - Sign up at https://www.twilio.com/try-twilio
   - Get your Account SID and Auth Token
   - Get a phone number (or use trial number)

2. **Set Environment Variables**
   ```bash
   export ALERT_MODE="twilio"
   export TWILIO_ACCOUNT_SID="your_account_sid"
   export TWILIO_AUTH_TOKEN="your_auth_token"
   export TWILIO_PHONE_NUMBER="+1234567890"  # Your Twilio number
   ```

3. **Install Twilio SDK**
   ```bash
   pip install twilio
   ```

4. **Update .env file** (optional)
   ```env
   ALERT_MODE=twilio
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=+1234567890
   ```

## ⚙️ Configuration

### Alert Rules

Alerts are sent based on fall severity:

| Severity | SMS | Call | Delay | Recipients |
|----------|-----|------|-------|------------|
| **Severe** | ✅ | ✅ | Immediate | Caretakers, Doctors, Patient |
| **Moderate** | ✅ | ❌ | 30 seconds | Caretakers, Doctors |
| **Mild** | ✅ | ❌ | 60 seconds | Caretakers only |

### Customizing Alert Rules

Edit `alert_service.py`:

```python
ALERT_RULES = {
    'severe': {
        'sms': True,
        'call': True,
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
- Calculates severity (mild/moderate/severe)
- Triggers alert service

### 2. Recipient Lookup
System finds:
- **Caretakers**: Users assigned to patient via `patient_caretaker` table
- **Doctors**: Users assigned to patient via `patient_doctor` table
- **Emergency Contacts**: Patient's own phone (for severe falls)

### 3. Alert Sending
- Sends SMS to all recipients (based on rules)
- Makes phone calls for severe falls
- Logs all attempts to `alert_logs` table

## 📋 Setting Up Patient-Caregiver Relationships

### Via Database
```sql
-- Assign caretaker to patient
INSERT INTO patient_caretaker (patient_id, caretaker_id, assigned_by)
VALUES ('patient_id', 'caretaker_id', 'doctor_id');

-- Assign doctor to patient
INSERT INTO patient_doctor (patient_id, doctor_id)
VALUES ('patient_id', 'doctor_id');
```

### Via API (Coming Soon)
```bash
POST /api/patients/assign
{
  "patient_id": "patient_123",
  "type": "caretaker"  # or "doctor"
}
```

## 🧪 Testing Alerts

### Test Alert Endpoint
```bash
# Send test alert (doctors/caretakers only)
curl -X POST http://localhost:5000/api/alerts/test \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{"severity": "moderate"}'
```

### Check Alert Status
```bash
# Get alert service status
curl http://localhost:5000/api/alerts/status
```

### View Alert Logs
```bash
# Get alert history
curl http://localhost:5000/api/alerts/logs
```

## 📊 Alert Logs

All alert attempts are logged to `alert_logs` table:

```sql
SELECT * FROM alert_logs ORDER BY timestamp DESC;
```

Columns:
- `fall_id`: Associated fall event
- `recipient_id`: Who received the alert
- `alert_type`: 'sms' or 'call'
- `success`: 1 if sent, 0 if failed
- `details`: Additional info
- `timestamp`: When alert was sent

## 🔔 Alert Messages

### SMS Format
```
🚨 FALL ALERT - SEVERE

Patient: John Doe
Time: 2024-01-15 14:30:25
Location: Living Room

Please check the CARE system dashboard immediately.
```

### Phone Call (TTS)
```
"Fall alert. Severe severity fall detected for patient John Doe at Living Room. 
Time: 2:30 PM. Please check the CARE system dashboard immediately."
```

## 🛠️ Troubleshooting

### Alerts Not Sending?

1. **Check Mode**
   ```python
   # In alert_service.py, check:
   print(alert_service.mode)  # Should be 'twilio' or 'mock'
   ```

2. **Check Recipients**
   - Ensure patient has assigned caretakers/doctors
   - Verify phone numbers are in database
   - Check `patient_caretaker` and `patient_doctor` tables

3. **Check Twilio Credentials**
   - Verify environment variables are set
   - Test Twilio connection:
     ```python
     from twilio.rest import Client
     client = Client(account_sid, auth_token)
     # Should not raise error
     ```

4. **Check Logs**
   - View console output for error messages
   - Check `alert_logs` table for failed attempts

### Mock Mode Still Sending?

- Ensure `ALERT_MODE` is not set to 'twilio'
- Check that Twilio credentials are missing
- System will auto-fallback to mock if Twilio unavailable

## 💰 Twilio Costs

**SMS**: ~$0.0075 per message (varies by country)
**Voice Calls**: ~$0.013 per minute (varies by country)

**Trial Account**: 
- Free $15.50 credit
- Can only send to verified numbers
- Perfect for testing

## 🔒 Security Considerations

1. **Phone Number Privacy**: Store phone numbers securely
2. **Rate Limiting**: Implement rate limits to prevent abuse
3. **Verification**: Verify phone numbers before sending
4. **Opt-Out**: Allow users to opt-out of alerts
5. **Audit Logs**: Keep detailed logs for compliance

## 📱 Future Enhancements

- [ ] Email alerts
- [ ] Push notifications (mobile app)
- [ ] WhatsApp integration
- [ ] Multi-language support
- [ ] Custom alert templates
- [ ] Alert scheduling (quiet hours)
- [ ] Alert escalation (if no response)
- [ ] Two-way SMS (patient can respond)

## 📞 Support

For Twilio issues:
- Twilio Docs: https://www.twilio.com/docs
- Twilio Support: https://support.twilio.com

For system issues:
- Check logs in console
- Review `alert_logs` table
- Test with mock mode first

