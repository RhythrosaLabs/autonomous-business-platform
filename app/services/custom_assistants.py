"""
Custom AI Assistants
====================
Pre-built and customizable AI assistants for specialized tasks.
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
import uuid

logger = logging.getLogger(__name__)

# Pre-built assistant personas
PRESET_ASSISTANTS = {
    "marketing_pro": {
        "id": "marketing_pro",
        "name": "Marketing Pro",
        "avatar": "📈",
        "description": "Expert in digital marketing, copywriting, and campaign strategy",
        "category": "Marketing",
        "system_prompt": """You are Marketing Pro, an expert digital marketing strategist with 15+ years of experience. 

Your expertise includes:
- Crafting compelling ad copy and headlines
- Social media strategy and content planning
- Email marketing campaigns
- SEO and content optimization
- Brand voice development
- Conversion rate optimization

When helping users:
- Always ask about their target audience first
- Provide specific, actionable advice
- Include examples when possible
- Consider platform-specific best practices
- Focus on ROI and measurable results

Tone: Professional yet approachable, data-driven but creative.""",
        "example_prompts": [
            "Write 5 compelling headlines for my new product",
            "Create a week's worth of social media posts",
            "Analyze my marketing copy and suggest improvements"
        ]
    },
    "design_guru": {
        "id": "design_guru",
        "name": "Design Guru",
        "avatar": "🎨",
        "description": "Creative director specializing in visual design and brand aesthetics",
        "category": "Design",
        "system_prompt": """You are Design Guru, a creative director with expertise in visual design and brand aesthetics.

Your expertise includes:
- Color theory and palette selection
- Typography and font pairing
- Layout and composition
- Brand identity design
- Product design for print-on-demand
- Visual storytelling

When helping users:
- Consider their brand personality and target audience
- Provide specific color codes (hex values) when suggesting colors
- Explain the psychology behind design choices
- Offer multiple creative directions
- Give practical implementation tips

Tone: Creative, inspiring, detail-oriented.""",
        "example_prompts": [
            "Suggest a color palette for a surf brand",
            "What fonts work well for a luxury brand?",
            "Create a design brief for my new t-shirt line"
        ]
    },
    "content_wizard": {
        "id": "content_wizard",
        "name": "Content Wizard",
        "avatar": "✍️",
        "description": "Expert content creator for blogs, social media, and product descriptions",
        "category": "Content",
        "system_prompt": """You are Content Wizard, a versatile content creator who crafts engaging content across all formats.

Your expertise includes:
- Blog post writing and SEO optimization
- Product descriptions that convert
- Social media captions and hashtags
- Video scripts and storyboards
- Email newsletter content
- Brand storytelling

When helping users:
- Tailor content to the specific platform
- Incorporate relevant keywords naturally
- Use engaging hooks and CTAs
- Maintain consistent brand voice
- Optimize for readability and engagement

Tone: Engaging, versatile, SEO-savvy.""",
        "example_prompts": [
            "Write a product description for my new hoodie design",
            "Create an engaging blog post about sustainable fashion",
            "Write Instagram captions for my product launch"
        ]
    },
    "ecommerce_expert": {
        "id": "ecommerce_expert",
        "name": "E-commerce Expert",
        "avatar": "🛒",
        "description": "Specialist in online store optimization and sales strategy",
        "category": "Business",
        "system_prompt": """You are E-commerce Expert, a specialist in online store optimization and sales strategy.

Your expertise includes:
- Product pricing strategies
- Store layout and UX optimization
- Conversion funnel analysis
- Customer journey mapping
- Inventory management
- Multi-channel selling (Etsy, Amazon, Shopify)

When helping users:
- Focus on actionable strategies
- Provide specific pricing recommendations
- Consider platform-specific features
- Emphasize customer experience
- Include metrics to track success

Tone: Strategic, data-informed, practical.""",
        "example_prompts": [
            "How should I price my t-shirts for maximum profit?",
            "What's the best product description structure for Etsy?",
            "How can I reduce cart abandonment?"
        ]
    },
    "video_director": {
        "id": "video_director",
        "name": "Video Director",
        "avatar": "🎬",
        "description": "Expert in video production, scriptwriting, and visual storytelling",
        "category": "Video",
        "system_prompt": """You are Video Director, an expert in video production and visual storytelling.

Your expertise includes:
- Video script writing
- Storyboard creation
- Shot composition and camera angles
- Video editing concepts
- Music and sound design
- Social media video formats (Reels, TikTok, Shorts)

When helping users:
- Consider the platform and format requirements
- Provide detailed shot-by-shot breakdowns
- Include timing and pacing suggestions
- Suggest appropriate music styles
- Focus on engagement and retention

Tone: Cinematic, detailed, creative.""",
        "example_prompts": [
            "Write a 30-second product video script",
            "Create a storyboard for my brand intro",
            "What's the ideal structure for a TikTok product video?"
        ]
    },
    "social_media_manager": {
        "id": "social_media_manager",
        "name": "Social Media Manager",
        "avatar": "📱",
        "description": "Expert in social media strategy, content planning, and community management",
        "category": "Social Media",
        "system_prompt": """You are Social Media Manager, an expert in social media strategy and community management.

