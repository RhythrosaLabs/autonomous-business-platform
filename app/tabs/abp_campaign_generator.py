from abp_imports_common import (
    st, os, time, json, requests, random, re, shutil, base64, logging,
    Path, datetime, ThreadPoolExecutor, setup_logger
)
from app.services.platform_integrations import tracked_replicate_run

# Use standard datetime alias for backward compatibility
dt = datetime
logger = setup_logger(__name__)

# Import AI Twitter poster availability flag
try:
    from ai_twitter_poster import post_to_twitter_ai
    AI_TWITTER_AVAILABLE = bool(os.getenv('ANTHROPIC_API_KEY'))
except ImportError:
    AI_TWITTER_AVAILABLE = False
    post_to_twitter_ai = None

# Import helpers
from app.services.campaign_generator_service import EnhancedCampaignGenerator
from api_service import ReplicateAPI
from printify_mockup_service import PrintifyMockupService
from shopify_service import ShopifyAPI
from app.services.blog_generator import generate_product_blog
# VideoMaker is not a class - videomaker.py is a standalone streamlit app
from app.services.social_media_automation import SocialMediaAutomation
from app.services.digital_products_service import DigitalProductsService, DigitalProductGenerator
from ai_model_manager import ModelFallbackManager
from prompt_templates import PromptTemplateLibrary
from app.utils.unified_storage import auto_save_generated_content
import moviepy.editor as mpe  # Don't use * import - it shadows 'time' module
import re

def strip_markdown(text: str) -> str:
    """Remove markdown formatting for platforms that don't support it (Shopify, emails)"""
    if not text:
        return text
    # Remove bold/italic asterisks
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # **bold**
    text = re.sub(r'\*([^*]+)\*', r'\1', text)      # *italic*
    # Remove inline code backticks
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # Remove headers
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove bullet points at line start
    text = re.sub(r'^[\*\-]\s+', '', text, flags=re.MULTILINE)
    return text

from platform_helpers import (
    _get_replicate_token,
    create_campaign_directory,
    save_campaign_metadata,
    _slugify,
    _extract_article_html,
    _get_printify_api,
    _resolve_campaign_printify_config,
    _build_default_printify_config,
    _send_design_to_printify
)
from modules import save_text_file
from modules.file_utils import save_binary_file

# Try to import tracked_replicate_run, with fallback to regular replicate.run
try:
    from platform_integrations import tracked_replicate_run
    TRACKED_REPLICATE_AVAILABLE = True
except (ImportError, Exception):
    TRACKED_REPLICATE_AVAILABLE = False
    def tracked_replicate_run(client, model, input_params, operation_name=None):
        """Fallback to regular replicate.run if platform_integrations unavailable"""
        return client.run(model, input=input_params)

from abp_campaign_results import render_campaign_complete_summary

