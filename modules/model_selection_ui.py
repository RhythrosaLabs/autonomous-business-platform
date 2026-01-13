"""
Model Selection UI Module
UI components for AI model selection and configuration
"""

import streamlit as st
from ai_model_manager import ModelFallbackManager, ModelPriority, VideoModel
import logging

logger = logging.getLogger(__name__)


def render_model_selection_ui():
    """
    Render the AI video model selection interface.
    
    Returns:
        dict: Model selection configuration
    """
    st.markdown("### 🤖 AI Video Model Selection")
    
    model_selection_mode = st.radio(
        "Selection Mode",
        ["🎯 Recommended (Auto)", "⚙️ Manual Selection", "🔄 Smart Fallback (Try Multiple)"],
        horizontal=True,
        key="module_model_selection_mode",
        help="Recommended uses AI to pick best model. Manual lets you choose. Smart Fallback tries multiple models until success."
    )
    
    
    config = {
        "mode": model_selection_mode,
        "ken_burns": False,
        "use_sora": False,
        "use_kling": False,
        "smart_fallback": False,
        "fallback_tier": "standard",
        "quality_threshold": 65
    }
    
    if model_selection_mode == "🎯 Recommended (Auto)":
        config.update(_render_recommended_mode())
        
    elif model_selection_mode == "⚙️ Manual Selection":
        config.update(_render_manual_mode())
        
    else:  # Smart Fallback
        config.update(_render_fallback_mode())
    
    return config


def _render_recommended_mode():
    """Render recommended (auto) model selection."""
    st.info("💡 AI will automatically select the best model based on your settings")
    
    rec_col1, rec_col2, rec_col3 = st.columns(3)
    with rec_col1:
        quality_priority = st.selectbox(
            "Quality Priority",
            ["Cinematic", "High", "Good", "Fast"],
            index=1,
            help="Higher quality = slower + more expensive"
        )
    with rec_col2:
        speed_priority = st.checkbox(
            "⚡ Speed Priority",
            value=False,
            help="Prioritize speed over quality"
        )
    with rec_col3:
        budget_level = st.selectbox(
            "Budget",
            ["Premium", "Standard", "Economy", "Free"],
            index=1,
            help="Premium = best quality, Free = Ken Burns only"
        )
    
    # Get recommendation
    manager = ModelFallbackManager()
    requirements = {
        "quality_needed": quality_priority.lower(),
        "speed_priority": speed_priority,
        "budget": budget_level.lower(),
        "duration": 10
    }
    
    recommended_model = manager.get_recommended_model(requirements)
    model_info = ModelPriority.MODEL_CAPABILITIES[recommended_model]
    
    st.success(f"🎬 Recommended: **{model_info['name']}**")
    st.caption(f"💡 {model_info['strengths']}")
    
    # Set flags
    return {
        "ken_burns": recommended_model.value == "ken_burns",
        "use_sora": recommended_model.value == "sora",
        "use_kling": recommended_model.value == "kling",
        "recommended_model": recommended_model.value
    }


def _render_manual_mode():
    """Render manual model selection."""
    video_col1, video_col2, video_col3 = st.columns(3)
    
    with video_col1:
        ken_burns = st.checkbox(
            "🎞️ Ken Burns Effect",
            value=True,
            help="Fast, free, reliable zoom/pan effects. Perfect for static product shots."
        )
        if ken_burns:
            st.caption("✅ FREE • ⚡ Instant • 🎯 Always works")
    
    with video_col2:
        use_sora = st.checkbox(
            "🎬 Sora-2 (OpenAI)",
            value=False,
            help="Premium cinematic AI video with realistic motion and complex scenes."
        )
        if use_sora:
            st.caption("⭐ Premium • 🎥 Cinematic • 💰 $$$")
    
    with video_col3:
        use_kling = st.checkbox(
            "✨ Kling AI",
            value=False,
            help="Creative animated video with smooth transitions and effects."
        )
        if use_kling:
            st.caption("⚡ Fast • 🎨 Creative • 💰 $$")
    
    # Show comparison table
    show_comparison = st.checkbox("📊 Show Model Comparison", value=False)
    if show_comparison:
        st.markdown("""
        | Model | Quality | Speed | Cost | Best For |
        |-------|---------|-------|------|----------|
        | **Ken Burns** | ⭐⭐⭐ | ⚡⚡⚡⚡⚡ | FREE | Product showcases, quick videos |
        | **Kling AI** | ⭐⭐⭐⭐ | ⚡⚡⚡⚡ | $$ | Creative animations, social media |
        | **Sora-2** | ⭐⭐⭐⭐⭐ | ⚡⚡ | $$$ | Cinematic commercials, professional ads |
        """)
    
    return {
        "ken_burns": ken_burns,
        "use_sora": use_sora,
        "use_kling": use_kling
    }


def _render_fallback_mode():
    """Render smart fallback mode."""
    st.info("🔄 Will try multiple models automatically until one succeeds")
    
    fallback_col1, fallback_col2 = st.columns(2)
    with fallback_col1:
        quality_tier = st.selectbox(
            "Quality Tier",
            ["Premium", "Standard", "Fast", "Free"],
            index=1,
            help="Determines which models to try and in what order"
        )
    with fallback_col2:
        quality_threshold = st.slider(
            "Min Quality Score",
            0, 100, 65, 5,
            help="Videos below this score will be regenerated"
        )
    
    # Show fallback order
    tier_key = quality_tier.lower()
    fallback_order = ModelPriority.QUALITY_TIERS.get(tier_key, [])
    
    st.caption("📋 Fallback Order:")
    for i, model in enumerate(fallback_order, 1):
        model_info = ModelPriority.MODEL_CAPABILITIES[model]
        st.caption(f"  {i}. {model_info['name']} → ", end="")
    st.caption("Done!")
    
    # Enable all models in fallback order
    return {
        "ken_burns": any(m.value == "ken_burns" for m in fallback_order),
        "use_sora": any(m.value == "sora" for m in fallback_order),
        "use_kling": any(m.value == "kling" for m in fallback_order),
        "smart_fallback": True,
        "fallback_tier": tier_key,
        "quality_threshold": quality_threshold
    }


def render_model_info_card(model: VideoModel):
    """
    Render detailed information card for a model.
    
    Args:
        model: VideoModel enum value
    """
    info = ModelPriority.MODEL_CAPABILITIES[model]
    
    with st.container():
        st.markdown(f"### {info['name']}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Quality", f"{info['quality']}/100")
        with col2:
            st.metric("Speed", f"{info['speed']}/100")
        with col3:
            st.metric("Cost", f"{info['cost']}/100")
        
        st.markdown(f"**Max Duration:** {info['max_duration']}s")
        st.markdown(f"**Features:** {', '.join(info['features'])}")
        st.success(f"**Strengths:** {info['strengths']}")
        st.warning(f"**Weaknesses:** {info['weaknesses']}")


def get_selected_models(config: dict) -> list:
    """
    Get list of selected models from config.
    
    Args:
        config: Model selection configuration
        
    Returns:
        list: List of selected model names
    """
    models = []
    if config.get("ken_burns"):
        models.append("ken_burns")
    if config.get("use_sora"):
        models.append("sora")
    if config.get("use_kling"):
        models.append("kling")
    return models
