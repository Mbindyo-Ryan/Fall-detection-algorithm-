# Twilio Quick Start Guide

## 🎯 You're on the Right Track!

You selected **"With code"** - perfect for our alert system! This gives you full control over SMS and voice calls.

## 📋 Setup Checklist

### Step 1: Complete Twilio Onboarding
- ✅ Select "With code" (you've done this!)
- Complete the onboarding questions
- Verify your email/phone if prompted

### Step 2: Get Your Credentials

After onboarding, you'll need:

1. **Account SID**
   - Found in: Console Dashboard → Account Info
   - Looks like: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

2. **Auth Token**
   - Found in: Console Dashboard → Account Info
   - Click "View" to reveal (keep this secret!)
   - Looks like: `your_auth_token_here`

3. **Phone Number**
   - Go to: Phone Numbers → Manage → Buy a number
   - Or use your **Trial Number** (free, but limited)
   - Trial numbers can only send to **verified numbers**

### Step 3: Verify Test Numbers (Trial Account)

If using a **Trial Account** ($15.50 free credit):
- Go to: Phone Numbers → Manage → Verified Caller IDs
- Add phone numbers you want to test with
- You can only send SMS/calls to verified numbers

### Step 4: Configure Your App

Add to your `.env` file or export as environment variables:

```bash
export ALERT_MODE="twilio"
export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TWILIO_AUTH_TOKEN="your_auth_token_here"
export TWILIO_PHONE_NUMBER="+1234567890"  # Your Twilio number
```

### Step 5: Install Twilio SDK

```bash
pip install twilio
```

### Step 6: Test It!

```bash
# Start your Flask app
python app_auth.py

# The alert system will automatically use Twilio now
# When a fall is detected, it will send real SMS/calls!
```

## 🧪 Testing

### Test Alert Endpoint
```bash
# As a doctor or caretaker, send a test alert
curl -X POST http://localhost:5000/api/alerts/test \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{"severity": "moderate"}'
```

### Check Alert Status
```bash
curl http://localhost:5000/api/alerts/status
```

## 📱 Trial Account Limitations

**Trial Account** ($15.50 free):
- ✅ Can send SMS to verified numbers
- ✅ Can make calls to verified numbers
- ✅ Perfect for testing
- ❌ Cannot send to unverified numbers
- ❌ Limited to verified numbers only

**Upgrade to Full Account** when ready:
- Send to any phone number
- Production-ready
- Pay-as-you-go pricing

## 💰 Pricing (After Trial)

- **SMS**: ~$0.0075 per message
- **Voice Calls**: ~$0.013 per minute
- Very affordable for healthcare alerts!

## 🔍 Where to Find Everything

### Account SID & Auth Token
1. Go to: **Console Dashboard**
2. Look for **"Account Info"** section
3. Copy **Account SID** and **Auth Token**

### Phone Numbers
1. Go to: **Phone Numbers** → **Manage**
2. Click **"Buy a number"** (or use trial number)
3. Choose a number with SMS + Voice capabilities

### Verified Numbers (Trial)
1. Go to: **Phone Numbers** → **Manage** → **Verified Caller IDs**
2. Click **"Add a new Caller ID"**
3. Enter phone number and verify via SMS/call

## 🚀 Next Steps

1. ✅ Complete Twilio onboarding
2. ✅ Get Account SID and Auth Token
3. ✅ Get/verify a phone number
4. ✅ Set environment variables
5. ✅ Install Twilio SDK
6. ✅ Test with a fall detection!

## 🆘 Troubleshooting

**"Invalid phone number"**
- Make sure number is verified (trial accounts)
- Format: +1234567890 (with country code)

**"Authentication failed"**
- Double-check Account SID and Auth Token
- Make sure no extra spaces in environment variables

**"Number not verified"**
- Add number to Verified Caller IDs (trial accounts)
- Or upgrade to full account

## 📚 Resources

- Twilio Docs: https://www.twilio.com/docs
- Python SDK: https://www.twilio.com/docs/libraries/python
- Support: https://support.twilio.com

---

**Pro Tip**: Start with mock mode to test the system, then switch to Twilio when ready for real alerts!

