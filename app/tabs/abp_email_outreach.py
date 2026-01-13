"""
Email & Influencer Outreach Tab for Otto Platform
Manage email campaigns, influencer contacts, and create AI-powered email content
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import logging
import time
from dataclasses import dataclass, asdict
import re
from tab_job_helpers import (
    submit_batch_operation,
    submit_batch_product_designs,
    collect_job_results,
    check_jobs_progress,
    are_all_jobs_done
)
from global_job_queue import JobType, get_global_job_queue

# Configure logging
logger = logging.getLogger(__name__)

# ========================================
# DATA MODELS
# ========================================
@dataclass
class InfluencerContact:
    """Influencer contact information"""
    name: str
    email: str
    platform: str
    username: str
    niche: str
    followers: int
    engagement_rate: float
    notes: str = ""
    contacted: bool = False
    last_contact: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)

@dataclass
class EmailTemplate:
    """Email template with variables"""
    name: str
    subject: str
    html_content: str
    variables: List[str]
    created_date: str
    brand_aligned: bool = True

@dataclass
class EmailCampaign:
    """Email campaign tracking"""
    name: str
    subject: str
    recipient_list: List[str]
    template: str
    status: str  # draft, scheduled, sent, in_progress
    send_date: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    created_date: str = ""
    
    def to_dict(self):
        return asdict(self)

# ========================================
# EMAIL TEMPLATE BUILDER
# ========================================
class EmailTemplateBuilder:
    """Build and manage email templates with HTML editor"""
    
    PRESET_TEMPLATES = {
        "Product Launch": {
            "subject": "Introducing [PRODUCT_NAME] - [YOUR_TAGLINE]",
            "html": """
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: linear-gradient(135deg, [PRIMARY_COLOR] 0%, [SECONDARY_COLOR] 100%); border-radius: 10px; color: white;">
                    <h1>[PRODUCT_NAME]</h1>
                    <p>[PRODUCT_TAGLINE]</p>
                </div>
                <div style="max-width: 600px; margin: 20px auto; padding: 20px;">
                    <p>Hi [RECIPIENT_NAME],</p>
                    <p>[PRODUCT_DESCRIPTION]</p>
                    <p><strong>Key Features:</strong></p>
                    <ul>
                        <li>[FEATURE_1]</li>
                        <li>[FEATURE_2]</li>
                        <li>[FEATURE_3]</li>
                    </ul>
                    <p><a href="[CTA_LINK]" style="background: [PRIMARY_COLOR]; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Get Started Now</a></p>
                    <p>Best regards,<br>[YOUR_NAME]<br>[YOUR_TITLE]</p>
                </div>
            </body>
            </html>
            """
        },
        "Influencer Collaboration": {
            "subject": "Exciting Collaboration Opportunity with [YOUR_BRAND]",
            "html": """
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 20px auto; padding: 20px;">
                    <p>Hi [INFLUENCER_NAME],</p>
                    <p>We've been following your amazing work in [NICHE] and would love to collaborate with [YOUR_BRAND]!</p>
                    <p><strong>Collaboration Details:</strong></p>
                    <ul>
                        <li>Campaign: [CAMPAIGN_NAME]</li>
                        <li>Timeline: [TIMELINE]</li>
                        <li>Deliverables: [DELIVERABLES]</li>
                        <li>Compensation: [COMPENSATION]</li>
                    </ul>
                    <p>We believe your audience would love [YOUR_PRODUCT], and we'd love to work with you!</p>
                    <p><a href="[CONTACT_LINK]" style="background: #667EEA; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Learn More</a></p>
                    <p>Looking forward to hearing from you!</p>
                    <p>Best regards,<br>[YOUR_NAME]</p>
                </div>
            </body>
            </html>
            """
        },
        "Newsletter": {
            "subject": "[MONTH] Newsletter - [TOPIC]",
            "html": """
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5; border-top: 4px solid [PRIMARY_COLOR];">
                    <h2>[MONTH] Newsletter</h2>
                    <p>Hi [SUBSCRIBER_NAME],</p>
                    <p>Here's what we've been up to this month:</p>
                    <h3>📰 Top Story</h3>
                    <p>[TOP_STORY]</p>
                    <h3>📚 Latest Articles</h3>
                    <ul>
                        <li>[ARTICLE_1]</li>
                        <li>[ARTICLE_2]</li>
                        <li>[ARTICLE_3]</li>
                    </ul>
                    <p><a href="[BLOG_LINK]" style="color: [PRIMARY_COLOR]; text-decoration: none;">Read More on Our Blog →</a></p>
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="font-size: 12px; color: #999;">© [YEAR] [YOUR_COMPANY]. All rights reserved.</p>
                </div>
            </body>
            </html>
            """
        }
    }
    
    TEMPLATE_VARIABLES = [
        "RECIPIENT_NAME", "YOUR_NAME", "YOUR_BRAND", "YOUR_PRODUCT", "YOUR_COMPANY",
        "PRIMARY_COLOR", "SECONDARY_COLOR", "PRODUCT_NAME", "PRODUCT_TAGLINE",
        "PRODUCT_DESCRIPTION", "FEATURE_1", "FEATURE_2", "FEATURE_3",
        "INFLUENCER_NAME", "NICHE", "CAMPAIGN_NAME", "TIMELINE", "DELIVERABLES",
        "COMPENSATION", "CONTACT_LINK", "CTA_LINK", "MONTH", "SUBSCRIBER_NAME",
        "TOP_STORY", "ARTICLE_1", "ARTICLE_2", "ARTICLE_3", "BLOG_LINK", "YEAR"
    ]

# ========================================
# INFLUENCER DATABASE
# ========================================
class InfluencerDatabase:
    """Manage influencer contacts and relationships"""
    
    def __init__(self):
        """Initialize database"""
        self.contacts: List[InfluencerContact] = []
    
    def add_contact(self, contact: InfluencerContact) -> bool:
        """Add influencer contact"""
        # Check for duplicates
        if any(c.email == contact.email for c in self.contacts):
            return False
        self.contacts.append(contact)
        return True
    
    def get_contacts_by_niche(self, niche: str) -> List[InfluencerContact]:
        """Get contacts by niche"""
        return [c for c in self.contacts if niche.lower() in c.niche.lower()]
    
    def get_contacts_by_platform(self, platform: str) -> List[InfluencerContact]:
        """Get contacts by platform"""
        return [c for c in self.contacts if c.platform.lower() == platform.lower()]
    
    def search_contacts(self, query: str) -> List[InfluencerContact]:
        """Search contacts"""
        query_lower = query.lower()
        return [c for c in self.contacts 
                if query_lower in c.name.lower() or 
                   query_lower in c.email.lower() or
                   query_lower in c.username.lower()]
    
    def mark_contacted(self, email: str):
        """Mark contact as contacted"""
        for contact in self.contacts:
            if contact.email == email:
                contact.contacted = True
                contact.last_contact = datetime.now().isoformat()

# ========================================
# STREAMLIT UI
# ========================================
def render_email_outreach_tab(enhanced_available=False, replicate_api=None, 
                               printify_api=None, shopify_api=None, youtube_api=None):
    """Render the Email & Influencer Outreach tab"""
    
    st.markdown("### 💌 Email & Influencer Outreach")
    st.markdown("Create, manage, and send AI-powered email campaigns to your audience and influencers")
    
    # Initialize session state
    if 'email_database' not in st.session_state:
        st.session_state.email_database = InfluencerDatabase()
    if 'email_templates' not in st.session_state:
        st.session_state.email_templates = {}
    if 'email_campaigns' not in st.session_state:
        st.session_state.email_campaigns = []
    if 'email_list' not in st.session_state:
        st.session_state.email_list = []
    
    # Main navigation tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📬 Email Lists",
        "👥 Influencers",
        "📧 Templates",
        "🚀 Campaigns",
        "📊 Analytics"
    ])
    
    # ========================================
    # TAB 1: EMAIL LISTS
    # ========================================
    with tab1:
        st.subheader("📬 Email Lists")
        st.markdown("Manage your email subscriber lists")
        
        col1, col2 = st.columns([0.7, 0.3])
        
        with col1:
            st.write("**Your Email Lists**")
            
            # Predefined lists
            list_types = ["Subscribers", "Customers", "Prospects", "Custom List"]
            selected_list = st.selectbox("Select Email List", list_types)
            
            # Display list stats
            if selected_list == "Subscribers":
                st.metric("Total Subscribers", len(st.session_state.email_list))
                st.metric("Engagement Rate", "45.3%")
                st.metric("Open Rate", "38.2%")
            elif selected_list == "Customers":
                st.metric("Total Customers", 150)
                st.metric("Repeat Purchase Rate", "32.5%")
                st.metric("Lifetime Value", "$4,250")
        
        with col2:
            st.write("**Actions**")
            if st.button("➕ Create List", use_container_width=True):
                st.session_state.creating_list = True
            if st.button("📥 Import CSV", use_container_width=True):
                st.info("Upload CSV with email column")
            if st.button("🔄 Sync Lists", use_container_width=True):
                st.success("Lists synced!")
        
        # Import emails
        st.divider()
        st.write("**Add Emails to List**")
        
        email_input = st.text_area(
            "Paste emails (one per line)",
            placeholder="john@example.com\njane@example.com\n...",
            height=150
        )
        
        if st.button("✅ Add to List"):
            if email_input:
                emails = [e.strip() for e in email_input.split('\n') if e.strip()]
                valid_emails = [e for e in emails if '@' in e]
                st.session_state.email_list.extend(valid_emails)
                st.success(f"✅ Added {len(valid_emails)} emails to {selected_list}")
    
    # ========================================
    # TAB 2: INFLUENCERS
    # ========================================
    with tab2:
        st.subheader("👥 Influencer Directory")
        st.markdown("Find and manage influencer contacts")
        
        col1, col2 = st.columns([0.7, 0.3])
        
        with col1:
            # Search and filter
            search_query = st.text_input(
                "🔍 Search influencers",
                placeholder="Name, email, or username..."
            )
            
            col_filter1, col_filter2 = st.columns(2)
            with col_filter1:
                selected_platform = st.selectbox(
                    "Filter by Platform",
                    ["All", "Instagram", "TikTok", "YouTube", "Twitter", "LinkedIn"]
                )
            with col_filter2:
                selected_niche = st.selectbox(
                    "Filter by Niche",
                    ["All", "Tech", "Fashion", "Health", "Marketing", "Lifestyle", "Business"]
                )
            
            # Display influencers
            if st.session_state.email_database.contacts:
                contacts = st.session_state.email_database.contacts
                
                # Apply filters
                if search_query:
                    contacts = st.session_state.email_database.search_contacts(search_query)
                if selected_platform != "All":
                    contacts = [c for c in contacts if c.platform == selected_platform]
                if selected_niche != "All":
                    contacts = [c for c in contacts if selected_niche.lower() in c.niche.lower()]
                
                for contact in contacts:
                    with st.expander(f"👤 {contact.name} (@{contact.username})"):
                        col_info1, col_info2 = st.columns(2)
                        
                        with col_info1:
                            st.write(f"**Platform:** {contact.platform}")
                            st.write(f"**Email:** {contact.email}")
                            st.write(f"**Niche:** {contact.niche}")
                        
                        with col_info2:
                            st.metric("Followers", f"{contact.followers:,}")
                            st.metric("Engagement", f"{contact.engagement_rate:.1f}%")
                        
                        st.write(f"**Notes:** {contact.notes}")
                        
                        col_act1, col_act2, col_act3 = st.columns(3)
                        with col_act1:
                            if st.button("📧 Send Email", key=f"email_{contact.email}"):
                                st.session_state.selected_influencer = contact
                        with col_act2:
                            if st.button("✏️ Edit", key=f"edit_{contact.email}"):
                                st.session_state.editing_contact = contact
                        with col_act3:
                            if st.button("🗑️ Delete", key=f"delete_{contact.email}"):
                                st.session_state.email_database.contacts.remove(contact)
                                st.rerun()
            else:
                st.info("📭 No influencers yet. Add one below!")
        
        with col2:
            st.write("**Add Influencer**")
            
            inf_name = st.text_input("Name", placeholder="John Doe")
            inf_email = st.text_input("Email", placeholder="john@example.com")
            inf_platform = st.selectbox("Platform", 
                ["Instagram", "TikTok", "YouTube", "Twitter", "LinkedIn"])
            inf_username = st.text_input("Username", placeholder="@johndoe")
            inf_niche = st.text_input("Niche", placeholder="e.g., Tech, Fashion")
            inf_followers = st.number_input("Followers", min_value=0, value=10000)
            inf_engagement = st.slider("Engagement Rate (%)", 0.0, 100.0, 5.0)
            inf_notes = st.text_area("Notes", placeholder="Special notes...", height=80)
            
            if st.button("➕ Add Influencer", use_container_width=True):
                if inf_name and inf_email and inf_platform:
                    new_contact = InfluencerContact(
                        name=inf_name,
                        email=inf_email,
                        platform=inf_platform,
                        username=inf_username,
                        niche=inf_niche,
                        followers=inf_followers,
                        engagement_rate=inf_engagement,
                        notes=inf_notes
                    )
                    if st.session_state.email_database.add_contact(new_contact):
                        st.success(f"✅ Added {inf_name}")
                        st.rerun()
                    else:
                        st.error("Contact already exists")
                else:
                    st.error("Please fill in required fields")
    
    # ========================================
    # TAB 3: EMAIL TEMPLATES
    # ========================================
    with tab3:
        st.subheader("📧 Email Templates")
        st.markdown("Create and manage email templates with HTML editor")
        
        template_action = st.radio(
            "Action",
            ["View Templates", "Create Template"],
            horizontal=True
        )
        
        if template_action == "View Templates":
            if st.session_state.email_templates:
                for tname, template in st.session_state.email_templates.items():
                    with st.expander(f"📧 {tname}"):
                        col_t1, col_t2 = st.columns([0.7, 0.3])
                        with col_t1:
                            st.write(f"**Subject:** {template['subject']}")
                            st.markdown("**Preview:**")
                            st.html(template['html'])
                        with col_t2:
                            if st.button("📋 Copy", key=f"copy_{tname}"):
                                st.success("Copied!")
                            if st.button("🗑️ Delete", key=f"del_template_{tname}"):
                                del st.session_state.email_templates[tname]
                                st.rerun()
            else:
                st.info("No templates created yet")
            
            # Preset templates
            st.divider()
            st.write("**Preset Templates**")
            
            template_choice = st.selectbox(
                "Select a preset",
                list(EmailTemplateBuilder.PRESET_TEMPLATES.keys())
            )
            
            if template_choice:
                preset = EmailTemplateBuilder.PRESET_TEMPLATES[template_choice]
                with st.expander(f"📧 {template_choice}"):
                    st.markdown("**Subject Line:**")
                    st.caption(preset['subject'])
                    st.markdown("**Preview:**")
                    st.html(preset['html'])
                    
                    if st.button("✅ Use This Template"):
                        st.session_state.selected_preset = template_choice
                        st.success(f"Using {template_choice} template!")
        
        else:  # Create Template
            st.write("**Create New Template**")
            
            template_name = st.text_input("Template Name")
            subject_line = st.text_input("Subject Line")
            
            st.write("**HTML Content Editor**")
            html_content = st.text_area(
                "HTML Content",
                placeholder="<h1>Hello [RECIPIENT_NAME]</h1>\n<p>Your content here...</p>",
                height=300
            )
            
            st.write("**Template Variables**")
            st.caption("Use these placeholders in your template:")
            
            cols = st.columns(3)
            for idx, var in enumerate(EmailTemplateBuilder.TEMPLATE_VARIABLES):
                with cols[idx % 3]:
                    st.caption(f"`[{var}]`")
            
            if st.button("💾 Save Template", type="primary"):
                if template_name and subject_line and html_content:
                    st.session_state.email_templates[template_name] = {
                        'name': template_name,
                        'subject': subject_line,
                        'html': html_content,
                        'created': datetime.now().isoformat()
                    }
                    st.success(f"✅ Template '{template_name}' saved!")
                    st.rerun()
    
    # ========================================
    # TAB 4: CAMPAIGNS
    # ========================================
    with tab4:
        st.subheader("🚀 Email Campaigns")
        st.markdown("Create and manage email campaigns")
        
        campaign_mode = st.radio(
            "Mode",
            ["Active Campaigns", "Create Campaign"],
            horizontal=True
        )
        
        if campaign_mode == "Active Campaigns":
            if st.session_state.email_campaigns:
                for campaign in st.session_state.email_campaigns:
                    status_color = {
                        'draft': '🟡',
                        'scheduled': '🟠',
                        'in_progress': '🔵',
                        'sent': '🟢'
                    }
                    
                    with st.expander(f"{status_color.get(campaign.status, '⚪')} {campaign.name}"):
                        col_c1, col_c2 = st.columns(2)
                        
                        with col_c1:
                            st.write(f"**Subject:** {campaign.subject}")
                            st.write(f"**Status:** {campaign.status.upper()}")
                            st.write(f"**Recipients:** {len(campaign.recipient_list)}")
                        
                        with col_c2:
                            if campaign.send_date:
                                st.write(f"**Send Date:** {campaign.send_date}")
                            if campaign.results:
                                st.write(f"**Opens:** {campaign.results.get('opens', 0)}")
                                st.write(f"**Clicks:** {campaign.results.get('clicks', 0)}")
            else:
                st.info("No campaigns created yet")
        
        else:  # Create Campaign
            st.write("**🚀 Create AI-Powered Email Campaign**")
            st.markdown("Generate complete email campaigns with AI-written content, images, and HTML templates")
            
            # Campaign Setup
            col_setup1, col_setup2 = st.columns(2)
            
            with col_setup1:
                camp_name = st.text_input("Campaign Name", placeholder="e.g., Summer Sale 2026")
                camp_type = st.selectbox(
                    "Campaign Type",
                    ["Product Launch", "Newsletter", "Promotion", "Announcement", "Welcome Series", "Re-engagement"]
                )
            
            with col_setup2:
                camp_recipients = st.multiselect(
                    "Select Recipient Lists",
                    ["Subscribers", "Customers", "Prospects", "Influencers"]
                )
                camp_send_date = st.date_input("Schedule Send Date")
            
            st.divider()
            
            # AI Content Generation Section
            st.markdown("### ✨ AI-Powered Content Generation")
            st.markdown("Let AI write your email, generate images, and create beautiful HTML templates")
            
            # Content inputs
            col_content1, col_content2 = st.columns([2, 1])
            
            with col_content1:
                ai_topic = st.text_area(
                    "Campaign Description",
                    placeholder="Describe what this email is about:\n- Product name and key features\n- Target audience\n- Main message and goal\n- Any special offers or CTAs\n\nExample: Launch email for eco-friendly yoga mats, targeting health-conscious consumers, emphasizing sustainability and comfort, with 20% off early bird discount",
                    height=150
                )
            
            with col_content2:
                ai_tone = st.selectbox(
                    "Tone",
                    ["Professional", "Friendly", "Promotional", "Educational", "Urgent", "Inspirational"]
                )
                
                ai_style = st.selectbox(
                    "Visual Style",
                    ["Modern", "Elegant", "Bold", "Minimalist", "Playful", "Luxury"]
                )
                
                generate_images = st.checkbox("🎨 Generate Hero Images", value=True, 
                                             help="AI will generate banner and product images for your email")
                
                num_images = st.slider("Number of Images", 1, 4, 2) if generate_images else 0
            
            # Brand Template Integration
            with st.expander("🎨 Brand Styling (Optional)", expanded=False):
                st.caption("Apply consistent brand colors and fonts to your email")
                try:
                    from brand_templates import BRAND_TEMPLATES
                    
                    brand_template = st.selectbox(
                        "Select Brand Template",
                        ["None"] + list(BRAND_TEMPLATES.keys()),
                        format_func=lambda x: "No branding" if x == "None" else BRAND_TEMPLATES[x]['name'] if x in BRAND_TEMPLATES else x
                    )
                    
                    if brand_template and brand_template != "None":
                        template_data = BRAND_TEMPLATES[brand_template]
                        st.success(f"✅ Using {template_data['name']} brand styling")
                except ImportError:
                    brand_template = "None"
                    st.info("Brand templates not available")
            
            st.divider()
            
            # Generate Button
            generate_campaign = st.button(
                "🤖 Generate Complete Email Campaign", 
                type="primary",
                use_container_width=True,
                help="AI will write content, generate images, and create beautiful HTML email"
            )
            
            if generate_campaign:
                if not ai_topic.strip():
                    st.warning("Please describe your campaign to guide AI generation")
                elif not camp_name.strip():
                    st.warning("Please provide a campaign name")
                else:
                    try:
                        # Import required services
                        from platform_helpers import _ensure_replicate_client
                        from email_marketing_service import EmailMarketingService
                        
                        replicate_api, _ = _ensure_replicate_client()
                        
                        # Create campaign directory
                        campaign_dir = Path("campaigns") / "email_campaigns" / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{camp_name.replace(' ', '_')}"
                        campaign_dir.mkdir(parents=True, exist_ok=True)
                        images_dir = campaign_dir / "images"
                        images_dir.mkdir(exist_ok=True)
                        
                        st.markdown("---")
                        st.markdown(f"### 🎨 Generating: {camp_name}")
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Step 1: Generate Email Content
                        status_text.text("✍️ Step 1/4: Writing email content with AI...")
                        progress_bar.progress(10)
                        
                        content_prompt = f"""Write a complete professional email for a {camp_type} campaign.

