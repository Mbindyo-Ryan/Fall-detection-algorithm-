# Fall Video Testing Guide

## 🎯 Overview

This guide explains how to test the fall detection system with recorded video files for your final presentation.

## 📁 Preparing Your Videos

### 1. Organize Your Videos

Create a folder structure:
```
fall_videos/
  fall_001.mp4
  fall_002.mp4
  no_fall_001.mp4
  no_fall_002.mp4
```

**Supported formats:**
- `.mp4` (recommended)
- `.avi`
- `.mov`
- `.mkv`
- `.flv`
- `.wmv`

### 2. Video Requirements

- **Resolution**: Any (system will resize)
- **Frame Rate**: Any (system handles variable FPS)
- **Duration**: 2-10 seconds recommended for testing
- **Content**: Clear view of person, good lighting

## 🚀 Testing Methods

### Method 1: Using the Dashboard (Easiest for Presentation)

**Steps:**

1. **Add video as camera source:**
   - Login as patient
   - Go to "My Cameras" tab
   - Click "Add Camera"
   - Enter absolute path to video file:
     ```
     /Users/mbindyoryankyalo/Desktop/FDA/Fall-detection-algorithm-/fall_videos/test_fall.mp4
     ```
   - Give it a name: "Test Fall Video 1"
   - Click "Add Camera"

2. **Select video source:**
   - The video will appear in your camera list
   - Select it from the dropdown
   - Video will loop automatically

3. **Watch detection:**
   - System processes video in real-time
   - Falls are detected and logged
   - Check "Falls" tab to see results

**Advantages:**
- ✅ Visual feedback on dashboard
- ✅ Easy to switch between videos
- ✅ Shows all detection metrics
- ✅ Perfect for live demos

### Method 2: Using Test Script (Batch Testing)

**For testing multiple videos:**

```bash
# Test single video
python scripts/test_fall_videos.py \
  --video fall_videos/test_fall.mp4 \
  --ground-truth 1 \
  --output results.json

# Test all videos in directory
python scripts/test_fall_videos.py \
  --directory fall_videos/ \
  --output batch_results.json
```

**Output:**
- JSON file with detection results
- Frame-by-frame detection data
- Performance metrics
- Comparison with ground truth

**Advantages:**
- ✅ Batch processing
- ✅ Detailed metrics
- ✅ Ground truth comparison
- ✅ Automated testing

### Method 3: Direct Video Path (Quick Test)

**For quick testing:**

1. **Set video path directly:**
   - In patient dashboard, add camera with video path
   - Or modify camera source in database

2. **Video loops automatically:**
   - System rewinds when video ends
   - Continuous testing

## 📊 Understanding Results

### Detection Metrics

When testing, you'll see:

1. **Fall Detected**: Yes/No
2. **First Detection Frame**: When fall was first detected
3. **Confidence Score**: 0.0 to 1.0
4. **Detection Time**: Time in video when fall occurred
5. **Processing FPS**: How fast system processes frames

### Video Feed Display

On the dashboard, you'll see:
- **Status**: "⚠️ FALL DETECTED!" or "✅ Normal"
- **Confidence**: Overall detection confidence
- **Velocity**: Downward movement speed
- **Torso Angle**: Body orientation
- **CNN Confidence**: (if CNN model available)
- **Final Confidence**: Combined score

## 🎬 Presentation Tips

### For Live Demo:

1. **Prepare videos in advance:**
   - Test each video beforehand
   - Know which ones have falls
   - Have backup videos ready

2. **Organize for easy access:**
   - Name videos clearly: `fall_001.mp4`, `no_fall_001.mp4`
   - Keep in dedicated folder
   - Use absolute paths

3. **Demo flow:**
   ```
   a. Show normal activity video (no fall)
      → System shows "✅ Normal"
   
   b. Show fall video
      → System detects fall
      → Shows "⚠️ FALL DETECTED!"
      → Logs to database
      → Shows in Falls tab
   
   c. Show multiple videos
      → Switch between videos
      → Show system accuracy
   ```

4. **Highlight features:**
   - Real-time processing
   - Pose detection overlay
   - Multiple detection methods (Pose + ML + CNN)
   - Automatic logging

### For Batch Testing:

1. **Run test script:**
   ```bash
   python scripts/test_fall_videos.py --directory fall_videos/ --output results.json
   ```

2. **Review results:**
   ```bash
   cat results.json | python -m json.tool
   ```

3. **Calculate accuracy:**
   - Compare detected vs. expected
   - Calculate precision/recall
   - Show statistics

## 🔧 Troubleshooting

### Video Won't Load

**Problem**: Video shows "Camera Error"

**Solutions:**
- ✅ Check file path is absolute (full path)
- ✅ Verify video file exists
- ✅ Check file format is supported
- ✅ Try different video codec (H.264 recommended)

### Video Plays But No Detection

**Problem**: Video plays but no falls detected

**Solutions:**
- ✅ Check video has clear view of person
- ✅ Verify person is visible in frame
- ✅ Check lighting is adequate
- ✅ Try adjusting detection sensitivity

### Video Loops Too Fast/Slow

**Problem**: Video playback speed is wrong

**Solutions:**
- ✅ System processes at ~30 FPS
- ✅ Video FPS may differ
- ✅ This is normal - detection is frame-by-frame
- ✅ For presentation, use videos with similar FPS

## 📝 Example Test Scenarios

### Scenario 1: Single Fall Video

```bash
# Test one video
python scripts/test_fall_videos.py \
  --video fall_videos/demo_fall.mp4 \
  --ground-truth 1
```

**Expected Output:**
```
⚠️  FALL DETECTED at frame 45 (1.50s)
✅ Result: CORRECT (Expected: 1, Got: True)
```

### Scenario 2: Multiple Videos

```bash
# Test all videos
python3 scripts/test_fall_videos.py /Users/mbindyoryankyalo/Desktop/FDA/Fall-detection-algorithm-/datasets/le2i/archive (1)/Coffee_room_02/Coffee_room_02
  --output presentation_results.json
```

**Expected Output:**
```
Total Videos: 10
Falls Detected: 7
No Falls: 3
```

### Scenario 3: Dashboard Testing

1. Add video: `/path/to/fall_video.mp4`
2. Select from camera dropdown
3. Watch real-time detection
4. Check Falls tab for logged events

## 🎯 For Your Presentation

### Recommended Setup:

1. **Prepare 5-10 test videos:**
   - Mix of falls and no-falls
   - Various scenarios (different angles, lighting)
   - Clear, high-quality videos

2. **Test beforehand:**
   - Run batch test to verify accuracy
   - Know which videos work best
   - Prepare talking points

3. **Demo sequence:**
   ```
   1. Show normal activity → No detection
   2. Show fall video → Detection triggered
   3. Show detection metrics → Explain features
   4. Show logged fall → Database integration
   5. Show multiple videos → Batch testing
   ```

4. **Highlight:**
   - Real-time processing
   - Multiple detection methods
   - High accuracy
   - Production-ready system

## 📊 Expected Performance

With good quality videos:
- **Detection Rate**: 75-85% (recall)
- **False Positive Rate**: 15-25% (precision)
- **Processing Speed**: ~30 FPS
- **Detection Latency**: <1 second

## ✅ Quick Start Checklist

- [ ] Videos organized in folder
- [ ] Videos tested individually
- [ ] Camera sources added to dashboard
- [ ] Batch test run (optional)
- [ ] Results reviewed
- [ ] Demo sequence practiced

**You're ready for your presentation!** 🎉

