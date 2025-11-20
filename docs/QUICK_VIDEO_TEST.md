cd# Quick Video Testing Guide

## 🚀 Fastest Way to Test Videos (For Presentation)

### Step 1: Prepare Your Videos

1. Create a folder: `fall_videos/`
2. Place your test videos there:
   ```
   fall_videos/
     test_fall_1.mp4
     test_fall_2.mp4
     normal_activity.mp4
   ```

### Step 2: Add Videos to Dashboard

1. **Login** as patient
2. Go to **"My Cameras"** tab
3. Click **"Add Camera"**
4. Enter **absolute path** to video:
   ```
   /Users/mbindyoryankyalo/Desktop/FDA/Fall-detection-algorithm-/fall_videos/test_fall_1.mp4
   ```
5. Name it: "Test Fall Video 1"
6. Click **"Add Camera"**

### Step 3: Test Videos

1. **Select video** from camera dropdown
2. **Watch** real-time detection
3. **Check** "My History" tab for logged falls
4. **Switch** between videos easily

## 📝 Quick Commands

### Test Single Video (Command Line)
```bash
python scripts/test_fall_videos.py --video fall_videos/test.mp4 --ground-truth 1
```

### Test All Videos in Folder
```bash
python scripts/test_fall_videos.py --directory fall_videos/ --output results.json
```

## ✅ What to Expect

- **Video loops automatically** when it ends
- **Falls are detected** in real-time
- **Results logged** to database
- **Metrics displayed** on video feed

## 🎯 For Presentation

1. **Prepare 5-10 videos** (mix of falls and no-falls)
2. **Add them as cameras** in dashboard
3. **Switch between videos** during demo
4. **Show detection** in real-time
5. **Show logged results** in Falls tab

**That's it!** The system handles everything automatically. 🎉