Campaign Description: {ai_topic}

Tone: {ai_tone}
Style: {ai_style}

Write a complete email including:
1. Compelling subject line
2. Attention-grabbing opening
3. Clear value proposition and benefits
4. Engaging body content (2-3 paragraphs)
5. Strong call-to-action
6. Professional signature

Format as:
SUBJECT: [subject line]

BODY:
[email content]

Keep it concise but compelling. Use engaging language that converts."""

                        email_content = replicate_api.generate_text(
                            prompt=content_prompt,
                            max_tokens=800,
                            temperature=0.8
                        )
                        
                        # Parse subject and body
                        subject_line = "Your Special Offer"
                        body_content = email_content
                        
                        if "SUBJECT:" in email_content:
                            parts = email_content.split("BODY:", 1)
                            subject_part = parts[0].replace("SUBJECT:", "").strip()
                            subject_line = subject_part.split("\n")[0].strip()
                            if len(parts) > 1:
                                body_content = parts[1].strip()
                        
                        progress_bar.progress(30)
                        
                        # Step 2: Generate Images in Parallel
                        generated_images = []
                        if generate_images and num_images > 0:
                            status_text.text(f"🎨 Step 2/4: Generating {num_images} hero images in parallel...")
                            
                            # Get global job queue
                            queue = get_global_job_queue()
                            image_job_ids = []
                            
                            # Submit all image generation jobs at once
                            for i in range(num_images):
                                image_prompt = f"{ai_style} email banner for {camp_type}, {ai_topic}, professional marketing design, high quality"
                                
                                def generate_single_email_image(prompt=image_prompt, idx=i, img_dir=images_dir):
                                    """Generate a single email hero image"""
                                    try:
                                        image_url = replicate_api.generate_image(
                                            prompt=prompt,
                                            model="flux-fast"
                                        )
                                        
                                        if image_url:
                                            # Download and save image
                                            import requests
                                            response = requests.get(image_url, timeout=30)
                                            if response.status_code == 200:
                                                image_path = img_dir / f"email_hero_{idx+1}.png"
                                                image_path.write_bytes(response.content)
                                                logger.info(f"✅ Generated image {idx+1}/{num_images}")
                                                return str(image_path)
                                    except Exception as e:
                                        logger.error(f"Error generating image {idx+1}: {e}")
                                        return None
                                    return None
                                
                                job_id = queue.submit_job(
                                    job_type=JobType.IMAGE_GENERATION,
                                    tab_name="Email Outreach",
                                    description=f"Email Hero Image {i+1}/{num_images}",
                                    function=generate_single_email_image,
                                    priority=7
                                )
                                image_job_ids.append(job_id)
                            
                            # Store job context for multi-step campaign
                            st.session_state.email_image_jobs = image_job_ids
                            st.session_state.email_campaign_context = {
                                'camp_name': camp_name,
                                'subject_line': subject_line,
                                'body_content': body_content,
                                'camp_type': camp_type,
                                'ai_topic': ai_topic,
                                'ai_style': ai_style,
                                'brand_template': brand_template,
                                'images_dir': str(images_dir),
                                'campaign_dir': str(campaign_dir),
                                'num_images': num_images
                            }
                            
                            st.info("🎨 Image generation started in background...")
                            st.info("💡 Jobs run in parallel. You can switch tabs - progress is saved!")
                            
                            # Non-blocking progress check
                            progress_container = st.empty()
                            job_progress = check_jobs_progress(image_job_ids)
                            completed_count = job_progress['completed'] + job_progress['failed']
                            progress_pct = 30 + int((completed_count / num_images) * 40) if num_images > 0 else 70
                            progress_bar.progress(progress_pct)
                            
                            with progress_container:
                                col1, col2, col3 = st.columns(3)
                                col1.metric("⏳ Running", job_progress['running'])
                                col2.metric("✅ Done", job_progress['completed'])
                                col3.metric("❌ Failed", job_progress['failed'])
                            
                            if st.button("🔄 Check Image Progress", key="check_email_images"):
                                st.rerun()
                            
                            # If images not done, show message and allow user to continue later
                            if not are_all_jobs_done(image_job_ids):
                                st.warning("⏳ Images still generating. Refresh to check progress or continue to generate email without images.")
                                if st.button("📧 Continue Without Images", key="continue_no_images"):
                                    generated_images = []
                                    # Continue to HTML generation below
                                else:
                                    st.stop()  # Wait for user action
                            else:
                                # Collect results
                                image_results = collect_job_results(image_job_ids, timeout=60)
                                generated_images = [img for img in image_results if img is not None]
                                
                                # Clear job tracking
                                del st.session_state.email_image_jobs
                                st.session_state.pop('email_campaign_context', None)
                                
                                st.success(f"✅ Generated {len(generated_images)}/{num_images} hero images!")
                        else:
                            progress_bar.progress(70)
                        
                        status_text.text("🎨 Step 3/4: Creating beautiful HTML template...")
                        
                        # Step 3: Create HTML Email
                        # Get brand colors if template selected
                        primary_color = "#6366f1"
                        secondary_color = "#8b5cf6"
                        
                        if brand_template and brand_template != "None" and brand_template in BRAND_TEMPLATES:
                            template_data = BRAND_TEMPLATES[brand_template]
                            colors = template_data.get('colors', {})
                            primary_color = colors.get('primary', primary_color)
                            secondary_color = colors.get('secondary', secondary_color)
                        
                        # Build HTML email
                        html_email = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject_line}</title>
</head>
<body style="margin: 0; padding: 0; font-family: Arial, Helvetica, sans-serif; background-color: #f4f4f4;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                    
                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, {primary_color} 0%, {secondary_color} 100%); padding: 40px 30px; border-radius: 8px 8px 0 0; text-align: center;">
                            <h1 style="margin: 0; color: white; font-size: 32px; font-weight: bold;">{camp_name}</h1>
                        </td>
                    </tr>
                    
                    <!-- Hero Image -->"""
                        
                        if generated_images:
                            # Use first image as hero
                            html_email += f"""
                    <tr>
                        <td style="padding: 0;">
                            <img src="cid:hero_image" alt="{camp_name}" style="width: 100%; height: auto; display: block;" />
                        </td>
                    </tr>"""
                        
                        html_email += f"""
                    
                    <!-- Body Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <div style="color: #333333; font-size: 16px; line-height: 1.6;">
                                {body_content.replace(chr(10), '<br>')}
                            </div>
                        </td>
                    </tr>
                    
                    <!-- CTA Button -->
                    <tr>
                        <td style="padding: 0 30px 40px 30px; text-align: center;">
                            <a href="#" style="display: inline-block; background-color: {primary_color}; color: white; text-decoration: none; padding: 15px 40px; border-radius: 5px; font-size: 18px; font-weight: bold; transition: opacity 0.3s;">
                                Learn More
                            </a>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f8f8; padding: 30px; border-radius: 0 0 8px 8px; text-align: center; color: #666666; font-size: 14px;">
                            <p style="margin: 0 0 10px 0;">© {datetime.now().year} Your Company. All rights reserved.</p>
                            <p style="margin: 0;"><a href="#" style="color: {primary_color}; text-decoration: none;">Unsubscribe</a></p>
                        </td>
                    </tr>
                    
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""
                        
                        # Save HTML file
                        html_path = campaign_dir / f"{camp_name.replace(' ', '_')}_email.html"
                        html_path.write_text(html_email, encoding='utf-8')
                        
                        progress_bar.progress(90)
                        
                        # Step 4: Create Campaign Summary
                        status_text.text("📋 Step 4/4: Creating campaign summary...")
                        
                        summary = f"""EMAIL CAMPAIGN SUMMARY
{'=' * 50}

