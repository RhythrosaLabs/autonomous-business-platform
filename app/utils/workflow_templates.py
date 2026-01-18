"""
Workflow Templates
==================
Pre-built workflow templates for common marketing tasks.
"""

import json
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

# Pre-built workflow templates
WORKFLOW_TEMPLATES = {
    # ===== PRODUCT LAUNCH WORKFLOWS =====
    "product_launch_basic": {
        "id": "product_launch_basic",
        "name": "Basic Product Launch",
        "description": "Generate design, create product, and publish to store",
        "category": "Product Launch",
        "difficulty": "Beginner",
        "estimated_time": "5-10 minutes",
        "steps": [
            {"type": "trigger", "node": "manual", "config": {}},
            {"type": "image_generation", "node": "flux_fast", "config": {"prompt_template": "{{user_prompt}}"}},
            {"type": "processing", "node": "bg_remove", "config": {}},
            {"type": "integration", "node": "printify", "config": {"action": "create_product"}},
            {"type": "integration", "node": "printify", "config": {"action": "publish"}}
        ]
    },
    "product_launch_full": {
        "id": "product_launch_full",
        "name": "Full Product Campaign",
        "description": "Design, mockups, video, social posts, and publishing",
        "category": "Product Launch",
        "difficulty": "Advanced",
        "estimated_time": "15-30 minutes",
        "steps": [
            {"type": "trigger", "node": "manual", "config": {}},
            {"type": "image_generation", "node": "flux_pro", "config": {"prompt_template": "{{user_prompt}}, professional product design"}},
            {"type": "processing", "node": "bg_remove", "config": {}},
            {"type": "processing", "node": "upscale", "config": {}},
            {"type": "integration", "node": "printify", "config": {"action": "create_product"}},
            {"type": "video_generation", "node": "kling", "config": {"prompt_template": "product showcase, {{user_prompt}}"}},
            {"type": "text_generation", "node": "llama", "config": {"prompt_template": "Write 3 social media posts for: {{user_prompt}}"}},
            {"type": "integration", "node": "printify", "config": {"action": "publish"}},
            {"type": "output", "node": "file_output", "config": {"save_all": True}}
        ]
    },
    
    # ===== CONTENT CREATION WORKFLOWS =====
    "blog_post_creator": {
        "id": "blog_post_creator",
        "name": "Blog Post Creator",
        "description": "Generate blog post with images and publish to Shopify",
        "category": "Content Creation",
        "difficulty": "Intermediate",
        "estimated_time": "5-10 minutes",
        "steps": [
            {"type": "trigger", "node": "manual", "config": {}},
            {"type": "text_generation", "node": "llama", "config": {"prompt_template": "Write a detailed blog post about: {{topic}}. Include introduction, 3 main sections, and conclusion."}},
            {"type": "image_generation", "node": "flux_fast", "config": {"prompt_template": "blog header image, {{topic}}, professional"}},
            {"type": "integration", "node": "shopify", "config": {"action": "create_blog_post"}}
        ]
    },
    "social_media_batch": {
        "id": "social_media_batch",
        "name": "Social Media Batch",
        "description": "Generate a week's worth of social content",
        "category": "Content Creation",
        "difficulty": "Intermediate",
        "estimated_time": "10-15 minutes",
        "steps": [
            {"type": "trigger", "node": "manual", "config": {}},
            {"type": "loop", "node": "loop", "config": {"iterations": 7}},
            {"type": "text_generation", "node": "llama", "config": {"prompt_template": "Write an engaging social media post about {{brand}} for day {{iteration}}"}},
            {"type": "image_generation", "node": "flux_fast", "config": {"prompt_template": "social media graphic, {{brand}}, day {{iteration}}"}},
            {"type": "output", "node": "file_output", "config": {"folder": "social_batch"}}
        ]
    },
    
    # ===== VIDEO PRODUCTION WORKFLOWS =====
    "product_video": {
        "id": "product_video",
        "name": "Product Promo Video",
        "description": "Create a promotional video for products",
        "category": "Video Production",
        "difficulty": "Advanced",
        "estimated_time": "10-20 minutes",
        "steps": [
            {"type": "trigger", "node": "manual", "config": {}},
            {"type": "text_generation", "node": "llama", "config": {"prompt_template": "Write a 30-second video script for: {{product}}"}},
            {"type": "image_generation", "node": "flux_pro", "config": {"prompt_template": "{{product}}, promotional style, hero shot"}},
            {"type": "video_generation", "node": "kling", "config": {"prompt_template": "product showcase animation"}},
            {"type": "audio", "node": "speech", "config": {"text_from": "previous_text"}},
            {"type": "audio", "node": "musicgen", "config": {"prompt_template": "upbeat commercial background music"}},
            {"type": "output", "node": "file_output", "config": {"format": "mp4"}}
        ]
    },
    "youtube_shorts": {
        "id": "youtube_shorts",
        "name": "YouTube Shorts Generator",
        "description": "Create vertical short-form video content",
        "category": "Video Production",
        "difficulty": "Intermediate",
        "estimated_time": "5-10 minutes",
        "steps": [
            {"type": "trigger", "node": "manual", "config": {}},
            {"type": "text_generation", "node": "llama", "config": {"prompt_template": "Write a hook and 15-second script for: {{topic}}"}},
            {"type": "image_generation", "node": "flux_fast", "config": {"aspect_ratio": "9:16", "prompt_template": "{{topic}}, vertical format, eye-catching"}},
            {"type": "video_generation", "node": "kling", "config": {"aspect_ratio": "9:16"}},
            {"type": "integration", "node": "youtube", "config": {"type": "shorts"}}
        ]
    },
    
    # ===== MARKETING WORKFLOWS =====
    "ad_campaign": {
        "id": "ad_campaign",
        "name": "Ad Campaign Generator",
        "description": "Create multi-platform ad creatives",
        "category": "Marketing",
        "difficulty": "Advanced",
        "estimated_time": "15-25 minutes",
        "steps": [
            {"type": "trigger", "node": "manual", "config": {}},
            {"type": "text_generation", "node": "llama", "config": {"prompt_template": "Write 5 ad headlines and descriptions for: {{product}}"}},
            {"type": "ads_generation", "node": "product_ads", "config": {"platforms": ["instagram", "facebook", "tiktok"]}},
            {"type": "ads_generation", "node": "video_ads", "config": {"duration": 15}},
            {"type": "output", "node": "file_output", "config": {"organize_by_platform": True}}
        ]
    },
    "email_newsletter": {
        "id": "email_newsletter",
        "name": "Email Newsletter",
        "description": "Generate email newsletter content with images",
        "category": "Marketing",
        "difficulty": "Beginner",
        "estimated_time": "5 minutes",
        "steps": [
            {"type": "trigger", "node": "manual", "config": {}},
            {"type": "text_generation", "node": "llama", "config": {"prompt_template": "Write an email newsletter about: {{topic}}. Include subject line, preview text, and body."}},
            {"type": "image_generation", "node": "flux_fast", "config": {"prompt_template": "email header banner, {{topic}}"}},
            {"type": "output", "node": "file_output", "config": {"format": "html"}}
        ]
    },
    
    # ===== RESEARCH WORKFLOWS =====
    "competitor_analysis": {
        "id": "competitor_analysis",
        "name": "Competitor Analysis",
        "description": "Research competitors and generate insights",
        "category": "Research",
        "difficulty": "Intermediate",
        "estimated_time": "10-15 minutes",
        "steps": [
            {"type": "trigger", "node": "manual", "config": {}},
            {"type": "browser", "node": "scrape", "config": {"url_template": "{{competitor_url}}"}},
            {"type": "text_generation", "node": "llama", "config": {"prompt_template": "Analyze this competitor data and provide insights: {{scraped_data}}"}},
            {"type": "output", "node": "file_output", "config": {"format": "md"}}
        ]
    },
    "trend_report": {
        "id": "trend_report",
        "name": "Trend Research Report",
        "description": "Generate market trend analysis",
        "category": "Research",
        "difficulty": "Intermediate",
        "estimated_time": "10 minutes",
        "steps": [
            {"type": "trigger", "node": "manual", "config": {}},
            {"type": "text_generation", "node": "llama", "config": {"prompt_template": "Research and write a trend report for the {{industry}} industry in 2025"}},
            {"type": "image_generation", "node": "flux_fast", "config": {"prompt_template": "infographic style, {{industry}} trends visualization"}},
            {"type": "output", "node": "file_output", "config": {"format": "pdf"}}
        ]
    },
    
    # ===== AUTOMATION WORKFLOWS =====
    "daily_content": {
        "id": "daily_content",
        "name": "Daily Content Automation",
        "description": "Automatically generate daily social content",
        "category": "Automation",
        "difficulty": "Intermediate",
        "estimated_time": "Auto",
        "steps": [
            {"type": "trigger", "node": "schedule", "config": {"cron": "0 9 * * *"}},
            {"type": "text_generation", "node": "llama", "config": {"prompt_template": "Generate today's motivational quote for {{brand}}"}},
            {"type": "image_generation", "node": "flux_fast", "config": {"prompt_template": "quote graphic, inspiring, {{brand_style}}"}},
            {"type": "integration", "node": "twitter", "config": {"action": "post"}},
            {"type": "integration", "node": "instagram", "config": {"action": "post"}}
        ]
    },
    "weekly_report": {
        "id": "weekly_report",
        "name": "Weekly Analytics Report",
        "description": "Generate weekly performance summary",
        "category": "Automation",
        "difficulty": "Advanced",
        "estimated_time": "Auto",
        "steps": [
            {"type": "trigger", "node": "schedule", "config": {"cron": "0 8 * * 1"}},
            {"type": "data", "node": "fetch_analytics", "config": {"period": "7d"}},
            {"type": "text_generation", "node": "llama", "config": {"prompt_template": "Generate a weekly report from this analytics data: {{analytics}}"}},
            {"type": "output", "node": "email", "config": {"to": "{{owner_email}}"}}
        ]
    }
}


