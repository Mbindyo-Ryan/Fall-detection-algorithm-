# CARE System – Reviewer Guide

This guide is inspired by the format of OmondiKevin/toxicity-detector’s `REVIEWER_GUIDE.md`. It highlights exactly what examiners should run, what evidence to capture, and where supporting artifacts live.

---

## 1. Preparation (5 minutes)

```bash
git clone https://github.com/mbindyoryankyalo/Fall-detection-algorithm-.git
cd Fall-detection-algorithm-
python3 -m venv .venv && source .venv/bin/activate
make install
make seed-db
make run
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

---

## 2. Accounts to Use

| Role | Email | Password | Notes |
|------|-------|----------|-------|
| Admin | `admin@care.com` | `admin123` | Enables camera management + system logs |
| Doctor | `sarah.thompson@care.com` | `doctor123` | Review forms, PDF export |
| Caretaker | `alice.cooper@care.com` | `caretaker123` | Receives alerts, sees assigned patients |
| Patient | `john.smith@patient.com` | `patient123` | Live feed + fall history |

2FA secrets are already registered; enter the TOTP shown in the console when prompted.

---

## 3. Core Demo Script

1. **Admin – Add camera**
   - Go to `My Cameras` → `Add Camera`.
   - Source: `/Users/.../fall_videos/video (36).avi`
   - Location: “living room”.
   - Confirm the status badge turns `Active`.

2. **Patient – Monitor feed**
   - Login as John Smith.
   - Visit `My Stats`.
   - Observe the live feed overlay (pose skeleton, heuristic confidence, ML/CNN scores). Capture a screenshot when the status banner lights up red.

3. **Detection evidence**
   - Leave the feed running until the clip loops; check `My Recent Fall Events`.
   - Confirm entries include severity, confidence, and download link (`fall_videos/fall_*.mp4`).

4. **Doctor review**
   - Login as Dr. Sarah.
   - Open `Review Falls`.
   - Pick the new fall, add remarks, recommendations, and generate the PDF.

5. **Caretaker follow-up**
   - Login as Alice.
   - Navigate to assigned patient list and verify the same fall shows up with doctor remarks.

---

## 4. Testing Scripts (Offline Verification)

| Command | Purpose |
|---------|---------|
| `make test-video VIDEO="fall_videos/video (36).avi" GROUND=1` | Batch analysis with metrics + JSON export |
| `python scripts/setup_test_data.py --list` | Show absolute paths of categorized clips |
| `python scripts/test_model.py` | Smoke-test the RandomForest classifier |

Artifacts are written to `test_results.json` and `data/feature_logs*.csv`. Include them in appendices if needed.

---

## 5. Documentation Bundle

| File | Content |
|------|---------|
| `PROJECT_DOCUMENTATION.md` | Strathmore-style chapters 1–6 |
| `RUN_INSTRUCTIONS.md` | This setup/runbook |
| `VIDEO_TESTING_GUIDE.md` | Detailed evaluation workflow |
| `CNN_INTEGRATION_GUIDE.md` | Architecture + performance for the CNN validator |
| `REVIEW_SYSTEM_GUIDE.md` | Doctor-facing review features |

Everything is zipped automatically via `make package-release`.

---

## 6. Grading Checklist

- [ ] Live fall detection from prerecorded video (with overlay + logs)
- [ ] Multi-role dashboards & RBAC (admin, doctor, caretaker, patient)
- [ ] Alert pathway demonstrated (mock Twilio logs in console)
- [ ] Doctor review workflow (remarks, recommendations, PDF export)
- [ ] Offline evaluation evidence (`test_results.json`, saved fall clips)
- [ ] CNN validator status (loaded or message explaining why disabled)
- [ ] Documentation package handed in (zip file, references, appendices)

If any box is unchecked, refer to the relevant guide above for remediation steps.

