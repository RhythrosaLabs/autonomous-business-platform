from abp_imports_common import (
    st, os, time, json, random, re, Path, datetime, setup_logger
)

# Maintain backward compatibility alias
dt = datetime
logger = setup_logger(__name__)

from app.services.platform_helpers import (
    _get_replicate_token,
    _get_printify_api,
    _ensure_replicate_client,
    create_campaign_directory,
    save_campaign_metadata,
    _render_printify_product_config
)
from app.services.api_service import ReplicateAPI
from app.utils.ray_integration_helpers import is_ray_enabled
from app.services.smart_dashboard_widget import SmartDashboard, ActivityFeed
from app.utils.cross_page_state import render_campaign_status_banner
from abp_campaign_generator import run_campaign_generation
from ai_model_manager import ModelFallbackManager, ModelPriority
from prompt_templates import PromptTemplateLibrary

def render_dashboard_tab(
    smart_dashboard_available,
    cross_page_mgr
):
    """
    Renders the main Dashboard tab (Tab 0).
    """
    st.markdown('<div class="main-header">🚀 Autonomous Business Platform Pro</div>', unsafe_allow_html=True)

    # Show campaign status banner if there's an active/completed campaign
    render_campaign_status_banner()

    st.markdown("### 🚀 What Are You Selling?")
    st.markdown("Describe your product idea and let AI create everything you need")

    col_random, _ = st.columns([1, 3])
    with col_random:
        if st.button("🎲 Randomize Concept", use_container_width=True):
            with st.spinner("Generating creative concept..."):
                replicate_token = _get_replicate_token()

                fallback_concepts = [
                    "Majestic Siberian husky portrait in geometric minimalist style",
                    "Retro 80s synthwave husky running through neon city",
                    "Watercolor husky pack running through autumn forest",
                    "Motivational husky fitness: determined sled dog aesthetic",
                    "Cute kawaii husky puppy illustrations with big blue eyes",
                    "Abstract marble pattern featuring husky silhouettes",
                    "Vintage adventure poster: husky expedition in Arctic landscape",
                    "Zen meditation husky in peaceful snow mandala design",
                    "Cyberpunk neon husky with glowing blue eyes cityscape",
                    "Hand-lettered quotes with husky paw prints and portraits",
                    "Scandinavian hygge cozy husky by fireplace illustration",
                    "Astrology constellation husky: celestial wolf spirit guide",
                    "Retro pixel art 8-bit husky gaming character sprite",
                    "Tropical beach husky: Arctic dog on paradise vacation",
                    "Gothic dark academia aesthetic: scholarly husky with books"
                ]

                if replicate_token:
                    try:
                        from app.services.api_service import ReplicateAPI
                        import random

                        replicate_api = ReplicateAPI(replicate_token)
                        prompt = (
                            "Create ONE specific, creative design concept for husky-themed print-on-demand products. "
                            "Format: Brief descriptive phrase for the design (10-15 words max). "
                            "Example: 'Cyberpunk neon husky with glowing eyes in futuristic cityscape' "
                            "Example: 'Watercolor husky pack running through vibrant autumn forest' "
                            "Example: 'Minimalist geometric husky portrait with bold color blocks' "
                            "Generate ONE creative husky design concept now:"
                        )
                        generated = replicate_api.generate_text(prompt, max_tokens=50, temperature=0.9)
                        
                        # Extract just the first concept if multiple were generated
                        lines = generated.strip().split('\n')
                        concept = lines[0].strip()
                        
                        # Clean up numbering, bullets, or markdown
                        import re
                        concept = re.sub(r'^[\d\.\*\-\#\:]+\s*', '', concept)  # Remove leading numbers/bullets
                        concept = re.sub(r'^\*\*(.+)\*\*:?', r'\1', concept)  # Remove bold markdown
                        concept = concept.strip('"\'')  # Remove quotes
                        
                        # If still too short or looks like a list, use fallback
                        if len(concept) < 10 or concept.lower().startswith('here'):
                            concept = random.choice(fallback_concepts)
                        
                        st.session_state.concept_input = concept[:200]  # Limit length
                        st.toast("✨ AI-generated concept!")
                    except Exception as exc:
                        st.warning(f"AI generation failed: {exc}")
                        st.session_state.concept_input = random.choice(fallback_concepts)
                else:
                    st.info("Provide a Replicate API key in Settings to use AI concept generation.")
                    st.session_state.concept_input = random.choice(fallback_concepts)
            st.rerun()

    # Initialize concept_input in session state if not already set
    if 'concept_input' not in st.session_state:
        st.session_state.concept_input = ''

    concept_input = st.text_area(
        "🎨 Design Theme / Concept",
        placeholder="e.g., 'Cyberpunk neon cityscape aesthetic' or 'Minimalist botanical line art' or 'Retro 80s vaporwave vibes'",
        height=100,
        key="concept_input",
        help="Describe the DESIGN/AESTHETIC you want to create. This will be printed on canvas art, posters, journals, mugs, etc."
    )

    st.markdown("---")

    # ===== BRAND TEMPLATE SELECTION =====
    st.markdown("### 🎨 Brand Template")

    # Load brand templates
    brand_templates_file = Path(__file__).parent / "brand_templates.json"
    brand_templates = []
    active_brand_id = None

    if brand_templates_file.exists():
        try:
            with open(brand_templates_file, 'r') as f:
                brand_data = json.load(f)
                brand_templates = brand_data.get('templates', [])
                active_brand_id = brand_data.get('active_brand')
        except Exception:
            pass

    if brand_templates:
        brand_options = ["None (No brand template)"] + [t['name'] for t in brand_templates]
        brand_values = [None] + [t['id'] for t in brand_templates]
    
        # Find default
        default_idx = 0
        if active_brand_id:
            for idx, bid in enumerate(brand_values):
                if bid == active_brand_id:
                    default_idx = idx
                    break
    
        brand_col1, brand_col2 = st.columns([2, 1])
        with brand_col1:
            selected_brand_idx = st.selectbox(
                "Apply Brand Template",
                range(len(brand_options)),
                format_func=lambda x: brand_options[x],
                index=default_idx,
                help="Select a brand template to guide all generations - styles, colors, voice, hashtags"
            )
            selected_brand_id = brand_values[selected_brand_idx]
            selected_brand = None
            for t in brand_templates:
                if t.get('id') == selected_brand_id:
                    selected_brand = t
                    break
    
        with brand_col2:
            if selected_brand:
                st.success(f"✅ **{selected_brand['name']}**")
    
        if selected_brand:
            with st.expander("📋 Brand Details", expanded=False):
                bc1, bc2, bc3 = st.columns(3)
                with bc1:
                    st.markdown(f"**Voice:** {selected_brand.get('voice', 'N/A')}")
                    st.markdown(f"**Tone:** {', '.join(selected_brand.get('content_tone', []))}")
                with bc2:
                    st.markdown(f"**Image Style:** {selected_brand.get('image_style', 'N/A')}")
                    st.markdown(f"**Font:** {selected_brand.get('font_style', 'N/A')}")
                with bc3:
                    colors = selected_brand.get('colors', {})
                    st.markdown(f"**Colors:** {colors.get('primary', '#000')} / {colors.get('secondary', '#000')}")
                    st.markdown(f"**CTA:** {selected_brand.get('cta_text', 'Shop Now')}")
        
            # Store in session state for use during generation
            st.session_state['selected_brand_template'] = selected_brand
        else:
            st.session_state['selected_brand_template'] = None
    else:
        st.info("💡 Create brand templates in the **Brand Templates** page for consistent styling across all generations!")
        st.session_state['selected_brand_template'] = None

    st.markdown("---")
    st.markdown("### 🎯 Select Automation Workflows")

    # Master "Check All" checkbox
    col_check, col_fast = st.columns([2, 1])
    with col_check:
        check_all = st.checkbox(
            "☑️ **CHECK ALL** (Enable complete automation)",
            value=False,
            help="Enable all workflows and auto-publish options at once"
        )
    with col_fast:
        fast_mode = st.checkbox(
            "⚡ **FAST MODE**",
            value=False,
            help="Skip enhancement steps and use faster models. ~50% faster but slightly less polished results."
        )

    # Show speed indicator
    if fast_mode:
        st.success("⚡ Fast Mode ON - Using accelerated generation")

    st.markdown("Check everything you want AI to generate from your concept:")

    col1, col2 = st.columns(2)

    with col1:
        campaign_enabled = st.checkbox(
            "📊 **Campaign Strategy**",
            value=True if check_all else False,
            help="AI analyzes your concept and creates a comprehensive marketing campaign plan"
        )

        product_enabled = st.checkbox(
            "🎨 **Design Generation**",
            value=True if check_all else True,
            help="Generate AI artwork/designs that will be printed on products (canvas art, posters, journals, mugs, etc.)"
        )
    
        # Digital Products - now between design and blog
        digital_products_enabled = st.checkbox(
            "💾 **Digital Products**",
            value=True if check_all else False,
            help="Create complete digital products: e-books, coloring books, courses, comics (AI generates full content)"
        )

        blog_enabled = st.checkbox(
            "📰 **Blog Post Generation**",
            value=True if check_all else False,
            help="Generate professional HTML blog posts with images (publishes to Shopify)"
        )

    with col2:
        video_enabled = st.checkbox(
            "🎬 **Video Production**",
            value=True if check_all else False,
            help="Generate promotional videos with voiceover and music"
        )

        social_enabled = st.checkbox(
            "📱 **Social Media Assets**",
            value=True if check_all else False,
            help="Create platform-specific social media posts and graphics"
        )
    
        email_enabled = st.checkbox(
            "📧 **Email Campaign Generation**",
            value=True if check_all else False,
            help="Generate professional HTML email campaigns with images",
            disabled=not social_enabled
        )

    # Digital Products Configuration (if enabled) - Full Generator
    if digital_products_enabled:
        with st.expander("💾 Digital Products Settings - Complete Product Generator", expanded=False):
            st.markdown("**🚀 AI will create COMPLETE digital products - full books, courses, not just cover art!**")
        
            dp_col1, dp_col2 = st.columns(2)
            with dp_col1:
                digital_product_type = st.selectbox(
                    "Product Type",
                    options=['ebook', 'coloring_book', 'course', 'comic', 'graphic_art'],
                    format_func=lambda x: {
                        'ebook': '📚 Complete E-Book (Full chapters + PDF + optional audiobook)',
                        'coloring_book': '🖍️ Coloring Book (Full pages + PDF)',
                        'course': '🎓 Online Course (Modules + Lessons + Worksheets)',
                        'comic': '💥 Comic Book (Full pages + Script + PDF)',
                        'graphic_art': '🎨 Digital Art (Quick image generation)'
                    }.get(x, x)
                )
                digital_price = st.number_input("Price ($)", min_value=4.99, value=19.99, step=1.00, key="digital_price_main")
        
            with dp_col2:
                digital_title = st.text_input("Product Title (optional)", placeholder="Auto-generated from concept if blank", key="digital_title_main")
                auto_publish_digital = st.checkbox("🚀 Auto-publish to Shopify", value=True, key="auto_pub_digital")
        
            # Type-specific settings
            if digital_product_type == 'ebook':
                st.markdown("##### 📚 E-Book Settings")
                ebook_col1, ebook_col2 = st.columns(2)
                with ebook_col1:
                    ebook_chapters = st.slider("Number of Chapters", 3, 15, 5, key="ebook_ch_main")
                    ebook_genre = st.selectbox("Genre", ['how-to', 'fiction', 'self-help', 'business', 'children', 'sci-fi', 'romance'], key="ebook_genre_main")
                with ebook_col2:
                    ebook_audience = st.selectbox("Target Audience", ['general', 'beginner', 'intermediate', 'expert', 'children', 'teens', 'adults'], key="ebook_aud_main")
                    ebook_include_audio = st.checkbox("Include Audiobook (MP3)", value=False, key="ebook_audio_main")
            
                st.session_state['digital_products_config'] = {
                    'enabled': True, 'type': 'ebook', 'price': digital_price, 'title': digital_title,
                    'auto_publish': auto_publish_digital, 'chapters': ebook_chapters,
                    'genre': ebook_genre, 'audience': ebook_audience, 'include_audio': ebook_include_audio
                }
        
            elif digital_product_type == 'coloring_book':
                st.markdown("##### 🖍️ Coloring Book Settings")
                cb_col1, cb_col2 = st.columns(2)
                with cb_col1:
                    cb_pages = st.slider("Number of Pages", 5, 50, 15, key="cb_pages_main")
                    cb_difficulty = st.selectbox("Difficulty", ['kids', 'teen', 'adult', 'intricate'], key="cb_diff_main")
                with cb_col2:
                    cb_style = st.selectbox("Art Style", ['line art', 'mandala', 'realistic', 'cartoon', 'geometric', 'nature'], key="cb_style_main")
            
                st.session_state['digital_products_config'] = {
                    'enabled': True, 'type': 'coloring_book', 'price': digital_price, 'title': digital_title,
                    'auto_publish': auto_publish_digital, 'pages': cb_pages,
                    'difficulty': cb_difficulty, 'style': cb_style
                }
        
            elif digital_product_type == 'course':
                st.markdown("##### 🎓 Course Settings")
                course_col1, course_col2 = st.columns(2)
                with course_col1:
                    course_modules = st.slider("Number of Modules", 2, 8, 4, key="course_mod_main")
                    course_lessons = st.slider("Lessons per Module", 2, 6, 3, key="course_less_main")
                with course_col2:
                    course_level = st.selectbox("Skill Level", ['beginner', 'intermediate', 'advanced'], key="course_lvl_main")
                    course_include_worksheets = st.checkbox("Include Worksheets", value=True, key="course_ws_main")
            
                st.session_state['digital_products_config'] = {
                    'enabled': True, 'type': 'course', 'price': digital_price, 'title': digital_title,
                    'auto_publish': auto_publish_digital, 'modules': course_modules,
                    'lessons': course_lessons, 'level': course_level, 'worksheets': course_include_worksheets
                }
        
            elif digital_product_type == 'comic':
                st.markdown("##### 💥 Comic Book Settings")
                comic_col1, comic_col2 = st.columns(2)
                with comic_col1:
                    comic_pages = st.slider("Number of Pages", 4, 24, 8, key="comic_pg_main")
                    comic_genre = st.selectbox("Genre", ['action', 'comedy', 'drama', 'fantasy', 'sci-fi', 'horror', 'superhero'], key="comic_genre_main")
                with comic_col2:
                    comic_style = st.selectbox("Art Style", ['manga', 'western', 'indie', 'noir', 'cartoon', 'realistic'], key="comic_style_main")
            
                st.session_state['digital_products_config'] = {
                    'enabled': True, 'type': 'comic', 'price': digital_price, 'title': digital_title,
                    'auto_publish': auto_publish_digital, 'pages': comic_pages,
                    'genre': comic_genre, 'style': comic_style
                }
        
            else:  # graphic_art
                st.markdown("##### 🎨 Digital Art Settings")
                art_col1, art_col2 = st.columns(2)
                with art_col1:
                    digital_variations = st.slider("Variations to Generate", 1, 5, 3, key="art_var_main")
                with art_col2:
                    digital_license = st.selectbox("License Type", ['personal', 'commercial', 'extended'],
                        format_func=lambda x: {'personal': '👤 Personal', 'commercial': '💼 Commercial', 'extended': '🌟 Extended'}.get(x, x),
                        index=1, key="art_lic_main")
            
                st.session_state['digital_products_config'] = {
                    'enabled': True, 'type': 'graphic_art', 'price': digital_price, 'title': digital_title,
                    'auto_publish': auto_publish_digital, 'variations': digital_variations, 'license': digital_license
                }
        
            st.info("💡 AI will generate the COMPLETE product (not just artwork) and auto-list on Shopify!")
    else:
        st.session_state['digital_products_config'] = {'enabled': False}

    # Extra AI Intelligence Steps
    st.markdown("---")
    st.markdown("### 🧠 Extra AI Intelligence Steps")
    st.markdown("*Advanced AI analysis and optimization*")

    extra_col1, extra_col2, extra_col3 = st.columns(3)

    with extra_col1:
        st.markdown("**📊 Research & Analysis**")
        enable_trend_scanning = st.checkbox(
            "📈 Trend & Competition Scan",
            value=True if check_all else False,
            help="Analyze current market trends and competitor products"
        )
    
        enable_seo_research = st.checkbox(
            "🔍 SEO & Keyword Research", 
            value=True if check_all else False,
            help="Research optimal keywords and SEO strategy"
        )
    
        enable_demand_prediction = st.checkbox(
            "📊 Predictive Demand Modeling",
            value=True if check_all else False,
            help="AI predicts potential demand based on market data"
        )

    with extra_col2:
        st.markdown("**🎯 Optimization**")
        enable_ab_testing = st.checkbox(
            "🔬 A/B Title & Design Testing",
            value=True if check_all else False,
            help="Generate multiple variations for testing"
        )
    
        enable_seasonality = st.checkbox(
            "📅 Seasonality Refresh",
            value=True if check_all else False,
            help="Optimize content for current season/holidays"
        )
    
        enable_bundle_generation = st.checkbox(
            "📦 Bundle & Upsell Generation",
            value=True if check_all else False,
            help="Create product bundle suggestions"
        )

    with extra_col3:
        st.markdown("**🤝 Outreach & PR**")
        enable_influencer_outreach = st.checkbox(
            "👥 Influencer Outreach List",
            value=True if check_all else False,
            help="Generate list of relevant influencers to contact"
        )
    
        enable_pr_press = st.checkbox(
            "📰 PR & Press Kit",
            value=True if check_all else False,
            help="Generate press release and media kit"
        )
    
        enable_analytics_cohort = st.checkbox(
            "📈 Analytics & Cohort Setup",
            value=True if check_all else False,
            help="Set up tracking and cohort analysis"
        )

    # Store extra steps in session state
    st.session_state['extra_ai_steps'] = {
        'trend_scanning': enable_trend_scanning,
        'seo_research': enable_seo_research,
        'demand_prediction': enable_demand_prediction,
        'ab_testing': enable_ab_testing,
        'seasonality': enable_seasonality,
        'bundle_generation': enable_bundle_generation,
        'influencer_outreach': enable_influencer_outreach,
        'pr_press': enable_pr_press,
        'analytics_cohort': enable_analytics_cohort
    }

    # Show enabled extra AI steps summary
    enabled_extra_steps = []
    if enable_trend_scanning: enabled_extra_steps.append("📈 Trends")
    if enable_seo_research: enabled_extra_steps.append("🔍 SEO")
    if enable_demand_prediction: enabled_extra_steps.append("📊 Demand")
    if enable_ab_testing: enabled_extra_steps.append("🔬 A/B Test")
    if enable_seasonality: enabled_extra_steps.append("📅 Seasonal")
    if enable_bundle_generation: enabled_extra_steps.append("📦 Bundles")
    if enable_influencer_outreach: enabled_extra_steps.append("👥 Influencers")
    if enable_pr_press: enabled_extra_steps.append("📰 PR")
    if enable_analytics_cohort: enabled_extra_steps.append("📈 Analytics")

    if enabled_extra_steps:
        st.info(f"🧠 **Extra AI steps enabled:** {', '.join(enabled_extra_steps)}")

    st.markdown("---")
    st.markdown("### 🚀 Auto-Publish Options")
    st.markdown("*Automatically publish content when generation completes*")

    col_pub1, col_pub2, col_pub3 = st.columns(3)

    with col_pub1:
        st.markdown("**📦 E-Commerce**")
        auto_publish_printify = st.checkbox(
            "📦 → Printify",
            value=True if check_all else False,
            help="Auto-publish products to Printify shop",
            disabled=not product_enabled
        )

        auto_publish_shopify = st.checkbox(
            "📰 → Shopify Blog",
            value=True if check_all else False,
            help="Auto-publish blog to Shopify store",
            disabled=not blog_enabled
        )

        auto_publish_youtube = st.checkbox(
            "🎬 → YouTube",
            value=True if check_all else False,
            help="Auto-upload video to YouTube channel",
            disabled=not video_enabled
        )
    
        auto_send_email = st.checkbox(
            "📧 → Email Campaign",
            value=True if check_all else False,
            help="Automatically send email campaign to recipient list",
            disabled=not email_enabled
        )

    with col_pub2:
        st.markdown("**📱 Social Media**")
        auto_publish_twitter = st.checkbox(
            "🐦 → Twitter/X",
            value=True if check_all else False,
            help="Post to Twitter with AI captions",
            disabled=not social_enabled
        )
    
        auto_publish_instagram = st.checkbox(
            "📸 → Instagram",
            value=True if check_all else False,
            help="Post to Instagram feed and stories",
            disabled=not social_enabled
        )
    
        auto_publish_tiktok = st.checkbox(
            "🎵 → TikTok",
            value=True if check_all else False,
            help="Post video content to TikTok",
            disabled=not social_enabled
        )
    
        auto_publish_facebook = st.checkbox(
            "👥 → Facebook",
            value=True if check_all else False,
            help="Post to Facebook page/profile",
            disabled=not social_enabled
        )

    with col_pub3:
        st.markdown("**🌐 Discovery & Communities**")
        auto_publish_pinterest = st.checkbox(
            "📌 → Pinterest",
            value=True if check_all else False,
            help="Pin products to Pinterest boards",
            disabled=not social_enabled
        )
    
        auto_publish_reddit = st.checkbox(
            "🤖 → Reddit",
            value=False,  # Default off - requires care with subreddit rules
            help="Share to relevant subreddit communities",
            disabled=not social_enabled
        )
    
        if auto_publish_reddit:
            reddit_subreddits = st.text_input(
                "Subreddits (comma-separated)",
                value="",
                placeholder="e.g., printify, etsy, entrepreneurship",
                help="Be mindful of subreddit rules!"
            )
            st.session_state['reddit_subreddits'] = reddit_subreddits

    # Social media browser settings (shown if any social platform is enabled)
    any_social_enabled = any([auto_publish_twitter, auto_publish_instagram, auto_publish_tiktok, 
                              auto_publish_facebook, auto_publish_pinterest, auto_publish_reddit])

    # ALWAYS store platform selections in session state (not just when expander is open)
    st.session_state['social_platforms'] = {
        'twitter': auto_publish_twitter,
        'instagram': auto_publish_instagram,
        'tiktok': auto_publish_tiktok,
        'facebook': auto_publish_facebook,
        'pinterest': auto_publish_pinterest,
        'reddit': auto_publish_reddit
    }

    # Show selected platforms summary
    if any_social_enabled:
        selected_platforms = []
        if auto_publish_twitter: selected_platforms.append("🐦 Twitter")
        if auto_publish_instagram: selected_platforms.append("📸 Instagram")
        if auto_publish_tiktok: selected_platforms.append("🎵 TikTok")
        if auto_publish_facebook: selected_platforms.append("👥 Facebook")
        if auto_publish_pinterest: selected_platforms.append("📌 Pinterest")
        if auto_publish_reddit: selected_platforms.append("🤖 Reddit")
    
        st.success(f"✅ **Will auto-post to:** {', '.join(selected_platforms)}")
    
        with st.expander("🌐 Social Media Browser Settings", expanded=False):
            browser_type = st.selectbox(
                "Browser for Social Posting",
                options=['brave', 'chrome', 'firefox'],
                index=['brave', 'chrome', 'firefox'].index(os.getenv('BROWSER_TYPE', 'brave').lower()) if os.getenv('BROWSER_TYPE', 'brave').lower() in ['brave', 'chrome', 'firefox'] else 0,
                help="Use your existing browser with saved logins to avoid login loops!"
            )
            st.session_state['browser_type'] = browser_type
            st.info(f"💡 Make sure you're logged into all platforms in {browser_type.title()}!")

    # Initialize email_recipients with empty default
    email_recipients = ""
    
    # Email recipients section (if email enabled)
    if auto_send_email:
        # Load mailing list from local file and Shopify
        all_emails = ["scatterboxxrocks@gmail.com"]  # Default always included
    
        # Try to load from local mailing list
        try:
            import json
            mailing_list_path = Path(__file__).parent / "mailing_list.json"
            if mailing_list_path.exists():
                with open(mailing_list_path, 'r') as f:
                    mailing_data = json.load(f)
                local_emails = [s['email'] for s in mailing_data.get('subscribers', []) 
                               if s.get('accepts_marketing', True)]
                all_emails.extend(local_emails)
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass
    
        # Also try Shopify if no local list
        if len(all_emails) <= 1:
            try:
                from shopify_service import ShopifyAPI
                shopify_svc = ShopifyAPI()
                if shopify_svc.connected:
                    shopify_emails = shopify_svc.get_customer_emails(limit=100, marketing_only=True)
                    all_emails.extend(shopify_emails)
            except (ImportError, Exception):
                pass
        
        # Add contacts found during campaign generation
        if 'campaign_contact_emails' in st.session_state and st.session_state.campaign_contact_emails:
            all_emails.extend(st.session_state.campaign_contact_emails)
            st.info(f"👥 Added {len(st.session_state.campaign_contact_emails)} contacts from AI research")
    
        # Deduplicate
        all_emails = list(dict.fromkeys(all_emails))
    
        with st.expander("📧 Email Campaign Recipients", expanded=False):
            email_col1, email_col2 = st.columns([3, 1])
        
            with email_col1:
                email_recipients = st.text_area(
                    "📋 Recipients (one per line)",
                    value="\n".join(all_emails[:50]),
                    height=100,
                    help="Your mailing list is auto-loaded. Manage it in the Customers page."
                )
        
            with email_col2:
                st.markdown(f"**📊 {len(all_emails)} subscribers**")
                st.caption("Manage in **Customers** page")
            
                if st.button("🔄 Refresh List", help="Reload mailing list"):
                    st.rerun()

    st.markdown("---")

    # Combined Advanced Configuration & Model Parameters
    with st.expander("⚙️ Advanced Configuration & Model Parameters", expanded=False):
    
        # ========== SMART CONCEPT ANALYZER ==========
        def analyze_concept_for_defaults(concept: str) -> dict:
            """Analyze concept text to suggest smart defaults"""
            concept_lower = concept.lower()
        
            # Audience detection
            audience_hints = {
                'kids': ['kids', 'children', 'toddler', 'baby', 'nursery', 'kawaii', 'cute', 'cartoon'],
                'gamers': ['gaming', 'gamer', 'pixel', 'retro game', '8-bit', 'arcade', 'esports'],
                'fitness': ['fitness', 'gym', 'workout', 'athletic', 'yoga', 'sports', 'motivation'],
                'pet lovers': ['dog', 'cat', 'husky', 'puppy', 'kitten', 'pet', 'animal'],
                'nature lovers': ['nature', 'forest', 'mountain', 'ocean', 'botanical', 'flower', 'wildlife'],
                'tech enthusiasts': ['tech', 'cyber', 'neon', 'futuristic', 'sci-fi', 'robot', 'AI'],
                'art collectors': ['art', 'abstract', 'minimalist', 'modern', 'gallery', 'artistic'],
                'music fans': ['music', 'band', 'concert', 'vinyl', 'jazz', 'rock', 'hip hop'],
            }
        
            detected_audience = "General consumers"
            for audience, keywords in audience_hints.items():
                if any(kw in concept_lower for kw in keywords):
                    detected_audience = audience.title()
                    break
        
            # Style detection for video/content
            style_hints = {
                'Cinematic': ['dramatic', 'epic', 'cinematic', 'movie', 'film'],
                'Modern': ['modern', 'contemporary', 'sleek', 'clean'],
                'Elegant': ['elegant', 'luxury', 'premium', 'sophisticated'],
                'Dynamic': ['dynamic', 'action', 'energetic', 'vibrant'],
                'Minimalist': ['minimalist', 'simple', 'minimal', 'clean'],
            }
        
            detected_style = "Modern"
            for style, keywords in style_hints.items():
                if any(kw in concept_lower for kw in keywords):
                    detected_style = style
                    break
        
            # Price range suggestion
            premium_indicators = ['luxury', 'premium', 'exclusive', 'limited', 'collector', 'art']
            budget_indicators = ['fun', 'simple', 'basic', 'everyday', 'casual']
        
            if any(ind in concept_lower for ind in premium_indicators):
                price_suggestion = "Premium ($35-50)"
            elif any(ind in concept_lower for ind in budget_indicators):
                price_suggestion = "Budget ($10-20)"
            else:
                price_suggestion = "Mid-range ($20-35)"
        
            return {
                'audience': detected_audience,
                'style': detected_style,
                'price_range': price_suggestion
            }
    
        # Get smart defaults from concept
        smart_defaults = analyze_concept_for_defaults(concept_input) if concept_input else {}
    
        # ========== CAMPAIGN SETTINGS ==========
        st.markdown("## 📊 Campaign Settings")
    
        # Show smart detection if we found something
        detected_audience = smart_defaults.get('audience', 'General consumers')
        detected_style = smart_defaults.get('style', 'Modern')
        if detected_audience != "General consumers":
            st.info(f"🧠 **Smart Detection:** Detected audience: *{detected_audience}* | Style: *{detected_style}*")
    
        col_a, col_b = st.columns(2)
        with col_a:
            num_products = st.slider("Number of Products", 1, 5, 1)
            target_audience = st.text_input("Target Audience", smart_defaults.get('audience', "General consumers"))
        with col_b:
            price_options = ["Budget ($10-20)", "Mid-range ($20-35)", "Premium ($35-50)"]
            default_price_idx = price_options.index(smart_defaults.get('price_range', "Mid-range ($20-35)"))
            price_range = st.selectbox("Price Range", price_options, index=default_price_idx)
    
        st.markdown("---")

        # ========== PRINTIFY PRODUCT TARGET ==========
        st.markdown("## 🛍️ Printify Product Target")
        st.caption("These selections control how products are created when the full automation publishes to Printify.")
        campaign_printify_config, campaign_printify_ready, _ = _render_printify_product_config(
            "Campaign Product Target (Printify)",
            config_key="campaign_printify_config",
            allow_auto_toggle=False,
            instructions="Set the blueprint, provider, and variants that campaign generations should use when auto-publishing to Printify."
        )
        if auto_publish_printify and not campaign_printify_ready:
            st.warning("Auto-publish to Printify is enabled above, but no product is configured yet. Complete the selections here before running the campaign.")
    
        st.markdown("---")
    
        # ========== VIDEO PRODUCTION ==========
        st.markdown("## 🎬 Video Production Settings")
        st.caption("Customize video generation (only applies if 'Generate Video' is checked)")
    
        # Video Model Selection (same as Video Production tab)
        st.markdown("### 🎬 AI Video Model")
        video_model_option = st.selectbox(
            "Select video generation model:",
            [
                "🎉 Minimax Hailuo Fast (Image-to-Video, Best Product Consistency) ⭐",
                "🏞️ Ken Burns Effect (Free, Instant)",
                "⚡ Luma Ray Flash 2 (Fast, 540p)",
                "💨 Luma Ray 2 (High Quality, 540p)",
                "🌟 Kling v2.5 Turbo Pro (Premium)",
                "🎥 OpenAI Sora-2 (Best, Slow)",
                "🌌 Google Veo 3 (Audio, Top Quality)",
                "⚡ Google Veo 3 Fast (Audio, Quick)",
                "🎆 Google Veo 3.1 Fast (Audio, Improved)",
                "🕹️ Google Veo 2 (4K Quality)",
                "🎨 Pixverse v5 (Anime, 1080p/8s)",
                "🎬 Pixverse v4.5 (Fast, 1080p)",
                "🎁 Leonardo Motion 2.0 (480p)",
                "🌊 Wan Video 2.5 (Fast T2V)",
                "🌱 Bytedance Seedance Pro (Cinematic)"
            ],
            index=0,  # Default to Hailuo for best product consistency
            key="auto_video_model",
            help="Hailuo (default) provides the best product consistency by using your product image as the starting frame"
        )
    
        # Parse model selection
        auto_use_hailuo = "Hailuo" in video_model_option
        auto_use_ken_burns = "Ken Burns" in video_model_option
        auto_use_luma = "Luma Ray Flash" in video_model_option
        auto_use_luma2 = "Luma Ray 2" in video_model_option
        auto_use_kling = "Kling" in video_model_option
        auto_use_sora = "Sora-2" in video_model_option
        auto_use_veo3 = video_model_option == "🌌 Google Veo 3 (Audio, Top Quality)"
        auto_use_veo3_fast = video_model_option == "⚡ Google Veo 3 Fast (Audio, Quick)"
        auto_use_veo31_fast = "Veo 3.1 Fast" in video_model_option
        auto_use_veo2 = "Veo 2" in video_model_option
        auto_use_pixverse5 = "Pixverse v5" in video_model_option
        auto_use_pixverse45 = "Pixverse v4.5" in video_model_option
        auto_use_leonardo = "Leonardo Motion" in video_model_option
        auto_use_wan = "Wan Video" in video_model_option
        auto_use_seedance = "Seedance" in video_model_option
    
        # Show info about Hailuo recommendation
        if auto_use_hailuo:
            st.success("✅ **Hailuo selected** - Best choice for product videos! Uses your product image to ensure consistent appearance throughout the video.")
    
        st.markdown("### 🎬 Video Production Options")
        video_settings_col1, video_settings_col2, video_settings_col3 = st.columns(3)
    
        with video_settings_col1:
            num_segments = st.slider(
                "Number of Video Segments:",
                min_value=1,
                max_value=5,
                value=3,
                key="auto_num_segments",
                help="Split commercial into multiple scenes"
            )
            video_style = st.selectbox(
                "Visual Style:",
                ["Cinematic", "Modern", "Elegant", "Dynamic", "Minimalist", "Luxury"],
                key="auto_video_style",
                help="Choose the visual style for your commercial"
            )
    
        with video_settings_col2:
            include_music = st.checkbox(
                "🎵 Background Music",
                value=True,
                key="auto_include_music",
                help="Generate AI background music"
            )
            include_voiceover = st.checkbox(
                "🎙️ Voiceover Narration",
                value=True,
                key="auto_include_voiceover",
                help="Add professional voiceover per segment"
            )
    
        with video_settings_col3:
            aspect_ratio = st.selectbox(
                "Aspect Ratio:",
                ["16:9", "9:16", "1:1", "4:3"],
                key="auto_aspect_ratio",
                help="16:9 for YouTube, 9:16 for TikTok/Reels"
            )
            camera_movement = st.selectbox(
                "Camera Movement:",
                ["Smooth Pan", "Zoom In", "Zoom Out", "Static", "Dynamic"],
                key="auto_camera_movement",
                help="Product showcase camera movement"
            )
    
        # Voice settings (only if voiceover enabled)
        if include_voiceover:
            st.markdown("### 🎙️ Voice Settings")
            voice_col1, voice_col2 = st.columns(2)
            with voice_col1:
                selected_voice = st.selectbox(
                    "Voiceover Voice:",
                    options=["Deep Voice Man", "Friendly Person", "Calm Woman", "Casual Guy", 
                             "Wise Woman", "Inspirational Girl", "Lively Girl", "Patient Man"],
                    index=0,
                    key="auto_selected_voice",
                    help="Professional voice for product narration"
                )
            with voice_col2:
                selected_emotion = st.selectbox(
                    "Voice Emotion:",
                    options=["auto", "happy", "excited", "confident", "calm", "friendly"],
                    index=1,
                    key="auto_selected_emotion",
                    help="Emotional tone for the commercial"
                )
        else:
            selected_voice = "Deep Voice Man"
            selected_emotion = "excited"
    
        # Show model-specific info
        if auto_use_hailuo:
            st.info("⚠️ Minimax Hailuo requires product image - will use Printify mockups")
        elif auto_use_ken_burns:
            st.info("⚡ Ken Burns uses instant rendering with zoom/pan effects")
        elif auto_use_sora:
            st.info("⭐ Sora-2 provides premium cinematic quality (slower generation)")
    
        # Deprecated model selection mode - keeping for backwards compatibility
        model_selection_mode = "⚙️ Manual Selection"
    
        if model_selection_mode == "🎯 Recommended (Auto)":
            st.info("💡 AI will automatically select the best model based on your settings")
        
            rec_col1, rec_col2, rec_col3 = st.columns(3)
            with rec_col1:
                quality_priority = st.selectbox(
                    "Quality Priority",
                    ["Cinematic", "High", "Good", "Fast"],
                    index=1,
                    help="Higher quality = slower + more expensive"
                )
            with rec_col2:
                speed_priority = st.checkbox(
                    "⚡ Speed Priority",
                    value=False,
                    help="Prioritize speed over quality"
                )
            with rec_col3:
                budget_level = st.selectbox(
                    "Budget",
                    ["Premium", "Standard", "Economy", "Free"],
                    index=1,
                    help="Premium = best quality, Free = Ken Burns only"
                )
        
            # Set model flags based on recommendation
            from ai_model_manager import ModelFallbackManager
            manager = ModelFallbackManager()
        
            requirements = {
                "quality_needed": quality_priority.lower(),
                "speed_priority": speed_priority,
                "budget": budget_level.lower(),
                "duration": 10  # Will be updated based on actual settings
            }
        
            recommended_model = manager.get_recommended_model(requirements)
        
            # Map to checkbox states
            ken_burns = recommended_model.value == "ken_burns"
            use_sora = recommended_model.value == "sora"
            use_kling = recommended_model.value == "kling"
        
            from ai_model_manager import ModelPriority
            model_info = ModelPriority.MODEL_CAPABILITIES[recommended_model]
            st.success(f"🎬 Recommended: **{model_info['name']}**")
            st.caption(f"💡 {model_info['strengths']}")
        
        elif model_selection_mode == "⚙️ Manual Selection":
            video_col1, video_col2, video_col3 = st.columns(3)
        
            with video_col1:
                ken_burns = st.checkbox(
                    "🎞️ Ken Burns Effect",
                    value=True,
                    help="Fast, free, reliable zoom/pan effects. Perfect for static product shots."
                )
                if ken_burns:
                    st.caption("✅ FREE • ⚡ Instant • 🎯 Always works")
        
            with video_col2:
                use_sora = st.checkbox(
                    "🎬 Sora-2 (OpenAI)",
                    value=False,
                    help="Premium cinematic AI video with realistic motion and complex scenes."
                )
                if use_sora:
                    st.caption("⭐ Premium • 🎥 Cinematic • 💰 $$$")
        
            with video_col3:
                use_kling = st.checkbox(
                    "✨ Kling AI",
                    value=False,
                    help="Creative animated video with smooth transitions and effects."
                )
                if use_kling:
                    st.caption("⚡ Fast • 🎨 Creative • 💰 $$")
        
            # Show comparison table
            show_comparison = st.checkbox("📊 Show Model Comparison", value=False)
            if show_comparison:
                st.markdown("""
                | Model | Quality | Speed | Cost | Best For |
                |-------|---------|-------|------|----------|
                | **Ken Burns** | ⭐⭐⭐ | ⚡⚡⚡⚡⚡ | FREE | Product showcases, quick videos |
                | **Kling AI** | ⭐⭐⭐⭐ | ⚡⚡⚡⚡ | $$ | Creative animations, social media |
                | **Sora-2** | ⭐⭐⭐⭐⭐ | ⚡⚡ | $$$ | Cinematic commercials, professional ads |
                """)
    
        else:  # Smart Fallback
            st.info("🔄 Will try multiple models automatically until one succeeds")
        
            fallback_col1, fallback_col2 = st.columns(2)
            with fallback_col1:
                quality_tier = st.selectbox(
                    "Quality Tier",
                    ["Premium", "Standard", "Fast", "Free"],
                    index=1,
                    help="Determines which models to try and in what order"
                )
            with fallback_col2:
                quality_threshold = st.slider(
                    "Min Quality Score",
                    0, 100, 65, 5,
                    help="Videos below this score will be regenerated"
                )
        
            # Show fallback order
            from ai_model_manager import ModelPriority
            tier_key = quality_tier.lower()
            fallback_order = ModelPriority.QUALITY_TIERS.get(tier_key, [])
        
            st.caption("📋 Fallback Order:")
            for i, model in enumerate(fallback_order, 1):
                model_info = ModelPriority.MODEL_CAPABILITIES[model]
                st.caption(f"  {i}. {model_info['name']} → ", end="")
            st.caption("Done!")
        
            # Enable all models in fallback order
            ken_burns = any(m.value == "ken_burns" for m in fallback_order)
            use_sora = any(m.value == "sora" for m in fallback_order)
            use_kling = any(m.value == "kling" for m in fallback_order)
        
            # Store fallback settings
            use_smart_fallback = True
            smart_fallback_tier = tier_key
            smart_fallback_threshold = quality_threshold
    
        # Quality Settings
        st.markdown("### ⚙️ Video Quality Settings")
        quality_col1, quality_col2, quality_col3 = st.columns(3)
        with quality_col1:
            video_resolution = st.selectbox(
                "Resolution",
                ["720p", "1080p", "4K"],
                index=1,
                help="Output video resolution (1080p recommended for most platforms)"
            )
        with quality_col2:
            video_fps = st.selectbox(
                "Frame Rate (FPS)",
                [24, 30, 60],
                index=1,
                help="24fps=cinematic, 30fps=standard, 60fps=smooth"
            )
        with quality_col3:
            video_bitrate = st.selectbox(
                "Bitrate Quality",
                ["Low", "Medium", "High"],
                index=1,
                help="Low=smaller files, High=better quality"
            )
    
        # Prompt Templates
        st.markdown("### 📝 Prompt Engineering")
        use_prompt_templates = st.checkbox(
            "🎨 Use Professional Prompt Templates",
            value=True,
            help="Use optimized prompt templates for consistent, high-quality results"
        )
    
        if use_prompt_templates:
            from prompt_templates import PromptTemplateLibrary, PromptEnhancer
            template_lib = PromptTemplateLibrary()
        
            template_col1, template_col2 = st.columns(2)
            with template_col1:
                video_template = st.selectbox(
                    "Video Style Template",
                    ["product_showcase", "lifestyle_commercial", "quick_promo", "cinematic_story"],
                    format_func=lambda x: template_lib.get_template("video", x)["name"],
                    help="Professional prompt template for consistent quality"
                )
            with template_col2:
                prompt_quality_level = st.selectbox(
                    "Prompt Quality Level",
                    ["medium", "high", "ultra"],
                    index=1,
                    help="Adds quality modifiers to prompts"
                )
        
            # Show template preview
            show_template_preview = st.checkbox("👁️ Show Template Preview", value=False)
            if show_template_preview:
                template_data = template_lib.get_template("video", video_template)
                st.code(template_data["template"][:500] + "...", language="text")
                st.caption(f"Variables: {', '.join(template_data['variables'][:5])}...")
        else:
            video_template = None
            prompt_quality_level = "high"
    
        # Output Presets
        st.markdown("### 📱 Platform Presets")
        preset_col1, preset_col2 = st.columns(2)
        with preset_col1:
            platform_preset = st.selectbox(
                "Quick Preset",
                ["Custom", "YouTube (16:9, 1080p, 30fps)", "Instagram (1:1, 1080p, 30fps)", 
                 "TikTok (9:16, 1080p, 30fps)", "Twitter (16:9, 720p, 30fps)"],
                help="Apply platform-optimized settings automatically"
            )
        with preset_col2:
            batch_export = st.checkbox(
                "🎯 Batch Export All Formats",
                value=False,
                help="Generate videos for all major platforms at once (YouTube, Instagram, TikTok, Twitter)"
            )
            if batch_export:
                st.caption("✅ Will generate 4 optimized videos + ZIP download")
    
        # Apply preset if selected
        if platform_preset != "Custom":
            preset_map = {
                "YouTube (16:9, 1080p, 30fps)": {"aspect": "16:9", "res": "1080p", "fps": 30},
                "Instagram (1:1, 1080p, 30fps)": {"aspect": "1:1", "res": "1080p", "fps": 30},
                "TikTok (9:16, 1080p, 30fps)": {"aspect": "9:16", "res": "1080p", "fps": 30},
                "Twitter (16:9, 720p, 30fps)": {"aspect": "16:9", "res": "720p", "fps": 30}
            }
            if platform_preset in preset_map:
                preset_settings = preset_map[platform_preset]
                video_resolution = preset_settings["res"]
                video_fps = preset_settings["fps"]
                st.info(f"📌 Preset applied: {platform_preset}")
    
        # Voice & Tone
        st.markdown("### 🎤 Voice & Tone")
        voice_col1, voice_col2 = st.columns(2)
        with voice_col1:
            video_voice_style = st.selectbox(
                "Voice Style",
                ["Professional", "Luxury", "Friendly", "Energetic"],
                help="Voice style for narration/voiceover"
            )
        with voice_col2:
            video_ad_tone = st.selectbox(
                "Ad Tone",
                ["Professional & Trustworthy", "Exciting & Dynamic", "Warm & Friendly", "Luxury & Elegant", "Fun & Playful"],
                help="Overall tone and energy of the video"
            )
    
        # Music
        st.markdown("### 🎵 Background Music")
        music_col1, music_col2 = st.columns(2)
        with music_col1:
            music_style = st.selectbox(
                "Music Genre",
                ["Cinematic", "Electronic", "Upbeat", "Ambient", "Corporate", "Hip Hop", "Jazz"],
                help="Style of background music"
            )
        with music_col2:
            music_prompt = st.text_input(
                "Music Description (optional)",
                placeholder="e.g., uplifting, dramatic, mysterious...",
                help="Additional description for music generation"
            )
    
        st.markdown("---")
    
        # ========== AI MODEL PARAMETERS ==========
        st.markdown("## 🤖 AI Model Parameters")
        st.caption("Fine-tune the AI models for maximum control over generation quality and style")
    
        # IMAGE MODEL
        with st.container():
            st.markdown("### 🎨 Image Generation (Flux)")
            st.caption("prunaai/flux-fast - Product designs and social media assets")
        
            img_col1, img_col2, img_col3 = st.columns(3)
            with img_col1:
                img_width = st.number_input("Width (px)", min_value=256, max_value=2048, value=1024, step=64, help="Image width in pixels")
                img_height = st.number_input("Height (px)", min_value=256, max_value=2048, value=1024, step=64, help="Image height in pixels")
                img_aspect_ratio = st.selectbox("Aspect Ratio", ["1:1", "16:9", "9:16", "4:3", "3:4", "21:9"], index=0, help="Override width/height with aspect ratio")
            with img_col2:
                img_guidance = st.slider("Guidance Scale", min_value=0.0, max_value=20.0, value=3.5, step=0.1, help="How closely to follow prompt (3.5 recommended)")
                img_steps = st.slider("Inference Steps", min_value=10, max_value=150, value=28, step=1, help="More steps = better quality but slower (28 default)")
                img_speed_mode = st.selectbox("Speed Mode", ["Extra Juiced 🔥 (more speed)", "Juiced ⚡ (balanced)", "Normal (quality)"], index=0, help="Speed vs quality tradeoff")
            with img_col3:
                img_seed = st.number_input("Seed (-1 = random)", value=-1, help="Use same seed for reproducible results")
                img_output_format = st.selectbox("Output Format", ["jpg", "png", "webp"], index=0, help="Image file format")
                img_output_quality = st.slider("Output Quality", min_value=1, max_value=100, value=80, help="Compression quality (jpg/webp only)")
                img_num_outputs = st.number_input("Num Outputs", min_value=1, max_value=4, value=1, help="Generate multiple variations")
    
        # VIDEO MODEL - SORA
        with st.container():
            st.markdown("### 🎬 Video Generation - Sora-2")
            st.caption("openai/sora-2 - Cinematic video with synchronized audio")
        
            sora_col1, sora_col2, sora_col3 = st.columns(3)
            with sora_col1:
                sora_aspect_ratio = st.selectbox("Sora Aspect Ratio", ["landscape", "portrait"], index=0, help="Sora-2 uses 'landscape' or 'portrait'")
                sora_seconds = st.selectbox("Duration (seconds)", [4, 8, 12], index=1, help="Sora-2 supports 4, 8, or 12 seconds")
            with sora_col2:
                sora_resolution = st.selectbox("Resolution", ["720p", "1080p"], index=1, help="Output video resolution")
                sora_seed = st.number_input("Sora Seed (-1 = random)", value=-1, help="Seed for reproducible Sora outputs")
            with sora_col3:
                sora_loop = st.checkbox("Loop Video", value=False, help="Create seamless loop (if supported)")
                sora_include_audio = st.checkbox("Generate Audio", value=True, help="Sora-2 generates synchronized audio")
    
        # VIDEO MODEL - KLING
        with st.container():
            st.markdown("### 🎞️ Video Generation - Kling")
            st.caption("kwaivgi/kling-v2.5-turbo-pro - Image-to-video with cinematic motion")
        
            kling_col1, kling_col2, kling_col3 = st.columns(3)
            with kling_col1:
                kling_aspect_ratio = st.selectbox("Kling Aspect Ratio", ["16:9", "9:16", "1:1", "4:3"], index=0, help="Video dimensions for Kling")
                kling_duration = st.number_input("Duration (seconds)", min_value=3, max_value=20, value=5, help="Kling video length (3-20s)")
            with kling_col2:
                kling_motion_level = st.slider("Motion Intensity", min_value=1, max_value=5, value=2, help="1=Subtle motion, 5=Very dynamic")
                kling_cfg_scale = st.slider("CFG Scale", min_value=0.0, max_value=20.0, value=7.5, step=0.5, help="How closely to follow prompt")
            with kling_col3:
                kling_seed = st.number_input("Kling Seed (-1 = random)", value=-1, help="Seed for reproducible Kling outputs")
                kling_negative_prompt = st.text_input("Negative Prompt", placeholder="blurry, low quality...", help="What to avoid in generation")
        
            # Kling-specific visual style (only shown if Kling is checked earlier)
            if use_kling:
                st.caption("Additional Kling settings")
                kling_visual_style = st.selectbox(
                    "Visual Style",
                    ["Cinematic", "Documentary", "Fashion", "Lifestyle", "Dramatic", "Minimalist"],
                    help="Visual treatment for animated clips"
                )
    
        # VOICE MODEL
        with st.container():
            st.markdown("### 🗣️ Voice Synthesis")
            st.caption("minimax/speech-02-hd - Professional text-to-speech with 300+ voices")
        
            voice_col1, voice_col2, voice_col3 = st.columns(3)
            with voice_col1:
                voice_preset = st.selectbox(
                    "Voice Preset",
                    ["English_Trustworth_Man", "English_CalmWoman", "English_Graceful_Lady", "English_Deep-VoicedGentleman",
                     "English_CaptivatingStoryteller", "English_ConfidentWoman", "English_Professional_Male", "English_Energetic_Female"],
                    index=0,
                    help="Pre-trained voice identity"
                )
                voice_speed = st.slider("Speed", min_value=0.5, max_value=2.0, value=1.0, step=0.05, help="Speech rate multiplier")
            with voice_col2:
                voice_pitch = st.slider("Pitch Shift", min_value=-10, max_value=10, value=0, help="Pitch adjustment (semitones)")
                voice_volume = st.slider("Volume", min_value=0.0, max_value=2.0, value=1.0, step=0.1, help="Audio volume multiplier")
            with voice_col3:
                voice_emotion = st.selectbox("Emotion", ["neutral", "happy", "sad", "excited", "calm", "angry", "fearful"], index=0, help="Emotional tone")
                voice_sample_rate = st.selectbox("Sample Rate", ["16000", "22050", "24000", "44100", "48000"], index=3, help="Audio quality (Hz)")
                voice_format = st.selectbox("Audio Format", ["mp3", "wav", "flac"], index=0, help="Output audio format")
    
        # MUSIC MODEL
        with st.container():
            st.markdown("### 🎵 Music Generation")
            st.caption("Background music and soundtrack (duration auto-calculated from video length)")
        
            music_col1, music_col2 = st.columns(2)
            with music_col1:
                music_genre = st.selectbox("Genre", ["Cinematic", "Ambient", "Electronic", "Pop", "Acoustic", "Jazz", "Hip Hop", "Rock", "Corporate"], index=0)
                music_mood = st.selectbox("Mood", ["uplifting", "dramatic", "mysterious", "energetic", "calm", "dark", "playful", "epic"], index=0)
                music_tempo = st.slider("Tempo (BPM)", min_value=60, max_value=180, value=120, help="Beats per minute")
            with music_col2:
                music_key = st.selectbox("Key", ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"], index=0)
                music_scale = st.selectbox("Scale", ["Major", "Minor", "Pentatonic", "Blues"], index=0)
                music_intensity = st.slider("Intensity", min_value=0.0, max_value=1.0, value=0.5, help="Energy level")
    
        # TEXT MODEL
        with st.container():
            st.markdown("### 🎙️ Text Generation")
            st.caption("openai/gpt-oss-120b - AI text for scripts, descriptions, and content")
        
            text_col1, text_col2 = st.columns(2)
            with text_col1:
                text_max_tokens = st.number_input("Max Tokens", min_value=50, max_value=4096, value=500, help="Maximum response length")
                text_temperature = st.slider("Temperature", min_value=0.0, max_value=2.0, value=0.75, step=0.05, help="Creativity (0=focused, 2=random)")
            with text_col2:
                text_top_p = st.slider("Top P", min_value=0.0, max_value=1.0, value=0.95, step=0.05, help="Nucleus sampling threshold")
                text_frequency_penalty = st.slider("Frequency Penalty", min_value=0.0, max_value=2.0, value=0.0, step=0.1, help="Reduce repetition")
                text_presence_penalty = st.slider("Presence Penalty", min_value=0.0, max_value=2.0, value=0.0, step=0.1, help="Encourage new topics")

        # Collate all advanced params for downstream calls
        advanced_model_params = {
            "image": {
                "width": img_width, "height": img_height, "aspect_ratio": img_aspect_ratio,
                "guidance": img_guidance, "steps": img_steps, "seed": img_seed,
                "speed_mode": img_speed_mode, "output_format": img_output_format,
                "output_quality": img_output_quality, "num_outputs": img_num_outputs
            },
            "video_quality": {
                "resolution": video_resolution,
                "fps": video_fps,
                "bitrate": video_bitrate,
                "platform_preset": platform_preset,
                "batch_export": batch_export
            },
            "model_selection": {
                "mode": model_selection_mode,
                "ken_burns": ken_burns,
                "use_sora": use_sora,
                "use_kling": use_kling,
                "smart_fallback": locals().get('use_smart_fallback', False),
                "fallback_tier": locals().get('smart_fallback_tier', 'standard'),
                "quality_threshold": locals().get('smart_fallback_threshold', 65)
            },
            "prompts": {
                "use_templates": use_prompt_templates,
                "video_template": video_template if use_prompt_templates else None,
                "quality_level": prompt_quality_level
            },
            "sora": {
                "aspect_ratio": sora_aspect_ratio, "seconds": sora_seconds, "resolution": sora_resolution,
                "seed": sora_seed, "loop": sora_loop, "include_audio": sora_include_audio
            },
            "kling": {
                "aspect_ratio": kling_aspect_ratio, "duration": kling_duration, "motion_level": kling_motion_level,
                "cfg_scale": kling_cfg_scale, "seed": kling_seed, "negative_prompt": kling_negative_prompt
            },
            "voice": {
                "voice_id": voice_preset, "speed": voice_speed, "pitch": voice_pitch,
                "volume": voice_volume, "emotion": voice_emotion, "sample_rate": voice_sample_rate,
                "format": voice_format
            },
            "music": {
                "genre": music_genre, "mood": music_mood, "tempo": music_tempo,
                "key": music_key, "scale": music_scale, "intensity": music_intensity
                # Note: duration is auto-calculated based on video length
            },
            "text": {
                "max_tokens": text_max_tokens, "temperature": text_temperature, "top_p": text_top_p,
                "frequency_penalty": text_frequency_penalty, "presence_penalty": text_presence_penalty
            }
        }

    st.markdown("---")

    estimated_time = 0
    if campaign_enabled:
        estimated_time += 2
    if product_enabled:
        estimated_time += num_products * 3
    if blog_enabled:
        estimated_time += 5
    if video_enabled:
        estimated_time += 10
    if social_enabled:
        estimated_time += 3

    col_btn, col_time = st.columns([2, 1])
    with col_btn:
        start_button = st.button(
            "🚀 Start Your Campaign",
            use_container_width=True,
            disabled=not concept_input or not any([campaign_enabled, product_enabled, blog_enabled, video_enabled, social_enabled])
        )
    with col_time:
        if estimated_time > 0:
            st.info(f"⏱️ Est. time: ~{estimated_time} min")

    if start_button:
        from abp_campaign_generator import run_campaign_generation
        run_campaign_generation(
            concept_input=concept_input,
            target_audience=target_audience,
            price_range=price_range,
            campaign_enabled=campaign_enabled,
            product_enabled=product_enabled,
            blog_enabled=blog_enabled,
            video_enabled=video_enabled,
            social_enabled=social_enabled,
            num_products=num_products,
            fast_mode=fast_mode,
            advanced_model_params=advanced_model_params,
            auto_publish_settings={
                "printify": auto_publish_printify,
                "shopify": auto_publish_shopify,
                "youtube": auto_publish_youtube,
                "email": auto_send_email,
                "twitter": auto_publish_twitter,
                "instagram": auto_publish_instagram,
                "tiktok": auto_publish_tiktok,
                "facebook": auto_publish_facebook,
                "pinterest": auto_publish_pinterest,
                "reddit": auto_publish_reddit
            },
            digital_products_enabled=digital_products_enabled,
            cross_page_mgr=cross_page_mgr,
            email_recipients=email_recipients,
            video_style=video_style,
            camera_movement=camera_movement,
            include_music=include_music,
            include_voiceover=include_voiceover,
            aspect_ratio=aspect_ratio,
            num_segments=num_segments,
            auto_use_hailuo=auto_use_hailuo,
            auto_use_ken_burns=auto_use_ken_burns,
            auto_use_luma=auto_use_luma,
            auto_use_sora=auto_use_sora,
            auto_use_kling=auto_use_kling
        )
    
    # Show recent campaigns
    if st.session_state.campaign_history:
        st.markdown("---")
        st.markdown("### 📜 Recent Campaigns")
        for campaign in reversed(st.session_state.campaign_history[-3:]):
            with st.expander(f"🎯 {campaign['concept'][:50]}... ({campaign['timestamp']})"):
                st.markdown(f"""
                **Concept:** {campaign['concept']}
            
                **Generated:**
                - Products: {campaign['products']}
                - Blog Posts: {campaign['blogs']}
                - Video: {'Yes' if campaign['video'] else 'No'}
                - Social Media: {'Yes' if campaign['social'] else 'No'}
                """)

    st.markdown("---")
    
    st.markdown("### 📋 Recent Activity")
    
    if st.session_state.campaign_history:
        for campaign in st.session_state.campaign_history[-5:]:
            campaign_title = campaign.get('concept', campaign.get('name', 'Campaign'))[:50]
            with st.expander(f"📌 {campaign_title}... - {campaign['timestamp']}"):
                st.json(campaign)
    else:
        st.info("📭 No recent activity. Start creating!")
    
    # TAB 1: TASK QUEUE (Autonomous AI Task System)
    # ========================================