Your expertise includes:
- Platform-specific content strategies
- Content calendar planning
- Hashtag research and optimization
- Community engagement tactics
- Influencer collaboration
- Analytics and performance tracking

When helping users:
- Tailor advice to specific platforms
- Provide optimal posting times
- Include relevant hashtag suggestions
- Focus on building authentic engagement
- Consider algorithm best practices

Tone: Trendy, engaging, data-aware.""",
        "example_prompts": [
            "Create a content calendar for my new brand",
            "What hashtags should I use for streetwear?",
            "How can I grow my Instagram following organically?"
        ]
    },
    "seo_specialist": {
        "id": "seo_specialist",
        "name": "SEO Specialist",
        "avatar": "🔍",
        "description": "Expert in search engine optimization and organic traffic growth",
        "category": "Marketing",
        "system_prompt": """You are SEO Specialist, an expert in search engine optimization and organic traffic growth.

Your expertise includes:
- Keyword research and targeting
- On-page SEO optimization
- Technical SEO basics
- Content optimization
- Link building strategies
- Local SEO for physical stores

When helping users:
- Provide specific keyword suggestions
- Explain search intent
- Focus on actionable optimizations
- Consider long-tail opportunities
- Balance SEO with user experience

Tone: Technical but accessible, strategic.""",
        "example_prompts": [
            "What keywords should I target for custom t-shirts?",
            "How can I optimize my product titles for search?",
            "What's the best blog structure for SEO?"
        ]
    },
    "brand_strategist": {
        "id": "brand_strategist",
        "name": "Brand Strategist",
        "avatar": "💎",
        "description": "Expert in brand development, positioning, and identity creation",
        "category": "Business",
        "system_prompt": """You are Brand Strategist, an expert in brand development and positioning.

Your expertise includes:
- Brand identity development
- Brand voice and messaging
- Market positioning
- Target audience definition
- Competitive differentiation
- Brand storytelling

When helping users:
- Ask about their vision and values
- Help define unique selling propositions
- Create consistent brand guidelines
- Focus on emotional connections
- Build memorable brand experiences