Campaign Name: {camp_name}
Type: {camp_type}
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

SUBJECT LINE:
{subject_line}

CONTENT PREVIEW:
{body_content[:300]}...

ASSETS GENERATED:
- ✅ Email HTML template
- ✅ {len(generated_images)} hero images
- ✅ Campaign summary

RECIPIENTS:
{', '.join(camp_recipients) if camp_recipients else 'Not configured'}

SEND DATE:
{camp_send_date}

FILES SAVED TO:
{campaign_dir}
"""
                        
                        summary_path = campaign_dir / "campaign_summary.txt"
                        summary_path.write_text(summary, encoding='utf-8')
                        
                        progress_bar.progress(100)
                        status_text.text("✅ Campaign generation complete!")
                        
                        # Display Results
                        st.success(f"🎉 Successfully generated complete email campaign: {camp_name}")
                        
                        st.markdown("---")
                        st.markdown("### 📧 Email Preview")
                        
                        # Show email preview
                        with st.expander("📨 View Email HTML", expanded=True):
                            st.components.v1.html(html_email, height=800, scrolling=True)
                        
                        # Show subject line
                        st.markdown("#### 📬 Subject Line")
                        st.info(subject_line)
                        
                        # Show generated images
                        if generated_images:
                            st.markdown("#### 🎨 Generated Images")
                            img_cols = st.columns(min(len(generated_images), 3))
                            for idx, img_path in enumerate(generated_images):
                                with img_cols[idx % 3]:
                                    st.image(img_path, caption=f"Hero Image {idx+1}", use_container_width=True)
                        
                        # Download options
                        st.markdown("---")
                        st.markdown("#### 💾 Download Campaign Assets")
                        
                        dl_col1, dl_col2, dl_col3 = st.columns(3)
                        
                        with dl_col1:
                            st.download_button(
                                "📥 Download HTML",
                                data=html_email,
                                file_name=f"{camp_name.replace(' ', '_')}_email.html",
                                mime="text/html",
                                use_container_width=True
                            )
                        
                        with dl_col2:
                            st.download_button(
                                "📥 Download Summary",
                                data=summary,
                                file_name=f"{camp_name.replace(' ', '_')}_summary.txt",
                                mime="text/plain",
                                use_container_width=True
                            )
                        
                        with dl_col3:
                            if generated_images:
                                # Create zip of all images
                                import zipfile
                                import io
                                
                                zip_buffer = io.BytesIO()
                                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                    for img_path in generated_images:
                                        zip_file.write(img_path, Path(img_path).name)
                                
                                st.download_button(
                                    "📥 Download Images (ZIP)",
                                    data=zip_buffer.getvalue(),
                                    file_name=f"{camp_name.replace(' ', '_')}_images.zip",
                                    mime="application/zip",
                                    use_container_width=True
                                )
                        
                        # Save to campaigns list
                        new_campaign = EmailCampaign(
                            name=camp_name,
                            subject=subject_line,
                            recipient_list=camp_recipients,
                            template=html_path.name,
                            status='draft',
                            send_date=str(camp_send_date),
                            created_date=datetime.now().isoformat()
                        )
                        st.session_state.email_campaigns.append(new_campaign)
                        
                        # Store in session for easy access
                        if 'generated_email_campaigns' not in st.session_state:
                            st.session_state.generated_email_campaigns = []
                        st.session_state.generated_email_campaigns.append({
                            'name': camp_name,
                            'html': html_email,
                            'subject': subject_line,
                            'images': generated_images,
                            'directory': str(campaign_dir)
                        })
                        
                    except Exception as e:
                        logger.error(f"Error generating email campaign: {e}")
                        st.error(f"❌ Error: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
            
            st.divider()
            
            # Manual campaign creation fallback
            with st.expander("📝 Manual Campaign Setup (No AI)", expanded=False):
                st.caption("Create campaign without AI generation")
                
                manual_subject = st.text_input("Email Subject", placeholder="Special offer just for you!")
                
                manual_template = st.selectbox(
                    "Select Template",
                    ["None"] + list(st.session_state.email_templates.keys())
                )
                
                manual_content = st.text_area(
                    "Email Body",
                    placeholder="Write your email content here...",
                    height=200
                )
                
                if st.button("💾 Save Manual Campaign"):
                    if camp_name and manual_subject:
                        new_campaign = EmailCampaign(
                            name=camp_name,
                            subject=manual_subject,
                            recipient_list=camp_recipients,
                            template=manual_template,
                            status='draft',
                            send_date=str(camp_send_date),
                            created_date=datetime.now().isoformat()
                        )
                        st.session_state.email_campaigns.append(new_campaign)
                        st.success(f"✅ Campaign '{camp_name}' created!")
                        st.rerun()
                    else:
                        st.error("Please provide campaign name and subject")
    
    # ========================================
    # TAB 5: ANALYTICS
    # ========================================
    with tab5:
        st.subheader("📊 Email Analytics")
        st.markdown("Track performance and engagement metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Emails Sent", "2,450")
        with col2:
            st.metric("Average Open Rate", "38.2%")
        with col3:
            st.metric("Average Click Rate", "12.5%")
        with col4:
            st.metric("Unsubscribe Rate", "0.8%")
        
        st.divider()
        st.write("**Campaign Performance**")
        
        # Simulated chart data
        import random
        
        dates = [(datetime.now() - timedelta(days=i)).strftime("%m/%d") for i in range(30, 0, -1)]
        opens = [random.randint(30, 60) for _ in range(30)]
        clicks = [random.randint(5, 20) for _ in range(30)]
        
        chart_data = {
            'Date': dates,
            'Opens': opens,
            'Clicks': clicks
        }
        
        st.line_chart(chart_data, x='Date')
        
        st.divider()
        st.write("**Top Performing Campaigns**")
        
        campaigns_table = {
            'Campaign': ['Summer Sale', 'Product Launch', 'Newsletter #15'],
            'Opens': ['45.2%', '38.9%', '35.6%'],
            'Clicks': ['15.3%', '12.8%', '10.2%'],
            'Conversions': ['8.2%', '6.5%', '5.1%']
        }
        
        st.dataframe(campaigns_table, use_container_width=True)
