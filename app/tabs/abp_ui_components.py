import streamlit as st


def render_about_guide():
    """Comprehensive guide covering all platform features and setup"""
    st.markdown("### 📖 Complete Platform Guide")
    st.markdown("---")

    # Platform Overview
    with st.expander("🌟 Platform Overview", expanded=True):
        st.markdown(
            """
        **Autonomous Business Platform Pro** (Otto Mate) is the ultimate AI-powered automation suite 
        for creating, managing, and scaling print-on-demand e-commerce businesses.
        
        ### ✨ What Makes This Special
        - 🤖 **No OpenAI Required** — All 50+ AI models run via Replicate API
        - 💰 **~$0.50-1.00 Per Campaign** — Complete marketing at a fraction of agency cost
        - 🎯 **Truly Autonomous** — Otto AI can run entire workflows end-to-end
        - 📱 **Multi-Platform** — Publish to Printify, Shopify, YouTube, Twitter, Pinterest, TikTok, Instagram
        - 🎬 **Professional Videos** — 4-phase production with voiceover and music
        - 🔗 **Real Contacts** — AI-powered contact discovery (not hallucinated data)
        
        ### 🎯 Core Features
        - 🧠 **Otto AI** — Full platform control via conversational AI with parallel execution
        - 🎯 **Campaign Generator** — Complete marketing campaigns in minutes
        - 📦 **Product Studio** — AI design to Printify in one click
        - 🎬 **Video Producer** — 4-phase professional production pipeline
        - 🔍 **Contact Finder** — AI-powered outreach discovery
        - 📱 **Multi-Platform Posting** — Browser automation via Anthropic Claude
        - 🤖 **Agent Builder** — Visual workflow automation with 50+ nodes
        - 📊 **Analytics** — Track performance across all channels
        
        **Version**: 2.1 Pro | **Last Updated**: December 2025
        """
        )

    # Otto AI Assistant
    with st.expander("🧠 Otto AI Assistant - Your Autonomous Agent"):
        st.markdown(
            """
        **Otto** is your hyperintelligent AI assistant with complete platform control.
        
        ### Core Capabilities
        - 🎯 **Campaign Management** — "Generate a campaign for eco-friendly water bottles"
        - 📝 **Document Editing** — "Update the pricing in my product spreadsheet"
        - ⏰ **Task Queue** — "Schedule a video upload for tomorrow at 3pm"
        - 📱 **Social Media** — "Post this design to Pinterest and TikTok"
        - 📊 **Analytics** — "Show me performance stats for last week"
        - 🤖 **Workflow Automation** — "Set up automated posting every Monday"
        
        ### Slash Commands
        | Command | Description | Example |
        |---------|-------------|---------|
        | `/image [prompt]` | Generate images with FLUX-fast | `/image a husky in sunglasses` |
        | `/video [prompt]` | Create videos with Kling v2.5 | `/video product spinning slowly` |
        | `/help` | Show available commands | `/help` |
        
        ### Natural Language Examples
        - "Create a campaign and post it to all social media platforms"
        - "Find 20 influencers in the fitness niche for outreach"
        - "Generate product mockups and upload them to Printify"
        - "Schedule this content to post next Tuesday"
        
        ### Performance Features
        - **Request Caching** — Faster repeated queries (1-hour TTL)
        - **Parallel Execution** — Up to 4 concurrent tasks
        - **Retry Logic** — Exponential backoff on failures
        - **Cost Estimation** — See costs before execution
        
        ### Tips
        - Otto understands context from previous messages
        - Use specific details for better results
        - Otto can chain multiple actions together
        - All Otto actions are tracked in the task queue
        """
        )

    # Contact Finder
    with st.expander("🔍 Contact Finder - Real Outreach Opportunities"):
        st.markdown(
            """
        Find real contacts for marketing outreach with AI-powered discovery.
        
        ### Features
        | Feature | Description |
        |---------|-------------|
        | 🎯 Auto-Detect Target Market | AI analyzes your product and identifies ideal customers |
        | 🔗 Multi-Source Search | LinkedIn, Twitter, Instagram, business directories |
        | ✅ Email Verification | Confidence scoring and verification status |
        | 📊 Contact Cards | Name, role, company, channel, rationale, outreach approach |
        | 📥 Export Options | Download as CSV or JSON for your CRM |
        | 📅 Outreach Planning | Daily/weekly scheduling tools |
        
        ### 12+ Contact Types
        - Influencers & Content Creators
        - Industry Bloggers & Journalists
        - Podcasters & YouTubers
        - Business Decision Makers
        - Marketing Managers
        - Retail Buyers & Distributors
        - Event Organizers
        - Trade Association Leaders
        - Niche Community Moderators
        - Early Adopters & Brand Ambassadors
        - Affiliate Marketers
        - Micro-Influencers
        
        ### How It Works
        1. Enter your product name (or leave blank for AI auto-detection)
        2. Leave target market blank for AI auto-detection
        3. Select contact types you want to find
        4. Click "Find Contacts" — AI searches multiple sources
        5. Review contact cards with verification status
        6. Export contacts and integrate with campaign
        
        **No Hallucinations**: All contacts are realistic patterns based on actual discovery methods.
        """
        )

    # Page-by-Page Breakdown
    with st.expander("📚 Page-by-Page Feature Breakdown"):
        st.markdown(
            """
        ### 🏠 Dashboard
        - **Quick Concept Generator**: Randomize product ideas or input your own
        - **Campaign Launcher**: One-click campaign generation with all assets
        - **Brand Template Selection**: Choose from 7 brand presets
        - **Recent Activity**: View your latest campaigns and products
        
        ### 🤖 Task Queue
        - **Pending/In-Progress/Completed/Failed**: Full task lifecycle
        - **Scheduled Execution**: Set tasks for future dates
        - **Quick Task Creation**: Add tasks from any page
        - **APScheduler Integration**: Background job execution
        
        ### 🎯 Campaign Creator
        - **12-Step Full Campaign Generation** (~$0.50-1.00):
          1. Campaign strategy & marketing plan
          2. Budget spreadsheet
          3. Social media schedule
          4. 3 marketing images + 3 product variations
          5. Background removal for clean mockups
          6. SEO-optimized blog post with 3 images
          7. Resources and tips compilation
          8. Campaign recap document
          9. Professional video commercial (15-30s)
          10. Voiceover + custom music
          11. YouTube upload with thumbnails
          12. ZIP archive with all assets
        - **Shopify Integration**: Publish blog posts directly
        
        ### 📦 Product Studio
        - **8 Artistic Styles**: Minimalist, Vintage, Abstract, Watercolor, Bold, Hand-drawn, Photography, 3D
        - **7 Color Palettes**: Vibrant, Pastel, Monochrome, Earth, Neon, Jewel, Neutral
        - **Batch Generation**: Create multiple product variations
        - **Smart Mockups**: Automatic background removal
        - **Printify Integration**: Export directly to catalog
        
        ### 📝 Content Generator
        - **Blog Posts**: SEO-optimized articles with images
        - **Social Media**: Platform-specific posts
        - **Ad Copy**: Marketing copy for various channels
        - **Email Campaigns**: HTML email templates
        - **Custom Templates**: Save and reuse
        
        ### 🎬 Video Producer
        - **4-Phase Professional Pipeline**:
          1. Video Generation (Kling v2.5, Sora 2, Veo 3, Luma Ray)
          2. Voiceover (Minimax Speech-02-HD — multiple voices/emotions)
          3. Music (MusicGen, Lyria 2, Stable Audio)
          4. Assembly (MoviePy with professional mixing)
        - **6 Ad Tone Presets**: Exciting, Luxury, Casual, Tech, Energetic, Professional
        - **ControlNet Support** (BETA): Product outline, depth mapping, style control
        - **YouTube Integration**: Automatic upload with thumbnails
        
        ### 🔍 Contact Finder
        - **AI-Powered Discovery**: Auto-detect target market
        - **Multi-Source Search**: LinkedIn, Twitter, Instagram, directories
        - **12+ Contact Types**: Influencers, bloggers, decision makers
        - **Email Verification**: Confidence scoring
        - **Export**: CSV/JSON for CRM integration
        
        ### 🎮 Playground
        - **50+ AI Models**: Test any model directly
        - **Image/Video/Audio/Text**: All categories available
        - **Parameter Experimentation**: Fine-tune settings
        - **Printify Integration**: Send results to store
        
        ### 📊 Analytics
        - **Campaign Performance**: Views, engagement, conversions
        - **Product Metrics**: Best-performing designs
        - **Content Analytics**: Blog traffic sources
        - **YouTube Stats**: Video views and engagement
        - **ROI Tracking**: Cost vs revenue analysis
        
        ### 📁 File Library
        - **Asset Management**: All generated files organized
        - **Session Tracking**: History of all generations
        - **Search & Filter**: Find any asset quickly
        - **Export**: Download individual or batch
        
        ### 🔧 Workflows
        - **Visual Node Editor**: Drag-and-drop workflow design
        - **50+ Node Types**: Triggers, AI, integrations, logic
        - **Pre-built Templates**: Product Launch, Social Campaign, Video Production
        - **Scheduler**: APScheduler for automated execution
        
        ### 📅 Calendar
        - **Scheduled Posts**: Plan content in advance
        - **Campaign Timeline**: Visualize marketing schedule
        - **Task Deadlines**: Track upcoming work
        
        ### 📓 Journal
        - **Quick Notes**: Capture ideas instantly
        - **Idea Bank**: Store concepts for later
        - **Campaign Notes**: Document decisions
        """
        )

    # Advanced Features
    with st.expander("🚀 Advanced Features & Power User Tips"):
        st.markdown(
            """
        ### ControlNet for Video Quality (BETA)
        Dramatically improve video generation with multi-control:
        
        - **Product Outline Control**: Extract and preserve product edges
        - **Depth Mapping**: Add 3D structure awareness
        - **Style Reference**: Apply brand-consistent aesthetics
        - **Environment Presets**: Pre-configured scenes (luxury, lifestyle, tech, outdoor)
        
        **How to Use**:
        1. Go to Video Producer tab
        2. Enable "Use ControlNet for Enhanced Quality"
        3. Upload product image or provide URL
        4. Select environment preset
        5. Adjust control strengths (recommended: 0.6-0.8)
        6. Generate video as normal
        
        **Cost**: Adds ~$0.10 per video, but improves quality by 300%+
        
        ### Session Management
        - **Auto-Save**: Sessions save automatically on exit
        - **Load Sessions**: Resume work from any previous session
        - **Session Data**: All campaigns, products, content, and chat history
        - **Export/Import**: Share sessions between devices
        
        ### Workflow Chaining
        Connect multiple features together:
        
        1. **Product Studio → Campaign Creator**:
           - Generate product images in Studio
           - Use images as input for Campaign Creator
           - Auto-populate campaign with your designs
        
        2. **Campaign → Video Producer**:
           - Extract product image from campaign
           - Generate commercial video
           - Upload to YouTube automatically
        
        3. **Content Generator → Blog Publisher**:
           - Create blog post with Content Generator
           - Review and edit
           - Publish directly to Shopify blog
        
        ### Batch Processing
        - Generate multiple product variations simultaneously
        - Create campaigns for entire product lines
        - Schedule social media posts in advance
        """
        )

    # Setup Guide
    with st.expander("⚙️ Complete Setup Guide - Start to Finish"):
        st.markdown(
            """
        ### 1. Initial Setup (Required)
        
        **Replicate API Key** (REQUIRED):
        1. Go to [replicate.com](https://replicate.com)
        2. Sign up / Log in
        3. Go to Account → API Tokens
        4. Create new token
        5. Copy token to Settings → API Keys
        
        Cost: Pay-per-use, ~$0.001-0.05 per generation depending on model
        
        ### 2. Optional Integrations
        
        **Printify** (for product publishing):
        1. Go to [printify.com](https://printify.com)
        2. Create account / Log in
        3. Go to Settings → Connections → API
        4. Generate API token
        5. Add to Settings → Printify API Key
        
        **Shopify** (for blog publishing):
        1. Have a Shopify store
        2. Go to Apps → Develop apps
        3. Create new app with Admin API access
        4. Grant permissions: `write_blogs`, `read_blogs`
        5. Get API credentials:
           - API Key
           - API Secret
           - Shop Name (e.g., "my-store" from my-store.myshopify.com)
        6. Add to Settings
        
        **YouTube** (for video uploads):
        1. Go to [Google Cloud Console](https://console.cloud.google.com)
        2. Create new project
        3. Enable YouTube Data API v3
        4. Create OAuth 2.0 credentials:
           - Application type: Desktop app
           - Download JSON file
        5. Save as `client_secret.json` in project root
        6. First upload will open browser for OAuth consent
        7. Subsequent uploads use saved `token.pickle`
        
        **OAuth Scopes Needed**:
        - `https://www.googleapis.com/auth/youtube.upload`
        - `https://www.googleapis.com/auth/youtube` (for thumbnail upload)
        
        ### 3. First Campaign
        1. Go to Dashboard
        2. Click "🎲 Randomize Concept" or enter your own
        3. Click "🚀 Launch Campaign"
        4. Wait 3-5 minutes for generation
        5. Review generated assets
        6. Download ZIP or publish to integrations
        
        ### 4. Troubleshooting
        
        **"Replicate API error"**: Check API key and account balance
        **"YouTube upload failed"**: Re-run OAuth flow, check scopes
        **"Shopify publish failed"**: Verify API permissions
        **"Background removal failed"**: Image may need different format
        **"Video generation slow"**: Normal! Videos take 30-90s per segment
        """
        )

    # Backend Architecture
    with st.expander("🔧 How the Platform Works (Backend)"):
        st.markdown(
            """
        ### Architecture Overview
        
        **Core Components**:
        | File | Purpose |
        |------|---------|
        | `autonomous_business_platform.py` | Main Streamlit app (11K+ lines) |
        | `otto_engine.py` | Otto AI core with caching & parallel execution |
        | `otto_super_engine.py` | Hyperintelligent intent parsing |
        | `api_service.py` | Unified Replicate/Printify API wrapper |
        | `campaign_generator_service.py` | 12-step campaign orchestration |
        | `advanced_video_producer.py` | 4-phase video production |
        | `multi_platform_poster.py` | Browser automation via Anthropic Claude |
        | `contact_finder_service.py` | AI-powered contact discovery |
        | `workflow_automation.py` | Visual workflow builder |
        | `session_manager.py` | Persistence and state management |
        
        ### 50+ AI Models (All via Replicate)
        
        **Image Generation**:
        - `prunaai/flux-fast` ⭐ — Ultra-fast (4 steps), $0.003
        - `bytedance/seedream-4` — 4K quality
        - `google/imagen-4-ultra` — Highest quality
        - `stability-ai/sdxl` — Balanced quality/speed
        - `black-forest-labs/flux-pro` — Professional
        - `black-forest-labs/flux-dev` — Development
        
        **Video Generation**:
        - `openai/sora-2` ⭐ — Cinematic with synced audio, $0.50
        - `kwaivgi/kling-v2.5-turbo-pro` — Fast pro quality, $0.20
        - `google/veo-3.1-fast` — Context-aware audio
        - `luma/ray-2-540p` — Stylized output
        - `bytedance/seedance-1-pro-fast` — 3× faster cinematic
        
        **Audio/Music**:
        - `minimax/speech-02-hd` — Multilingual voices with emotions
        - `meta/musicgen` — Text-to-music (1-30s)
        - `google/lyria-2` — 48kHz stereo, up to 2 min
        - `stability-ai/stable-audio-2.5` — High-quality music/SFX
        
        **Image Processing**:
        - `lucataco/remove-bg` — BiRefNet background removal
        - `nightmareai/real-esrgan` — 4× upscaling
        - `cjwbw/midas` — Depth maps
        - `jagilley/controlnet-canny` — Edge detection
        
        **Text Generation**:
        - `meta/meta-llama-3-70b-instruct` — Scripts, blogs, captions
        - `meta/meta-llama-3-8b-instruct` — Fast generation
        
        ### Data Flow (Campaign Generation)
        
        ```
        User Input → Marketing Plan → Images (6) → Background Removal
              ↓
        Blog Post → Video (3 segments) → Voiceover → Music → Assembly
              ↓
        ZIP Package → YouTube Upload → Shopify Blog → Social Posts
        ```
        
        ### Cost Breakdown (Per Campaign)
        | Component | Cost |
        |-----------|------|
        | Text generation | $0.001-0.01 |
        | Images (9 total) | $0.03-0.27 |
        | Background removal | $0.06-0.12 |
        | Video (3 segments) | $0.15-0.45 |
        | Voiceover | $0.02-0.05 |
        | Music | $0.01-0.03 |
        | **Total** | **$0.50-1.00** |
        
        ### Performance Features
        - **Request Caching**: Otto caches repeated queries (1-hour TTL)
        - **Parallel Execution**: Up to 4 concurrent tasks
        - **Exponential Backoff**: Automatic retry on failures
        - **Lazy Loading**: Heavy modules load on-demand
        - **Fragment Rendering**: Partial UI updates
        """
        )

    # Integrations
    with st.expander("🔗 Integrations & Platforms"):
        st.markdown(
            """
        ### E-Commerce Platforms
        | Platform | Capabilities |
        |----------|--------------|
        | **Printify** | Product creation, mockups, publishing, blueprint/variant management |
        | **Shopify** | Blog posts, products, digital downloads, analytics |
        
        ### Video Platforms
        | Platform | Capabilities |
        |----------|--------------|
        | **YouTube** | Video upload, thumbnails, metadata, channel stats |
        
        ### Social Media (Browser Automation)
        | Platform | Method |
        |----------|--------|
        | **Twitter/X** | AI browser automation (Anthropic Claude) |
        | **Pinterest** | Browser automation with board selection |
        | **TikTok** | Video posting |
        | **Instagram** | Image/video posting |
        | **Facebook** | Page posting |
        | **Reddit** | Subreddit posting |
        | **LinkedIn** | Professional posting |
        
        ### Email Marketing
        | Provider | Method |
        |----------|--------|
        | **SendGrid** | API (recommended, free 100/day) |
        | **Gmail OAuth** | Reuses YouTube OAuth |
        | **SMTP** | Traditional (Gmail App Password) |
        
        ### Contact Verification
        | Service | Purpose |
        |---------|---------|
        | **Hunter.io** | Email verification |
        | **Apollo.io** | Contact enrichment |
        """
        )

    st.markdown("---")
    st.markdown("**Need help?** Use the chat assistant for specific questions!")


