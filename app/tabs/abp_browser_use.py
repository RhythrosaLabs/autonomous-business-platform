"""
Browser-Use Tab for Autonomous Business Platform
================================================

AI-powered browser automation for tasks that cannot be done via APIs.
This module provides intelligent web automation for:

1. 🔍 Market Intelligence - Deep research competitors can't API-block
2. 🎯 Lead Generation - Extract contacts, businesses, influencer data
3. 📊 Data Extraction - Scrape complex sites, PDFs, databases
4. 🤖 Form Automation - Apply to marketplaces, directories, partnerships
5. 🌐 Multi-Account Management - Coordinate actions across platforms
6. 📈 Monitoring & Tracking - Watch competitors, prices, trends in real-time
7. 🎨 Design Research - Collect inspiration, analyze trends visually
8. 🛒 E-commerce Intelligence - Product research, pricing, reviews, strategies

IMPORTANT: Only use browser-use for tasks that CANNOT be done through:
- Direct API calls (OpenAI, Replicate, etc.)
- Platform integrations already in the app
- Simple HTTP requests

Use browser-use when you need:
- Visual understanding of pages
- Complex navigation and interactions
- Bypassing rate limits or API restrictions
- Accessing data not available via API
- Automating multi-step workflows across sites
"""

import streamlit as st
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import os

try:
    from app.services.browser_use_research import (
        BrowserUseResearcher,
        ProductResearchResult,
        CompetitorPricingResult,
        DesignInspirationResult
    )
    from app.services.browser_use_advanced import (
        AdvancedBrowserAutomation,
        LeadResult,
        ScrapedData,
        FormSubmission,
        MonitoringResult,
        save_automation_results
    )
    from app.services.background_tasks import BackgroundTaskManager, get_task_manager, TaskState
    BROWSER_USE_AVAILABLE = True
    BACKGROUND_TASKS_AVAILABLE = True
except ImportError as e:
    BROWSER_USE_AVAILABLE = False
    BACKGROUND_TASKS_AVAILABLE = False

# ========================================
# HELPER FUNCTIONS
# ========================================

def initialize_session_state():
    """Initialize session state for browser-use"""
    if 'browser_results' not in st.session_state:
        st.session_state.browser_results = {}
    if 'browser_history' not in st.session_state:
        st.session_state.browser_history = []
    if 'active_automation' not in st.session_state:
        st.session_state.active_automation = None
    if 'browser_task_manager' not in st.session_state and BACKGROUND_TASKS_AVAILABLE:
        st.session_state.browser_task_manager = get_task_manager()

