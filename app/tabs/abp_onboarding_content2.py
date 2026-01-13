"""
Onboarding Content Part 2 - Playground, Integrations, Automations
"""

PLAYGROUND_GUIDE = """
### 🎮 Playground - AI Model Testing & Experimentation
**Test, compare, and fine-tune AI models interactively**

#### 🎯 What is the Playground?
An interactive environment for testing AI models before using them in production campaigns.
Think of it as a **sandbox** where you can experiment without affecting your main workflows.

#### 🤖 Available AI Models

**Image Generation Models:**

**FLUX Family (Best Quality)**
- **FLUX.1 Pro** - Highest quality, best for final production ($0.055/image)
  - Photorealistic results
  - Complex prompt understanding
  - Superior detail and composition

- **FLUX.1 Dev** - Great quality, faster ($0.025/image)
  - Excellent for most use cases
  - Good prompt adherence
  - 90% quality of Pro at half the cost

- **FLUX.1 Schnell** - Fast drafts ($0.003/image)
  - Quick iterations
  - Good for testing concepts
  - 5-10 second generation

**Stable Diffusion Models**
- **SDXL Lightning** - Ultra-fast, 4-step generation (Cheapest)
- **SDXL Base** - Reliable all-purpose model
- **Stable Diffusion 3** - Latest SD model
- **Playground V2.5** - Artistic styles

**Specialized Models**
- **Ideogram** - Text-in-image generation (logos, posters)
- **Recraft V3** - Vector-style illustrations
- **Midjourney (via API)** - Premium artistic generation

**Video Generation Models:**

**Sora** (OpenAI - Coming Soon)
- Highest quality video generation
- 60 second clips
- Photorealistic motion

**Kling AI** (Kuaishou - Available Now)
- 10 second clips
- Excellent motion quality
- Good for product showcases

**RunwayML Gen-3** (Available Now)
- 5-10 second clips
- Great for artistic effects
- Fast generation (1-2 minutes)

**Luma Dream Machine**
- Quick generations
- Good for motion tests
- Affordable pricing

**Text Generation Models:**
- **Claude Sonnet 4** - Best reasoning and writing
- **GPT-4 Turbo** - OpenAI's latest
- **Llama 3.1 70B** - Open source alternative
- **Gemini Pro** - Google's multimodal AI

#### 🎨 How the Playground Works

**Step 1: Select Model Category**
- Choose: Image, Video, or Text generation
- Each category shows available models
- See pricing and speed estimates

**Step 2: Configure Parameters**

**For Image Models:**
- **Prompt** - Describe what you want
- **Negative Prompt** - What to avoid
- **Aspect Ratio** - 1:1, 4:5, 16:9, 9:16, custom
- **Quality** - Draft, Standard, HD, Ultra HD
- **Steps** - 20-50 (more = better quality, slower)
- **Guidance Scale** - 5-15 (how strictly to follow prompt)
- **Seed** - For reproducible results
- **Batch Size** - Generate 1-10 variations

**For Video Models:**
- **Prompt** - Describe the scene/action
- **Duration** - 2s, 5s, 10s
- **FPS** - 24, 30, 60
- **Motion Intensity** - Low, Medium, High
- **Camera Movement** - Static, Pan, Zoom, Orbit, Dolly
- **Style** - Cinematic, Realistic, Artistic

**For Text Models:**
- **System Prompt** - AI personality/role
- **User Prompt** - Your request
- **Temperature** - 0.0-1.0 (creativity level)
- **Max Tokens** - Response length
- **Top P** - Sampling diversity

**Step 3: Generate & Compare**
- Click **Generate** to create
- Results appear with metadata
- Generation time displayed
- Cost breakdown shown

**Step 4: A/B Testing**
- Generate with different models side-by-side
- Compare quality vs. speed vs. cost
- Rate results (1-5 stars)
- Save winners to library

**Step 5: Refine & Iterate**
- Adjust parameters based on results
- Use **Seed** to maintain consistency
- Try variations of prompts
- Find optimal settings

#### 🔬 Advanced Features

**Parameter Presets**
- Save your favorite configurations
- Load presets for different use cases
- Share presets with team

**Batch Comparison**
- Test same prompt across multiple models
- Automatic side-by-side view
- Quality scoring
- Cost analysis

**Prompt Engineering Tools**
- Prompt templates library
- Style modifier suggestions
- Negative prompt builder
- Keyword analyzer

**History & Versions**
- All generations saved automatically
- Track parameter changes
- Compare iterations
- Rollback to previous versions

#### 🎯 Use Cases

**Finding the Right Model:**
"Which image model gives the best results for product photography?"
→ Test FLUX Pro, FLUX Dev, and SDXL with same prompt
→ Compare quality, choose winner for production

**Optimizing Costs:**
"Can I use a cheaper model without sacrificing quality?"
→ Generate with FLUX Pro ($0.055) and FLUX Dev ($0.025)
→ If Dev is good enough, save 54% per image

**Prompt Engineering:**
"What prompt variation works best?"
→ Test 5 different prompt formulations
→ Find winning formula
→ Use in Campaign Creator

**Style Exploration:**
"What artistic style fits my brand?"
→ Try different style modifiers
→ Test across models
→ Establish brand aesthetic

#### 💡 Pro Tips

**Start with Cheaper Models:**
- Use FLUX Schnell or SDXL Lightning for initial tests
- Only use expensive models for final production
- Can save 90% on testing costs

**Use Seeds for Consistency:**
- Lock seed when you get good results
- Modify only prompt to refine
- Ensures consistent style across campaign

**Batch Generate Variations:**
- Generate 4-10 variations at once
- Pick best one or two
- Faster than generating one at a time

**Save Successful Parameters:**
- Create presets for: Product photos, Logos, Ads, Art
- Name them clearly
- Reuse across projects

**A/B Test Everything:**
- Test different aspect ratios
- Try various guidance scales
- Compare step counts (20 vs 50)
- Find sweet spot for your needs
"""

