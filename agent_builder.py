"""
Agent Builder - Create Reusable AI Agents
Combines workflows, prompts, and Replicate models into saveable agent templates.
"""

import streamlit as st
import json
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

AGENTS_DIR = Path("agents")
AGENTS_DIR.mkdir(exist_ok=True)


# Pre-built agent templates
AGENT_TEMPLATES = {
    'product_launch': {
        'name': 'Product Launch Agent',
        'description': 'Complete product launch workflow: design → mockup → ads → blog → video → publish',
        'icon': '🚀',
        'workflow': [
            {'step': 'Generate Design', 'model': 'prunaai/flux-fast', 'type': 'image'},
            {'step': 'Create Printify Product', 'model': 'printify', 'type': 'integration'},
            {'step': 'Generate Mockups', 'model': 'printify', 'type': 'integration'},
            {'step': 'Create Static Ads', 'model': 'pipeline-examples/ads-for-products:latest', 'type': 'ads'},
            {'step': 'Create Video Ads', 'model': 'pipeline-examples/video-ads:latest', 'type': 'ads'},
            {'step': 'Write Blog Post', 'model': 'openai', 'type': 'text'},
            {'step': 'Generate Video', 'model': 'kwaivgi/kling-v2.5-turbo-pro', 'type': 'video'},
            {'step': 'Publish to Shopify', 'model': 'shopify', 'type': 'integration'},
            {'step': 'Upload to YouTube', 'model': 'youtube', 'type': 'integration'}
        ],
        'prompts': {
            'design': 'Create a {style} design featuring {concept}',
            'ads': 'Professional ad copy for {product} targeting {audience}',
            'blog': 'SEO-optimized blog post about {product} benefits'
        }
    },
    'social_media': {
        'name': 'Social Media Agent',
        'description': 'Generate complete social media campaign with images and captions',
        'icon': '📱',
        'workflow': [
            {'step': 'Generate Hero Image', 'model': 'prunaai/flux-fast', 'type': 'image'},
            {'step': 'Create 3 Variations', 'model': 'prunaai/flux-fast', 'type': 'image'},
            {'step': 'Generate Static Ads', 'model': 'loolau/flux-static-ads:latest', 'type': 'ads'},
            {'step': 'Write Captions', 'model': 'openai', 'type': 'text'},
            {'step': 'Generate Hashtags', 'model': 'openai', 'type': 'text'},
            {'step': 'Create Video Posts', 'model': 'pipeline-examples/video-ads:latest', 'type': 'ads'}
        ],
        'prompts': {
            'image': '{concept} social media post, {style}, high engagement',
            'caption': 'Engaging social media caption for {product}, max 150 chars',
            'hashtags': 'Generate 10 relevant hashtags for {concept}'
        }
    },
    'content_creator': {
        'name': 'Content Creator Agent',
        'description': 'Blog posts with AI-generated images and videos',
        'icon': '✍️',
        'workflow': [
            {'step': 'Research Topic', 'model': 'openai', 'type': 'text'},
            {'step': 'Generate Outline', 'model': 'openai', 'type': 'text'},
            {'step': 'Write Article', 'model': 'openai', 'type': 'text'},
            {'step': 'Create Featured Image', 'model': 'prunaai/flux-fast', 'type': 'image'},
            {'step': 'Generate 3-5 Section Images', 'model': 'prunaai/flux-fast', 'type': 'image'},
            {'step': 'Create Video Summary', 'model': 'kwaivgi/kling-v2.5-turbo-pro', 'type': 'video'},
            {'step': 'Publish to Shopify', 'model': 'shopify', 'type': 'integration'}
        ],
        'prompts': {
            'research': 'Research comprehensive information about {topic}',
            'outline': 'Create detailed blog outline for: {topic}',
            'article': 'Write 1500-word SEO article with sections from outline',
            'images': 'Section image for: {section_title}'
        }
    },
    'video_producer': {
        'name': 'Video Producer Agent',
        'description': 'Complete video production from concept to YouTube',
        'icon': '🎬',
        'workflow': [
            {'step': 'Write Script', 'model': 'openai', 'type': 'text'},
            {'step': 'Generate Scenes', 'model': 'kwaivgi/kling-v2.5-turbo-pro', 'type': 'video'},
            {'step': 'Create Voiceover', 'model': 'minimax/speech-02-hd', 'type': 'audio'},
            {'step': 'Generate Music', 'model': 'meta/musicgen', 'type': 'audio'},
            {'step': 'Assemble Video', 'model': 'moviepy', 'type': 'processing'},
            {'step': 'Create Thumbnail', 'model': 'prunaai/flux-fast', 'type': 'image'},
            {'step': 'Upload to YouTube', 'model': 'youtube', 'type': 'integration'}
        ],
        'prompts': {
            'script': '30-second commercial script for {product}',
            'scenes': 'Scene {number}: {description}',
            'voiceover': 'Professional narrator voice',
            'music': 'Upbeat background music for advertisement'
        }
    },
    'brand_builder': {
        'name': 'Brand Builder Agent',
        'description': 'Build complete brand identity with logo, colors, and assets',
        'icon': '🎨',
        'workflow': [
            {'step': 'Generate Logo Concepts', 'model': 'prunaai/flux-fast', 'type': 'image'},
            {'step': 'Create Color Palette', 'model': 'openai', 'type': 'text'},
            {'step': 'Design Brand Guidelines', 'model': 'openai', 'type': 'text'},
            {'step': 'Generate Brand Assets', 'model': 'prunaai/flux-fast', 'type': 'image'},
            {'step': 'Create Logo Variations', 'model': 'subhash25rawat/logo-in-context:latest', 'type': 'ads'},
            {'step': 'Build Brand Package', 'model': 'system', 'type': 'processing'}
        ],
        'prompts': {
            'logo': 'Modern minimalist logo for {brand_name}, {industry}',
            'palette': 'Color palette for {brand_name} brand, {mood} feel',
            'guidelines': 'Brand guidelines for {brand_name}, {industry} industry'
        }
    },
    'ecommerce_optimizer': {
        'name': 'E-commerce Optimizer Agent',
        'description': 'Optimize product listings with SEO, images, and ads',
        'icon': '🛒',
        'workflow': [
            {'step': 'Analyze Product', 'model': 'openai', 'type': 'text'},
            {'step': 'Generate Product Photos', 'model': 'prunaai/flux-fast', 'type': 'image'},
            {'step': 'Write SEO Title', 'model': 'openai', 'type': 'text'},
            {'step': 'Write Description', 'model': 'openai', 'type': 'text'},
            {'step': 'Generate Bullet Points', 'model': 'openai', 'type': 'text'},
            {'step': 'Create Product Ads', 'model': 'pipeline-examples/ads-for-products:latest', 'type': 'ads'},
            {'step': 'Export to CSV', 'model': 'system', 'type': 'processing'}
        ],
        'prompts': {
            'analyze': 'Analyze product: {product_name}',
            'photos': 'Professional product photography: {product_name}',
            'seo_title': 'SEO-optimized product title for {product_name}',
            'description': 'Compelling product description with benefits'
        }
    }
}


