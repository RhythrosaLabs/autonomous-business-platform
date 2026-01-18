# Ensure all necessary imports are included at the top of the file
# Fix SDL threading issue on macOS - must be set before any imports
import os
import sys
# Add app directories to path for Streamlit Cloud (symlinks may not work)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'tabs'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'services'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'utils'))
sys.path.insert(0, os.path.dirname(__file__))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
# Performance optimizations
os.environ.setdefault('STREAMLIT_SERVER_HEADLESS', 'true')
os.environ.setdefault('STREAMLIT_BROWSER_GATHER_USAGE_STATS', 'false')

from abp_imports_common import (
    time, logging, uuid, datetime, timedelta, Path, json, random, re, asyncio,
    Any, Dict, Tuple, Optional, requests, setup_logger
)
from PIL import Image, ImageFilter, ImageOps, ImageEnhance
from dotenv import load_dotenv

import streamlit as st
from abp_campaign_results import render_campaign_complete_summary
from abp_config import AppConfig
from abp_ui_components import render_about_guide, render_command_line_guide

# Set up logging
logger = setup_logger(__name__)

# Maintain backward compatibility alias
dt = datetime

# ========================================
# LAZY LOAD TAB MODULES (Performance Optimization)
# ========================================
# Only import tab modules when they're actually needed
# This reduces initial app load time by 40-60%

def get_tab_renderer(tab_name: str):
    """Dynamically import and return the appropriate tab renderer based on tab name"""
    # Map tab names to their module and function
    tab_renderers = {
        "🏠 Dashboard": ('app.tabs.abp_dashboard', 'render_dashboard_tab'),
        "⚡ Shortcuts": ('app.tabs.abp_shortcuts', 'render_shortcuts_tab'),
        "🤖 Task Queue": ('app.tabs.abp_task_queue', 'render_task_queue_tab'),
        "🔄 Job Monitor": ('app.tabs.abp_advanced_job_monitor', 'render_advanced_job_monitor_tab'),
        "📦 Product Studio": ('app.tabs.abp_products', 'render_product_studio_tab'),
        "💾 Digital Products": ('app.tabs.abp_digital_products', 'render_digital_products_tab'),
        "🎯 Campaign Creator": ('app.tabs.abp_campaigns', 'render_campaign_creator_tab'),
        "📝 Content Generator": ('app.tabs.abp_content', 'render_content_generator_tab'),
        "🎬 Video Producer": ('app.tabs.abp_video', 'render_video_producer_tab'),
        "🎮 Playground": ('app.tabs.abp_playground', 'render_playground_tab'),
        "🔧 Workflows": ('app.tabs.abp_custom_workflows', 'render_custom_workflows_tab'),
        "📅 Calendar": ('app.tabs.abp_calendar', 'render_calendar_tab'),
        "📓 Journal": ('app.tabs.abp_journal', 'render_journal_tab'),
        "🔍 Contact Finder": ('app.tabs.abp_contacts', 'render_contact_finder_tab'),
        "👥 Customers": ('app.tabs.abp_customers', 'render_customers_tab'),
        "📊 Analytics": ('app.tabs.abp_analytics', 'render_analytics_tab'),
        "🎨 Brand Templates": ('app.tabs.abp_brand_templates', 'render_brand_templates_tab'),
        "💌 Email Outreach": ('app.tabs.abp_email_outreach', 'render_email_outreach_tab'),
        "�� Music Platforms": ('app.tabs.abp_music_platforms_pro', 'render_music_platforms_tab'),
        "📁 File Library": ('app.tabs.abp_files', 'render_file_library_tab'),
        "🌐 Browser-Use": ('app.tabs.abp_browser_use', 'render_browser_use_tab'),
    }
    
    if tab_name not in tab_renderers:
        return None
    
    module_name, func_name = tab_renderers[tab_name]
    try:
        module = __import__(module_name, fromlist=[func_name])
        return getattr(module, func_name)
    except ImportError as e:
        st.error(f"❌ Failed to load tab module '{module_name}'")
        with st.expander("🔍 Debug Info"):
            st.code(f"Import Error: {str(e)}")
            st.info(f"Looking for: {module_name}.py in sys.path")
            st.code(f"sys.path includes:\n" + "\n".join(sys.path[:5]))
        logger.error(f"ImportError loading {module_name}: {e}")
        return None
    except AttributeError as e:
        st.error(f"❌ Function '{func_name}' not found in module '{module_name}'")
        with st.expander("🔍 Debug Info"):
            st.code(f"AttributeError: {str(e)}")
        logger.error(f"AttributeError in {module_name}: {e}")

