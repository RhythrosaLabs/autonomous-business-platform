"""
Quality Settings UI Module
UI components for video quality and platform settings
"""

import streamlit as st
from typing import Dict
import logging

logger = logging.getLogger(__name__)


def render_quality_settings_ui():
    """
    Render video quality settings interface.
    
    Returns:
        dict: Quality settings configuration
    """
    st.markdown("### ⚙️ Video Quality Settings")
    
    quality_col1, quality_col2, quality_col3 = st.columns(3)
    
    with quality_col1:
        video_resolution = st.selectbox(
            "Resolution",
            ["720p", "1080p", "4K"],
            index=1,
            help="Output video resolution (1080p recommended for most platforms)"
        )
    
    with quality_col2:
        video_fps = st.selectbox(
            "Frame Rate (FPS)",
            [24, 30, 60],
            index=1,
            help="24fps=cinematic, 30fps=standard, 60fps=smooth"
        )
    
    with quality_col3:
        video_bitrate = st.selectbox(
            "Bitrate Quality",
            ["Low", "Medium", "High"],
            index=1,
            help="Low=smaller files, High=better quality"
        )
    
    return {
        "resolution": video_resolution,
        "fps": video_fps,
        "bitrate": video_bitrate
    }


def render_platform_presets_ui():
    """
    Render platform presets interface.
    
    Returns:
        dict: Platform preset configuration
    """
    st.markdown("### 📱 Platform Presets")
    
    preset_col1, preset_col2 = st.columns(2)
    
    with preset_col1:
        platform_preset = st.selectbox(
            "Quick Preset",
            ["Custom", "YouTube (16:9, 1080p, 30fps)", "Instagram (1:1, 1080p, 30fps)", 
             "TikTok (9:16, 1080p, 30fps)", "Twitter (16:9, 720p, 30fps)"],
            help="Apply platform-optimized settings automatically"
        )
    
    with preset_col2:
        batch_export = st.checkbox(
            "🎯 Batch Export All Formats",
            value=False,
            help="Generate videos for all major platforms at once (YouTube, Instagram, TikTok, Twitter)"
        )
        if batch_export:
            st.caption("✅ Will generate 4 optimized videos + ZIP download")
    
    # Apply preset settings
    preset_settings = None
    if platform_preset != "Custom":
        preset_map = {
            "YouTube (16:9, 1080p, 30fps)": {"aspect": "16:9", "res": "1080p", "fps": 30},
            "Instagram (1:1, 1080p, 30fps)": {"aspect": "1:1", "res": "1080p", "fps": 30},
            "TikTok (9:16, 1080p, 30fps)": {"aspect": "9:16", "res": "1080p", "fps": 30},
            "Twitter (16:9, 720p, 30fps)": {"aspect": "16:9", "res": "720p", "fps": 30}
        }
        preset_settings = preset_map.get(platform_preset)
        if preset_settings:
            st.info(f"📌 Preset applied: {platform_preset}")
    
    return {
        "platform_preset": platform_preset,
        "batch_export": batch_export,
        "preset_settings": preset_settings
    }


def render_prompt_templates_ui():
    """
    Render prompt templates interface.
    
    Returns:
        dict: Prompt template configuration
    """
    from prompt_templates import PromptTemplateLibrary, PromptEnhancer
    
    st.markdown("### 📝 Prompt Engineering")
    
    use_prompt_templates = st.checkbox(
        "🎨 Use Professional Prompt Templates",
        value=True,
        help="Use optimized prompt templates for consistent, high-quality results"
    )
    
    if use_prompt_templates:
        template_lib = PromptTemplateLibrary()
        
        template_col1, template_col2 = st.columns(2)
        
        with template_col1:
            video_template = st.selectbox(
                "Video Style Template",
                ["product_showcase", "lifestyle_commercial", "quick_promo", "cinematic_story"],
                format_func=lambda x: template_lib.get_template("video", x)["name"],
                help="Professional prompt template for consistent quality"
            )
        
        with template_col2:
            prompt_quality_level = st.selectbox(
                "Prompt Quality Level",
                ["medium", "high", "ultra"],
                index=1,
                help="Adds quality modifiers to prompts"
            )
        
        # Show template preview
        show_template_preview = st.checkbox("👁️ Show Template Preview", value=False)
        if show_template_preview:
            template_data = template_lib.get_template("video", video_template)
            st.code(template_data["template"][:500] + "...", language="text")
            st.caption(f"Variables: {', '.join(template_data['variables'][:5])}...")
        
        return {
            "use_templates": True,
            "video_template": video_template,
            "quality_level": prompt_quality_level
        }
    else:
        return {
            "use_templates": False,
            "video_template": None,
            "quality_level": "high"
        }


def render_advanced_video_settings():
    """
    Render advanced video settings (Voice, Music, etc).
    
    Returns:
        dict: Advanced settings configuration
    """
    st.markdown("### 🎤 Voice & Tone")
    
    voice_col1, voice_col2 = st.columns(2)
    
    with voice_col1:
        video_voice_style = st.selectbox(
            "Voice Style",
            ["Professional", "Luxury", "Friendly", "Energetic"],
            help="Voice style for narration/voiceover"
        )
    
    with voice_col2:
        video_ad_tone = st.selectbox(
            "Ad Tone",
            ["Professional & Trustworthy", "Exciting & Dynamic", "Warm & Friendly", 
             "Luxury & Elegant", "Fun & Playful"],
            help="Overall tone and energy of the video"
        )
    
    st.markdown("### 🎵 Background Music")
    
    music_col1, music_col2 = st.columns(2)
    
    with music_col1:
        music_style = st.selectbox(
            "Music Genre",
            ["Cinematic", "Electronic", "Upbeat", "Ambient", "Corporate", "Hip Hop", "Jazz"],
            help="Style of background music"
        )
    
    with music_col2:
        music_prompt = st.text_input(
            "Music Description (optional)",
            placeholder="e.g., uplifting, dramatic, mysterious...",
            help="Additional description for music generation"
        )
    
    return {
        "voice_style": video_voice_style,
        "ad_tone": video_ad_tone,
        "music_style": music_style,
        "music_prompt": music_prompt
    }


def get_combined_quality_config():
    """
    Get all quality-related configurations in one call.
    
    Returns:
        dict: Combined configuration dictionary
    """
    config = {}
    
    config["quality"] = render_quality_settings_ui()
    config["platform"] = render_platform_presets_ui()
    config["prompts"] = render_prompt_templates_ui()
    config["advanced"] = render_advanced_video_settings()
    
    return config


def apply_preset_to_quality(quality_config: Dict, preset_settings: Dict):
    """
    Apply preset settings to quality configuration.
    
    Args:
        quality_config: Current quality settings
        preset_settings: Preset to apply
        
    Returns:
        dict: Updated quality configuration
    """
    if preset_settings:
        quality_config["resolution"] = preset_settings.get("res", quality_config["resolution"])
        quality_config["fps"] = preset_settings.get("fps", quality_config["fps"])
        
    return quality_config
