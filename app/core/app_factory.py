"""
Application Factory Module

Creates and configures the Streamlit application.
Extracted from autonomous_business_platform.py
"""

import logging
import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from app.core.container import setup_dependencies
from app.core.exceptions import ErrorContext, handle_errors
from app.core.session_init import initialize_session_state
from app.core.tab_loader import get_tab_renderer

logger = logging.getLogger(__name__)


def configure_environment() -> None:
    """Configure environment variables and system paths."""
    # Add app directories to path
    base_dir = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(base_dir / "app" / "tabs"))
    sys.path.insert(0, str(base_dir / "app" / "services"))
    sys.path.insert(0, str(base_dir / "app" / "utils"))
    sys.path.insert(0, str(base_dir))

    # SDL/Pygame configuration (macOS fix)
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

    # Performance optimizations
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")

    # Load environment variables
    load_dotenv()

    logger.info("✅ Environment configured")


def configure_streamlit() -> None:
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="Autonomous Business Platform",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    logger.info("✅ Streamlit configured")


@handle_errors(show_user=True, log_error=True)
def initialize_app() -> None:
    """
    Initialize the application.

    This should be called once at the start of the app.
    """
    with ErrorContext("Application initialization"):
        # Configure environment
        configure_environment()

        # Set up dependency injection
        setup_dependencies()

        # Configure Streamlit
        configure_streamlit()

        # Initialize session state
        initialize_session_state()

        logger.info("✅ Application initialized successfully")


def create_app() -> None:
    """
    Main application entry point.

    This is the thin entry point that delegates to modular components.
    """
    # Initialize app (idempotent)
    initialize_app()

    # Render UI
    from app.ui.layout import render_main_layout

    render_main_layout()
