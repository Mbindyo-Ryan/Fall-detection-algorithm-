# Fall Detection Dataset Guide - Video Only (No Sensors)

This guide focuses on **RGB video datasets only** - no sensor/IMU data. Perfect for our MediaPipe-based pose detection system.

---

## 🎯 Recommended Datasets (Video Only)

### 1. **UR Fall Detection Dataset** ⭐ (Best for Starters)

**What it is:**
- 30 fall videos + 40 ADL (Activities of Daily Living) videos
- Indoor environment, single camera view
- Clear labeling: falls vs. normal activities

**Download:**
- **Primary source:** https://www.sersc.org/journals/ijsh/vol11/12/5/
- **Alternative:** Search "UR Fall Detection Dataset" on Google Scholar
- **Direct link (if available):** Check ResearchGate or academic repositories

**Structure after extraction (PNG image sequences):**
```
urfd/
  falls/
    fall-01-cam0-rgb/  (directory with PNG images)
      frame_001.png
      frame_002.png
      ...
    fall-02-cam0-rgb/
      ...
    ... (30 sequences)
  adls/
    adl-01-cam0-rgb/  (directory with PNG images)
      frame_001.png
      frame_002.png
      ...
    adl-02-cam0-rgb/
      ...
    ... (40 sequences)
```

**Note:** UR dataset provides RGB data as PNG image sequences (not video files). Extract the RGB zip files to get folders of PNG images.

**Activities included:**
- Falls: Forward, backward, side falls
- ADLs: Walking, sitting, picking up objects, etc.

**Why it's good:**
- ✅ Well-structured
- ✅ Clear labels
- ✅ Good balance (falls vs. ADLs)
- ✅ Easy to process

---

### 2. **Le2i Fall Detection Dataset** ⭐⭐ (More Variety)

**What it is:**
- 191 videos total (fall + ADL)
- Multiple indoor environments
- Different camera angles and lighting conditions

**Download:**
- **Website:** https://sites.google.com/view/fall-detection-dataset
- **Direct:** https://www.rocq.inria.fr/fall-detection-dataset/
- **Alternative:** Search "Le2i Fall Detection Dataset"

**Structure:**
```
Le2i/
  Fall/
    Fall_Video_001.avi
    Fall_Video_002.avi
    ...
  NoFall/
    NoFall_Video_001.avi
    NoFall_Video_002.avi
    ...
```

**Activities included:**
- Falls: Various types
- ADLs: Walking, sitting, bending, crouching, lying down

**Why it's good:**
- ✅ Larger dataset
- ✅ More diverse scenarios
- ✅ Better for generalization

---

### 3. **Multiple Cameras Fall Dataset (MCFD)** ⭐⭐⭐ (Best Quality)

**What it is:**
- 24 fall scenarios + 24 ADL scenarios
- Recorded from 3 different camera angles
- High quality, well-annotated

**Download:**
- **Search:** "Multiple Cameras Fall Dataset" or "MCFD dataset"
- **Check:** IEEE Xplore, ResearchGate

**Activities:**
- Falls: Realistic fall scenarios
- ADLs: Walking, sitting, standing, picking objects, etc.

**Why it's good:**
- ✅ Multiple camera views (better for training)
- ✅ High quality videos
- ✅ Realistic scenarios

---

### 4. **Fall Detection Dataset (FDD)** - Simple & Clean

**What it is:**
- Small but clean dataset
- Good for quick testing
- Clear fall vs. ADL separation

**Download:**
- Search: "Fall Detection Dataset FDD" on GitHub or academic sites

---

## 📥 Step-by-Step Download Instructions

### For UR Fall Detection Dataset:

1. **Visit the paper:**
   - Go to: https://www.sersc.org/journals/ijsh/vol11/12/5/
   - Or search: "UR Fall Detection Dataset" on Google Scholar

2. **Find download link:**
   - Usually in "Supplementary Materials" or "Dataset" section
   - May require email registration (academic use)

3. **Download:**
   - Download the ZIP file (usually 100-500 MB)

4. **Extract:**
   ```bash
   mkdir -p datasets/urfd
   unzip downloaded_file.zip -d datasets/urfd
   ```

