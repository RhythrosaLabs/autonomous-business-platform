"""
Browser Automation Templates
============================
Pre-built templates for common browser automation tasks.
"""

import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

# Pre-built automation templates
AUTOMATION_TEMPLATES = {
    # ===== SOCIAL MEDIA POSTING =====
    "post_twitter": {
        "id": "post_twitter",
        "name": "Post to Twitter/X",
        "description": "Automatically post content to Twitter/X",
        "category": "Social Media",
        "platform": "twitter",
        "requires_credentials": True,
        "steps": [
            "Navigate to twitter.com",
            "Log in if not already logged in",
            "Click on the compose tweet button",
            "Type the tweet content: {{content}}",
            "Attach image if provided: {{image_url}}",
            "Click the Tweet button to post"
        ],
        "task_template": """
Go to twitter.com and post a tweet with the following content:

{{content}}

{{#if image_url}}
Also attach this image: {{image_url}}
{{/if}}

Make sure to:
1. Log in if needed (credentials should be auto-filled)
2. Wait for the page to fully load
3. Confirm the tweet was posted successfully
"""
    },
    "post_instagram": {
        "id": "post_instagram",
        "name": "Post to Instagram",
        "description": "Post image content to Instagram",
        "category": "Social Media",
        "platform": "instagram",
        "requires_credentials": True,
        "steps": [
            "Navigate to instagram.com",
            "Log in if not already logged in",
            "Click the create post button (+)",
            "Upload the image: {{image_path}}",
            "Add caption: {{caption}}",
            "Click Share to post"
        ],
        "task_template": """
Go to instagram.com and create a new post:

Image: {{image_path}}
Caption: {{caption}}
{{#if hashtags}}
Hashtags: {{hashtags}}
{{/if}}

Complete the posting process and confirm success.
"""
    },
    "post_linkedin": {
        "id": "post_linkedin",
        "name": "Post to LinkedIn",
        "description": "Share content on LinkedIn",
        "category": "Social Media",
        "platform": "linkedin",
        "requires_credentials": True,
        "task_template": """
Go to linkedin.com and create a new post with:

Content: {{content}}
{{#if image_url}}
Image: {{image_url}}
{{/if}}

Make sure the post is published to your feed.
"""
    },
    "post_facebook": {
        "id": "post_facebook",
        "name": "Post to Facebook",
        "description": "Share content on Facebook",
        "category": "Social Media",
        "platform": "facebook",
        "requires_credentials": True,
        "task_template": """
Go to facebook.com and create a new post:

Content: {{content}}
{{#if image_url}}
Attach image: {{image_url}}
{{/if}}

Post to your timeline and confirm success.
"""
    },
    
    # ===== RESEARCH TEMPLATES =====
    "research_competitor": {
        "id": "research_competitor",
        "name": "Competitor Research",
        "description": "Research a competitor's website and products",
        "category": "Research",
        "platform": "web",
        "requires_credentials": False,
        "task_template": """
Research the competitor website: {{url}}

Gather the following information:
1. Main products or services offered
2. Pricing information if visible
3. Unique selling propositions
4. Social media presence links
5. Recent blog posts or announcements
6. Contact information

Compile a summary of findings.
"""
    },
    "research_trends": {
        "id": "research_trends",
        "name": "Trend Research",
        "description": "Research current trends in a specific niche",
        "category": "Research",
        "platform": "web",
        "requires_credentials": False,
        "task_template": """
Research current trends for: {{topic}}

Search Google, social media, and trend sites to find:
1. Top 5 current trends in this niche
2. Popular products or content types
3. Emerging opportunities
4. Audience preferences
5. Successful examples

Provide a summary with actionable insights.
"""
    },
    "research_product_prices": {
        "id": "research_product_prices",
        "name": "Product Price Research",
        "description": "Research pricing for similar products",
        "category": "Research",
        "platform": "web",
        "requires_credentials": False,
        "task_template": """
Research pricing for products similar to: {{product_type}}

Check these marketplaces:
- Amazon
- Etsy
- eBay

Find:
1. Average price range
2. Lowest and highest prices
3. Common pricing strategies
4. Bundle or discount patterns

Summarize findings with pricing recommendations.
"""
    },
    
    # ===== E-COMMERCE TEMPLATES =====
    "check_etsy_listings": {
        "id": "check_etsy_listings",
        "name": "Check Etsy Listings",
        "description": "Review your Etsy shop listings",
        "category": "E-Commerce",
        "platform": "etsy",
        "requires_credentials": True,
        "task_template": """
Go to etsy.com and navigate to my shop dashboard.

Check:
1. Active listings count
2. Any listings that need attention
3. Recent orders
4. Shop stats overview
5. Any messages or notifications

Provide a summary of shop status.
"""
    },
    "check_amazon_seller": {
        "id": "check_amazon_seller",
        "name": "Check Amazon Seller Central",
        "description": "Review Amazon seller account status",
        "category": "E-Commerce",
        "platform": "amazon",
        "requires_credentials": True,
        "task_template": """
Go to sellercentral.amazon.com and check:

1. Account health status
2. New orders
3. Inventory levels
4. Performance metrics
5. Any alerts or action required

Summarize the seller account status.
"""
    },
    
    # ===== CONTENT COLLECTION =====
    "scrape_product_images": {
        "id": "scrape_product_images",
        "name": "Collect Product Images",
        "description": "Download product images from a webpage",
        "category": "Content",
        "platform": "web",
        "requires_credentials": False,
        "task_template": """
Go to: {{url}}

Find and collect all product images on the page.
Save them in a structured format with:
1. Image URLs
2. Product names if visible
3. Image dimensions

Note: Only collect images that appear to be product photos.
"""
    },
    "collect_testimonials": {
        "id": "collect_testimonials",
        "name": "Collect Testimonials",
        "description": "Gather customer testimonials from reviews",
        "category": "Content",
        "platform": "web",
        "requires_credentials": False,
        "task_template": """
Go to: {{url}}

Find and collect customer reviews/testimonials.
For each review, capture:
1. Customer name (or initial)
2. Rating if available
3. Review text
4. Date if shown

Compile into a formatted list.
"""
    },
    
    # ===== MONITORING TEMPLATES =====
    "monitor_brand_mentions": {
        "id": "monitor_brand_mentions",
        "name": "Monitor Brand Mentions",
        "description": "Check social media for brand mentions",
        "category": "Monitoring",
        "platform": "web",
        "requires_credentials": False,
        "task_template": """
Search for mentions of: {{brand_name}}

Check these platforms:
1. Twitter search
2. Reddit search
3. Google News

Find:
- Recent mentions (last 7 days)
- Sentiment (positive/negative/neutral)
- Any issues that need attention
- Opportunities for engagement

Summarize findings with any action items.
"""
    },
    "check_seo_rankings": {
        "id": "check_seo_rankings",
        "name": "Check SEO Rankings",
        "description": "Check search rankings for keywords",
        "category": "Monitoring",
        "platform": "web",
        "requires_credentials": False,
        "task_template": """
Search Google for these keywords and note where {{website}} appears:

Keywords:
{{keywords}}

For each keyword, record:
1. Position in search results (1-100 or not found)
2. Snippet preview if shown
3. Top 3 competitors for that keyword

Compile into a rankings report.
"""
    },
    
    # ===== FORM FILLING =====
    "fill_contact_form": {
        "id": "fill_contact_form",
        "name": "Fill Contact Form",
        "description": "Complete a contact form on a website",
        "category": "Outreach",
        "platform": "web",
        "requires_credentials": False,
        "task_template": """
Go to: {{url}}

Find the contact form and fill it with:
- Name: {{name}}
- Email: {{email}}
- Subject: {{subject}}
- Message: {{message}}

Submit the form and confirm submission.
"""
    },
    "submit_guest_post": {
        "id": "submit_guest_post",
        "name": "Submit Guest Post",
        "description": "Submit guest post pitch to a blog",
        "category": "Outreach",
        "platform": "web",
        "requires_credentials": False,
        "task_template": """
Go to: {{blog_url}}

Find their guest post submission page or contact form.
Submit a pitch with:
- Your name: {{name}}
- Email: {{email}}
- Proposed topic: {{topic}}
- Brief outline: {{outline}}

Complete the submission process.
"""
    }
}


