# Configuration Guide

This guide covers all configuration options for the Autonomous Business Platform.

## 📁 Configuration Files

### Environment Variables (.env)
Create a `.env` file in the root directory:

```bash
# Required API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
REPLICATE_API_TOKEN=r8_...

# Optional API Keys
GOOGLE_API_KEY=AIza...
STABILITY_API_KEY=sk-...
HUGGINGFACE_TOKEN=hf_...
ELEVENLABS_API_KEY=...
SUNO_API_KEY=...

# Platform Integrations
SHOPIFY_API_KEY=...
SHOPIFY_API_SECRET=...
SHOPIFY_STORE_URL=your-store.myshopify.com

PRINTIFY_API_TOKEN=...
PRINTIFY_SHOP_ID=...

# Social Media
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_SECRET=...

FACEBOOK_PAGE_ID=...
FACEBOOK_ACCESS_TOKEN=...

INSTAGRAM_BUSINESS_ID=...
INSTAGRAM_ACCESS_TOKEN=...

# Email & Marketing
SENDGRID_API_KEY=...
MAILCHIMP_API_KEY=...

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
REDIS_URL=redis://localhost:6379

# Application Settings
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=localhost
STREAMLIT_SERVER_HEADLESS=true
ENABLE_DEMO_MODE=false
LOG_LEVEL=INFO
```

### Streamlit Secrets (Cloud Deployment)

For Streamlit Cloud, add secrets in the dashboard:

```toml
# .streamlit/secrets.toml

[api_keys]
openai = "sk-..."
anthropic = "sk-ant-..."
replicate = "r8_..."

[shopify]
api_key = "..."
api_secret = "..."
store_url = "your-store.myshopify.com"

[printify]
api_token = "..."
shop_id = "..."

[social]
twitter_api_key = "..."
twitter_api_secret = "..."
facebook_page_id = "..."
instagram_business_id = "..."

[database]
url = "postgresql://..."
```

## 🔑 API Key Configuration

### Method 1: UI Configuration (Recommended)

1. Launch the application
2. Navigate to **Settings** → **API Configuration**
3. Enter your API keys in the secure form
4. Keys are encrypted and stored in session state
5. Enable **Demo Mode** if sharing your deployment

**Demo Mode Features:**
- Hides actual API keys from viewers
- Allows testing without exposing credentials
- Each user enters their own keys
- Keys are session-specific (not persisted)

### Method 2: Environment Variables

```bash
# Linux/macOS
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-..."
$env:ANTHROPIC_API_KEY="sk-ant-..."

# Windows (CMD)
set OPENAI_API_KEY=sk-...
set ANTHROPIC_API_KEY=sk-ant-...
```

### Method 3: .env File

Create `.env` in project root:
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
REPLICATE_API_TOKEN=r8_...
```

Load automatically with:
```python
from dotenv import load_dotenv
load_dotenv()
```

## 🎨 Brand Configuration

### Brand Templates

Edit `brand_templates.json`:

```json
{
  "brand_name": "Your Brand",
  "tagline": "Your memorable tagline",
  "brand_voice": "friendly, professional, innovative",
  "target_audience": "millennials, 25-40, tech-savvy",
  
  "colors": {
    "primary": "#3498db",
    "secondary": "#2ecc71",
    "accent": "#e74c3c",
    "background": "#ecf0f1",
    "text": "#2c3e50"
  },
  
  "typography": {
    "heading_font": "Montserrat",
    "body_font": "Open Sans",
    "heading_weight": "bold",
    "body_weight": "normal"
  },
  
  "logo": {
    "primary_url": "https://...",
    "icon_url": "https://...",
    "watermark_url": "https://..."
  },
  
  "social_handles": {
    "twitter": "@yourbrand",
    "instagram": "@yourbrand",
    "facebook": "yourbrand",
    "tiktok": "@yourbrand"
  },
  
  "content_guidelines": {
    "tone": ["conversational", "inspiring", "authentic"],
    "avoid": ["jargon", "negativity", "excessive emoji"],
    "hashtags": ["#yourbrand", "#sustainable", "#innovation"],
    "emojis": ["✨", "🌟", "💚", "🚀"]
  }
}
```

### Using Brand Templates

```python
from app.services.brand_brain import BrandBrain