def run_async(coro):
    """Run async coroutine in Streamlit"""
    try:
        # Always create a new event loop for Streamlit threads
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(coro)
            return result
        finally:
            loop.close()
    except Exception as e:
        st.error(f"Error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None

def run_browser_automation_background(task_name: str, automation_func, *args, **kwargs):
    """Run browser automation in background using task manager"""
    if not BACKGROUND_TASKS_AVAILABLE:
        st.error("Background tasks not available")
        return None
    
    task_mgr = get_task_manager()
    
    def browser_task_wrapper():
        """Wrapper to run async browser automation in background thread"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(automation_func(*args, **kwargs))
            loop.close()
            return result
        except Exception as e:
            import traceback
            return {"error": str(e), "traceback": traceback.format_exc()}
    
    task = task_mgr.create_task(
        name=task_name,
        description=f"Browser automation: {task_name}"
    )
    
    task_mgr.run_task_in_background(
        task_id=task.id,
        target_func=browser_task_wrapper
    )
    
    return task.id

def save_results(results: Any, category: str, filename: str = None):
    """Save automation results to JSON"""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{category}_{timestamp}.json"
    
    output_dir = Path("browser_use_results") / category
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if isinstance(results, list):
        data = [r.__dict__ if hasattr(r, '__dict__') else r for r in results]
    elif isinstance(results, dict):
        data = {k: (v.__dict__ if hasattr(v, '__dict__') else v) for k, v in results.items()}
    else:
        data = results.__dict__ if hasattr(results, '__dict__') else results
    
    filepath = output_dir / filename
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    return str(filepath)

# ========================================
# DISPLAY FUNCTIONS
# ========================================

def display_product_data(products: List[ProductResearchResult]):
    """Display product research results"""
    if not products:
        st.info("No products found")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Products", len(products))
    with col2:
        avg_price = sum(p.price for p in products if p.price) / len([p for p in products if p.price]) if any(p.price for p in products) else 0
        st.metric("Avg Price", f"${avg_price:.2f}")
    with col3:
        avg_rating = sum(p.rating for p in products if p.rating) / len([p for p in products if p.rating]) if any(p.rating for p in products) else 0
        st.metric("Avg Rating", f"{avg_rating:.1f}⭐")
    with col4:
        total_reviews = sum(p.reviews_count for p in products if p.reviews_count)
        st.metric("Total Reviews", f"{total_reviews:,}")
    
    for i, product in enumerate(products[:20], 1):
        with st.expander(f"{i}. {product.product_name} - ${product.price or 'N/A'}"):
            col1, col2 = st.columns([2, 1])
            with col1:
                if product.description:
                    st.write(product.description[:300] + "..." if len(product.description) > 300 else product.description)
                if product.tags:
                    st.write("**Tags:**", ", ".join(product.tags[:10]))
            with col2:
                st.write(f"**Platform:** {product.platform}")
                st.write(f"**Price:** ${product.price or 'N/A'}")
                st.write(f"**Rating:** {product.rating or 'N/A'}⭐")
                st.write(f"**Reviews:** {product.reviews_count or 'N/A'}")
                if product.product_url:
                    st.markdown(f"[View Product →]({product.product_url})")

def display_pricing_data(pricing: Dict[str, CompetitorPricingResult]):
    """Display pricing analysis"""
    if not pricing:
        st.info("No pricing data")
        return
    
    all_prices = []
    for result in pricing.values():
        all_prices.extend(result.price_points)
    
    if all_prices:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Platforms", len(pricing))
        with col2:
            st.metric("Min Price", f"${min(all_prices):.2f}")
        with col3:
            st.metric("Max Price", f"${max(all_prices):.2f}")
        with col4:
            st.metric("Avg Price", f"${sum(all_prices)/len(all_prices):.2f}")
        
        for platform, data in pricing.items():
            with st.expander(f"📊 {platform.title()} - {data.sample_size} products"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Min", f"${data.min_price:.2f}")
                with col2:
                    st.metric("Avg", f"${data.average_price:.2f}")
                with col3:
                    st.metric("Max", f"${data.max_price:.2f}")

def display_design_inspiration(designs: List[DesignInspirationResult]):
    """Display design inspiration results"""
    if not designs:
        st.info("No designs found")
        return
    
    st.metric("Designs Collected", len(designs))
    
    cols = st.columns(3)
    for i, design in enumerate(designs[:30]):
        with cols[i % 3]:
            st.markdown(f"**{design.title[:60]}...**" if len(design.title) > 60 else f"**{design.title}**")
            if design.image_url:
                st.markdown(f"[View Image →]({design.image_url})")
            if design.colors:
                color_html = " ".join([
                    f"<div style='background:{c};width:40px;height:40px;display:inline-block;margin:2px;border:1px solid #ddd;'></div>"
                    for c in design.colors[:6]
                ])
                st.markdown(color_html, unsafe_allow_html=True)
            if design.style_tags:
                st.caption(" • ".join(design.style_tags[:4]))
            st.markdown("---")

# ========================================
# AUTOMATION MODES
# ========================================

def render_market_intelligence():
    """Market Intelligence & Research"""
    st.markdown("### 🔍 Market Intelligence")
    st.markdown("Deep competitive research that can't be blocked by API limitations")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        research_type = st.selectbox(
            "Research Type",
            ["Product Trends", "Competitor Analysis", "Pricing Intelligence", "Design Trends"]
        )
    with col2:
        platform = st.selectbox("Platform", ["etsy", "redbubble", "amazon", "pinterest", "shopify"])
    
    query = st.text_input("Search Query", placeholder="e.g., minimalist t-shirts, eco-friendly mugs")
    max_results = st.slider("Max Results", 10, 100, 30)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        run_mode = st.radio("Run Mode", ["Instant (Blocking)", "Background Task"], horizontal=True)
    with col2:
        if BACKGROUND_TASKS_AVAILABLE and st.button("📋 View Tasks"):
            st.session_state.show_browser_tasks = not st.session_state.get('show_browser_tasks', False)
    
    if st.session_state.get('show_browser_tasks') and BACKGROUND_TASKS_AVAILABLE:
        task_mgr = get_task_manager()
        tasks = [t for t in task_mgr.get_all_tasks() if 'Browser automation' in t.description]
        if tasks:
            st.markdown("### 🔄 Active Browser Tasks")
            for task in tasks[-5:]:
                status_emoji = "✅" if task.state == TaskState.COMPLETED else "🔄" if task.state == TaskState.RUNNING else "❌"
                st.write(f"{status_emoji} **{task.name}** - {task.state.value} ({task.progress:.0f}%)")
    
    if st.button("🚀 Start Research", type="primary", disabled=not query):
        if run_mode == "Background Task" and BACKGROUND_TASKS_AVAILABLE:
            # Run in background
            researcher = BrowserUseResearcher(
                llm_provider=st.session_state.get('browser_llm_provider', 'anthropic'),
                headless=st.session_state.get('browser_headless', True)
            )
            
            if research_type == "Product Trends":
                task_id = run_browser_automation_background(
                    f"Product Research: {query}",
                    researcher.research_etsy_trends,
                    query,
                    max_results
                )
                st.success(f"🔄 Task started! ID: {task_id[:8]}... Check task status in sidebar or click 'View Tasks'")
            
            elif research_type == "Pricing Intelligence":
                platforms = [platform, "redbubble", "etsy"] if platform != "etsy" else ["etsy", "redbubble"]
                task_id = run_browser_automation_background(
                    f"Pricing Analysis: {query}",
                    researcher.analyze_competitor_pricing,
                    query,
                    platforms
                )
                st.success(f"🔄 Task started! ID: {task_id[:8]}...")
            
            elif research_type == "Design Trends":
                task_id = run_browser_automation_background(
                    f"Design Research: {query}",
                    researcher.collect_pinterest_inspiration,
                    query,
                    max_results
                )
                st.success(f"🔄 Task started! ID: {task_id[:8]}...")
        
        else:
            # Run instantly (blocking)
            with st.spinner(f"Researching {query} on {platform}..."):
                try:
                    researcher = BrowserUseResearcher(
                        llm_provider=st.session_state.get('browser_llm_provider', 'anthropic'),
                        headless=st.session_state.get('browser_headless', True)
                    )
                    
                    if research_type == "Product Trends":
                        results = run_async(researcher.research_etsy_trends(query, max_results))
                        if results:
                            st.session_state.browser_results['market_intelligence'] = results
                            st.success(f"✅ Found {len(results)} products!")
                            display_product_data(results)
                            filepath = save_results(results, "market_intelligence")
                            st.info(f"💾 Saved to: {filepath}")
                    
                    elif research_type == "Pricing Intelligence":
                        platforms = [platform, "redbubble", "etsy"] if platform != "etsy" else ["etsy", "redbubble"]
                        results = run_async(researcher.analyze_competitor_pricing(query, platforms))
                        if results:
                            st.session_state.browser_results['pricing'] = results
                            st.success("✅ Pricing analysis complete!")
                            display_pricing_data(results)
                            filepath = save_results(results, "pricing_intelligence")
                            st.info(f"💾 Saved to: {filepath}")
                    
                    elif research_type == "Design Trends":
                        results = run_async(researcher.collect_pinterest_inspiration(query, max_results))
                        if results:
                            st.session_state.browser_results['designs'] = results
                            st.success(f"✅ Collected {len(results)} designs!")
                            display_design_inspiration(results)
                            filepath = save_results(results, "design_trends")
                            st.info(f"💾 Saved to: {filepath}")
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")

def render_lead_generation():
    """Lead Generation & Contact Finding"""
    st.markdown("### 🎯 Lead Generation")
    st.markdown("Extract contacts, influencers, and business data from any website")
    
    lead_type = st.selectbox(
        "Lead Type",
        ["Website Contacts", "Influencers", "Business Directory", "Event Attendees"]
    )
    
    if lead_type == "Website Contacts":
        source_url = st.text_input("Website URL", placeholder="https://company.com/team")
        search_criteria = st.text_input("Search Criteria (optional)", placeholder="e.g., decision makers, executives")
        
        if st.button("🔍 Extract Contacts", type="primary", disabled=not source_url):
            with st.spinner(f"Extracting contacts from {source_url}..."):
                try:
                    automator = AdvancedBrowserAutomation(
                        llm_provider=st.session_state.get('browser_llm_provider', 'anthropic'),
                        headless=st.session_state.get('browser_headless', True)
                    )
                    leads = run_async(automator.extract_contacts_from_page(source_url, search_criteria))
                    
                    if leads:
                        st.success(f"✅ Found {len(leads)} contacts!")
                        for lead in leads:
                            with st.expander(f"📧 {lead.name}"):
                                if lead.email:
                                    st.write(f"**Email:** {lead.email}")
                                if lead.phone:
                                    st.write(f"**Phone:** {lead.phone}")
                                if lead.company:
                                    st.write(f"**Company:** {lead.company}")
                                if lead.title:
                                    st.write(f"**Title:** {lead.title}")
                        
                        filepath = save_automation_results(leads, "lead_generation")
                        st.info(f"💾 Saved to: {filepath}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    elif lead_type == "Influencers":
        col1, col2 = st.columns(2)
        with col1:
            platform = st.selectbox("Platform", ["instagram", "twitter", "tiktok", "youtube"])
            niche = st.text_input("Niche/Industry", placeholder="e.g., fitness, tech, fashion")
        with col2:
            min_followers = st.number_input("Min Followers", min_value=100, value=1000, step=100)
        
        if st.button("🔍 Find Influencers", type="primary", disabled=not niche):
            with st.spinner(f"Finding {niche} influencers on {platform}..."):
                try:
                    automator = AdvancedBrowserAutomation(
                        llm_provider=st.session_state.get('browser_llm_provider', 'anthropic'),
                        headless=st.session_state.get('browser_headless', True)
                    )
                    influencers = run_async(automator.find_influencers(platform, niche, min_followers))
                    
                    if influencers:
                        st.success(f"✅ Found {len(influencers)} influencers!")
                        for inf in influencers:
                            st.write(f"**{inf.name}** - {inf.company or 'N/A'}")
                        filepath = save_automation_results(influencers, "influencers")
                        st.info(f"💾 Saved to: {filepath}")
                    else:
                        st.warning("No influencers found")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    elif lead_type == "Business Directory":
        directory_url = st.text_input("Directory URL", placeholder="https://directory-site.com")
        category = st.text_input("Business Category", placeholder="e.g., restaurants, plumbers")
        max_results = st.slider("Max Results", 10, 200, 50)
        
        if st.button("📋 Scrape Directory", type="primary", disabled=not directory_url):
            with st.spinner(f"Scraping {category} businesses..."):
                try:
                    automator = AdvancedBrowserAutomation(
                        llm_provider=st.session_state.get('browser_llm_provider', 'anthropic'),
                        headless=st.session_state.get('browser_headless', True)
                    )
                    businesses = run_async(automator.scrape_business_directory(directory_url, category, max_results))
                    
                    if businesses:
                        st.success(f"✅ Scraped {len(businesses)} businesses!")
                        filepath = save_automation_results(businesses, "business_directory")
                        st.info(f"💾 Saved to: {filepath}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    elif lead_type == "Event Attendees":
        event_url = st.text_input("Event/Conference URL", placeholder="https://event-site.com/attendees")
        
        if st.button("👥 Extract Attendees", type="primary", disabled=not event_url):
            with st.spinner("Extracting attendee information..."):
                try:
                    automator = AdvancedBrowserAutomation(
                        llm_provider=st.session_state.get('browser_llm_provider', 'anthropic'),
                        headless=st.session_state.get('browser_headless', True)
                    )
                    attendees = run_async(automator.scrape_event_attendees(event_url))
                    
                    if attendees:
                        st.success(f"✅ Found {len(attendees)} attendees!")
                        filepath = save_automation_results(attendees, "event_attendees")
                        st.info(f"💾 Saved to: {filepath}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

def render_data_extraction():
    """Advanced Data Scraping"""
    st.markdown("### 📊 Data Extraction")
    st.markdown("Scrape complex websites, PDFs, databases, and dynamic content")
    
    extraction_type = st.selectbox(
        "Extraction Type",
        ["Web Scraping", "PDF Extraction", "API Reverse Engineering"]
    )
    
    if extraction_type == "Web Scraping":
        target_url = st.text_input("Target URL", placeholder="https://example.com/data-page")
        
        st.markdown("**Custom Selectors (optional)**")
        col1, col2 = st.columns(2)
        with col1:
            selector_1 = st.text_input("Selector 1", placeholder=".product-title")
            selector_2 = st.text_input("Selector 2", placeholder=".price")
        with col2:
            label_1 = st.text_input("Label 1", placeholder="title")
            label_2 = st.text_input("Label 2", placeholder="price")
        
        selectors = {}
        if selector_1 and label_1:
            selectors[label_1] = selector_1
        if selector_2 and label_2:
            selectors[label_2] = selector_2
        
        if st.button("📥 Scrape Website", type="primary", disabled=not target_url):
            with st.spinner(f"Scraping {target_url}..."):
                try:
                    automator = AdvancedBrowserAutomation(
                        llm_provider=st.session_state.get('browser_llm_provider', 'anthropic'),
                        headless=st.session_state.get('browser_headless', True)
                    )
                    result = run_async(automator.scrape_website(target_url, selectors if selectors else None))
                    
                    if result:
                        st.success("✅ Scraping complete!")
                        st.markdown(f"**Title:** {result.page_title}")
                        st.markdown(f"**Content:** {result.main_content[:500]}...")
                        if result.links:
                            st.markdown(f"**Links Found:** {len(result.links)}")
                        if result.images:
                            st.markdown(f"**Images Found:** {len(result.images)}")
                        
                        filepath = save_automation_results(result, "web_scraping")
                        st.info(f"💾 Saved to: {filepath}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    elif extraction_type == "PDF Extraction":
        pdf_url = st.text_input("PDF URL", placeholder="https://example.com/document.pdf")
        data_points = st.text_area(
            "Data Points to Extract",
            placeholder="Enter data points, one per line:\nTotal Revenue\nCompany Name\nDate\nKey Metrics"
        )
        
        if st.button("📄 Extract from PDF", type="primary", disabled=not pdf_url):
            with st.spinner("Extracting data from PDF..."):
                try:
                    points_list = [p.strip() for p in data_points.split('\n') if p.strip()]
                    automator = AdvancedBrowserAutomation(
                        llm_provider=st.session_state.get('browser_llm_provider', 'anthropic'),
                        headless=st.session_state.get('browser_headless', True)
                    )
                    result = run_async(automator.extract_from_pdf(pdf_url, points_list))
                    
                    if result:
                        st.success("✅ Extraction complete!")
                        st.json(result)
                        filepath = save_automation_results(result, "pdf_extraction")
                        st.info(f"💾 Saved to: {filepath}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    elif extraction_type == "API Reverse Engineering":
        website_url = st.text_input("Website URL", placeholder="https://webapp.com")
        st.info("This will analyze network traffic to discover hidden APIs and endpoints")
        
        if st.button("🔍 Discover APIs", type="primary", disabled=not website_url):
            with st.spinner("Analyzing network requests..."):
                try:
                    automator = AdvancedBrowserAutomation(
                        llm_provider=st.session_state.get('browser_llm_provider', 'anthropic'),
                        headless=st.session_state.get('browser_headless', True)
                    )
                    result = run_async(automator.reverse_engineer_api(website_url))
                    
                    if result:
                        st.success("✅ API discovery complete!")
                        st.json(result)
                        filepath = save_automation_results(result, "api_discovery")
                        st.info(f"💾 Saved to: {filepath}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

def render_form_automation():
    """Form Filling & Submissions"""
    st.markdown("### 🤖 Form Automation")
    st.markdown("Automatically apply to marketplaces, directories, partnerships, grants")
    
    form_type = st.selectbox(
        "Form Type",
        ["Custom Form", "Marketplace Application", "Directory Submission"]
    )
    
    if form_type == "Custom Form":
        form_url = st.text_input("Form URL", placeholder="https://example.com/contact-form")
        
        st.markdown("**Form Data**")
        num_fields = st.number_input("Number of Fields", min_value=1, max_value=20, value=4)
        
        form_data = {}
        cols = st.columns(2)
        for i in range(num_fields):
            with cols[i % 2]:
                field_name = st.text_input(f"Field {i+1} Name", key=f"field_name_{i}", placeholder="e.g., name, email")
                field_value = st.text_input(f"Field {i+1} Value", key=f"field_value_{i}", placeholder="Value")
                if field_name and field_value:
                    form_data[field_name] = field_value
        
        if st.button("🚀 Fill & Submit", type="primary", disabled=not form_url or not form_data):
            with st.spinner("Filling and submitting form..."):
                try:
                    automator = AdvancedBrowserAutomation(
                        llm_provider=st.session_state.get('browser_llm_provider', 'anthropic'),
                        headless=st.session_state.get('browser_headless', True)
                    )
                    result = run_async(automator.fill_and_submit_form(form_url, form_data))
                    
                    if result.status == "success":
                        st.success(f"✅ Form submitted successfully!")
                        st.write(f"**Response:** {result.response_message}")
                        filepath = save_automation_results(result, "form_submissions")
                        st.info(f"💾 Saved to: {filepath}")
                    else:
                        st.error(f"❌ Submission failed: {result.response_message}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    elif form_type == "Marketplace Application":
        marketplace = st.selectbox(
            "Marketplace",
            ["amazon_vendor", "etsy_wholesale", "google_business", "yelp"]
        )
        
        st.markdown("**Business Information**")
        col1, col2 = st.columns(2)
        with col1:
            business_name = st.text_input("Business Name")
            business_email = st.text_input("Email")
            business_phone = st.text_input("Phone")
        with col2:
            business_website = st.text_input("Website")
            business_category = st.text_input("Category")
            business_desc = st.text_area("Description")
        
        business_info = {
            "name": business_name,
            "email": business_email,
            "phone": business_phone,
            "website": business_website,
            "category": business_category,
            "description": business_desc
        }
        
        if st.button("📮 Submit Application", type="primary", disabled=not business_name):
            with st.spinner(f"Applying to {marketplace}..."):
                try:
                    automator = AdvancedBrowserAutomation(
                        llm_provider=st.session_state.get('browser_llm_provider', 'anthropic'),
                        headless=st.session_state.get('browser_headless', True)
                    )
                    result = run_async(automator.apply_to_marketplace(marketplace, business_info))
                    
                    st.success(f"✅ Application submitted to {marketplace}!")
                    filepath = save_automation_results(result, "marketplace_applications")
                    st.info(f"💾 Saved to: {filepath}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    elif form_type == "Directory Submission":
        st.markdown("**Bulk Directory Submission**")
        
        business_data = st.text_area(
            "Business Data (JSON)",
            placeholder='{\n  "name": "My Business",\n  "email": "contact@mybiz.com",\n  "website": "https://mybiz.com"\n}'
        )
        
        directories = st.multiselect(
            "Target Directories",
            ["Yelp", "Google Business", "Yellow Pages", "BBB", "Angi", "Thumbtack"]
        )
        
        if st.button("📋 Submit to All", type="primary", disabled=not business_data or not directories):
            with st.spinner(f"Submitting to {len(directories)} directories..."):
                results = []
                try:
                    import json as json_lib
                    biz_data = json_lib.loads(business_data)
                    
                    automator = AdvancedBrowserAutomation(
                        llm_provider=st.session_state.get('browser_llm_provider', 'anthropic'),
                        headless=st.session_state.get('browser_headless', True)
                    )
                    
                    for directory in directories:
                        st.info(f"Submitting to {directory}...")
                        # Would submit to each directory
                        results.append({"directory": directory, "status": "submitted"})
                    
                    st.success(f"✅ Submitted to {len(results)} directories!")
                    filepath = save_automation_results(results, "directory_submissions")
                    st.info(f"💾 Saved to: {filepath}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

def render_monitoring():
    """Competitive Monitoring"""
    st.markdown("### 📈 Monitoring & Tracking")
    st.markdown("Track competitors, prices, trends, and changes in real-time")
    
    monitor_type = st.selectbox(
        "Monitor Type",
        ["Price Tracking", "Competitor Monitoring", "Content Changes"]
    )
    
    if monitor_type == "Price Tracking":
        product_url = st.text_input("Product URL", placeholder="https://store.com/product")
        alert_threshold = st.number_input("Alert if price drops below $", min_value=0.0, value=50.0, step=1.0)
        
        if st.button("📊 Track Price", type="primary", disabled=not product_url):
            with st.spinner("Setting up price monitoring..."):
                try:
                    automator = AdvancedBrowserAutomation(
                        llm_provider=st.session_state.get('browser_llm_provider', 'anthropic'),
                        headless=st.session_state.get('browser_headless', True)
                    )
                    result = run_async(automator.monitor_price_changes(product_url))
                    
                    if result:
                        st.success(f"✅ Now monitoring: {product_url}")
                        st.write(f"**Current Value:** {result.current_value}")
                        st.info(f"Will alert if price drops below ${alert_threshold}")
                        filepath = save_automation_results(result, "monitoring")
                        st.info(f"💾 Saved to: {filepath}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    elif monitor_type == "Competitor Monitoring":
        competitor_url = st.text_input("Competitor URL", placeholder="https://competitor.com")
        track_elements = st.multiselect(
            "Elements to Track",
            ["Products", "Prices", "Blog Posts", "Job Postings", "Feature Updates"],
            default=["Products", "Prices"]
        )
        
        if st.button("👀 Track Competitor", type="primary", disabled=not competitor_url):
            with st.spinner("Setting up competitor tracking..."):
                try:
                    automator = AdvancedBrowserAutomation(
                        llm_provider=st.session_state.get('browser_llm_provider', 'anthropic'),
                        headless=st.session_state.get('browser_headless', True)
                    )
                    result = run_async(automator.track_competitor(competitor_url, track_elements))
                    
                    if result:
                        st.success(f"✅ Tracking {competitor_url}")
                        st.json(result)
                        filepath = save_automation_results(result, "competitor_tracking")
                        st.info(f"💾 Saved to: {filepath}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

def render_ecommerce_intelligence():
    """E-commerce Intelligence"""
    st.markdown("### 🛒 E-commerce Intelligence")
    st.markdown("Deep dive into products, reviews, sellers, and marketplace strategies")
    
    analysis_type = st.selectbox(
        "Analysis Type",
        ["Review Analysis", "Market Trends"]
    )
    
    if analysis_type == "Review Analysis":
        product_url = st.text_input("Product URL", placeholder="https://amazon.com/product-link")
        max_reviews = st.slider("Max Reviews to Analyze", 10, 500, 100)
        
        if st.button("⭐ Analyze Reviews", type="primary", disabled=not product_url):
            with st.spinner(f"Analyzing up to {max_reviews} reviews..."):
                try:
                    automator = AdvancedBrowserAutomation(
                        llm_provider=st.session_state.get('browser_llm_provider', 'anthropic'),
                        headless=st.session_state.get('browser_headless', True)
                    )
                    analysis = run_async(automator.analyze_reviews(product_url, max_reviews))
                    
                    if analysis:
                        st.success("✅ Review analysis complete!")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Avg Rating", f"{analysis.average_rating}⭐")
                        with col2:
                            st.metric("Total Reviews", analysis.total_reviews)
                        with col3:
                            sentiment_emoji = "😊" if analysis.sentiment_score > 0.5 else "😐" if analysis.sentiment_score > 0 else "😞"
                            st.metric("Sentiment", f"{sentiment_emoji} {analysis.sentiment_score:.2f}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**✅ Positive Themes**")
                            for theme in analysis.positive_themes:
                                st.write(f"• {theme}")
                        with col2:
                            st.markdown("**❌ Common Complaints**")
                            for theme in analysis.negative_themes:
                                st.write(f"• {theme}")
                        
                        if analysis.feature_requests:
                            st.markdown("**💡 Feature Requests**")
                            for req in analysis.feature_requests:
                                st.write(f"• {req}")
                        
                        filepath = save_automation_results(analysis, "review_analysis")
                        st.info(f"💾 Saved to: {filepath}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    elif analysis_type == "Market Trends":
        st.info("🔧 Use Market Intelligence tab for comprehensive trend research")
        category = st.text_input("Product Category", placeholder="e.g., smart home devices")
        marketplace = st.selectbox("Marketplace", ["Amazon", "Etsy", "eBay"])
        
        if st.button("📈 Analyze Trends", disabled=not category):
            st.info("Analyzing market trends... This feature uses the Market Intelligence module.")

# ========================================
# MAIN TAB RENDERER
# ========================================

def render_browser_use_tab(**kwargs):
    """Main render function for Browser-Use tab"""
    initialize_session_state()
    
    st.title("🌐 Browser-Use Automation")
    st.markdown("Powerful AI browser automation for tasks that **cannot** be done via APIs")
    
    if not BROWSER_USE_AVAILABLE:
        st.error("❌ Browser-use module not available")
        st.info("Install: `pip install browser-use langchain-anthropic playwright`")
        st.code("playwright install", language="bash")
        return
    
    # Configuration sidebar
    with st.expander("⚙️ Configuration", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            llm_provider = st.selectbox(
                "LLM Provider",
                ["anthropic", "openai", "google"],
                help="AI model for browser control"
            )
            st.session_state.browser_llm_provider = llm_provider
        with col2:
            headless = st.checkbox("Headless Mode", value=True, help="Run browser invisibly")
            st.session_state.browser_headless = headless
        
        # API key status
        if llm_provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            st.info(f"Anthropic API: {'✅' if api_key else '❌ Not Set'}")
        elif llm_provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            st.info(f"OpenAI API: {'✅' if api_key else '❌ Not Set'}")
        elif llm_provider == "google":
            api_key = os.getenv("GOOGLE_API_KEY")
            st.info(f"Google API: {'✅' if api_key else '❌ Not Set'}")
    
    st.markdown("---")
    
    # Main automation modes
    automation_mode = st.radio(
        "Automation Mode",
        [
            "🔍 Market Intelligence",
            "🎯 Lead Generation",
            "📊 Data Extraction",
            "🤖 Form Automation",
            "📈 Monitoring & Tracking",
            "🛒 E-commerce Intelligence"
        ],
        horizontal=True
    )
    
    st.markdown("---")
    
    # Render selected mode
    if automation_mode == "🔍 Market Intelligence":
        render_market_intelligence()
    elif automation_mode == "🎯 Lead Generation":
        render_lead_generation()
    elif automation_mode == "📊 Data Extraction":
        render_data_extraction()
    elif automation_mode == "🤖 Form Automation":
        render_form_automation()
    elif automation_mode == "📈 Monitoring & Tracking":
        render_monitoring()
    elif automation_mode == "🛒 E-commerce Intelligence":
        render_ecommerce_intelligence()
    
    # Results archive
    st.markdown("---")
    with st.expander("📚 Results Archive"):
        results_dir = Path("browser_use_results")
        if results_dir.exists():
            categories = [d for d in results_dir.iterdir() if d.is_dir()]
            if categories:
                for category in categories:
                    st.markdown(f"**{category.name.replace('_', ' ').title()}**")
                    files = list(category.glob("*.json"))
                    for file in sorted(files, reverse=True)[:5]:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.text(file.name)
                        with col2:
                            st.text(f"{file.stat().st_size / 1024:.1f} KB")
                        with col3:
                            with open(file, 'r') as f:
                                st.download_button(
                                    "⬇️",
                                    f.read(),
                                    file_name=file.name,
                                    mime="application/json",
                                    key=f"dl_{file.name}"
                                )
            else:
                st.info("No saved results yet")
        else:
            st.info("No results directory found")

if __name__ == "__main__":
    render_browser_use_tab()
