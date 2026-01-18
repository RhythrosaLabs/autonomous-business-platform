import streamlit as st
from datetime import datetime as dt
import logging
import asyncio
import os

# Configure logger
logger = logging.getLogger(__name__)

try:
    from app.services.shortcuts_manager import (
        ShortcutsManager,
        init_shortcuts,
        add_shortcut,
        update_shortcut,
        delete_shortcut,
        save_shortcuts,
        load_shortcuts,
        export_shortcuts,
        import_shortcuts,
        get_shortcut_css,
        render_icon_picker,
        render_style_picker,
        render_size_picker,
        SHORTCUT_ICONS,
        BUTTON_STYLES,
        BUTTON_SIZES,
        SHORTCUT_CATEGORIES
    )
    SHORTCUTS_MANAGER_AVAILABLE = True
    # Create global manager instance
    shortcuts_mgr = ShortcutsManager()
except ImportError:
    SHORTCUTS_MANAGER_AVAILABLE = False
    shortcuts_mgr = None
    def init_shortcuts():
        if 'magic_shortcuts' not in st.session_state:
            st.session_state.magic_shortcuts = []
    def get_shortcut_css(): return ""
    SHORTCUT_ICONS = ["⚡", "🚀", "🎯", "💰", "🔥", "✨", "💎", "🎨", "📦", "🛒"]
    BUTTON_STYLES = {}
    BUTTON_SIZES = {}
    SHORTCUT_CATEGORIES = {}

try:
    from app.services.platform_helpers import _get_replicate_token
except ImportError:
    def _get_replicate_token(): return None

async def execute_shortcut_in_background(task_id, shortcut):
    """
    Execute a shortcut in the background, updating task progress.
    This runs independently and persists across page navigation.
    """
    try:
        from app.services.background_task_manager import BackgroundTaskManager
        from app.services.otto_engine import get_slash_processor
        from app.services.api_service import ReplicateAPI
        
        task_mgr = BackgroundTaskManager()
        task_mgr.update_task(task_id, status='running', progress=0.0)
        
        results = []
        context = {'description': shortcut.get('description', '')}
        
        # Get Replicate API token
        replicate_token = _get_replicate_token()
        if not replicate_token:
            task_mgr.update_task(task_id, status='failed', error='Replicate API token not configured')
            return
        
        replicate_api = ReplicateAPI(api_token=replicate_token)
        slash_processor = get_slash_processor(replicate_api)
        
        total_steps = len(shortcut['steps'])
        
        for step_idx, step in enumerate(shortcut['steps']):
            step_name = step.get('name', f'Step {step_idx + 1}')
            current_step = step_idx + 1
            progress = current_step / total_steps
            
            task_mgr.update_task(
                task_id, 
                status='running', 
                progress=progress,
                current_step=current_step
            )
            
            try:
                if step['type'] == 'generate':
                    action = step.get('action', '')
                    prompt = step.get('prompt_template', '').format(**context)
                    
                    result = await slash_processor.execute(f"{action} {prompt}")
                    
                    if result.get('success'):
                        results.append(result)
                        # Store output for chaining
                        if 'output_var' in step:
                            output_url = result.get('url') or (result.get('artifacts', [{}])[0].get('url') if result.get('artifacts') else None)
                            context[step['output_var']] = output_url
                        
                        task_mgr.update_task(task_id, result=result)
                    else:
                        error_msg = result.get('error', 'Generation failed')
                        task_mgr.update_task(task_id, error=f"Step {current_step}: {error_msg}")
                
                elif step['type'] == 'post':
                    # Posting step
                    platform = step.get('platform', step.get('action', 'twitter')).lower()
                    content = step.get('content', step.get('caption', ''))
                    image_path = context.get('image_url') or context.get('product_image')
                    
                    if 'twitter' in platform and image_path:
                        from app.services.ai_twitter_poster import AITwitterPoster
                        poster = AITwitterPoster(headless=True)
                        
                        # Download image if URL
                        if image_path.startswith('http'):
                            import tempfile, requests
                            response = requests.get(image_path)
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                                tmp.write(response.content)
                                local_image = tmp.name
                        else:
                            local_image = image_path
                        
                        success = await poster.post_to_twitter(local_image, content)
                        result = {'step': step_name, 'status': 'success' if success else 'uncertain', 'platform': platform}
                    else:
                        result = {'step': step_name, 'status': 'configured', 'platform': platform}
                    
                    results.append(result)
                    task_mgr.update_task(task_id, result=result)
                
                elif step['type'] == 'ai':
                    # AI processing
                    prompt = step.get('prompt_template', '')
                    
                    from app.services.chat_assistant import ChatAssistant
                    chat_assistant = ChatAssistant()
                    
                    ai_response = await chat_assistant.process_message(prompt, [])
                    
                    if ai_response:
                        result = {'step': step_name, 'status': 'success', 'response': ai_response[:200]}
                        context['ai_output'] = ai_response
                    else:
                        result = {'step': step_name, 'status': 'failed'}
                    
                    results.append(result)
                    task_mgr.update_task(task_id, result=result)
                    
            except Exception as step_error:
                task_mgr.update_task(task_id, error=f"Step {current_step} error: {str(step_error)}")
        
        # Mark as completed
        task_mgr.update_task(task_id, status='completed', progress=1.0)
        
    except Exception as e:
        logger.error(f"Background execution error: {e}")
        try:
            from app.services.background_task_manager import BackgroundTaskManager
            task_mgr = BackgroundTaskManager()
            task_mgr.update_task(task_id, status='failed', error=str(e))
        except:
            pass

