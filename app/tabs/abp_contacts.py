from abp_imports_common import (
    st, os, logging, asyncio, json, setup_logger
)

logger = setup_logger(__name__)

import pandas as pd
from platform_helpers import _get_replicate_token
from app.services.contact_finder_service import ContactFinderService, Contact, OutreachPlan
from api_service import ReplicateAPI
from platform_integrations import tracked_replicate_run

def render_contact_finder_tab():
    """
    Renders the Contact Finder tab (Tab 12).
    """
    st.markdown('<div class="main-header">🔍 Contact Finder</div>', unsafe_allow_html=True)
    st.markdown("### AI-Powered Outreach Opportunity Discovery")
    st.caption("Find real contacts and strategic outreach opportunities for your products")
    
    # AI Outreach Assistant at the top
    with st.expander("🤖 AI Outreach Assistant", expanded=False):
        st.markdown("**Get AI help crafting perfect outreach messages**")
        
        outreach_tabs = st.tabs(["📧 Email Generator", "💬 DM Generator", "🎯 Lead Scorer", "📊 Market Analysis"])
        
        with outreach_tabs[0]:
            st.markdown("#### AI Email Generator")
            email_col1, email_col2 = st.columns(2)
            
            with email_col1:
                email_recipient_type = st.selectbox("Recipient Type", 
                    ["Gallery Owner", "Store Manager", "Influencer", "Podcast Host", "Brand Manager", "Other"],
                    key="ai_email_recipient")
                email_your_product = st.text_input("Your Product/Service", 
                    placeholder="e.g., Neon art prints", key="ai_email_product")
                email_goal = st.selectbox("Email Goal",
                    ["Introduction/Partnership", "Product Feature Request", "Collaboration Proposal", 
                     "Event/Pop-up Opportunity", "Wholesale Inquiry", "Press/Media Coverage"],
                    key="ai_email_goal")
            
            with email_col2:
                email_tone = st.selectbox("Email Tone",
                    ["Professional", "Friendly & Casual", "Bold & Direct", "Warm & Personal"],
                    key="ai_email_tone")
                email_unique_angle = st.text_input("Unique Angle/Hook",
                    placeholder="e.g., Featured in NYT, 10k Instagram followers", key="ai_email_angle")
            
            if st.button("✍️ Generate Outreach Email", use_container_width=True, key="gen_outreach_email"):
                if email_your_product:
                    try:
                        replicate_token = _get_replicate_token()
                    except ValueError:
                        replicate_token = None
                    if replicate_token:
                        with st.spinner("✍️ Crafting personalized email..."):
                            try:
                                import replicate
                                client = replicate.Client(api_token=replicate_token)
                                email_prompt = f"""Write a professional cold outreach email:

TO: {email_recipient_type}
FROM: Creator/seller of {email_your_product}
GOAL: {email_goal}
TONE: {email_tone}
UNIQUE ANGLE: {email_unique_angle or 'High-quality, unique products'}

Requirements:
1. Compelling subject line (under 50 chars)
2. Personal opening (not generic)
3. Clear value proposition for THEM
4. Specific ask/CTA
5. Keep under 150 words
6. Include a PS line

Format:
SUBJECT: [subject line]

[email body]

PS: [ps line]"""
                                response = tracked_replicate_run(client, "meta/meta-llama-3-8b-instruct", {"prompt": email_prompt, "max_tokens": 400}, operation_name="Outreach Email Generation")
                                st.session_state['ai_outreach_email'] = "".join(response) if isinstance(response, list) else response
                            except Exception as e:
                                st.error(f"Failed: {e}")
                    else:
                        st.warning("Add API key in Settings")
                else:
                    st.warning("Enter your product first")
            
            if st.session_state.get('ai_outreach_email'):
                st.markdown("#### 📧 Generated Email")
                st.text_area("Copy this email:", st.session_state['ai_outreach_email'], height=300, key="email_output")
                
                # Generate variations
                if st.button("🔄 Generate 2 More Variations", key="email_variations"):
                    st.info("Click the generate button again to get a new variation!")
        
        with outreach_tabs[1]:
            st.markdown("#### AI DM/Message Generator")
            dm_col1, dm_col2 = st.columns(2)
            
            with dm_col1:
                dm_platform = st.selectbox("Platform",
                    ["Instagram DM", "LinkedIn Message", "Twitter DM", "TikTok Comment", "Facebook Message"],
                    key="ai_dm_platform")
                dm_target = st.text_input("Who are you messaging?",
                    placeholder="e.g., Fashion influencer with 50k followers", key="ai_dm_target")
            
            with dm_col2:
                dm_your_offer = st.text_input("What's your offer/ask?",
                    placeholder="e.g., Free product for review", key="ai_dm_offer")
                dm_style = st.selectbox("Message Style",
                    ["Casual & Friendly", "Professional", "Enthusiastic Fan", "Straight to Business"],
                    key="ai_dm_style")
            
            if st.button("💬 Generate DM", use_container_width=True, key="gen_dm"):
                if dm_target and dm_your_offer:
                    try:
                        replicate_token = _get_replicate_token()
                    except ValueError:
                        replicate_token = None
                    if replicate_token:
                        with st.spinner("💬 Crafting your DM..."):
                            try:
                                import replicate
                                client = replicate.Client(api_token=replicate_token)
                                dm_prompt = f"""Write a {dm_platform} message:

TO: {dm_target}
OFFER: {dm_your_offer}
STYLE: {dm_style}

Rules:
- Keep under 100 words for DMs
- Sound natural, not salesy
- Include a compliment about their work
- Clear but soft CTA
- Platform-appropriate (casual for IG/TikTok, professional for LinkedIn)

Just the message, no explanation."""
                                response = tracked_replicate_run(client, "meta/meta-llama-3-8b-instruct", {"prompt": dm_prompt, "max_tokens": 200}, operation_name="DM Message Generation")
                                st.session_state['ai_dm'] = "".join(response) if isinstance(response, list) else response
                            except Exception as e:
                                st.error(f"Failed: {e}")
                    else:
                        st.warning("Add API key")
                else:
                    st.warning("Fill in target and offer")
            
            if st.session_state.get('ai_dm'):
                st.markdown("#### 💬 Generated Message")
                st.info(st.session_state['ai_dm'])
        
        with outreach_tabs[2]:
            st.markdown("#### AI Lead Scorer")
            st.caption("Paste contact info to get an AI assessment of lead quality")
            
            lead_info = st.text_area("Paste lead information:",
                placeholder="Name: John Smith\nCompany: Cool Gallery\nRole: Owner\nFollowers: 15k\nLocation: NYC...",
                height=120, key="ai_lead_info")
            lead_product = st.text_input("Your product:", placeholder="Art prints", key="ai_lead_product")
            
            if st.button("📊 Score This Lead", use_container_width=True, key="score_lead"):
                if lead_info and lead_product:
                    try:
                        replicate_token = _get_replicate_token()
                    except ValueError:
                        replicate_token = None
                    if replicate_token:
                        with st.spinner("📊 Analyzing lead..."):
                            try:
                                import replicate
                                client = replicate.Client(api_token=replicate_token)
                                score_prompt = f"""Score this lead for selling {lead_product}:

{lead_info}

Provide:
1. LEAD SCORE: X/100
2. FIT RATING: (Poor/Fair/Good/Excellent)
3. STRENGTHS: (2-3 bullet points)
4. CONCERNS: (1-2 bullet points)
5. RECOMMENDED APPROACH: (1 sentence)
6. PRIORITY: (Low/Medium/High/Hot)

Be realistic and specific."""
                                response = tracked_replicate_run(client, "meta/meta-llama-3-8b-instruct", {"prompt": score_prompt, "max_tokens": 300}, operation_name="Lead Scoring Analysis")
                                st.session_state['ai_lead_score'] = "".join(response) if isinstance(response, list) else response
                            except Exception as e:
                                st.error(f"Failed: {e}")
                    else:
                        st.warning("Add API key")
                else:
                    st.warning("Enter lead info and your product")
            
            if st.session_state.get('ai_lead_score'):
                st.markdown("#### 📊 Lead Analysis")
                st.markdown(st.session_state['ai_lead_score'])
        
        with outreach_tabs[3]:
            st.markdown("#### AI Market Analysis")
            st.caption("Get AI insights on your target market and outreach strategy")
            
            market_product = st.text_input("Your product/service:", key="ai_market_product")
            market_niche = st.text_input("Target niche:", placeholder="e.g., Gaming streamers, Yoga studios", key="ai_market_niche")
            
            if st.button("🎯 Analyze Market", use_container_width=True, key="analyze_market"):
                if market_product and market_niche:
                    try:
                        replicate_token = _get_replicate_token()
                    except ValueError:
                        replicate_token = None
                    if replicate_token:
                        with st.spinner("🎯 Analyzing market..."):
                            try:
                                import replicate
                                client = replicate.Client(api_token=replicate_token)
                                market_prompt = f"""Analyze outreach opportunities for selling {market_product} to {market_niche}:

Provide:
## TOP 5 CONTACT TYPES TO TARGET
(with why each is valuable)

## BEST OUTREACH CHANNELS
(ranked by effectiveness)

## TIMING RECOMMENDATIONS
(best times/seasons to reach out)

## COMMON OBJECTIONS & RESPONSES
(3 objections with counter-responses)

## QUICK WINS
(3 easy opportunities to start with)

Be specific and actionable."""
                                response = tracked_replicate_run(client, "meta/meta-llama-3-70b-instruct", {"prompt": market_prompt, "max_tokens": 800}, operation_name="Market Analysis")
                                st.session_state['ai_market_analysis'] = "".join(response) if isinstance(response, list) else response
                            except Exception as e:
                                st.error(f"Failed: {e}")
                    else:
                        st.warning("Add API key")
                else:
                    st.warning("Enter product and niche")
            
            if st.session_state.get('ai_market_analysis'):
                st.markdown("#### 🎯 Market Analysis")
                st.markdown(st.session_state['ai_market_analysis'])
    
    st.markdown("---")
    
    # Initialize contact finder
    if 'contact_finder' not in st.session_state:
        replicate_token = _get_replicate_token()
        if replicate_token:
            replicate_api = ReplicateAPI(api_token=replicate_token)
            # FREE mode - no paid APIs like Hunter.io or Apollo.io
            st.session_state.contact_finder = ContactFinderService(
                replicate_api=replicate_api
            )
        else:
            st.session_state.contact_finder = None
    
    if st.session_state.contact_finder is None:
        st.warning("⚠️ Contact Finder requires Replicate API key. Please configure in Settings.")
    else:
        # Search Configuration
        st.markdown("### 🎯 Search Parameters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            product_name = st.text_input("Product Name", placeholder="Aura Sky Neon Posters", key="cf_product_name")
            product_type = st.selectbox("Product Type", [
                "poster", "audio", "merch", "digital_download", "course", "ebook", "other"
            ], key="cf_product_type")
            
            location = st.text_input("Geographic Focus", value="United States", key="cf_location")
            remote_search = st.checkbox("Search Globally (Remote)", value=True, key="cf_remote")
        
        with col2:
            target_market = st.text_area(
                "Target Market Description (Optional - AI will auto-detect)",
                placeholder="Leave blank for AI to automatically determine target market from product...",
                height=90,
                key="cf_target_market",
                help="AI will analyze your product and determine the target market automatically"
            )
            
            result_count = st.slider("Number of Contacts", 5, 25, 10, key="cf_result_count")
            
            # Show AI-detected market if available
            if 'cf_ai_detected_market' in st.session_state:
                st.info(f"🤖 AI Detected Market: {st.session_state.cf_ai_detected_market}")
        
        # Contact Type Filters
        st.markdown("#### 📋 Contact Type Preferences (Optional)")
        
        contact_type_cols = st.columns(4)
        selected_types = []
        
        with contact_type_cols[0]:
            if st.checkbox("Gallery Owners"): selected_types.append("Gallery Owner")
            if st.checkbox("Store Managers"): selected_types.append("Store Manager")
            if st.checkbox("Event Organizers"): selected_types.append("Event Organizer")
        
        with contact_type_cols[1]:
            if st.checkbox("Influencers"): selected_types.append("Social Media Influencer")
            if st.checkbox("Content Creators"): selected_types.append("Content Creator")
            if st.checkbox("Playlist Curators"): selected_types.append("Playlist Curator")
        
        with contact_type_cols[2]:
            if st.checkbox("Marketing Managers"): selected_types.append("Marketing Manager")
            if st.checkbox("Brand Managers"): selected_types.append("Brand Manager")
            if st.checkbox("Talent Buyers"): selected_types.append("Talent Buyer")
        
        with contact_type_cols[3]:
            if st.checkbox("Podcast Hosts"): selected_types.append("Podcast Host")
            if st.checkbox("Music Supervisors"): selected_types.append("Music Supervisor")
            if st.checkbox("Design Studios"): selected_types.append("Design Studio")
        
        # Planning Options
        st.markdown("#### 📅 Outreach Planning")
        plan_col1, plan_col2 = st.columns(2)
        
        with plan_col1:
            plan_day = st.checkbox("Generate Daily Outreach Plan", value=True)
        with plan_col2:
            plan_week = st.checkbox("Generate Weekly Outreach Plan", value=False)
        
        # Search Button
        if st.button("🔍 Find Contacts", type="primary", use_container_width=True):
            if not product_name:
                st.error("Please provide Product Name")
            else:
                with st.spinner(f"🔍 Analyzing product and finding contacts..."):
                    
                    # Auto-detect target market if not provided
                    if not target_market or target_market.strip() == "":
                        with st.spinner("🤖 AI detecting target market..."):
                            # Use AI to determine target market from product name and type
                            replicate_token = _get_replicate_token()
                            if replicate_token:
                                temp_replicate = ReplicateAPI(api_token=replicate_token)
                                
                                market_prompt = f"""Analyze this product and determine the target market:

Product: {product_name}
Type: {product_type}

Provide a concise 2-3 sentence description of the ideal target market, including:
- Demographics (age, interests, lifestyle)
- Psychographics (values, aesthetics, preferences)
- Buying behavior

Be specific and actionable."""
                                
                                try:
                                    detected_market = temp_replicate.generate_text(
                                        prompt=market_prompt,
                                        model="meta/meta-llama-3-70b-instruct",
                                        max_tokens=200
                                    )
                                    target_market = detected_market.strip()
                                    st.session_state.cf_ai_detected_market = target_market
                                    st.success(f"✅ AI Detected Market: {target_market[:100]}...")
                                except Exception as e:
                                    logger.error(f"Market detection error: {e}")
                                    # Use default based on product type
                                    target_market = f"Consumers interested in {product_type} products"
                            else:
                                target_market = f"Consumers interested in {product_type} products"
                    
                    # Run async contact search
                    contacts = asyncio.run(st.session_state.contact_finder.find_contacts(
                        product_name=product_name,
                        product_type=product_type,
                        target_market=target_market,
                        location=location,
                        contact_types=selected_types if selected_types else None,
                        result_count=result_count,
                        remote=remote_search
                    ))
                    
                    st.session_state.cf_contacts = contacts
                    
                    # Generate plans if requested (parallel execution)
                    if (plan_day or plan_week) and contacts:
                        from global_job_queue import get_global_job_queue, JobType
                        
                        queue = get_global_job_queue()
                        plan_jobs = []
                        
                        if plan_day:
                            plan_jobs.append(('day', queue.submit_job(
                                job_type=JobType.TEXT_GENERATION,
                                tab_name="Contacts",
                                description="Generate Day Plan",
                                function=lambda: asyncio.run(st.session_state.contact_finder.generate_day_plan(contacts)),
                                priority=7
                            )))
                        
                        if plan_week:
                            plan_jobs.append(('week', queue.submit_job(
                                job_type=JobType.TEXT_GENERATION,
                                tab_name="Contacts",
                                description="Generate Week Plan",
                                function=lambda: asyncio.run(st.session_state.contact_finder.generate_week_plan(contacts)),
                                priority=7
                            )))
                        
                        # Store job IDs
                        st.session_state.contact_plan_jobs = plan_jobs
                        st.info(f"⚡ Generating {len(plan_jobs)} plans in parallel...")
                        import time
                        time.sleep(0.5)
                        st.rerun()
        
        # Check for plan generation jobs
        if 'contact_plan_jobs' in st.session_state and st.session_state.contact_plan_jobs:
            from tab_job_helpers import check_jobs_progress, are_all_jobs_done, collect_job_results
            
            plan_jobs = st.session_state.contact_plan_jobs
            job_ids = [job_id for _, job_id in plan_jobs]
            progress = check_jobs_progress(job_ids)
            
            if are_all_jobs_done(job_ids):
                results = collect_job_results(job_ids)
                for (plan_type, _), result in zip(plan_jobs, results):
                    if plan_type == 'day':
                        st.session_state.cf_day_plan = result
                    elif plan_type == 'week':
                        st.session_state.cf_week_plan = result
                st.session_state.contact_plan_jobs = []
                st.success("✅ Plans generated!")
                st.rerun()
            else:
                st.info(f"⚡ Generating plans: {progress['completed']}/{len(job_ids)} complete")
                if st.button("🔄 Refresh Plans", key="refresh_contact_plans"):
                    st.rerun()
        
        # Display Results
        if 'cf_contacts' in st.session_state and st.session_state.cf_contacts:
            st.markdown("---")
            st.markdown(f"### 📇 Found {len(st.session_state.cf_contacts)} Contacts")
            
            # Summary metrics
            metric_cols = st.columns(4)
            verified_count = sum(1 for c in st.session_state.cf_contacts if c.verified)
            avg_confidence = sum(c.confidence for c in st.session_state.cf_contacts) / len(st.session_state.cf_contacts)
            email_count = sum(1 for c in st.session_state.cf_contacts if c.channel_type == 'email')
            linkedin_count = sum(1 for c in st.session_state.cf_contacts if c.channel_type == 'linkedin')
            
            metric_cols[0].metric("Verified", verified_count)
            metric_cols[1].metric("Avg Confidence", f"{avg_confidence:.0%}")
            metric_cols[2].metric("Email Contacts", email_count)
            metric_cols[3].metric("LinkedIn Profiles", linkedin_count)
            
            # Contact Cards
            for i, contact in enumerate(st.session_state.cf_contacts):
                with st.expander(f"{'✅' if contact.verified else '📋'} {contact.name} — {contact.role} at {contact.company}", expanded=i<3):
                    card_cols = st.columns([2, 1])
                    
                    with card_cols[0]:
                        st.markdown(f"**Role:** {contact.role}")
                        st.markdown(f"**Company:** {contact.company}")
                        st.markdown(f"**Contact Type:** {contact.contact_type}")
                        st.markdown(f"**Channel:** `{contact.channel}` ({contact.channel_type})")
                        
                        st.markdown(f"**Why This Contact:**")
                        st.info(contact.rationale)
                        
                        st.markdown(f"**Outreach Approach:**")
                        st.success(contact.outreach_approach)
                    
                    with card_cols[1]:
                        st.markdown(f"**Confidence:** {contact.confidence:.0%}")
                        if contact.verified:
                            st.success("✅ Verified")
                        else:
                            st.warning("⚠️ Unverified")
                        
                        st.markdown(f"**Source:** {contact.source}")
                        
                        # Action buttons
                        if st.button(f"📧 Draft Email", key=f"draft_email_{i}"):
                            st.session_state.cf_draft_contact_index = i
                            st.rerun()
                        
                        if st.button(f"📋 Copy Contact", key=f"copy_contact_{i}"):
                            st.session_state.cf_copied = contact.channel
                            st.success("Copied!")
            
            # Export Options
            st.markdown("---")
            export_cols = st.columns(3)
            
            with export_cols[0]:
                # Export to CSV
                df = pd.DataFrame([c.to_dict() for c in st.session_state.cf_contacts])
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"contacts_{product_name.replace(' ', '_')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with export_cols[1]:
                # Export to JSON
                json_data = json.dumps([c.to_dict() for c in st.session_state.cf_contacts], indent=2)
                st.download_button(
                    label="📥 Download JSON",
                    data=json_data,
                    file_name=f"contacts_{product_name.replace(' ', '_')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with export_cols[2]:
                # Add to Campaign
                if st.button("➕ Add to Active Campaign", use_container_width=True):
                    if 'current_campaign' in st.session_state and st.session_state.current_campaign:
                        st.session_state.current_campaign['contacts'] = [c.to_dict() for c in st.session_state.cf_contacts]
                        st.success("✅ Contacts added to campaign!")
                    else:
                        st.warning("No active campaign. Create a campaign first.")
            
            # Display Plans
            if 'cf_day_plan' in st.session_state and st.session_state.cf_day_plan:
                st.markdown("---")
                st.markdown("### 📅 Daily Outreach Plan")
                
                for plan in st.session_state.cf_day_plan:
                    with st.container():
                        st.markdown(f"**{plan.best_time}** ({plan.duration})")
                        st.markdown(f"📍 {plan.contact_name}")
                        st.markdown(f"**Strategy:** {plan.strategy}")
                        st.markdown("")
            
            if 'cf_week_plan' in st.session_state and st.session_state.cf_week_plan:
                st.markdown("---")
                st.markdown("### 🗓️ Weekly Outreach Plan")
                
                for plan in st.session_state.cf_week_plan:
                    with st.container():
                        st.markdown(f"**{plan.day}** - {plan.best_time}")
                        st.markdown(f"📍 {plan.contact_name}")
                        st.markdown(f"**Strategy:** {plan.strategy}")
                        st.markdown("")
