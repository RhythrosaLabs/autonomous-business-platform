"""
Shortcut Saver - Helper to convert successful workflows/pipelines into reusable shortcuts
"""
import streamlit as st
from datetime import datetime as dt
import uuid

def save_pipeline_as_shortcut(
    name: str,
    description: str,
    steps: list,
    icon: str = "⚡",
    category: str = "custom",
    auto_add_to_sidebar: bool = False
):
    """
    Save a completed pipeline/workflow as a reusable shortcut.
    
    Args:
        name: Display name for the shortcut
        description: What the shortcut does
        steps: List of step dicts with keys: type, name, action, prompt_template, etc.
        icon: Emoji icon for the shortcut
        category: Category for organization
        auto_add_to_sidebar: Whether to automatically add to sidebar
    
    Returns:
        str: The ID of the created shortcut
    """
    try:
        from shortcuts_manager import ShortcutsManager
        shortcuts_mgr = ShortcutsManager()
    except ImportError:
        shortcuts_mgr = None
    
    # Create shortcut object
    shortcut = {
        'id': str(uuid.uuid4()),
        'name': name,
        'description': description,
        'icon': icon,
        'category': category,
        'steps': steps,
        'created_at': dt.now().isoformat(),
        'run_count': 0,
        'last_run': None,
        'in_sidebar': auto_add_to_sidebar,
        'settings': {
            'log': True,
            'notify': True,
            'confirm': False
        }
    }
    
    # Add to session state
    if 'magic_shortcuts' not in st.session_state:
        st.session_state.magic_shortcuts = []
    
    st.session_state.magic_shortcuts.append(shortcut)
    
    # Persist to disk
    if shortcuts_mgr:
        shortcuts_mgr.save_shortcut(shortcut)
    
    return shortcut['id']


def render_save_shortcut_button(
    pipeline_name: str,
    pipeline_description: str,
    steps: list,
    icon: str = "⚡",
    button_key: str = None,
    expanded: bool = False
):
    """
    Render a "Save as Shortcut" button after a successful pipeline run.
    
    Args:
        pipeline_name: Name of the pipeline
        pipeline_description: Description of what it does
        steps: List of steps that were executed
        icon: Icon to use for the shortcut
        button_key: Unique key for the button
        expanded: Whether to show expanded UI with customization options
    """
    if not button_key:
        button_key = f"save_shortcut_{pipeline_name.replace(' ', '_')}"
    
    if expanded:
        # Show expandable section with customization
        with st.expander("💾 Save as Reusable Shortcut", expanded=False):
            st.markdown("Save this successful workflow as a magic button you can run anytime!")
            
            col1, col2 = st.columns([3, 1])
            with col1:
                custom_name = st.text_input(
                    "Shortcut Name",
                    value=pipeline_name,
                    key=f"{button_key}_name"
                )
            with col2:
                custom_icon = st.text_input(
                    "Icon",
                    value=icon,
                    max_chars=2,
                    key=f"{button_key}_icon"
                )
            
            custom_desc = st.text_area(
                "Description",
                value=pipeline_description,
                height=60,
                key=f"{button_key}_desc"
            )
            
            add_to_sidebar = st.checkbox(
                "Add to sidebar for quick access",
                value=True,
                key=f"{button_key}_sidebar"
            )
            
            col_save, col_cancel = st.columns([1, 1])
            with col_save:
                if st.button("💾 Save Shortcut", key=f"{button_key}_save", type="primary", use_container_width=True):
                    shortcut_id = save_pipeline_as_shortcut(
                        name=custom_name,
                        description=custom_desc,
                        steps=steps,
                        icon=custom_icon,
                        auto_add_to_sidebar=add_to_sidebar
                    )
                    st.success(f"✅ Saved as shortcut: **{custom_icon} {custom_name}**")
                    st.balloons()
                    st.info("💡 Find it in the **⚡ Shortcuts** tab or sidebar!")
                    return True
    else:
        # Simple button version
        if st.button(
            f"💾 Save as Shortcut",
            key=button_key,
            help=f"Save '{pipeline_name}' as a reusable magic button",
            use_container_width=True
        ):
            shortcut_id = save_pipeline_as_shortcut(
                name=pipeline_name,
                description=pipeline_description,
                steps=steps,
                icon=icon,
                auto_add_to_sidebar=True
            )
            st.success(f"✅ Saved **{icon} {pipeline_name}** as a shortcut!")
            st.info("💡 Find it in the **⚡ Shortcuts** tab!")
            return True
    
    return False


def convert_workflow_to_steps(workflow_data: dict) -> list:
    """
    Convert a workflow execution log into shortcut steps.
    
    Args:
        workflow_data: Dict with workflow execution info
        
    Returns:
        list: List of step dicts formatted for shortcuts
    """
    steps = []
    
    for idx, step_data in enumerate(workflow_data.get('steps', [])):
        step = {
            'id': idx + 1,
            'type': step_data.get('type', 'generate'),
            'name': step_data.get('name', f'Step {idx + 1}'),
            'action': step_data.get('action', '/image'),
            'prompt_template': step_data.get('prompt', ''),
        }
        
        if 'output_var' in step_data:
            step['output_var'] = step_data['output_var']
        
        steps.append(step)
    
    return steps


def convert_chain_to_steps(chain_results: list) -> list:
    """
    Convert model chain results into shortcut steps.
    
    Args:
        chain_results: List of model outputs from chaining
        
    Returns:
        list: List of step dicts formatted for shortcuts
    """
    steps = []
    
    for idx, result in enumerate(chain_results):
        model_type = result.get('model_type', 'image')
        model_name = result.get('model', 'flux-pro')
        prompt = result.get('prompt', '')
        
        # Map model type to action
        action_map = {
            'image': '/image',
            'video': '/video',
            'text': '/python',  # or appropriate text command
            '3d': '/python',  # Could use custom 3D command if available
        }
        
        step = {
            'id': idx + 1,
            'type': 'generate',
            'name': f'{model_type.title()} Generation ({model_name})',
            'action': action_map.get(model_type, '/image'),
            'prompt_template': prompt,
        }
        
        if idx > 0:
            step['output_var'] = f'output_{idx}'
        
        steps.append(step)
    
    return steps


def convert_task_to_steps(task_data: dict) -> list:
    """
    Convert a completed task into shortcut steps.
    
    Args:
        task_data: Dict with task execution info
        
    Returns:
        list: List of step dicts formatted for shortcuts
    """
    steps = []
    
    task_type = task_data.get('type', 'generate')
    task_desc = task_data.get('description', '')
    
    # Create appropriate steps based on task type
    if task_type == 'generate_image':
        steps.append({
            'id': 1,
            'type': 'generate',
            'name': 'Generate Image',
            'action': '/image',
            'prompt_template': task_desc
        })
    elif task_type == 'generate_video':
        steps.append({
            'id': 1,
            'type': 'generate',
            'name': 'Generate Video',
            'action': '/video',
            'prompt_template': task_desc
        })
    elif task_type == 'social_post':
        steps.extend([
            {
                'id': 1,
                'type': 'ai',
                'name': 'Generate Post Content',
                'prompt_template': f'Create engaging social media post: {task_desc}'
            },
            {
                'id': 2,
                'type': 'post',
                'name': 'Post to Social Media',
                'platform': task_data.get('platform', 'twitter'),
                'action': 'post'
            }
        ])
    else:
        # Generic step
        steps.append({
            'id': 1,
            'type': 'ai',
            'name': task_type.replace('_', ' ').title(),
            'prompt_template': task_desc
        })
    
    return steps
