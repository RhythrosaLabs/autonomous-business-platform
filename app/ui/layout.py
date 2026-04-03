"""
UI Layout Module

Handles the main application layout and navigation.
Extracted from autonomous_business_platform.py
"""

import logging

import streamlit as st

from app.core.exceptions import handle_errors
from app.core.tab_loader import get_available_tabs, get_tab_renderer

logger = logging.getLogger(__name__)


@handle_errors(show_user=True, log_error=True)
def render_main_layout() -> None:
    """
    Render the main application layout with navigation.
    """
    # Render header
    render_header()

    # Render sidebar navigation
    selected_tab = render_sidebar()

    # Render selected tab content
    render_tab_content(selected_tab)

    # Render footer
    render_footer()


def render_header() -> None:
    """Render application header."""
    st.title("🚀 Autonomous Business Platform")
    st.caption("AI-Powered Business Automation Suite")


def render_sidebar() -> str:
    """
    Render sidebar with navigation.

    Returns:
        Selected tab name
    """
    with st.sidebar:
        st.header("Navigation")

        # Get available tabs
        tabs = get_available_tabs()

        # Tab selection
        if "current_main_tab" not in st.session_state:
            st.session_state.current_main_tab = 0

        # Create radio buttons for tab selection
        selected_index = st.radio(
            "Select a page:",
            range(len(tabs)),
            format_func=lambda i: tabs[i],
            key="main_tab_selector",
            index=st.session_state.current_main_tab,
        )

        # Update session state
        st.session_state.current_main_tab = selected_index

        # Session manager shortcut
        st.divider()
        if st.button("💾 Session Manager", use_container_width=True):
            st.session_state.show_session_manager = True

        # Settings
        with st.expander("⚙️ Settings"):
            theme = st.selectbox(
                "Theme",
                ["light", "dark"],
                index=0 if st.session_state.get("theme", "light") == "light" else 1,
            )
            st.session_state.theme = theme

            st.session_state.auto_save = st.checkbox(
                "Auto-save session",
                value=st.session_state.get("auto_save", False),
            )

        return tabs[selected_index]


@handle_errors(show_user=True, log_error=True, default_return=None)
def render_tab_content(tab_name: str) -> None:
    """
    Render the content for the selected tab.

    Args:
        tab_name: Name of the tab to render
    """
    # Show session manager modal if requested
    if st.session_state.get("show_session_manager", False):
        render_session_manager_modal()
        return

    # Get tab renderer
    renderer = get_tab_renderer(tab_name)

    if renderer is None:
        st.error(f"❌ Could not load tab: {tab_name}")
        st.info("Please check the logs for more information.")
        return

    # Render the tab
    try:
        renderer()
    except Exception as e:
        logger.error(f"Error rendering tab {tab_name}: {e}")
        st.error(f"❌ Error rendering tab: {str(e)}")
        with st.expander("🔍 Error Details"):
            st.exception(e)


def render_session_manager_modal() -> None:
    """Render session manager modal."""
    from app.services.unified_session_manager import render_session_manager_modal

    st.header("💾 Session Manager")
    render_session_manager_modal()

    if st.button("✖️ Close", key="close_session_manager"):
        st.session_state.show_session_manager = False
        st.rerun()


def render_footer() -> None:
    """Render application footer."""
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        st.caption("🚀 Autonomous Business Platform")

    with col2:
        st.caption("v2.0 | Made with ❤️")

    with col3:
        from app.core.session_init import get_session_info

        info = get_session_info()
        st.caption(f"📊 {info['campaigns_count']} campaigns | {info['files_count']} files")