class AutomationTemplateManager:
    """Manage browser automation templates."""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".pod_wizard" / "automation_templates"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.templates = {**AUTOMATION_TEMPLATES}
        self._load_custom_templates()
    
    def _load_custom_templates(self):
        """Load custom templates from storage."""
        for file in self.storage_dir.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    self.templates[data['id']] = data
            except Exception as e:
                logger.warning(f"Failed to load automation template {file}: {e}")
    
    def get_template(self, template_id: str) -> Optional[Dict]:
        return self.templates.get(template_id)
    
    def list_templates(self, category: Optional[str] = None) -> List[Dict]:
        templates = list(self.templates.values())
        if category:
            templates = [t for t in templates if t.get('category') == category]
        return sorted(templates, key=lambda t: t.get('name', ''))
    
    def get_categories(self) -> List[str]:
        return sorted(set(t.get('category', 'Other') for t in self.templates.values()))
    
    def build_task(self, template_id: str, variables: Dict) -> str:
        """Build a task string from a template with variables filled in."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        task = template.get('task_template', '')
        
        # Simple variable substitution
        for key, value in variables.items():
            task = task.replace(f"{{{{{key}}}}}", str(value))
        
        # Handle conditionals (simple version)
        import re
        # Remove unfilled conditionals
        task = re.sub(r'\{\{#if \w+\}\}.*?\{\{/if\}\}', '', task, flags=re.DOTALL)
        
        return task.strip()
    
    def save_template(self, template: Dict):
        """Save a custom template."""
        template_id = template.get('id', str(uuid.uuid4()))
        template['id'] = template_id
        template['modified_at'] = datetime.now().isoformat()
        template['custom'] = True
        
        self.templates[template_id] = template
        
        file_path = self.storage_dir / f"{template_id}.json"
        with open(file_path, 'w') as f:
            json.dump(template, f, indent=2)


def render_automation_templates():
    """Render automation templates UI in Streamlit."""
    import streamlit as st
    
    st.markdown("### 🤖 Browser Automation Templates")
    st.caption("Pre-built templates for automating web tasks")
    
    manager = AutomationTemplateManager()
    
    # Category filter
    categories = manager.get_categories()
    selected_category = st.selectbox("Filter by Category", ["All"] + categories, key="auto_template_cat")
    
    templates = manager.list_templates(
        category=None if selected_category == "All" else selected_category
    )
    
    for template in templates:
        with st.expander(f"**{template['name']}** ({template.get('platform', 'web')})"):
            st.markdown(template.get('description', ''))
            
            if template.get('requires_credentials'):
                st.warning("⚠️ This template requires login credentials")
            
            if template.get('steps'):
                st.markdown("**Steps:**")
                for i, step in enumerate(template['steps'][:5]):
                    st.text(f"  {i+1}. {step}")
            
            # Variable inputs
            task_template = template.get('task_template', '')
            import re
            variables = re.findall(r'\{\{(\w+)\}\}', task_template)
            variables = list(set(variables))  # Remove duplicates
            
            if variables:
                st.markdown("**Configure:**")
                var_values = {}
                for var in variables:
                    if var not in ['#if', '/if']:
                        var_values[var] = st.text_input(
                            var.replace('_', ' ').title(),
                            key=f"var_{template['id']}_{var}"
                        )
                
                if st.button("Run Automation", key=f"run_{template['id']}", use_container_width=True):
                    if all(var_values.values()):
                        task = manager.build_task(template['id'], var_values)
                        st.session_state['pending_automation_task'] = task
                        st.success("✅ Task prepared! Go to Otto Mate to execute.")
                        st.code(task)
                    else:
                        st.warning("Please fill in all fields")
