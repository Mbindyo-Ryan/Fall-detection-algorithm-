# CARE System – Run Instructions

This guide mirrors the reviewer-friendly layout from the toxicity-detector project so that anyone can spin up the fall detection platform, reproduce experiments, and capture evidence quickly.

---

## 1. Requirements

- **OS**: Tested on macOS 13+ and Ubuntu 22.04.
- **Python**: 3.9–3.11.
- **Hardware**: CPU works for heuristics + RandomForest. A GPU (or Apple Silicon acceleration) speeds up TensorFlow-based CNN validation but is optional.
- **FFmpeg/OpenCV**: The system uses OpenCV’s video backend; install OS-level codecs if videos fail to open.

---

## 2. Environment Setup

```bash
git clone https://github.com/mbindyoryankyalo/Fall-detection-algorithm-.git
cd Fall-detection-algorithm-
python3 -m venv .venv
source .venv/bin/activate
make install
```

> Tip: The `requirements.txt` file now mirrors all modules used across Flask, MediaPipe, TensorFlow, PDF generation, and Twilio alerts.

### Required environment variables

Create a `.env` file or export the following before running Flask:

| Variable | Purpose |
|----------|---------|
| `FLASK_SECRET` | Session secret key |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth credentials for SSO |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` | Only if you want real SMS/call alerts; otherwise the alert service falls back to mock mode |
| `ALERT_MODE` | `mock` (default) or `twilio` |

---

## 3. Database & Dummy Data

1. Initialize tables automatically by launching the app once (`make run`).
2. Seed realistic data:

```bash
make seed-db
```

Creates admins, doctors, caretakers, patients, and 30+ fall incidents for UI exploration.

Default accounts (2FA already configured):
- Admin: `admin@care.com` / `admin123`
- Doctor: `sarah.thompson@care.com` / `doctor123`
- Caretaker: `alice.cooper@care.com` / `caretaker123`
- Patient: `john.smith@patient.com` / `patient123`

---

## 4. Running the System

```bash
make run           # Production-style
# or
make run-debug     # With Flask debugger + reload
```

Navigate to [http://127.0.0.1:5000](http://127.0.0.1:5000). Log in as admin first to add cameras or approve relationships.

---

## 5. Working with Videos

### 5.1 Organize evaluation clips

```bash
make setup-test-data  # interactive helper
```

This creates `fall_videos/falls` and `fall_videos/no_falls`, then walks you through labeling each clip (previewed via OpenCV).

### 5.2 Run offline tests

```bash
make test-video VIDEO="fall_videos/video (36).avi" GROUND=1
```

Outputs per-frame stats, hybrid confidence, detection timestamps, and saves results to `test_results.json`.

---

## 6. Training Pipelines

| Target | Description |
|--------|-------------|
| `make train-ml` | Re-trains the RandomForest classifier on features from `data/feature_logs*.csv` |
| `make train-cnn` | Trains or fine-tunes the TensorFlow CNN validator (`models/cnn_validator.h5`) |

Guides:
- `ML_MODEL_GUIDE.md`
- `CNN_INTEGRATION_GUIDE.md`
- `DATASET_GUIDE.md`

---

## 7. Dashboards & Roles

1. **Admin**: Add cameras pointing to files or RTSP feeds. Monitor metrics + logs (`/dashboard_admin`).
2. **Patient**: View live feed, fall history, upload docs.
3. **Caretaker/Doctor**: Receive alerts, review incidents, add remarks (see `REVIEW_SYSTEM_GUIDE.md`).

Role-based content is enforced server-side; simply log in with the appropriate dummy credentials.

---

## 8. Packaging a Submission

```bash
make package-release
```

Creates `dist/care-system-release.zip` containing:
- Application source (`app_auth.py`, `detection_skeleton.py`, `scripts/`, `templates/`)
- Models + data artifacts (`models/`, `data/`)
- Documentation (`PROJECT_DOCUMENTATION.md`, `REVIEWER_GUIDE.md`, `VIDEO_TESTING_GUIDE.md`)
- This runbook + Makefile + requirements.

You can hand the ZIP to reviewers exactly like the toxicity-detector bundle.

---

## 9. Troubleshooting

| Issue | Fix |
|-------|-----|
| Video loops too quickly | Edit camera entry → set `rewind_delay_seconds` or adjust `ThreadedCamera` sleep |
| CNN disabled message | Ensure `models/cnn_validator.h5` exists or re-run `make train-cnn` |
| Twilio errors | Set `ALERT_MODE=mock` until credentials are ready |
| Mediapipe missing | Re-run `make install` (it may fail silently without pip upgrade) |

For more depth (methodology, testing matrices, literature review) open `PROJECT_DOCUMENTATION.md`.