def render_shortcuts_tab():
    """
    Renders the Shortcuts tab (Tab 1).
    """
    st.markdown('<div class="main-header">⚡ Shortcuts</div>', unsafe_allow_html=True)
    st.markdown("### Create Magic Buttons for Any Workflow")
    st.caption("Describe what you want to happen and we'll create a one-click button for it")
    
    # Initialize shortcuts from disk (persistent storage) - only on first load
    if 'magic_shortcuts' not in st.session_state:
        init_shortcuts()
        if shortcuts_mgr:
            loaded_shortcuts = shortcuts_mgr.load_shortcuts()
            if loaded_shortcuts:
                st.session_state.magic_shortcuts = loaded_shortcuts
    
    if 'shortcut_results' not in st.session_state:
        st.session_state.shortcut_results = {}
    
    # Inject custom CSS for button styles
    if SHORTCUTS_MANAGER_AVAILABLE:
        st.markdown(get_shortcut_css(), unsafe_allow_html=True)
    
    # Shortcut tabs
    shortcut_tabs = st.tabs(["✨ Create Shortcut", "⚡ My Shortcuts", "📚 Preset Library", "📜 History", "📤 Import/Export"])
    
    # ==========================================
    # TAB: CREATE SHORTCUT
    # ==========================================
    with shortcut_tabs[0]:
        st.markdown("### ✨ Make a Magic Button")
        st.markdown("Describe what you want your button to do in plain English. Our AI will convert it into a one-click shortcut.")
        
        # Input area
        shortcut_description = st.text_area(
            "What should this button do?",
            placeholder="Example: Generate a product image, create 3 social media posts, and schedule them for tomorrow at 9am",
            height=120,
            key="shortcut_description_input"
        )
        
        st.markdown("---")
        st.markdown("#### 🎨 Customize Your Button")
        
        col_name, col_icon = st.columns([3, 1])
        with col_name:
            shortcut_name = st.text_input("Button Name", placeholder="e.g., Quick Product Launch", key="shortcut_name_input")
        
        # Enhanced icon picker with more options
        with col_icon:
            if SHORTCUTS_MANAGER_AVAILABLE:
                shortcut_icon = st.selectbox(
                    "Icon", 
                    SHORTCUT_ICONS,
                    key="shortcut_icon_select",
                    help="Choose from 100+ icons"
                )
            else:
                shortcut_icon = st.selectbox("Icon", ["⚡", "🚀", "🎯", "💰", "🔥", "✨", "💎", "🎨", "📦", "🛒"], key="shortcut_icon_select")
        
        col_cat, col_style, col_size = st.columns(3)
        with col_cat:
            if SHORTCUTS_MANAGER_AVAILABLE:
                shortcut_category = st.selectbox(
                    "Category",
                    list(SHORTCUT_CATEGORIES.keys()),
                    key="shortcut_category_select"
                )
            else:
                shortcut_category = st.selectbox(
                    "Category",
                    ["🎨 Content Creation", "📱 Social Media", "📦 Products", "📧 Marketing", "🔄 Automation"],
                    key="shortcut_category_select"
                )
        
        with col_style:
            if SHORTCUTS_MANAGER_AVAILABLE:
                style_options = list(BUTTON_STYLES.keys())
                style_labels = [BUTTON_STYLES[s]["label"] for s in style_options]
                style_idx = st.selectbox(
                    "Button Style",
                    range(len(style_options)),
                    format_func=lambda i: style_labels[i],
                    key="shortcut_style_select"
                )
                shortcut_color = style_options[style_idx]
            else:
                shortcut_color = st.selectbox(
                    "Button Style",
                    ["primary", "success", "warning", "danger", "info", "secondary"],
                    format_func=lambda x: x.title(),
                    key="shortcut_color_select"
                )
        
        with col_size:
            if SHORTCUTS_MANAGER_AVAILABLE:
                size_options = list(BUTTON_SIZES.keys())
                size_labels = [BUTTON_SIZES[s]["label"] for s in size_options]
                size_idx = st.selectbox(
                    "Button Size",
                    range(len(size_options)),
                    format_func=lambda i: size_labels[i],
                    index=1,  # Default to medium
                    key="shortcut_size_select"
                )
                shortcut_size = size_options[size_idx]
            else:
                shortcut_size = "medium"
        
        # Button preview
        st.markdown("**Preview:**")
        preview_col1, preview_col2 = st.columns([1, 3])
        with preview_col1:
            # Show preview based on style
            preview_style = ""
            if "gradient_purple" in shortcut_color:
                preview_style = "background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;"
            elif "gradient_blue" in shortcut_color:
                preview_style = "background: linear-gradient(135deg, #5ee7df 0%, #b490ca 100%); color: white;"
            elif "gradient_green" in shortcut_color:
                preview_style = "background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white;"
            elif "gradient_orange" in shortcut_color:
                preview_style = "background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white;"
            elif shortcut_color == "primary":
                preview_style = "background-color: #667eea; color: white;"
            elif shortcut_color == "success":
                preview_style = "background-color: #28a745; color: white;"
            elif shortcut_color == "warning":
                preview_style = "background-color: #ffc107; color: #212529;"
            elif shortcut_color == "danger":
                preview_style = "background-color: #dc3545; color: white;"
            elif shortcut_color == "info":
                preview_style = "background-color: #17a2b8; color: white;"
            elif shortcut_color == "outline":
                preview_style = "background-color: transparent; border: 2px solid #667eea; color: #667eea;"
            else:
                preview_style = "background-color: #6c757d; color: white;"
            
            # Size padding
            if shortcut_size == "small":
                size_style = "padding: 4px 8px; font-size: 0.8em;"
            elif shortcut_size == "large":
                size_style = "padding: 12px 24px; font-size: 1.2em;"
            elif shortcut_size == "xl":
                size_style = "padding: 16px 32px; font-size: 1.4em;"
            else:
                size_style = "padding: 8px 16px; font-size: 1em;"
            
            st.markdown(f"""
            <div style="
                display: inline-block;
                {preview_style}
                {size_style}
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
            ">
                {shortcut_icon} {shortcut_name or 'Button Name'}
            </div>
            """, unsafe_allow_html=True)
        
        # Advanced options expander
        with st.expander("⚙️ Advanced Options"):
            col_adv1, col_adv2 = st.columns(2)
            with col_adv1:
                shortcut_confirm = st.checkbox("Require confirmation before running", value=False, key="shortcut_confirm_check")
                shortcut_notify = st.checkbox("Show notification when complete", value=True, key="shortcut_notify_check")
                shortcut_sidebar_only = st.checkbox("Show only in sidebar (not in main tab)", value=False, key="shortcut_sidebar_only")
            with col_adv2:
                shortcut_log = st.checkbox("Log results to history", value=True, key="shortcut_log_check")
                shortcut_chain = st.checkbox("Allow chaining with other shortcuts", value=True, key="shortcut_chain_check")
                shortcut_favorite = st.checkbox("⭐ Add to favorites", value=False, key="shortcut_favorite_check")
            
            # Keyboard shortcut
            shortcut_hotkey = st.text_input(
                "Keyboard Shortcut (optional)",
                placeholder="e.g., Ctrl+Shift+1 or Cmd+Alt+S",
                key="shortcut_hotkey_input",
                help="Press keys combination - works when viewing shortcuts"
            )
        
        # Make Magic Button
        st.markdown("---")
        if st.button("🪄 Make Magic Button", type="primary", use_container_width=True, key="create_magic_btn"):
            if not shortcut_description:
                st.error("Please describe what the button should do")
            elif not shortcut_name:
                st.error("Please give your button a name")
            else:
                with st.spinner("🔮 Creating your magic button..."):
                    try:
                        from app.services.api_service import ReplicateAPI
                        
                        # Use AI to analyze and break down the workflow
                        replicate_token = _get_replicate_token()
                        steps = []
                        
                        if replicate_token:
                            try:
                                replicate_api = ReplicateAPI(replicate_token)
                                analysis_prompt = f"""Analyze this workflow request and break it into clear, actionable steps:

Request: \"{shortcut_description}\"

Provide a numbered list of specific steps needed to complete this workflow. Each step should be:
- Clear and actionable
- In order of execution
- Specific about what needs to be done

Example format:
1. Generate product image using FLUX model
2. Create 3 social media posts with captions
3. Schedule posts for tomorrow at 9am on Instagram, Twitter, and Facebook

Now analyze the request above and provide the steps:"""
                                
                                analysis = replicate_api.generate_text(analysis_prompt, max_tokens=500, temperature=0.7)
                                
                                # Parse AI response into steps
                                import re
                                lines = analysis.strip().split('\n')
                                step_id = 1
                                
                                for line in lines:
                                    line = line.strip()
                                    if not line or len(line) < 10:
                                        continue
                                    # Remove numbering if present
                                    line = re.sub(r'^[\d\.\)\-]+\s*', '', line)
                                    if line:
                                        steps.append({
                                            'id': step_id,
                                            'type': 'ai',
                                            'action': 'otto_chat',
                                            'name': line[:50],
                                            'description': line,
                                            'prompt_template': line
                                        })
                                        step_id += 1
                            except Exception as ai_error:
                                logger.warning(f"AI analysis failed: {ai_error}, using fallback")
                        
                        # Fallback: Simple keyword detection if AI fails
                        if not steps:
                            desc_lower = shortcut_description.lower()
                            patterns = {
                                'image': ['image', 'picture', 'photo', 'graphic', 'design', 'artwork'],
                                'video': ['video', 'clip', 'animation', 'motion'],
                                'music': ['music', 'song', 'audio', 'soundtrack', 'tune'],
                                'speech': ['speech', 'voice', 'narration', 'voiceover', 'tts'],
                                'post_twitter': ['twitter', 'tweet', 'x.com'],
                                'post_instagram': ['instagram', 'ig', 'insta'],
                                'post_youtube': ['youtube', 'yt'],
                                'printify': ['printify', 'print on demand', 'pod', 't-shirt', 'merch'],
                                'shopify': ['shopify', 'store', 'ecommerce'],
                                'email': ['email', 'newsletter', 'mailing'],
                                'schedule': ['schedule', 'tomorrow', 'later', 'timing', 'at ', 'am', 'pm'],
                                '3d': ['3d', 'model', 'three dimensional'],
                                'ad': ['ad', 'advertisement', 'promo', 'commercial'],
                                'blog': ['blog', 'article', 'post', 'content'],
                            }
                            
                            detected = []
                            for intent, keywords in patterns.items():
                                if any(kw in desc_lower for kw in keywords):
                                    detected.append(intent)
                            
                            # Build steps based on detected intents
                            step_id = 1
                            for intent in detected:
                                if intent == 'image':
                                    steps.append({
                                        'id': step_id,
                                        'type': 'generate',
                                        'action': '/image',
                                        'name': 'Generate Image',
                                        'prompt_template': '{description}',
                                        'output_var': 'generated_image'
                                    })
                                    step_id += 1
                                elif intent == 'video':
                                    steps.append({
                                        'id': step_id,
                                        'type': 'generate',
                                        'action': '/video',
                                        'name': 'Generate Video',
                                        'prompt_template': '{description}',
                                        'input_var': 'generated_image',
                                        'output_var': 'generated_video'
                                    })
                                    step_id += 1
                                elif intent == 'music':
                                    steps.append({
                                        'id': step_id,
                                        'type': 'generate',
                                        'action': '/music',
                                        'name': 'Generate Music',
                                        'prompt_template': 'background music for {description}',
                                        'output_var': 'generated_music'
                                    })
                                    step_id += 1
                                elif intent == 'speech':
                                    steps.append({
                                        'id': step_id,
                                        'type': 'generate',
                                        'action': '/speak',
                                        'name': 'Generate Speech',
                                        'prompt_template': '{description}',
                                        'output_var': 'generated_speech'
                                    })
                                    step_id += 1
                                elif intent == 'post_twitter':
                                    steps.append({
                                        'id': step_id,
                                        'type': 'post',
                                        'action': 'twitter',
                                        'name': 'Post to Twitter',
                                        'input_var': 'generated_image',
                                        'caption_template': '{description}'
                                    })
                                    step_id += 1
                                elif intent == 'post_instagram':
                                    steps.append({
                                        'id': step_id,
                                        'type': 'post',
                                        'action': 'instagram',
                                        'name': 'Post to Instagram',
                                        'input_var': 'generated_image',
                                        'caption_template': '{description}'
                                    })
                                    step_id += 1
                                elif intent == 'printify':
                                    steps.append({
                                        'id': step_id,
                                        'type': 'upload',
                                        'action': 'printify',
                                        'name': 'Upload to Printify',
                                        'input_var': 'generated_image'
                                    })
                                    step_id += 1
                                elif intent == 'schedule':
                                    steps.append({
                                        'id': step_id,
                                        'type': 'schedule',
                                        'action': 'schedule',
                                        'name': 'Schedule Task',
                                        'time_template': 'next available slot'
                                    })
                                    step_id += 1
                                elif intent == '3d':
                                    steps.append({
                                        'id': step_id,
                                        'type': 'generate',
                                        'action': '/3d',
                                        'name': 'Generate 3D Model',
                                        'prompt_template': '{description}',
                                        'output_var': 'generated_3d'
                                    })
                                    step_id += 1
                                elif intent == 'ad':
                                    steps.append({
                                        'id': step_id,
                                        'type': 'generate',
                                        'action': '/ad',
                                        'name': 'Generate Ad',
                                        'prompt_template': 'advertisement for {description}',
                                        'output_var': 'generated_ad'
                                    })
                                    step_id += 1
                                elif intent == 'blog':
                                    steps.append({
                                        'id': step_id,
                                        'type': 'generate',
                                        'action': '/blog',
                                        'name': 'Generate Blog Post',
                                        'prompt_template': '{description}',
                                        'output_var': 'generated_blog'
                                    })
                                    step_id += 1
                        
                        # If no specific intents detected, create a generic step
                        if not steps:
                            steps.append({
                                'id': 1,
                                'type': 'ai',
                                'action': 'otto_chat',
                                'name': 'AI Processing',
                                'prompt_template': shortcut_description
                            })
                        
                        # Create the shortcut object
                        import uuid
                        shortcut = {
                            'id': str(uuid.uuid4())[:8],
                            'name': shortcut_name,
                            'icon': shortcut_icon,
                            'description': shortcut_description,
                            'category': shortcut_category,
                            'color': shortcut_color.split()[0].lower() if ' ' in shortcut_color else shortcut_color.lower(),
                            'gradient': shortcut_color,  # Store full gradient name for styling
                            'steps': steps,
                            'settings': {
                                'confirm': shortcut_confirm,
                                'notify': shortcut_notify,
                                'log': shortcut_log,
                                'chain': shortcut_chain,
                                'sidebar_only': shortcut_sidebar_only,
                                'favorite': shortcut_favorite
                            },
                            'hotkey': shortcut_hotkey,
                            'in_sidebar': False,
                            'created_at': dt.now().isoformat(),
                            'run_count': 0,
                            'last_run': None
                        }
                        
                        # Save to persistent storage AND session state
                        if shortcuts_mgr:
                            shortcuts_mgr.save_shortcut(shortcut)
                            st.session_state.magic_shortcuts = shortcuts_mgr.load_shortcuts()
                        else:
                            st.session_state.magic_shortcuts.append(shortcut)
                        
                        st.success(f"✅ Created magic button: **{shortcut_icon} {shortcut_name}**")
                        st.info(f"🔗 {len(steps)} step(s) detected: {', '.join([s['name'] for s in steps])}")
                        
                        # Force reload to show new shortcut
                        st.rerun()
                        
                        # Show preview
                        st.markdown("### Preview:")
                        btn_style = {
                            'primary': 'primary',
                            'success': 'secondary',
                            'warning': 'secondary',
                            'danger': 'secondary',
                            'info': 'secondary',
                            'secondary': 'secondary'
                        }
                        st.button(f"{shortcut_icon} {shortcut_name}", type=btn_style.get(shortcut['color'], 'primary'), disabled=True)
                        
                        st.balloons()
                        
                    except Exception as e:
                        st.error(f"Error creating shortcut: {str(e)}")
    
    # ==========================================
    # TAB: MY SHORTCUTS
    # ==========================================
    with shortcut_tabs[1]:
        st.markdown("### ⚡ Your Magic Buttons")
        
        # Deduplicate shortcuts by ID (keep first occurrence)
        if st.session_state.magic_shortcuts:
            seen_ids = set()
            deduped = []
            for shortcut in st.session_state.magic_shortcuts:
                shortcut_id = shortcut.get('id')
                if shortcut_id and shortcut_id not in seen_ids:
                    seen_ids.add(shortcut_id)
                    deduped.append(shortcut)
            st.session_state.magic_shortcuts = deduped
        
        if not st.session_state.magic_shortcuts:
            st.info("🪄 No shortcuts yet! Create your first magic button in the 'Create Shortcut' tab.")
        else:
            # Group by category
            categories = {}
            for shortcut in st.session_state.magic_shortcuts:
                cat = shortcut.get('category', '🔧 Utilities')
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(shortcut)
            
            # Gradient mappings for styling
            gradient_styles = {
                'Purple Aurora': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                'Ocean Blue': 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                'Sunset Orange': 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
                'Forest Green': 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
                'Ruby Red': 'linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%)',
                'Golden Yellow': 'linear-gradient(135deg, #f7971e 0%, #ffd200 100%)',
                'Deep Pink': 'linear-gradient(135deg, #ee0979 0%, #ff6a00 100%)',
                'Cyber Teal': 'linear-gradient(135deg, #00c9ff 0%, #92fe9d 100%)',
                'Midnight Blue': 'linear-gradient(135deg, #2c3e50 0%, #4ca1af 100%)',
                'Electric Violet': 'linear-gradient(135deg, #a855f7 0%, #6366f1 100%)',
                'Neon Lime': 'linear-gradient(135deg, #b4ec51 0%, #429321 100%)',
                'Cool Gray': 'linear-gradient(135deg, #636fa4 0%, #e8cbc0 100%)',
                'Fire Orange': 'linear-gradient(135deg, #ff5f6d 0%, #ffc371 100%)',
                'Ice Blue': 'linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 100%)',
                'Dark Mode': 'linear-gradient(135deg, #232526 0%, #414345 100%)'
            }
            
            for category, shortcuts in categories.items():
                st.markdown(f"#### {category}")
                
                # Display shortcuts in grid
                cols = st.columns(3)
                for idx, shortcut in enumerate(shortcuts):
                    with cols[idx % 3]:
                        with st.container():
                            # Get gradient style
                            gradient = shortcut.get('gradient', 'Purple Aurora')
                            bg_gradient = gradient_styles.get(gradient, gradient_styles['Purple Aurora'])
                            
                            st.markdown(f"""
                            <div style="border: none; border-radius: 12px; padding: 15px; margin-bottom: 10px; background: {bg_gradient}; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
                                <h4 style="margin: 0; color: white; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">{shortcut['icon']} {shortcut['name']}</h4>
                                <p style="font-size: 0.85em; color: rgba(255,255,255,0.9); margin: 5px 0;">{shortcut['description'][:80]}{'...' if len(shortcut['description']) > 80 else ''}</p>
                                <p style="font-size: 0.75em; color: rgba(255,255,255,0.7);">📊 Run {shortcut['run_count']} times • {len(shortcut['steps'])} steps{' • ⌨️ ' + shortcut.get('hotkey', '') if shortcut.get('hotkey') else ''}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            col_run, col_edit, col_sidebar, col_del = st.columns([2, 1, 1, 1])
                            with col_run:
                                run_clicked = st.button(f"▶️ Run", key=f"my_shortcuts_run_{shortcut['id']}", use_container_width=True, type="primary")
                            
                            with col_edit:
                                if st.button("✏️", key=f"my_shortcuts_edit_{shortcut['id']}", use_container_width=True):
                                    st.session_state[f'editing_shortcut_{shortcut["id"]}'] = True
                                    st.rerun()
                            
                            # Show edit dialog if editing
                            if st.session_state.get(f'editing_shortcut_{shortcut["id"]}', False):
                                st.markdown("---")
                                st.markdown(f"### ✏️ Edit: {shortcut['name']}")
                                
                                with st.form(key=f"edit_form_{shortcut['id']}"):
                                    edit_col1, edit_col2 = st.columns([3, 1])
                                    with edit_col1:
                                        new_name = st.text_input("Name", value=shortcut['name'])
                                    with edit_col2:
                                        new_icon = st.text_input("Icon", value=shortcut['icon'], max_chars=2)
                                    
                                    new_desc = st.text_area("Description", value=shortcut['description'], height=80)
                                    new_gradient = st.selectbox(
                                        "Color Theme",
                                        list(gradient_styles.keys()),
                                        index=list(gradient_styles.keys()).index(shortcut.get('gradient', 'Purple Aurora'))
                                    )
                                    
                                    col_save, col_cancel = st.columns(2)
                                    with col_save:
                                        if st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary"):
                                            # Update shortcut
                                            shortcut['name'] = new_name
                                            shortcut['icon'] = new_icon
                                            shortcut['description'] = new_desc
                                            shortcut['gradient'] = new_gradient
                                            
                                            # Update in session state
                                            for s in st.session_state.magic_shortcuts:
                                                if s['id'] == shortcut['id']:
                                                    s.update(shortcut)
                                                    break
                                            
                                            # Persist to disk
                                            if shortcuts_mgr:
                                                shortcuts_mgr.save_shortcut(shortcut)
                                            
                                            st.session_state[f'editing_shortcut_{shortcut["id"]}'] = False
                                            st.success("✅ Shortcut updated!")
                                            st.rerun()
                                    
                                    with col_cancel:
                                        if st.form_submit_button("❌ Cancel", use_container_width=True):
                                            st.session_state[f'editing_shortcut_{shortcut["id"]}'] = False
                                            st.rerun()
                            
                            with col_sidebar:
                                in_sidebar = shortcut.get('in_sidebar', False)
                                sidebar_icon = "📌" if in_sidebar else "➕"
                                if st.button(sidebar_icon, key=f"my_shortcuts_sidebar_{shortcut['id']}", use_container_width=True, help="Add to/Remove from sidebar"):
                                    # Toggle the flag
                                    new_sidebar_state = not in_sidebar
                                    shortcut['in_sidebar'] = new_sidebar_state
                                    
                                    # Update in session state
                                    for s in st.session_state.magic_shortcuts:
                                        if s['id'] == shortcut['id']:
                                            s['in_sidebar'] = new_sidebar_state
                                            break
                                    
                                    # Persist to disk
                                    if shortcuts_mgr:
                                        shortcuts_mgr.save_shortcut(shortcut)
                                    
                                    st.success(f"{'✅ Added to' if new_sidebar_state else '❌ Removed from'} sidebar!")
                                    st.rerun()
                            
                            with col_del:
                                if st.button("🗑️", key=f"my_shortcuts_del_{shortcut['id']}", use_container_width=True):
                                    # Delete from persistent storage AND session state
                                    if shortcuts_mgr:
                                        shortcuts_mgr.delete_shortcut(shortcut['id'])
                                    
                                    # Also remove from session state
                                    st.session_state.magic_shortcuts = [
                                        s for s in st.session_state.magic_shortcuts 
                                        if s['id'] != shortcut['id']
                                    ]
                                    st.success("🗑️ Shortcut deleted!")
                                    st.rerun()
                            
                            # Execute shortcut if Run button was clicked (outside columns context)
                            if run_clicked:
                                # Check if user wants background execution
                                bg_option = st.checkbox(
                                    "🌐 Run in background (continue while navigating other pages)", 
                                    value=True,
                                    key=f"bg_option_{shortcut['id']}",
                                    help="Enable to keep automation running even when you navigate away"
                                )
                                
                                if bg_option:
                                    # Execute in background using BackgroundTaskManager
                                    try:
                                        from app.services.background_task_manager import BackgroundTaskManager
                                        import threading
                                        
                                        task_mgr = BackgroundTaskManager()
                                        
                                        task_id = task_mgr.create_task(
                                            name=f"{shortcut['icon']} {shortcut['name']}",
                                            task_type='shortcut',
                                            total_steps=len(shortcut['steps']),
                                            params={
                                                'shortcut_id': shortcut['id'],
                                                'shortcut': shortcut
                                            }
                                        )
                                        
                                        # Start background execution in separate thread
                                        def run_async_task():
                                            asyncio.run(execute_shortcut_in_background(task_id, shortcut))
                                        
                                        thread = threading.Thread(target=run_async_task, daemon=True)
                                        thread.start()
                                        
                                        st.success(f"✅ Started in background! Task ID: {task_id}")
                                        st.info("💡 Check the progress indicator at the top of the page. You can navigate away and it will keep running.")
                                        
                                        with st.expander("📋 View background task details"):
                                            st.json({
                                                'task_id': task_id,
                                                'name': shortcut['name'],
                                                'steps': len(shortcut['steps']),
                                                'status': 'running'
                                            })
                                            
                                        # Auto-refresh to show progress
                                        import time
                                        time.sleep(1)
                                        st.rerun()
                                        
                                    except ImportError as ie:
                                        st.warning(f"⚠️ Background task manager not available: {ie}. Running in foreground instead...")
                                        bg_option = False
                                    except Exception as e:
                                        st.error(f"❌ Failed to start background task: {e}")
                                        bg_option = False
                                
                                if not bg_option:
                                    # Execute the shortcut with beautiful card-based progress display (foreground)
                                    st.markdown(f"### 🚀 Running: {shortcut['name']}")
                                    st.markdown("---")
                                    
                                    try:
                                        results = []
                                        context = {'description': shortcut['description']}
                                        
                                        from app.services.otto_engine import get_slash_processor
                                        from app.services.api_service import ReplicateAPI
                                        
                                        # Get Replicate API token
                                        replicate_token = _get_replicate_token()
                                        if not replicate_token:
                                            st.error("❌ Replicate API token not configured. Please add REPLICATE_API_TOKEN to your .env file.")
                                            st.stop()
                                        
                                        replicate_api = ReplicateAPI(api_token=replicate_token)
                                        slash_processor = get_slash_processor(replicate_api)
                                        
                                        # Create grid layout for step progress (max 3 columns)
                                        num_steps = len(shortcut['steps'])
                                        cols_per_row = min(num_steps, 3)
                                        
                                        for step_idx, step in enumerate(shortcut['steps']):
                                            # Create new row every 3 steps
                                            if step_idx % 3 == 0:
                                                step_cols = st.columns(3)
                                            
                                            col_idx = step_idx % 3
                                            step_name = step.get('name', 'Step')
                                            
                                            # Show processing card
                                            with step_cols[col_idx]:
                                                st.markdown(f"""
                                                <div style="
                                                    padding: 15px;
                                                    border-radius: 10px;
                                                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                                    color: white;
                                                    margin-bottom: 15px;
                                                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                                                    min-height: 120px;
                                                ">
                                                    <div style="font-size: 1.5em; margin-bottom: 8px;">⏳</div>
                                                    <div style="font-weight: 700; font-size: 0.95em; margin-bottom: 5px;">{step_name[:50]}</div>
                                                    <div style="font-size: 0.75em; opacity: 0.85;">Processing...</div>
                                                    </div>
                                                    """, unsafe_allow_html=True)
                                                
                                                # Execute step
                                                if step['type'] == 'generate':
                                                    action = step.get('action', '')
                                                    prompt = step.get('prompt_template', '').format(**context)
                                                    
                                                    import asyncio
                                                    try:
                                                        result = asyncio.run(slash_processor.execute(f"{action} {prompt}"))
                                                        
                                                        if result.get('success'):
                                                            results.append(result)
                                                            # Store output for chaining
                                                            if 'output_var' in step:
                                                                output_url = result.get('url') or (result.get('artifacts', [{}])[0].get('url') if result.get('artifacts') else None)
                                                                context[step['output_var']] = output_url
                                                            
                                                            # Update to success card
                                                            with step_cols[col_idx]:
                                                                st.markdown(f"""
                                                                <div style="
                                                                    padding: 15px;
                                                                    border-radius: 10px;
                                                                    background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
                                                                    color: white;
                                                                margin-bottom: 15px;
                                                                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                                                                min-height: 120px;
                                                            ">
                                                                <div style="font-size: 1.5em; margin-bottom: 8px;">✅</div>
                                                                <div style="font-weight: 700; font-size: 0.95em; margin-bottom: 5px;">{step_name[:50]}</div>
                                                                <div style="font-size: 0.75em; opacity: 0.85;">Completed!</div>
                                                            </div>
                                                            """, unsafe_allow_html=True)
                                                            
                                                            # Display media if available
                                                            if result.get('type') == 'media':
                                                                for artifact in result.get('artifacts', []):
                                                                    art_type = artifact.get('type', '')
                                                                    url = artifact.get('url', '')
                                                                    if art_type == 'image' and url:
                                                                        st.image(url, use_container_width=True)
                                                                    elif art_type == 'video' and url:
                                                                        st.video(url)
                                                        else:
                                                            error_msg = result.get('error', 'Unknown error')
                                                            results.append({'step': step_name, 'status': 'failed', 'error': error_msg})
                                                            with step_cols[col_idx]:
                                                                st.markdown(f"""
                                                                <div style="
                                                                    padding: 15px;
                                                                    border-radius: 10px;
                                                                    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
                                                                    color: white;
                                                                    margin-bottom: 15px;
                                                                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                                                                    min-height: 120px;
                                                                ">
                                                                    <div style="font-size: 1.5em; margin-bottom: 8px;">⚠️</div>
                                                                    <div style="font-weight: 700; font-size: 0.95em; margin-bottom: 5px;">{step_name[:50]}</div>
                                                                    <div style="font-size: 0.7em; opacity: 0.85;">{error_msg[:60]}</div>
                                                                </div>
                                                                """, unsafe_allow_html=True)
                                                    except Exception as gen_error:
                                                        results.append({'step': step_name, 'status': 'error', 'error': str(gen_error)})
                                                        with step_cols[col_idx]:
                                                            st.markdown(f"""
                                                            <div style="
                                                                padding: 15px;
                                                                border-radius: 10px;
                                                                background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
                                                                color: white;
                                                                margin-bottom: 15px;
                                                                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                                                                min-height: 120px;
                                                            ">
                                                                <div style="font-size: 1.5em; margin-bottom: 8px;">❌</div>
                                                                <div style="font-weight: 700; font-size: 0.95em; margin-bottom: 5px;">Failed</div>
                                                                <div style="font-size: 0.7em; opacity: 0.85;">{str(gen_error)[:60]}</div>
                                                            </div>
                                                            """, unsafe_allow_html=True)
                                                
                                                elif step['type'] == 'post':
                                                    # Posting step
                                                    platform = step.get('platform', step.get('action', 'twitter')).lower()
                                                    content = step.get('content', step.get('caption', ''))
                                                    image_path = context.get('image_url') or context.get('product_image')
                                                    
                                                    try:
                                                        if 'twitter' in platform and image_path:
                                                            from app.services.ai_twitter_poster import AITwitterPoster
                                                            poster = AITwitterPoster(headless=True)
                                                            import asyncio
                                                            
                                                            # Download image if URL
                                                            if image_path.startswith('http'):
                                                                import tempfile, requests
                                                                response = requests.get(image_path)
                                                                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                                                                    tmp.write(response.content)
                                                                    local_image = tmp.name
                                                            else:
                                                                local_image = image_path
                                                            
                                                            success = asyncio.run(poster.post_to_twitter(local_image, content))
                                                            status = "success" if success else "uncertain"
                                                        else:
                                                            status = "configured"
                                                        
                                                        results.append({'step': step_name, 'status': status, 'platform': platform})
                                                        with step_cols[col_idx]:
                                                            st.markdown(f"""
                                                            <div style="
                                                                padding: 15px;
                                                                border-radius: 10px;
                                                                background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
                                                                color: #333;
                                                                margin-bottom: 15px;
                                                                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                                                                min-height: 120px;
                                                            ">
                                                                <div style="font-size: 1.5em; margin-bottom: 8px;">📤</div>
                                                                <div style="font-weight: 700; font-size: 0.95em; margin-bottom: 5px;">{step_name[:50]}</div>
                                                                <div style="font-size: 0.75em; opacity: 0.75;">Posted to {platform.title()}</div>
                                                            </div>
                                                            """, unsafe_allow_html=True)
                                                    except Exception as e:
                                                        results.append({'step': step_name, 'status': 'pending'})
                                                        with step_cols[col_idx]:
                                                            st.markdown(f"""
                                                            <div style="
                                                                padding: 15px;
                                                                border-radius: 10px;
                                                                background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
                                                                color: #333;
                                                                margin-bottom: 15px;
                                                                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                                                                min-height: 120px;
                                                            ">
                                                                <div style="font-size: 1.5em; margin-bottom: 8px;">ℹ️</div>
                                                                <div style="font-weight: 700; font-size: 0.95em; margin-bottom: 5px;">Ready</div>
                                                                <div style="font-size: 0.7em; opacity: 0.75;">Configure credentials</div>
                                                            </div>
                                                            """, unsafe_allow_html=True)
                                                
                                                elif step['type'] == 'ai':
                                                    # Generic AI processing through Otto's chat assistant
                                                    prompt = step.get('prompt_template', '')
                                                    
                                                    with step_cols[col_idx]:
                                                        st.markdown(f"""
                                                        <div style="
                                                            padding: 15px;
                                                            border-radius: 8px;
                                                            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                                                            color: white;
                                                            margin-bottom: 10px;
                                                            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                                                        ">
                                                            <div style="font-size: 1.2em; margin-bottom: 5px;">🤖</div>
                                                            <div style="font-weight: 600;">AI Processing...</div>
                                                        </div>
                                                        """, unsafe_allow_html=True)
                                                    
                                                    try:
                                                        # Use Otto's chat assistant for AI processing
                                                        if 'chat_assistant' not in st.session_state:
                                                            from app.services.chat_assistant import ChatAssistant
                                                            st.session_state.chat_assistant = ChatAssistant()
                                                        
                                                        chat_assistant = st.session_state.chat_assistant
                                                        import asyncio
                                                        
                                                        # Process through Otto
                                                        ai_response = asyncio.run(chat_assistant.process_message(prompt, []))
                                                        
                                                        if ai_response:
                                                            results.append({'step': step_name, 'status': 'success', 'response': ai_response[:200]})
                                                            context['ai_output'] = ai_response
                                                            
                                                            with step_cols[col_idx]:
                                                                st.markdown(f"""
                                                                <div style="
                                                                    padding: 15px;
                                                                    border-radius: 8px;
                                                                    background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                                                                    color: white;
                                                                    margin-bottom: 10px;
                                                                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                                                                ">
                                                                    <div style="font-size: 1.2em; margin-bottom: 5px;">✅</div>
                                                                    <div style="font-weight: 600;">{step_name[:40]}</div>
                                                                </div>
                                                                """, unsafe_allow_html=True)
                                                        else:
                                                            results.append({'step': step_name, 'status': 'failed'})
                                                            with step_cols[col_idx]:
                                                                st.markdown(f"""
                                                                <div style="
                                                                    padding: 15px;
                                                                    border-radius: 8px;
                                                                    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%);
                                                                    color: white;
                                                                    margin-bottom: 10px;
                                                                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                                                                ">
                                                                    <div style="font-size: 1.2em; margin-bottom: 5px;">⚠️</div>
                                                                    <div style="font-weight: 600;">Processing Issue</div>
                                                                </div>
                                                                """, unsafe_allow_html=True)
                                                    except Exception as ai_ex:
                                                        results.append({'step': step_name, 'status': 'error', 'error': str(ai_ex)})
                                                        with step_cols[col_idx]:
                                                            st.markdown(f"""
                                                            <div style="
                                                                    padding: 15px;
                                                                    border-radius: 8px;
                                                                    background: linear-gradient(135deg, #ffa751 0%, #ffe259 100%);
                                                                    color: #333;
                                                                    margin-bottom: 10px;
                                                                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                                                                ">
                                                                    <div style="font-size: 1.2em; margin-bottom: 5px;">ℹ️</div>
                                                                    <div style="font-weight: 600;">Service Unavailable</div>
                                                                </div>
                                                                """, unsafe_allow_html=True)
                                            
                                            # All steps completed - show summary
                                            st.markdown("---")
                                            st.markdown(f"""
                                            <div style="
                                                padding: 25px;
                                                border-radius: 15px;
                                                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                                                color: white;
                                                text-align: center;
                                                box-shadow: 0 6px 20px rgba(0,0,0,0.2);
                                                margin: 20px 0;
                                            ">
                                                <div style="font-size: 3em; margin-bottom: 10px;">🎉</div>
                                            <h2 style="margin: 10px 0; font-weight: 700;">{shortcut['name']} Complete!</h2>
                                            <p style="font-size: 1.1em; opacity: 0.9; margin: 10px 0;">All {len(shortcut['steps'])} steps executed successfully</p>
                                        </div>
                                        """, unsafe_allow_html=True)
                                        
                                        # Update shortcut stats
                                        shortcut['run_count'] += 1
                                        shortcut['last_run'] = dt.now().isoformat()
                                        
                                        # Update in session state
                                        for s in st.session_state.magic_shortcuts:
                                            if s['id'] == shortcut['id']:
                                                s['run_count'] = shortcut['run_count']
                                                s['last_run'] = shortcut['last_run']
                                                break
                                        
                                        # Persist to disk
                                        if shortcuts_mgr:
                                            shortcuts_mgr.save_shortcut(shortcut)
                                        
                                        # Store results
                                        if shortcut['settings'].get('log'):
                                            if 'shortcut_history' not in st.session_state:
                                                st.session_state.shortcut_history = []
                                            st.session_state.shortcut_history.append({
                                                'shortcut': shortcut['name'],
                                                'timestamp': dt.now().isoformat(),
                                                'results': results
                                            })
                                        
                                        if shortcut['settings'].get('notify'):
                                            st.balloons()
                                    
                                    except Exception as e:
                                        st.error(f"❌ Error running shortcut: {str(e)}")
                                        import traceback
                                        st.code(traceback.format_exc())
                
                st.markdown("---")
    
    # ==========================================
    # TAB: PRESET LIBRARY
    # ==========================================
    with shortcut_tabs[2]:
        st.markdown("### 📚 Preset Shortcuts Library")
        st.markdown("Ready-to-use magic buttons for common tasks")
        
        # Preset shortcuts organized by category
        preset_shortcuts = {
            "🎨 Content Creation": [
                {
                    'id': 'preset_quick_product',
                    'name': 'Quick Product Image',
                    'icon': '🎨',
                    'description': 'Generate a professional product image with AI',
                    'steps': [{'id': 1, 'type': 'generate', 'action': '/image', 'name': 'Generate Product Image', 'prompt_template': 'professional product photography, {description}, studio lighting, white background'}]
                },
                {
                    'id': 'preset_social_pack',
                    'name': 'Social Media Pack',
                    'icon': '📱',
                    'description': 'Generate images optimized for all social platforms',
                    'steps': [
                        {'id': 1, 'type': 'generate', 'action': '/image', 'name': 'Instagram Square', 'prompt_template': '{description}, square format, instagram style'},
                        {'id': 2, 'type': 'generate', 'action': '/image', 'name': 'Twitter Header', 'prompt_template': '{description}, wide banner format'},
                        {'id': 3, 'type': 'generate', 'action': '/image', 'name': 'Pinterest Pin', 'prompt_template': '{description}, vertical tall format, pinterest style'}
                    ]
                },
                {
                    'id': 'preset_video_ad',
                    'name': 'Quick Video Ad',
                    'icon': '🎬',
                    'description': 'Create a short promotional video from a description',
                    'steps': [
                        {'id': 1, 'type': 'generate', 'action': '/image', 'name': 'Generate Visual', 'prompt_template': '{description}, cinematic, promotional', 'output_var': 'base_image'},
                        {'id': 2, 'type': 'generate', 'action': '/video', 'name': 'Animate to Video', 'prompt_template': 'subtle cinematic motion, {description}', 'input_var': 'base_image'}
                    ]
                }
            ],
            "📱 Social Media": [
                {
                    'id': 'preset_tweet_visual',
                    'name': 'Tweet with Visual',
                    'icon': '🐦',
                    'description': 'Generate an image and post to Twitter',
                    'steps': [
                        {'id': 1, 'type': 'generate', 'action': '/image', 'name': 'Generate Image', 'prompt_template': '{description}', 'output_var': 'tweet_image'},
                        {'id': 2, 'type': 'post', 'action': 'twitter', 'name': 'Post to Twitter', 'input_var': 'tweet_image'}
                    ]
                },
                {
                    'id': 'preset_content_calendar',
                    'name': 'Week of Content',
                    'icon': '📅',
                    'description': 'Generate 7 days of social media content',
                    'steps': [
                        {'id': 1, 'type': 'generate', 'action': '/image', 'name': 'Monday Post', 'prompt_template': 'motivational monday, {description}'},
                        {'id': 2, 'type': 'generate', 'action': '/image', 'name': 'Wednesday Post', 'prompt_template': 'wisdom wednesday, {description}'},
                        {'id': 3, 'type': 'generate', 'action': '/image', 'name': 'Friday Post', 'prompt_template': 'feel good friday, {description}'}
                    ]
                }
            ],
            "📦 E-Commerce": [
                {
                    'id': 'preset_product_launch',
                    'name': 'Product Launch Kit',
                    'icon': '🚀',
                    'description': 'Generate product image, video, and social posts',
                    'steps': [
                        {'id': 1, 'type': 'generate', 'action': '/image', 'name': 'Product Hero Image', 'prompt_template': 'hero product shot, {description}, premium quality', 'output_var': 'hero_image'},
                        {'id': 2, 'type': 'generate', 'action': '/video', 'name': 'Product Video', 'prompt_template': 'product showcase, smooth rotation, {description}'},
                        {'id': 3, 'type': 'generate', 'action': '/ad', 'name': 'Launch Ad', 'prompt_template': 'launch announcement, {description}, exciting'}
                    ]
                },
                {
                    'id': 'preset_pod_design',
                    'name': 'POD Design Generator',
                    'icon': '👕',
                    'description': 'Create a print-on-demand ready design',
                    'steps': [
                        {'id': 1, 'type': 'generate', 'action': '/image', 'name': 'Generate Design', 'prompt_template': 't-shirt design, {description}, transparent background, vector style'}
                    ]
                }
            ],
            "🎵 Audio & Video": [
                {
                    'id': 'preset_podcast_intro',
                    'name': 'Podcast Intro',
                    'icon': '🎙️',
                    'description': 'Generate intro music and voiceover',
                    'steps': [
                        {'id': 1, 'type': 'generate', 'action': '/music', 'name': 'Intro Music', 'prompt_template': 'podcast intro music, upbeat, professional, 10 seconds'},
                        {'id': 2, 'type': 'generate', 'action': '/speak', 'name': 'Intro Voiceover', 'prompt_template': 'Welcome to {description}'}
                    ]
                },
                {
                    'id': 'preset_promo_video',
                    'name': 'Promo Video Bundle',
                    'icon': '🎥',
                    'description': 'Create video with music and voiceover',
                    'steps': [
                        {'id': 1, 'type': 'generate', 'action': '/image', 'name': 'Generate Visual', 'prompt_template': '{description}, cinematic', 'output_var': 'visual'},
                        {'id': 2, 'type': 'generate', 'action': '/video', 'name': 'Create Video', 'prompt_template': 'cinematic motion, {description}'},
                        {'id': 3, 'type': 'generate', 'action': '/music', 'name': 'Background Music', 'prompt_template': 'promotional background music, uplifting'}
                    ]
                }
            ]
        }
        
        for category, presets in preset_shortcuts.items():
            st.markdown(f"#### {category}")
            
            cols = st.columns(3)
            for idx, preset in enumerate(presets):
                with cols[idx % 3]:
                    with st.container():
                        st.markdown(f"""
                        <div style="border: 1px solid #444; border-radius: 10px; padding: 15px; margin-bottom: 10px;">
                            <h4 style="margin: 0;">{preset['icon']} {preset['name']}</h4>
                            <p style="font-size: 0.85em; color: #888; margin: 5px 0;">{preset['description']}</p>
                            <p style="font-size: 0.75em; color: #666;">📋 {len(preset['steps'])} steps</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col_add, col_preview = st.columns(2)
                        with col_add:
                            if st.button("➕ Add", key=f"add_preset_{preset['id']}", use_container_width=True):
                                # Check if already added
                                existing_ids = [s['id'] for s in st.session_state.magic_shortcuts]
                                if preset['id'] not in existing_ids:
                                    import uuid
                                    new_shortcut = preset.copy()
                                    new_shortcut['id'] = str(uuid.uuid4())[:8]
                                    new_shortcut['category'] = category
                                    new_shortcut['color'] = 'primary'
                                    new_shortcut['gradient'] = 'Purple Aurora'
                                    new_shortcut['settings'] = {'confirm': False, 'notify': True, 'log': True, 'chain': True}
                                    new_shortcut['created_at'] = dt.now().isoformat()
                                    new_shortcut['run_count'] = 0
                                    new_shortcut['last_run'] = None
                                    # Save to persistent storage AND session state
                                    if shortcuts_mgr:
                                        shortcuts_mgr.save_shortcut(new_shortcut)
                                        st.session_state.magic_shortcuts = shortcuts_mgr.load_shortcuts()
                                    else:
                                        st.session_state.magic_shortcuts.append(new_shortcut)
                                    st.success(f"✅ Added {preset['name']}")
                                    st.rerun()
                                else:
                                    st.warning("Already added")
                        
                        with col_preview:
                            if st.button("👁️ View", key=f"view_preset_{preset['id']}", use_container_width=True):
                                st.session_state[f'viewing_preset_{preset["id"]}'] = True
                        
                        if st.session_state.get(f'viewing_preset_{preset["id"]}'):
                            st.markdown("**Steps:**")
                            for step in preset['steps']:
                                st.markdown(f"• {step['name']}")
    
    # ==========================================
    # TAB: HISTORY
    # ==========================================
    with shortcut_tabs[3]:
        st.markdown("### 📜 Run History")
        
        if 'shortcut_history' not in st.session_state:
            st.session_state.shortcut_history = []
        
        if not st.session_state.shortcut_history:
            st.info("No history yet. Run a shortcut to see results here.")
        else:
            if st.button("🗑️ Clear History", key="clear_shortcut_history"):
                st.session_state.shortcut_history = []
                st.rerun()
            
            for entry in reversed(st.session_state.shortcut_history[-20:]):
                with st.expander(f"🕐 {entry['timestamp']} - {entry['shortcut']}", expanded=False):
                    for result in entry['results']:
                        status_icon = "✅" if result.get('status') == 'success' or result.get('success') else "⚠️"
                        st.markdown(f"{status_icon} **{result.get('step', 'Step')}**")
                        if result.get('url'):
                            st.markdown(f"[View Output]({result['url']})")
    
    # ==========================================
    # TAB: IMPORT/EXPORT
    # ==========================================
    with shortcut_tabs[4]:
        st.markdown("### 📤 Import / Export Shortcuts")
        
        col_ex, col_im = st.columns(2)
        
        with col_ex:
            st.markdown("#### Export")
            st.markdown("Save your shortcuts to a file to share or backup.")
            
            if st.button("📦 Export All Shortcuts", key="export_shortcuts_btn"):
                if shortcuts_mgr:
                    export_data = shortcuts_mgr.export_shortcuts()
                    st.download_button(
                        "📥 Download JSON",
                        export_data,
                        f"magic_shortcuts_{dt.now().strftime('%Y%m%d')}.json",
                        mime="application/json"
                    )
                else:
                    import json
                    export_data = json.dumps(st.session_state.magic_shortcuts, indent=2)
                    st.download_button(
                        "📥 Download JSON",
                        export_data,
                        f"magic_shortcuts_{dt.now().strftime('%Y%m%d')}.json",
                        mime="application/json"
                    )
        
        with col_im:
            st.markdown("#### Import")
            st.markdown("Load shortcuts from a JSON file.")
            
            uploaded_file = st.file_uploader("Choose JSON file", type=['json'], key="import_shortcuts_file")
            if uploaded_file is not None:
                if st.button("📥 Import Shortcuts", key="import_shortcuts_btn"):
                    try:
                        import json
                        content = uploaded_file.read().decode('utf-8')
                        shortcuts_data = json.loads(content)
                        
                        if isinstance(shortcuts_data, list):
                            count = 0
                            for s in shortcuts_data:
                                # Basic validation
                                if 'name' in s and 'steps' in s:
                                    # Check if ID exists
                                    existing_ids = [ex['id'] for ex in st.session_state.magic_shortcuts]
                                    if s.get('id') not in existing_ids:
                                        if shortcuts_mgr:
                                            shortcuts_mgr.save_shortcut(s)
                                        else:
                                            st.session_state.magic_shortcuts.append(s)
                                        count += 1
                            
                            if shortcuts_mgr:
                                st.session_state.magic_shortcuts = shortcuts_mgr.load_shortcuts()
                                
                            st.success(f"✅ Successfully imported {count} shortcuts!")
                            st.rerun()
                        else:
                            st.error("Invalid file format. Expected a list of shortcuts.")
                    except Exception as e:
                        st.error(f"Error importing: {str(e)}")
