import streamlit as st
from datetime import datetime as dt
import logging
from app.services.platform_integrations import tracked_replicate_run
from app.services.platform_helpers import _get_replicate_token

# Configure logger
logger = logging.getLogger(__name__)

def render_brand_templates_tab():
    """
    Renders the Brand Templates tab (Tab 15).
    """
    st.markdown('<div class="main-header">🎨 Brand Templates</div>', unsafe_allow_html=True)
    st.markdown("### Create and manage brand guidelines for consistent styling")
    
    # AI Brand Builder Section
    with st.expander("🤖 AI Brand Builder", expanded=True):
        st.markdown("**Let AI help you create a complete brand identity**")
        
        ai_brand_col1, ai_brand_col2 = st.columns(2)
        
        with ai_brand_col1:
            brand_business = st.text_input("What's your business/product?", 
                placeholder="e.g., Eco-friendly yoga accessories", key="ai_brand_business")
            brand_values = st.text_input("Core values (comma-separated)", 
                placeholder="e.g., sustainability, wellness, simplicity", key="ai_brand_values")
            brand_audience = st.text_input("Target audience", 
                placeholder="e.g., Health-conscious millennials", key="ai_brand_audience")
        
        with ai_brand_col2:
            brand_competitors = st.text_input("Main competitors (optional)", 
                placeholder="e.g., Lululemon, Alo Yoga", key="ai_brand_competitors")
            brand_mood = st.selectbox("Desired mood/feeling", 
                ["Calm & Peaceful", "Bold & Energetic", "Luxurious & Premium", "Fun & Playful", 
                 "Professional & Trustworthy", "Innovative & Modern", "Warm & Friendly", "Edgy & Rebellious"],
                key="ai_brand_mood")
        
        ai_brand_buttons = st.columns(4)
        
        with ai_brand_buttons[0]:
            if st.button("🎨 Generate Color Palette", use_container_width=True):
                if brand_business:
                    try:
                        replicate_token = _get_replicate_token()
                    except ValueError:
                        replicate_token = None
                    if replicate_token:
                        with st.spinner("🎨 Creating your perfect color palette..."):
                            try:
                                import replicate
                                client = replicate.Client(api_token=replicate_token)
                                color_prompt = f"""You are a brand color expert. Create a 5-color palette for:

Business: {brand_business}
Values: {brand_values or 'Not specified'}
Mood: {brand_mood}
Audience: {brand_audience or 'General'}

Provide exactly 5 HEX colors with their names and psychological meaning:
Format each as: #HEXCODE - Color Name - Why it works

Make colors work harmoniously together. Be specific about the hex codes."""
                                response = tracked_replicate_run(client, "meta/meta-llama-3-8b-instruct", {"prompt": color_prompt, "max_tokens": 400}, operation_name="Color Palette Generation")
                                st.session_state['ai_color_palette'] = "".join(response) if isinstance(response, list) else response
                            except Exception as e:
                                st.error(f"Failed: {e}")
                    else:
                        st.warning("Add API key in Settings")
                else:
                    st.warning("Enter your business first")
        
        with ai_brand_buttons[1]:
            if st.button("✍️ Generate Brand Voice", use_container_width=True):
                if brand_business:
                    try:
                        replicate_token = _get_replicate_token()
                    except ValueError:
                        replicate_token = None
                    if replicate_token:
                        with st.spinner("✍️ Crafting your brand voice..."):
                            try:
                                import replicate
                                client = replicate.Client(api_token=replicate_token)
                                voice_prompt = f"""Create a brand voice guide for:

Business: {brand_business}
Values: {brand_values or 'Not specified'}
Mood: {brand_mood}
Audience: {brand_audience or 'General'}
Competitors: {brand_competitors or 'Not specified'}

Provide:
1. VOICE DESCRIPTION (2 sentences)
2. TONE KEYWORDS (5 adjectives)
3. DO's (3 bullet points of how to write)
4. DON'Ts (3 bullet points of what to avoid)
5. SAMPLE TAGLINE (1 catchy line)
6. SAMPLE SOCIAL POST (1 example)

Be specific and actionable."""
                                response = tracked_replicate_run(client, "meta/meta-llama-3-8b-instruct", {"prompt": voice_prompt, "max_tokens": 500}, operation_name="Brand Voice Generation")
                                st.session_state['ai_brand_voice'] = "".join(response) if isinstance(response, list) else response
                            except Exception as e:
                                st.error(f"Failed: {e}")
                    else:
                        st.warning("Add API key in Settings")
                else:
                    st.warning("Enter your business first")
        
        with ai_brand_buttons[2]:
            if st.button("🏷️ Generate Brand Name Ideas", use_container_width=True):
                if brand_business:
                    try:
                        replicate_token = _get_replicate_token()
                    except ValueError:
                        replicate_token = None
                    if replicate_token:
                        with st.spinner("🏷️ Brainstorming brand names..."):
                            try:
                                import replicate
                                client = replicate.Client(api_token=replicate_token)
                                name_prompt = f"""Generate 10 unique brand name ideas for:

Business: {brand_business}
Values: {brand_values or 'Not specified'}
Mood: {brand_mood}
Audience: {brand_audience or 'General'}

Requirements:
- Easy to pronounce and remember
- Available as .com domain (check-worthy)
- Works for social media handles
- Mix of: invented words, compound words, metaphors

For each name provide:
Name - Brief explanation of meaning/vibe

Be creative and unique!"""
                                response = tracked_replicate_run(client, "meta/meta-llama-3-8b-instruct", {"prompt": name_prompt, "max_tokens": 400}, operation_name="Brand Name Ideas")
                                st.session_state['ai_brand_names'] = "".join(response) if isinstance(response, list) else response
                            except Exception as e:
                                st.error(f"Failed: {e}")
                    else:
                        st.warning("Add API key in Settings")
                else:
                    st.warning("Enter your business first")
        
        with ai_brand_buttons[3]:
            if st.button("📋 Generate Full Brand Kit", use_container_width=True, type="primary"):
                if brand_business:
                    try:
                        replicate_token = _get_replicate_token()
                    except ValueError:
                        replicate_token = None
                    if replicate_token:
                        with st.spinner("📋 Creating comprehensive brand kit..."):
                            try:
                                import replicate
                                client = replicate.Client(api_token=replicate_token)
                                full_prompt = f"""Create a complete brand identity kit for:

Business: {brand_business}
Values: {brand_values or 'Professional, Quality'}
Mood: {brand_mood}
Audience: {brand_audience or 'General consumers'}
Competitors: {brand_competitors or 'Market leaders'}

Provide a structured brand kit with:

## BRAND ESSENCE
- Mission (1 sentence)
- Vision (1 sentence)
- Tagline

## COLOR PALETTE
- Primary Color: #HEX - name
- Secondary Color: #HEX - name
- Accent Color: #HEX - name
- Background: #HEX
- Text: #HEX

## TYPOGRAPHY
- Headline Font Style
- Body Font Style

## VOICE & TONE
- 3 voice characteristics
- Do's and Don'ts

## VISUAL STYLE
- Image style description
- Icon style
- Overall aesthetic

## SAMPLE CONTENT
- Sample headline
- Sample social post
- Sample CTA button text

Be specific with hex codes and font suggestions."""
                                response = tracked_replicate_run(client, "meta/meta-llama-3-70b-instruct", {"prompt": full_prompt, "max_tokens": 1000}, operation_name="Full Brand Kit Generation")
                                st.session_state['ai_full_brand_kit'] = "".join(response) if isinstance(response, list) else response
                            except Exception as e:
                                st.error(f"Failed: {e}")
                    else:
                        st.warning("Add API key in Settings")
                else:
                    st.warning("Enter your business first")
        
        # Display AI Results
        if st.session_state.get('ai_color_palette'):
            st.markdown("#### 🎨 AI-Generated Color Palette")
            st.markdown(st.session_state['ai_color_palette'])
        
        if st.session_state.get('ai_brand_voice'):
            st.markdown("#### ✍️ AI-Generated Brand Voice")
            st.markdown(st.session_state['ai_brand_voice'])
        
        if st.session_state.get('ai_brand_names'):
            st.markdown("#### 🏷️ AI-Generated Brand Names")
            st.markdown(st.session_state['ai_brand_names'])
        
        if st.session_state.get('ai_full_brand_kit'):
            st.markdown("---")
            st.markdown("### 📋 Complete AI Brand Kit")
            st.markdown(st.session_state['ai_full_brand_kit'])
            
            # Save brand kit button
            if st.button("💾 Save as Brand Template", use_container_width=True):
                # Extract and save to templates
                new_template = {
                    'id': f"ai_brand_{dt.now().strftime('%Y%m%d%H%M%S')}",
                    'name': brand_business[:30] if brand_business else "AI Brand",
                    'description': f"AI-generated brand for {brand_business}",
                    'ai_generated': True,
                    'full_kit': st.session_state['ai_full_brand_kit'],
                    'created_at': dt.now().isoformat()
                }
                if 'custom_brand_templates' not in st.session_state:
                    st.session_state['custom_brand_templates'] = []
                st.session_state['custom_brand_templates'].append(new_template)
                st.success("✅ Brand template saved!")
    
    st.markdown("---")
    
    # Import brand templates module
    try:
        from brand_templates import render_template_library, get_active_template, PRESET_TEMPLATES
        
        # Show active template at top
        active_template = get_active_template()
        if active_template:
            st.success(f"🎨 Active Brand: **{active_template.name}** - All generations will follow this brand's style")
            if st.button("❌ Clear Active Brand", key="clear_brand_main"):
                if 'active_brand_template' in st.session_state:
                    del st.session_state['active_brand_template']
                st.rerun()
        else:
            st.info("💡 Select a brand template below to apply consistent styling across all generations")
        
        st.markdown("---")
        
        # Template library
        render_template_library()
        
    except ImportError as e:
        st.error(f"Brand templates module not available: {e}")
        
        # Fallback: Simple brand selection
        st.markdown("### Quick Brand Presets")
        
        presets = [
            {"name": "Minimalist Modern", "colors": "#000000,#666666,#FF6B6B", "style": "Clean, minimal, professional"},
            {"name": "Bold & Vibrant", "colors": "#FF3366,#6C5CE7,#00D9FF", "style": "Energetic, dynamic, youthful"},
            {"name": "Organic Natural", "colors": "#4A6741,#8B7355,#C9A86C", "style": "Earthy, sustainable, organic"},
            {"name": "Luxury Premium", "colors": "#C9A227,#1A1A2E,#D4AF37", "style": "Elegant, exclusive, high-end"},
        ]
        
        cols = st.columns(4)
        for idx, preset in enumerate(presets):
            with cols[idx]:
                st.markdown(f"**{preset['name']}**")
                color_bar = " ".join([f'<span style="display:inline-block;width:15px;height:15px;background:{c};border-radius:2px;margin:1px;"></span>' 
                                     for c in preset['colors'].split(',')])
                st.markdown(color_bar, unsafe_allow_html=True)
                st.caption(preset['style'])
                if st.button("Use", key=f"use_preset_{idx}", use_container_width=True):
                    st.session_state['active_brand_preset'] = preset
                    st.success(f"✅ Using {preset['name']}")
