# ⚡ Quick Start Guide - Absolute Beginner Edition

**Goal:** Get the platform running in under 10 minutes

---

## Step 1: Install Python (if you don't have it)

**Mac/Linux:**
```bash
# Check if you already have Python 3.11+
python3 --version

# If version is less than 3.11, install it:
# Mac: brew install python@3.11
# Linux: sudo apt install python3.11 python3.11-venv
```

**Windows:**
- Download from [python.org](https://www.python.org/downloads/)
- ✅ Check "Add Python to PATH" during installation

---

## Step 2: Download the Platform

```bash
# Open terminal and run:
git clone https://github.com/RhythrosaLabs/autonomous-business-platform.git
cd autonomous-business-platform
```

**Don't have git?**
- Download ZIP from GitHub → Extract → Open terminal in that folder

---

## Step 3: Set Up Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # Mac/Linux
# OR
venv\Scripts\activate     # Windows

# You should see (venv) in your terminal prompt now
```

---

## Step 4: Install Dependencies

```bash
# This takes 2-3 minutes - be patient!
pip install -r requirements.txt
```

**If you get errors:**
- Make sure you're in the `autonomous-business-platform` folder
- Make sure `(venv)` shows in your terminal
- Try: `pip install --upgrade pip` then retry

---

## Step 5: Configure API Keys

```bash
# Copy the example file
cp .env.example .env

# Edit it (use any text editor)
nano .env  # or: code .env  # or: open .env
```

**Minimum Required** (get FREE trial keys):
1. **Replicate** → https://replicate.com/account/api-tokens
   - Sign up → Copy token → Paste in `.env` next to `REPLICATE_API_TOKEN=`

2. **Anthropic (Claude)** → https://console.anthropic.com/
   - Sign up → Copy API key → Paste next to `ANTHROPIC_API_KEY=`

**Optional** (add later if needed):
- Printify (for product mockups)
- Shopify (for e-commerce)
- Other social media APIs

**Save and close the file!**

---

## Step 6: Launch the Platform 🚀

### Option A: Simple Launch (Recommended for First Test)

```bash
# Just run the Streamlit app - perfect for testing!
streamlit run autonomous_business_platform.py
```

**What you get:**
- ✅ Full Streamlit UI (all tabs, all features)
- ✅ API validation test buttons
- ✅ Campaign generation works
- ⚠️ No parallel processing (slower for batch operations)
- ⚠️ No background job queue

**You'll see:**
```
  You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
```

**Open that URL in your browser!** 🎉

### Option B: Full Launch (Backend + Ray + Frontend) - Recommended for Production

```bash
cd scripts
./start_platform.sh
```

**What you get:**
- ✅ Everything from Option A
- ✅ FastAPI backend (async job processing)
- ✅ Ray distributed computing (7x faster campaigns)
- ✅ Background job queue
- ✅ Advanced monitoring dashboard

**Access:**
- Frontend (UI): http://localhost:8501
- API Docs: http://localhost:8000/docs
- Ray Dashboard: http://localhost:8265

**When to use Full Launch:**
- 📦 Batch processing (hundreds of products/campaigns)
- 🚀 Need maximum speed (7x faster with Ray parallelization)
- 🔄 Long-running background jobs
- 💼 Production deployment

**For your first test, stick with Option A!** ✨

---

## Step 7: Test Your Setup ✅

1. **Open** http://localhost:8501 in browser

2. **Click sidebar** → Settings → 🔑 API Keys

3. **Test your APIs:**
   - Click "🔌 Test" button next to Replicate
   - Click "🔌 Test" button next to Anthropic
   - You should see ✅ green success messages!

4. **If tests fail:**
   - Double-check your API keys in `.env`
   - Make sure there are no spaces before/after the key
   - Restart: `Ctrl+C` then `streamlit run autonomous_business_platform.py` again

---

## 🎯 What to Do Next

### Try Creating Your First Campaign:

1. Go to **🎯 Campaign Creator** tab
2. Fill in:
   - **Product Name**: "Cosmic Galaxy T-Shirt"
   - **Description**: "Vibrant space-themed tee with nebula design"
   - **Target Audience**: "Sci-fi fans, space enthusiasts"
3. Click **🚀 Generate Complete Campaign!**
4. Watch the magic happen! ✨

### Explore Other Features:

- **🤖 Otto AI**: Chat with your AI assistant (type `/help` for commands)
- **🛍️ Products**: Connect Printify/Shopify for real products
- **🎨 Content Generator**: Create images, videos, music with 100+ AI models
- **📧 Email Marketing**: Design and send email campaigns

---

## 🆘 Common Issues & Fixes

### "Module not found" error
```bash
# Make sure venv is activated (you see (venv) in prompt)
source venv/bin/activate
pip install -r requirements.txt
```

### "Port already in use"
```bash
# Kill existing Streamlit process
pkill -f streamlit
# Then relaunch
streamlit run autonomous_business_platform.py
```

### "API key invalid"
- Get fresh keys from Replicate/Anthropic
- Make sure `.env` file is in the root folder (same folder as `autonomous_business_platform.py`)
- No spaces: `REPLICATE_API_TOKEN=r8_abc123` not `REPLICATE_API_TOKEN = r8_abc123`

### Tests show ❌ but keys are correct
- Check your internet connection
- Try the "🔌 Test All Connections" button
- Check API service status pages

---

## 🎓 Video Tutorial (Coming Soon)
Watch step-by-step setup: [Link will be added]

---

## 💬 Need Help?

- **Issues**: https://github.com/RhythrosaLabs/autonomous-business-platform/issues
- **Discussions**: Use GitHub Discussions tab
- **Documentation**: See full [README.md](README.md)

---

## ✅ Success Checklist

- [ ] Python 3.11+ installed
- [ ] Repository cloned/downloaded
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created with API keys
- [ ] Platform launched (`streamlit run autonomous_business_platform.py`)
- [ ] Browser opened to http://localhost:8501
- [ ] API tests show ✅ green checkmarks
- [ ] First campaign generated successfully

**If all checked, you're ready to automate your business! 🚀**
