# Installation Guide

## Prerequisites

Before installing the Autonomous Business Platform, ensure you have:

- **Python 3.11+** installed
- **Git** installed
- **8GB RAM minimum** (16GB recommended)
- **API Keys** ready:
  - [Replicate API Key](https://replicate.com/account/api-tokens) (required for AI models)
  - [Anthropic API Key](https://console.anthropic.com/) (optional, for Claude/Otto)
  - [OpenAI API Key](https://platform.openai.com/api-keys) (optional)

## Quick Install (Recommended)

### 1. Clone the Repository

```bash
git clone https://github.com/RhythrosaLabs/autonomous-business-platform.git
cd autonomous-business-platform
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API Keys

You can configure API keys in two ways:

#### Option A: Via UI (Easiest)
1. Run the app: `streamlit run autonomous_business_platform.py`
2. Open the sidebar
3. Click on "⚙️ Settings" 
4. Enter your API keys in the secure input fields

#### Option B: Environment Variables
Create a `.env` file:

```bash
# Required
REPLICATE_API_TOKEN=your_replicate_key_here

# Optional
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here
PRINTIFY_API_TOKEN=your_printify_key_here
SHOPIFY_ACCESS_TOKEN=your_shopify_key_here
```

### 4. Run the Application

```bash
streamlit run autonomous_business_platform.py
```

The app will open at `http://localhost:8501`

## Docker Install

### Using Docker Compose (Recommended)

```bash
docker-compose up -d
```

Access at `http://localhost:8501`

### Manual Docker

```bash
docker build -t autonomous-business-platform .
docker run -p 8501:8501 \
  -e REPLICATE_API_TOKEN=your_key \
  autonomous-business-platform
```

## Cloud Deployment

### Streamlit Cloud
1. Fork the repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Deploy from your forked repo
4. Add secrets in Streamlit dashboard

### Railway
[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/autonomous-business-platform)

### Render
1. Create new Web Service
2. Connect your GitHub repo
3. Set build command: `pip install -r requirements.txt`
4. Set start command: `streamlit run autonomous_business_platform.py`

## Verification

After installation, verify everything works:

1. **Check Dashboard** - Should load without errors
2. **Test Otto AI** - Type `/help` in the chat
3. **Generate Content** - Try creating an image in Content tab
4. **Check Integrations** - Verify API keys in Settings

## Next Steps

- [Configuration Guide](Configuration) - Set up your preferences
- [First Campaign](First-Campaign) - Generate your first campaign
- [Otto AI Guide](Otto-AI-Assistant) - Learn Otto's capabilities

## Troubleshooting

### Common Issues

**App won't start:**
```bash
# Check Python version
python --version  # Should be 3.11+

# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

**Import errors:**
```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +
```

**Ray errors:**
```bash
# Ray is optional for single-machine use
# Comment out Ray imports if having issues
```

Need help? Check [Common Issues](Common-Issues) or open an [issue](https://github.com/RhythrosaLabs/autonomous-business-platform/issues).
