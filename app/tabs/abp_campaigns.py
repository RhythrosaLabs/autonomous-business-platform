from app.tabs.abp_imports_common import (
    st, os, Path, datetime, requests, json, setup_logger
)
import time
from app.services.secure_config import get_api_key

# Maintain backward compatibility alias
dt = datetime
logger = setup_logger(__name__)

from app.services.platform_integrations import tracked_replicate_run
from app.services.platform_helpers import _get_replicate_token
from app.services.tab_job_helpers import (
    submit_batch_product_designs,
    submit_batch_operation,
    collect_job_results,
    check_jobs_progress,
    are_all_jobs_done
)
from app.services.global_job_queue import JobType, get_global_job_queue

def render_campaign_creator_tab():
    st.header("🎯 Campaign Creator")
    st.markdown("Manually generate a complete, professional marketing campaign using the enhanced 12-step workflow.")

    with st.form("campaign_creator_form"):
        st.subheader("1. Define Your Campaign Core")
        product_description = st.text_area(
            "Product/Service Description",
            "e.g., A new line of eco-friendly, reusable coffee cups made from bamboo fiber.",
            height=100,
        )
        target_audience = st.text_input(
            "Target Audience", "e.g., Environmentally conscious millennials aged 25-40."
        )
        budget = st.number_input("Campaign Budget ($)", min_value=100.0, value=5000.0, step=500.0)
        
        st.subheader("2. Select Your Platforms")
        available_platforms = ["Facebook", "Instagram", "Twitter", "LinkedIn", "TikTok", "Pinterest", "YouTube"]
        selected_platforms = st.multiselect(
            "Choose marketing platforms",
            available_platforms,
            default=["Instagram", "Facebook", "TikTok"],
        )
        
        st.subheader("3. Campaign Goals & Strategy")
        campaign_goal = st.selectbox(
            "Primary Campaign Goal",
            ["Brand Awareness", "Lead Generation", "Direct Sales", "Community Building", "Product Launch", "Seasonal Promotion"],
            help="AI will optimize the campaign strategy for this specific goal"
        )
        
        campaign_tone = st.selectbox(
            "Brand Voice / Tone",
            ["Professional", "Playful & Fun", "Inspirational", "Educational", "Bold & Edgy", "Luxurious", "Friendly & Casual"],
            help="Sets the overall tone for all generated content"
        )
        
        competitor_info = st.text_input(
            "Top Competitor (optional)",
            placeholder="e.g., Brand X - helps AI differentiate your campaign",
            help="AI will analyze competitor positioning to make your campaign stand out"
        )

        st.subheader("4. Generation Options")
        fast_mode = st.checkbox(
            "⚡ Fast Mode (skip enhancement step)",
            value=False,
            help="Skips the AI enhancement step for each asset. Cuts generation time roughly in half but results may be less polished."
        )
        
        include_ab_testing = st.checkbox(
            "🔬 Generate A/B Test Variants",
            value=False,
            help="Create multiple headline/image variants for testing"
        )

        submitted = st.form_submit_button("🚀 Generate Complete Campaign!", use_container_width=True)
    
    # AI Campaign Advisor (outside form)
    with st.expander("🤖 AI Campaign Advisor", expanded=False):
        st.markdown("Get AI-powered recommendations before generating your campaign")
        
        advisor_col1, advisor_col2 = st.columns(2)
        with advisor_col1:
            if st.button("📊 Analyze My Strategy", use_container_width=True):
                if product_description:
                    try:
                        replicate_token = _get_replicate_token()
                    except ValueError:
                        replicate_token = None
                    if replicate_token:
                        with st.spinner("🧠 Analyzing your campaign strategy..."):
                            try:
                                import replicate
                                client = replicate.Client(api_token=replicate_token)
                                analysis_prompt = f"""You are a marketing strategist. Analyze this campaign:

Product: {product_description}
Target Audience: {target_audience}
Budget: ${budget}
Platforms: {', '.join(selected_platforms) if selected_platforms else 'Not selected'}

Provide:
1. STRENGTHS of this approach (2 points)
2. RISKS to watch (2 points)
3. ONE specific tactic to maximize ROI
4. Recommended budget split across platforms

Be concise - under 150 words total."""
                                response = tracked_replicate_run(client, "meta/meta-llama-3-8b-instruct", {"prompt": analysis_prompt, "max_tokens": 300}, operation_name="Campaign Analysis")
                                st.session_state['campaign_analysis'] = "".join(response) if isinstance(response, list) else response
                            except Exception as e:
                                st.error(f"Analysis failed: {e}")
                    else:
                        st.warning("Add API key in Settings or set REPLICATE_API_TOKEN")
                else:
                    st.warning("Enter product description first")
        
        with advisor_col2:
            if st.button("💡 Get Headline Ideas", use_container_width=True):
                if product_description:
                    try:
                        replicate_token = _get_replicate_token()
                    except ValueError:
                        replicate_token = None
                    if replicate_token:
                        with st.spinner("✨ Generating headline ideas..."):
                            try:
                                import replicate
                                client = replicate.Client(api_token=replicate_token)
                                headline_prompt = f"""Generate 5 compelling ad headlines for:
Product: {product_description}
Target: {target_audience}

Rules:
- Each headline under 10 words
- Mix emotional and benefit-driven
- Include one question-based headline
- Include one number/statistic headline

Format: Just the 5 headlines, numbered."""
                                response = tracked_replicate_run(client, "meta/meta-llama-3-8b-instruct", {"prompt": headline_prompt, "max_tokens": 200}, operation_name="Headline Generation")
                                st.session_state['headline_ideas'] = "".join(response) if isinstance(response, list) else response
                            except Exception as e:
                                st.error(f"Failed: {e}")
                    else:
                        st.warning("Add API key in Settings")
                else:
                    st.warning("Enter product description first")
        
        if st.session_state.get('campaign_analysis'):
            st.markdown("##### 📊 Strategy Analysis")
            st.markdown(st.session_state['campaign_analysis'])
        
        if st.session_state.get('headline_ideas'):
            st.markdown("##### 💡 Headline Ideas")
            st.markdown(st.session_state['headline_ideas'])

    if submitted:
        if not all([product_description, target_audience, budget, selected_platforms]):
            st.error("Please fill out all fields before generating the campaign.")
        else:
            st.info("🔥 Your request has been submitted! The autonomous agent is now crafting your campaign...")

            # Create a unique directory for this campaign run
            timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
            campaign_name = f"{timestamp}_{product_description[:25].replace(' ', '_')}"
            campaign_dir = Path("campaigns") / campaign_name
            campaign_dir.mkdir(parents=True, exist_ok=True)

            st.write(f"📂 Campaign assets will be saved to: `{campaign_dir}`")

            progress_bar = st.progress(0, text="Initializing campaign generator...")
            status_text = st.empty()

            try:
                # Initialize replicate_api if not in session state
                if 'replicate_api' not in st.session_state or st.session_state.replicate_api is None:
                    replicate_token = get_api_key('REPLICATE_API_TOKEN')
                    if not replicate_token:
                        st.error("❌ REPLICATE_API_TOKEN not found. Please set it in your environment or Settings.")
                        st.stop()
                    from app.services.api_service import ReplicateAPI
                    st.session_state.replicate_api = ReplicateAPI(replicate_token)
                
                # Create generator with fast_mode option
                from campaign_generator_service import EnhancedCampaignGenerator
                generator = EnhancedCampaignGenerator(
                    replicate_api=st.session_state.replicate_api,
                    skip_enhancement=fast_mode
                )
                
                if fast_mode:
                    st.info("⚡ Fast Mode enabled - skipping enhancement steps for faster generation")
                
                # Initialize session state for campaign jobs
                if 'campaign_generation_jobs' not in st.session_state:
                    st.session_state.campaign_generation_jobs = []
                
                # Check if jobs are already running
                if st.session_state.campaign_generation_jobs:
                    job_ids = st.session_state.campaign_generation_jobs
                    progress = check_jobs_progress(job_ids)
                    
                    status_text.text(f"⚡ Parallel Generation: {progress['completed']}/{len(job_ids)} complete")
                    completion_pct = int((progress['completed'] / len(job_ids)) * 90)
                    progress_bar.progress(completion_pct, text=f"Running {progress['running']} jobs...")
                    
                    if are_all_jobs_done(job_ids):
                        # Collect results
                        results = collect_job_results(job_ids)
                        concept, analyzed_concept = results[0] if results[0] else ("", "")
                        plan, analyzed_plan = results[1] if results[1] else ("", "")
                        budget_bytes = results[2] if results[2] else b""
                        schedule_bytes = results[3] if results[3] else b""
                        resources, analyzed_resources = results[4] if results[4] else ("", "")
                        recap, analyzed_recap = results[5] if results[5] else ("", "")
                        
                        # Save spreadsheets
                        if budget_bytes:
                            budget_path = campaign_dir / "budget_spreadsheet.xlsx"
                            with open(budget_path, 'wb') as f: f.write(budget_bytes)
                        if schedule_bytes:
                            schedule_path = campaign_dir / "social_media_schedule.xlsx"
                            with open(schedule_path, 'wb') as f: f.write(schedule_bytes)
                        
                        # Clear jobs
                        st.session_state.campaign_generation_jobs = []
                        
                        status_text.text("Step 7/7: Compiling Master Document and ZIP Archive...")
                        progress_bar.progress(95, text="Step 7/7: Compiling Master Document and ZIP Archive...")
                    else:
                        # Still running, show refresh button
                        if st.button("🔄 Refresh Progress", key="refresh_campaign_progress"):
                            st.rerun()
                        st.stop()
                else:
                    # Submit all jobs in parallel
                    status_text.text("🚀 Submitting 6 parallel generation jobs...")
                    progress_bar.progress(5, text="🚀 Submitting parallel jobs...")
                    
                    queue = get_global_job_queue()
                    job_ids = []
                    
                    # Job 1: Campaign Concept
                    job_ids.append(queue.submit_job(
                        job_type=JobType.TEXT_GENERATION,
                        tab_name="Campaigns",
                        description="Campaign Concept",
                        function=generator.generate_campaign_concept,
                        args=(product_description, target_audience, str(budget), selected_platforms),
                        priority=7
                    ))
                    
                    # Job 2: Marketing Plan
                    job_ids.append(queue.submit_job(
                        job_type=JobType.TEXT_GENERATION,
                        tab_name="Campaigns",
                        description="Marketing Plan",
                        function=generator.generate_marketing_plan,
                        args=(product_description, str(budget), selected_platforms),
                        priority=7
                    ))
                    
                    # Job 3: Budget Spreadsheet
                    job_ids.append(queue.submit_job(
                        job_type=JobType.CAMPAIGN_GENERATION,
                        tab_name="Campaigns",
                        description="Budget Spreadsheet",
                        function=generator.generate_budget_spreadsheet,
                        args=(budget,),
                        priority=6
                    ))
                    
                    # Job 4: Social Media Schedule
                    job_ids.append(queue.submit_job(
                        job_type=JobType.CAMPAIGN_GENERATION,
                        tab_name="Campaigns",
                        description="Social Media Schedule",
                        function=lambda: generator.generate_social_media_schedule("", selected_platforms),
                        priority=6
                    ))
                    
                    # Job 5: Resources & Tips
                    job_ids.append(queue.submit_job(
                        job_type=JobType.TEXT_GENERATION,
                        tab_name="Campaigns",
                        description="Resources & Tips",
                        function=generator.generate_resources_and_tips,
                        args=(product_description, target_audience),
                        priority=6
                    ))
                    
                    # Job 6: Campaign Recap
                    job_ids.append(queue.submit_job(
                        job_type=JobType.TEXT_GENERATION,
                        tab_name="Campaigns",
                        description="Campaign Recap",
                        function=generator.generate_campaign_recap,
                        args=(product_description, str(budget), selected_platforms),
                        priority=6
                    ))
                    
                    st.session_state.campaign_generation_jobs = job_ids
                    st.success(f"✅ Submitted {len(job_ids)} parallel jobs! They'll complete ~7x faster.")
                    st.info("💡 You can switch tabs while generation runs in the background.")
                    time.sleep(1)  # Brief pause to let jobs start
                    st.rerun()

                # If we got here, jobs completed - continue with final steps
                status_text.text("Step 7/7: Compiling Master Document and ZIP Archive...")
                progress_bar.progress(95, text="Step 7/7: Compiling Master Document and ZIP Archive...")
                master_doc = generator.create_master_document()
                zip_buffer = generator.create_campaign_zip(campaign_dir)

                progress_bar.progress(100, text="✅ Campaign Generation Complete!")
                st.success("🎉 Your new marketing campaign is ready!")

                # Display results
                st.subheader("Campaign Summary")
                st.text_area("Campaign Concept", value=concept, height=150, disabled=True)
                st.text_area("Marketing Plan Snippet", value=plan[:500] + "...", height=150, disabled=True)

                # Add to campaign history
                campaign_summary = {
                    "concept": product_description[:50],
                    "timestamp": dt.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "path": str(campaign_dir),
                    "zip_path": str(campaign_dir / "complete_campaign.zip"),
                    "status": "Completed"
                }
                st.session_state.campaign_history.append(campaign_summary)

                # Provide download link for the ZIP file
                st.download_button(
                    label="📦 Download Complete Campaign ZIP",
                    data=zip_buffer,
                    file_name=f"{campaign_name}.zip",
                    mime="application/zip",
                    use_container_width=True,
                )

                st.balloons()

            except Exception as e:
                st.error(f"An error occurred during campaign generation: {e}")
                st.exception(e) # Show full traceback for debugging