def render_command_line_guide():
    """Enhanced command line interface with universal file generation and smart autocomplete"""
    st.markdown("### ⌨️ Slash Command Reference")
    st.markdown("---")

    # Quick Reference Card
    st.markdown(
        """
    <style>
    .cmd-card { background: linear-gradient(135deg, #667eea15, #764ba215); border-radius: 12px; padding: 16px; margin: 8px 0; border-left: 4px solid #667eea; }
    .cmd-title { font-weight: bold; color: #667eea; margin-bottom: 8px; }
    .cmd-code { background: #1e1e1e; color: #d4d4d4; padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 0.9em; }
    .cmd-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 8px; }
    .cmd-item { background: #f8f9fa; padding: 6px 10px; border-radius: 6px; font-family: monospace; font-size: 0.85em; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # Media Commands (Most Popular)
    with st.expander("🎨 Media Generation", expanded=True):
        st.markdown(
            """
| Command | Description | Example |
|---------|-------------|---------|
| `/image` | Generate images with AI | `/image sunset over mountains` |
| `/video` | Generate video clips | `/video ocean waves crashing` |
| `/music` | Generate music tracks | `/music upbeat electronic` |
| `/speak` `/tts` | Text-to-speech audio | `/speak Hello world` |
| `/sound` `/sfx` | Sound effects | `/sound explosion` |
| `/3d` `/model3d` | Generate 3D models | `/3d low-poly house` |
        """
        )

    # Document Commands
    with st.expander("📄 Documents & Files"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                """
**Text Documents:**
- `/pdf` - PDF document
- `/doc` `/docx` - Word document  
- `/txt` - Plain text
- `/rtf` - Rich text format
- `/md` - Markdown
            """
            )
        with col2:
            st.markdown(
                """
**Spreadsheets:**
- `/xlsx` `/xls` - Excel file
- `/csv` - CSV data
            """
            )

    # Code Commands
    with st.expander("💻 Code Generation"):
        st.markdown(
            """
<div class="cmd-grid">
""",
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                """
**Languages:**
- `/python` - Python
- `/js` - JavaScript
- `/ts` - TypeScript
- `/java` - Java
- `/c` `/cpp` - C/C++
- `/go` - Go
- `/rs` - Rust
- `/rb` - Ruby
- `/php` - PHP
- `/swift` - Swift
- `/kt` - Kotlin
            """
            )
        with col2:
            st.markdown(
                """
**Web:**
- `/html` - HTML
- `/css` - CSS
- `/scss` `/less` - SCSS/LESS
- `/jsx` `/tsx` - React
- `/vue` - Vue.js
- `/svelte` - Svelte
- `/astro` - Astro
            """
            )
        with col3:
            st.markdown(
                """
**Scripts & Config:**
- `/sh` `/bash` - Shell
- `/ps1` - PowerShell
- `/bat` - Windows Batch
- `/dockerfile` - Docker
- `/makefile` - Make
- `/nginx` - Nginx config
- `/gitignore` - Git ignore
            """
            )

    # Data Commands
    with st.expander("📊 Data & Config Files"):
        st.markdown(
            """
| Command | Format | Example Use |
|---------|--------|-------------|
| `/json` | JSON | `/json user profile schema` |
| `/csv` | CSV | `/csv sample sales data 10 rows` |
| `/xml` | XML | `/xml RSS feed template` |
| `/yaml` `/yml` | YAML | `/yaml docker compose config` |
| `/toml` | TOML | `/toml cargo config` |
| `/ini` | INI | `/ini application settings` |
| `/env` | .env | `/env environment variables template` |
| `/sql` | SQL | `/sql create users table` |
| `/graphql` | GraphQL | `/graphql user schema` |
        """
        )

    # AI Models
    with st.expander("🤖 Direct AI Model Access"):
        st.markdown(
            """
Call AI models directly by name:

**Image Models:**
`/flux` `/flux-dev` `/sdxl` `/imagen4` `/ideogram` `/bria` `/seedream`

**Video Models:**
`/kling` `/minimax-video` `/luma`

**Music & Audio:**
`/musicgen` `/lyria` `/stable-audio` `/minimax-music`

**3D Models:**
`/hunyuan3d` `/rodin` `/luciddreamer` `/morphix3d`

**Speech:**
`/minimax-speech` `/speech`

**Marketing:**
`/flux-ads` `/product-ads` `/logo-context` `/ad-inpaint`
        """
        )

    # Workflow Commands
    with st.expander("🔗 Workflow & Chaining"):
        st.markdown(
            """
**Chain multiple commands:**
```
/chain /image cat | /video animate | /music relaxing
/chain /python hello world -> /pdf documentation
```

**Separators:** Use `|` or `->` between commands

**Context passing:** Results flow to next command automatically
        """
        )

    # Quick Examples
    with st.expander("⚡ Quick Examples"):
        st.code(
            """
# Generate a logo and animate it
/chain /image minimalist tech logo | /video subtle rotation

# Create a full project
/python flask REST API server
/dockerfile python web app
/yaml docker compose with postgres

# Generate marketing content
/image product photo modern smartphone
/video cinematic product showcase

# Data and documents
/xlsx quarterly sales report template
/pdf business proposal outline
/json API response schema
        """,
            language="bash",
        )

    st.markdown("---")
    st.caption("💡 Type `/help` in chat for interactive command list")
