import streamlit as st
import os

def init_session_defaults():
    """Initialize default session state variables."""
    # Skip if already initialized this session
    if st.session_state.get('_app_initialized', False):
        return
    
    # Load API keys from environment variables (with fallback to empty strings)
    api_keys_from_env = {
        'printify': os.getenv('PRINTIFY_API_KEY', ''),
        'replicate': os.getenv('REPLICATE_API_TOKEN', ''),
        'shopify': os.getenv('SHOPIFY_ACCESS_TOKEN', ''),
        'youtube': os.getenv('YOUTUBE_API_KEY', ''),
        'openai': os.getenv('OPENAI_API_KEY', ''),
        'stability': os.getenv('STABILITY_API_KEY', ''),
        'clipdrop': os.getenv('CLIPDROP_API_KEY', ''),
        'luma': os.getenv('LUMA_API_KEY', ''),
        'anthropic': os.getenv('ANTHROPIC_API_KEY', ''),
        'printify_shop_id': os.getenv('PRINTIFY_SHOP_ID', ''),
    }
    
    default_states = {
        'randomized_concept': "",
        'current_step': 0,
        'show_template_editor': False,
        'show_shop_form': False,
        'config': {},
        'api_keys': api_keys_from_env,
        'shopify_api': None,
        'youtube_service': None,
        'current_campaign': None,
        'campaign_plan': None,
        'campaign_history': [],
        'campaign_generator': None,
        'generated_assets': {},
        'selected_tab': 0,
        'active_agent': None,
        'session_manager': None,
        'final_video': None,
        'chain_pipeline': [],
        'chain_results': [],
        # Product Studio
        'product_studio_results': [],
        'printify_uploads': [],
        'printify_products': [],
        'printify_api': None,
        # Content Generation
        'content_generation_history': [],
        # Playground
        'playground_results': [],
        # Workflows
        'workflows': {},
        'current_workflow': None,
        'workflow_running': False,
        # Queue items
        'queue_items': {
            'pending': [],
            'in_progress': [],
            'completed': [],
            'failed': []
        },
        # Scheduled items
        'scheduled_items': [],
        # Shopify
        'shopify_url': '',
        'shopify_api_key': '',
        'shopify_api_secret': '',
        'shopify_access_token': '',
    }

    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Initialize experimental features preferences
    if 'enable_experimental_features' not in st.session_state:
        st.session_state.enable_experimental_features = True  # Default to enabled
    if 'fullscreen_chat_mode' not in st.session_state:
        st.session_state.fullscreen_chat_mode = False
    
    # Mark as initialized to skip on future reruns
    st.session_state._app_initialized = True
