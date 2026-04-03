"""
Session Initialization Module

Handles all session state initialization logic.
Extracted from autonomous_business_platform.py
"""

import logging
from typing import Any, Dict

import streamlit as st

logger = logging.getLogger(__name__)


def initialize_session_state() -> None:
    """
    Initialize all session state variables with defaults.

    This should be called once at app startup to ensure all
    necessary session state keys exist.
    """
    # Initialize session manager
    if "session_manager" not in st.session_state:
        from app.services.unified_session_manager import (
            UnifiedSessionManager,
            initialize_session_persistence,
        )

        st.session_state.session_manager = UnifiedSessionManager()
        initialize_session_persistence()
        logger.info("✅ Session manager initialized")

    # Core state
    if "initialized" not in st.session_state:
        st.session_state.initialized = True
        logger.info("✅ Session state initialized")

    # UI state
    _initialize_ui_state()

    # Data state
    _initialize_data_state()

    # Feature flags
    _initialize_feature_flags()

    # API tracking
    _initialize_api_tracking()


def _initialize_ui_state() -> None:
    """Initialize UI-related session state."""
    defaults = {
        "current_tab": 0,
        "current_main_tab": 0,
        "current_subtab": {},
        "sidebar_expanded": True,
        "show_session_manager": False,
        "theme": "light",
        "notifications_enabled": True,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _initialize_data_state() -> None:
    """Initialize data-related session state."""
    defaults = {
        "campaigns": [],
        "products": [],
        "content": [],
        "videos": [],
        "current_campaign": None,
        "generated_files": [],
        "file_library_index": {},
        "campaign_history": [],
        "recent_files": [],
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _initialize_feature_flags() -> None:
    """Initialize feature flag session state."""
    defaults = {
        "auto_save": False,
        "enable_analytics": True,
        "enable_monitoring": True,
        "debug_mode": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _initialize_api_tracking() -> None:
    """Initialize API tracking session state."""
    defaults = {
        "api_keys": {},
        "printify_shop_id": None,
        "shopify_store": None,
        "youtube_authenticated": False,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_session_info() -> Dict[str, Any]:
    """
    Get information about current session state.

    Returns:
        Dict with session statistics
    """
    return {
        "initialized": st.session_state.get("initialized", False),
        "current_tab": st.session_state.get("current_tab", 0),
        "campaigns_count": len(st.session_state.get("campaigns", [])),
        "products_count": len(st.session_state.get("products", [])),
        "files_count": len(st.session_state.get("generated_files", [])),
        "keys_count": len(st.session_state.keys()),
    }
