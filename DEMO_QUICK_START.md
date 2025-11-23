# 🎯 Quick Demo Guide - Monday Presentation

## ⚡ Fastest Way to Demo (30 seconds)

```bash
cd /Users/mbindyoryankyalo/Desktop/FDA/Fall-detection-algorithm-
python3 scripts/demo_email_alerts.py
```

**That's it!** This shows:
- ✅ Email alert system configuration
- ✅ Email preview (what recipients receive)
- ✅ Simulated alerts for all severity levels
- ✅ Console output showing emails being "sent"

## 📋 What to Say

1. **"We've replaced phone/SMS with email notifications"**
2. **"Currently in mock mode - emails logged to console"**
3. **"In production, these would be real emails via SMTP"**
4. **"Severity-based routing: severe=immediate, moderate=30s delay, mild=60s delay"**
5. **"HTML emails with color-coded severity levels"**

## 🎬 Live Demo Option

If you want to show it working with actual fall detection:

1. Start Flask: `python3 app_auth.py`
2. Login to dashboard
3. Trigger a fall (stand in front of camera)
4. Show console logs: `📧 [MOCK EMAIL] To: ...`

## 📧 Email Preview

The demo script shows exactly what recipients receive:
- Color-coded headers (red=severe, orange=moderate, blue=mild)
- Patient details, severity, time, location
- Link to dashboard
- Professional HTML formatting

## 💡 Pro Tip

Run the demo script **before** your presentation to make sure it works, then just run it again during the demo!

---

**Full guide:** See `docs/DEMO_GUIDE.md` for complete details


