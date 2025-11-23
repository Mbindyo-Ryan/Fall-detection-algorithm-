# Troubleshooting: No Fall Detected

If the system is not detecting falls, follow these steps:

## Quick Checks

### 1. **Camera/Video Feed**
- ✅ Is the video feed showing in the dashboard?
- ✅ Is a person visible in the frame?
- ✅ Is the camera/video source correct?

**To check:**
```bash
python3 scripts/diagnose_detection.py
```

**Common issues:**
- Camera index wrong (try 0, 1, 2, etc.)
- Video file path incorrect
- Camera permissions not granted
- Camera already in use by another app

### 2. **User ID**
The detector must have the correct user_id set. Check:
- Are you logged in?
- Does the dashboard show your user info?
- Check server console for: `🎯 Video feed: Set detector user_id to <your_user_id>`

**Fix:** Make sure you're logged in and the video feed route is active.

### 3. **Pose Detection**
MediaPipe must detect a person in the frame. Check:
- Person is fully visible (not cut off)
- Good lighting
- Person is facing the camera (side view works but less accurate)
- No obstructions

**Debug:** Look for "No Person Detected" message on video feed.

### 4. **Detection Thresholds**

Current thresholds (more sensitive):
- `FALL_CONFIRM_FRAMES`: 3 (must detect fall for 3 consecutive frames)
- `FALL_THRESHOLD_VELOCITY`: 0.01 (downward velocity threshold)
- `fall_score threshold`: 0.4 (confidence threshold)
- `torso_angle_threshold`: 30° (torso angle from vertical)
- `height_ratio_threshold`: 0.65 (height compared to normal)
- `ground_contact_threshold`: 0.75 (contact with ground plane)

**If still not detecting, try:**
1. Make a more dramatic fall (faster, more obvious)
2. Check server console for detection messages
3. Run diagnostic script to see current values

## Diagnostic Steps

### Step 1: Run Diagnostic Script
```bash
cd /Users/mbindyoryankyalo/Desktop/FDA/Fall-detection-algorithm-
python3 scripts/diagnose_detection.py
```

This will show:
- Detector configuration
- Camera status
- Detection thresholds
- Sample frame test results

### Step 2: Check Server Console
When testing fall detection, watch the Flask server console for:
- `🔍 Fall detected: counter=X/3...` - Detection is working
- `✅ Fall confirmed!` - Fall was confirmed and logged
- `⚠️ No person detected...` - Pose detection issue
- `📝 Attempting to log fall to DB...` - Logging attempt

### Step 3: Test with Video File
If camera isn't working, test with a video file:

1. Add video as camera source in dashboard
2. Use a video file with a clear fall
3. Watch console for detection messages

### Step 4: Check Database
```bash
python3 scripts/debug_falls.py
```

This shows:
- Recent falls in database
- User IDs
- Detection status

## Common Issues & Solutions

### Issue: "Cannot open camera source: 0"
**Solution:**
- Try different camera indices (1, 2, etc.)
- Use a video file instead
- Check camera permissions
- Close other apps using the camera

### Issue: "No Person Detected"
**Solution:**
- Ensure person is fully visible
- Improve lighting
- Move closer to camera
- Check camera focus

### Issue: "Fall detected but not logged"
**Solution:**
- Check user_id is set correctly
- Check database connection
- Look for cooldown messages
- Check database permissions

### Issue: "Detection too sensitive (false positives)"
**Solution:**
Edit `detection_skeleton.py`:
```python
FALL_CONFIRM_FRAMES = 5  # Increase from 3
FALL_THRESHOLD_VELOCITY = 0.015  # Increase from 0.01
fall_detected = fall_score > 0.5  # Increase from 0.4
```

### Issue: "Detection not sensitive enough"
**Solution:**
Edit `detection_skeleton.py`:
```python
FALL_CONFIRM_FRAMES = 2  # Decrease from 3
FALL_THRESHOLD_VELOCITY = 0.008  # Decrease from 0.01
fall_detected = fall_score > 0.3  # Decrease from 0.4
```

## Testing Fall Detection

### Manual Test:
1. Stand in front of camera
2. Slowly lower yourself (simulate fall)
3. Watch console for detection messages
4. Check dashboard for fall event

### Video Test:
1. Use a test video with a known fall
2. Add video as camera source
3. Let it play
4. Check console and database

### Debug Mode:
Add more logging by editing `detection_skeleton.py`:
- Reduce `_frame_debug_counter % 300` to `% 30` for more frequent logs
- Add print statements in `detect_fall_enhanced()`

## Still Not Working?

1. **Check all logs:**
   - Flask server console
   - Browser console (F12)
   - Database debug script output

2. **Verify setup:**
   - Database connection working
   - Models loaded (ML model, CNN if enabled)
   - User logged in and authenticated

3. **Test components:**
   - Camera/video feed
   - Pose detection (MediaPipe)
   - Database logging
   - User ID propagation

4. **Contact support:**
   - Share diagnostic script output
   - Share server console logs
   - Describe what you're testing (camera/video, type of fall, etc.)

## Current Settings (More Sensitive)

After recent updates, detection is more sensitive:
- ✅ Faster confirmation (3 frames instead of 5)
- ✅ Lower velocity threshold (0.01 instead of 0.015)
- ✅ Lower confidence threshold (0.4 instead of 0.5)
- ✅ More lenient angle/height thresholds

If you need to adjust, edit `detection_skeleton.py` and restart the Flask server.