class WorkflowTemplateManager:
    """Manage workflow templates."""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".pod_wizard" / "workflow_templates"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.templates = {**WORKFLOW_TEMPLATES}
        self._load_custom_templates()
    
    def _load_custom_templates(self):
        """Load custom templates from storage."""
        for file in self.storage_dir.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    self.templates[data['id']] = data
            except Exception as e:
                logger.warning(f"Failed to load workflow template {file}: {e}")
    
    def get_template(self, template_id: str) -> Optional[Dict]:
        return self.templates.get(template_id)
    
    def list_templates(self, category: Optional[str] = None) -> List[Dict]:
        templates = list(self.templates.values())
        if category:
            templates = [t for t in templates if t.get('category') == category]
        return sorted(templates, key=lambda t: t.get('name', ''))
    
    def get_categories(self) -> List[str]:
        return sorted(set(t.get('category', 'Other') for t in self.templates.values()))
    
    def instantiate_template(self, template_id: str) -> Optional[Dict]:
        """Create a new workflow instance from a template."""
        template = self.get_template(template_id)
        if not template:
            return None
            
        # Create a deep copy of the template
        import copy
        instance = copy.deepcopy(template)
        
        # Add instance-specific metadata
        instance['instance_id'] = str(uuid.uuid4())
        instance['created_at'] = datetime.now().isoformat()
        instance['status'] = 'draft'
        instance['template_id'] = template_id
        
        return instance

    def save_template(self, template: Dict):
        """Save a custom template."""
        template_id = template.get('id', str(uuid.uuid4()))
        template['id'] = template_id
        template['modified_at'] = datetime.now().isoformat()
        
        self.templates[template_id] = template
        
        file_path = self.storage_dir / f"{template_id}.json"
        with open(file_path, 'w') as f:
            json.dump(template, f, indent=2)
    
    def create_from_template(self, template_id: str, variables: Dict) -> Dict:
        """Create a workflow instance from a template with variables filled in."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        # Deep copy and substitute variables
        import copy
        instance = copy.deepcopy(template)
        instance['id'] = str(uuid.uuid4())
        instance['created_from'] = template_id
        instance['created_at'] = datetime.now().isoformat()
        instance['variables'] = variables
        
        # Replace template variables in step configs
        for step in instance.get('steps', []):
            config = step.get('config', {})
            for key, value in config.items():
                if isinstance(value, str):
                    for var_name, var_value in variables.items():
                        value = value.replace(f"{{{{{var_name}}}}}", str(var_value))
                    config[key] = value
        
        return instance


def render_workflow_templates():
    """Render workflow templates UI in Streamlit."""
    import streamlit as st
    
    st.markdown("### 🔄 Workflow Templates")
    st.caption("Pre-built workflows for common marketing tasks")
    
    manager = WorkflowTemplateManager()
    
    # Category tabs
    categories = manager.get_categories()
    selected_category = st.selectbox("Category", ["All"] + categories)
    
    templates = manager.list_templates(
        category=None if selected_category == "All" else selected_category
    )
    
    for template in templates:
        with st.expander(f"**{template['name']}** - {template.get('difficulty', 'N/A')}"):
            st.markdown(template.get('description', ''))
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.caption(f"⏱️ {template.get('estimated_time', 'N/A')}")
            with col2:
                st.caption(f"📊 {len(template.get('steps', []))} steps")
            with col3:
                st.caption(f"📁 {template.get('category', 'N/A')}")
            
            # Show steps preview
            st.markdown("**Steps:**")
            for i, step in enumerate(template.get('steps', [])[:5]):
                st.text(f"  {i+1}. {step.get('node', step.get('type', 'Unknown'))}")
            if len(template.get('steps', [])) > 5:
                st.text(f"  ... and {len(template['steps']) - 5} more")
            
            if st.button("Use This Workflow", key=f"use_wf_{template['id']}", use_container_width=True):
                st.session_state['selected_workflow_template'] = template['id']
                st.success(f"✅ Selected: {template['name']}")