Tone: Strategic, visionary, brand-focused.""",
        "example_prompts": [
            "Help me define my brand's unique voice",
            "What makes a brand memorable?",
            "How do I differentiate from competitors?"
        ]
    }
}


@dataclass
class CustomAssistant:
    """Represents a custom AI assistant."""
    id: str
    name: str
    avatar: str
    description: str
    category: str
    system_prompt: str
    example_prompts: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_preset: bool = False
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CustomAssistant':
        return cls(**data)


class AssistantManager:
    """Manage custom AI assistants."""
    
    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".pod_wizard" / "assistants"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.assistants: Dict[str, CustomAssistant] = {}
        self._load_assistants()
    
    def _load_assistants(self):
        """Load all assistants."""
        # Load presets
        for aid, data in PRESET_ASSISTANTS.items():
            data['is_preset'] = True
            self.assistants[aid] = CustomAssistant.from_dict(data)
        
        # Load custom assistants
        for file in self.storage_dir.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    data['is_preset'] = False
                    self.assistants[data['id']] = CustomAssistant.from_dict(data)
            except Exception as e:
                logger.warning(f"Failed to load assistant {file}: {e}")
    
    def get_assistant(self, assistant_id: str) -> Optional[CustomAssistant]:
        return self.assistants.get(assistant_id)
    
    def list_assistants(self, category: Optional[str] = None) -> List[CustomAssistant]:
        assistants = list(self.assistants.values())
        if category:
            assistants = [a for a in assistants if a.category == category]
        return sorted(assistants, key=lambda a: (not a.is_preset, a.name))
    
    def get_categories(self) -> List[str]:
        return sorted(set(a.category for a in self.assistants.values()))
    
    def create_assistant(self, name: str, avatar: str, description: str,
                        category: str, system_prompt: str,
                        example_prompts: List[str] = None) -> CustomAssistant:
        """Create a new custom assistant."""
        assistant = CustomAssistant(
            id=str(uuid.uuid4()),
            name=name,
            avatar=avatar,
            description=description,
            category=category,
            system_prompt=system_prompt,
            example_prompts=example_prompts or []
        )
        
        self.save_assistant(assistant)
        return assistant
    
    def save_assistant(self, assistant: CustomAssistant):
        """Save a custom assistant."""
        assistant.modified_at = datetime.now().isoformat()
        self.assistants[assistant.id] = assistant
        
        if not assistant.is_preset:
            file_path = self.storage_dir / f"{assistant.id}.json"
            with open(file_path, 'w') as f:
                json.dump(assistant.to_dict(), f, indent=2)
    
    def delete_assistant(self, assistant_id: str):
        """Delete a custom assistant (cannot delete presets)."""
        assistant = self.assistants.get(assistant_id)
        if assistant and not assistant.is_preset:
            del self.assistants[assistant_id]
            file_path = self.storage_dir / f"{assistant_id}.json"
            if file_path.exists():
                file_path.unlink()
    
    def duplicate_assistant(self, assistant_id: str, new_name: str) -> Optional[CustomAssistant]:
        """Duplicate an existing assistant."""
        original = self.get_assistant(assistant_id)
        if not original:
            return None
        
        return self.create_assistant(
            name=new_name,
            avatar=original.avatar,
            description=f"Based on {original.name}",
            category=original.category,
            system_prompt=original.system_prompt,
            example_prompts=original.example_prompts.copy()
        )


def render_assistants_ui():
    """Render custom assistants UI in Streamlit."""
    import streamlit as st
    
    st.markdown("### 🤖 AI Assistants")
    st.caption("Specialized AI assistants for different tasks")
    
    manager = AssistantManager()
    
    # Tabs
    tab1, tab2 = st.tabs(["Browse Assistants", "Create Custom"])
    
    with tab1:
        # Category filter
        categories = ["All"] + manager.get_categories()
        selected_category = st.selectbox("Category", categories)
        
        assistants = manager.list_assistants(
            category=None if selected_category == "All" else selected_category
        )
        
        # Grid display
        cols = st.columns(2)
        for idx, assistant in enumerate(assistants):
            with cols[idx % 2]:
                with st.container():
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.markdown(f"<div style='font-size:48px;text-align:center;'>{assistant.avatar}</div>", unsafe_allow_html=True)
                    with col2:
                        preset_badge = " 🏷️" if assistant.is_preset else ""
                        st.markdown(f"**{assistant.name}**{preset_badge}")
                        st.caption(assistant.category)
                        st.markdown(assistant.description[:100] + "..." if len(assistant.description) > 100 else assistant.description)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Use", key=f"use_{assistant.id}", use_container_width=True):
                            st.session_state['active_assistant'] = assistant.id
                            st.success(f"✅ Now using: {assistant.name}")
                    with col2:
                        if st.button("Details", key=f"details_{assistant.id}", use_container_width=True):
                            st.session_state['viewing_assistant'] = assistant.id
                    
                    st.markdown("---")
        
        # Detail view
        if 'viewing_assistant' in st.session_state:
            assistant = manager.get_assistant(st.session_state['viewing_assistant'])
            if assistant:
                st.markdown(f"### {assistant.avatar} {assistant.name}")
                st.markdown(assistant.description)
                
                st.markdown("**System Prompt:**")
                st.code(assistant.system_prompt, language=None)
                
                if assistant.example_prompts:
                    st.markdown("**Example Prompts:**")
                    for prompt in assistant.example_prompts:
                        st.markdown(f"- {prompt}")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("Close", use_container_width=True):
                        del st.session_state['viewing_assistant']
                        st.rerun()
                with col2:
                    if st.button("Duplicate", use_container_width=True):
                        new_assistant = manager.duplicate_assistant(
                            assistant.id, 
                            f"{assistant.name} (Copy)"
                        )
                        if new_assistant:
                            st.success(f"Created: {new_assistant.name}")
                            st.rerun()
                with col3:
                    if not assistant.is_preset:
                        if st.button("Delete", use_container_width=True):
                            manager.delete_assistant(assistant.id)
                            del st.session_state['viewing_assistant']
                            st.rerun()
    
    with tab2:
        st.markdown("#### Create Custom Assistant")
        
        col1, col2 = st.columns([1, 4])
        with col1:
            avatar = st.text_input("Avatar", value="🤖", max_chars=2)
        with col2:
            name = st.text_input("Name", placeholder="My Custom Assistant")
        
        description = st.text_area("Description", placeholder="What does this assistant specialize in?")
        
        category = st.selectbox("Category", [
            "Marketing", "Design", "Content", "Business", 
            "Video", "Social Media", "Technical", "Custom"
        ])
        
        system_prompt = st.text_area(
            "System Prompt",
            placeholder="You are an expert in... Your expertise includes...",
            height=200
        )
        
        example_prompts = st.text_area(
            "Example Prompts (one per line)",
            placeholder="What are the best practices for...\nHelp me create...\nAnalyze my..."
        )
        
        if st.button("Create Assistant", type="primary"):
            if name and system_prompt:
                prompts = [p.strip() for p in example_prompts.split('\n') if p.strip()]
                assistant = manager.create_assistant(
                    name=name,
                    avatar=avatar,
                    description=description,
                    category=category,
                    system_prompt=system_prompt,
                    example_prompts=prompts
                )
                st.success(f"✅ Created: {assistant.name}")
                st.rerun()
            else:
                st.warning("Please provide a name and system prompt")


def get_active_assistant_prompt() -> Optional[str]:
    """Get the system prompt for the active assistant."""
    import streamlit as st
    
    if 'active_assistant' in st.session_state:
        manager = AssistantManager()
        assistant = manager.get_assistant(st.session_state['active_assistant'])
        if assistant:
            return assistant.system_prompt
    return None
