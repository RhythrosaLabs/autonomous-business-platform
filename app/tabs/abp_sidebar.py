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
    all_tabs = []  # Initialize to prevent NameError

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
                st.session_state.fullscreen_chat_mode = True
                st.rerun()
        with otto_col2:
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
        
                settings_tabs = st.tabs(["🔑 API Keys", "📺 YouTube", "🎨 Preferences", "⌨️ Shortcuts", "🔗 Integrations", "📤 Export", "⚡ Performance", ])
                
                # Rename tab1-8 to settings_tabs[0]-[7]
                tab1, tab2, tab3, tab_shortcuts, tab4, tab5, tab6 = settings_tabs
                
                with tab1:
                    # Use the new secure configuration UI
                    try:
                        render_secure_config_ui()
                    except Exception as e:
                        st.error(f"Error loading API configuration: {str(e)}")
                        # Fallback to basic display
                        st.markdown("#### API Configuration")
                        st.info("Please configure your API keys in the .env file or use Streamlit Cloud secrets.")
                with tab2:
                    st.markdown("#### YouTube Video Publishing")
                    st.markdown("*Configure OAuth 2.0 credentials for automated video uploads*")
        
                    from youtube_upload_service import YouTubeUploadService
        
                    # Initialize YouTube service
                    yt_service = YouTubeUploadService()
        
                    # Check credentials status
                    creds_status = yt_service.check_credentials()
        
                    # Display status
                    st.markdown("---")
                    st.markdown("**📊 Connection Status**")
        
                    col_yt1, col_yt2, col_yt3 = st.columns(3)
        
                    with col_yt1:
                        if creds_status['authenticated']:
                            st.success("✅ Authenticated")
                        else:
                            st.error("❌ Not Authenticated")
        
                    with col_yt2:
                        if creds_status['client_secrets_exists']:
                            st.success("✅ Credentials File")
                        else:
                            st.error("❌ No Credentials")
        
                    with col_yt3:
                        if creds_status['token_exists']:
                            st.info("🔐 Token Saved")
                        else:
                            st.warning("⚠️ No Token")
        
                    st.markdown(f"**Status:** {creds_status['message']}")
        
                    # Setup instructions
                    st.markdown("---")
                    with st.expander("🔧 Setup Instructions", expanded=not creds_status['authenticated']):
                        st.markdown("""
                #### Step 1: Create Google Cloud Project
                1. Go to [Google Cloud Console](https://console.cloud.google.com/)
                2. Create a new project or select existing
                3. Enable **YouTube Data API v3**
        
                #### Step 2: Create OAuth 2.0 Credentials
                1. Go to **APIs & Services → Credentials**
                2. Click **Create Credentials → OAuth client ID**
                3. Choose **Desktop application**
                4. Download the JSON file
        
                #### Step 3: Install Credentials
                1. Rename downloaded file to `client_secret.json`
                2. Place it in: `/Users/sheils/repos/printify/`
                3. Click **Authenticate** button below
        
                #### Step 4: First-Time Authorization
                1. Browser will open automatically
                2. Sign in with your YouTube account
                3. Grant permissions
                4. Token will be saved for future use
        
                #### Important Notes:
                - ✅ Free to use (within YouTube API quotas)
                - ✅ Token persists across sessions
                - ✅ One-time setup per machine
                - ⚠️ Keep `client_secret.json` secure (don't commit to git)
                """)
        
                    # Authentication actions
                    st.markdown("---")
                    st.markdown("**🔐 Actions**")
        
                    col_act1, col_act2, col_act3 = st.columns(3)
        
                    with col_act1:
                        if st.button("🔓 Authenticate YouTube", use_container_width=True, type="primary"):
                            if not creds_status['client_secrets_exists']:
                                st.error("❌ Missing client_secret.json file")
                                st.info("Download from Google Cloud Console and place in project root")
                            else:
                                with st.spinner("Opening browser for OAuth..."):
                                    try:
                                        if yt_service.authenticate():
                                            st.success("✅ Authentication successful!")
                                            st.balloons()
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error("❌ Authentication failed")
                                    except Exception as e:
                                        st.error(f"❌ Error: {e}")
        
                    with col_act2:
                        if st.button("🔄 Refresh Status", use_container_width=True):
                            st.rerun()
        
                    with col_act3:
                        if st.button("🗑️ Clear Token", use_container_width=True):
                            token_path = Path(__file__).parent / 'token.pickle'
                            if token_path.exists():
                                token_path.unlink()
                                st.success("✅ Token cleared")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.info("No token to clear")
        
                    # Upload history
                    if creds_status['authenticated']:
                        st.markdown("---")
                        st.markdown("**📺 Recent Uploads**")
        
                        try:
                            recent_videos = yt_service.get_upload_history(limit=5)
        
                            if recent_videos:
                                for video in recent_videos:
                                    with st.expander(f"▶️ {video['title']}", expanded=False):
                                        col_v1, col_v2 = st.columns([1, 2])
                                        with col_v1:
                                            if video.get('thumbnail'):
                                                st.image(video['thumbnail'])
                                        with col_v2:
                                            st.markdown(f"**Video ID:** `{video['id']}`")
                                            st.markdown(f"**URL:** {video['url']}")
                                            st.markdown(f"**Published:** {video['publishedAt'][:10]}")
                            else:
                                st.info("No videos found on this channel")
                        except Exception as e:
                            st.warning(f"Could not load upload history: {e}")
        
                    # Test upload section
                    if creds_status['authenticated']:
                        st.markdown("---")
                        with st.expander("🧪 Test Upload", expanded=False):
                            st.markdown("Upload a test video to verify your configuration")
        
                            test_video = st.file_uploader("Select video file", type=['mp4', 'mov', 'avi'])
                            test_title = st.text_input("Test Title", "Test Video Upload")
                            test_privacy = st.selectbox("Privacy", ["private", "unlisted", "public"], index=0)
        
                            if st.button("Upload Test Video") and test_video:
                                import tempfile
                                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
                                    tmp.write(test_video.read())
                                    tmp_path = tmp.name
        
                                with st.spinner("Uploading..."):
                                    metadata = {
                                        'title': test_title,
                                        'description': 'Test upload from autonomous platform',
                                        'tags': ['test'],
                                        'category': '22',
                                        'privacy': test_privacy,
                                        'notify_subscribers': False
                                    }
        
                                    result = yt_service.upload_commercial(
                                        video_path=tmp_path,
                                        product_name=test_title,
                                        metadata=metadata
                                    )
        
                                    if result:
                                        st.success(f"✅ Uploaded: {result['url']}")
                                    else:
                                        st.error("❌ Upload failed")
        
                                    os.unlink(tmp_path)
        
        with tab3:  # Preferences
                    st.markdown("#### 🎨 User Preferences")
            
                    st.markdown("---")
                    st.markdown("**💬 Chat Display**")
            
                    fullscreen_chat = st.checkbox(
                        "Full-Screen Chat Mode",
                        value=st.session_state.fullscreen_chat_mode,
                        help="Display chat in main screen area instead of sidebar"
                    )
            
                    if fullscreen_chat != st.session_state.fullscreen_chat_mode:
                        st.session_state.fullscreen_chat_mode = fullscreen_chat
                        st.success("✅ Chat display mode updated")
                        st.rerun()
            
                    st.markdown("---")
                    
                    # Tab Visibility Preferences
                    render_tab_preferences()
                    
                    
                    
                    st.markdown("---")
                    st.markdown("**🤖 Default AI Models**")
                    st.caption("Set default models for quick generation")
                    
                    if 'default_image_model' not in st.session_state:
                        st.session_state.default_image_model = 'prunaai/flux-fast'
                    if 'default_video_model' not in st.session_state:
                        st.session_state.default_video_model = 'minimax/video-01'
                    if 'default_music_model' not in st.session_state:
                        st.session_state.default_music_model = 'meta/musicgen'
                    
                    ai_col1, ai_col2 = st.columns(2)
                    with ai_col1:
                        st.session_state.default_image_model = st.selectbox(
                            "🎨 Image",
                            ['prunaai/flux-fast', 'bytedance/seedream-4', 'google/imagen-4-ultra'],
                            key="default_img_sel"
                        )
                        st.session_state.default_music_model = st.selectbox(
                            "🎵 Music",
                            ['meta/musicgen', 'auffusion/stable-audio'],
                            key="default_music_sel"
                        )
                    with ai_col2:
                        st.session_state.default_video_model = st.selectbox(
                            "🎬 Video",
                            ['minimax/video-01', 'luma/photon-flash', 'lightricks/ltx-video'],
                            key="default_vid_sel"
                        )
                    
                    st.caption("💡 Dashboard uses its own model selection")
            
                    st.markdown("---")
                    st.markdown("**⚙️ Performance**")
            
                    perf_col1, perf_col2 = st.columns(2)
                    with perf_col1:
                        auto_save = st.checkbox("Auto-save Progress", value=True, help="Automatically save work in progress")
                    with perf_col2:
                        cache_results = st.checkbox("Cache API Results", value=True, help="Speed up by caching API responses")
        
        with tab4:  # Integrations
                    st.markdown("#### 🔗 Platform Integrations")
            
                    integration_tabs = st.tabs(["📦 POD Services", "🛒 Marketplaces", "📱 Social Media", "💝 Charity", "📅 Scheduling"])
            
                    with integration_tabs[0]:  # POD Services
                        st.markdown("##### Print-on-Demand Connectors")
                        st.caption("Connect to additional POD services beyond Printify")
                
                        pod_services = {
                            'printful': {'name': 'Printful', 'icon': '🖨️', 'status': 'Ready to connect'},
                            'gooten': {'name': 'Gooten', 'icon': '🎨', 'status': 'Ready to connect'},
                            'gelato': {'name': 'Gelato', 'icon': '🌍', 'status': 'Ready to connect'}
                        }
                
                        for pod_id, pod_info in pod_services.items():
                            with st.expander(f"{pod_info['icon']} {pod_info['name']}", expanded=False):
                                # Check if already connected
                                existing_key = os.getenv(f"{pod_id.upper()}_API_KEY", "")
                                is_connected = bool(existing_key)
                        
                                if is_connected:
                                    st.success(f"✅ Connected to {pod_info['name']}")
                                    if st.button(f"Disconnect {pod_info['name']}", key=f"pod_{pod_id}_disconnect"):
                                        st.session_state[f'pod_{pod_id}_connected'] = False
                                        st.info(f"Disconnected from {pod_info['name']}")
                                else:
                                    api_key = st.text_input(f"{pod_info['name']} API Key", type="password", key=f"pod_{pod_id}_key")
                                    if st.button(f"Connect {pod_info['name']}", key=f"pod_{pod_id}_connect"):
                                        if api_key:
                                            # Store in session and .env file
                                            st.session_state[f'pod_{pod_id}_connected'] = True
                                            st.session_state[f'pod_{pod_id}_api_key'] = api_key
                                    
                                            # Try to save to .env file
                                            try:
                                                env_path = os.path.join(os.path.dirname(__file__), '.env')
                                                with open(env_path, 'a') as f:
                                                    f.write(f"\n{pod_id.upper()}_API_KEY={api_key}")
                                                st.success(f"✅ {pod_info['name']} connected and saved!")
                                            except Exception as e:
                                                st.success(f"✅ {pod_info['name']} connected for this session!")
                                                st.caption(f"Note: Add {pod_id.upper()}_API_KEY to .env for persistence")
                                        else:
                                            st.warning("Please enter an API key")
            
                    with integration_tabs[1]:  # Marketplaces
                        st.markdown("##### Store Connectors")
                        st.caption("Sell across multiple marketplaces")
                
                        marketplaces = {
                            'etsy': {
                                'name': 'Etsy', 
                                'icon': '🧵', 
                                'oauth': True,
                                'client_id_env': 'ETSY_CLIENT_ID',
                                'client_secret_env': 'ETSY_CLIENT_SECRET',
                                'oauth_url': 'https://www.etsy.com/oauth/connect'
                            },
                            'amazon': {
                                'name': 'Amazon', 
                                'icon': '📦', 
                                'oauth': True,
                                'client_id_env': 'AMAZON_CLIENT_ID',
                                'client_secret_env': 'AMAZON_CLIENT_SECRET',
                                'oauth_url': 'https://sellercentral.amazon.com/apps/authorize/consent'
                            },
                            'ebay': {
                                'name': 'eBay', 
                                'icon': '🏷️', 
                                'oauth': True,
                                'client_id_env': 'EBAY_CLIENT_ID',
                                'client_secret_env': 'EBAY_CLIENT_SECRET',
                                'oauth_url': 'https://auth.ebay.com/oauth2/authorize'
                            }
                        }
                
                        for market_id, market_info in marketplaces.items():
                            with st.expander(f"{market_info['icon']} {market_info['name']}", expanded=False):
                                # Check if credentials exist
                                client_id = os.getenv(market_info['client_id_env'])
                                client_secret = os.getenv(market_info['client_secret_env'])
                                token_key = f"{market_id.upper()}_ACCESS_TOKEN"
                                access_token = os.getenv(token_key)
                        
                                if access_token:
                                    st.success(f"✅ Connected to {market_info['name']}")
                                    if st.button(f"🔄 Reconnect {market_info['name']}", key=f"reconnect_{market_id}"):
                                        st.session_state[f'{market_id}_oauth_flow'] = True
                                else:
                                    st.warning(f"⚠️ {market_info['name']} not connected")
                            
                                    # OAuth setup instructions
                                    st.markdown(f"**To connect {market_info['name']}:**")
                            
                                    if client_id and client_secret:
                                        st.success("✅ API credentials found in .env")
                                
                                        # Generate OAuth URL
                                        redirect_uri = "http://localhost:8507/oauth/callback"
                                        oauth_state = f"{market_id}_oauth_{dt.now().timestamp()}"
                                
                                        if market_id == 'etsy':
                                            scope = "listings_r listings_w transactions_r"
                                            oauth_link = f"{market_info['oauth_url']}?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&scope={scope}&state={oauth_state}"
                                        elif market_id == 'amazon':
                                            oauth_link = f"{market_info['oauth_url']}?application_id={client_id}&state={oauth_state}"
                                        else:  # ebay
                                            scope = "https://api.ebay.com/oauth/api_scope/sell.inventory"
                                            oauth_link = f"{market_info['oauth_url']}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={scope}&state={oauth_state}"
                                
                                        if st.button(f"🔗 Connect with {market_info['name']} OAuth", key=f"market_{market_id}_oauth"):
                                            st.markdown(f"[Click here to authorize]({oauth_link})")
                                            st.info("After authorizing, paste the code below:")
                                    
                                        auth_code = st.text_input(f"Authorization Code", key=f"{market_id}_auth_code", type="password")
                                        if auth_code and st.button(f"Complete {market_info['name']} Setup", key=f"complete_{market_id}"):
                                            st.success(f"✅ {market_info['name']} connected! (Save token to .env as {token_key})")
                                            st.code(f'{token_key}=YOUR_ACCESS_TOKEN_HERE')
                                    else:
                                        st.info(f"Add your {market_info['name']} API credentials to .env:")
                                        st.code(f"""
                {market_info['client_id_env']}=your_client_id
                {market_info['client_secret_env']}=your_client_secret
                                        """)
                                        st.markdown(f"**Get credentials at:** [{market_info['name']} Developer Portal]({market_info['oauth_url'].split('/oauth')[0]})")
            
                    with integration_tabs[2]:  # Social Media
                        st.markdown("##### 📱 Social Media Integration")
                        st.caption("Connect your social accounts for automated posting")
                
                        social_platforms = st.tabs(["🐦 Twitter/X", "📷 Instagram", "📘 Facebook", "🔗 LinkedIn"])
                
                        with social_platforms[0]:  # Twitter
                            st.markdown("**🐦 Twitter/X Connection**")
                    
                            twitter_username = os.getenv('TWITTER_USERNAME')
                            twitter_password = os.getenv('TWITTER_PASSWORD')
                    
                            if twitter_username:
                                st.success(f"✅ Connected: @{twitter_username}")
                        
                                # Test posting
                                st.markdown("---")
                                st.markdown("**📝 Quick Post:**")
                                test_caption = st.text_area("Tweet Content", max_chars=280, key="twitter_test_caption")
                                test_image = st.file_uploader("Attach Image (optional)", type=['png', 'jpg', 'jpeg'], key="twitter_test_image")
                        
                                if st.button("🐦 Post to Twitter", type="primary"):
                                    if test_caption:
                                        with st.spinner("Posting to Twitter..."):
                                            try:
                                                from app.services.ai_twitter_poster import AITwitterPoster
                                                poster = AITwitterPoster(headless=False, browser_type='chrome')
                                        
                                                # Save uploaded image if provided
                                                image_path = None
                                                if test_image:
                                                    import tempfile
                                                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                                                        tmp.write(test_image.getvalue())
                                                        image_path = tmp.name
                                        
                                                if image_path:
                                                    import asyncio
                                                    success = asyncio.run(poster.post_to_twitter(image_path, test_caption))
                                                    if success:
                                                        st.success("✅ Posted to Twitter!")
                                                        st.balloons()
                                                    else:
                                                        st.error("❌ Failed to post. Check terminal for details.")
                                                else:
                                                    st.warning("Please attach an image to post")
                                            except ImportError as e:
                                                st.error(f"Twitter posting requires ai_twitter_poster module: {e}")
                                            except Exception as e:
                                                st.error(f"Error: {e}")
                                    else:
                                        st.warning("Please enter tweet content")
                            else:
                                st.warning("⚠️ Twitter not connected")
                                st.markdown("**Add to your .env file:**")
                                st.code("""
                TWITTER_USERNAME=your_twitter_username
                TWITTER_PASSWORD=your_twitter_password
                ANTHROPIC_API_KEY=your_anthropic_key  # Required for AI browser control
                                """)
                        
                                # Manual credential entry
                                st.markdown("---")
                                st.markdown("**Or enter credentials here:**")
                                new_twitter_user = st.text_input("Twitter Username", key="new_twitter_user")
                                new_twitter_pass = st.text_input("Twitter Password", type="password", key="new_twitter_pass")
                        
                                if st.button("💾 Save Twitter Credentials"):
                                    if new_twitter_user and new_twitter_pass:
                                        # Write to .env
                                        env_path = Path('.env')
                                        env_content = env_path.read_text() if env_path.exists() else ""
                                
                                        if 'TWITTER_USERNAME' not in env_content:
                                            env_content += f"\nTWITTER_USERNAME={new_twitter_user}"
                                        if 'TWITTER_PASSWORD' not in env_content:
                                            env_content += f"\nTWITTER_PASSWORD={new_twitter_pass}"
                                
                                        env_path.write_text(env_content)
                                        st.success("✅ Saved! Restart the app to apply.")
                                    else:
                                        st.warning("Please enter both username and password")
                
                        with social_platforms[1]:  # Instagram
                            st.markdown("**📷 Instagram Connection**")
                    
                            insta_username = os.getenv('INSTAGRAM_USERNAME')
                    
                            if insta_username:
                                st.success(f"✅ Connected: @{insta_username}")
                            else:
                                st.warning("⚠️ Instagram not connected")
                                st.markdown("**Add to your .env file:**")
                                st.code("""
                INSTAGRAM_USERNAME=your_instagram_username
                INSTAGRAM_PASSWORD=your_instagram_password
                                """)
                                st.info("Instagram posting uses browser automation (similar to Twitter)")
                
                        with social_platforms[2]:  # Facebook
                            st.markdown("**📘 Facebook Page Connection**")
                    
                            fb_page_token = os.getenv('FACEBOOK_PAGE_TOKEN')
                    
                            if fb_page_token:
                                st.success("✅ Facebook Page connected")
                            else:
                                st.warning("⚠️ Facebook not connected")
                                st.markdown("**Setup requires:**")
                                st.markdown("1. Create a Facebook App at developers.facebook.com")
                                st.markdown("2. Get a Page Access Token")
                                st.markdown("3. Add to .env: `FACEBOOK_PAGE_TOKEN=your_token`")
                
                        with social_platforms[3]:  # LinkedIn
                            st.markdown("**🔗 LinkedIn Connection**")
                    
                            linkedin_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
                    
                            if linkedin_token:
                                st.success("✅ LinkedIn connected")
                            else:
                                st.warning("⚠️ LinkedIn not connected")
                                st.markdown("**Setup requires:**")
                                st.markdown("1. Create a LinkedIn App at linkedin.com/developers")
                                st.markdown("2. Get OAuth 2.0 access token")
                                st.markdown("3. Add to .env: `LINKEDIN_ACCESS_TOKEN=your_token`")
            
                    with integration_tabs[3]:  # Charity
                        st.markdown("##### 💝 Virtue - Charitable Giving")
                        st.caption("Link your sales to charitable donations")
                
                        st.markdown("""
                        **Virtue Integration** allows you to:
                        - Donate a percentage of sales to charity
                        - Create charity-linked product campaigns
                        - Track your charitable impact
                        """)
                
                        # Initialize virtue settings
                        if 'virtue_settings' not in st.session_state:
                            st.session_state.virtue_settings = {'percent': 5, 'charity': '', 'enabled': False}
                
                        donation_percent = st.slider("Donation Percentage", 1, 25, st.session_state.virtue_settings.get('percent', 5), help="Percent of each sale to donate")
                        charity_name = st.text_input("Charity/Organization Name", value=st.session_state.virtue_settings.get('charity', ''), placeholder="American Red Cross, local food bank...")
                
                        if st.button("💝 Save Virtue Settings"):
                            if charity_name.strip():
                                st.session_state.virtue_settings = {
                                    'percent': donation_percent,
                                    'charity': charity_name,
                                    'enabled': True,
                                    'saved_at': dt.now().isoformat()
                                }
                                st.success(f"✅ Set to donate {donation_percent}% to {charity_name}")
                            else:
                                st.warning("Please enter a charity/organization name")
            
                    with integration_tabs[4]:  # Scheduling
                        st.markdown("##### 📅 Workflow Scheduling")
                        st.caption("Schedule workflows to run automatically")
                
                        # Initialize schedules storage
                        if 'scheduled_workflows' not in st.session_state:
                            st.session_state.scheduled_workflows = []
                
                        # Show existing schedules
                        if st.session_state.scheduled_workflows:
                            st.markdown("**Active Schedules:**")
                            for idx, schedule in enumerate(st.session_state.scheduled_workflows):
                                col_sched, col_del = st.columns([4, 1])
                                with col_sched:
                                    st.info(f"📅 {schedule['workflow']} - {schedule['type']} (Created: {schedule['created'][:10]})")
                                with col_del:
                                    if st.button("🗑️", key=f"del_sched_{idx}"):
                                        st.session_state.scheduled_workflows.pop(idx)
                                        st.rerun()
                            st.markdown("---")
                
                        st.markdown("**Create New Schedule:**")
                        schedule_type = st.selectbox("Schedule Type", ["Daily", "Weekly", "Monthly", "Custom Cron"])
                
                        cron_expr = None
                        if schedule_type == "Custom Cron":
                            cron_expr = st.text_input("Cron Expression", placeholder="0 9 * * 1-5 (9am weekdays)")
                
                        schedule_workflow = st.selectbox("Workflow to Run", ["Content Generation", "Analytics Report", "Social Media Post", "Product Sync"])
                
                        if st.button("📅 Create Schedule"):
                            new_schedule = {
                                'workflow': schedule_workflow,
                                'type': schedule_type,
                                'cron': cron_expr,
                                'created': dt.now().isoformat(),
                                'enabled': True
                            }
                            st.session_state.scheduled_workflows.append(new_schedule)
                            st.success(f"✅ Scheduled {schedule_workflow} to run {schedule_type.lower()}")
                            st.rerun()
        
        with tab_shortcuts:  # Keyboard Shortcuts
                    st.markdown("#### ⌨️ Keyboard Shortcut Customization")
                    st.markdown("Customize keyboard shortcuts for your magic buttons")
                    
                    # Initialize shortcuts settings
                    if 'keyboard_shortcuts' not in st.session_state:
                        st.session_state.keyboard_shortcuts = {}
                    
                    # Check if ShortcutsManager is available (imported at module level)
                    try:
                        from app.services.shortcuts_manager import ShortcutsManager as SM
                        shortcuts_mgr_local = SM()
                        all_shortcuts = shortcuts_mgr_local.load_shortcuts()
                        
                        if all_shortcuts:
                            st.markdown("**Configure Hotkeys for Your Shortcuts:**")
                            
                            for shortcut in all_shortcuts:
                                shortcut_id = shortcut['id']
                                shortcut_name = shortcut.get('name', 'Unnamed')
                                current_hotkey = shortcut.get('hotkey', '')
                                
                                with st.expander(f"{shortcut.get('icon', '⚡')} {shortcut_name}", expanded=False):
                                    col_key1, col_key2 = st.columns([3, 1])
                                    
                                    with col_key1:
                                        # Modifier keys
                                        mod_col1, mod_col2, mod_col3, mod_col4 = st.columns(4)
                                        with mod_col1:
                                            ctrl = st.checkbox("Ctrl", key=f"ctrl_{shortcut_id}", value='Ctrl' in current_hotkey)
                                        with mod_col2:
                                            alt = st.checkbox("Alt", key=f"alt_{shortcut_id}", value='Alt' in current_hotkey)
                                        with mod_col3:
                                            shift = st.checkbox("Shift", key=f"shift_{shortcut_id}", value='Shift' in current_hotkey)
                                        with mod_col4:
                                            cmd = st.checkbox("Cmd", key=f"cmd_{shortcut_id}", value='Cmd' in current_hotkey)
                                        
                                        # Main key
                                        main_key = st.text_input(
                                            "Key",
                                            value=current_hotkey.split('+')[-1] if current_hotkey else '',
                                            max_chars=1,
                                            key=f"key_{shortcut_id}",
                                            placeholder="e.g., P, G, M"
                                        )
                                        
                                        # Build hotkey string
                                        modifiers = []
                                        if cmd:
                                            modifiers.append('Cmd')
                                        if ctrl:
                                            modifiers.append('Ctrl')
                                        if alt:
                                            modifiers.append('Alt')
                                        if shift:
                                            modifiers.append('Shift')
                                        
                                        new_hotkey = '+'.join(modifiers + [main_key.upper()]) if main_key else ''
                                        
                                        if new_hotkey:
                                            st.caption(f"Hotkey: **{new_hotkey}**")
                                            
                                            # Check for conflicts
                                            conflicts = [s['name'] for s in all_shortcuts 
                                                       if s['id'] != shortcut_id and s.get('hotkey') == new_hotkey]
                                            if conflicts:
                                                st.warning(f"⚠️ Conflict with: {', '.join(conflicts)}")
                                    
                                    with col_key2:
                                        if st.button("💾 Save", key=f"save_hotkey_{shortcut_id}", use_container_width=True):
                                            shortcut['hotkey'] = new_hotkey
                                            shortcuts_mgr_local.save_shortcut(shortcut)
                                            st.success("✅ Saved!")
                                            st.rerun()
                                        
                                        if current_hotkey and st.button("🗑️ Clear", key=f"clear_hotkey_{shortcut_id}", use_container_width=True):
                                            shortcut['hotkey'] = ''
                                            shortcuts_mgr_local.save_shortcut(shortcut)
                                            st.success("✅ Cleared!")
                                            st.rerun()
                            
                            st.markdown("---")
                            st.info("💡 **Tip:** Keyboard shortcuts work when you press the key combination. Use Cmd on Mac, Ctrl on Windows/Linux.")
                        else:
                            st.info("📭 No shortcuts created yet. Create shortcuts in the Shortcuts tab!")
                    except (ImportError, Exception) as e:
                        st.warning(f"⚠️ Shortcuts manager not available: {e}")
        
        with tab5:  # Export
                    st.markdown("#### 📤 Export Settings")
                    st.markdown("Export your data in various formats for backup, analysis, or sharing")
            
                    export_tabs = st.tabs(["📊 Campaign Data", "📈 Analytics", "⚡ Shortcuts", "🔧 Full Backup"])
            
                    # Campaign Data Export
                    with export_tabs[0]:
                        st.markdown("##### Export Campaign Data")
                
                        # Gather campaign data
                        campaign_data = {
                            'campaigns': st.session_state.get('campaign_history', []),
                            'generated_products': st.session_state.get('generated_products', []),
                            'blog_posts': st.session_state.get('blog_posts', []),
                            'social_posts': st.session_state.get('social_posts', []),
                            'exported_at': dt.now().isoformat()
                        }
                
                        col_fmt1, col_fmt2, col_fmt3 = st.columns(3)
                
                        with col_fmt1:
                            st.markdown("**JSON Format**")
                            st.caption("Best for importing back into the app")
                            import json
                            campaign_json = json.dumps(campaign_data, indent=2, default=str)
                            st.download_button(
                                "📥 Download JSON",
                                campaign_json,
                                f"campaigns_{dt.now().strftime('%Y%m%d')}.json",
                                "application/json",
                                use_container_width=True
                            )
                
                        with col_fmt2:
                            st.markdown("**CSV Format**")
                            st.caption("Best for spreadsheets")
                            # Convert to CSV
                            import csv
                            import io
                            csv_buffer = io.StringIO()
                            writer = csv.writer(csv_buffer)
                            writer.writerow(['Type', 'Name', 'Description', 'Date', 'Status'])
                            for camp in campaign_data.get('campaigns', []):
                                writer.writerow(['Campaign', camp.get('name', ''), camp.get('description', ''), camp.get('date', ''), camp.get('status', '')])
                            for prod in campaign_data.get('generated_products', []):
                                writer.writerow(['Product', prod.get('name', ''), prod.get('prompt', ''), prod.get('date', ''), 'generated'])
                            st.download_button(
                                "📥 Download CSV",
                                csv_buffer.getvalue(),
                                f"campaigns_{dt.now().strftime('%Y%m%d')}.csv",
                                "text/csv",
                                use_container_width=True
                            )
                
                        with col_fmt3:
                            st.markdown("**Summary Report**")
                            st.caption("Text summary of campaigns")
                            summary = f"""
                Campaign Export Report
                Generated: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}
                =====================================
        
                Total Campaigns: {len(campaign_data.get('campaigns', []))}
                Total Products: {len(campaign_data.get('generated_products', []))}
                Total Blog Posts: {len(campaign_data.get('blog_posts', []))}
                Total Social Posts: {len(campaign_data.get('social_posts', []))}
        
                ---
                Exported by Otto Mate Business Platform
                """
                            st.download_button(
                                "📥 Download Report",
                                summary,
                                f"campaign_report_{dt.now().strftime('%Y%m%d')}.txt",
                                "text/plain",
                                use_container_width=True
                            )
            
                    # Analytics Export
                    with export_tabs[1]:
                        st.markdown("##### Export Analytics Data")
                
                        analytics_data = {
                            'api_usage': {},
                            'performance_metrics': st.session_state.get('performance_metrics', {}),
                            'shortcut_history': st.session_state.get('shortcut_history', []),
                            'exported_at': dt.now().isoformat()
                        }
                
                        # Try to get API usage data
                        try:
                            if API_USAGE_TRACKER_AVAILABLE:
                                from api_usage_tracker import api_tracker
                                analytics_data['api_usage'] = {
                                    'total_cost': api_tracker.get_total_cost(),
                                    'today_cost': api_tracker.get_today_cost(),
                                    'call_count': len(api_tracker.usage_log)
                                }
                        except:
                            pass
                
                        col_ana1, col_ana2 = st.columns(2)
                
                        with col_ana1:
                            analytics_json = json.dumps(analytics_data, indent=2, default=str)
                            st.download_button(
                                "📥 Download Analytics JSON",
                                analytics_json,
                                f"analytics_{dt.now().strftime('%Y%m%d')}.json",
                                "application/json",
                                use_container_width=True
                            )
                
                        with col_ana2:
                            # CSV for analytics
                            ana_csv = io.StringIO()
                            ana_writer = csv.writer(ana_csv)
                            ana_writer.writerow(['Metric', 'Value'])
                            for key, value in analytics_data.items():
                                if isinstance(value, dict):
                                    for k, v in value.items():
                                        ana_writer.writerow([f"{key}.{k}", str(v)])
                                else:
                                    ana_writer.writerow([key, str(value)])
                            st.download_button(
                                "📥 Download Analytics CSV",
                                ana_csv.getvalue(),
                                f"analytics_{dt.now().strftime('%Y%m%d')}.csv",
                                "text/csv",
                                use_container_width=True
                            )
            
                    # Shortcuts Export
                    with export_tabs[2]:
                        st.markdown("##### Export Shortcuts")
                        st.caption("Export your magic buttons for backup or sharing")
                
                        if st.session_state.get('magic_shortcuts'):
                            shortcuts_data = {
                                'version': '1.0',
                                'exported_at': dt.now().isoformat(),
                                'shortcuts': st.session_state.magic_shortcuts
                            }
                            shortcuts_json = json.dumps(shortcuts_data, indent=2)
                            st.download_button(
                                "📥 Download Shortcuts",
                                shortcuts_json,
                                f"shortcuts_{dt.now().strftime('%Y%m%d')}.json",
                                "application/json",
                                use_container_width=True,
                                type="primary"
                            )
                            st.success(f"📊 {len(st.session_state.magic_shortcuts)} shortcuts ready to export")
                        else:
                            st.info("No shortcuts to export. Create some in the Shortcuts tab!")
            
                    # Full Backup
                    with export_tabs[3]:
                        st.markdown("##### Full Platform Backup")
                        st.caption("Export all your data in one file")
                
                        full_backup = {
                            'version': '1.0',
                            'backup_date': dt.now().isoformat(),
                            'campaigns': st.session_state.get('campaign_history', []),
                            'products': st.session_state.get('generated_products', []),
                            'shortcuts': st.session_state.get('magic_shortcuts', []),
                            'shortcut_history': st.session_state.get('shortcut_history', []),
                            'scheduled_items': st.session_state.get('scheduled_items', []),
                            'queue_items': st.session_state.get('queue_items', {}),
                            'settings': {
                                'brand_voice': st.session_state.get('brand_voice', ''),
                                'brand_colors': st.session_state.get('brand_colors', [])
                            }
                        }
                
                        backup_json = json.dumps(full_backup, indent=2, default=str)
                
                        st.download_button(
                            "📥 Download Full Backup",
                            backup_json,
                            f"otto_backup_{dt.now().strftime('%Y%m%d_%H%M%S')}.json",
                            "application/json",
                            use_container_width=True,
                            type="primary"
                        )
                
                        st.markdown("---")
                        st.markdown("##### Restore from Backup")
                        uploaded_backup = st.file_uploader("Upload backup file", type=['json'], key="restore_backup")
                        if uploaded_backup:
                            try:
                                restore_data = json.loads(uploaded_backup.read().decode('utf-8'))
                                st.success(f"✅ Valid backup file from {restore_data.get('backup_date', 'unknown date')}")
                        
                                with st.expander("Preview Backup Contents"):
                                    st.write(f"- Campaigns: {len(restore_data.get('campaigns', []))}")
                                    st.write(f"- Products: {len(restore_data.get('products', []))}")
                                    st.write(f"- Shortcuts: {len(restore_data.get('shortcuts', []))}")
                        
                                if st.button("🔄 Restore Backup", type="primary"):
                                    # Restore data
                                    if restore_data.get('campaigns'):
                                        st.session_state.campaign_history = restore_data['campaigns']
                                    if restore_data.get('products'):
                                        st.session_state.generated_products = restore_data['products']
                                    if restore_data.get('shortcuts'):
                                        st.session_state.magic_shortcuts = restore_data['shortcuts']
                                        if shortcuts_mgr:
                                            for shortcut in restore_data['shortcuts']:
                                                shortcuts_mgr.save_shortcut(shortcut)
                                    st.success("✅ Backup restored successfully!")
                                    st.balloons()
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Invalid backup file: {e}")
        
        with tab6:  # Performance
            st.markdown("#### ⚡ Performance Settings")
            render_performance_settings()
            
            # Ray Distributed Computing
            st.markdown("---")
            try:
                from abp_ray_cluster import render_ray_cluster_ui
                render_ray_cluster_ui()
            except Exception as e:
                st.info(f"ℹ️ Ray distributed computing not available: {e}")

    # Define base tabs list
    base_tabs = [
    "🏠 Dashboard",
    "💬 Chat",
    "🎯 Campaign Planner",
    "🎥 Video Maker",
    "🖼️ Static Ad Creator",
    "📣 Social Poster",
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


    return all_tabs