5. **Verify structure:**
   ```bash
   ls datasets/urfd/
   # Should see: falls/ and adls/ folders
   ```

### For Le2i Dataset:

1. **Visit:** https://sites.google.com/view/fall-detection-dataset

2. **Download:**
   - Click download link
   - May require form submission

3. **Extract:**
   ```bash
   mkdir -p datasets/le2i
   unzip downloaded_file.zip -d datasets/le2i
   ```

---

## 🎬 Activities Included in These Datasets

### Fall Activities:
- Forward fall
- Backward fall
- Side fall (left/right)
- Fall while walking
- Fall while sitting down

### ADL (Activities of Daily Living):
- ✅ **Walking** (normal pace)
- ✅ **Sitting down** on chair
- ✅ **Standing up** from chair
- ✅ **Bending down** to pick up object
- ✅ **Crouching**
- ✅ **Lying down** on bed/floor
- ✅ **Getting up** from lying position
- ✅ **Reaching** for objects
- ✅ **Standing still**
- ✅ **Turning around**

These ADLs are important because they can be confused with falls (e.g., lying down looks similar to a fall).

---

## 🚀 Using the Datasets with Our Script

### Process UR Fall Detection:
```bash
cd Fall-detection-algorithm-
python scripts/prepare_training_data.py --dataset urfd --output data/feature_logs.csv
```

### Process Le2i Dataset:
```bash
# First, organize Le2i into falls/ and adls/ folders if needed
python scripts/prepare_training_data.py --videos datasets/le2i/Fall --output data/feature_logs.csv
# Then process ADLs separately or combine
```

### Process Custom Videos:
```bash
# Create annotation template
python scripts/prepare_training_data.py --create-template

# Edit annotations_template.csv with your video labels
# Then process:
python scripts/prepare_training_data.py --videos path/to/videos --annotations annotations_template.csv --output data/feature_logs.csv
```

---

## 📊 Dataset Comparison

| Dataset | Videos | Falls | ADLs | Quality | Difficulty |
|---------|--------|-------|------|---------|------------|
| UR Fall | 70 | 30 | 40 | Good | Easy |
| Le2i | 191 | ~95 | ~96 | Good | Medium |
| MCFD | 48 | 24 | 24 | Excellent | Medium |
| FDD | ~50 | ~25 | ~25 | Good | Easy |

---

## 💡 Tips for Best Results

1. **Start with UR Fall Detection** - Easiest to get started
2. **Combine multiple datasets** - Better generalization
3. **Balance your data** - Aim for ~50% falls, ~50% ADLs
4. **Include diverse ADLs** - Especially ones that look like falls (lying down, crouching)
5. **Process at least 1000+ frames** - More data = better model

---

## 🔍 Where to Find These Datasets

### Academic Repositories:
- **IEEE Xplore** - Search paper titles
- **ResearchGate** - Often has dataset links
- **GitHub** - Search "fall detection dataset"
- **Google Scholar** - Find papers, check supplementary materials

### Direct Search Terms:
- "UR Fall Detection Dataset download"
- "Le2i fall detection dataset"
- "RGB fall detection dataset"
- "Video fall detection dataset"

---

## ⚠️ Important Notes

- **No sensor data needed** - We only use video frames
- **Look for RGB/AVI/MP4 files** - Not IMU/accelerometer data
- **Check license** - Most are for research/academic use
- **May require registration** - Some datasets require email signup

---

## 🎯 Quick Start Command

Once you have UR Fall Detection dataset:

```bash
# 1. Extract dataset to datasets/urfd/
# 2. Process it:
python scripts/prepare_training_data.py --dataset urfd --output data/feature_logs.csv

# 3. Train model:
pip install scikit-learn pandas joblib
python scripts/train_classifier.py --csv data/feature_logs.csv --model models/fall_classifier.pkl
```

---

## 📞 Need Help?

If you can't find a dataset:
1. Check the paper's supplementary materials
2. Email the authors (usually listed in paper)
3. Try alternative datasets (Le2i, MCFD)
4. Use your own videos with the annotation system

Good luck! 🚀

