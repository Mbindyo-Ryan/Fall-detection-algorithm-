# CARE System – Real-Time Fall Detection Platform

The CARE (Continuous Alert and Responsive Engagement) System is a Flask-based monitoring platform that combines MediaPipe pose estimation, heuristic rules, classical ML, and an optional CNN validator to detect elderly falls in real time.
---

## Architecture Snapshot

- **Web & Security**: Flask + Authlib Google OAuth, enforced 2FA (PyOTP), role-based dashboards (Admin, Doctor, Caretaker, Patient).
- **Detection Engine**: `detection_skeleton.py` orchestrates MediaPipe pose tracking, RandomForest classification, hybrid heuristics, and an optional TensorFlow CNN validator fed by a rolling frame buffer.
- **Video I/O**: Threaded OpenCV capture supporting webcams, RTSP streams, and looping MP4/AVI files for demos.
- **Alerting**: Twilio SMS/call integration with mock mode fallback; alert rules per severity stored in SQLite.
- **Data Layer**: `system_config.db` with tables for falls, alerts, user relationships, and doctor reviews; dummy data generator for sandbox demos.

---

## Feature Highlights

- Secure authentication with Google SSO + mandatory TOTP.
- Multi-role dashboards tailored to patients, caretakers, doctors, and admins.
- Live monitoring overlay showing pose confidence, ML/CNN scores, FPS, and severity.
- Automated fall clips (pre/post event) saved to `fall_videos/`.
- Doctor review workflow with PDF exports and patient file uploads.
- Offline benchmarking scripts for batch testing any folder of videos.

---

## Documentation Map

| File | Purpose |
|------|---------|
| `RUN_INSTRUCTIONS.md` | Step-by-step setup, env vars, Makefile targets |
| `REVIEWER_GUIDE.md` | Script for examiners to validate features quickly |
| `PROJECT_DOCUMENTATION.md` | Full academic Chapters 1–6 (Strathmore format) |
| `VIDEO_TESTING_GUIDE.md` / `QUICK_VIDEO_TEST.md` | Detailed vs. cheat-sheet evaluation instructions |
| `CNN_INTEGRATION_GUIDE.md` / `ML_MODEL_GUIDE.md` | Model architecture + training notes |
| `REVIEW_SYSTEM_GUIDE.md` | Doctor review & PDF workflow |

---

## Quick Start (Make-driven)

```bash
git clone https://github.com/mbindyoryankyalo/Fall-detection-algorithm-.git
cd Fall-detection-algorithm-
python3 -m venv .venv && source .venv/bin/activate
make install
make run           # or: make run-debug
```

1. Visit [http://127.0.0.1:5000](http://127.0.0.1:5000).
2. Use the registration form (local or Google OAuth) to create your own account.
3. After logging in and completing 2FA setup, add a camera on the same network, or for demonstration purposes, a video link, pointing to any clip in `fall_videos/` to trigger detections.



---

## Make Targets

| Command | Description |
|---------|-------------|
| `make install` | Install all Python dependencies from `requirements.txt` |
| `make run` / `make run-debug` | Start the Flask server (production vs. debug) |
| `make setup-test-data` | Interactive labeling of raw videos into `falls/` and `no_falls/` |
| `make test-video VIDEO=... [GROUND=0|1]` | Batch test a single clip via `scripts/test_fall_videos.py` |
| `make train-ml` / `make train-cnn` | Retrain the RandomForest classifier or CNN validator |
| `make package-release` | Generate `dist/care-system-release.zip` (code + models + docs) |
| `make lint` | Run flake8 over the main modules and scripts |

See `RUN_INSTRUCTIONS.md` for additional context and troubleshooting tips.

---

## Release Bundle

Running `make package-release` invokes `tools/package_release.py` to zip:
- Application source (`app_auth.py`, `detection_skeleton.py`, `alert_service.py`, `templates/`, `scripts/`)
- Models + datasets (`models/`, `data/`, categorized `fall_videos/`)
- Complete documentation set (all guides listed above)
- `requirements.txt`, `Makefile`, and `test_results.json`

Hand this ZIP to stakeholders just like the toxicity-detector reviewer package.

---

## Repository Layout (excerpt)

| Path | Description |
|------|-------------|
| `app_auth.py` | Flask entrypoint with OAuth, 2FA, RBAC, and dashboard routes |
| `detection_skeleton.py` | Hybrid fall detection engine + video recorder |
| `scripts/` | Utilities for dummy data, training, dataset prep, and testing |
| `templates/` | Tailwind dashboards for each role |
| `models/` | Serialized RandomForest + optional CNN validator |
| `fall_videos/` | Sample videos, recorded incidents, and categorized folders |
| `tools/package_release.py` | Automated release bundle creator |

---

## Notes & Next Steps

- 2FA secrets are pre-generated for dummy users; console displays the code when you log in.
- Twilio integration defaults to mock mode—set `ALERT_MODE=twilio` and provide credentials for live SMS/calls.
- CNN validation is optional but recommended; train it with `make train-cnn` and place the `.h5` file under `models/`.
- Academic deliverables (diagrams, references, appendices) still need final polishing—see `PROJECT_DOCUMENTATION.md` for placeholders.