# ========================================
# APP CONFIGURATION
# ========================================
# AppConfig is imported from abp_config.py

# ========================================
# IMPORTS
# ========================================

# Import performance optimizations (lazy - no session state calls at import)
try:
    from performance_optimizations import (
        get_replicate_client,
        get_replicate_api,
        get_youtube_service,
        get_printify_api,
        get_shopify_api,
        LazyLoader,
        fragment_render,
        PerformanceMonitor,
        timed_operation,
        optimize_image_for_display,
        render_performance_settings
    )
    PERF_OPTIMIZATIONS_AVAILABLE = True
except ImportError:
    PERF_OPTIMIZATIONS_AVAILABLE = False
    def render_performance_settings():
        st.info("⚙️ Performance settings module not available. Install 'performance_optimizations' for advanced options.")

# Import platform integrations (API tracking, session persistence, performance boost)
try:
    from platform_integrations import (
        init_all_integrations,
        tracked_replicate_run,
        tracked_replicate_text_generation,
        render_integrations_sidebar,
        render_recovery_check,
        render_full_usage_dashboard,
        get_draft,
        auto_save_form,
        API_TRACKER_AVAILABLE,
        SESSION_PERSISTENCE_AVAILABLE,
        PERFORMANCE_BOOST_AVAILABLE
    )
    PLATFORM_INTEGRATIONS_AVAILABLE = True
except ImportError as e:
    PLATFORM_INTEGRATIONS_AVAILABLE = False
    API_TRACKER_AVAILABLE = False
    SESSION_PERSISTENCE_AVAILABLE = False
    PERFORMANCE_BOOST_AVAILABLE = False
    def render_integrations_sidebar():
        pass  # Silent - sidebar element
    def render_recovery_check():
        pass  # Silent - background check
    def render_full_usage_dashboard():
        st.info("📊 Usage dashboard requires 'platform_integrations' module for API tracking and analytics.")
    def tracked_replicate_run(client, model, input_params, operation_name=None):
        return client.run(model, input=input_params)
    def init_all_integrations():
        return {}
    logging.warning(f"⚠️ Platform integrations not available: {e}")

# Import Playground models configuration
from playground_models import (
    IMAGE_MODELS, VIDEO_MODELS, EDITING_MODELS, MARKETING_MODELS,
    VIDEO_EDITING_MODELS, MODEL_3D, MUSIC_MODELS, SPEECH_MODELS,
    build_model_input
)