brain = BrandBrain()
brand = brain.get_brand_profile()

# Generate branded content
post = brain.generate_social_post(
    product="Eco Water Bottle",
    platform="instagram"
)
# Output uses brand voice, colors, hashtags
```

## 🏪 E-commerce Integration

### Shopify Setup

1. **Create Private App:**
   - Go to Shopify Admin → Apps → Develop apps
   - Create new app
   - Configure Admin API scopes:
     - `read_products`, `write_products`
     - `read_orders`, `write_orders`
     - `read_inventory`, `write_inventory`
   - Copy API key and Admin API access token

2. **Configure in App:**
   ```python
   # In Settings → Integrations → Shopify
   store_url = "your-store.myshopify.com"
   api_key = "..."
   api_secret = "..."
   ```

3. **Test Connection:**
   ```python
   from app.services.shopify_service import ShopifyService
   
   shopify = ShopifyService()
   products = shopify.list_products()
   print(f"Connected! Found {len(products)} products")
   ```

### Printify Setup

1. **Get API Token:**
   - Go to Printify Dashboard
   - Navigate to **Connections** → **API**
   - Generate Personal Access Token

2. **Get Shop ID:**
   - In Printify, go to **My Shops**
   - Copy Shop ID (numerical value)

3. **Configure:**
   ```python
   # In Settings → Integrations → Printify
   api_token = "..."
   shop_id = "12345678"
   ```

4. **Test:**
   ```python
   from app.services.printify import PrintifyService
   
   printify = PrintifyService()
   catalog = printify.get_catalog()
   print(f"Available products: {len(catalog)}")
   ```

## 📱 Social Media Integration

### Twitter/X Setup

1. **Create Developer Account:**
   - Go to developer.twitter.com
   - Apply for Elevated access
   - Create new app

2. **Get Credentials:**
   - API Key and Secret (OAuth 1.0a)
   - Access Token and Secret
   - Copy all 4 values

3. **Configure:**
   ```bash
   TWITTER_API_KEY=...
   TWITTER_API_SECRET=...
   TWITTER_ACCESS_TOKEN=...
   TWITTER_ACCESS_SECRET=...
   ```

### Facebook/Instagram Setup

1. **Create Meta App:**
   - Go to developers.facebook.com
   - Create new app → Business type
   - Add Instagram Graph API

2. **Get Page Access Token:**
   - Use Graph API Explorer
   - Select your page
   - Generate long-lived token

3. **Configure:**
   ```bash
   FACEBOOK_PAGE_ID=...
   FACEBOOK_ACCESS_TOKEN=...
   INSTAGRAM_BUSINESS_ID=...
   INSTAGRAM_ACCESS_TOKEN=...
   ```

## 🤖 AI Model Configuration

### Model Selection

Configure in `app/services/ai_model_manager.py`:

```python
AI_MODELS = {
    "chat": {
        "default": "claude-3.5-sonnet",
        "fast": "gpt-3.5-turbo",
        "advanced": "gpt-4-turbo"
    },
    "image": {
        "default": "flux-schnell",
        "quality": "flux-dev",
        "fast": "sdxl-turbo"
    },
    "video": {
        "default": "runway-gen2",
        "advanced": "pika"
    }
}
```

### Model Parameters

```python
# Chat Models
CHAT_CONFIG = {
    "temperature": 0.7,  # 0.0 = deterministic, 1.0 = creative
    "max_tokens": 4096,
    "top_p": 0.9,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0
}

# Image Models
IMAGE_CONFIG = {
    "num_inference_steps": 30,
    "guidance_scale": 7.5,
    "width": 1024,
    "height": 1024,
    "num_outputs": 1
}

