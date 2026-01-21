from app.tabs.abp_imports_common import (
    st, os, time, json, Path, datetime, setup_logger
)

# Maintain backward compatibility alias
dt = datetime
logger = setup_logger(__name__)

from app.services.secure_config import render_secure_config_ui, init_api_clients, is_demo_mode, get_api_key
from app.services.enhanced_features import GlobalSearchManager
from app.services.tab_visibility_manager import (
    initialize_tab_visibility,
    get_visible_tabs,
    get_filtered_tabs,
    render_tab_preferences
)
from app.services.youtube_upload_service import YouTubeUploadService
from app.services.shopify_service import ShopifyAPI
from app.services.platform_helpers import _get_replicate_token
from app.services.platform_integrations import render_recovery_check
from app.utils.performance_optimizations import render_performance_settings
try:
    from app.services.background_tasks import get_task_manager, TaskState
    BACKGROUND_TASKS_AVAILABLE = True
except ImportError:
    BACKGROUND_TASKS_AVAILABLE = False
    get_task_manager = None
    TaskState = None
try:
    from app.services.shortcuts_manager import ShortcutsManager
except ImportError:
    ShortcutsManager = None

def render_sidebar(
    enhanced_features_available,
    platform_integrations_available,
    render_chat_interface_func,
    render_about_guide_func,
    render_command_line_guide_func,
    render_integrations_sidebar_func
):
    """
    Renders the sidebar content.
    """
    with st.sidebar:
        # ========================================
        # GLOBAL SEARCH (NEW ENHANCED FEATURE)
        # ========================================
        if enhanced_features_available:
            st.markdown("### 🔍 Global Search")
            global_search = st.text_input(
                "Search all content",
                placeholder="campaigns, products, chats...",
                key="global_search_sidebar",
                label_visibility="collapsed"
            )
            
            if global_search and len(global_search) > 2:
                results = GlobalSearchManager.search(global_search)
                if results:
                    st.caption(f"📌 Found {len(results)} results")
                    for result in results[:3]:
                        if st.button(f"📍 {result['title'][:40]}", key=f"search_result_{result['type']}_{result['index']}", use_container_width=True):
                            st.session_state[f'load_{result["type"]}'] = result['item']
                            st.success("Loaded!")
            
            st.markdown("---")
        
        # ========================================
        # OTTO MATE - FULL SCREEN AI ASSISTANT
        # ========================================
        st.markdown("### 🤖 Otto Mate")
        
        otto_col1, otto_col2 = st.columns([3, 1])
        with otto_col1:
            if st.button("🚀 Launch Otto Full Screen", use_container_width=True, type="primary", key="sidebar_otto_fullscreen"):
                st.session_state.with otto_col2:
            st.markdown("AI ✨")
        
        st.caption("Your hyperintelligent AI assistant for all automation tasks")
        
        st.markdown("---")
        # Compact Background Task status (visible on all pages)
        if BACKGROUND_TASKS_AVAILABLE:
            try:
                from app.services.background_tasks import render_task_status_widget
                render_task_status_widget()
            except Exception:
                pass
        
        # Horizontal Tabs in Sidebar
        sidebar_tabs = st.tabs(["💬 Chat", "⚡ Shortcuts", "ℹ️ About", "⚙️ Settings", "📊 Status", "💻 Command Line"])
        
        # Render content based on selected sidebar tab
        with sidebar_tabs[0]:  # Chat
                # AI Assistant Selector at the top
                st.markdown("#### 🤖 AI Assistant")
                
                try:
                    from custom_assistants import PRESET_ASSISTANTS
                    
                    # Initialize active assistant in session state
                    if 'active_assistant' not in st.session_state:
                        st.session_state.active_assistant = None
                    
                    # Get assistant options
                    assistant_options = {"otto_default": "🤖 Otto (Default)"}
                    for preset_id, preset in PRESET_ASSISTANTS.items():
                        assistant_options[preset_id] = f"{preset.get('avatar', '🤖')} {preset['name']}"
                    
                    # Assistant selector
                    selected_assistant = st.selectbox(
                        "Choose Assistant",
                        options=list(assistant_options.keys()),
                        format_func=lambda x: assistant_options[x],
                        index=0 if st.session_state.active_assistant is None or st.session_state.active_assistant == "otto_default" 
                              else list(assistant_options.keys()).index(st.session_state.active_assistant) if st.session_state.active_assistant in assistant_options else 0,
                        key="assistant_selector",
                        label_visibility="collapsed"
                    )
                    
                    # Update session state if changed
                    if selected_assistant != st.session_state.active_assistant:
                        st.session_state.active_assistant = selected_assistant
                        st.rerun()
                    
                    # Show assistant info if not default
                    if selected_assistant != "otto_default" and selected_assistant in PRESET_ASSISTANTS:
                        preset = PRESET_ASSISTANTS[selected_assistant]
                        with st.expander("ℹ️ About this assistant", expanded=False):
                            st.caption(f"**{preset.get('category', 'General')}:** {preset.get('description', '')}")
                            if preset.get('example_prompts'):
                                st.markdown("**Try asking:**")
                                for prompt in preset['example_prompts'][:3]:
                                    st.caption(f"• {prompt}")
                except ImportError:
                    pass
                
                st.markdown("---")
                
                # Chat interface
                render_chat_interface_func()
        
        with sidebar_tabs[2]:  # About
                render_about_guide_func()
        
                # Transfer the "Settings" content from the main page to the sidebar's "Settings" tab
        with sidebar_tabs[3]:  # Settings
                st.markdown("### ⚙️ Platform Configuration")
        
                settings_tabs = st.tabs(["🔑 API Keys", "📺 YouTube", "🎨 Preferences", "⌨️ Shortcuts", "🔗 Integrations", "📤 Export", "⚡ Performance"])
                
                # Rename tab1-8 to settings_tabs[0]-[7]
                tab1, tab2, tab3, tab_shortcuts, tab4, tab5, tab6, tab7 = settings_tabs
                
                with sidebar_tabs[4]:  # Status (Platform integrations)
            st.markdown("### 📊 Platform Status")
            
            # Background Tasks Status
            if BACKGROUND_TASKS_AVAILABLE:
                try:
                    task_manager = get_task_manager()
                    running_tasks = task_manager.get_running_tasks()
                    
                    if running_tasks:
                        st.markdown("#### 🔄 Active Tasks")
                        for task in running_tasks[:3]:
                            with st.container():
                                st.markdown(f"**{task.name}**")
                                st.progress(task.progress, text=task.current_step or "Processing...")
                                if task.completed_steps and task.total_steps:
                                    st.caption(f"Step {task.completed_steps}/{task.total_steps}")
                        if len(running_tasks) > 3:
                            st.caption(f"+ {len(running_tasks) - 3} more tasks...")
                        st.markdown("---")
                    
                    # Show recent completed/failed
                    all_tasks = task_manager.get_all_tasks()
                    completed = [t for t in all_tasks if t.state == TaskState.COMPLETED][-3:]
                    failed = [t for t in all_tasks if t.state == TaskState.FAILED][-2:]
                    
                    if completed or failed:
                        with st.expander("📋 Recent Tasks", expanded=False):
                            for task in completed:
                                st.success(f"✅ {task.name}")
                            for task in failed:
                                st.error(f"❌ {task.name}: {task.error[:50] if task.error else 'Unknown'}...")
                            if st.button("🧹 Clear History", key="clear_task_history_sidebar"):
                                task_manager.clear_completed_tasks()
                                st.rerun()
                except Exception as e:
                    st.caption(f"Task manager: {e}")
            
            if platform_integrations_available:
                render_integrations_sidebar_func()
            else:
                st.info("Platform integrations not available")
        
        with sidebar_tabs[5]:  # Command Line
            render_command_line_guide_func()
        
        
        
        st.markdown("---")
        st.markdown("### 📁 File Storage")
        st.info("""
**Local Version**: Files save to `file_library/` folder
        
**Demo Version** ([otto-mate.streamlit.app](https://otto-mate.streamlit.app)):
- Files are temporary (session only)
- Download immediately after generation
- Limited resources & API integrations
        
For production use, install locally!
        """)

        with sidebar_tabs[1]:  # Shortcuts
            st.markdown("### ⚡ Magic Buttons")
            st.caption("Quick access to your shortcuts")
        
            # Import shortcuts manager if available
            try:
                from app.services.shortcuts_manager import ShortcutsManager
                sidebar_shortcuts_mgr = ShortcutsManager()
                
                # Initialize shortcuts in session state if not exists - load from persistence
                if 'magic_shortcuts' not in st.session_state:
                    st.session_state.magic_shortcuts = sidebar_shortcuts_mgr.load_shortcuts()
            except ImportError:
                sidebar_shortcuts_mgr = None
                if 'magic_shortcuts' not in st.session_state:
                    st.session_state.magic_shortcuts = []
            
            # Gradient styles for button backgrounds
            sidebar_gradient_styles = {
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
            
            if not st.session_state.magic_shortcuts:
                st.info("🪄 No shortcuts yet!")
                st.markdown("Go to **⚡ Shortcuts** tab in the main area to create magic buttons.")
            else:
                # Filter shortcuts that are pinned to sidebar
                sidebar_shortcuts = [s for s in st.session_state.magic_shortcuts if s.get('in_sidebar', False)]
                
                if not sidebar_shortcuts:
                    st.info("📌 No shortcuts pinned to sidebar yet!")
                    st.caption("Create shortcuts and click the \"+\" button to add them here.")
                else:
                    # Display shortcuts as compact styled buttons
                    for shortcut in sidebar_shortcuts:
                        shortcut_id = shortcut.get('id', '')
                        shortcut_name = shortcut.get('name', 'Untitled')
                        shortcut_icon = shortcut.get('icon', '⚡')
                        shortcut_desc = shortcut.get('description', '')[:50]
                        gradient = shortcut.get('gradient', 'Purple Aurora')
                        bg_gradient = sidebar_gradient_styles.get(gradient, sidebar_gradient_styles['Purple Aurora'])
                        
                        # Styled button with gradient background
                        st.markdown(f"""
                        <style>
                        div[data-testid="stButton"] button[kind="primary"][key="sidebar_shortcut_{shortcut_id}"] {{
                            background: {bg_gradient} !important;
                            border: none !important;
                            color: white !important;
                            text-shadow: 1px 1px 2px rgba(0,0,0,0.3) !important;
                        }}
                        </style>
                        """, unsafe_allow_html=True)
                        
                        # Container with button and remove option
                        with st.container():
                            col_btn, col_remove = st.columns([5, 1])
                            
                            with col_btn:
                                if st.button(
                                    f"{shortcut_icon} {shortcut_name}",
                                    key=f"sidebar_shortcut_{shortcut_id}",
                                    use_container_width=True,
                                    type="primary" if shortcut.get('run_count', 0) > 0 else "secondary"
                                ):
                                    # Execute the shortcut
                                    with st.spinner(f"Running {shortcut_name}..."):
                                        try:
                                            results = []
                                            context = {'description': shortcut['description']}
                                            
                                            from app.services.otto_engine import get_slash_processor
                                            from app.services.api_service import ReplicateAPI
                                            
                                            # Get Replicate API token
                                            replicate_token = _get_replicate_token()
                                            if not replicate_token:
                                                st.error("❌ Replicate API token not configured.")
                                            else:
                                                replicate_api = ReplicateAPI(api_token=replicate_token)
                                                slash_processor = get_slash_processor(replicate_api)
                                                
                                                for step in shortcut.get('steps', []):
                                                    step_name = step.get('name', 'Step')
                                                    
                                                    if step['type'] == 'generate':
                                                        action = step.get('action', '')
                                                        prompt = step.get('prompt_template', '').format(**context)
                                                        
                                                        import asyncio
                                                        result = asyncio.run(slash_processor.execute(f"{action} {prompt}"))
                                                        
                                                        if result.get('success'):
                                                            results.append(result)
                                                            if 'output_var' in step:
                                                                output_url = result.get('url') or (result.get('artifacts', [{}])[0].get('url') if result.get('artifacts') else None)
                                                                context[step['output_var']] = output_url
                                                            
                                                            # Display result
                                                            if result.get('type') == 'media':
                                                                for artifact in result.get('artifacts', []):
                                                                    art_type = artifact.get('type', '')
                                                                    url = artifact.get('url', '')
                                                                    if art_type == 'image' and url:
                                                                        st.image(url, caption=step_name, width=200)
                                                                    elif art_type == 'video' and url:
                                                                        st.video(url)
                                                                    elif art_type == 'audio' and url:
                                                                        st.audio(url)
                                                            
                                                            st.success(f"✅ {step_name}")
                                                        else:
                                                            st.warning(f"⚠️ {step_name}: {result.get('error', 'Unknown error')}")
                                                    
                                                    elif step['type'] == 'post':
                                                        # Actual social media posting
                                                        platform = step.get('platform', step.get('action', 'twitter')).lower()
                                                        content = step.get('content', step.get('caption', ''))
                                                        image_path = context.get('image_url') or context.get('product_image')
                                                        
                                                        if 'twitter' in platform and image_path:
                                                            try:
                                                                from app.services.ai_twitter_poster import AITwitterPoster
                                                                poster = AITwitterPoster(headless=True)
                                                                import asyncio
                                                                
                                                                # Download image if it's a URL
                                                                if image_path.startswith('http'):
                                                                    import tempfile
                                                                    import requests
                                                                    response = requests.get(image_path)
                                                                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                                                                        tmp.write(response.content)
                                                                        local_image = tmp.name
                                                                else:
                                                                    local_image = image_path
                                                                
                                                                success = asyncio.run(poster.post_to_twitter(local_image, content))
                                                                if success:
                                                                    st.success(f"✅ Posted to Twitter!")
                                                                    results.append({'step': step_name, 'status': 'success', 'platform': 'twitter'})
                                                                else:
                                                                    st.warning(f"⚠️ Twitter post may have failed - check manually")
                                                                    results.append({'step': step_name, 'status': 'uncertain'})
                                                            except Exception as post_error:
                                                                st.info(f"📤 {step.get('action', 'social media')} - {post_error}")
                                                                results.append({'step': step_name, 'status': 'simulated', 'error': str(post_error)})
                                                        else:
                                                            st.info(f"📤 {step.get('action', 'social media')} ready (configure credentials)")
                                                            results.append({'step': step_name, 'status': 'pending'})
                                                    
                                                    elif step['type'] == 'ai':
                                                        st.info(f"🤖 AI processing...")
                                                        results.append({'step': step_name, 'status': 'processed'})
                                                
                                                # Update shortcut stats and persist
                                                shortcut['run_count'] = shortcut.get('run_count', 0) + 1
                                                shortcut['last_run'] = dt.now().isoformat()
                                                
                                                # Persist the updated stats
                                                if sidebar_shortcuts_mgr:
                                                    sidebar_shortcuts_mgr.save_shortcut(shortcut)
                                                    st.session_state.magic_shortcuts = sidebar_shortcuts_mgr.load_shortcuts()
                                                
                                                if shortcut.get('settings', {}).get('notify', True):
                                                    st.success(f"🎉 Done!")
                                        
                                        except Exception as e:
                                            st.error(f"Error: {str(e)}")
                            
                            with col_remove:
                                if st.button("🗑️", key=f"remove_sidebar_{shortcut_id}", help="Remove from sidebar"):
                                    # Remove from sidebar
                                    shortcut['in_sidebar'] = False
                                    if sidebar_shortcuts_mgr:
                                        sidebar_shortcuts_mgr.save_shortcut(shortcut)
                                        st.session_state.magic_shortcuts = sidebar_shortcuts_mgr.load_shortcuts()
                                    st.rerun()
                            
                        # Show run count and keyboard shortcut below button
                        info_parts = []
                        run_count = shortcut.get('run_count', 0)
                        if run_count > 0:
                            info_parts.append(f"📊 {run_count} runs")
                        
                        # Show keyboard shortcut if assigned
                        kb_shortcut = shortcut.get('keyboard_shortcut', '')
                        if kb_shortcut:
                            info_parts.append(f"⌨️ {kb_shortcut}")
                        
                        if info_parts:
                            st.caption(" • ".join(info_parts))
            
                    st.markdown("---")
                    st.caption("💡 Manage shortcuts in the ⚡ Shortcuts tab")
                    
                    # Keyboard Shortcuts Section
                    with st.expander("⌨️ Keyboard Shortcuts", expanded=False):
                        st.markdown("**Assign keyboard shortcuts to your magic buttons**")
                        st.caption("Press the key combination to trigger shortcuts instantly")
                        
                        # Show current keyboard shortcuts
                        shortcuts_with_kb = [s for s in sidebar_shortcuts if s.get('keyboard_shortcut')]
                        
                        if shortcuts_with_kb:
                            st.markdown("**Active Shortcuts:**")
                            for shortcut in shortcuts_with_kb:
                                kb_key = shortcut.get('keyboard_shortcut', '')
                                st.caption(f"⌨️ `{kb_key}` → {shortcut.get('icon', '⚡')} {shortcut.get('name', 'Untitled')}")
                        else:
                            st.info("No keyboard shortcuts assigned yet")
                        
                        st.markdown("---")
                        st.markdown("**Assign Shortcut:**")
                        
                        # Select shortcut to assign keyboard key
                        shortcut_to_assign = st.selectbox(
                            "Select Magic Button",
                            options=sidebar_shortcuts,
                            format_func=lambda s: f"{s.get('icon', '⚡')} {s.get('name', 'Untitled')}",
                            key="kb_assign_select"
                        )
                        
                        if shortcut_to_assign:
                            current_kb = shortcut_to_assign.get('keyboard_shortcut', '')
                            
                            col_kb1, col_kb2 = st.columns([3, 1])
                            
                            with col_kb1:
                                new_kb_shortcut = st.text_input(
                                    "Keyboard Shortcut",
                                    value=current_kb,
                                    placeholder="e.g., Ctrl+Shift+1, Alt+Q, Ctrl+K",
                                    help="Use format: Ctrl+Key, Alt+Key, Shift+Key, or combinations",
                                    key="kb_shortcut_input"
                                )
                            
                            with col_kb2:
                                if st.button("💾 Save", key="save_kb_shortcut"):
                                    shortcut_to_assign['keyboard_shortcut'] = new_kb_shortcut
                                    if sidebar_shortcuts_mgr:
                                        sidebar_shortcuts_mgr.save_shortcut(shortcut_to_assign)
                                        st.session_state.magic_shortcuts = sidebar_shortcuts_mgr.load_shortcuts()
                                    st.success(f"✅ Shortcut saved!")
                                    st.rerun()
                        
                        st.markdown("---")
                        st.caption("💡 **Tips:**")
                        st.caption("• Use Ctrl+Shift+[Key] for most shortcuts")
                        st.caption("• Numbers 1-9 work great for quick access")
                        st.caption("• Avoid common browser shortcuts (Ctrl+T, Ctrl+W, etc.)")
                        st.caption("• Test shortcuts after saving")
                    
                    # Inject JavaScript for keyboard shortcuts
                    # Build shortcut mapping
                    kb_mapping = {}
                    for shortcut in sidebar_shortcuts:
                        kb_key = shortcut.get('keyboard_shortcut', '').strip()
                        if kb_key:
                            kb_mapping[kb_key.lower()] = {
                                'id': shortcut.get('id', ''),
                                'name': shortcut.get('name', 'Untitled'),
                                'icon': shortcut.get('icon', '⚡')
                            }
                    
                    if kb_mapping:
                        # Generate JavaScript keyboard handler
                        import json
                        kb_json = json.dumps(kb_mapping)
                        
                        keyboard_script = f"""
                        <script>
                        // Keyboard shortcut handler for Magic Buttons
                        (function() {{
                            const shortcuts = {kb_json};
                            
                            // Track pressed modifier keys
                            let modifiers = {{
                                ctrl: false,
                                alt: false,
                                shift: false,
                                meta: false
                            }};
                            
                            // Build shortcut string from current state
                            function getShortcutString(key) {{
                                let parts = [];
                                if (modifiers.ctrl) parts.push('ctrl');
                                if (modifiers.alt) parts.push('alt');
                                if (modifiers.shift) parts.push('shift');
                                if (modifiers.meta) parts.push('meta');
                                parts.push(key.toLowerCase());
                                return parts.join('+');
                            }}
                            
                            // Update modifier state
                            function updateModifiers(event) {{
                                modifiers.ctrl = event.ctrlKey;
                                modifiers.alt = event.altKey;
                                modifiers.shift = event.shiftKey;
                                modifiers.meta = event.metaKey;
                            }}
                            
                            // Handle keydown
                            document.addEventListener('keydown', function(event) {{
                                updateModifiers(event);
                                
                                // Get the key (normalize)
                                let key = event.key.toLowerCase();
                                
                                // Build shortcut string
                                let shortcutStr = getShortcutString(key);
                                
                                // Check if this matches any shortcut
                                if (shortcuts[shortcutStr]) {{
                                    const shortcut = shortcuts[shortcutStr];
                                    
                                    // Prevent default browser behavior
                                    event.preventDefault();
                                    event.stopPropagation();
                                    
                                    // Show notification
                                    console.log('🎯 Triggering shortcut:', shortcut.name);
                                    
                                    // Find and click the corresponding button
                                    const buttonId = 'sidebar_shortcut_' + shortcut.id;
                                    const buttons = document.querySelectorAll('button');
                                    
                                    for (let btn of buttons) {{
                                        if (btn.textContent.includes(shortcut.icon) && btn.textContent.includes(shortcut.name)) {{
                                            console.log('✅ Found button, clicking...');
                                            btn.click();
                                            
                                            // Visual feedback
                                            const notification = document.createElement('div');
                                            notification.style.position = 'fixed';
                                            notification.style.top = '20px';
                                            notification.style.right = '20px';
                                            notification.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
                                            notification.style.color = 'white';
                                            notification.style.padding = '15px 25px';
                                            notification.style.borderRadius = '8px';
                                            notification.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
                                            notification.style.zIndex = '9999';
                                            notification.style.fontFamily = 'Arial, sans-serif';
                                            notification.style.fontWeight = 'bold';
                                            notification.style.fontSize = '14px';
                                            notification.innerHTML = '⚡ ' + shortcut.icon + ' ' + shortcut.name;
                                            document.body.appendChild(notification);
                                            
                                            setTimeout(() => {{
                                                notification.style.transition = 'opacity 0.3s';
                                                notification.style.opacity = '0';
                                                setTimeout(() => notification.remove(), 300);
                                            }}, 2000);
                                            
                                            break;
                                        }}
                                    }}
                                }}
                            }}, true);
                            
                            // Reset modifiers on keyup
                            document.addEventListener('keyup', function(event) {{
                                updateModifiers(event);
                            }});
                            
                            // Show available shortcuts on Ctrl+Shift+?
                            document.addEventListener('keydown', function(event) {{
                                if (event.ctrlKey && event.shiftKey && event.key === '?') {{
                                    event.preventDefault();
                                    const shortcutList = Object.entries(shortcuts)
                                        .map(([key, val]) => `⌨️ ${{key.toUpperCase()}} → ${{val.icon}} ${{val.name}}`)
                                        .join('\\n');
                                    
                                    const helpBox = document.createElement('div');
                                    helpBox.style.position = 'fixed';
                                    helpBox.style.top = '50%';
                                    helpBox.style.left = '50%';
                                    helpBox.style.transform = 'translate(-50%, -50%)';
                                    helpBox.style.background = 'white';
                                    helpBox.style.padding = '30px';
                                    helpBox.style.borderRadius = '12px';
                                    helpBox.style.boxShadow = '0 8px 32px rgba(0,0,0,0.3)';
                                    helpBox.style.zIndex = '10000';
                                    helpBox.style.maxWidth = '500px';
                                    helpBox.style.fontFamily = 'monospace';
                                    helpBox.style.fontSize = '14px';
                                    helpBox.innerHTML = '<h3 style="margin-top:0">⌨️ Keyboard Shortcuts</h3><pre style="white-space:pre-wrap">' + shortcutList + '</pre><p style="text-align:center;margin-bottom:0"><button onclick="this.parentElement.parentElement.remove()" style="padding:8px 20px;background:#667eea;color:white;border:none;border-radius:6px;cursor:pointer">Close</button></p>';
                                    document.body.appendChild(helpBox);
                                }}
                            }});
                            
                            console.log('⚡ Keyboard shortcuts activated:', Object.keys(shortcuts).length, 'shortcuts loaded');
                        }})();
                        </script>
                        """
                        
                        st.components.v1.html(keyboard_script, height=0)
        
                # ========================================
                # CRASH RECOVERY CHECK
                # ========================================
        if platform_integrations_available:
                render_recovery_check()
        
                # ========================================
    # HORIZONTAL NAVIGATION (TOP)
    # ========================================
        
    # Remove Settings, About, and Command Line from the main page
    # Keep only the main horizontal tabs for Dashboard, Campaign Creator, etc.
        
    # Build tab list - All tabs visible by default in horizontal navigation
    # Brand Templates, Digital Products, Customers now in horizontal tabs
    base_tabs = [
    "🏠 Dashboard",
    "⚡ Shortcuts",
    "🤖 Task Queue",
    "🔄 Job Monitor",
    "📦 Product Studio",
    "💾 Digital Products",
    "🎯 Campaign Creator",
    "📝 Content Generator",
    "🎬 Video Producer",
    "🎮 Playground",
    "🔧 Workflows",
    "📅 Calendar",
    "📓 Journal",
    "🔍 Contact Finder",
    "👥 Customers",
    "📊 Analytics",
    "🎨 Brand Templates",
    "💌 Email Outreach",
    "🎵 Music Platforms",
    "📁 File Library",
    "🌐 Browser-Use"
    ]
        
    # No separate experimental tabs - all features visible by default
    # Apply tab visibility filtering based on user preferences
    initialize_tab_visibility()
    all_tabs = get_filtered_tabs(base_tabs)
        
    # ========================================
    # FULLSCREEN CHAT MODE CHECK
    # ========================================
    if st.session_state.get('st.markdown("---")
        
    # Main chat area - centered like ChatGPT
        render_chat_interface_func(key_suffix="fullscreen")
        
        # Stop here - don't render the tabs
        st.stop()
        
    # ========================================
    # GLOBAL HEADER ROW - Session controls + Progress indicator
    # ========================================
    # Create columns for buttons and progress indicator
    header_cols = st.columns([5, 1, 1, 1, 3])
    
    with header_cols[1]:
        if st.button("💾", use_container_width=False, type="secondary", key="global_save_session_btn", help="Save current session state"):
            st.session_state.show_session_manager = True
            st.session_state.session_manager_mode = "save"
            st.rerun()
    
    with header_cols[2]:
        if st.button("📂", use_container_width=False, type="secondary", key="global_load_session_btn", help="Load saved session"):
            st.session_state.show_session_manager = True
            st.session_state.session_manager_mode = "load"
            st.rerun()
    
    with header_cols[3]:
        if st.button("🤖 Otto", use_container_width=False, type="secondary", key="global_otto_btn", help="Chat with Otto Mate AI Assistant"):
            st.session_state.with header_cols[4]:
        # Render global progress indicator in the header (compact version)
        try:
            from app.services.background_task_manager import render_compact_progress_indicator
            render_compact_progress_indicator()
        except Exception as e:
            pass  # Silently fail if not available

    return all_tabs
