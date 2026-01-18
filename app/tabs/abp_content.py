from abp_imports_common import (
    st, os, Path, datetime, json, re, asyncio, setup_logger
)

# Maintain backward compatibility alias
dt = datetime
logger = setup_logger(__name__)

from app.utils.cross_page_state import restore_page_to_session
from app.services.platform_helpers import _ensure_replicate_client, _slugify, _extract_article_html, _get_replicate_token
from app.services.blog_generator import generate_product_blog
from app.utils.brand_templates import PRESET_TEMPLATES as BRAND_TEMPLATES
from app.services.email_marketing_service import EmailMarketingService
from shopify_service import ShopifyAPI
from app.services.campaign_generator_service import EnhancedCampaignGenerator
from app.services.platform_integrations import tracked_replicate_run
from app.utils.ray_integration_helpers import ray_generate_image_sync, is_ray_enabled
from app.services.tab_job_helpers import (
    submit_blog_generation_job,
    submit_social_content_job,
    submit_batch_operation,
    collect_job_results,
    check_jobs_progress,
    are_all_jobs_done
)
from app.services.global_job_queue import JobType, get_global_job_queue

def render_content_generator_tab():
    # Restore any saved Content Generator state
    restore_page_to_session("content_generator", keys_to_restore=[
        'content_generator_results', 'selected_brand_template',
        'content_topic', 'content_style'
    ])
    
    st.markdown("### 📝 Multi-Modal Content Generator")
    st.markdown("Produce production-ready marketing assets with a single click")

    # Brand Template Selector
    with st.expander("🎨 Brand Templates", expanded=False):
        st.caption("Apply consistent brand styling to your content")
        try:
            # Try the proper import location first
            try:
                from brand_templates import BRAND_TEMPLATES, BrandTemplateManager
            except ImportError:
                # Fallback to legacy location
                from brand_brain import BRAND_TEMPLATES
                BrandTemplateManager = None
            
            if BRAND_TEMPLATES:
                template_cols = st.columns(4)
                selected_template = None
                
                for i, (template_id, template) in enumerate(BRAND_TEMPLATES.items()):
                    with template_cols[i % 4]:
                        # Show template preview card
                        colors = template.get('colors', {})
                        primary = colors.get('primary', '#6366f1')
                        st.markdown(f"""
                        <div style="background: {primary}; padding: 10px; border-radius: 8px; color: white; text-align: center; margin-bottom: 10px;">
                            <strong>{template['name']}</strong>
                        </div>
                        """, unsafe_allow_html=True)
                        st.caption(template.get('description', '')[:50] + '...')
                        if st.button(f"Use", key=f"brand_template_{template_id}"):
                            st.session_state['selected_brand_template'] = template_id
                            selected_template = template_id
                            st.success(f"✅ {template['name']} template applied!")
                
                if st.session_state.get('selected_brand_template'):
                    active = BRAND_TEMPLATES.get(st.session_state['selected_brand_template'])
                    if active:
                        st.info(f"🎨 Active template: **{active['name']}** - {active.get('tone', 'professional').title()} tone")
            else:
                st.info("No brand templates configured. Create one in the 🎨 Brand Templates tab!")
        except ImportError as e:
            st.info("💡 Create brand templates in the **🎨 Brand Templates** tab for consistent styling!")

    content_type = st.selectbox(
        "Content Type",
        ["📝 Blog Post", "📱 Social Media Post", "📧 Email Campaign", "🎯 Ad Copy"]
    )

    content_root = Path("campaigns") / "content_library"

    if content_type == "📝 Blog Post":
        st.markdown("#### Blog Post Generator")

        col_a, col_b = st.columns(2)
        with col_a:
            product_name = st.text_input("Product or Campaign Name", placeholder="EcoFlow Yoga Mat Collection")
            tone = st.selectbox("Tone", ["Professional", "Casual", "Inspirational", "Educational", "Playful"])
        with col_b:
            product_description = st.text_area(
                "Key Details",
                placeholder="Describe the product, audience, benefits, and differentiators...",
                height=140
            )

        hero_upload = st.file_uploader("Optional hero image", type=["png", "jpg", "jpeg"])
        
        # Shopify auto-publish option
        st.markdown("---")
        st.markdown("#### 🛍️ Shopify Auto-Publish")
        publish_to_shopify = st.checkbox("📤 Auto-publish to Shopify Blog", value=False, 
                                         help="Automatically publish this blog post to your Shopify store")
        
        shopify_blog_tags = ""
        shopify_author = "Skya"
        
        if publish_to_shopify:
            shopify_col1, shopify_col2 = st.columns(2)
            with shopify_col1:
                shopify_blog_tags = st.text_input("Blog Tags (comma-separated)", 
                                                  placeholder="product, launch, eco-friendly",
                                                  help="Tags help categorize your blog posts")
            with shopify_col2:
                shopify_author = st.text_input("Author Name", 
                                              value="Skya", 
                                              help="Author name that will appear on the blog post")
        
        generate_blog = st.button("✍️ Generate Full Blog Post", use_container_width=True)

        if generate_blog:
            if not product_name.strip() or not product_description.strip():
                st.warning("Provide both the product name and key details to guide the article.")
            else:
                try:
                    _ensure_replicate_client()
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    run_root = content_root / "blogs"
                    run_root.mkdir(parents=True, exist_ok=True)
                    timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
                    slug = _slugify(product_name)
                    session_dir = run_root / f"{timestamp}_{slug}"
                    session_dir.mkdir(parents=True, exist_ok=True)

                    hero_path = None
                    if hero_upload is not None:
                        hero_ext = Path(hero_upload.name).suffix or ".png"
                        hero_path = session_dir / f"hero{hero_ext}"
                        hero_path.write_bytes(hero_upload.getbuffer())

                    with st.spinner("Generating SEO blog, inline images, and exports..."):
                        html_path, pdf_path = generate_product_blog(
                            product_name,
                            product_description,
                            tone,
                            output_dir=str(session_dir),
                            image_path=str(hero_path) if hero_path else None
                        )

                    html_file = Path(html_path)
                    pdf_file = Path(pdf_path)
                    html_content = html_file.read_text(encoding="utf-8")
                    article_html = _extract_article_html(html_content)

                    st.markdown("---")
                    st.markdown(f"#### {product_name.title()} Blog Preview")
                    st.markdown(article_html, unsafe_allow_html=True)
                    
                    # Add enhanced analysis (magic-marketer pattern)
                    with st.expander("✨ Enhance with AI Analysis", expanded=False):
                        st.info("💡 Get AI-powered content analysis and recommendations to improve your blog post")
                        if st.button("🔍 Analyze & Enhance Blog", key="enhance_blog"):
                            with st.spinner("Analyzing blog content and generating improvements..."):
                                try:
                                    replicate_api, _ = _ensure_replicate_client()
                                    enhanced_generator = EnhancedCampaignGenerator(replicate_api)
                                    
                                    # Extract text from HTML for analysis
                                    text_content = re.sub('<[^<]+?>', '', article_html)
                                    
                                    analyzed_blog = enhanced_generator.enhance_content(
                                        text_content[:2000],  # Limit for analysis
                                        "Blog Post"
                                    )
                                    
                                    st.markdown("##### 📊 AI Analysis & Recommendations")
                                    st.markdown(analyzed_blog)
                                    
                                    # Save enhanced version
                                    enhanced_file = session_dir / f"{timestamp}_{slug}_analysis.txt"
                                    enhanced_file.write_text(analyzed_blog, encoding="utf-8")
                                    
                                    st.download_button(
                                        "💾 Download Analysis",
                                        data=analyzed_blog,
                                        file_name=enhanced_file.name,
                                        mime="text/plain",
                                        use_container_width=True,
                                        key="dl_enhanced_blog"
                                    )
                                    st.success("✅ Blog analyzed with improvement recommendations!")
                                except Exception as e:
                                    st.error(f"Analysis failed: {e}")

                    col_dl1, col_dl2 = st.columns(2)
                    with col_dl1:
                        st.download_button(
                            "📥 Download HTML",
                            data=html_content,
                            file_name=html_file.name,
                            mime="text/html",
                            use_container_width=True
                        )
                    with col_dl2:
                        if pdf_file.exists():
                            pdf_bytes = pdf_file.read_bytes()
                            pdf_label = "📄 Download PDF" if pdf_file.suffix == ".pdf" else "📄 Download Text Export"
                            mime_type = "application/pdf" if pdf_file.suffix == ".pdf" else "text/plain"
                            st.download_button(
                                pdf_label,
                                data=pdf_bytes,
                                file_name=pdf_file.name,
                                mime=mime_type,
                                use_container_width=True
                            )
                        else:
                            st.info("PDF export not available (missing system dependencies).")

                    st.toast("Blog post generated with inline imagery.")
                    st.success("Blog content saved to your content library.")
                    
                    # Initialize shopify_info
                    shopify_info = None
                    
                    # Shopify Auto-Publish
                    if publish_to_shopify:
                        st.markdown("---")
                        st.markdown("#### 🛍️ Publishing to Shopify...")
                        
                        shopify_shop_url = os.getenv('SHOPIFY_SHOP_URL')
                        shopify_api_key = os.getenv('SHOPIFY_API_KEY')
                        shopify_api_secret = os.getenv('SHOPIFY_API_SECRET')
                        shopify_access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
                        
                        if not shopify_shop_url or (not shopify_access_token and (not shopify_api_key or not shopify_api_secret)):
                            st.error("❌ Shopify credentials not found. Please configure in Settings.")
                            st.info("💡 Go to Settings page and add your Shopify API credentials")
                        else:
                            try:
                                with st.spinner("Publishing to Shopify..."):
                                    shopify_api = ShopifyAPI(
                                        shop_url=shopify_shop_url,
                                        api_key=shopify_api_key,
                                        api_secret=shopify_api_secret,
                                        access_token=shopify_access_token
                                    )
                                    
                                    # Test connection
                                    if not shopify_api.test_connection():
                                        st.error("❌ Failed to connect to Shopify. Check your credentials.")
                                        shopify_info = {'published': False, 'error': 'Connection failed'}
                                    else:
                                        st.info("✅ Connected to Shopify successfully")
                                        
                                        # Prepare tags
                                        tags = []
                                        if shopify_blog_tags:
                                            tags = [tag.strip() for tag in shopify_blog_tags.split(',')]
                                        
                                        st.info(f"📝 Publishing blog post: '{product_name}'...")
                                        
                                        # Publish the blog post
                                        article = shopify_api.create_blog_post(
                                            title=product_name,
                                            body_html=html_content,
                                            author=shopify_author,
                                            tags=tags if tags else None,
                                            published=True,
                                            handle=slug
                                        )
                                        
                                        if article:
                                            st.success(f"✅ Blog post published to Shopify!")
                                            article_url = article.get('url', f"https://{shopify_shop_url}/blogs/news/{slug}")
                                            st.info(f"🔗 View at: {article_url}")
                                            
                                            # Save Shopify info to session
                                            shopify_info = {
                                                'published': True,
                                                'article_id': article.get('id'),
                                                'url': article_url,
                                                'published_at': dt.now().strftime('%Y-%m-%d %H:%M:%S')
                                            }
                                        else:
                                            st.error("❌ Failed to publish to Shopify - API returned None")
                                            st.warning("Check the terminal/console for detailed error messages")
                                            shopify_info = {'published': False, 'error': 'Publication failed'}
                                        
                            except Exception as e:
                                st.error(f"❌ Shopify publishing failed: {e}")
                                shopify_info = {'published': False, 'error': str(e)}

                    run_info = {
                        "timestamp": timestamp,
                        "type": "blog",
                        "title": product_name,
                        "tone": tone,
                        "html_path": str(html_file),
                        "pdf_path": str(pdf_file) if pdf_file.exists() else None,
                        "preview_html": article_html,
                        "output_dir": str(session_dir),
                        "shopify": shopify_info if publish_to_shopify else None
                    }
                    st.session_state.content_generation_history.insert(0, run_info)
                    st.session_state.generated_assets.setdefault('blogs', []).append(str(html_file))

    elif content_type == "📱 Social Media Post":
        st.markdown("#### Social Caption Generator")
        
        # AI Content Advisor
        with st.expander("🤖 AI Content Advisor", expanded=False):
            advisor_col1, advisor_col2 = st.columns(2)
            with advisor_col1:
                if st.button("🔥 Get Viral Hook Ideas", use_container_width=True):
                    try:
                        replicate_token = _get_replicate_token()
                    except ValueError:
                        replicate_token = None
                    if replicate_token:
                        with st.spinner("Generating viral hooks..."):
                            try:
                                import replicate
                                client = replicate.Client(api_token=replicate_token)
                                hooks_prompt = """Generate 5 viral social media hook formulas that work in 2024:

1. A curiosity gap hook
2. A controversial/hot take hook  
3. A "secret" or insider knowledge hook
4. A relatable pain point hook
5. A transformation/before-after hook

Format: Just the hook templates with [BLANK] for customization. Under 15 words each."""
                                response = tracked_replicate_run(client, "meta/meta-llama-3-8b-instruct", {"prompt": hooks_prompt, "max_tokens": 250}, operation_name="Viral Hooks Generation")
                                st.session_state['viral_hooks'] = "".join(response) if isinstance(response, list) else response
                            except Exception as e:
                                st.error(f"Failed: {e}")
                    else:
                        st.warning("Add API key")
            
            with advisor_col2:
                if st.button("📈 Best Posting Times", use_container_width=True):
                    st.session_state['posting_times'] = """📊 **Best Posting Times by Platform:**

**Instagram:** 11am-1pm, 7-9pm (Tue-Fri)
**TikTok:** 7-9am, 12-3pm, 7-11pm (Tue-Thu)
**Twitter/X:** 8-10am, 12-1pm (Mon-Thu)
**Facebook:** 1-4pm (Wed-Fri)
**LinkedIn:** 7-8am, 12pm, 5-6pm (Tue-Thu)

💡 *Test your specific audience for best results*"""
            
            if st.session_state.get('viral_hooks'):
                st.markdown("##### 🔥 Viral Hook Templates")
                st.markdown(st.session_state['viral_hooks'])
            
            if st.session_state.get('posting_times'):
                st.markdown(st.session_state['posting_times'])

        platform = st.selectbox("Platform", ["Instagram", "TikTok", "Twitter/X", "Facebook", "LinkedIn"])
        tone = st.selectbox("Tone", ["Energetic", "Playful", "Educational", "Inspirational", "Bold"], index=0)
        
        # Content strategy selector
        content_strategy = st.selectbox(
            "Content Strategy",
            ["Standard Post", "Viral Hook Formula", "Story-Driven", "Value-First", "Controversy/Hot Take"],
            help="AI will structure your caption using this strategy"
        )
        
        campaign_angle = st.text_area(
            "Campaign Angle",
            height=120,
            placeholder="e.g., Launching our new limited-edition cyberpunk hoodies with reflective accents"
        )
        hashtags = st.text_input("Preferred hashtags (optional)", placeholder="#cyberpunk #streetwear")
        include_emoji = st.checkbox("Include emoji flair", value=True)
        
        # Caption variations
        num_variations = st.slider("Generate Variations", 1, 3, 1, help="Create multiple caption options to test")
        
        generate_caption = st.button("📱 Generate Social Caption", use_container_width=True)

        if generate_caption:
            if not campaign_angle.strip():
                st.warning("Describe the campaign angle so the AI can tailor the hook.")
            else:
                try:
                    replicate_api, _ = _ensure_replicate_client()
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    emoji_instruction = "Use relevant emoji for energy." if include_emoji else "Avoid using emoji."
                    hashtag_instruction = (
                        f"Include these hashtags exactly: {hashtags}."
                        if hashtags.strip()
                        else "Add two relevant hashtags at the end."
                    )
                    
                    # Strategy-specific instructions
                    strategy_instructions = {
                        "Standard Post": "Write a clear, engaging caption.",
                        "Viral Hook Formula": "Start with a scroll-stopping hook that creates curiosity. Use pattern interrupts.",
                        "Story-Driven": "Tell a mini-story in 3 acts: setup, conflict, resolution. Make it personal.",
                        "Value-First": "Lead with a valuable tip or insight. Position the product as the solution.",
                        "Controversy/Hot Take": "Start with a bold, slightly controversial statement that sparks engagement."
                    }
                    
                    all_captions = []
                    run_root = content_root / "social_posts"
                    run_root.mkdir(parents=True, exist_ok=True)
                    timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
                    
                    # Generate captions in parallel
                    with st.spinner(f"Generating {num_variations} captions in parallel..."):
                        import time
                        queue = get_global_job_queue()
                        caption_job_ids = []
                        
                        for var_num in range(num_variations):
                            prompt = (
                                f"You are a viral social media copywriter for a print-on-demand brand.\n"
                                f"Platform: {platform}\n"
                                f"Tone: {tone}\n"
                                f"Strategy: {strategy_instructions.get(content_strategy, '')}\n"
                                f"Campaign focus: {campaign_angle.strip()}\n"
                                f"{emoji_instruction}\n"
                                f"{hashtag_instruction}\n"
                                f"Variation: {var_num + 1} (make it unique from other variations)\n"
                                "Return a single caption under 280 characters with a clear call-to-action."
                            )
                            
                            def generate_single_caption(prompt=prompt, var_idx=var_num):
                                """Generate a single social media caption"""
                                try:
                                    caption = replicate_api.generate_text(prompt, max_tokens=220, temperature=0.85 + (var_idx * 0.05)).strip()
                                    return caption
                                except Exception as error:
                                    logger.error(f"Caption {var_idx + 1} generation failed: {error}")
                                    return None
                            
                            job_id = queue.submit_job(
                                job_type=JobType.TEXT_GENERATION,
                                tab_name="Content",
                                description=f"Social Caption {var_num+1}/{num_variations}",
                                function=generate_single_caption,
                                priority=5
                            )
                            caption_job_ids.append(job_id)
                        
                        # Store job IDs for persistence
                        st.session_state.content_caption_jobs = caption_job_ids
                        st.session_state.content_caption_platform = platform
                        st.session_state.content_caption_angle = campaign_angle
                        st.session_state.content_caption_strategy = content_strategy
                        st.session_state.content_caption_timestamp = timestamp
                        st.session_state.content_caption_run_root = str(run_root)
                        
                        st.success(f"✅ Submitted {len(caption_job_ids)} caption jobs!")
                        st.info("💡 Jobs run in background. You can switch tabs!")
                        st.rerun()
                
                # Show progress for running jobs (non-blocking)
                if st.session_state.get('content_caption_jobs'):
                    caption_job_ids = st.session_state.content_caption_jobs
                    
                    st.markdown("---")
                    st.markdown("### ⚙️ Caption Generation in Progress")
                    
                    prog = check_jobs_progress(caption_job_ids)
                    total = len(caption_job_ids)
                    done = prog['completed'] + prog['failed']
                    
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("🔄 Running", prog['running'])
                    with c2:
                        st.metric("✅ Done", prog['completed'])
                    with c3:
                        st.metric("❌ Failed", prog['failed'])
                    with c4:
                        st.metric("📊 Progress", f"{done}/{total}")
                    
                    st.progress(done / total if total > 0 else 0)
                    
                    if st.button("🔄 Refresh Progress", key="refresh_content_progress"):
                        st.rerun()
                    
                    if are_all_jobs_done(caption_job_ids):
                        st.success("🎉 All captions completed!")
                        
                        # Collect results
                        all_captions = collect_job_results(caption_job_ids, timeout=60)
                        all_captions = [c for c in all_captions if c is not None]
                        
                        # Restore metadata
                        platform = st.session_state.get('content_caption_platform', '')
                        campaign_angle = st.session_state.get('content_caption_angle', '')
                        content_strategy = st.session_state.get('content_caption_strategy', '')
                        timestamp = st.session_state.get('content_caption_timestamp', dt.now().strftime("%Y%m%d_%H%M%S"))
                        run_root = Path(st.session_state.get('content_caption_run_root', 'campaigns/content/social_posts'))
                        
                        # Clear job tracking
                        del st.session_state.content_caption_jobs
                        for key in ['content_caption_platform', 'content_caption_angle', 'content_caption_strategy', 
                                   'content_caption_timestamp', 'content_caption_run_root']:
                            st.session_state.pop(key, None)
                        
                        st.success(f"✅ Generated {len(all_captions)} captions!")
                    
                        if all_captions:
                            st.markdown("---")
                            st.markdown("#### 📱 Generated Captions")
                            
                            for idx, caption in enumerate(all_captions, 1):
                                st.markdown(f"**Option {idx}:** {content_strategy}")
                                st.info(caption)
                                
                                # Quick content score
                                score_elements = []
                                if any(emoji in caption for emoji in ['🔥', '💯', '✨', '🚀', '💪', '❤️', '😍']):
                                    score_elements.append("✅ Has engaging emoji")
                                if '?' in caption:
                                    score_elements.append("✅ Has question (engagement driver)")
                                if len(caption) < 150:
                                    score_elements.append("✅ Optimal length")
                                if '#' in caption:
                                    score_elements.append("✅ Has hashtags")
                                if any(cta in caption.lower() for cta in ['link', 'shop', 'get', 'grab', 'click', 'tap', 'check']):
                                    score_elements.append("✅ Has CTA")
                                
                                engagement_score = len(score_elements) * 20
                                st.caption(f"📊 Engagement Score: {engagement_score}/100 - {', '.join(score_elements[:3])}")
                        
                        # Save all captions
                        slug = _slugify(f"{platform}_{campaign_angle[:30]}")
                        all_captions_text = "\n\n---\n\n".join([f"OPTION {i+1}:\n{c}" for i, c in enumerate(all_captions)])
                        file_path = run_root / f"{timestamp}_{slug}.txt"
                        file_path.write_text(all_captions_text, encoding="utf-8")
                        
                        # Add enhanced analysis (magic-marketer pattern)
                        with st.expander("✨ Enhance with AI Analysis", expanded=False):
                            if st.button("🔍 Analyze & Improve Captions", key="enhance_social"):
                                with st.spinner("Analyzing and enhancing captions..."):
                                    enhanced_generator = EnhancedCampaignGenerator(replicate_api)
                                    analyzed_caption = enhanced_generator.enhance_content(
                                        all_captions[0], 
                                        f"{platform} Social Media Post"
                                    )
                                    
                                    st.markdown("##### 📊 AI Analysis & Enhanced Version")
                                    st.markdown(analyzed_caption)
                                    
                                    # Save enhanced version
                                    enhanced_file = run_root / f"{timestamp}_{slug}_enhanced.txt"
                                    enhanced_file.write_text(analyzed_caption, encoding="utf-8")
                                    
                                    st.download_button(
                                        "💾 Download Enhanced Caption",
                                        data=analyzed_caption,
                                        file_name=enhanced_file.name,
                                        mime="text/plain",
                                        use_container_width=True,
                                        key="dl_enhanced_social"
                                    )
                                    st.success("✅ Caption analyzed and enhanced!")
                        
                        st.download_button(
                            "💾 Download All Captions",
                            data=all_captions_text,
                            file_name=file_path.name,
                            mime="text/plain",
                            use_container_width=True
                        )
                        st.toast(f"Saved {len(all_captions)} social caption(s) for {platform}.")
                        st.success("Captions stored in your content library.")

                        run_info = {
                            "timestamp": timestamp,
                            "type": "social",
                            "title": f"{platform} post ({len(all_captions)} variations)",
                            "tone": tone,
                            "content": all_captions[0] if all_captions else "",
                            "all_variations": all_captions,
                            "output_path": str(file_path),
                            "metadata": {"platform": platform, "strategy": content_strategy}
                        }
                        st.session_state.content_generation_history.insert(0, run_info)
                        st.session_state.generated_assets.setdefault('social_posts', []).append(str(file_path))

    elif content_type == "📧 Email Campaign":
        st.markdown("#### 📧 Professional Email Campaign Generator")
        st.markdown("*Create beautiful HTML emails and optionally send them to your mailing list*")

        email_col1, email_col2 = st.columns(2)
        
        with email_col1:
            product_name = st.text_input("Product or Offer Name", placeholder="Aurora Glow Galaxy Lamp")
            audience = st.text_input("Target Audience", placeholder="Night owls, gamers, and mood lighting lovers")
            tone = st.selectbox("Email Tone", ["Friendly", "Premium", "Excited", "Educational", "Urgent"], index=0)
        
        with email_col2:
            offer = st.text_area("Key Offer or Story", height=100, placeholder="Early access launch with 20% off + free shipping for 48 hours")
            cta_link = st.text_input("CTA Link (product URL)", placeholder="https://your-store.com/product", value=os.getenv('SHOPIFY_SHOP_URL', ''))
        
        # Upload product image for email
        email_image = st.file_uploader("Product Image (for email hero)", type=["png", "jpg", "jpeg"], key="email_hero_img")
        
        st.markdown("---")
        
        # Auto-send settings
        st.markdown("#### 📤 Auto-Send Settings")
        auto_send_from_content = st.checkbox("📧 Auto-send to mailing list after generation", value=False,
                                              help="Automatically send this email to your subscribers")
        
        email_recipients_content = ""
        if auto_send_from_content:
            # Load mailing list
            all_emails = ["scatterboxxrocks@gmail.com"]
            try:
                mailing_list_path = Path(__file__).parent / "mailing_list.json"
                if mailing_list_path.exists():
                    with open(mailing_list_path, 'r') as f:
                        mailing_data = json.load(f)
                    local_emails = [s['email'] for s in mailing_data.get('subscribers', []) 
                                   if s.get('accepts_marketing', True)]
                    all_emails.extend(local_emails)
            except (FileNotFoundError, json.JSONDecodeError, KeyError):
                pass
            
            all_emails = list(dict.fromkeys(all_emails))
            
            send_col1, send_col2 = st.columns([3, 1])
            with send_col1:
                email_recipients_content = st.text_area(
                    "📋 Recipients (one per line)",
                    value="\n".join(all_emails[:50]),
                    height=80,
                    key="content_email_recipients"
                )
            with send_col2:
                st.markdown(f"**{len(all_emails)} subscribers**")
                st.caption("Manage in Customers page")
        
        generate_email = st.button("📧 Generate Professional Email", use_container_width=True, type="primary")

        if generate_email:
            if not product_name.strip() or not offer.strip():
                st.warning("Fill in the product name and offer to craft the campaign.")
            else:
                try:
                    replicate_api, _ = _ensure_replicate_client()
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    with st.spinner("✨ Generating professional email campaign..."):
                        # Generate email content using AI
                        prompt = (
                            f"Write a {tone.lower()} marketing email for '{product_name}'.\n"
                            f"Target audience: {audience}.\n"
                            f"Key offer: {offer}.\n"
                            "Return a JSON object with these fields:\n"
                            "- subject: catchy email subject line\n"
                            "- preview_text: short preview text (50 chars max)\n"
                            "- headline: main headline for email\n"
                            "- body: 2-3 paragraphs of compelling copy\n"
                            "- cta_text: call-to-action button text\n"
                            "Return ONLY valid JSON, no markdown."
                        )
                        
                        try:
                            email_response = replicate_api.generate_text(prompt, max_tokens=600, temperature=0.75)
                            
                            # Parse JSON response
                            # Extract JSON from response
                            json_match = re.search(r'\{[^{}]*\}', email_response, re.DOTALL)
                            if json_match:
                                email_data = json.loads(json_match.group())
                            else:
                                # Fallback to manual extraction
                                email_data = {
                                    'subject': f"🎉 Introducing {product_name}!",
                                    'preview_text': offer[:50] if offer else "Don't miss this!",
                                    'headline': f"Meet Your New Favorite: {product_name}",
                                    'body': email_response,
                                    'cta_text': "Shop Now"
                                }
                            
                            # Create gorgeous HTML email
                            email_service = EmailMarketingService()
                            
                            # Handle image upload
                            product_image_url = None
                            if email_image:
                                # Save uploaded image temporarily
                                run_root = content_root / "email_campaigns"
                                run_root.mkdir(parents=True, exist_ok=True)
                                img_path = run_root / f"email_hero_{dt.now().strftime('%Y%m%d%H%M%S')}.png"
                                with open(img_path, 'wb') as f:
                                    f.write(email_image.getbuffer())
                                product_image_url = str(img_path)
                            
                            # Generate HTML email
                            html_content = email_service.create_html_email(
                                subject=email_data.get('subject', f"Introducing {product_name}!"),
                                preview_text=email_data.get('preview_text', offer[:50]),
                                headline=email_data.get('headline', f"Discover {product_name}"),
                                body=email_data.get('body', offer),
                                cta_text=email_data.get('cta_text', 'Shop Now'),
                                cta_link=cta_link or "https://your-store.com",
                                product_image_url=product_image_url,
                                brand_color="#6366f1",
                                product_name=product_name
                            )
                            
                            # Save files
                            run_root = content_root / "email_campaigns"
                            run_root.mkdir(parents=True, exist_ok=True)
                            timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
                            slug = _slugify(product_name)
                            
                            html_file = run_root / f"{timestamp}_{slug}.html"
                            html_file.write_text(html_content, encoding="utf-8")
                            
                            # Also save markdown version
                            md_file = run_root / f"{timestamp}_{slug}.md"
                            md_content = f"""# {email_data.get('subject', product_name)}

**Preview:** {email_data.get('preview_text', '')}

## {email_data.get('headline', '')}

{email_data.get('body', '')}

[{email_data.get('cta_text', 'Shop Now')}]({cta_link})
"""
                            md_file.write_text(md_content, encoding="utf-8")
                            
                            st.success("✅ Professional HTML email generated!")
                            
                            # Preview tabs
                            preview_tab1, preview_tab2 = st.tabs(["📧 HTML Preview", "📝 Text Version"])
                            
                            with preview_tab1:
                                st.markdown("#### Email Preview")
                                st.components.v1.html(html_content, height=800, scrolling=True)
                            
                            with preview_tab2:
                                st.markdown("#### Text Version")
                                st.markdown(md_content)
                            
                            # Download buttons
                            dl_col1, dl_col2 = st.columns(2)
                            with dl_col1:
                                st.download_button(
                                    "📥 Download HTML",
                                    data=html_content,
                                    file_name=html_file.name,
                                    mime="text/html",
                                    use_container_width=True
                                )
                            with dl_col2:
                                st.download_button(
                                    "📥 Download Markdown",
                                    data=md_content,
                                    file_name=md_file.name,
                                    mime="text/markdown",
                                    use_container_width=True
                                )
                            
                            # Auto-send if enabled
                            if auto_send_from_content and email_recipients_content:
                                st.markdown("---")
                                st.markdown("#### 📤 Sending Email Campaign...")
                                
                                recipient_list = [e.strip() for e in email_recipients_content.split('\n') if e.strip() and '@' in e]
                                
                                if recipient_list:
                                    with st.spinner(f"Sending to {len(recipient_list)} recipients..."):
                                        send_results = email_service.send_batch_emails(
                                            recipients=recipient_list,
                                            subject=email_data.get('subject', f"Introducing {product_name}!"),
                                            html_content=html_content,
                                            delay_seconds=1.0
                                        )
                                        
                                        if send_results['sent'] > 0:
                                            st.success(f"✅ Email sent to {send_results['sent']} recipients!")
                                            st.balloons()
                                        if send_results['failed'] > 0:
                                            st.warning(f"⚠️ {send_results['failed']} emails failed to send")
                                else:
                                    st.warning("No valid email addresses found")
                            
                            # Manual send button
                            elif not auto_send_from_content:
                                st.markdown("---")
                                if st.button("📤 Send This Email Now", key="manual_send_email"):
                                    st.session_state['pending_email'] = {
                                        'subject': email_data.get('subject'),
                                        'html': html_content
                                    }
                                    st.info("💡 Enable 'Auto-send to mailing list' above and regenerate, or go to Customers page to manage recipients")
                            
                            # Save to history
                            run_info = {
                                "timestamp": timestamp,
                                "type": "email",
                                "title": product_name,
                                "tone": tone,
                                "subject": email_data.get('subject'),
                                "html_path": str(html_file),
                                "md_path": str(md_file),
                                "output_path": str(html_file),
                                "metadata": {"audience": audience, "offer": offer}
                            }
                            st.session_state.content_generation_history.insert(0, run_info)
                            st.session_state.generated_assets.setdefault('email_flows', []).append(str(html_file))
                            
                        except Exception as error:
                            st.error(f"Email generation failed: {error}")
                            import traceback
                            st.code(traceback.format_exc())

    else:  # 🎯 Ad Copy
        st.markdown("#### High-Converting Ad Copy")

        platform = st.selectbox("Ad Platform", ["Meta Ads", "Google Ads", "TikTok Ads", "YouTube Pre-roll", "Pinterest"], index=0)
        product = st.text_input("Product Focus", placeholder="NeoWave LED Desk Lamp")
        audience = st.text_input("Audience", placeholder="Remote workers who love ambient lighting")
        differentiator = st.text_area(
            "Key Differentiator",
            height=120,
            placeholder="dual-tone lighting, wireless charging base, smart home integration"
        )
        tone = st.selectbox("Tone", ["Bold", "Trustworthy", "Playful", "Luxury", "Conversational"], index=0)
        generate_ads = st.button("🎯 Generate Ad Variations", use_container_width=True)

        if generate_ads:
            if not product.strip() or not audience.strip() or not differentiator.strip():
                st.warning("Provide product, audience, and differentiators to craft high-intent ads.")
            else:
                try:
                    replicate_api, _ = _ensure_replicate_client()
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    prompt = (
                        f"Create three {tone.lower()} ad copy variations for {platform}.\n"
                        f"Product: {product}.\n"
                        f"Audience: {audience}.\n"
                        f"Differentiators: {differentiator}.\n"
                        "Each variation should include a headline (<= 40 chars), a primary text (<= 90 chars), and a CTA."
                        "Return the result as Markdown with numbered variations."
                    )
                    try:
                        ad_copy = replicate_api.generate_text(prompt, max_tokens=400, temperature=0.8)
                    except Exception as error:
                        st.error(f"Ad copy generation failed: {error}")
                    else:
                        run_root = content_root / "ad_copy"
                        run_root.mkdir(parents=True, exist_ok=True)
                        timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
                        slug = _slugify(product)
                        file_path = run_root / f"{timestamp}_{slug}.md"
                        file_path.write_text(ad_copy, encoding="utf-8")

                        st.markdown("---")
                        st.markdown("#### Ad Variations")
                        st.markdown(ad_copy)
                        st.download_button(
                            " Download Ads",
                            data=ad_copy,
                            file_name=file_path.name,
                            mime="text/markdown",
                            use_container_width=True
                        )
                        st.toast("Ad variations generated.")
                        st.success("Ads saved to your content library.")

                        run_info = {
                            "timestamp": timestamp,
                            "type": "ad",
                            "title": product,
                            "tone": tone,
                            "content": ad_copy,
                            "output_path": str(file_path),
                            "metadata": {"platform": platform}
                        }
                        st.session_state.content_generation_history.insert(0, run_info)
                        st.session_state.generated_assets.setdefault('ad_copy', []).append(str(file_path))

    if st.session_state.content_generation_history:
        st.markdown("---")
        st.markdown("#### Recent Content Library")
        for entry in st.session_state.content_generation_history[:5]:
            label = entry.get('title', entry['type']).title()
            with st.expander(f"{entry['type'].title()} • {entry['timestamp']} • {label}", expanded=False):
                if entry['type'] == 'blog':
                    st.markdown(entry.get('preview_html', ''), unsafe_allow_html=True)
                    st.markdown(f"HTML: `{entry['html_path']}`")
                    if entry.get('pdf_path'):
                        st.markdown(f"PDF/Text Export: `{entry['pdf_path']}`")
                else:
                    st.markdown(entry.get('content', ''))
                    st.markdown(f"Saved to `{entry.get('output_path', 'unknown')}`")