# Video Models
VIDEO_CONFIG = {
    "fps": 24,
    "duration": 3,  # seconds
    "resolution": "1080p"
}
```

## 💾 Database Configuration

### PostgreSQL Setup

```bash
# Install PostgreSQL
brew install postgresql  # macOS
sudo apt install postgresql  # Ubuntu

# Create database
createdb autonomous_platform

# Configure connection
DATABASE_URL=postgresql://user:password@localhost:5432/autonomous_platform
```

### Redis Setup (Optional - for caching)

```bash
# Install Redis
brew install redis  # macOS
sudo apt install redis  # Ubuntu

# Start Redis
redis-server

# Configure
REDIS_URL=redis://localhost:6379
```

## 📧 Email Configuration

### SendGrid Setup

1. Create account at sendgrid.com
2. Generate API key
3. Verify sender email
4. Configure:

```python
SENDGRID_API_KEY=SG...
FROM_EMAIL=your-email@domain.com
FROM_NAME=Your Brand
```

### SMTP Configuration (Alternative)

```python
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## 🔒 Security Configuration

### Enable Authentication

```python
# config/security.py
ENABLE_AUTH = True
AUTH_METHOD = "streamlit"  # or "oauth", "ldap"

# Simple password protection
ADMIN_PASSWORD = "your-secure-password"
```

### Rate Limiting

```python
# Prevent API abuse
RATE_LIMITS = {
    "chat": "60/hour",
    "image": "30/hour",
    "video": "10/hour"
}
```

### IP Whitelist

```python
# Restrict access to specific IPs
ALLOWED_IPS = [
    "192.168.1.0/24",
    "10.0.0.1"
]
```

## 🎯 Performance Configuration

### Caching

```python
# Enable aggressive caching
CACHE_CONFIG = {
    "enable": True,
    "ttl": 3600,  # seconds
    "max_size": 1000  # entries
}
```

### Parallel Processing

```python
# Ray configuration for distributed processing
RAY_CONFIG = {
    "num_cpus": 4,
    "num_gpus": 0,
    "memory": 8 * 1024**3  # 8GB
}
```

### Image Optimization

```python
IMAGE_OPTIMIZATION = {
    "compress_uploads": True,
    "max_dimension": 2048,
    "quality": 85,
    "format": "webp"
}
```

## 📊 Logging Configuration

```python
# config/logging.py
LOGGING = {
    "version": 1,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO"
        },
        "file": {
            "class": "logging.FileHandler",
            "filename": "logs/app.log",
            "level": "DEBUG"
        }
    },
    "loggers": {
        "app": {
            "handlers": ["console", "file"],
            "level": "INFO"
        }
    }
}
```

## 🧪 Development Configuration

### Debug Mode

```python
# Enable detailed error messages
DEBUG = True
STREAMLIT_SERVER_ENABLE_STATIC_SERVING = True
STREAMLIT_LOGGER_LEVEL = "debug"
```

### Hot Reload

```bash
# Auto-reload on file changes
streamlit run autonomous_business_platform.py --server.runOnSave true
```

## 🚀 Production Configuration

### Optimize for Production

```python
# .streamlit/config.toml
[server]
port = 8501
enableCORS = false
enableXsrfProtection = true
maxUploadSize = 200

[browser]
gatherUsageStats = false
serverAddress = "your-domain.com"

[theme]
primaryColor = "#3498db"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
```

### Docker Configuration

```dockerfile
# Dockerfile optimization
FROM python:3.11-slim

# Performance
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLE_CORS=false

# Security
RUN useradd -m -u 1000 appuser
USER appuser
```

## 🔧 Troubleshooting

**API keys not working:**
```python
# Check if loaded correctly
import os
print(os.getenv('OPENAI_API_KEY'))  # Should print your key
```

**Database connection issues:**
```bash
# Test PostgreSQL connection
psql $DATABASE_URL
```

**Slow performance:**
```python
# Enable caching
import streamlit as st

@st.cache_data
def expensive_function():
    # Your code here
    pass
```

---

**Need help?** Check the [Troubleshooting Guide](Common-Issues) or [FAQ](FAQ)
