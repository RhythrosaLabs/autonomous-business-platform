"""
Helper functions for rendering dynamic UI controls based on model parameters
"""
import streamlit as st
from typing import Dict, Any, Optional


def render_model_parameters(model_ref: str, model_config: Dict, key_prefix: str = "pg") -> Dict[str, Any]:
    """
    Dynamically render UI controls for model parameters
    
    Args:
        model_ref: Model reference string (e.g., "luma/modify-video")
        model_config: Model configuration dict with parameters
        key_prefix: Prefix for session state keys to avoid conflicts
        
    Returns:
        Dict of parameter values ready to pass to model
    """
    parameters = model_config.get("parameters", {})
    if not parameters:
        return {}
    
    param_values = {}
    
    for param_name, param_config in parameters.items():
        param_type = param_config.get("type")
        required = param_config.get("required", False)
        default = param_config.get("default")
        help_text = param_config.get("help", "")
        
        # Generate unique key
        key = f"{key_prefix}_{model_ref.replace('/', '_')}_{param_name}"
        
        # Skip file uploads - handle separately
        if param_type == "file":
            continue
        
        # Render appropriate control based on type
        if param_type == "text":
            label = param_name.replace("_", " ").title()
            if required:
                label += " *"
            value = st.text_area(
                label,
                value=default if default else "",
                help=help_text,
                key=key,
                height=80 if param_name in ["prompt", "text"] else 100
            )
            if value:
                param_values[param_name] = value
                
        elif param_type == "slider":
            label = param_name.replace("_", " ").title()
            min_val = param_config.get("min", 0)
            max_val = param_config.get("max", 100)
            step = param_config.get("step", 1 if isinstance(min_val, int) else 0.1)
            value = st.slider(
                label,
                min_value=min_val,
                max_value=max_val,
                value=default if default is not None else min_val,
                step=step,
                help=help_text,
                key=key
            )
            param_values[param_name] = value
            
        elif param_type == "number":
            label = param_name.replace("_", " ").title()
            min_val = param_config.get("min", 0)
            max_val = param_config.get("max", 999999)
            value = st.number_input(
                label,
                min_value=min_val,
                max_value=max_val,
                value=default if default is not None else min_val,
                help=help_text,
                key=key
            )
            if value != 0 or param_name == "seed":  # Include seed even if 0
                param_values[param_name] = value
                
        elif param_type == "select":
            label = param_name.replace("_", " ").title()
            options = param_config.get("options", [])
            if options:
                default_idx = 0
                if default and default in options:
                    default_idx = options.index(default)
                value = st.selectbox(
                    label,
                    options=options,
                    index=default_idx,
                    help=help_text,
                    key=key
                )
                param_values[param_name] = value
                
        elif param_type == "checkbox":
            label = param_name.replace("_", " ").title()
            value = st.checkbox(
                label,
                value=default if default is not None else False,
                help=help_text,
                key=key
            )
            param_values[param_name] = value
    
    return param_values


def render_file_upload(param_name: str, param_config: Dict, key_prefix: str = "pg") -> Optional[Any]:
    """
    Render file upload control
    
    Args:
        param_name: Parameter name
        param_config: Parameter configuration
        key_prefix: Prefix for session state keys
        
    Returns:
        Uploaded file or None
    """
    required = param_config.get("required", False)
    help_text = param_config.get("help", "")
    
    label = param_name.replace("_", " ").title()
    if required:
        label += " *"
    
    # Determine file types based on parameter name
    if "video" in param_name.lower():
        file_types = ['mp4', 'mov', 'avi', 'webm']
    elif "audio" in param_name.lower():
        file_types = ['mp3', 'wav', 'ogg', 'm4a']
    elif "image" in param_name.lower() or "mask" in param_name.lower() or "logo" in param_name.lower():
        file_types = ['jpg', 'png', 'jpeg', 'webp']
    else:
        file_types = None
    
    key = f"{key_prefix}_{param_name}_upload"
    
    uploaded_file = st.file_uploader(
        label,
        type=file_types,
        help=help_text,
        key=key
    )
    
    return uploaded_file
