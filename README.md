# Free Fire Bot Controller

A complete bot controller for Free Fire with multi-account support, auto-match making, and live dashboard.

## Features

- ✅ Multi-Account Support (Max 4 accounts)
- ✅ Auto Login to Free Fire
- ✅ Auto Guild Join
- ✅ Auto Group/Create Team
- ✅ Auto Match Start
- ✅ Auto Replay
- ✅ Live Bot Screens
- ✅ Match History
- ✅ Real-time Statistics
- ✅ Mobile View Emulation

## Deployment on Hugging Face Spaces

1. **Create a ZIP file** of all these files
2. **Go to** https://huggingface.co/new-space
3. **Select** "Docker" as Space SDK
4. **Upload** the ZIP file
5. **Set Environment Variables:**
   - `SECRET_KEY`: Your secret key
   - `FIREBASE_PRIVATE_KEY`: Your Firebase private key (if using)

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py