INTEGRATIONS_GUIDE = """
### 🔗 Platform Integrations
**Complete list of connected services and APIs**

#### 🎨 AI Generation Services

**Replicate.com** (Primary AI Platform)
- **Status:** Required for platform operation
- **Models:** FLUX, Stable Diffusion, Video AI, Audio AI
- **Setup:** Add API key in Settings → API Keys
- **Cost:** Pay-per-use ($0.003 - $0.055 per generation)
- **Docs:** [replicate.com/docs](https://replicate.com/docs)

**OpenAI** (Optional)
- **Models:** GPT-4, DALL-E 3, Whisper, TTS
- **Used For:** Advanced chat, image generation, voice
- **Setup:** Add key in `.env` file
- **Cost:** Token-based pricing

**Anthropic Claude** (Optional)
- **Models:** Claude Sonnet 4, Claude Opus
- **Used For:** Otto AI assistant, browser automation
- **Setup:** Add key in `.env` file
- **Cost:** Token-based pricing

#### 🛍️ E-Commerce Platforms

**Printify API** (Product Fulfillment)
- **Status:** Recommended for mockup generation
- **Features:**
  - 850+ product catalog
  - Automatic mockup generation
  - Order fulfillment integration
  - Print-on-demand services
- **Setup:**
  1. Sign up at [printify.com](https://printify.com)
  2. Generate API token in account settings
  3. Add token in Settings → API Keys
  4. Add Shop ID (found in URL)
- **Cost:** Free API, pay-per-order
- **Products:**
  - Apparel (t-shirts, hoodies, hats)
  - Home goods (mugs, pillows, blankets)
  - Accessories (phone cases, bags, stickers)
  - Wall art (posters, canvases, framed prints)

**Shopify** (Online Store)
- **Status:** Optional
- **Features:**
  - Store analytics integration
  - Product sync
  - Order tracking
  - Inventory management
- **Setup:**
  1. Configure in Settings → API Keys
  2. Add shop URL: `yourstore.myshopify.com`
  3. Choose auth method:
     - **Access Token** (Recommended): Private app token
     - **API Key + Secret**: Public app credentials
- **Cost:** Shopify subscription required
- **Use Cases:**
  - Import store analytics to dashboard
  - Sync products from Product Studio
  - Track sales performance
  - Monitor inventory levels

#### 📱 Social Media Platforms

**Twitter/X** (Social Posting)
- **Status:** Available
- **Features:**
  - Auto-posting tweets
  - Image/video uploads
  - Thread creation
  - Analytics tracking
- **Setup:**
  1. Create Twitter Developer account
  2. Generate API keys and tokens
  3. Configure in Settings → Integrations
- **Cost:** Free (within API limits)

**TikTok** (Short Video Platform)
- **Status:** Available
- **Features:**
  - Video uploads
  - Caption and hashtag management
  - Scheduled posting
- **Setup:** Configure credentials in Settings
- **Cost:** Free

**Pinterest** (Visual Discovery)
- **Status:** Available
- **Features:**
  - Pin creation
  - Board management
  - Analytics integration
- **Setup:** OAuth connection in Settings
- **Cost:** Free

**Instagram** (Meta)
- **Status:** Coming Soon
- **Features:** Photo/video posting, stories, reels
- **Setup:** Via Meta Business Suite integration

**Facebook** (Meta)
- **Status:** Coming Soon
- **Features:** Page posting, ad management
- **Setup:** Via Meta Business Suite integration

#### 📺 Video Platforms

**YouTube** (Video Hosting)
- **Status:** Fully Integrated
- **Features:**
  - Automated video uploads
  - Metadata management (title, description, tags)
  - Privacy settings (public, unlisted, private)
  - Channel analytics
  - Upload history tracking
- **Setup:**
  1. Go to Settings → YouTube
  2. Create Google Cloud Project
  3. Enable YouTube Data API v3
  4. Download OAuth credentials (`client_secret.json`)
  5. Place in project root
  6. Click **Authenticate** button
  7. Grant permissions in browser
- **Cost:** Free (within API quotas)
- **Quotas:** 10,000 units/day (1 upload = ~1600 units)

#### 🎵 Music Distribution

**Spotify for Artists** (Coming Soon)
- **Features:** Track analytics, playlist pitching
- **Setup:** Via Spotify for Artists API

**Apple Music for Artists** (Coming Soon)
- **Features:** Stream tracking, audience insights

**DistroKid/TuneCore** (Planned)
- **Features:** Multi-platform music distribution

#### 💌 Email & Marketing

**SendGrid** (Email Service)
- **Status:** Available
- **Features:** Transactional emails, bulk sending
- **Setup:** Add API key in Settings
- **Cost:** Free tier available

**Mailchimp** (Coming Soon)
- **Features:** Newsletter campaigns, automation

**ConvertKit** (Planned)
- **Features:** Creator-focused email marketing

#### 🗄️ Storage & Files

**Local File System** (Built-in)
- **Features:**
  - All files saved locally
  - Automatic organization
  - ZIP exports
  - File library management
- **Location:** `/generated_files/` folder
- **Cost:** Free (uses your disk space)

**Google Drive** (Planned)
- **Features:** Cloud backup, sharing

**Dropbox** (Planned)
- **Features:** Sync across devices

#### 🔍 Research & Data

**Google Search API** (Available)
- **Features:** Web research, competitor analysis
- **Setup:** Google Cloud credentials

**Hunter.io** (Email Finder)
- **Status:** Available in Contact Finder
- **Features:** Find email addresses, verify contacts
- **Setup:** Add API key in Settings
- **Cost:** Free tier + paid plans

**Clearbit** (Business Data)
- **Status:** Planned
- **Features:** Company enrichment, lead data

#### 🤖 Browser Automation

**Browser-Use (Anthropic)** (Built-in)
- **Status:** Active when Anthropic key provided
- **Features:**
  - Control Chrome browser
  - Navigate any website
  - Extract data automatically
  - Perform complex multi-step tasks
- **Requirements:** Anthropic Claude API key
- **Use Cases:**
  - Research competitors
  - Extract contact information
  - Automate repetitive web tasks
  - Cross-platform posting

#### 📊 Analytics & Tracking

**Google Analytics** (Planned)
- **Features:** Website traffic, conversion tracking

**Mixpanel** (Planned)
- **Features:** Product analytics, user behavior

#### 🔐 Setup Priority

**Essential (Required):**
1. ✅ **Replicate API** - Core AI generation

**Highly Recommended:**
2. ⭐ **Printify API** - Product mockups and fulfillment
3. ⭐ **YouTube OAuth** - Video uploads and distribution

**Optional (Based on Use Case):**
4. **Shopify** - If you have online store
5. **Twitter/TikTok/Pinterest** - For social media automation
6. **Anthropic Claude** - For advanced Otto AI features
7. **Hunter.io** - For lead generation and outreach

#### 💡 Integration Tips

**API Key Security:**
- Never share API keys publicly
- Store in `.env` file (excluded from git)
- Rotate keys periodically
- Use separate keys for testing vs production

**Cost Management:**
- Monitor usage in each platform's dashboard
- Set spending limits where available
- Start with free tiers
- Upgrade only when needed

**Testing Integrations:**
- Use test/sandbox modes when available
- Verify each integration after setup
- Check Settings → Status tab for connection health
- Test with small operations first

**Getting Help:**
- Ask Otto: "How do I connect Shopify?"
- Check About tab for detailed guides
- Visit each service's documentation
- Use test connections buttons in Settings
"""

