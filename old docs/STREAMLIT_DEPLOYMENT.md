# Streamlit Cloud Deployment Guide

## Changes Made for Streamlit Cloud Compatibility

### 1. Fixed Python Version
- Added `.python-version` file to force Python 3.11
- Streamlit Cloud was using Python 3.13 which has compatibility issues with many packages

### 2. Removed Non-Existent Packages
- **Removed**: `printify-python>=0.1.0` (doesn't exist on PyPI)
  - We use the local `printify.py` module instead
- **Commented out**: `ray[default]>=2.9.0` (causes deployment issues on Streamlit Cloud)
- **Commented out**: `rembg>=2.0.50` (Python 3.13 compatibility issues)

### 3. Added Fallback for Optional Features
- Background removal now has a fallback method when `rembg` is not available
- Ray features are already handled with conditional imports

### 4. System Dependencies
- Created `packages.txt` with required system packages:
  - `ffmpeg` - Video processing
  - `libsm6`, `libxext6`, `libxrender-dev` - OpenCV dependencies
  - `libgomp1` - Parallel processing support

## Deployment Steps

1. **Push changes to GitHub** ✅ (Already done)

2. **Redeploy on Streamlit Cloud**:
   - Go to your Streamlit Cloud dashboard
   - Click "Reboot app" or it will auto-redeploy on push

3. **Configure Secrets** (if not already done):
   - In Streamlit Cloud: App → Settings → Secrets
   - Add your `.env` variables in TOML format:
   ```toml
   REPLICATE_API_TOKEN = "your-token"
   ANTHROPIC_API_KEY = "your-key"
   OPENAI_API_KEY = "your-key"
   PRINTIFY_API_TOKEN = "your-token"
   SHOPIFY_ACCESS_TOKEN = "your-token"
   SHOPIFY_SHOP_URL = "your-shop.myshopify.com"
   # ... add all other env variables
   ```

4. **Wait for deployment** (3-5 minutes)

## What Features Are Affected?

### Still Work:
- ✅ All 34 tabs and core features
- ✅ AI model integration (Replicate)
- ✅ Image generation and editing
- ✅ Video generation (via Replicate)
- ✅ Printify and Shopify integration
- ✅ Social media posting
- ✅ Otto AI assistant
- ✅ Campaign generation
- ✅ Browser automation (with Playwright)
- ✅ Background removal (using fallback method)

### Limited:
- ⚠️ **Ray distributed computing**: Commented out for Streamlit Cloud
  - The app will work without Ray, just won't use distributed processing
  - For Ray features, deploy with Docker instead
- ⚠️ **Advanced background removal**: Using built-in transparency method
  - `rembg` commented out due to Python version conflicts
  - Still functional, just slightly less sophisticated

## Alternative Deployment Options

If you need Ray or other advanced features, consider:

1. **Docker Deployment** (Railway, Render, Fly.io):
   ```bash
   docker-compose up
   ```
   - Full feature support including Ray
   - See `README.md` for Docker deployment instructions

2. **Local Development**:
   ```bash
   pip install -r requirements.txt
   streamlit run autonomous_business_platform.py
   ```

## Troubleshooting

### If deployment still fails:

1. **Check Python version in Streamlit Cloud**:
   - Should show Python 3.11.x in logs
   - If not, `.python-version` file may not be recognized

2. **Check for missing secrets**:
   - Some tabs may fail if API keys are not configured
   - This is expected - configure secrets for features you need

3. **Check terminal output**:
   - Streamlit Cloud → Manage App → View logs
   - Look for import errors or missing dependencies

4. **Minimal deployment** (if still issues):
   - Further reduce requirements.txt to only essential packages
   - Comment out browser-use and playwright if not needed

## GitHub Repository
https://github.com/RhythrosaLabs/autonomous-business-platform