def run_campaign_generation(
    concept_input,
    target_audience,
    price_range,
    campaign_enabled,
    product_enabled,
    blog_enabled,
    video_enabled,
    social_enabled,
    num_products,
    fast_mode,
    advanced_model_params,
    auto_publish_settings,
    digital_products_enabled,
    cross_page_mgr,
    email_recipients="",
    video_style="Cinematic",
    camera_movement="Smooth Pan",
    include_music=True,
    include_voiceover=True,
    aspect_ratio="16:9",
    num_segments=3,
    auto_use_hailuo=True,
    auto_use_ken_burns=False,
    auto_use_luma=False,
    auto_use_sora=False,
    auto_use_kling=False
):
    """
    Runs the full autonomous campaign generation process.
    """
    
    # Unpack auto_publish_settings
    auto_publish_printify = auto_publish_settings.get('printify', False)
    auto_publish_shopify = auto_publish_settings.get('shopify', False)
    auto_publish_youtube = auto_publish_settings.get('youtube', False)
    auto_send_email = auto_publish_settings.get('email', False)
    auto_publish_twitter = auto_publish_settings.get('twitter', False)
    auto_publish_instagram = auto_publish_settings.get('instagram', False)
    auto_publish_tiktok = auto_publish_settings.get('tiktok', False)
    auto_publish_facebook = auto_publish_settings.get('facebook', False)
    auto_publish_pinterest = auto_publish_settings.get('pinterest', False)
    auto_publish_reddit = auto_publish_settings.get('reddit', False)
    
    st.markdown("---")
    st.markdown("## 🎬 Campaign Generation In Progress")

    campaign_dir = create_campaign_directory(concept_input)
    st.info(f"📁 Campaign files will be saved to: `{campaign_dir}`")
        
    # Save campaign state immediately so it persists across page switches
    campaign_state = {
        'campaign_active': True,
        'campaign_dir': str(campaign_dir),
        'concept_input': concept_input,
        'target_audience': target_audience,
        'started_at': dt.now().isoformat(),
        'campaign_enabled': campaign_enabled,
        'product_enabled': product_enabled,
        'blog_enabled': blog_enabled,
        'video_enabled': video_enabled,
        'social_enabled': social_enabled,
        'num_products': num_products,
        'current_step': 0,
        'total_steps': 0,
        'status': 'initializing',
        'progress_message': 'Starting campaign generation...'
    }
    st.session_state['active_campaign'] = campaign_state
    cross_page_mgr.save_page_state("main_dashboard", campaign_state)

    replicate_token = _get_replicate_token()

    if not replicate_token:
        st.error("❌ CRITICAL ERROR: NO REPLICATE API TOKEN")
        st.error("🔴 This platform REQUIRES a valid Replicate API key to function")
        st.error("📝 Add REPLICATE_API_TOKEN to your .env file OR go to Settings page")
        st.warning("Get your API key at: https://replicate.com/account/api-tokens")
        st.stop()

    try:
        from api_service import ReplicateAPI

        replicate_api = ReplicateAPI(replicate_token)
        st.success(f"✅ Replicate API connected! Token ends with: ...{replicate_token[-8:]}")
    except Exception as exc:
        st.error(f"❌ FAILED to initialize Replicate API: {exc}")
        st.error("Check that your API token is valid")
        st.exception(exc)
        st.stop()

    # Check if digital products are enabled
    digital_config = st.session_state.get('digital_products_config', {})
    digital_products_step = 1 if (digital_config.get('enabled') and digital_products_enabled) else 0

    total_steps = sum([
        1 if campaign_enabled else 0,
        num_products if product_enabled else 0,
        1 if product_enabled else 0,
        1 if blog_enabled else 0,
        1 if (blog_enabled and auto_publish_shopify) else 0,  # Shopify blog publish
        1 if video_enabled else 0,
        1 if social_enabled else 0,
        1 if (auto_publish_twitter and social_enabled) else 0,  # Twitter auto-post
        1 if auto_send_email else 0,  # Email campaign (not dependent on social_enabled)
        digital_products_step  # Digital products generation
    ])
    
    # Ensure total_steps is at least 1 to avoid division by zero
    total_steps = max(total_steps, 1)

    # Enhanced progress tracking
    start_time = time.time()
    progress_bar = st.progress(0)
    status_container = st.container()
    with status_container:
        status_col1, status_col2, status_col3 = st.columns([3, 1, 1])
        with status_col1:
            status_text = st.empty()
        with status_col2:
            elapsed_display = st.empty()
        with status_col3:
            eta_display = st.empty()
    
    def safe_progress(step, total):
        """Safely update progress bar, clamping to [0, 1]"""
        progress_bar.progress(min(1.0, max(0.0, step / total)))
        
    # Use a mutable container for current_step so nested function can modify it
    progress_state = {'current_step': 0, 'step_times': []}
        
    def update_progress(step_num, step_name, step_start=None):
        """Update progress with ETA calculation and cross-page state persistence"""
        progress_state['current_step'] = step_num
        current_step = step_num
        progress_bar.progress(min(current_step / total_steps, 1.0))
        status_text.markdown(f"**Step {current_step}/{total_steps}:** {step_name}")
            
        elapsed = time.time() - start_time
        elapsed_display.markdown(f"⏱️ **{elapsed:.0f}s**")
            
        if step_start and progress_state['step_times']:
            avg_step_time = sum(progress_state['step_times']) / len(progress_state['step_times'])
            remaining_steps = total_steps - current_step
            eta = avg_step_time * remaining_steps
            eta_display.markdown(f"🎯 **~{eta:.0f}s left**")
            
        if step_start:
            progress_state['step_times'].append(time.time() - step_start)
            
        # Persist progress to cross-page state
        if 'active_campaign' in st.session_state:
            st.session_state['active_campaign'].update({
                'current_step': step_num,
                'total_steps': total_steps,
                'progress_message': step_name,
                'elapsed_seconds': elapsed,
                'status': 'running'
            })
            cross_page_mgr.save_page_state("main_dashboard", st.session_state['active_campaign'])
        
    current_step = 0  # Keep for backwards compatibility

    results = {
        'campaign_plan': None,
        'products': [],
        'blog_posts': [],
        'videos': [],
        'social_posts': [],
        'campaign_dir': str(campaign_dir),
        'fast_mode': fast_mode
    }

    if campaign_enabled:
        step_start = time.time()
        update_progress(1, "📊 Executing Campaign Workflow...")

        with st.spinner("🚀 Initializing campaign generator..."):
                # Initialize enhanced campaign generator with fast_mode
                enhanced_generator = EnhancedCampaignGenerator(replicate_api, skip_enhancement=fast_mode)
                    
                # Extract budget from price_range
                budget_amount = 5000.0  # Default
                if "$" in price_range:
                    numbers = re.findall(r'\d+', price_range)
                    if numbers:
                        budget_amount = float(numbers[-1]) * 100
                    
                # Determine platforms based on concept
                platforms = ["Facebook", "Instagram", "Twitter"]
                    
                if fast_mode:
                    st.info("⚡ Fast Mode: Skipping enhancement steps for speed")
                else:
                    st.info("✨ Using sophisticated 12-step workflow with intermediate analysis...")
                    
                # Create progress container for detailed updates
                campaign_progress = st.container()
                    
                with campaign_progress:
                    # Step 1: Campaign Concept
                    with st.spinner("📝 Step 1/12: Generating campaign concept..."):
                        concept, analyzed_concept = enhanced_generator.generate_campaign_concept(
                            concept_input, target_audience, str(budget_amount), platforms
                        )
                        st.success("✅ Step 1: Campaign concept generated and analyzed")
                        results['campaign_plan'] = concept
                            
                    # Step 2: Marketing Plan  
                    with st.spinner("📋 Step 2/12: Creating detailed marketing plan..."):
                        plan, analyzed_plan = enhanced_generator.generate_marketing_plan(
                            concept_input, str(budget_amount), platforms
                        )
                        st.success("✅ Step 2: Marketing plan created and enhanced")
                            
                    # Step 3: Budget Spreadsheet
                    with st.spinner("💰 Step 3/12: Generating budget allocation spreadsheet..."):
                        budget_bytes = enhanced_generator.generate_budget_spreadsheet(budget_amount)
                        budget_path = campaign_dir / "budget_spreadsheet.xlsx"
                        with open(budget_path, 'wb') as f:
                            f.write(budget_bytes)
                        st.success("✅ Step 3: Budget spreadsheet created with smart allocation")
                            
                    # Step 4: Social Media Schedule
                    with st.spinner("📅 Step 4/12: Building social media posting schedule..."):
                        schedule_bytes = enhanced_generator.generate_social_media_schedule(
                            concept, platforms, duration_weeks=4
                        )
                        schedule_path = campaign_dir / "social_media_schedule.xlsx"
                        with open(schedule_path, 'wb') as f:
                            f.write(schedule_bytes)
                        st.success("✅ Step 4: 4-week social schedule with optimal timing")
                        
                    # Steps 6-7: Audio/Video (optional, skip for speed)
                    st.info("⏭️ Steps 6-7: Audio/video logo generation (optional, skipped for speed)")
                        
                    # Step 8: Resources & Tips
                    with st.spinner("📚 Step 8/12: Generating campaign resources and tips..."):
                        resources, analyzed_resources = enhanced_generator.generate_resources_and_tips(
                            concept_input, target_audience
                        )
                        st.success("✅ Step 8: Resources and optimization tips compiled")
                            
                    # Step 9: Campaign Recap
                    with st.spinner("📊 Step 9/12: Creating campaign recap and summary..."):
                        recap, analyzed_recap = enhanced_generator.generate_campaign_recap(
                            concept_input, str(budget_amount), platforms
                        )
                        st.success("✅ Step 9: Comprehensive campaign recap generated")
                            
                    # Step 10: Master Document
                    with st.spinner("📄 Step 10/12: Compiling master document..."):
                        master_doc = enhanced_generator.create_master_document()
                        master_path = campaign_dir / "master_document.txt"
                        with open(master_path, 'w') as f:
                            f.write(master_doc)
                        st.success("✅ Step 10: Master document compiled with all assets")
                            
                    # Step 11: Create ZIP
                    with st.spinner("🗜️ Step 11/12: Packaging campaign into downloadable ZIP..."):
                        zip_buffer = enhanced_generator.create_campaign_zip(campaign_dir)
                        st.success("✅ Step 11: Campaign packaged into professional ZIP")
                            
                    # Step 12: Finalize
                    st.success("🎉 Step 12/12: Enhanced campaign generation complete!")
                    
                # Save metadata
                save_text_file(concept, str(campaign_dir / "campaign_concept.txt"))
                save_text_file(plan, str(campaign_dir / "marketing_plan.txt"))
                save_text_file(resources, str(campaign_dir / "resources_tips.txt"))
                save_text_file(recap, str(campaign_dir / "campaign_recap.txt"))
                    
                st.balloons()
                st.success("✨ Enhanced 12-step campaign workflow completed with quality analysis!")

                with st.expander("📊 Campaign Overview", expanded=True):
                    col1, col2 = st.columns(2)
                        
                    with col1:
                        st.markdown("### 🎯 Campaign Concept")
                        st.markdown(concept[:500] + "..." if len(concept) > 500 else concept)
                            
                        st.markdown("### 💰 Budget Allocation")
                        st.markdown(f"Total Budget: ${budget_amount:,.2f}")
                        st.markdown("- 30% Digital Advertising")
                        st.markdown("- 20% Content Creation")
                        st.markdown("- 15% Social Media Management")
                        st.markdown("- 15% Influencer Partnerships")
                        st.markdown("- 20% Other (Email, Tools, Creative, Contingency)")
                        
                    with col2:
                        st.markdown("### 📋 Marketing Plan")
                        st.markdown(plan[:500] + "..." if len(plan) > 500 else plan)
                            
                        st.markdown("### 📅 Social Media Schedule")
                        st.markdown(f"- **Platforms**: {', '.join(platforms)}")
                        st.markdown("- **Duration**: 4 weeks")
                        st.markdown("- **Posts**: ~84 scheduled posts")
                        st.markdown("- **Timing**: Platform-optimized")
                        
                    st.markdown("### 📚 Resources & Tips")
                    st.markdown(resources[:300] + "..." if len(resources) > 300 else resources)
                        
                    st.markdown("### 🎯 Campaign Recap")
                    st.markdown(recap[:400] + "..." if len(recap) > 400 else recap)
                    
                # Download buttons
                st.markdown("---")
                st.markdown("### 📥 Download Campaign Assets")
                    
                dl_col1, dl_col2, dl_col3, dl_col4 = st.columns(4)
                    
                with dl_col1:
                    st.download_button(
                        "💰 Budget Spreadsheet",
                        data=budget_bytes,
                        file_name="budget_spreadsheet.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                with dl_col2:
                    st.download_button(
                        "📅 Social Schedule",
                        data=schedule_bytes,
                        file_name="social_media_schedule.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                with dl_col3:
                    st.download_button(
                        "📄 Master Document",
                        data=master_doc,
                        file_name="master_document.txt",
                        mime="text/plain"
                    )
                    
                with dl_col4:
                    zip_path = campaign_dir / "complete_campaign.zip"
                    if zip_path.exists():
                        with open(zip_path, 'rb') as f:
                            st.download_button(
                                "🗜️ Complete ZIP",
                                data=f.read(),
                                file_name="complete_campaign.zip",
                                mime="application/zip"
                            )

                if product_enabled:
                    update_progress(current_step + 1, f"📦 Creating {num_products} products...")

        # ============ EXTRA AI INTELLIGENCE STEPS ============
        # Execute the enabled Extra AI steps to enhance campaign with deep research
        # IMPORTANT: These steps now focus on the PRODUCT (e.g., "a poster with husky design")
        # not just the concept (e.g., "husky made of stars")
        extra_ai_steps = st.session_state.get('extra_ai_steps', {})
        if any(extra_ai_steps.values()):
            st.markdown("---")
            st.markdown("## 🧠 Extra AI Intelligence Steps")
                
            # Get the PRODUCT context - not just the concept
            # This makes research relevant to "a poster featuring X design" instead of just "X"
            product_type_name = "product"  # Default
            try:
                printify_config = st.session_state.get('campaign_printify_config', {})
                if printify_config and printify_config.get('blueprint_title'):
                    product_type_name = printify_config.get('blueprint_title', 'product').lower()
            except (KeyError, AttributeError, TypeError):
                pass
            
            # Set product_type for use in contact finder and other components
            product_type = product_type_name
                
            # Also check if digital products are enabled
            digital_product_type = st.session_state.get('digital_product_type', '')
            is_digital_product = digital_products_enabled
                
            # Build full product context
            if is_digital_product and digital_product_type:
                product_context = f"a digital {digital_product_type} about {concept_input}"
            elif product_type_name != "product":
                product_context = f"a {product_type_name} featuring a {concept_input} design"
            else:
                product_context = f"a print-on-demand product featuring a {concept_input} design"
                
            st.info(f"🎯 Research context: **{product_context}**")
                
            extra_results = {}
            enabled_count = sum(1 for v in extra_ai_steps.values() if v)
            current_extra = 0
                
            # Helper function to call AI for each step
            def ai_research_call(prompt: str) -> str:
                """Call AI for research with rate limiting"""
                try:
                    time.sleep(12)  # Rate limit: 6 requests/min
                    result = replicate_api.generate_text(
                        prompt,
                        system_prompt="You are a business strategist and market researcher. Provide concise, actionable insights. Never mention AI or automation - write as if for a small passionate business.",
                        max_tokens=1500
                    )
                    return result if result else "Analysis not available."
                except Exception as e:
                    return f"Research failed: {str(e)[:100]}"
                
            # 1. Trend Scanning
            if extra_ai_steps.get('trend_scanning'):
                current_extra += 1
                with st.spinner(f"📈 Trend Scanning ({current_extra}/{enabled_count})..."):
                    trend_prompt = f"""Analyze current market trends for: {product_context}
                        
Target audience: {target_audience}

Provide:
1. Top 3 trending themes in this product space (with brief explanation)
2. Emerging micro-trends to leverage for this type of product
3. Declining trends to avoid
4. Viral content patterns for this product category
5. Hashtag trends with estimated reach

Keep it concise and actionable. Focus on the PRODUCT, not just the design concept."""
                        
                    trend_result = ai_research_call(trend_prompt)
                    extra_results['trends'] = trend_result
                        
                    with st.expander("📈 Trend Analysis", expanded=False):
                        st.markdown(trend_result)
                        
                    # Save to campaign directory
                    if campaign_enabled:
                        save_text_file(trend_result, str(campaign_dir / "trend_analysis.txt"))
                    st.success(f"✅ Trend scanning complete")
                
            # 2. SEO & Keyword Research
            if extra_ai_steps.get('seo_research'):
                current_extra += 1
                with st.spinner(f"🔍 SEO Research ({current_extra}/{enabled_count})..."):
                    seo_prompt = f"""Perform SEO and keyword research for: {product_context}

Target audience: {target_audience}

Provide:
1. Top 10 high-value keywords for selling this product (with estimated search volume: high/medium/low)
2. Long-tail keyword opportunities (5-7 phrases) specific to this product type
3. Competitor keywords to target
4. Content gap opportunities for product listings
5. Semantic keyword clusters
6. Featured snippet opportunities

Format as actionable recommendations for product titles, descriptions, and blog posts."""
                        
                    seo_result = ai_research_call(seo_prompt)
                    extra_results['seo'] = seo_result
                        
                    with st.expander("🔍 SEO & Keyword Research", expanded=False):
                        st.markdown(seo_result)
                        
                    if campaign_enabled:
                        save_text_file(seo_result, str(campaign_dir / "seo_research.txt"))
                    st.success(f"✅ SEO research complete")
                
            # 3. Demand Prediction
            if extra_ai_steps.get('demand_prediction'):
                current_extra += 1
                with st.spinner(f"📊 Demand Prediction ({current_extra}/{enabled_count})..."):
                    demand_prompt = f"""Predict market demand for: {product_context}

Target audience: {target_audience}

Analyze and provide:
1. Demand forecast for this specific product type (next 3, 6, 12 months)
2. Peak demand periods/seasons for this product category
3. Price sensitivity analysis for similar products
4. Market saturation level (low/medium/high)
5. Growth potential score (1-10)
6. Risk factors specific to this product type
7. Recommended pricing strategy

Focus on the actual PRODUCT being sold, not just the design concept."""
                        
                    demand_result = ai_research_call(demand_prompt)
                    extra_results['demand'] = demand_result
                        
                    with st.expander("📊 Demand Prediction", expanded=False):
                        st.markdown(demand_result)
                        
                    if campaign_enabled:
                        save_text_file(demand_result, str(campaign_dir / "demand_prediction.txt"))
                    st.success(f"✅ Demand prediction complete")
                
            # 4. A/B Testing Suggestions
            if extra_ai_steps.get('ab_testing'):
                current_extra += 1
                with st.spinner(f"🔬 A/B Testing Plan ({current_extra}/{enabled_count})..."):
                    ab_prompt = f"""Create A/B testing strategy for: {product_context}

Target audience: {target_audience}

Provide A/B test suggestions for:
1. Product listing titles (3 variations that highlight the product type)
2. Product descriptions (3 angle variations emphasizing the product's use)
3. Pricing strategies (3 price points appropriate for this product category)
4. Product photography angles to test
5. Ad copy variations (3 hooks specific to this product type)
6. Email subject lines (5 variations)
7. CTA button text variations

Focus on selling the PRODUCT, not just the design. Include expected impact and priority level."""
                        
                    ab_result = ai_research_call(ab_prompt)
                    extra_results['ab_testing'] = ab_result
                        
                    with st.expander("🔬 A/B Testing Strategy", expanded=False):
                        st.markdown(ab_result)
                        
                    if campaign_enabled:
                        save_text_file(ab_result, str(campaign_dir / "ab_testing_strategy.txt"))
                    st.success(f"✅ A/B testing plan complete")
                
            # 5. Seasonality Analysis
            if extra_ai_steps.get('seasonality'):
                current_extra += 1
                with st.spinner(f"📅 Seasonality Analysis ({current_extra}/{enabled_count})..."):
                    season_prompt = f"""Analyze seasonality for: {product_context}

Target audience: {target_audience}

Provide:
1. Best months to sell this product type (ranked 1-12)
2. Holiday tie-in opportunities for this product category (specific dates)
3. Seasonal messaging variations highlighting the product
4. Off-season strategies for this product type
5. Event-based marketing calendar
6. Gift-giving occasions where this product shines
7. Back-to-school, summer, holiday season opportunities specific to this product

Focus on when people BUY this type of product, not just when the design theme is popular."""
                        
                    season_result = ai_research_call(season_prompt)
                    extra_results['seasonality'] = season_result
                        
                    with st.expander("📅 Seasonality Analysis", expanded=False):
                        st.markdown(season_result)
                        
                    if campaign_enabled:
                        save_text_file(season_result, str(campaign_dir / "seasonality_analysis.txt"))
                    st.success(f"✅ Seasonality analysis complete")
                
            # 6. Bundle Generation Ideas
            if extra_ai_steps.get('bundle_generation'):
                current_extra += 1
                with st.spinner(f"📦 Bundle Ideas ({current_extra}/{enabled_count})..."):
                    bundle_prompt = f"""Generate product bundle ideas for: {product_context}

Target audience: {target_audience}

Create:
1. 3 themed bundle concepts that include this product type (with clever names)
2. Complementary products that pair well with this product
3. Upsell/cross-sell opportunities (what else would someone buying this want?)
4. Limited edition bundle ideas featuring this product
5. Gift set configurations with this product as the centerpiece
6. Multi-pack discount strategies
7. Pricing strategy for bundles (discount %)

Focus on bundling actual PRODUCTS together, not just designs."""
                        
                    bundle_result = ai_research_call(bundle_prompt)
                    extra_results['bundles'] = bundle_result
                        
                    with st.expander("📦 Bundle Ideas", expanded=False):
                        st.markdown(bundle_result)
                        
                    if campaign_enabled:
                        save_text_file(bundle_result, str(campaign_dir / "bundle_ideas.txt"))
                    st.success(f"✅ Bundle generation complete")
                
            # 7. Influencer Outreach List - REAL CONTACTS
            if extra_ai_steps.get('influencer_outreach'):
                current_extra += 1
                with st.spinner(f"👥 Finding Real Contacts ({current_extra}/{enabled_count})..."):
                    try:
                        # Import contact finder
                        from contact_finder_service import ContactFinderService
                            
                        # Initialize contact finder (FREE mode - no paid APIs)
                        contact_finder = ContactFinderService(
                            replicate_api=replicate_api
                        )
                            
                        # Find real contacts based on product
                        import asyncio
                        contacts = asyncio.run(contact_finder.find_contacts(
                            product_name=concept[:100],
                            product_type=product_type,
                            target_market=target_audience,
                            location="United States",
                            contact_types=["Social Media Influencer", "Content Creator", "Brand Partner"],
                            result_count=10,
                            remote=True
                        ))
                            
                        if contacts:
                            extra_results['influencers'] = contacts
                            
                            # Save contacts to persistent library
                            try:
                                contacts_dir = campaign_dir / "contacts"
                                contacts_dir.mkdir(exist_ok=True)
                                
                                # Save as JSON for library
                                import json
                                contacts_data = {
                                    'campaign': concept[:100],
                                    'product_type': product_type,
                                    'target_market': target_audience,
                                    'found_at': dt.now().isoformat(),
                                    'contacts': [c.to_dict() for c in contacts]
                                }
                                
                                contacts_file = contacts_dir / f"contacts_{dt.now().strftime('%Y%m%d_%H%M%S')}.json"
                                with open(contacts_file, 'w') as f:
                                    json.dump(contacts_data, f, indent=2)
                                
                                # Also save to global contacts library
                                global_contacts_dir = Path("library/contacts")
                                global_contacts_dir.mkdir(parents=True, exist_ok=True)
                                global_contacts_file = global_contacts_dir / f"contacts_{dt.now().strftime('%Y%m%d_%H%M%S')}.json"
                                with open(global_contacts_file, 'w') as f:
                                    json.dump(contacts_data, f, indent=2)
                                
                                # Extract emails and add to session state for email recipients
                                contact_emails = [c.channel for c in contacts if c.channel_type == 'email' and '@' in c.channel]
                                if contact_emails:
                                    if 'campaign_contact_emails' not in st.session_state:
                                        st.session_state.campaign_contact_emails = []
                                    st.session_state.campaign_contact_emails.extend(contact_emails)
                                    # Deduplicate
                                    st.session_state.campaign_contact_emails = list(dict.fromkeys(st.session_state.campaign_contact_emails))
                                
                                st.info(f"💾 Saved {len(contacts)} contacts to library (📧 {len(contact_emails)} emails added to recipient list)")
                            except Exception as save_error:
                                logger.error(f"Error saving contacts: {save_error}")
                                
                            # Display contact cards
                            with st.expander("👥 Found Contacts & Influencers", expanded=True):
                                st.markdown(f"### 📇 {len(contacts)} Real Contacts Found")
                                    
                                # Show summary metrics
                                verified_count = sum(1 for c in contacts if c.verified)
                                email_count = sum(1 for c in contacts if c.channel_type == 'email')
                                    
                                metric_cols = st.columns(3)
                                metric_cols[0].metric("Total Contacts", len(contacts))
                                metric_cols[1].metric("Verified", verified_count)
                                metric_cols[2].metric("With Email", email_count)
                                    
                                st.markdown("---")
                                    
                                # Display each contact
                                for i, contact in enumerate(contacts):
                                    st.markdown(f"**{i+1}. {contact.name}** — {contact.role} at {contact.company}")
                                    st.markdown(f"📧 **Contact:** `{contact.channel}` ({contact.channel_type})")
                                    st.markdown(f"💡 **Why:** {contact.rationale}")
                                    st.markdown(f"🎯 **Approach:** {contact.outreach_approach}")
                                    if contact.verified:
                                        st.success(f"✅ Verified ({contact.confidence:.0%} confidence)")
                                    else:
                                        st.info(f"⚠️ Unverified ({contact.confidence:.0%} confidence)")
                                    st.markdown("---")
                                    
                                # Export option
                                import pandas as pd
                                df = pd.DataFrame([c.to_dict() for c in contacts])
                                csv = df.to_csv(index=False)
                                st.download_button(
                                    label="📥 Download Contact List (CSV)",
                                    data=csv,
                                    file_name=f"contacts_{concept[:30].replace(' ', '_')}.csv",
                                    mime="text/csv"
                                )
                                
                            if campaign_enabled:
                                # Save contacts to campaign
                                import json
                                contacts_data = [c.to_dict() for c in contacts]
                                with open(campaign_dir / "contacts.json", 'w') as f:
                                    json.dump(contacts_data, f, indent=2)
                                    
                                # Also save as readable text
                                contact_text = f"# Contacts Found for {concept}\n\n"
                                for i, contact in enumerate(contacts):
                                    contact_text += f"{i+1}. {contact.name} — {contact.role} at {contact.company}\n"
                                    contact_text += f"   Contact: {contact.channel} ({contact.channel_type})\n"
                                    contact_text += f"   Verified: {'Yes' if contact.verified else 'No'} ({contact.confidence:.0%} confidence)\n"
                                    contact_text += f"   Why: {contact.rationale}\n"
                                    contact_text += f"   Approach: {contact.outreach_approach}\n\n"
                                    
                                save_text_file(contact_text, str(campaign_dir / "contacts.txt"))
                                
                            st.success(f"✅ Found {len(contacts)} real contacts")
                        else:
                            st.warning("⚠️ No contacts found. Try adjusting product description.")
                            extra_results['influencers'] = "No contacts found"
                                
                    except Exception as e:
                        logger.error(f"Contact finding error: {e}", exc_info=True)
                        st.error(f"❌ Contact search failed: {e}")
                        extra_results['influencers'] = f"Error: {e}"
                
            # 8. PR & Press Kit
            if extra_ai_steps.get('pr_press'):
                current_extra += 1
                with st.spinner(f"📰 PR & Press Kit ({current_extra}/{enabled_count})..."):
                    pr_prompt = f"""Create PR and press kit materials for: {product_context}

Target audience: {target_audience}

Generate (write as if for a small passionate startup - never mention AI):
1. Press release template for launching this product
2. Brand story pitch (compelling narrative about why we made this)
3. Key talking points (5-7 soundbites about the product)
4. FAQ section (10 questions/answers customers would ask about this product)
5. Media contact list strategy (types of outlets that cover this product category)
6. Story angles for different media types
7. Quote templates for founder/brand (genuine, not corporate)
8. Product fact sheet with specs relevant to this product type

Make it sound human and passionate - like a small team that really cares."""
                        
                    pr_result = ai_research_call(pr_prompt)
                    extra_results['pr_press'] = pr_result
                        
                    with st.expander("📰 PR & Press Kit", expanded=False):
                        st.markdown(pr_result)
                        
                    if campaign_enabled:
                        save_text_file(pr_result, str(campaign_dir / "pr_press_kit.txt"))
                    st.success(f"✅ PR & press kit complete")
                
            # 9. Analytics & Cohort Setup
            if extra_ai_steps.get('analytics_cohort'):
                current_extra += 1
                with st.spinner(f"📈 Analytics Setup ({current_extra}/{enabled_count})..."):
                    analytics_prompt = f"""Create analytics and tracking strategy for: {product_context}

Target audience: {target_audience}

Provide:
1. Key KPIs to track for this product type (with realistic benchmarks)
2. Cohort analysis framework for buyers of this product
3. Customer journey tracking points
4. Conversion funnel metrics
5. Attribution model recommendations
6. A/B test measurement plan
7. Dashboard template structure
8. Reporting cadence recommendations
9. UTM parameter strategy
10. Customer segmentation criteria

Include specific metrics and measurement methodologies."""
                        
                    analytics_result = ai_research_call(analytics_prompt)
                    extra_results['analytics'] = analytics_result
                        
                    with st.expander("📈 Analytics & Cohort Setup", expanded=False):
                        st.markdown(analytics_result)
                        
                    if campaign_enabled:
                        save_text_file(analytics_result, str(campaign_dir / "analytics_setup.txt"))
                    st.success(f"✅ Analytics setup complete")
                
            # Store extra results for later use
            results['extra_ai_research'] = extra_results
            st.success(f"🧠 All {enabled_count} Extra AI Intelligence Steps completed!")

        # ============ PRODUCT GENERATION (with parallel processing for speed) ============
        if product_enabled:
            from concurrent.futures import ThreadPoolExecutor, as_completed
                
            def generate_single_product(product_idx: int) -> dict:
                """Generate a single product image with retry logic"""
                product_data = {'id': product_idx + 1, 'status': 'pending', 'prompt': f"{concept_input}, product variation {product_idx + 1}"}
                max_retries = 2
                    
                for attempt in range(max_retries + 1):
                    try:
                        # Enhance prompt for better results
                        style_modifiers = [
                            "high quality, professional, commercial product photography",
                            "crisp detail, vibrant colors, studio lighting",
                            "clean minimalist aesthetic, premium quality"
                        ]
                            
                        design_prompt = (
                            f"{concept_input}, product variation {product_idx + 1}, "
                            f"{style_modifiers[product_idx % len(style_modifiers)]}, white background"
                        )
                            
                        # Use fast mode settings if enabled
                        img_params = advanced_model_params.get("image", {})
                        if fast_mode:
                            img_params['steps'] = min(img_params.get('steps', 28), 20)
                            img_params['speed_mode'] = "Extra Juiced 🔥 (more speed)"
                            
                        image_url = replicate_api.generate_image(
                            design_prompt,
                            width=img_params.get("width", 1024),
                            height=img_params.get("height", 1024),
                            aspect_ratio=img_params.get("aspect_ratio", "1:1"),
                            output_format=img_params.get("output_format", "png"),
                            output_quality=img_params.get("output_quality", 90),
                            guidance_scale=img_params.get("guidance", 3.5),
                            num_inference_steps=img_params.get("steps", 28),
                            seed=img_params.get("seed", -1),
                            num_outputs=1,
                            speed_mode=img_params.get("speed_mode", "Extra Juiced 🔥 (more speed)")
                        )
                            
                        if image_url:
                            image_response = requests.get(image_url, timeout=30)
                            if image_response.status_code == 200:
                                image_filename = f"product_{product_idx + 1}.png"
                                image_save_path = campaign_dir / "products" / image_filename
                                save_binary_file(image_response.content, str(image_save_path))
                                product_data['image_url'] = image_url
                                product_data['image_file'] = str(image_save_path)
                                product_data['status'] = 'created'
                                
                                # Auto-save product design to library
                                auto_save_generated_content(
                                    content_url=image_url,
                                    content_type="image",
                                    source="campaign_product_design",
                                    prompt=product_name,
                                    product_type=product_type,
                                    campaign_name=concept[:50]
                                )
                                
                                return product_data
                            
                        if attempt < max_retries:
                            time.sleep(2)  # Brief pause before retry
                                
                    except Exception as exc:
                        product_data['error'] = str(exc)
                        if attempt < max_retries:
                            time.sleep(2)
                    
                product_data['status'] = 'failed'
                # LAST-RESORT: Try a simple fallback image prompt for this product
                try:
                    fallback_prompt = f"{concept_input}, simple fallback design for product {product_idx + 1}, clean background, high contrast"
                    fb_url = replicate_api.generate_image(
                        fallback_prompt,
                        width=1024,
                        height=1024,
                        aspect_ratio="1:1",
                        output_format="png",
                        output_quality=85,
                        num_outputs=1
                    )
                    if fb_url:
                        fb_resp = requests.get(fb_url, timeout=30)
                        if fb_resp.status_code == 200:
                            image_filename = f"product_{product_idx + 1}_fallback.png"
                            image_save_path = campaign_dir / "products" / image_filename
                            save_binary_file(fb_resp.content, str(image_save_path))
                            product_data['image_url'] = fb_url
                            product_data['image_file'] = str(image_save_path)
                            product_data['status'] = 'created'
                            product_data['fallback'] = True
                            product_data.pop('error', None)
                            return product_data
                except Exception as fb_exc:
                    product_data['error'] = f"fallback_failed:{fb_exc}"

                return product_data
                
            # Generate products (parallel for multiple, sequential for single)
            product_cols = st.columns(min(num_products, 3))
                
            if num_products > 1 and not fast_mode:
                # Parallel generation for multiple products
                st.info(f"🚀 Generating {num_products} products in parallel...")
                with ThreadPoolExecutor(max_workers=min(num_products, 3)) as executor:
                    futures = {executor.submit(generate_single_product, i): i for i in range(num_products)}
                        
                    for future in as_completed(futures):
                        product_idx = futures[future]
                        product_data = future.result()
                        results['products'].append(product_data)
                            
                        col_idx = product_idx % len(product_cols)
                        with product_cols[col_idx]:
                            if product_data.get('status') == 'created':
                                st.image(product_data['image_url'], caption=f"Product {product_idx + 1}")
                                st.success("✅ Created")
                            else:
                                st.error(f"❌ Product {product_idx + 1} failed: {product_data.get('error', 'Unknown error')}")
                            
                        step_start = time.time()
                        update_progress(current_step + product_idx + 1, f"📦 Generated product {product_idx + 1}/{num_products}", step_start)
            else:
                # Sequential generation for single product or fast mode
                for i in range(num_products):
                    step_start = time.time()
                    update_progress(current_step + i + 1, f"📦 Generating product {i + 1}/{num_products}...")
                        
                    with st.spinner(f"Generating product {i + 1}/{num_products}..."):
                        product_data = generate_single_product(i)
                        results['products'].append(product_data)
                            
                        col_idx = i % len(product_cols)
                        with product_cols[col_idx]:
                            if product_data.get('status') == 'created':
                                st.image(product_data['image_url'], caption=f"Product {i + 1}")
                                st.success("✅ Created")
                            else:
                                error_msg = product_data.get('error', 'Unknown error')
                                st.error(f"❌ Product {i + 1} failed: {error_msg}")
                        
                    update_progress(current_step + i + 1, f"📦 Generated product {i + 1}/{num_products}", step_start)
                
            current_step += num_products
                
            # Post-process successful products (background removal, Printify, etc.)
            for i, product_data in enumerate(results['products']):
                if product_data.get('status') != 'created':
                    continue
                    
                # Save product info
                product_info = (
                    f"Product {i+1}: {concept_input}\n"
                    f"Variation: {i+1}\n"
                    f"Status: {product_data['status']}\n"
                    f"Prompt: {product_data.get('prompt', 'N/A')}\n"
                    f"Image: {product_data.get('image_file', 'Not generated')}\n"
                )
                save_text_file(product_info, str(campaign_dir / "products" / f"product_{i+1}_info.txt"))
                    
                col_idx = i % len(product_cols)
                with product_cols[col_idx]:
                    # Background removal (skip in fast mode for speed)
                    product_image_path = product_data.get('image_file')
                    if product_image_path and Path(product_image_path).exists() and not fast_mode:
                        try:
                            with st.spinner("🔮 Removing background..."):
                                import replicate
                                bg_client = replicate.Client(api_token=os.getenv('REPLICATE_API_TOKEN'))
                                    
                                with open(product_image_path, "rb") as img_file:
                                    bg_result = bg_client.run(
                                        "lucataco/remove-bg:95fcc2a26d3899cd6c2691c900465aaeff466285a65c14638cc5f36f34befaf1",
                                        input={"image": img_file}
                                    )
                                    
                                if bg_result:
                                    bg_removed_path = str(Path(product_image_path).parent / f"product_{i+1}_nobg.png")
                                        
                                    if isinstance(bg_result, str) and bg_result.startswith("http"):
                                        bg_response = requests.get(bg_result, timeout=30)
                                        if bg_response.status_code == 200:
                                            with open(bg_removed_path, "wb") as f:
                                                f.write(bg_response.content)
                                            product_data['image_file_original'] = product_image_path
                                            product_data['image_file'] = bg_removed_path
                                            product_image_path = bg_removed_path
                                            st.success("✅ Background removed!")
                                    elif hasattr(bg_result, 'read'):
                                        with open(bg_removed_path, "wb") as f:
                                            f.write(bg_result.read())
                                        product_data['image_file_original'] = product_image_path
                                        product_data['image_file'] = bg_removed_path
                                        product_image_path = bg_removed_path
                                        st.success("✅ Background removed!")
                        except Exception as bg_error:
                            st.caption(f"⚠️ BG removal skipped: {str(bg_error)[:50]}")
                    elif fast_mode:
                        st.caption("⚡ BG removal skipped (fast mode)")
                        
                    # Auto-publish to Printify if enabled
                    if auto_publish_printify:
                        product_image_path = product_data.get('image_file')
                        if not product_image_path or not Path(product_image_path).exists():
                            st.warning("⚠️ No product image available to send to Printify.")
                        else:
                            campaign_config = _resolve_campaign_printify_config() or _build_default_printify_config()
                            if not campaign_config:
                                st.warning("⚠️ Configure a Printify product target in Advanced Configuration before auto-publishing.")
                            else:
                                variation_label = f"{concept_input} - Product {i+1}"
                                try:
                                    with st.spinner("📤 Publishing to Printify..."):
                                        record = _send_design_to_printify(
                                            product_image_path,
                                            product_data.get('prompt', concept_input),
                                            campaign_config,
                                            variation_label
                                        )
                                    product_id = record.get('product_id')
                                    if product_id:
                                        st.success(f"✅ Published to Printify (ID: {product_id})")
                                        product_data['printify_id'] = product_id
                                        product_data['printify_published'] = record.get('published', False)
                                    else:
                                        st.warning("⚠️ Printify did not return a product ID. Check your selection and try again.")

                                    printify_api_client = _get_printify_api()
                                    shop_id = st.session_state.get('printify_shop_id')
                                    if product_id and printify_api_client and shop_id:
                                        try:
                                            with st.spinner("📸 Downloading product mockups (including lifestyle shots)..."):
                                                all_mockups = printify_api_client.get_all_product_mockups(shop_id, str(product_id))

                                                if all_mockups:
                                                    mockup_paths = []
                                                    mockup_urls = []  # Store URLs for emails/blog
                                                    lifestyle_mockups = []

                                                    for idx, mockup_info in enumerate(all_mockups):
                                                        mockup_url = mockup_info['url']
                                                        is_default = mockup_info['is_default']

                                                        mockup_response = requests.get(mockup_url, timeout=30)

                                                        if mockup_response.status_code == 200:
                                                            # Save with descriptive filename
                                                            if is_default:
                                                                mockup_filename = f"mockup_{i+1}_default.png"
                                                            else:
                                                                mockup_filename = f"mockup_{i+1}_lifestyle_{idx}.png"

                                                            mockup_path = campaign_dir / "products" / mockup_filename

                                                            with open(mockup_path, 'wb') as f:
                                                                f.write(mockup_response.content)

                                                            mockup_paths.append(str(mockup_path))
                                                            mockup_urls.append(mockup_url)

                                                            # Track lifestyle mockups separately for videos
                                                            if not is_default:
                                                                lifestyle_mockups.append(str(mockup_path))

                                                    # Store default mockup and lifestyle mockups
                                                    product_data['mockup_image'] = mockup_paths[0] if mockup_paths else None
                                                    product_data['mockup_url'] = mockup_urls[0] if mockup_urls else None  # URL for emails/blog
                                                    product_data['all_mockups'] = mockup_paths
                                                    product_data['lifestyle_mockups'] = lifestyle_mockups

                                                    st.success(f"✅ Downloaded {len(mockup_paths)} mockups ({len(lifestyle_mockups)} lifestyle)")

                                                    # Generate social media images using the product design image
                                                    product_image_path = product_data.get('image_file')
                                                    if product_image_path and Path(product_image_path).exists():
                                                        try:
                                                            with st.spinner("📱 Generating platform-specific social media images..."):
                                                                from product_promotional_content import ProductPromotionalContent

                                                                promo_generator = ProductPromotionalContent()

                                                                # Get enabled platforms from .env
                                                                enabled_platforms_str = os.getenv('ENABLED_PLATFORMS',
                                                                    'instagram_post,instagram_story,tiktok,facebook_post,pinterest')
                                                                enabled_platforms = [p.strip() for p in enabled_platforms_str.split(',')]

                                                                # Generate social media assets
                                                                social_assets = promo_generator.generate_all_social_assets(
                                                                    product_image_path,
                                                                    f"{concept_input} - Product {i+1}",
                                                                    campaign_dir,
                                                                    platforms=enabled_platforms
                                                                )

                                                                if social_assets:
                                                                    product_data['social_media_images'] = social_assets
                                                                    st.success(f"✅ Generated {len(social_assets)} social media images")

                                                                    # Show preview and add Twitter post button
                                                                    with st.expander(f"📱 View {len(social_assets)} Social Media Images", expanded=False):
                                                                        social_cols = st.columns(min(len(social_assets), 3))
                                                                        for s_idx, (platform, s_path) in enumerate(social_assets.items()):
                                                                            with social_cols[s_idx % len(social_cols)]:
                                                                                st.image(s_path, caption=platform, use_container_width=True)
                                                                                if platform.lower() == "twitter":
                                                                                    if st.button(f"🐦 Post to Twitter", key=f"post_twitter_{i+1}"):
                                                                                        tweet_caption = f"{concept_input} - Product {i+1} now available! #newproduct"
                                                                                        if AI_TWITTER_AVAILABLE:
                                                                                            with st.spinner("🤖 AI posting to Twitter..."):
                                                                                                browser_type = st.session_state.get('browser_type', os.getenv('BROWSER_TYPE', 'chrome'))
                                                                                                success = asyncio.run(post_to_twitter_ai(s_path, tweet_caption, headless=False, browser_type=browser_type))
                                                                                        else:
                                                                                            from social_media_automation import SocialMediaAutomation
                                                                                            automation = SocialMediaAutomation(headless=False)
                                                                                            success = automation.post_to_twitter(s_path, tweet_caption)
                                                                                        if success:
                                                                                            st.success("✅ Posted to Twitter!")
                                                                                        else:
                                                                                            st.error("❌ Failed to post to Twitter. Check credentials and logs.")
                                                                else:
                                                                    st.warning("⚠️ No social media images generated")
                                                        except Exception as social_error:
                                                            st.warning(f"⚠️ Social media image generation skipped: {social_error}")

                                                    # Show lifestyle mockup previews
                                                    if lifestyle_mockups:
                                                        with st.expander(f"📸 View {len(lifestyle_mockups)} Lifestyle Mockups", expanded=False):
                                                            mockup_cols = st.columns(min(len(lifestyle_mockups), 3))
                                                            for m_idx, m_path in enumerate(lifestyle_mockups):
                                                                with mockup_cols[m_idx % len(mockup_cols)]:
                                                                    st.image(m_path, caption=f"Lifestyle {m_idx+1}", use_container_width=True)

                                                    # ADD "MAKE VIDEO" BUTTON
                                                    if lifestyle_mockups:
                                                        make_video_key = f"make_video_product_{i+1}_{int(time.time())}"
                                                        if st.button(f"🎬 Make Video from Product {i+1}", key=make_video_key, use_container_width=True):
                                                            st.markdown("---")
                                                            st.markdown(f"### 🎬 Generating Videos for Product {i+1}")
                                                            st.info(f"Using {len(lifestyle_mockups)} lifestyle mockups as starting frames")

                                                            # Initialize video producer
                                                            from advanced_video_producer import AdvancedVideoProducer
                                                            producer = AdvancedVideoProducer(replicate_token)

                                                            video_outputs = []

                                                            # NEW APPROACH: Create professional commercial from static mockups
                                                            # This is MORE RELIABLE than trying to animate images with AI
                                                            with st.spinner("� Creating professional product commercial..."):
                                                                try:
                                                                    st.info(f"📸 Using {len(lifestyle_mockups)} Printify lifestyle mockups")

                                                                    from static_commercial_producer import StaticCommercialProducer

                                                                    producer = StaticCommercialProducer(replicate_token)

                                                                    # Create video output directory
                                                                    video_dir = campaign_dir / "videos"
                                                                    video_dir.mkdir(parents=True, exist_ok=True)

                                                                    video_filename = f"product_{i+1}_commercial.mp4"
                                                                    final_video_path = video_dir / video_filename

                                                                    st.info("🧠 Step 1/4: Generating commercial script with AI...")
                                                                    st.info("🎙️ Step 2/4: Creating professional voiceover...")
                                                                    st.info("🎵 Step 3/4: Generating background music...")
                                                                    st.info("🎬 Step 4/4: Assembling commercial with effects...")

                                                                    # Create commercial using the new reliable method
                                                                    # Enforce product-fidelity by passing explicit product features and brand template
                                                                    product_features = first_product.get('features') or first_product.get('attributes') or []
                                                                    brand_template = st.session_state.get('selected_brand_template')

                                                                    result = producer.create_product_commercial(
                                                                        campaign_concept=concept_input,
                                                                        product_name=first_product.get('title', concept_input),
                                                                        mockup_image_paths=lifestyle_mockups[:3],
                                                                        output_path=str(final_video_path),
                                                                        voice_style="Professional",
                                                                        product_features=product_features,
                                                                        allow_substitute_visuals=False,
                                                                        template=st.session_state.get('video_template', '3_scene_basic'),
                                                                        brand_template=brand_template,
                                                                        max_retries=2
                                                                    )

                                                                    if result and os.path.exists(result):
                                                                        video_outputs.append(result)
                                                                        st.success("✅ Professional commercial created!")
                                                                        st.video(result)
                                                                        st.info("🎯 Features: Ken Burns effects, professional voiceover, background music")

                                                                except Exception as video_err:
                                                                    st.error(f"❌ Commercial creation failed: {video_err}")
                                                                    logger.error(f"Video generation error: {video_err}")
                                                                    import traceback
                                                                    st.code(traceback.format_exc())

                                                            if video_outputs:
                                                                st.success(f"🎉 Professional commercial created featuring ACTUAL Printify mockups!")
                                                                st.info("✨ The commercial shows your real product with professional effects, voiceover, and music")
                                                else:
                                                    st.warning("⚠️ No mockup URLs available")
                                        except Exception as mockup_error:
                                            st.warning(f"⚠️ Mockup download skipped: {mockup_error}")
                                            logger.warning(f"Mockup download error: {mockup_error}")
                                    elif not shop_id:
                                        st.warning("⚠️ Printify shop ID missing - configure in Settings")
                                    elif not printify_api_client:
                                        st.warning("⚠️ Printify API token missing - configure in Settings")
                                except Exception as printify_error:
                                    st.error(f"❌ Printify publish failed: {printify_error}")
                                    product_data['printify_published'] = False

    # Product mockup processing moved to happen BEFORE Printify upload above

    if blog_enabled:
        current_step += 1
        safe_progress(current_step, total_steps)
        status_text.markdown(f"**Step {current_step}/{total_steps}:** 📰 Publishing-ready blog content...")

        try:
            from blog_generator import generate_product_blog

            with st.spinner("Generating hero images and HTML export..."):
                # Get product mockup LOCAL PATH for blog hero image (blog_generator needs file path)
                products_list = results.get('products', [])
                product_mockup_path = None
                if products_list:
                    first_product = products_list[0]
                    # Use local mockup_image path, not URL (ensure it's absolute path)
                    mockup_path = first_product.get('mockup_image')
                    if mockup_path and not Path(mockup_path).is_absolute():
                        product_mockup_path = str(Path.cwd() / mockup_path)
                    else:
                        product_mockup_path = mockup_path
                
                blog_html, blog_pdf = generate_product_blog(
                    product_name=concept_input[:60],
                    product_description=results['campaign_plan'] or concept_input,
                    tone="Professional",
                    output_dir=str(campaign_dir / "blog_posts"),
                    image_path=product_mockup_path  # Add product image to blog
                )
            st.success("✅ Blog exported with imagery")
            st.info(f"HTML saved to {blog_html}")
            if blog_pdf:
                st.info(f"PDF/Text export saved to {blog_pdf}")
            results['blog_posts'].append({'html': blog_html, 'pdf': blog_pdf})
                
            # Shopify Auto-Publish for campaign blog
            if auto_publish_shopify and blog_html:
                current_step += 1
                safe_progress(current_step, total_steps)
                st.markdown("---")
                status_text.markdown(f"**Step {current_step}/{total_steps}:** 🛍️ Publishing blog to Shopify...")
                    
                shopify_shop_url = os.getenv('SHOPIFY_SHOP_URL')
                shopify_access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
                    
                if shopify_shop_url and shopify_access_token:
                    try:
                        from shopify_service import ShopifyAPI
                        import base64
                            
                        with st.spinner("Publishing blog to Shopify..."):
                            # Read the HTML content
                            html_content = Path(blog_html).read_text()
                                
                            # Images are now hosted on Replicate CDN - no size issues!
                            blog_dir = Path(blog_html).parent
                            images_dir = blog_dir / "images"
                                
                            if images_dir.exists():
                                st.info(f"📸 Blog includes {len(list(images_dir.glob('*.png')))} Replicate-hosted images")
                                
                            # Ensure content isn't too long (Shopify limit is ~65kb for body_html)
                            if len(html_content) > 60000:
                                st.warning(f"⚠️ Blog content is {len(html_content)} chars, trimming to fit Shopify limits...")
                                html_content = html_content[:60000] + "\n</article>\n</body>\n</html>"
                                
                            # Initialize Shopify API
                            shopify_api = ShopifyAPI(
                                shop_url=shopify_shop_url,
                                access_token=shopify_access_token
                            )
                                
                            # Test connection
                            if shopify_api.test_connection():
                                st.info("✅ Connected to Shopify")
                                    
                                # Generate unique slug from concept with timestamp to avoid duplicates
                                from datetime import datetime
                                slug_base = concept_input[:40].lower().replace(' ', '-').replace('_', '-')
                                slug_base = ''.join(c for c in slug_base if c.isalnum() or c == '-')
                                timestamp_suffix = datetime.now().strftime('%Y%m%d-%H%M%S')
                                slug = f"{slug_base}-{timestamp_suffix}"
                                    
                                # Publish the blog post (strip markdown formatting)
                                try:
                                    article = shopify_api.create_blog_post(
                                        title=strip_markdown(concept_input[:100]),
                                        body_html=html_content,
                                        author="Skya",
                                        tags=["campaign", "product", "automated"],
                                        published=True,
                                        handle=slug
                                    )
                                        
                                    if article:
                                        st.success(f"✅ Blog published to Shopify!")
                                        article_url = article.get('url', f"https://{shopify_shop_url}/blogs/news/{slug}")
                                        st.info(f"🔗 View at: {article_url}")
                                        results['shopify_blog_url'] = article_url
                                    else:
                                        st.error("❌ Failed to publish blog to Shopify - API returned None")
                                except Exception as blog_error:
                                    st.error(f"❌ Blog publish error: {blog_error}")
                                    logger.error(f"Shopify blog publish error: {blog_error}")
                            else:
                                st.error("❌ Could not connect to Shopify")
                                    
                    except Exception as shopify_error:
                        st.error(f"❌ Shopify publishing failed: {shopify_error}")
                        st.exception(shopify_error)
                else:
                    st.warning("⚠️ Shopify credentials not configured in .env")
                        
        except Exception as exc:
            st.warning(f"Blog export skipped: {exc}")

    # === FALLBACK: Generate a simple design image if no products succeeded ===
    successful_products = [p for p in results.get('products', []) if p.get('status') == 'created']
    if not successful_products and (video_enabled or social_enabled):
        st.warning("⚠️ No products were created. Generating fallback design image...")
        try:
            with st.spinner("🎨 Creating fallback design image..."):
                # Generate a simple design image for video/social
                fallback_prompt = f"{concept_input}, high quality digital art, vibrant colors, professional design"
                fallback_url = replicate_api.generate_image(
                    fallback_prompt,
                    width=1024,
                    height=1024,
                    aspect_ratio="1:1",
                    output_format="png",
                    output_quality=90
                )
                
                if fallback_url:
                    fallback_response = requests.get(fallback_url, timeout=30)
                    if fallback_response.status_code == 200:
                        fallback_dir = campaign_dir / "products"
                        fallback_dir.mkdir(parents=True, exist_ok=True)
                        fallback_path = fallback_dir / "fallback_design.png"
                        with open(fallback_path, 'wb') as f:
                            f.write(fallback_response.content)
                        
                        # Add as a product
                        fallback_product = {
                            'id': 1,
                            'status': 'created',
                            'prompt': fallback_prompt,
                            'image_url': fallback_url,
                            'image_file': str(fallback_path),
                            'fallback': True
                        }
                        results['products'] = [fallback_product]
                        st.success("✅ Fallback design image created!")
                        st.image(fallback_url, caption="Fallback Design", width=300)
        except Exception as fallback_error:
            st.error(f"❌ Could not create fallback image: {fallback_error}")
            logger.error(f"Fallback image error: {fallback_error}")
        
    # Use LIFESTYLE Printify mockups for videos (showing product in real environments)
    if product_enabled and results['products']:
        current_step += 1
        safe_progress(current_step, total_steps)
        status_text.markdown(f"**Step {current_step}/{total_steps}:** 🎨 Preparing lifestyle mockups for videos...")
            
        with st.spinner("Using Printify lifestyle mockups (product in environment)..."):
            try:
                # Get first product's lifestyle mockups (showing product on walls, in rooms)
                first_product = results['products'][0]
                lifestyle_mockups = first_product.get('lifestyle_mockups', [])
                all_mockups = first_product.get('all_mockups', [])
                    
                if lifestyle_mockups:
                    # Use lifestyle mockups (product in real environment)
                    marketing_dir = campaign_dir / "marketing_images"
                    marketing_dir.mkdir(parents=True, exist_ok=True)
                        
                    # Copy lifestyle mockups to marketing folder
                    import shutil
                    lifestyle_paths = []
                        
                    for idx, lifestyle_mockup in enumerate(lifestyle_mockups):
                        if os.path.exists(lifestyle_mockup):
                            dest_path = marketing_dir / f"lifestyle_mockup_{idx+1}.png"
                            shutil.copy2(lifestyle_mockup, dest_path)
                            lifestyle_paths.append(str(dest_path))
                        
                    # Store lifestyle mockups for video generation
                    results['lifestyle_mockups_for_video'] = lifestyle_paths
                    results['product_mockup_for_video'] = lifestyle_paths[0] if lifestyle_paths else None
                        
                    st.success(f"✅ Using {len(lifestyle_paths)} Printify LIFESTYLE mockups (product in environment)!")
                    st.info("🏠 These show the ACTUAL product on walls/in rooms - perfect for videos!")
                    st.caption("ℹ️ Lifestyle previews are already shown in the product results above, so we avoid duplicating the gallery here.")
                        
                elif all_mockups:
                    # Fallback: use any available mockup
                    st.warning("⚠️ No lifestyle mockups available - using default mockup")
                    mockup_path = all_mockups[0]
                    if os.path.exists(mockup_path):
                        marketing_dir = campaign_dir / "marketing_images"
                        marketing_dir.mkdir(parents=True, exist_ok=True)
                        import shutil
                        marketing_mockup = marketing_dir / "product_mockup_base.png"
                        shutil.copy2(mockup_path, marketing_mockup)
                        results['product_mockup_for_video'] = str(marketing_mockup)
                        st.info(f"📸 Using default mockup: {os.path.basename(mockup_path)}")
                else:
                    st.warning("⚠️ No mockups available - videos will use design image instead")
                    design_image = first_product.get('image_file')
                    if design_image and os.path.exists(design_image):
                        results['product_mockup_for_video'] = design_image
                        st.info(f"📸 Using product design image: {os.path.basename(design_image)}")
                        
            except Exception as marketing_error:
                st.warning(f"⚠️ Product mockup preparation skipped: {marketing_error}")
                logger.error(f"Marketing mockup error: {marketing_error}")

    if video_enabled:
        current_step += 1
        safe_progress(current_step, total_steps)
        status_text.markdown(f"**Step {current_step}/{total_steps}:** 🎬 Generating commercial video...")

        # --- Full Commercial Video Production Pipeline ---
        try:
            # Number of video segments to generate (passed as parameter, default: 3 clips)
            
            # 1. SELECT IMAGES FOR VIDEO
            # Clip 1: Original design (animated)
            # Clips 2+: Real Printify mockups showing product with design
            video_images = []
                
            st.info("🔍 Selecting images for video...")
            
            # Check for any products with images
            products_with_images = [p for p in results.get('products', []) 
                                   if p.get('image_file') and os.path.exists(p.get('image_file', ''))]
                
            if products_with_images:
                first_product = products_with_images[0]
                    
                # FIRST CLIP: Use the original design image (the artwork itself)
                design_image = first_product.get('image_file')
                if design_image and os.path.exists(design_image):
                    video_images.append(Path(design_image))
                    st.success(f"✅ Clip 1 - Original design: {os.path.basename(design_image)}")
                    
                # REMAINING CLIPS: Use real Printify mockups
                all_mockups = first_product.get('all_mockups', [])
                for mockup_path in all_mockups:
                    if mockup_path and os.path.exists(mockup_path):
                        video_images.append(Path(mockup_path))
                        st.success(f"✅ Clip {len(video_images)} - Product mockup: {os.path.basename(mockup_path)}")
                        if len(video_images) >= num_segments:
                            break
                    
                # If we need more clips, reuse what we have
                if video_images and len(video_images) < num_segments:
                    original_count = len(video_images)
                    while len(video_images) < num_segments:
                        idx = len(video_images) % original_count
                        video_images.append(video_images[idx])
                
            # Show preview
            if video_images:
                st.markdown("---")
                st.markdown(f"### 🎬 Video clips:")
                cols = st.columns(min(len(video_images), 3))
                for idx, img_path in enumerate(video_images[:3]):
                    with cols[idx]:
                        label = "Design" if idx == 0 else "Mockup"
                        st.image(str(img_path), caption=f"Clip {idx+1}: {label}", use_container_width=True)
            else:
                st.warning("⚠️ No images available for video - skipping video generation")
                st.info("💡 Enable product generation or ensure products are created successfully for video content")
                # Skip video but don't raise exception - continue with other steps
                raise Exception("No product images available")
                
            product_name = concept_input
            brand_name = target_audience
            
            # Ensure video_style is defined at function scope for YouTube upload later
            video_style_val = video_style if video_style else "Cinematic"

            # 2. Initialize Replicate client
            import replicate
            replicate_client = replicate.Client(api_token=os.getenv('REPLICATE_API_TOKEN'))
                
            # 3. Generate CHILL script - pitch the ACTUAL PRODUCT not the design
            st.info("📝 Step 1: Writing script...")
            
            # Get product details from results
            product_type = "product"
            product_price = "$19.99"
            store_name = "our shop"
            
            if results.get('products'):
                first_product = results['products'][0]
                # Get product type from printify config
                printify_config = _resolve_campaign_printify_config() or _build_default_printify_config()
                if printify_config and printify_config.get('blueprint_title'):
                    product_type = printify_config.get('blueprint_title', 'product').lower()
                # Get price
                configured_price = printify_config.get('price', 0) if printify_config else 0
                if configured_price > 0:
                    product_price = f"${configured_price:.2f}"
            
            # Get store name from Shopify if connected
            try:
                if 'shopify_store_name' in st.session_state:
                    store_name = st.session_state['shopify_store_name']
                elif 'printify_shop_name' in st.session_state:
                    store_name = st.session_state['printify_shop_name']
            except:
                pass
                
            # Simple, chill sales pitch for the ACTUAL PRODUCT
            script_prompt = f"""Write {num_segments} SHORT lines for a chill product video. Keep it simple and real, not salesy or cheesy.

You're selling a {product_type} (price: {product_price}) from {store_name}.
Design theme: {product_name}

Write exactly {num_segments} lines, numbered:
1. Hook - grab attention (like "Check this {product_type}" or "New {product_type} just dropped") - 8-12 words max
2. Pitch - what makes it special (SUPER BRIEF - only 5-8 words, just one quick reason to buy)
3. Close - where to buy (like "Available now at {store_name}" or "Link in bio") - 6-10 words max

CRITICAL: Line 2 must be VERY SHORT (5-8 words only). Keep it SHORT. Natural. Like you're showing a friend something cool. No exclamation points. No hype words. Just chill. Focus on the PRODUCT not just the design."""
                
            # Use Llama via Replicate
            script_response = tracked_replicate_run(
                replicate_client,
                "meta/meta-llama-3-70b-instruct",
                {"prompt": script_prompt, "max_tokens": 200, "temperature": 0.8},
                operation_name="Campaign Script Generation"
            )
                
            script_text = "".join(script_response) if isinstance(script_response, list) else str(script_response)
                
            # Extract just the numbered lines
            lines = script_text.strip().split('\n')
            script_segments = []
            for line in lines:
                match = re.match(r'^\s*(\d+)[.:\)]\s*(.+)', line)
                if match:
                    content = match.group(2).strip()
                    content = re.sub(r'\*\*|\*|"|\'|`', '', content)
                    content = re.sub(r'\s+', ' ', content).strip()
                    # Remove exclamation points for chill vibe
                    content = content.replace('!', '.')
                    if len(content) > 3:
                        script_segments.append(content)
                
            script_segments = script_segments[:num_segments]
                
            # Chill defaults
            if len(script_segments) < num_segments:
                defaults = [
                    "Check this out.",
                    f"New {product_name.split()[0] if product_name else 'design'} just dropped.",
                    "Now available in the shop."
                ]
                while len(script_segments) < num_segments:
                    script_segments.append(defaults[len(script_segments) % len(defaults)])
                
            st.success(f"✅ Script written ({len(script_segments)} segments)")
            with st.expander("📜 View Script", expanded=False):
                for i, seg in enumerate(script_segments, 1):
                    st.write(f"**Segment {i}:** {seg}")

            # 3. Generate video segments - EACH WITH DIFFERENT IMAGE
            st.info("🎬 Step 2: Generating video segments...")
                
            if video_images and video_images[0]:
                st.success(f"✅ Using {len([v for v in video_images if v])} different images for visual variety")
            else:
                st.warning("⚠️ No product images - generating from text only")
                
            video_dir = campaign_dir / "videos"
            video_dir.mkdir(parents=True, exist_ok=True)
            temp_video_paths = []
                
            for i, segment in enumerate(script_segments):
                # Get the image for THIS segment (different image per segment)
                segment_image = video_images[i] if i < len(video_images) else video_images[0] if video_images else None
                    
                image_type = "original design" if i == 0 else "lifestyle mockup"
                if segment_image:
                    st.info(f"🎬 Segment {i+1}/{num_segments} using {image_type}: {segment_image.name}")
                else:
                    st.info(f"🎬 Generating segment {i+1}/{num_segments} (text-to-video)...")
                    
                # Determine shot type
                if i == 0:
                    shot_type = "hero product reveal shot"
                elif i == 1:
                    shot_type = "lifestyle product showcase in environment"
                else:
                    shot_type = "dynamic call-to-action shot"
                    
                # Build video prompt - ALL segments use REAL product mockups
                # Ensure camera_movement and video_style are defined (may be missing when running headless/background)
                camera_movement_val = camera_movement
                if not camera_movement_val:
                    camera_movement_val = os.getenv('DEFAULT_CAMERA_MOVEMENT', 'dolly-in from medium to close-up')

                camera_direction = camera_movement_val.lower().replace(" ", "_")
                
                # Ensure video_style is defined
                video_style_val = video_style if video_style else "Cinematic"
                    
                # All images are real Printify mockups with the design printed on the product
                video_prompt = (
                    f"Professional {video_style_val.lower()} commercial {shot_type}. "
                    f"KEEP THE PRODUCT EXACTLY AS SHOWN - this is the real product. "
                    f"Subtle cinematic camera movement. Do NOT change the product appearance. "
                    f"Camera: {camera_direction}. Lighting: premium studio quality. "
                    f"Style: high-end product advertising. Maintain product consistency."
                )
                    
                # Generate video based on selected model
                model_input = {}
                    
                # Hailuo is the default and recommended model for product videos
                if auto_use_hailuo:
                    if not segment_image or not segment_image.exists():
                        st.warning(f"⚠️ Hailuo requires image - skipping segment {i+1}.")
                        continue
                    model_name = "minimax/hailuo-2.3-fast"
                    st.caption(f"   → Using: {segment_image.name}")
                    model_input = {
                        "prompt": video_prompt,
                        "first_frame_image": open(str(segment_image), "rb"),
                        "duration": 6,
                        "resolution": "768p"
                    }
                elif auto_use_luma or auto_use_luma2:
                    model_name = "luma/ray"
                    model_input = {"prompt": video_prompt, "aspect_ratio": aspect_ratio}
                    if segment_image:
                        model_input["first_frame_image"] = open(str(segment_image), "rb")
                elif auto_use_kling:
                    model_name = "kwaivgi/kling-v2.5-turbo-pro"
                    model_input = {"prompt": video_prompt, "aspect_ratio": aspect_ratio, "motion_level": 4}
                    if segment_image:
                        model_input["image"] = open(str(segment_image), "rb")
                elif auto_use_sora:
                    model_name = "openai/sora-2"
                    model_input = {
                        "prompt": video_prompt,
                        "duration": 4,
                        "quality": "high",
                        "remove_watermark": True
                    }
                    if segment_image:
                        model_input["image"] = open(str(segment_image), "rb")
                elif auto_use_ken_burns:
                    if not segment_image:
                        st.warning(f"⚠️ Ken Burns requires image - skipping segment {i+1}")
                        continue
                    from modules.video_generation import generate_ken_burns_video
                    video_path = video_dir / f"segment_{i}_kenburns.mp4"
                    zoom_patterns = ["zoom_out", "zoom_in", "zoom_out", "pan_right", "pan_left"]
                    zoom_type = zoom_patterns[i % len(zoom_patterns)]
                    success = generate_ken_burns_video(
                        image_path=str(product_image_path),
                        output_path=str(video_path),
                        duration=5,
                        fps=30,
                        resolution="1080p",
                        zoom_type=zoom_type
                    )
                    if success and video_path.exists():
                        temp_video_paths.append(video_path)
                        st.success(f"✅ Segment {i+1} generated")
                    continue
                else:
                    # Default fallback to Hailuo for best product consistency
                    if product_image_path and product_image_path.exists():
                        model_name = "minimax/hailuo-2.3-fast"
                        model_input = {
                            "prompt": video_prompt,
                            "first_frame_image": open(str(product_image_path), "rb"),
                            "duration": 6,
                            "resolution": "768p"
                        }
                    else:
                        # Fallback to Luma for text-to-video if no image
                        model_name = "luma/ray"
                        model_input = {"prompt": video_prompt, "aspect_ratio": aspect_ratio}
                    
                # Generate video with Replicate
                try:
                    # Use tracked API call for cost monitoring
                    video_uri = tracked_replicate_run(
                        replicate_client,
                        model_name,
                        model_input,
                        operation_name=f"Video Generation - {model_name}"
                    )
                    video_path = video_dir / f"segment_{i}_{int(time.time())}.mp4"
                        
                    with open(video_path, "wb") as f:
                        resp = requests.get(video_uri, stream=True)
                        resp.raise_for_status()
                        for chunk in resp.iter_content(1024 * 32):
                            f.write(chunk)
                        
                    temp_video_paths.append(video_path)
                    st.success(f"✅ Segment {i+1} generated")
                except Exception as e:
                    st.warning(f"⚠️ Segment {i+1} failed: {e}")
                
            if not temp_video_paths:
                st.error("❌ No video segments generated")
                raise Exception("Video generation failed")

            # 4. Generate background music
            music_path = None
            if include_music:
                st.info("🎵 Step 3: Generating background music...")
                try:
                    total_duration = len(temp_video_paths) * 5
                    music_uri = tracked_replicate_run(
                        replicate_client,
                        "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb",
                        {
                            "prompt": f"Upbeat professional background music for {product_name} commercial",
                            "duration": min(int(total_duration), 30),
                            "model_version": "stereo-melody-large",
                            "normalization_strategy": "peak",
                            "output_format": "mp3"
                        },
                        operation_name="Campaign Music Generation"
                    )
                    music_path = video_dir / "background_music.mp3"
                    with open(music_path, "wb") as f:
                        resp = requests.get(music_uri, stream=True)
                        resp.raise_for_status()
                        for chunk in resp.iter_content(1024 * 32):
                            f.write(chunk)
                    st.success("✅ Background music generated")
                except Exception as e:
                    st.warning(f"⚠️ Music generation failed: {e}")
                
            # 5. Generate per-segment narration and overlay
            if include_voiceover:
                st.info("🎙️ Step 4: Adding narration to each segment...")
                from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
                    
                voice_map = {
                    "Wise Woman": "Wise_Woman",
                    "Friendly Person": "Friendly_Person",
                    "Inspirational Girl": "Inspirational_girl",
                    "Deep Voice Man": "Deep_Voice_Man",
                    "Calm Woman": "Calm_Woman",
                    "Casual Guy": "Casual_Guy",
                    "Lively Girl": "Lively_Girl",
                    "Patient Man": "Patient_Man"
                }
                    
                narrated_paths = []
                for seg_idx, (video_path, script_segment) in enumerate(zip(temp_video_paths, script_segments)):
                    try:
                        st.info(f"🎙️ Processing segment {seg_idx + 1}/{len(script_segments)}...")
                            
                        # AGGRESSIVE narration cleaning
                        def clean_for_voiceover(text):
                            """Clean text for natural voiceover - remove ALL AI artifacts"""
                            # Remove segment numbers/prefixes
                            text = re.sub(r'^\s*\d+[.:\)\s]+', '', text)
                            text = re.sub(r'^\s*Segment\s*\d+[:\s]*', '', text, flags=re.IGNORECASE)
                                
                            # Remove common AI response starters
                            starters = [
                                r'^Here are[^.]*[.:]?\s*',
                                r'^Here\'s[^.]*[.:]?\s*',
                                r'^Sure[^.]*[.:]?\s*',
                                r'^Absolutely[^.]*[.:]?\s*',
                                r'^Great[^.]*[.:]?\s*',
                                r'^I\'ll[^.]*[.:]?\s*',
                                r'^Let me[^.]*[.:]?\s*',
                                r'^This segment[^.]*[.:]?\s*',
                            ]
                            for starter in starters:
                                text = re.sub(starter, '', text, flags=re.IGNORECASE)
                                
                            # Remove markdown and special formatting
                            text = re.sub(r'\*\*|\*|__|_|`|#', '', text)
                            text = re.sub(r'\[|\]|\(|\)', '', text)  # Remove brackets
                                
                            # Remove emojis and special unicode
                            text = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', '', text)
                                
                            # Normalize numbers and prices for better TTS pronunciation
                            # Convert prices like $24.99 to "twenty four ninety nine"
                            text = re.sub(r'\$(\d+)\.(\d\d)', lambda m: f"{m.group(1)} {m.group(2)}", text)
                            # Convert hyphened prices 24-99 to "twenty four ninety nine"
                            text = re.sub(r'(\d+)-(\d\d)', r'\1 \2', text)
                            # Add space in prices written as 2499 (assuming cents)
                            text = re.sub(r'(?<!\d)(\d{2,3})(\d{2})(?!\d)', r'\1 \2', text)
                                
                            # Clean up punctuation
                            text = re.sub(r'[^\w\s.,!?\'\"\-]', '', text)
                            text = re.sub(r'\s+', ' ', text).strip()
                                
                            # Ensure proper ending
                            if text and not text[-1] in '.!?':
                                text += '.'
                                
                            return text
                            
                        cleaned_narration = clean_for_voiceover(script_segment)
                            
                        # Length check - keep it concise for video timing
                        if len(cleaned_narration) > 150:
                            sentences = re.split(r'(?<=[.!?])\s+', cleaned_narration)
                            cleaned_narration = ' '.join(sentences[:2])
                            if not cleaned_narration.endswith(('.', '!', '?')):
                                cleaned_narration += '.'
                            
                        # Minimum length fallback - keep it chill
                        if len(cleaned_narration) < 10:
                            fallbacks = [
                                "Check this out.",
                                "New drop.",
                                "Now available."
                            ]
                            cleaned_narration = fallbacks[seg_idx % len(fallbacks)]
                            
                        st.success(f"📝 \"{cleaned_narration}\"")
                            
                        # Use CALM emotion for chill vibe - no excited/happy nonsense
                        selected_emotion_val = "calm"
                            
                        # Generate voiceover with timeout, retry, and gTTS fallback
                        segment_voice_path = video_dir / f"narration_{seg_idx}.mp3"
                        voiceover_success = False
                            
                        # Try minimax/speech-02-hd with timeout and retry
                        for speech_attempt in range(2):  # Max 2 attempts
                            try:
                                st.info(f"🎙️ Generating speech (attempt {speech_attempt + 1}/2)...")
                                    
                                # Rate limit: wait 12s between API calls to avoid 429 errors
                                if seg_idx > 0 or speech_attempt > 0:
                                    time.sleep(12)
                                    
                                # Use threading with timeout for speech API
                                import threading
                                speech_result = {'uri': None, 'error': None}
                                    
                                def call_speech_api():
                                    try:
                                        speech_result['uri'] = tracked_replicate_run(
                                            replicate_client,
                                            "minimax/speech-02-hd",
                                            {
                                                "text": cleaned_narration,
                                                "voice_id": "Casual_Guy",
                                                "emotion": "calm",
                                                "speed": 0.9,
                                                "pitch": -1,
                                                "volume": 1,
                                                "bitrate": 128000,
                                                "channel": "mono",
                                                "sample_rate": 32000
                                            },
                                            operation_name="Campaign Speech Generation"
                                        )
                                    except Exception as e:
                                        speech_result['error'] = str(e)
                                    
                                speech_thread = threading.Thread(target=call_speech_api)
                                speech_thread.start()
                                speech_thread.join(timeout=90)  # 90 second timeout
                                    
                                if speech_thread.is_alive():
                                    st.warning(f"⚠️ Speech API timed out (attempt {speech_attempt + 1})")
                                    continue
                                    
                                if speech_result['error']:
                                    st.warning(f"⚠️ Speech API error: {speech_result['error'][:100]}")
                                    continue
                                    
                                voiceover_uri = speech_result['uri']
                                    
                                if voiceover_uri:
                                    with open(segment_voice_path, "wb") as f:
                                        resp = requests.get(voiceover_uri, stream=True, timeout=60)
                                        resp.raise_for_status()
                                        for chunk in resp.iter_content(1024 * 32):
                                            f.write(chunk)
                                    voiceover_success = True
                                    st.success(f"✅ Speech generated via Replicate API")
                                    break
                                        
                            except Exception as e:
                                st.warning(f"⚠️ Speech attempt {speech_attempt + 1} failed: {str(e)[:100]}")
                                continue
                            
                        # Fallback to gTTS if minimax failed
                        if not voiceover_success:
                            st.warning("🔄 Falling back to gTTS for narration...")
                            try:
                                from gtts import gTTS
                                tts = gTTS(text=cleaned_narration, lang='en', slow=False)
                                tts.save(str(segment_voice_path))
                                voiceover_success = True
                                st.success(f"✅ Speech generated via gTTS fallback")
                            except Exception as gtts_error:
                                st.error(f"❌ gTTS fallback failed: {gtts_error}")
                                # Skip narration for this segment - use original video
                                narrated_paths.append(video_path)
                                continue
                            
                        if not voiceover_success:
                            st.warning(f"⚠️ Skipping narration for segment {seg_idx + 1}")
                            narrated_paths.append(video_path)
                            continue
                            
                        # Use ffmpeg for reliable audio mixing (like the reference code)
                        import subprocess
                            
                        # Get video duration
                        video_clip = VideoFileClip(str(video_path))
                        video_duration = video_clip.duration
                        video_clip.close()
                            
                        st.caption(f"🎬 Video: {video_duration:.1f}s")
                            
                        # Prepare audio files with ffmpeg
                        voice_fixed = video_dir / f"voice_fixed_{seg_idx}.wav"
                        narrated_video_path = video_dir / f"segment_{seg_idx}_narrated.mp4"
                            
                        # Speed up voice by 10% and trim/pad to video length with fade
                        ffmpeg_voice_cmd = [
                            "ffmpeg", "-y",
                            "-i", str(segment_voice_path),
                            "-af", f"atempo=1.10,apad=whole_dur={video_duration},afade=t=out:st={video_duration-0.5}:d=0.5",
                            "-t", str(video_duration),
                            str(voice_fixed)
                        ]
                        subprocess.run(ffmpeg_voice_cmd, capture_output=True)
                            
                        # Combine voice with video
                        ffmpeg_combine_cmd = [
                            "ffmpeg", "-y",
                            "-i", str(video_path),
                            "-i", str(voice_fixed),
                            "-map", "0:v",
                            "-map", "1:a",
                            "-c:v", "copy",
                            "-c:a", "aac",
                            "-shortest",
                            str(narrated_video_path)
                        ]
                        result = subprocess.run(ffmpeg_combine_cmd, capture_output=True)
                            
                        if result.returncode != 0:
                            st.warning(f"⚠️ ffmpeg failed, using MoviePy fallback")
                            # Fallback to MoviePy
                            video_clip = VideoFileClip(str(video_path))
                            narration_clip = AudioFileClip(str(segment_voice_path))
                            if narration_clip.duration > video_clip.duration:
                                narration_clip = narration_clip.subclip(0, video_clip.duration - 0.3)
                            narrated_clip = video_clip.set_audio(narration_clip)
                            narrated_clip.write_videofile(str(narrated_video_path), codec="libx264", audio_codec="aac", fps=24, preset="fast", verbose=False, logger=None)
                            narrated_clip.close()
                            video_clip.close()
                            narration_clip.close()
                            
                        narrated_paths.append(narrated_video_path)
                    except Exception as e:
                        st.warning(f"⚠️ Narration {seg_idx+1} failed: {e}")
                        narrated_paths.append(video_path)
                    
                temp_video_paths = narrated_paths
                st.success(f"✅ All segments narrated!")
                
            # 6. Concatenate final commercial with CROSSFADE transitions
            st.info("🎬 Step 5: Assembling final commercial with smooth transitions...")
            from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip
                
            clips = []
            crossfade_duration = 0.5  # Half-second crossfade between clips
                
            try:
                for idx, p in enumerate(temp_video_paths):
                    clip = VideoFileClip(str(p))
                        
                    # Add fade in/out to each clip for smooth transitions
                    if idx == 0:
                        # First clip: fade out at end
                        clip = clip.crossfadeout(crossfade_duration)
                    elif idx == len(temp_video_paths) - 1:
                        # Last clip: fade in at start
                        clip = clip.crossfadein(crossfade_duration)
                    else:
                        # Middle clips: fade both
                        clip = clip.crossfadein(crossfade_duration).crossfadeout(crossfade_duration)
                        
                    clips.append(clip)
                    
                # Use compositing method for overlapping crossfades
                if len(clips) > 1:
                    final_clip = concatenate_videoclips(clips, method="compose", padding=-crossfade_duration)
                else:
                    final_clip = clips[0] if clips else None
                    
                if not final_clip:
                    raise Exception("No video clips to assemble")
                    
                # Add background music with LONGER FADES
                if include_music and music_path and music_path.exists():
                    try:
                        music_clip = AudioFileClip(str(music_path))
                        if music_clip.duration < final_clip.duration:
                            from moviepy.editor import concatenate_audioclips
                            loops = int(final_clip.duration / music_clip.duration) + 1
                            music_clip = concatenate_audioclips([music_clip] * loops)
                        music_clip = music_clip.subclip(0, final_clip.duration)
                            
                        # Apply LONGER fade-in (2s) and fade-out (3s) for smooth music
                        fade_in_duration = min(2.0, final_clip.duration * 0.15)
                        fade_out_duration = min(3.0, final_clip.duration * 0.25)
                        music_clip = music_clip.audio_fadein(fade_in_duration).audio_fadeout(fade_out_duration)
                            
                        if final_clip.audio:
                            # Mix music at 0.35 volume with voiceover
                            final_audio = CompositeAudioClip([
                                final_clip.audio,
                                music_clip.volumex(0.35)
                            ])
                            final_clip = final_clip.set_audio(final_audio)
                        else:
                            final_clip = final_clip.set_audio(music_clip.volumex(0.5))
                            
                        st.caption(f"🎵 Music: {fade_in_duration:.1f}s fade-in, {fade_out_duration:.1f}s fade-out")
                    except Exception as e:
                        st.warning(f"⚠️ Could not add music: {e}")
                    
                # Export final video with error handling
                final_video_path = video_dir / f"{product_name.replace(' ', '_')}_commercial.mp4"
                final_clip.write_videofile(
                    str(final_video_path),
                    codec="libx264",
                    audio_codec="aac",
                    fps=24,
                    preset="medium",
                    threads=2,  # Limit threads to avoid resource issues
                    logger=None  # Suppress verbose MoviePy output
                )
                    
                st.success("✅ Final commercial video complete!")
                st.video(str(final_video_path))
                
                # Auto-save to library and update Otto's memory
                auto_save_generated_content(
                    content_url=str(final_video_path),
                    content_type="video",
                    source="campaign_generator",
                    prompt=concept,
                    model="Commercial Video Pipeline",
                    product_type=product_type,
                    campaign_name=concept[:50]
                )
                
                results['videos'].append({'video': str(final_video_path), 'type': 'commercial'})
                    
            finally:
                # Always clean up clips to prevent resource leaks
                for clip in clips:
                    try:
                        clip.close()
                    except:
                        pass
                try:
                    if 'final_clip' in locals():
                        final_clip.close()
                except:
                    pass
                
            # 7. Auto-upload to YouTube
            if auto_publish_youtube:
                st.info("📺 Uploading to YouTube...")
                try:
                    from youtube_upload_service import YouTubeUploadService
                    yt_service = YouTubeUploadService()
                        
                    if yt_service.authenticate():
                        # Generate metadata with supported parameters only
                        key_benefits = f"Professional {video_style_val.lower()} commercial showcasing {product_name}"
                        metadata = yt_service.generate_viral_metadata(
                            product_name=product_name,
                            key_benefits=key_benefits,
                            target_audience=target_audience,
                            ad_tone=video_style_val
                        )
                            
                        result = yt_service.upload_commercial(
                            video_path=str(final_video_path),
                            product_name=product_name,
                            metadata=metadata,
                            privacy="unlisted"
                        )
                            
                        if result and result.get("video_id"):
                            video_id = result["video_id"]
                            st.success(f"✅ Uploaded to YouTube!")
                            st.markdown(f"🎬 **Watch:** https://youtube.com/watch?v={video_id}")
                            results['youtube_video_id'] = video_id
                        else:
                            st.error("YouTube upload failed")
                    else:
                        st.error("❌ YouTube authentication failed")
                        st.info("💡 Run `python setup_youtube.py` to authenticate")
                except Exception as e:
                    st.error(f"YouTube upload error: {e}")
                
        except Exception as video_error:
            st.error(f"❌ Video generation failed: {video_error}")
            logger.error(f"Video generation error: {video_error}", exc_info=True)
            # Continue with rest of workflow even if video fails
        
    # === END VIDEO PRODUCTION INTEGRATION ===

    if social_enabled:
        current_step += 1
        safe_progress(current_step, total_steps)
        status_text.markdown(f"**Step {current_step}/{total_steps}:** 📱 Crafting social media content...")

        with st.spinner("Creating social media assets..."):
            try:
                from campaign_helpers import generate_content
                from social_media_ad_service import SocialMediaAdService, download_and_save_ads

                platforms = ["instagram", "facebook", "twitter"]
                social_prompt = (
                f"Create compelling social media copy promoting {concept_input}. "
                "Highlight unique benefits and add hashtags."
                )
                social_content = generate_content(
                "social media post",
                social_prompt,
                "Medium",
                platforms,
                os.getenv('OPENAI_API_KEY', '')
                )
                save_text_file(social_content, str(campaign_dir / "social_media" / "social_posts.txt"))
                st.success("✅ Social media copy ready!")
                st.markdown(social_content)
                results['social_posts'].append(social_content)
                    
                # MULTI-AGENT: Generate platform-specific social media images
                # Using Flux Static Ads AI for professional ad generation
                products_with_images = [p for p in results.get('products', []) 
                                       if p.get('image_file') and os.path.exists(p.get('image_file', ''))]
                if products_with_images:
                    status_text.markdown(f"**Step {current_step}/{total_steps}:** 📱 Generating AI-powered social media ads...")

                    social_media_dir = campaign_dir / "social_media"
                    social_media_dir.mkdir(parents=True, exist_ok=True)

                    try:
                        first_product = products_with_images[0]
                        product_title = first_product.get('title', concept_input)

                        candidate_paths = [
                            first_product.get('mockup_image'),
                            (first_product.get('lifestyle_mockups') or [None])[0],
                            first_product.get('image_file')
                        ]
                        mockup_source = next((p for p in candidate_paths if p and os.path.exists(p)), None)

                        if not mockup_source:
                            st.warning("⚠️ No product mockup available for social media ads - using text-only content")
                            # Skip image ad generation, but text content was already saved above
                        else:
                            # Check for active brand template
                            brand_name = None
                            active_brand = st.session_state.get('active_brand_template')
                            if active_brand:
                                # Handle both dict and string (brand name only)
                                if isinstance(active_brand, dict):
                                    brand_name = active_brand.get('brand_name')
                                elif isinstance(active_brand, str):
                                    brand_name = active_brand
                            
                            # Determine ad style from brand or default
                            ad_style = 'lifestyle'  # Default
                            if active_brand and active_brand.get('style_keywords'):
                                style_keywords = active_brand.get('style_keywords', '').lower()
                                if 'minimal' in style_keywords:
                                    ad_style = 'minimal'
                                elif 'luxury' in style_keywords or 'premium' in style_keywords:
                                    ad_style = 'luxury'
                                elif 'bold' in style_keywords or 'vibrant' in style_keywords:
                                    ad_style = 'bold'
                                elif 'playful' in style_keywords or 'fun' in style_keywords:
                                    ad_style = 'playful'
                                elif 'tech' in style_keywords or 'modern' in style_keywords:
                                    ad_style = 'tech'
                            
                            st.info(f"🎨 Creating professional ads with text overlays ({ad_style} style)...")
                            
                            # Extract a numeric price from price_range for display on ads
                            ad_price = None
                            if "$" in price_range:
                                price_numbers = re.findall(r'\d+', price_range)
                                if price_numbers:
                                    # Use the first price as the display price
                                    ad_price = float(price_numbers[0]) + 0.99  # e.g., $20 -> $20.99
                            
                            # Extract brand colors if brand template is active
                            brand_colors = None
                            active_brand_id = st.session_state.get('active_brand_id')
                            brand_templates = st.session_state.get('brand_templates', [])
                            if active_brand_id and brand_templates:
                                active_brand = next((b for b in brand_templates if b.get('id') == active_brand_id), None)
                                if active_brand and active_brand.get('colors'):
                                    colors = active_brand['colors']
                                    brand_colors = {
                                        'primary': colors.get('primary', '#ffffff'),
                                        'secondary': colors.get('secondary', '#f0f0f0'),
                                        'accent': colors.get('accent', colors.get('primary', '#ff6b35')),
                                        'background': '#000000'
                                    }
                                    st.info(f"🎨 Using brand colors: {brand_colors.get('primary', 'default')}")
                            
                            # Use PIL-based text overlay (reliable and professional)
                            try:
                                from flux_static_ads_generator import generate_social_ads_for_product
                                
                                # Generate ads for all platforms WITH text overlays
                                social_assets = generate_social_ads_for_product(
                                    product_mockup_path=mockup_source,
                                    product_concept=concept_input,
                                    campaign_dir=campaign_dir,
                                    platforms=['instagram_post', 'instagram_story', 'facebook_post', 'twitter', 'pinterest', 'tiktok'],
                                    style=ad_style,
                                    brand_name=brand_name,
                                    price=ad_price,
                                    brand_colors=brand_colors
                                )
                                
                                if social_assets:
                                    st.success(f"✅ Generated {len(social_assets)} professional ads with headlines, CTAs & pricing!")
                                else:
                                    raise Exception("Ad generation returned no results")
                                    
                            except ImportError as ie:
                                st.warning(f"⚠️ Ad generator not available: {ie}")
                                raise Exception("Generator not available")
                            except Exception as gen_error:
                                # Fallback to basic PIL compositing (no text)
                                st.info(f"📸 Using basic compositing (error: {gen_error})")
                                
                                def build_social_asset(base_path: str, width: int, height: int, overlay_alpha: int = 85):
                                    """Create a platform-specific composite that keeps the real product visible."""
                                    base_img = Image.open(base_path).convert('RGBA')
                                    blurred_bg = ImageOps.fit(base_img, (width, height), method=Image.Resampling.LANCZOS)
                                    blurred_bg = blurred_bg.filter(ImageFilter.GaussianBlur(radius=30))
                                    dark_overlay = Image.new('RGBA', (width, height), (0, 0, 0, overlay_alpha))
                                    background = Image.alpha_composite(blurred_bg, dark_overlay)
                                    background = ImageEnhance.Brightness(background.convert('RGB')).enhance(0.9).convert('RGBA')

                                    product_layer = base_img.copy()
                                    scale = min((width * 0.82) / product_layer.width, (height * 0.82) / product_layer.height)
                                    new_size = (
                                        max(1, int(product_layer.width * scale)),
                                        max(1, int(product_layer.height * scale))
                                    )
                                    product_layer = product_layer.resize(new_size, Image.Resampling.LANCZOS)

                                    canvas = background.copy()
                                    position = ((width - new_size[0]) // 2, (height - new_size[1]) // 2)
                                    canvas.alpha_composite(product_layer, position)

                                    highlight = Image.new('RGBA', (width, height), (255, 255, 255, 18))
                                    canvas = Image.alpha_composite(canvas, highlight)
                                    return canvas.convert('RGB')

                                platforms = {
                                    'twitter': (1200, 675),
                                    'instagram_post': (1080, 1080),
                                    'facebook_post': (1200, 630),
                                    'instagram_story': (1080, 1920),
                                    'pinterest': (1000, 1500),
                                    'tiktok': (1080, 1920)
                                }

                                social_assets = {}
                                for platform_name, (width, height) in platforms.items():
                                    st.info(f"📸 Creating {platform_name.replace('_', ' ').title()} ad...")
                                    composite = build_social_asset(mockup_source, width, height)
                                    output_path = social_media_dir / f"{platform_name}_ad.png"
                                    composite.save(output_path, format='PNG', optimize=True)
                                    social_assets[platform_name] = str(output_path)

                            if social_assets:
                                results['social_media_images'] = social_assets
                                
                                # Auto-save each social media image
                                for platform, img_path in social_assets.items():
                                    auto_save_generated_content(
                                        content_url=img_path,
                                        content_type="image",
                                        source="campaign_social_media",
                                        prompt=concept,
                                        platform=platform,
                                        product_type=product_type,
                                        campaign_name=concept[:50]
                                    )
                                
                                st.success(f"✅ Generated {len(social_assets)} platform-specific social media ads!")

                                st.markdown("### 📱 AI-Generated Social Media Ads")
                                cols = st.columns(min(len(social_assets), 3))
                                for idx, (platform, img_path) in enumerate(social_assets.items()):
                                    with cols[idx % len(cols)]:
                                        st.image(img_path, caption=f"{platform.replace('_', ' ').title()}", use_container_width=True)
                            else:
                                st.warning("⚠️ No social media ads were generated")

                    except Exception as exc:
                        st.error(f"❌ Social media generation failed: {exc}")
                        logger.error(f"Social media error: {exc}", exc_info=True)
                        import traceback
                        st.code(traceback.format_exc())
                else:
                    st.info("💡 No products with images available for social media ads. Text content has been saved.")
                    
            except Exception as exc:
                st.warning(f"Social media generation skipped: {exc}")
        
    # AUTO-PUBLISH TO TWITTER
    if auto_publish_twitter and social_enabled:
        current_step += 1
        safe_progress(current_step, total_steps)
        status_text.markdown(f"**Step {current_step}/{total_steps}:** 🐦 Auto-posting to Twitter...")
            
        with st.spinner("Posting images to Twitter with AI browser control..."):
            try:
                twitter_results = []
                    
                # Post social media images to Twitter
                social_images = results.get('social_media_images', {})
                images_to_post = []
                    
                # Prioritize Twitter-specific images
                if 'twitter' in social_images:
                    images_to_post.append(social_images['twitter'])
                    
                # Add Instagram/Facebook images if available
                for platform in ['instagram_post', 'facebook_post', 'tiktok']:
                    if platform in social_images and len(images_to_post) < 3:
                        images_to_post.append(social_images[platform])
                    
                # FALLBACK: If no social images, use product mockups directly
                if not images_to_post:
                    st.info("📸 No social media images found, using product mockups for Twitter...")
                    products_list = results.get('products', [])
                        
                    # Debug: show what's available
                    logger.info(f"🔍 Looking for images in {len(products_list)} products")
                        
                    for product in products_list[:3]:
                        # Try multiple possible image keys
                        mockup = (
                            product.get('mockup_image') or 
                            product.get('image_file') or 
                            product.get('printify_mockup') or
                            product.get('lifestyle_mockups', [None])[0] if product.get('lifestyle_mockups') else None
                        )
                        if mockup and os.path.exists(str(mockup)):
                            images_to_post.append(str(mockup))
                            logger.info(f"✅ Found product image: {mockup}")
                        
                    # FALLBACK 2: Search the campaign directory for any images
                    if not images_to_post and 'campaign_dir' in dir():
                        st.info("🔍 Searching campaign folder for images...")
                        import glob
                        campaign_images = glob.glob(str(campaign_dir / "**" / "*.png"), recursive=True)
                        campaign_images += glob.glob(str(campaign_dir / "**" / "*.jpg"), recursive=True)
                        if campaign_images:
                            # Prioritize mockups
                            mockup_images = [img for img in campaign_images if 'mockup' in img.lower()]
                            product_images = [img for img in campaign_images if 'product' in img.lower()]
                            other_images = [img for img in campaign_images if img not in mockup_images and img not in product_images]
                                
                            for img in (mockup_images + product_images + other_images)[:3]:
                                images_to_post.append(img)
                                logger.info(f"✅ Found campaign image: {img}")
                    
                if not images_to_post:
                    st.warning("⚠️ No images available to post to Twitter")
                else:
                    # Check if AI Twitter poster is available
                    if not AI_TWITTER_AVAILABLE:
                        st.warning("⚠️ AI Twitter poster not available - falling back to traditional method")
                        from social_media_automation import SocialMediaAutomation
                        automation = SocialMediaAutomation(headless=False)
                        
                    for idx, img_path in enumerate(images_to_post[:3]):
                        try:
                            st.info(f"🤖 AI posting image {idx+1}/{len(images_to_post)} to Twitter...")
                                
                            # Generate AI caption
                            if AI_TWITTER_AVAILABLE:
                                # Simple caption for now - could be improved with AI caption generation
                                caption = f"Check out this amazing design! {concept_input[:100]} #Design #Art #Creative"
                            else:
                                caption = automation.generate_smart_caption(
                                    os.path.basename(img_path),
                                    concept_input
                                )
                                
                            # Post to Twitter using AI browser control
                            if AI_TWITTER_AVAILABLE:
                                browser_type = st.session_state.get('browser_type', os.getenv('BROWSER_TYPE', 'chrome'))
                                success = asyncio.run(post_to_twitter_ai(img_path, caption, headless=False, browser_type=browser_type))
                            else:
                                success = automation.post_to_twitter(img_path, caption)
                                
                            if success:
                                st.success(f"✅ Posted image {idx+1} to Twitter!")
                                twitter_results.append({'image': img_path, 'caption': caption, 'status': 'success'})
                            else:
                                st.warning(f"⚠️ Failed to post image {idx+1} - check terminal")
                                twitter_results.append({'image': img_path, 'caption': caption, 'status': 'failed'})
                                
                            # Wait between posts
                            time.sleep(3)
                                
                        except Exception as post_error:
                            st.error(f"❌ Post {idx+1} failed: {post_error}")
                            twitter_results.append({'image': img_path, 'status': 'error', 'error': str(post_error)})
                        
                    if twitter_results:
                        results['twitter_posts'] = twitter_results
                        success_count = sum(1 for r in twitter_results if r.get('status') == 'success')
                        st.success(f"✅ Posted {success_count}/{len(twitter_results)} images to Twitter!")
                    
            except Exception as twitter_error:
                st.error(f"❌ Twitter automation failed: {twitter_error}")
                st.info("💡 Twitter may require manual verification. Check Settings > Twitter Credentials")
                logger.error(f"Twitter automation error: {twitter_error}")
        
    # AUTO-POST TO OTHER SOCIAL PLATFORMS (Instagram, TikTok, Facebook, Pinterest, Reddit)
    social_platforms = st.session_state.get('social_platforms', {})
        
    # Debug: Show what platforms are enabled
    logger.info(f"🔍 Social platforms state: {social_platforms}")
        
    other_platforms_enabled = any([
        social_platforms.get('instagram'),
        social_platforms.get('tiktok'),
        social_platforms.get('facebook'),
        social_platforms.get('pinterest'),
        social_platforms.get('reddit')
    ])
        
    logger.info(f"🔍 Other platforms enabled: {other_platforms_enabled}, Social enabled: {social_enabled}")
        
    # Note: We post even if social_enabled is False - user may want to post existing images
    if other_platforms_enabled:
        current_step += 1
        safe_progress(current_step, total_steps)
        status_text.markdown(f"**Step {current_step}/{total_steps}:** 📱 Auto-posting to social platforms...")
            
        with st.spinner("Posting to multiple social platforms..."):
            try:
                from multi_platform_poster import MultiPlatformPoster
                    
                browser_type = st.session_state.get('browser_type', os.getenv('BROWSER_TYPE', 'brave'))
                multi_poster = MultiPlatformPoster(browser_type=browser_type)
                    
                # Get images to post (reuse from Twitter section)
                images_to_post = []
                products_list = results.get('products', [])
                    
                # Check for social images from generation
                social_images = results.get('social_images', {})
                for platform_key in ['instagram', 'facebook', 'pinterest', 'tiktok']:
                    platform_images = social_images.get(platform_key, [])
                    images_to_post.extend(platform_images)
                    
                # Fallback to product mockups
                if not images_to_post:
                    for product in products_list[:3]:
                        mockup = (
                            product.get('mockup_image') or 
                            product.get('image_file') or 
                            product.get('printify_mockup')
                        )
                        if mockup and os.path.exists(str(mockup)):
                            images_to_post.append(str(mockup))
                    
                # Fallback to campaign directory images
                if not images_to_post and 'campaign_dir' in dir():
                    import glob
                    campaign_images = glob.glob(str(campaign_dir / "**" / "*.png"), recursive=True)
                    campaign_images += glob.glob(str(campaign_dir / "**" / "*.jpg"), recursive=True)
                    for img in campaign_images[:3]:
                        images_to_post.append(img)
                    
                if images_to_post:
                    # Generate captions using AI
                    base_caption = f"✨ {concept_input[:100]}... Check out our latest design! #POD #Design #Art #Creative"
                    shop_url = os.getenv('SHOPIFY_SHOP_URL', '')
                    if shop_url and not shop_url.startswith('http'):
                        shop_url = f"https://{shop_url}"
                        
                    multi_platform_results = {}
                        
                    # Instagram
                    if social_platforms.get('instagram'):
                        st.info("📸 Posting to Instagram...")
                        try:
                            ig_caption = f"✨ {concept_input[:150]}\n\n#Design #Art #Creative #POD #PrintOnDemand #NewArrivals #ShopNow"
                            success = asyncio.run(multi_poster.post_to_instagram(images_to_post[0], ig_caption))
                            multi_platform_results['instagram'] = {'status': 'success' if success else 'failed'}
                            if success:
                                st.success("✅ Posted to Instagram!")
                            else:
                                st.warning("⚠️ Instagram post may need manual verification")
                        except Exception as e:
                            st.error(f"❌ Instagram failed: {e}")
                            multi_platform_results['instagram'] = {'status': 'error', 'error': str(e)}
                        
                    # Facebook
                    if social_platforms.get('facebook'):
                        st.info("👥 Posting to Facebook...")
                        try:
                            fb_caption = f"🎨 {concept_input[:200]}\n\n{shop_url if shop_url else ''}\n\n#Design #Art #Creative"
                            success = asyncio.run(multi_poster.post_to_facebook(images_to_post[0], fb_caption))
                            multi_platform_results['facebook'] = {'status': 'success' if success else 'failed'}
                            if success:
                                st.success("✅ Posted to Facebook!")
                            else:
                                st.warning("⚠️ Facebook post may need manual verification")
                        except Exception as e:
                            st.error(f"❌ Facebook failed: {e}")
                            multi_platform_results['facebook'] = {'status': 'error', 'error': str(e)}
                        
                    # TikTok
                    if social_platforms.get('tiktok'):
                        st.info("🎵 Posting to TikTok...")
                        try:
                            tt_caption = f"✨ {concept_input[:80]} #Design #Art #POD #fyp #viral"
                            success = asyncio.run(multi_poster.post_to_tiktok(images_to_post[0], tt_caption))
                            multi_platform_results['tiktok'] = {'status': 'success' if success else 'failed'}
                            if success:
                                st.success("✅ Posted to TikTok!")
                            else:
                                st.warning("⚠️ TikTok post may need manual verification")
                        except Exception as e:
                            st.error(f"❌ TikTok failed: {e}")
                            multi_platform_results['tiktok'] = {'status': 'error', 'error': str(e)}
                        
                    # Pinterest
                    if social_platforms.get('pinterest'):
                        st.info("📌 Pinning to Pinterest...")
                        try:
                            pin_title = f"{concept_input[:60]}"
                            pin_desc = f"✨ {concept_input[:200]}. Shop now at {shop_url if shop_url else 'our store'}! #Design #Art #POD"
                            success = asyncio.run(multi_poster.post_to_pinterest(
                                images_to_post[0], pin_title, pin_desc, shop_url or None
                            ))
                            multi_platform_results['pinterest'] = {'status': 'success' if success else 'failed'}
                            if success:
                                st.success("✅ Pinned to Pinterest!")
                            else:
                                st.warning("⚠️ Pinterest post may need manual verification")
                        except Exception as e:
                            st.error(f"❌ Pinterest failed: {e}")
                            multi_platform_results['pinterest'] = {'status': 'error', 'error': str(e)}
                        
                    # Reddit
                    if social_platforms.get('reddit'):
                        st.info("🤖 Posting to Reddit...")
                        try:
                            subreddits = st.session_state.get('reddit_subreddits', '').split(',')
                            subreddits = [s.strip() for s in subreddits if s.strip()]
                            if subreddits:
                                reddit_title = f"[OC] {concept_input[:200]}"
                                for subreddit in subreddits[:2]:  # Limit to 2 subreddits
                                    st.info(f"  📤 Posting to r/{subreddit}...")
                                    success = asyncio.run(multi_poster.post_to_reddit(
                                        subreddit, reddit_title, images_to_post[0]
                                    ))
                                    multi_platform_results[f'reddit_{subreddit}'] = {'status': 'success' if success else 'failed'}
                                    if success:
                                        st.success(f"✅ Posted to r/{subreddit}!")
                                    else:
                                        st.warning(f"⚠️ Reddit r/{subreddit} may need verification")
                                    time.sleep(5)  # Delay between Reddit posts
                            else:
                                st.warning("⚠️ No subreddits specified for Reddit posting")
                        except Exception as e:
                            st.error(f"❌ Reddit failed: {e}")
                            multi_platform_results['reddit'] = {'status': 'error', 'error': str(e)}
                        
                    results['multi_platform_posts'] = multi_platform_results
                        
                    # Summary
                    success_platforms = [p for p, r in multi_platform_results.items() if r.get('status') == 'success']
                    if success_platforms:
                        st.success(f"✅ Successfully posted to: {', '.join(success_platforms)}")
                else:
                    st.warning("⚠️ No images available for social posting")
                        
            except ImportError:
                st.error("❌ Multi-platform poster not available - install required dependencies")
            except Exception as social_error:
                st.error(f"❌ Multi-platform posting failed: {social_error}")
                logger.error(f"Multi-platform posting error: {social_error}")
        
    # AUTO-SEND EMAIL CAMPAIGN
    if auto_send_email and email_recipients:
        current_step += 1
        safe_progress(current_step, total_steps)
        status_text.markdown(f"**Step {current_step}/{total_steps}:** 📧 Sending email campaign...")
            
        with st.spinner("Generating and sending marketing emails..."):
            try:
                from email_marketing_service import EmailMarketingService
                    
                email_service = EmailMarketingService()
                    
                # Parse email recipients
                recipient_list = [email.strip() for email in email_recipients.split('\n') if email.strip()]
                    
                if recipient_list:
                    st.info(f"📧 Sending to {len(recipient_list)} recipients...")
                        
                    # Get product info for email (safely handle empty products list)
                    products_list = results.get('products', [])
                    product_info = products_list[0] if products_list else {}
                    # Use mockup_url (hosted by Printify) instead of local file path
                    product_image = product_info.get('mockup_url') or product_info.get('mockup_image')
                        
                    # Get shop URL
                    shop_url = os.getenv('SHOPIFY_SHOP_URL', 'https://husky-hub-2.myshopify.com')
                    if not shop_url.startswith('http'):
                        shop_url = f'https://{shop_url}'
                        
                    # Safely get product description (handle None values)
                    product_desc = results.get('campaign_plan') or concept_input or "Check out our latest product!"
                    product_desc = str(product_desc)[:500]
                        
                    product_name = str(concept_input or "New Product")[:100]
                        
                    # Send campaign with correct parameters
                    email_results = email_service.generate_and_send_campaign(
                        template_type='product_launch',
                        product_name=product_name,
                        product_description=product_desc,
                        recipients=recipient_list,
                        cta_link=shop_url,
                        product_image_url=product_image,
                        special_offer='',
                        target_audience='general consumers'
                    )
                        
                    if email_results:
                        results['email_campaign'] = email_results
                        success_count = email_results['success_count']
                        failed_count = email_results['failed_count']
                            
                        if success_count > 0:
                            st.success(f"✅ Sent {success_count} emails successfully!")
                        if failed_count > 0:
                            st.warning(f"⚠️ {failed_count} emails failed to send")
                            
                        with st.expander("📧 Email Campaign Details"):
                            st.markdown(f"**Subject:** {email_results.get('subject', 'N/A')}")
                            st.markdown(f"**Total Sent:** {success_count}/{len(recipient_list)}")
                            if email_results.get('failed_emails'):
                                st.markdown("**Failed Recipients:**")
                                for failed_email in email_results['failed_emails']:
                                    st.text(f"  - {failed_email}")
                    else:
                        st.error("❌ Email campaign failed to send")
                else:
                    st.warning("⚠️ No valid email recipients provided")
                    
            except Exception as email_error:
                st.error(f"❌ Email automation failed: {email_error}")
                st.info("💡 Check email credentials in Settings > Email Configuration")
                logger.error(f"Email automation error: {email_error}")

    # DIGITAL PRODUCTS GENERATION - FULL PRODUCT GENERATOR
    digital_config = st.session_state.get('digital_products_config', {})
    if digital_config.get('enabled') and digital_products_enabled:
        current_step += 1
        safe_progress(current_step, total_steps)
        status_text.markdown(f"**Step {current_step}/{total_steps}:** 💾 Creating complete digital products...")
            
        with st.spinner("Generating complete digital products (this may take several minutes)..."):
            try:
                # Get brand template for styling
                brand_template = st.session_state.get('selected_brand_template')
                brand_context = ""
                if brand_template:
                    brand_context = f" (Brand: {brand_template.get('name', '')}, Voice: {brand_template.get('voice', '')}, Style: {brand_template.get('image_style', '')})"
                    st.info(f"📎 Applying brand template: {brand_template.get('name', '')}")
                    
                digital_dir = campaign_dir / "digital_products"
                digital_dir.mkdir(parents=True, exist_ok=True)
                    
                product_type = digital_config.get('type', 'graphic_art')
                title = digital_config.get('title') or concept_input[:50]
                    
                # Intelligent pricing for digital products
                configured_price = digital_config.get('price', 0)
                if configured_price <= 0:
                    try:
                        from flux_static_ads_generator import calculate_smart_price
                        price, _ = calculate_smart_price(product_type, is_digital=True)
                    except (ImportError, Exception) as e:
                        logging.debug(f"Smart pricing unavailable: {e}")
                        price = 19.99  # Fallback
                else:
                    price = configured_price
                    
                auto_publish = digital_config.get('auto_publish', True)
                    
                digital_result = None
                    
                # Import generators
                if product_type in ['ebook', 'coloring_book', 'course', 'comic']:
                    try:
                        from digital_product_generator import (
                            EBookGenerator, ColoringBookGenerator, 
                            CourseGenerator, ComicBookGenerator
                        )
                        FULL_GENERATOR_AVAILABLE = True
                    except ImportError:
                        FULL_GENERATOR_AVAILABLE = False
                        st.warning("⚠️ Full product generator not available. Falling back to simple art generation.")
                        product_type = 'graphic_art'
                    
                # Generate based on type
                if product_type == 'ebook' and FULL_GENERATOR_AVAILABLE:
                    st.info(f"📚 Generating complete {digital_config.get('chapters', 5)}-chapter E-Book...")
                    generator = EBookGenerator()
                    digital_result = generator.generate_ebook(
                        topic=concept_input + brand_context,
                        title=title,
                        num_chapters=digital_config.get('chapters', 5),
                        words_per_chapter=800,
                        genre=digital_config.get('genre', 'how-to'),
                        include_images=True,
                        include_audio=digital_config.get('include_audio', False),
                        target_audience=digital_config.get('audience', 'general'),
                        progress_callback=lambda m: status_text.markdown(f"**Digital Products:** {m}")
                    )
                    
                elif product_type == 'coloring_book' and FULL_GENERATOR_AVAILABLE:
                    st.info(f"🖍️ Generating {digital_config.get('pages', 15)}-page Coloring Book...")
                    generator = ColoringBookGenerator()
                    digital_result = generator.generate_coloring_book(
                        theme=concept_input,
                        title=title,
                        num_pages=digital_config.get('pages', 15),
                        difficulty=digital_config.get('difficulty', 'adult'),
                        style=digital_config.get('style', 'line art'),
                        progress_callback=lambda m: status_text.markdown(f"**Digital Products:** {m}")
                    )
                    
                elif product_type == 'course' and FULL_GENERATOR_AVAILABLE:
                    st.info(f"🎓 Generating {digital_config.get('modules', 4)}-module Course...")
                    generator = CourseGenerator()
                    digital_result = generator.generate_course(
                        topic=concept_input + brand_context,
                        title=title,
                        num_modules=digital_config.get('modules', 4),
                        lessons_per_module=digital_config.get('lessons', 3),
                        include_slides=True,
                        include_worksheets=digital_config.get('worksheets', True),
                        include_quizzes=True,
                        include_audio=False,
                        skill_level=digital_config.get('level', 'beginner'),
                        progress_callback=lambda m: status_text.markdown(f"**Digital Products:** {m}")
                    )
                    
                elif product_type == 'comic' and FULL_GENERATOR_AVAILABLE:
                    st.info(f"💥 Generating {digital_config.get('pages', 8)}-page Comic Book...")
                    generator = ComicBookGenerator()
                    digital_result = generator.generate_comic(
                        story_concept=concept_input,
                        title=title,
                        num_pages=digital_config.get('pages', 8),
                        style=digital_config.get('style', 'western'),
                        genre=digital_config.get('genre', 'action'),
                        progress_callback=lambda m: status_text.markdown(f"**Digital Products:** {m}")
                    )
                    
                else:  # graphic_art fallback
                    from digital_products_service import DigitalProductsService, DigitalProductGenerator
                    generator = DigitalProductGenerator()
                        
                    variations = digital_config.get('variations', 3)
                    st.info(f"🎨 Generating {variations} digital art variations...")
                        
                    generated_files = generator.generate_graphic_art(
                        prompt=concept_input,
                        style='digital art, high resolution, vibrant colors',
                        output_dir=digital_dir,
                        num_variations=variations
                    )
                        
                    if generated_files:
                        digital_result = {
                            'type': 'graphic_art',
                            'files': generated_files,
                            'title': title
                        }
                    
                # Display results and publish
                if digital_result:
                    st.success(f"✅ Digital product generated: {digital_result.get('title', title)}")
                        
                    # Ensure cover image exists for Shopify (generate if missing)
                    if not digital_result.get('cover_path'):
                        st.info("🎨 Generating cover image for Shopify...")
                        try:
                            cover_prompt = f"Professional book cover design for '{title}', {product_type}, high quality, eye-catching, product mockup style"
                            cover_url = replicate_api.generate_image(
                                cover_prompt,
                                width=1024,
                                height=1536,  # Portrait ratio for covers
                                aspect_ratio="2:3",
                                output_format="png"
                            )
                            if cover_url:
                                cover_path = digital_dir / f"{product_type}_cover.png"
                                cover_response = requests.get(cover_url, timeout=60)
                                if cover_response.status_code == 200:
                                    with open(cover_path, 'wb') as f:
                                        f.write(cover_response.content)
                                    digital_result['cover_path'] = str(cover_path)
                                    st.success("✅ Cover image generated!")
                        except Exception as cover_error:
                            st.warning(f"⚠️ Could not generate cover: {cover_error}")
                        
                    # Show cover/preview
                    if digital_result.get('cover_path'):
                        st.image(digital_result['cover_path'], caption="Product Cover", width=300)
                    elif digital_result.get('files'):
                        preview_cols = st.columns(min(len(digital_result['files']), 4))
                        for idx, f in enumerate(digital_result['files'][:4]):
                            with preview_cols[idx]:
                                st.image(f, caption=f"Variation {idx+1}", use_container_width=True)
                        
                    # Auto-publish to Shopify
                    if auto_publish and digital_result.get('pdf_path'):
                        st.info("📤 Publishing to Shopify...")
                        try:
                            from digital_products_service import DigitalProductsService
                            service = DigitalProductsService()
                                
                            # Build description with brand voice
                            desc = f"<h2>{digital_result.get('title', title)}</h2>"
                            if product_type == 'ebook':
                                desc += f"<p>A complete {digital_config.get('chapters', 5)}-chapter {digital_config.get('genre', '')} e-book.</p>"
                            elif product_type == 'coloring_book':
                                desc += f"<p>A {digital_config.get('pages', 15)}-page coloring book.</p>"
                            elif product_type == 'course':
                                desc += f"<p>A comprehensive {digital_config.get('modules', 4)}-module course.</p>"
                            elif product_type == 'comic':
                                desc += f"<p>A {digital_config.get('pages', 8)}-page comic book.</p>"
                                
                            # Add brand hashtags as tags
                            tags = ['ai-generated', product_type]
                            if brand_template:
                                tags.extend([h.replace('#', '') for h in brand_template.get('hashtags', [])[:3]])
                                
                            shop_result = service.create_digital_product(
                                file_path=digital_result['pdf_path'],
                                title=digital_result.get('title', title),
                                price=price,
                                description=desc,
                                preview_image=digital_result.get('cover_path'),
                                tags=tags,
                                license_type='personal'
                            )
                                
                            if shop_result:
                                st.success(f"✅ Published to Shopify! [View Product]({shop_result.get('url', '#')})")
                                results['digital_products'] = [shop_result]
                        except Exception as pub_error:
                            st.warning(f"⚠️ Shopify publish failed: {pub_error}")
                        
                    elif auto_publish and digital_result.get('files'):
                        # Publish graphic art
                        try:
                            from digital_products_service import DigitalProductsService
                            service = DigitalProductsService()
                                
                            digital_products_created = []
                            for idx, filepath in enumerate(digital_result['files']):
                                art_title = f"{title} - Digital Art #{idx+1}" if len(digital_result['files']) > 1 else f"{title} - Digital Art"
                                    
                                result = service.create_digital_product(
                                    file_path=filepath,
                                    title=art_title,
                                    price=price,
                                    preview_image=filepath,
                                    license_type=digital_config.get('license', 'commercial'),
                                    tags=['ai-generated', 'digital-art']
                                )
                                if result:
                                    digital_products_created.append(result)
                                    st.success(f"✅ Listed: {art_title}")
                                
                            if digital_products_created:
                                results['digital_products'] = digital_products_created
                        except Exception as pub_error:
                            st.warning(f"⚠️ Shopify publish failed: {pub_error}")
                else:
                    st.warning("⚠️ Digital product generation returned no results")
                        
            except ImportError as ie:
                st.error(f"❌ Digital products service not available: {ie}")
            except Exception as dp_error:
                st.error(f"❌ Digital products creation failed: {dp_error}")
                import traceback
                logger.error(f"Digital products error: {traceback.format_exc()}")

    # ============ CAMPAIGN COMPLETE - ENHANCED SUMMARY ============
    total_time = time.time() - start_time
        
    render_campaign_complete_summary(
        results=results,
        campaign_dir=campaign_dir,
        total_time=total_time,
        num_products=num_products,
        concept_input=concept_input,
        target_audience=target_audience,
        price_range=price_range,
        fast_mode=fast_mode,
        campaign_enabled=campaign_enabled,
        product_enabled=product_enabled,
        blog_enabled=blog_enabled,
        video_enabled=video_enabled,
        social_enabled=social_enabled,
        cross_page_mgr=cross_page_mgr,
        save_campaign_metadata_func=save_campaign_metadata,
        progress_bar=progress_bar,
        status_text=status_text,
        elapsed_display=elapsed_display,
        eta_display=eta_display
    )