class Agent:
    """Represents a custom AI agent."""
    
    def __init__(self, name: str, description: str = "", template: str = None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.template = template
        self.workflow_steps = []
        self.prompts = {}
        self.settings = {}
        self.created_at = datetime.now().isoformat()
        self.modified_at = datetime.now().isoformat()
    
    def add_step(self, step: Dict[str, Any]):
        """Add a workflow step to the agent."""
        self.workflow_steps.append(step)
    
    def set_prompt(self, key: str, prompt: str):
        """Set a prompt template."""
        self.prompts[key] = prompt
    
    def to_dict(self) -> Dict:
        """Convert agent to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'template': self.template,
            'workflow_steps': self.workflow_steps,
            'prompts': self.prompts,
            'settings': self.settings,
            'created_at': self.created_at,
            'modified_at': self.modified_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Agent':
        """Create agent from dictionary."""
        agent = cls(data['name'], data.get('description', ''), data.get('template'))
        agent.id = data['id']
        agent.workflow_steps = data.get('workflow_steps', [])
        agent.prompts = data.get('prompts', {})
        agent.settings = data.get('settings', {})
        agent.created_at = data.get('created_at', datetime.now().isoformat())
        agent.modified_at = data.get('modified_at', datetime.now().isoformat())
        return agent
    
    def save(self) -> Path:
        """Save agent to file."""
        self.modified_at = datetime.now().isoformat()
        file_path = AGENTS_DIR / f"{self.id}.json"
        
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        
        return file_path
    
    @classmethod
    def load(cls, file_path: Path) -> 'Agent':
        """Load agent from file."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        return cls.from_dict(data)
    
    @classmethod
    def list_saved(cls) -> List['Agent']:
        """List all saved agents."""
        agents = []
        
        for file_path in AGENTS_DIR.glob("*.json"):
            try:
                agent = cls.load(file_path)
                agents.append(agent)
            except Exception as e:
                logger.error(f"Error loading agent {file_path}: {e}")
        
        return agents


def render_agent_builder():
    """Render the Agent Builder interface."""
    st.markdown("### 🤖 Custom Agent Builder")
    st.markdown("Create reusable AI agents by combining workflows, prompts, and Replicate models")
    
    # Tabs for different sections
    builder_tabs = st.tabs(["📦 Templates", "🛠️ Builder", "💾 Saved Agents", "▶️ Run Agent"])
    
    # Tab 1: Templates
    with builder_tabs[0]:
        st.markdown("#### Pre-built Agent Templates")
        st.markdown("Start with a template or create your own from scratch")
        
        # Display templates in grid
        cols = st.columns(2)
        
        for idx, (template_id, template) in enumerate(AGENT_TEMPLATES.items()):
            with cols[idx % 2]:
                with st.container():
                    st.markdown(f"### {template['icon']} {template['name']}")
                    st.markdown(template['description'])
                    
                    with st.expander("📋 View Workflow"):
                        for step in template['workflow']:
                            st.markdown(f"**{step['step']}**")
                            st.caption(f"Model: `{step['model']}` | Type: {step['type']}")
                    
                    col_use, col_customize = st.columns(2)
                    
                    with col_use:
                        if st.button(f"Use Template", key=f"use_{template_id}", use_container_width=True):
                            # Create agent from template
                            agent = Agent(template['name'], template['description'], template_id)
                            agent.workflow_steps = template['workflow']
                            agent.prompts = template['prompts']
                            agent.save()
                            st.success(f"✅ Created: {template['name']}")
                            st.rerun()
                    
                    with col_customize:
                        if st.button(f"Customize", key=f"custom_{template_id}", use_container_width=True):
                            st.session_state.editing_template = template_id
                            st.session_state.agent_builder_mode = 'customize'
                            st.rerun()
    
    # Tab 2: Builder
    with builder_tabs[1]:
        st.markdown("#### Build Custom Agent")
        
        # Agent basic info
        agent_name = st.text_input("Agent Name:", placeholder="e.g., My Custom Agent")
        agent_description = st.text_area("Description:", placeholder="What does this agent do?")
        
        if agent_name:
            # Initialize or load agent
            if 'current_agent' not in st.session_state or st.session_state.get('agent_name_changed'):
                st.session_state.current_agent = Agent(agent_name, agent_description)
                st.session_state.agent_name_changed = False
            
            agent = st.session_state.current_agent
            agent.name = agent_name
            agent.description = agent_description
            
            st.markdown("---")
            st.markdown("#### Workflow Steps")
            
            # Add step
            with st.expander("➕ Add Workflow Step", expanded=False):
                step_name = st.text_input("Step Name:", placeholder="e.g., Generate Product Image")
                
                step_type = st.selectbox(
                    "Step Type:",
                    ["image", "video", "audio", "text", "ads", "integration", "processing"]
                )
                
                if step_type == "image":
                    step_model = st.selectbox("Model:", ["prunaai/flux-fast", "black-forest-labs/flux-pro", "black-forest-labs/flux-dev"])
                elif step_type == "video":
                    step_model = st.selectbox("Model:", ["kwaivgi/kling-v2.5-turbo-pro", "luma/dream-machine"])
                elif step_type == "audio":
                    step_model = st.selectbox("Model:", ["minimax/speech-02-hd", "meta/musicgen", "riffusion/riffusion"])
                elif step_type == "ads":
                    step_model = st.selectbox("Model:", ["pipeline-examples/ads-for-products:latest", "pipeline-examples/video-ads:latest", "loolau/flux-static-ads:latest"])
                elif step_type == "integration":
                    step_model = st.selectbox("Integration:", ["printify", "shopify", "youtube"])
                elif step_type == "text":
                    step_model = st.selectbox("Model:", ["openai", "anthropic"])
                else:
                    step_model = st.text_input("Model/System:", placeholder="e.g., moviepy")
                
                if st.button("Add Step", type="primary"):
                    agent.add_step({
                        'step': step_name,
                        'model': step_model,
                        'type': step_type
                    })
                    st.success(f"✅ Added: {step_name}")
                    st.rerun()
            
            # Display current steps
            if agent.workflow_steps:
                st.markdown("**Current Workflow:**")
                
                for idx, step in enumerate(agent.workflow_steps):
                    col_step, col_actions = st.columns([4, 1])
                    
                    with col_step:
                        st.markdown(f"**{idx + 1}. {step['step']}**")
                        st.caption(f"Model: `{step['model']}` | Type: {step['type']}")
                    
                    with col_actions:
                        if st.button("🗑️", key=f"del_step_{idx}"):
                            agent.workflow_steps.pop(idx)
                            st.rerun()
            
            # Prompts
            st.markdown("---")
            st.markdown("#### Prompt Templates")
            
            with st.expander("➕ Add Prompt Template"):
                prompt_key = st.text_input("Prompt Key:", placeholder="e.g., product_description")
                prompt_template = st.text_area(
                    "Prompt Template:",
                    placeholder="Use {variables} in curly braces, e.g., 'Generate {product} image in {style}'"
                )
                
                if st.button("Add Prompt"):
                    agent.set_prompt(prompt_key, prompt_template)
                    st.success(f"✅ Added prompt: {prompt_key}")
                    st.rerun()
            
            if agent.prompts:
                st.markdown("**Current Prompts:**")
                for key, prompt in agent.prompts.items():
                    st.code(f"{key}: {prompt}", language="text")
            
            # Save agent
            st.markdown("---")
            
            col_save, col_clear = st.columns(2)
            
            with col_save:
                if st.button("💾 Save Agent", type="primary", use_container_width=True):
                    agent.save()
                    st.success(f"✅ Agent saved: {agent.name}")
                    st.balloons()
            
            with col_clear:
                if st.button("🗑️ Clear", use_container_width=True):
                    del st.session_state.current_agent
                    st.rerun()
    
    # Tab 3: Saved Agents
    with builder_tabs[2]:
        st.markdown("#### Your Saved Agents")
        
        saved_agents = Agent.list_saved()
        
        if not saved_agents:
            st.info("No saved agents yet. Create one in the Builder tab!")
        else:
            for agent in saved_agents:
                with st.expander(f"🤖 {agent.name}", expanded=False):
                    st.markdown(f"**Description:** {agent.description}")
                    st.markdown(f"**Created:** {agent.created_at[:10]}")
                    st.markdown(f"**Steps:** {len(agent.workflow_steps)}")
                    
                    if agent.template:
                        st.markdown(f"**Template:** {agent.template}")
                    
                    col_run, col_edit, col_delete = st.columns(3)
                    
                    with col_run:
                        if st.button("▶️ Run", key=f"run_{agent.id}"):
                            st.session_state.running_agent = agent
                            st.rerun()
                    
                    with col_edit:
                        if st.button("✏️ Edit", key=f"edit_{agent.id}"):
                            st.session_state.current_agent = agent
                            st.info("Go to Builder tab to edit")
                    
                    with col_delete:
                        if st.button("🗑️ Delete", key=f"delete_{agent.id}"):
                            (AGENTS_DIR / f"{agent.id}.json").unlink()
                            st.success("Agent deleted")
                            st.rerun()
    
    # Tab 4: Run Agent
    with builder_tabs[3]:
        st.markdown("#### Run Agent")
        
        if 'running_agent' in st.session_state:
            agent = st.session_state.running_agent
            
            st.success(f"Running: **{agent.name}**")
            st.markdown(agent.description)
            
            st.markdown("---")
            st.markdown("#### Workflow Steps")
            
            for idx, step in enumerate(agent.workflow_steps):
                st.markdown(f"**{idx + 1}. {step['step']}**")
                st.caption(f"Model: {step['model']}")
            
            st.markdown("---")
            st.markdown("#### Agent Inputs")
            
            # Collect inputs for prompt variables
            agent_inputs = {}
            
            if agent.prompts:
                st.markdown("Fill in the variables for this agent:")
                
                # Extract all unique variables from prompts
                all_variables = set()
                for prompt in agent.prompts.values():
                    import re
                    variables = re.findall(r'\{(\w+)\}', prompt)
                    all_variables.update(variables)
                
                for var in sorted(all_variables):
                    agent_inputs[var] = st.text_input(f"{var}:", key=f"input_{var}")
            
            if st.button("🚀 Execute Agent", type="primary"):
                with st.spinner("Running agent workflow..."):
                    st.info("🚧 Agent execution framework in place. Full implementation will execute each workflow step with Replicate APIs.")
                    
                    # Show what would happen
                    st.markdown("**Execution Plan:**")
                    for idx, step in enumerate(agent.workflow_steps):
                        st.markdown(f"✓ {step['step']} (using {step['model']})")
                    
                    st.success("✅ Agent execution complete!")
        else:
            st.info("Select an agent from 'Saved Agents' tab to run it")