AUTOMATIONS_GUIDE = """
### ⚙️ Automation Systems & Pipelines
**Build powerful workflows across the entire platform**

#### 🎯 What are Automations?
Automations are **intelligent workflows** that connect multiple platform features together to accomplish complex tasks without manual intervention. Think of them as recipes that execute automatically.

#### 🔧 Types of Automation Systems

### 1. 🏠 Dashboard Automations (Mass Campaign Generation)

**The "Check All Boxes" Power Move:**

When you enable all checkboxes in Dashboard and click "Launch Complete Workflow":

**Pipeline Flow:**
```
Concept Input
↓
AI Analysis → Generate Creative Brief
↓
[PARALLEL EXECUTION - All happen simultaneously]
├─→ Image Generation (4-10 images)
├─→ Printify Mockups (Multiple products)
├─→ Video Production (Promo + AI videos)
├─→ Blog Post Writing (1000+ words)
├─→ Social Media Content (Multi-platform)
├─→ Email Templates
└─→ Campaign Timeline (12 steps)
↓
Package Everything → ZIP Download
↓
Optional: Auto-publish to platforms
```

**What Gets Automated:**
- Image generation with multiple style variations
- Mockup creation on 10+ product types
- Video rendering with music and effects
- Content writing (blog, captions, descriptions)
- Social media post scheduling
- Email sequence creation
- YouTube video upload
- Multi-platform distribution

**Advanced Parameters Integration:**
- Your parameter selections cascade through the entire pipeline
- Image model choice affects mockup quality
- Video settings apply to all video generations
- Content tone flows through all written material
- Style consistency across all outputs

### 2. ⚡ Shortcuts (One-Click Automations)

**Creating Smart Shortcuts:**

**Example: "Coffee Mug Campaign Shortcut"**
```
When clicked:
1. Load preset: "Cozy beverage designs"
2. Generate 5 mug designs
3. Create Printify mockups
4. Write product descriptions
5. Save to Product Studio
6. Export as ZIP
```

**Building Your Shortcut:**
1. Go to **⚡ Shortcuts** tab
2. Click **➕ Create New Shortcut**
3. **Configure Trigger:**
   - Name: "Coffee Mug Blast"
   - Icon: ☕
   - Hotkey: Ctrl+Shift+C

4. **Define Actions (Chain multiple steps):**
   - Action 1: Generate images (FLUX Dev, 5 variations)
   - Action 2: Create mockups (mugs only)
   - Action 3: Write descriptions (casual tone)
   - Action 4: Auto-save to folder

5. **Set Parameters:**
   - Each action has its own settings
   - Parameters remembered between runs
   - Override options available

**Shortcut Types:**
- **Generation Shortcuts** - Create content with presets
- **Navigation Shortcuts** - Jump to specific tab/view
- **Command Shortcuts** - Execute Otto AI commands
- **Workflow Shortcuts** - Trigger custom pipelines

### 3. 🤖 Task Queue (Background Automations)

**Bulk Operations:**

**Example: "Generate 50 Products Overnight"**
```
Task Queue Setup:
1. Upload CSV with 50 product concepts
2. Configure generation parameters
3. Set schedule: Start at 11 PM
4. Queue processes each row:
   - Generate image
   - Create mockup
   - Write description
   - Save to folder
5. Wake up to 50 ready products
```

**Queue Features:**
- **Scheduling** - Run at specific times
- **Batch Processing** - Handle 100s of items
- **Priority Levels** - Rush vs normal
- **Dependencies** - Task B waits for Task A
- **Error Handling** - Retry failed operations
- **Progress Tracking** - Monitor completion

**Use Cases:**
- Bulk product generation
- Mass social media posting
- Large-scale mockup creation
- Scheduled campaign launches
- Automated daily content

### 4. 🔧 Workflows Tab (Visual Pipeline Builder)

**Creating Custom Workflows:**

**Example: "Etsy Product Pipeline"**
```
Trigger: New concept added
↓
Step 1: Generate product image (FLUX Pro)
↓
Step 2: Create Printify mockup (5 products)
↓
Step 3: Write SEO description
↓
Step 4: Generate tags and categories
↓
Step 5: Create social media posts
↓
Step 6: Upload to Etsy (via API)
↓
Step 7: Post to Instagram
↓
End: Notify me via email
```

**Workflow Builder Features:**
- **Drag-and-Drop Interface** - Visual flow design
- **Conditional Logic** - If/then branching
- **Loops** - Repeat steps multiple times
- **Variables** - Pass data between steps
- **Templates** - Start from proven workflows
- **Testing Mode** - Validate before running

**Built-in Workflow Templates:**
- Product Launch Pipeline
- Social Media Scheduler
- Content Repurposing Flow
- Customer Onboarding Sequence
- Analytics Report Generator

### 5-10. Other Automation Systems

**Campaign Creator** - 12-step marketing pipeline  
**Content Generator** - Multi-platform content production  
**Video Producer** - Automated video creation  
**Calendar** - Scheduling automation  
**Email Outreach** - Email sequence automation  
**Otto AI Automation** - Natural language automation

#### 🎯 Automation Best Practices

**Start Simple:**
- Begin with 2-3 step automations
- Test thoroughly before scaling
- Monitor first few runs
- Gradually add complexity

**Use Templates:**
- Start from built-in templates
- Modify for your needs
- Save successful variations
- Share with team

**Error Handling:**
- Set up retry logic
- Configure fallbacks
- Enable notifications
- Review failed tasks

**Optimization:**
- Run during off-peak hours
- Batch similar operations
- Use cheaper models for testing
- Cache common results

**Monitoring:**
- Check Task Queue regularly
- Review automation logs
- Track success rates
- Measure ROI

#### 💡 Advanced Automation Ideas

**"Evergreen Content Machine"**
- Generate content library
- Auto-schedule throughout year
- Recycle top performers
- Continuous improvement

**"Product Launch Sequence"**
- T-30 days: Teaser campaign
- T-14 days: Pre-launch content
- T-7 days: Email sequence
- Launch day: Multi-platform blast
- Post-launch: Analytics and optimization

**"Competitor Monitor"**
- Daily competitor analysis
- Track their content
- Generate counter-content
- Stay ahead of trends

**"Personal Brand Builder"**
- Daily thought leadership posts
- Weekly blog articles
- Monthly video content
- Quarterly email newsletters
- Automated across all platforms

#### 🚀 Getting Started with Automation

**Beginner:** Use Dashboard with all checkboxes  
**Intermediate:** Create Shortcuts for frequent tasks  
**Advanced:** Build Workflows in Workflows tab  
**Expert:** Combine multiple systems with Otto AI

**Remember:** Automations are meant to save time, not complicate your workflow. Start with what provides the most immediate value for your specific use case.
"""
