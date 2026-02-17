# Quick Start Guide

## Generate Dummy Data

From the project root directory (`Fall-detection-algorithm-`):

```bash
cd /Users/mbindyoryankyalo/Desktop/FDA/Fall-detection-algorithm-
python3 scripts/generate_dummy_data.py
```

This will create:
- 4 doctors
- 4 caretakers  
- 12 patients
- 30 fall incidents
- 20 doctor reviews
- 10 file uploads with comments

## Test the Review System

1. **Start the Flask app:**
   ```bash
   python app_auth.py
   ```

2. **Login as Doctor:**
   - Go to "Review Falls" in sidebar
   - Review a fall → Add remarks and recommendations
   - Generate PDF report

3. **Login as Patient:**
   - View "My Recent Fall Events"
   - Click "View Review" to see doctor's remarks
   - Upload X-ray/scan file
   - View doctor's comments on uploaded files

4. **Login as Caretaker:**
   - View alerts for assigned patients
   - See doctor reviews
   - Upload files on behalf of patients

## Troubleshooting

If you get "can't open file" error:
- Make sure you're in the `Fall-detection-algorithm-` directory
- Check: `ls scripts/generate_dummy_data.py` should show the file

If database errors:
- The script will create the database if it doesn't exist
- Make sure you have write permissions