# Configure Streamlit for better performance
st.set_page_config(
    page_title="Autonomous Business Platform",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================================
# IMPORTS - ENHANCED FEATURES
# ========================================

try:
    from enhanced_features import (
        GlobalSearchManager,
        SmartSuggestionEngine,
        ContentOptimizer,
        SmartTemplateGenerator,
        BatchProcessingQueue,
        ContentCalendarManager,
        QuickActionsBar,
        render_enhanced_features_ui
    )
    ENHANCED_FEATURES_AVAILABLE = True
except ImportError:
    ENHANCED_FEATURES_AVAILABLE = False

try:
    from smart_dashboard_widget import (
        SmartDashboard,
        ActivityFeed,
        NotificationCenter
    )
    SMART_DASHBOARD_AVAILABLE = True
except ImportError:
    SMART_DASHBOARD_AVAILABLE = False

try:
    from session_state_manager import SessionStateManager, render_session_manager_modal
    SESSION_MANAGER_AVAILABLE = True
except ImportError:
    SESSION_MANAGER_AVAILABLE = False
    def render_session_manager_modal():
        pass

# ========================================
# PERFORMANCE: CACHING FUNCTIONS
# ========================================
# Caching functions are imported from abp_utils.py
from abp_utils import (
    get_cached_replicate_client,
    get_cached_replicate_api,
    cached_scan_files,
    cached_scan_products,
    cached_list_campaigns,
    clear_file_cache,
    get_env_api_keys
)







# Import AI Twitter poster (uses Anthropic Claude via browser-use)
try:
    from ai_twitter_poster import post_to_twitter_ai
    # Check if Anthropic key is available
    if os.getenv('ANTHROPIC_API_KEY'):
        AI_TWITTER_AVAILABLE = True
        logging.info("✅ AI Twitter poster (Anthropic Claude) loaded successfully")
    else:
        AI_TWITTER_AVAILABLE = False
        logging.warning("⚠️ AI Twitter poster disabled - ANTHROPIC_API_KEY not found")
except ImportError as e:
    AI_TWITTER_AVAILABLE = False
    logging.warning(f"⚠️ AI Twitter poster not available: {e}")

from abp_state import init_session_defaults

def initialize_session_state():
    """Initialize all session state variables - runs once per session."""
    init_session_defaults()

# Call the refactored function at the top of the file
initialize_session_state()

# Import and initialize onboarding
try:
    from abp_onboarding import check_and_show_onboarding, render_getting_started_sidebar
    ONBOARDING_AVAILABLE = True
except ImportError:
    ONBOARDING_AVAILABLE = False
    def check_and_show_onboarding():
        pass
    def render_getting_started_sidebar():
        pass

# Show onboarding for first-time users (non-disruptive)
check_and_show_onboarding()

# Initialize platform integrations (API tracker, session persistence, performance)
if PLATFORM_INTEGRATIONS_AVAILABLE:
    platform_integrations = init_all_integrations()
    logging.info("✅ Platform integrations initialized")
else:
    platform_integrations = {}

from session_manager import SessionManager
if 'session_manager' not in st.session_state or st.session_state.session_manager is None:
    st.session_state.session_manager = SessionManager()

# Initialize Cross-Page State Manager for persistent state across pages
from cross_page_state import (
    init_cross_page_state,
    get_state_manager,
    save_current_page_state,
    restore_page_to_session,
    render_active_tasks_sidebar,
    render_task_monitor,
    render_campaign_status_banner,
    run_in_background,
    TaskStatus
)
cross_page_mgr = init_cross_page_state()

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lazy import for campaign_generator_service (takes 0.6s)
_campaign_generator_module = None
def _get_campaign_generator():
    """Lazy load EnhancedCampaignGenerator on first use."""
    global _campaign_generator_module
    if _campaign_generator_module is None:
        from campaign_generator_service import EnhancedCampaignGenerator
        _campaign_generator_module = EnhancedCampaignGenerator
    return _campaign_generator_module

# Alias for compatibility - creates instance on first call
def EnhancedCampaignGenerator(*args, **kwargs):
    return _get_campaign_generator()(*args, **kwargs)

# Lazy import for chat_assistant (takes 1.6s to import due to otto_engine chain)
# Import only when actually used
_chat_assistant_module = None
def get_chat_assistant():
    """Lazy load chat_assistant module on first use."""
    global _chat_assistant_module
    if _chat_assistant_module is None:
        from chat_assistant import render_chat_interface, render_autonomous_todo
        _chat_assistant_module = {
            'render_chat_interface': render_chat_interface,
            'render_autonomous_todo': render_autonomous_todo
        }
    return _chat_assistant_module

def render_chat_interface(**kwargs):
    """Wrapper for lazy-loaded chat interface."""
    return get_chat_assistant()['render_chat_interface'](**kwargs)

def render_autonomous_todo():
    """Wrapper for lazy-loaded todo renderer."""
    return get_chat_assistant()['render_autonomous_todo']()

# Import enhanced task queue
try:
    from task_queue_engine import render_enhanced_task_queue, EnhancedTaskQueue
    ENHANCED_TASK_QUEUE_AVAILABLE = True
except ImportError:
    ENHANCED_TASK_QUEUE_AVAILABLE = False

# Import shortcuts manager for persistent magic buttons
try:
    from shortcuts_manager import (
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
    # Create global manager instance for TAB 14
    shortcuts_mgr = ShortcutsManager()
except ImportError:
    SHORTCUTS_MANAGER_AVAILABLE = False
    shortcuts_mgr = None  # Fallback when module not available
    def init_shortcuts():
        if 'magic_shortcuts' not in st.session_state:
            st.session_state.magic_shortcuts = []
    def save_shortcuts(shortcuts):
        pass
    def load_shortcuts():
        return []
    SHORTCUT_ICONS = ["⚡", "🚀", "🎯", "💰", "🔥", "✨", "💎", "🎨", "📦", "🛒"]
    BUTTON_STYLES = {"primary": {"label": "Primary"}, "secondary": {"label": "Secondary"}}
    BUTTON_SIZES = {"small": {"label": "Small"}, "medium": {"label": "Medium"}, "large": {"label": "Large"}}
    SHORTCUT_CATEGORIES = {"🎨 Content Creation": "#9b59b6", "📱 Social Media": "#3498db"}

# Initialize shortcuts at startup - load from disk if available
if 'magic_shortcuts' not in st.session_state:
    st.session_state.magic_shortcuts = []
    if shortcuts_mgr:
        loaded = shortcuts_mgr.load_shortcuts()
        if loaded:
            st.session_state.magic_shortcuts = loaded

from session_manager import (
    initialize_session_persistence, 
    render_session_manager_ui,
    track_generated_file,
    scan_and_index_files
)
from unified_agent_builder import render_unified_agent_builder

# Lazy load video_export_utils (takes 5.5s due to moviepy import)
_video_export_module = None
def _get_video_export_utils():
    """Lazy load video export utilities on first use."""
    global _video_export_module
    if _video_export_module is None:
        from video_export_utils import (
            get_resolution_dimensions,
            get_bitrate_value,
            retry_with_exponential_backoff,
            batch_export_all_platforms,
            create_batch_export_zip,
            enhance_error_message
        )
        _video_export_module = {
            'get_resolution_dimensions': get_resolution_dimensions,
            'get_bitrate_value': get_bitrate_value,
            'retry_with_exponential_backoff': retry_with_exponential_backoff,
            'batch_export_all_platforms': batch_export_all_platforms,
            'create_batch_export_zip': create_batch_export_zip,
            'enhance_error_message': enhance_error_message
        }
    return _video_export_module

# Wrapper functions for video export utils
def get_resolution_dimensions(*args, **kwargs):
    return _get_video_export_utils()['get_resolution_dimensions'](*args, **kwargs)
def get_bitrate_value(*args, **kwargs):
    return _get_video_export_utils()['get_bitrate_value'](*args, **kwargs)
def retry_with_exponential_backoff(*args, **kwargs):
    return _get_video_export_utils()['retry_with_exponential_backoff'](*args, **kwargs)
def batch_export_all_platforms(*args, **kwargs):
    return _get_video_export_utils()['batch_export_all_platforms'](*args, **kwargs)
def create_batch_export_zip(*args, **kwargs):
    return _get_video_export_utils()['create_batch_export_zip'](*args, **kwargs)
def enhance_error_message(*args, **kwargs):
    return _get_video_export_utils()['enhance_error_message'](*args, **kwargs)

from brand.brand_template_generator import generate_dynamic_cta_text
from ai_model_manager import ModelFallbackManager, QualityAssessor, VideoModel, ModelPriority
from prompt_templates import PromptTemplateLibrary, PromptEnhancer

# Lazy load platform_helpers (takes 0.5s due to printify import)
_platform_helpers_cache = None
def _get_platform_helpers():
    """Lazy load platform helpers on first use."""
    global _platform_helpers_cache
    if _platform_helpers_cache is None:
        from platform_helpers import (
            _get_printify_api,
            _render_printify_product_config,
            _resolve_campaign_printify_config,
            _build_default_printify_config,
            _send_design_to_printify,
            _printify_selection_ready,
            _ensure_replicate_client,
            _get_replicate_token,
            _slugify,
            create_campaign_directory,
            save_campaign_metadata,
            _extract_article_html
        )
        _platform_helpers_cache = {
            '_get_printify_api': _get_printify_api,
            '_render_printify_product_config': _render_printify_product_config,
            '_resolve_campaign_printify_config': _resolve_campaign_printify_config,
            '_build_default_printify_config': _build_default_printify_config,
            '_send_design_to_printify': _send_design_to_printify,
            '_printify_selection_ready': _printify_selection_ready,
            '_ensure_replicate_client': _ensure_replicate_client,
            '_get_replicate_token': _get_replicate_token,
            '_slugify': _slugify,
            'create_campaign_directory': create_campaign_directory,
            'save_campaign_metadata': save_campaign_metadata,
            '_extract_article_html': _extract_article_html
        }
    return _platform_helpers_cache

# Wrapper functions for platform_helpers
def _get_printify_api(*args, **kwargs): return _get_platform_helpers()['_get_printify_api'](*args, **kwargs)
def _render_printify_product_config(*args, **kwargs): return _get_platform_helpers()['_render_printify_product_config'](*args, **kwargs)
def _resolve_campaign_printify_config(*args, **kwargs): return _get_platform_helpers()['_resolve_campaign_printify_config'](*args, **kwargs)
def _build_default_printify_config(*args, **kwargs): return _get_platform_helpers()['_build_default_printify_config'](*args, **kwargs)
def _send_design_to_printify(*args, **kwargs): return _get_platform_helpers()['_send_design_to_printify'](*args, **kwargs)
def _printify_selection_ready(*args, **kwargs): return _get_platform_helpers()['_printify_selection_ready'](*args, **kwargs)
def _ensure_replicate_client(*args, **kwargs): return _get_platform_helpers()['_ensure_replicate_client'](*args, **kwargs)
def _get_replicate_token(*args, **kwargs): return _get_platform_helpers()['_get_replicate_token'](*args, **kwargs)
def _slugify(*args, **kwargs): return _get_platform_helpers()['_slugify'](*args, **kwargs)
def create_campaign_directory(*args, **kwargs): return _get_platform_helpers()['create_campaign_directory'](*args, **kwargs)
def save_campaign_metadata(*args, **kwargs): return _get_platform_helpers()['save_campaign_metadata'](*args, **kwargs)
def _extract_article_html(*args, **kwargs): return _get_platform_helpers()['_extract_article_html'](*args, **kwargs)

# Lazy import modular functions (Phase 2 optimization - eliminates code duplication)
# The modules package imports moviepy which is slow (~2.8s)
_modules_cache = None
def _get_modules():
    """Lazy load modules package on first use."""
    global _modules_cache
    if _modules_cache is None:
        from modules import (
            # Video Generation
            generate_ken_burns_video,
            add_cta_card,
            orchestrate_video_generation,
            # AI Generation (Replicate API)
            generate_script_with_llama,
            parse_script_segments,
            generate_voiceover_audio,
            generate_background_music,
            generate_image_with_flux,
            VOICE_MAP,
            MUSIC_PROMPTS,
            # Audio Processing
            prepare_background_music,
            mix_audio_tracks,
            load_audio_clip,
            # File Utilities
            download_file,
            save_text_file,
            save_binary_file,
            create_temp_directory,
            cleanup_directory,
            sanitize_filename
        )
        _modules_cache = {
            'generate_ken_burns_video': generate_ken_burns_video,
            'add_cta_card': add_cta_card,
            'orchestrate_video_generation': orchestrate_video_generation,
            'generate_script_with_llama': generate_script_with_llama,
            'parse_script_segments': parse_script_segments,
            'generate_voiceover_audio': generate_voiceover_audio,
            'generate_background_music': generate_background_music,
            'generate_image_with_flux': generate_image_with_flux,
            'VOICE_MAP': VOICE_MAP,
            'MUSIC_PROMPTS': MUSIC_PROMPTS,
            'prepare_background_music': prepare_background_music,
            'mix_audio_tracks': mix_audio_tracks,
            'load_audio_clip': load_audio_clip,
            'download_file': download_file,
            'save_text_file': save_text_file,
            'save_binary_file': save_binary_file,
            'create_temp_directory': create_temp_directory,
            'cleanup_directory': cleanup_directory,
            'sanitize_filename': sanitize_filename
        }
    return _modules_cache

# Wrapper functions for lazy-loaded modules
def generate_ken_burns_video(*args, **kwargs): return _get_modules()['generate_ken_burns_video'](*args, **kwargs)
def add_cta_card(*args, **kwargs): return _get_modules()['add_cta_card'](*args, **kwargs)
def orchestrate_video_generation(*args, **kwargs): return _get_modules()['orchestrate_video_generation'](*args, **kwargs)
def generate_script_with_llama(*args, **kwargs): return _get_modules()['generate_script_with_llama'](*args, **kwargs)
def parse_script_segments(*args, **kwargs): return _get_modules()['parse_script_segments'](*args, **kwargs)
def generate_voiceover_audio(*args, **kwargs): return _get_modules()['generate_voiceover_audio'](*args, **kwargs)
def generate_background_music(*args, **kwargs): return _get_modules()['generate_background_music'](*args, **kwargs)
def generate_image_with_flux(*args, **kwargs): return _get_modules()['generate_image_with_flux'](*args, **kwargs)
def prepare_background_music(*args, **kwargs): return _get_modules()['prepare_background_music'](*args, **kwargs)
def mix_audio_tracks(*args, **kwargs): return _get_modules()['mix_audio_tracks'](*args, **kwargs)
def load_audio_clip(*args, **kwargs): return _get_modules()['load_audio_clip'](*args, **kwargs)
def download_file(*args, **kwargs): return _get_modules()['download_file'](*args, **kwargs)
def save_text_file(*args, **kwargs): return _get_modules()['save_text_file'](*args, **kwargs)
def save_binary_file(*args, **kwargs): return _get_modules()['save_binary_file'](*args, **kwargs)
def create_temp_directory(*args, **kwargs): return _get_modules()['create_temp_directory'](*args, **kwargs)
def cleanup_directory(*args, **kwargs): return _get_modules()['cleanup_directory'](*args, **kwargs)
def sanitize_filename(*args, **kwargs): return _get_modules()['sanitize_filename'](*args, **kwargs)
# Constants need special handling
def _get_voice_map(): return _get_modules()['VOICE_MAP']
def _get_music_prompts(): return _get_modules()['MUSIC_PROMPTS']


# Style and color prompts for Product Studio
STYLE_PROMPTS = {
    "Minimalist": "clean, simple, minimal design, modern aesthetic, white space",
    "Vintage": "retro, vintage style, aged look, classic design, nostalgic",
    "Abstract": "abstract art, geometric patterns, modern art style, artistic",
    "Watercolor": "watercolor painting, soft artistic style, dreamy",
    "Bold & Graphic": "bold graphics, strong lines, pop art style, eye-catching",
    "Hand-drawn": "hand-drawn illustration, sketch style, artistic feel",
    "Photography": "professional product photography, realistic, high quality",
    "3D Render": "3D rendered, digital art, modern CGI style, dimensional",
    "Cyberpunk": "cyberpunk aesthetic, neon lights, futuristic, tech noir",
    "Kawaii": "cute kawaii style, adorable, japanese illustration, chibi",
    "Gothic": "dark gothic style, dramatic, mysterious, elegant darkness",
    "Boho": "bohemian style, free spirit, earthy, organic patterns",
    "Art Deco": "art deco style, 1920s glamour, geometric elegance, golden age",
    "Vaporwave": "vaporwave aesthetic, retro 80s, synthwave, nostalgic digital",
    "Line Art": "clean line art, elegant strokes, modern illustration",
    "Graffiti": "street art style, urban graffiti, bold expression"
}

COLOR_PROMPTS = {
    "Vibrant": "vibrant colors, bold color palette, saturated, energetic",
    "Pastel": "soft pastel colors, gentle tones, dreamy palette",
    "Monochrome": "black and white, grayscale, minimalist palette, elegant",
    "Earth Tones": "natural earth tones, browns and greens, organic",
    "Neon": "neon colors, bright glowing effects, electric",
    "Jewel Tones": "rich jewel tones, deep colors, luxurious",
    "Neutral": "neutral colors, beige, cream, soft palette, understated",
    "Sunset": "warm sunset colors, orange, pink, golden hour palette",
    "Ocean": "ocean blues and teals, aquatic palette, serene",
    "Forest": "deep forest greens, natural woodland palette, organic",
    "Candy": "bright candy colors, playful, fun and sweet palette",
    "Metallic": "metallic sheen, gold, silver, bronze accents, luxe"
}

# AI-powered design enhancement prompts
DESIGN_ENHANCERS = {
    "Print-Ready": "high resolution, clean edges, suitable for printing, sharp details",
    "Transparent BG": "isolated design, transparent background ready, clean cutout",
    "Seamless Tile": "seamless pattern, tileable design, repeating pattern",
    "T-Shirt Ready": "centered composition, t-shirt print design, wearable art",
    "Poster Ready": "vertical composition, poster-worthy, wall art quality",
    "Logo Style": "logo design, brandable, scalable vector style, iconic"
}

# ========================================
# SIDEBAR: MAIN NAVIGATION
# ========================================
from abp_sidebar import render_sidebar
all_tabs = render_sidebar(
    enhanced_features_available=ENHANCED_FEATURES_AVAILABLE,
    platform_integrations_available=PLATFORM_INTEGRATIONS_AVAILABLE,
    render_chat_interface_func=render_chat_interface,
    render_about_guide_func=render_about_guide,
    render_command_line_guide_func=render_command_line_guide,
    render_integrations_sidebar_func=render_integrations_sidebar
)

# ========================================
# SESSION MANAGER MODAL
# ========================================
if 'show_session_manager' not in st.session_state:
    st.session_state.show_session_manager = False

if st.session_state.show_session_manager and SESSION_MANAGER_AVAILABLE:
    st.divider()
    col1, col2 = st.columns([0.9, 0.1])
    with col1:
        st.subheader("📂 Session Manager")
    with col2:
        if st.button("✕", key="close_session_manager", use_container_width=True):
            st.session_state.show_session_manager = False
            st.rerun()
    
    st.divider()
    render_session_manager_modal()
    st.divider()

# ========================================
# CROSS-PAGE STATE: Restore and show active tasks
# ========================================
# Restore any saved page state for the main dashboard
restore_page_to_session("main_dashboard")

# Show active background tasks in sidebar
render_active_tasks_sidebar()

# Track current tab for state persistence
if 'current_main_tab' not in st.session_state:
    st.session_state.current_main_tab = 0

# Ensure current_main_tab is within bounds of filtered tabs
if st.session_state.current_main_tab >= len(all_tabs):
    st.session_state.current_main_tab = 0

# ========================================
# NAVIGATION WITH LAZY RENDERING
# ========================================

# Row 1: Compact emoji quick-access buttons (filtered by role)
# IMPORTANT: Check buttons BEFORE selectbox to ensure button clicks aren't overridden
all_quick_items = [
    ("🏠", 0, "🏠 Dashboard"), ("⚡", 1, "⚡ Shortcuts"), ("🤖", 2, "🤖 Task Queue"), 
    ("🔄", 3, "🔄 Job Monitor"), ("📦", 4, "📦 Product Studio"), ("💾", 5, "💾 Digital Products"), 
    ("🎯", 6, "🎯 Campaign Creator"),
    ("📝", 7, "📝 Content Generator"), ("🎬", 8, "🎬 Video Producer"), ("🎮", 9, "🎮 Playground"),
    ("🔧", 10, "🔧 Workflows"), ("📅", 11, "📅 Calendar"), ("📓", 12, "📓 Journal"),
    ("🔍", 13, "🔍 Contact Finder"), ("👥", 14, "👥 Customers"), ("📊", 15, "📊 Analytics"),
    ("🎨", 16, "🎨 Brand Templates"), ("💌", 17, "💌 Email Outreach"), ("🎵", 18, "🎵 Music Platforms"), 
    ("📁", 19, "📁 File Library"), ("🌐", 20, "🌐 Browser-Use")
]

all_quick_items = [
    ("🏠", 0, "🏠 Dashboard"), ("⚡", 1, "⚡ Shortcuts"), ("🤖", 2, "�� Task Queue"), 
    ("🔄", 3, "🔄 Job Monitor"), ("📦", 4, "📦 Product Studio"), ("💾", 5, "💾 Digital Products"), 
    ("🎯", 6, "🎯 Campaign Creator"),
    ("📝", 7, "📝 Content Generator"), ("🎬", 8, "🎬 Video Producer"), ("🎮", 9, "🎮 Playground"),
    ("🔧", 10, "🔧 Workflows"), ("📅", 11, "📅 Calendar"), ("📓", 12, "📓 Journal"),
    ("🔍", 13, "🔍 Contact Finder"), ("👥", 14, "👥 Customers"), ("📊", 15, "📊 Analytics"),
    ("🎨", 16, "🎨 Brand Templates"), ("💌", 17, "💌 Email Outreach"), ("🎵", 18, "🎵 Music Platforms"), 
    ("📁", 19, "📁 File Library"), ("🌐", 20, "🌐 Browser-Use")
]

# Filter quick items to only show visible tabs
quick_items = [(emoji, idx, name) for emoji, idx, name in all_quick_items if name in all_tabs]

# Only create columns for visible tabs
if quick_items:
    btn_cols = st.columns(len(quick_items))
    for i, (emoji, idx, name) in enumerate(quick_items):
        with btn_cols[i]:
            # Get the correct index in the filtered all_tabs list
            try:
                filtered_idx = all_tabs.index(name)
                is_selected = (filtered_idx == st.session_state.current_main_tab)
                if st.button(emoji, key=f"q_{idx}", help=name, type="primary" if is_selected else "secondary"):
                    st.session_state.current_main_tab = filtered_idx
                    st.rerun()
            except ValueError:
                # Tab not in visible list, skip
                pass

# Row 2: Dropdown selector (placed AFTER buttons to not interfere)
selected_tab_name = st.selectbox(
    "📑 Navigate",
    all_tabs,
    index=st.session_state.current_main_tab,
    key="main_nav_select",
    label_visibility="collapsed"
)
selected_tab_idx = all_tabs.index(selected_tab_name)
if selected_tab_idx != st.session_state.current_main_tab:
    st.session_state.current_main_tab = selected_tab_idx
    st.rerun()

# ========================================
# GLOBAL STATE INITIALIZATION
# ========================================
# Initialize advanced_model_params with defaults to prevent NameError in other tabs
# This ensures Product Studio (Tab 3) works even if Campaign Creator (Tab 5) hasn't run
advanced_model_params = {
    "image": {},
    "video_quality": {},
    "model_selection": {}
}

selected_tab_idx = st.session_state.current_main_tab
# Update selected_tab_name to match the actual selected index
selected_tab_name = all_tabs[selected_tab_idx]


# ========================================
# RENDER SELECTED TAB (Lazy Loading for Performance)
# ========================================
# Only the selected tab is loaded and rendered
# This provides HUGE performance boost (40-60% faster page navigation)

with st.spinner("Loading tab..."):
    renderer = get_tab_renderer(selected_tab_name)
    
    if renderer:
        try:
            # Special handling for tabs with additional parameters
            if selected_tab_name == "🏠 Dashboard":
                renderer(
                    smart_dashboard_available=SMART_DASHBOARD_AVAILABLE,
                    cross_page_mgr=cross_page_mgr
                )
            elif selected_tab_name == "🤖 Task Queue":
                replicate_api = st.session_state.get('replicate_client')
                printify_api = st.session_state.get('printify_api')
                shopify_api = st.session_state.get('shopify_api')
                youtube_api = st.session_state.get('youtube_service')
                
                renderer(
                    enhanced_available=ENHANCED_TASK_QUEUE_AVAILABLE,
                    replicate_api=replicate_api,
                    printify_api=printify_api,
                    shopify_api=shopify_api,
                    youtube_api=youtube_api
                )
            else:
                # All other tabs use simple renderer
                renderer()
        except Exception as e:
            st.error(f"❌ Error rendering tab: {str(e)}")
            import traceback
            with st.expander("📋 Full Error Traceback"):
                st.code(traceback.format_exc())
    else:
        st.error(f"❌ Tab not found: {selected_tab_name}")
        st.info("Renderer returned None - check import errors above")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "🚀 Autonomous Business Platform Pro v2.1 | Powered by Multi-Agent AI & Browser-Use"
    "</div>",
    unsafe_allow_html=True
)
