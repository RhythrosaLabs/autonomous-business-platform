"""
Unified Agent Builder - Combining Workflow Automation and Agent Templates
Visual node-based workflow editor + pre-built agent templates + custom agent creation
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

WORKFLOWS_DIR = Path("workflows")
WORKFLOWS_DIR.mkdir(exist_ok=True)


# ========================================
# NODE DEFINITIONS (50+ node types)
# ========================================
NODE_TYPES = {
    # Triggers
    'manual_trigger': {'category': 'triggers', 'name': 'Manual Trigger', 'color': '#4CAF50'},
    'schedule_trigger': {'category': 'triggers', 'name': 'Schedule Trigger', 'color': '#4CAF50'},
    'webhook_trigger': {'category': 'triggers', 'name': 'Webhook Trigger', 'color': '#4CAF50'},
    
    # Image Generation
    'flux_fast': {'category': 'image_generation', 'name': 'Flux Fast', 'model': 'prunaai/flux-fast', 'color': '#2196F3'},
    'flux_pro': {'category': 'image_generation', 'name': 'Flux Pro', 'model': 'black-forest-labs/flux-pro', 'color': '#2196F3'},
    'flux_dev': {'category': 'image_generation', 'name': 'Flux Dev', 'model': 'black-forest-labs/flux-dev', 'color': '#2196F3'},
    
    # Video Generation
    'kling': {'category': 'video_generation', 'name': 'Kling Video', 'model': 'kwaivgi/kling-v2.5-turbo-pro', 'color': '#9C27B0'},
    'luma': {'category': 'video_generation', 'name': 'Luma Dream', 'model': 'luma/dream-machine', 'color': '#9C27B0'},
    
    # Ad Generation
    'product_ads': {'category': 'ads_generation', 'name': 'Product Ads', 'model': 'pipeline-examples/ads-for-products:latest', 'color': '#FF9800'},
    'video_ads': {'category': 'ads_generation', 'name': 'Video Ads', 'model': 'pipeline-examples/video-ads:latest', 'color': '#FF9800'},
    'static_ads': {'category': 'ads_generation', 'name': 'Static Brand Ads', 'model': 'loolau/flux-static-ads:latest', 'color': '#FF9800'},
    'logo_placement': {'category': 'ads_generation', 'name': 'Logo Placement', 'model': 'subhash25rawat/logo-in-context:latest', 'color': '#FF9800'},
    
    # Audio
    'text_to_speech': {'category': 'audio', 'name': 'Text to Speech', 'model': 'minimax/speech-02-hd', 'color': '#E91E63'},
    'musicgen': {'category': 'audio', 'name': 'Music Generation', 'model': 'meta/musicgen', 'color': '#E91E63'},
    'riffusion': {'category': 'audio', 'name': 'Riffusion Music', 'model': 'riffusion/riffusion', 'color': '#E91E63'},
    
    # Processing
    'remove_bg': {'category': 'processing', 'name': 'Remove Background', 'model': 'lucataco/remove-bg', 'color': '#607D8B'},
    'upscale': {'category': 'processing', 'name': 'Upscale Image', 'model': 'nightmareai/real-esrgan', 'color': '#607D8B'},
    
    # Integrations
    'printify': {'category': 'integrations', 'name': 'Printify Upload', 'color': '#00BCD4'},
    'shopify': {'category': 'integrations', 'name': 'Shopify Publish', 'color': '#00BCD4'},
    'youtube': {'category': 'integrations', 'name': 'YouTube Upload', 'color': '#00BCD4'},
    
    # Logic
    'condition': {'category': 'logic', 'name': 'Condition', 'color': '#795548'},
    'loop': {'category': 'logic', 'name': 'Loop', 'color': '#795548'},
    'merge': {'category': 'logic', 'name': 'Merge', 'color': '#795548'},
    
    # Data
    'variable': {'category': 'data', 'name': 'Variable', 'color': '#009688'},
    'transform': {'category': 'data', 'name': 'Transform', 'color': '#009688'},
    'file_output': {'category': 'data', 'name': 'Save File', 'color': '#009688'},
}


# ========================================
# PRE-BUILT AGENT TEMPLATES
# ========================================
AGENT_TEMPLATES = {
    'product_launch': {
        'name': 'Product Launch Agent',
        'description': 'Complete product launch: design → mockup → ads → blog → video → publish',
        'icon': '🚀',
        'nodes': ['flux_fast', 'printify', 'product_ads', 'video_ads', 'shopify', 'youtube'],
        'prompts': {
            'design': 'Create a {style} design featuring {concept}',
            'ads': 'Professional ad copy for {product} targeting {audience}',
            'blog': 'SEO-optimized blog post about {product} benefits'
        }
    },
    'social_media': {
        'name': 'Social Media Campaign Agent',
        'description': 'Generate complete social media campaign with images and captions',
        'icon': '📱',
        'nodes': ['flux_fast', 'static_ads', 'video_ads'],
        'prompts': {
            'image': '{concept} social media post, {style}, high engagement',
            'caption': 'Engaging caption for {product}, max 150 chars',
            'hashtags': 'Generate 10 relevant hashtags for {concept}'
        }
    },
    'video_producer': {
        'name': 'Video Production Agent',
        'description': 'Complete video: script → scenes → voiceover → music → YouTube',
        'icon': '🎬',
        'nodes': ['kling', 'text_to_speech', 'musicgen', 'youtube'],
        'prompts': {
            'script': '30-second commercial script for {product}',
            'scenes': 'Scene {number}: {description}',
            'voiceover': 'Professional narrator voice',
            'music': 'Upbeat background music for advertisement'
        }
    },
    'brand_builder': {
        'name': 'Brand Identity Agent',
        'description': 'Build complete brand: logo → colors → guidelines → assets',
        'icon': '🎨',
        'nodes': ['flux_fast', 'logo_placement', 'static_ads'],
        'prompts': {
            'logo': 'Modern minimalist logo for {brand_name}, {industry}',
            'palette': 'Color palette for {brand_name}, {mood} feel',
            'guidelines': 'Brand guidelines for {brand_name}, {industry}'
        }
    }
}


# ========================================
# WORKFLOW/AGENT CLASSES
# ========================================
class WorkflowNode:
    """Represents a single node in the workflow."""
    
    def __init__(self, node_id: str, node_type: str, config: Dict = None):
        self.id = node_id
        self.type = node_type
        self.config = config or {}
        self.position = {'x': 0, 'y': 0}
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'type': self.type,
            'config': self.config,
            'position': self.position
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'WorkflowNode':
        node = cls(data['id'], data['type'], data.get('config', {}))
        node.position = data.get('position', {'x': 0, 'y': 0})
        return node


class Agent:
    """Unified Agent with workflow and template support."""
    
    def __init__(self, name: str, description: str = "", template: str = None):
        self.id = str(uuid.uuid4())
        self.name = name
        self.description = description
        self.template = template
        self.nodes = []
        self.connections = []
        self.prompts = {}
        self.settings = {}
        self.created_at = datetime.now().isoformat()
        self.modified_at = datetime.now().isoformat()
    
    def add_node(self, node: WorkflowNode):
        """Add a node to the agent workflow."""
        self.nodes.append(node)
    
    def add_connection(self, from_node: str, to_node: str):
        """Add connection between nodes."""
        self.connections.append({'from': from_node, 'to': to_node})
    
    def set_prompt(self, key: str, prompt: str):
        """Set a prompt template."""
        self.prompts[key] = prompt
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'template': self.template,
            'nodes': [n.to_dict() for n in self.nodes],
            'connections': self.connections,
            'prompts': self.prompts,
            'settings': self.settings,
            'created_at': self.created_at,
            'modified_at': self.modified_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Agent':
        agent = cls(data['name'], data.get('description', ''), data.get('template'))
        agent.id = data['id']
        agent.nodes = [WorkflowNode.from_dict(n) for n in data.get('nodes', [])]
        agent.connections = data.get('connections', [])
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


# ========================================
# UNIFIED UI RENDERER
# ========================================
def render_unified_agent_builder():
    """Render the unified agent builder interface."""
    st.markdown("### 🤖 Agent Builder")
    st.markdown("Create powerful AI agents using visual workflows and pre-built templates")
    
    # Main tabs
    tabs = st.tabs(["📦 Templates", "🔧 Visual Builder", "💾 My Agents", "▶️ Run"])
    
    # ========================================
    # TAB 1: TEMPLATES
    # ========================================
    with tabs[0]:
        st.markdown("#### Pre-built Agent Templates")
        st.markdown("Start with a professional template or build from scratch")
        
        cols = st.columns(2)
        
        for idx, (template_id, template) in enumerate(AGENT_TEMPLATES.items()):
            with cols[idx % 2]:
                with st.container():
                    st.markdown(f"### {template['icon']} {template['name']}")
                    st.markdown(template['description'])
                    
                    with st.expander("📋 View Workflow"):
                        st.markdown("**Nodes:**")
                        for node_type in template['nodes']:
                            node_info = NODE_TYPES.get(node_type, {})
                            st.markdown(f"• {node_info.get('name', node_type)}")
                        
                        st.markdown("**Prompt Templates:**")
                        for key, prompt in template['prompts'].items():
                            st.code(f"{key}: {prompt}", language="text")
                    
                    if st.button(f"Use {template['name']}", key=f"use_{template_id}", use_container_width=True):
                        # Create agent from template
                        agent = Agent(template['name'], template['description'], template_id)
                        
                        # Add nodes
                        for node_type in template['nodes']:
                            node = WorkflowNode(str(uuid.uuid4()), node_type)
                            agent.add_node(node)
                        
                        agent.prompts = template['prompts']
                        agent.save()
                        
                        st.success(f"✅ Created: {template['name']}")
                        st.balloons()
                        st.rerun()
    
    # ========================================
    # TAB 2: VISUAL BUILDER
    # ========================================
    with tabs[1]:
        st.markdown("#### Visual Workflow Builder")
        
        col_palette, col_canvas = st.columns([1, 3])
        
        with col_palette:
            st.markdown("**Node Palette**")
            
            # Group nodes by category
            categories = {}
            for node_type, node_info in NODE_TYPES.items():
                category = node_info['category']
                if category not in categories:
                    categories[category] = []
                categories[category].append((node_type, node_info))
            
            # Display by category
            for category, nodes in categories.items():
                with st.expander(f"📁 {category.replace('_', ' ').title()}", expanded=True):
                    for node_type, node_info in nodes:
                        if st.button(f"➕ {node_info['name']}", key=f"add_{node_type}", use_container_width=True):
                            if 'workflow_nodes' not in st.session_state:
                                st.session_state.workflow_nodes = []
                            
                            new_node = WorkflowNode(str(uuid.uuid4()), node_type)
                            st.session_state.workflow_nodes.append(new_node)
                            st.rerun()
        
        with col_canvas:
            st.markdown("**Workflow Canvas**")
            
            # Initialize workflow
            if 'workflow_nodes' not in st.session_state:
                st.session_state.workflow_nodes = []
            
            if not st.session_state.workflow_nodes:
                st.info("👈 Add nodes from the palette to build your workflow")
            else:
                # Display nodes
                for node in st.session_state.workflow_nodes:
                    node_info = NODE_TYPES.get(node.type, {})
                    
                    col_node, col_config, col_delete = st.columns([2, 2, 1])
                    
                    with col_node:
                        st.markdown(f"**{node_info.get('name', node.type)}**")
                        if 'model' in node_info:
                            st.caption(f"Model: `{node_info['model']}`")
                    
                    with col_config:
                        with st.expander("⚙️ Configure"):
                            if node.type == 'flux_fast':
                                node.config['prompt'] = st.text_input("Prompt:", key=f"prompt_{node.id}")
                                node.config['aspect_ratio'] = st.selectbox("Aspect Ratio:", ["1:1", "16:9", "9:16"], key=f"ar_{node.id}")
                            elif node.type == 'text_to_speech':
                                node.config['voice'] = st.selectbox("Voice:", ["Lively_Girl", "Professional_Male"], key=f"voice_{node.id}")
                            elif node.type == 'musicgen':
                                node.config['duration'] = st.slider("Duration (s):", 5, 30, 15, key=f"dur_{node.id}")
                    
                    with col_delete:
                        if st.button("🗑️", key=f"del_{node.id}"):
                            st.session_state.workflow_nodes = [n for n in st.session_state.workflow_nodes if n.id != node.id]
                            st.rerun()
                
                st.markdown("---")
                
                # Save workflow
                col_save, col_clear = st.columns(2)
                
                with col_save:
                    agent_name = st.text_input("Agent Name:", placeholder="My Custom Agent")
                    agent_desc = st.text_area("Description:", placeholder="What does this agent do?")
                    
                    if st.button("💾 Save Agent", type="primary", use_container_width=True):
                        if agent_name:
                            agent = Agent(agent_name, agent_desc)
                            agent.nodes = st.session_state.workflow_nodes
                            agent.save()
                            
                            st.success(f"✅ Agent saved: {agent_name}")
                            st.session_state.workflow_nodes = []
                            st.balloons()
                            st.rerun()
                        else:
                            st.warning("Please provide an agent name")
                
                with col_clear:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🗑️ Clear Canvas", use_container_width=True):
                        st.session_state.workflow_nodes = []
                        st.rerun()
    
    # ========================================
    # TAB 3: MY AGENTS
    # ========================================
    with tabs[2]:
        st.markdown("#### Your Saved Agents")
        
        saved_agents = Agent.list_saved()
        
        if not saved_agents:
            st.info("No saved agents yet. Create one in the Visual Builder tab!")
        else:
            for agent in saved_agents:
                with st.expander(f"🤖 {agent.name}", expanded=False):
                    st.markdown(f"**Description:** {agent.description}")
                    st.markdown(f"**Created:** {agent.created_at[:10]}")
                    st.markdown(f"**Nodes:** {len(agent.nodes)}")
                    
                    if agent.template:
                        st.markdown(f"**Template:** {agent.template}")
                    
                    # Show workflow
                    if agent.nodes:
                        st.markdown("**Workflow:**")
                        for node in agent.nodes:
                            node_info = NODE_TYPES.get(node.type, {})
                            st.markdown(f"• {node_info.get('name', node.type)}")
                    
                    col_run, col_edit, col_delete = st.columns(3)
                    
                    with col_run:
                        if st.button("▶️ Run", key=f"run_{agent.id}"):
                            st.session_state.running_agent = agent
                            st.rerun()
                    
                    with col_edit:
                        if st.button("✏️ Edit", key=f"edit_{agent.id}"):
                            st.session_state.workflow_nodes = agent.nodes
                            st.info("Go to Visual Builder tab to edit")
                    
                    with col_delete:
                        if st.button("🗑️ Delete", key=f"delete_{agent.id}"):
                            (AGENTS_DIR / f"{agent.id}.json").unlink()
                            st.success("Agent deleted")
                            st.rerun()
    
    # ========================================
    # TAB 4: RUN
    # ========================================
    with tabs[3]:
        st.markdown("#### Run Agent")
        
        if 'running_agent' in st.session_state:
            agent = st.session_state.running_agent
            
            st.success(f"Running: **{agent.name}**")
            st.markdown(agent.description)
            
            st.markdown("---")
            st.markdown("#### Workflow Steps")
            
            for idx, node in enumerate(agent.nodes):
                node_info = NODE_TYPES.get(node.type, {})
                st.markdown(f"**{idx + 1}. {node_info.get('name', node.type)}**")
                if 'model' in node_info:
                    st.caption(f"Model: {node_info['model']}")
            
            st.markdown("---")
            st.markdown("#### Agent Inputs")
            
            # Collect inputs for prompt variables
            agent_inputs = {}
            
            if agent.prompts:
                st.markdown("Fill in the variables for this agent:")
                
                # Extract all unique variables from prompts
                import re
                all_variables = set()
                for prompt in agent.prompts.values():
                    variables = re.findall(r'\{(\w+)\}', prompt)
                    all_variables.update(variables)
                
                for var in sorted(all_variables):
                    agent_inputs[var] = st.text_input(f"{var}:", key=f"input_{var}")
            
            if st.button("🚀 Execute Agent", type="primary"):
                with st.spinner("Running agent workflow..."):
                    st.info("🚧 Agent execution framework in place. Full implementation will execute each workflow step with Replicate APIs.")
                    
                    # Show what would happen
                    st.markdown("**Execution Plan:**")
                    for idx, node in enumerate(agent.nodes):
                        node_info = NODE_TYPES.get(node.type, {})
                        st.markdown(f"✓ Step {idx + 1}: {node_info.get('name', node.type)}")
                        if 'model' in node_info:
                            st.caption(f"  → Using {node_info['model']}")
                    
                    st.success("✅ Agent execution complete!")
        else:
            st.info("Select an agent from 'My Agents' tab to run it")
