"""
Unified Session Manager for Autonomous Business Platform

Combines the best features from both previous session managers:
- JSON-based persistence (more portable than pickle)
- Comprehensive state tracking
- Export/Import functionality
- Auto-save on exit
- File library tracking

This replaces both session_manager.py and session_state_manager.py
"""

import streamlit as st
import json
import os
import atexit
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Session storage paths
SESSION_DIR = Path("sessions")
SESSION_DIR.mkdir(exist_ok=True)
CURRENT_SESSION_FILE = SESSION_DIR / "current_session.json"


class UnifiedSessionManager:
    """
    Unified session manager with JSON persistence and comprehensive state tracking.

    Features:
    - JSON-based storage (portable, human-readable)
    - Auto-save on exit
    - Export/Import sessions
    - File library tracking
    - Campaign history tracking
    """

    def __init__(self, session_dir: Path = SESSION_DIR):
        """
        Initialize session manager.

        Args:
            session_dir: Directory for storing session files
        """
        self.session_dir = session_dir
        self.session_dir.mkdir(exist_ok=True)
        self.current_session_file = self.session_dir / "current_session.json"

        # Register auto-save on exit
        atexit.register(self.auto_save_on_exit)

    def _get_persistable_keys(self) -> Dict[str, Any]:
        """
        Return mapping of all persistable session keys with their defaults.

        Returns:
            Dict mapping key names to default values
        """
        return {
            # Core data
            "campaigns": [],
            "products": [],
            "content": [],
            "videos": [],
            "current_campaign": None,
            # UI state
            "current_main_tab": 0,
            "current_tab": 0,  # Backward compatibility
            "current_subtab": {},
            "sidebar_expanded": True,
            # Configuration
            "api_keys": {},
            "settings": {},
            "theme": "light",
            "notifications_enabled": True,
            "auto_save": False,
            # Features
            "shortcuts": {},
            "workflows": [],
            "saved_agents": [],
            "chat_history": [],
            "chat_sessions": {},
            "batch_jobs": {},
            # Brand
            "brand_settings": {},
            "brand_colors": {},
            "brand_templates": {},
            # File management
            "generated_files": [],
            "file_library_index": {},
            "file_library_filter": "all",
            "current_file_tab": 0,
            "recent_files": [],
            # Platform integrations
            "printify_shop_id": None,
            "shopify_store": None,
            "youtube_authenticated": False,
            # History
            "campaign_history": [],
            "last_file_scan": None,
        }

    def save_session(self, session_name: Optional[str] = None) -> bool:
        """
        Save current session state to JSON file.

        Args:
            session_name: Optional custom name. If None, uses timestamp.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Generate session name if not provided
            if not session_name:
                session_name = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Sanitize session name
            session_name = "".join(c for c in session_name if c.isalnum() or c in ("_", "-"))

            # Prepare session data
            session_data = {
                "timestamp": datetime.now().isoformat(),
                "session_name": session_name,
                "version": "2.0",  # Version for tracking format changes
                "state": {},
            }

            # Get all persistable keys
            persistable_keys = self._get_persistable_keys()

            # Save each key from session state
            for key, default in persistable_keys.items():
                if key in st.session_state:
                    value = st.session_state[key]

                    # Handle special cases for large objects
                    if key == "campaigns" and isinstance(value, list):
                        # Save campaign metadata only
                        session_data["state"][key] = [
                            {
                                "name": c.get("name"),
                                "timestamp": c.get("timestamp"),
                                "path": c.get("path"),
                                "status": c.get("status", "unknown"),
                            }
                            for c in value
                            if isinstance(c, dict)
                        ]
                    else:
                        # Try to serialize the value
                        try:
                            json.dumps(value)  # Test if serializable
                            session_data["state"][key] = value
                        except (TypeError, ValueError) as e:
                            logger.warning(f"Skipping non-serializable key '{key}': {e}")
                            continue

            # Write to file
            session_file = self.session_dir / f"{session_name}.json"
            with open(session_file, "w") as f:
                json.dump(session_data, f, indent=2)

            # Also save as current session
            with open(self.current_session_file, "w") as f:
                json.dump(session_data, f, indent=2)

            logger.info(f"✅ Session saved: {session_name}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to save session: {e}")
            return False

    def load_session(self, session_name: Optional[str] = None) -> bool:
        """
        Load session state from JSON file.

        Args:
            session_name: Optional specific session name. If None, loads current session.

        Returns:
            True if successful, False otherwise
        """
        try:
            # Determine which file to load
            if session_name:
                session_file = self.session_dir / f"{session_name}.json"
            else:
                session_file = self.current_session_file

            if not session_file.exists():
                logger.info(f"No session found: {session_file}")
                return False

            # Load session data
            with open(session_file, "r") as f:
                session_data = json.load(f)

            # Restore state
            state = session_data.get("state", {})
            for key, value in state.items():
                st.session_state[key] = value

            logger.info(f"✅ Session loaded: {session_data.get('session_name', 'unknown')}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to load session: {e}")
            return False

    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all saved sessions with metadata.

        Returns:
            List of dicts with session metadata
        """
        sessions = []

        for session_file in self.session_dir.glob("*.json"):
            try:
                with open(session_file, "r") as f:
                    data = json.load(f)

                # Calculate statistics
                state = data.get("state", {})
                sessions.append(
                    {
                        "name": data.get("session_name", session_file.stem),
                        "filename": session_file.stem,
                        "timestamp": data.get("timestamp"),
                        "path": str(session_file),
                        "file_size": session_file.stat().st_size,
                        "campaigns": len(state.get("campaigns", [])),
                        "products": len(state.get("products", [])),
                        "content": len(state.get("content", [])),
                        "videos": len(state.get("videos", [])),
                        "current_tab": state.get("current_tab", "Unknown"),
                    }
                )
            except Exception as e:
                logger.error(f"Error reading session {session_file}: {e}")

        # Sort by timestamp, newest first
        sessions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return sessions

    def delete_session(self, session_name: str) -> bool:
        """
        Delete a saved session file.

        Args:
            session_name: Name of session to delete (without .json extension)

        Returns:
            True if successful, False otherwise
        """
        try:
            session_file = self.session_dir / f"{session_name}.json"

            if session_file.exists():
                session_file.unlink()
                logger.info(f"✅ Session deleted: {session_name}")
                return True
            else:
                logger.warning(f"⚠️ Session not found: {session_name}")
                return False
        except Exception as e:
            logger.error(f"❌ Failed to delete session: {e}")
            return False

    def export_session(self, session_name: str) -> Optional[bytes]:
        """
        Export session as downloadable JSON.

        Args:
            session_name: Name of session to export

        Returns:
            Session data as bytes, or None if failed
        """
        try:
            session_file = self.session_dir / f"{session_name}.json"

            if not session_file.exists():
                logger.error(f"Session not found: {session_name}")
                return None

            with open(session_file, "rb") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to export session: {e}")
            return None

    def import_session(self, uploaded_file) -> bool:
        """
        Import session from uploaded JSON file.

        Args:
            uploaded_file: Streamlit UploadedFile object or file bytes

        Returns:
            True if successful, False otherwise
        """
        try:
            # Handle both UploadedFile and raw bytes
            if hasattr(uploaded_file, "read"):
                session_data = json.load(uploaded_file)
            else:
                session_data = json.loads(uploaded_file)

            # Generate import session name
            import_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_name = f"imported_{import_time}"

            # Save as new session
            session_file = self.session_dir / f"{session_name}.json"
            with open(session_file, "w") as f:
                json.dump(session_data, f, indent=2)

            # Load the imported session
            return self.load_session(session_name)

        except Exception as e:
            logger.error(f"Failed to import session: {e}")
            return False

    def get_session_info(self, session_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about a session.

        Args:
            session_name: Optional specific session. If None, uses current.

        Returns:
            Dict with session metadata
        """
        try:
            if session_name:
                session_file = self.session_dir / f"{session_name}.json"
            else:
                session_file = self.current_session_file

            if not session_file.exists():
                return {"exists": False}

            with open(session_file, "r") as f:
                data = json.load(f)

            state = data.get("state", {})
            return {
                "exists": True,
                "name": data.get("session_name"),
                "timestamp": data.get("timestamp"),
                "version": data.get("version", "1.0"),
                "keys_count": len(state),
                "file_size": session_file.stat().st_size,
                "campaigns": len(state.get("campaigns", [])),
                "products": len(state.get("products", [])),
                "videos": len(state.get("videos", [])),
            }
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return {"exists": False, "error": str(e)}

    def auto_save_on_exit(self) -> None:
        """Auto-save session when application exits."""
        try:
            self.save_session("auto_save_on_exit")
            logger.info("✅ Auto-save on exit completed")
        except Exception as e:
            logger.error(f"❌ Auto-save on exit failed: {e}")

    def clear_session(self) -> None:
        """Clear all session state except essential keys."""
        keys_to_keep = {"session_manager", "theme", "notifications_enabled"}
        keys_to_delete = [k for k in st.session_state.keys() if k not in keys_to_keep]

        for key in keys_to_delete:
            del st.session_state[key]

        logger.info("✅ Session cleared")


# ========================================
# UI RENDERING FUNCTIONS
# ========================================


def render_session_manager_modal() -> None:
    """Render comprehensive session manager modal UI."""
    if "session_manager" not in st.session_state:
        st.session_state.session_manager = UnifiedSessionManager()

    manager = st.session_state.session_manager

    # Create tabs for organization
    tab1, tab2, tab3, tab4 = st.tabs(["💾 Save", "📂 Load", "📤 Export/Import", "⚙️ Manage"])

    with tab1:
        _render_save_tab(manager)

    with tab2:
        _render_load_tab(manager)

    with tab3:
        _render_export_import_tab(manager)

    with tab4:
        _render_manage_tab(manager)


def _render_save_tab(manager: UnifiedSessionManager) -> None:
    """Render save session tab."""
    st.write("**Save your current workspace state**")

    session_name = st.text_input(
        "Session name (optional):",
        placeholder="Leave blank for auto-timestamp",
        key="session_save_input",
    )

    if st.button("💾 Save Current Session", use_container_width=True, key="save_btn"):
        if manager.save_session(session_name if session_name else None):
            st.success("✅ Session saved successfully!")
            st.session_state.show_session_manager = False
            st.rerun()
        else:
            st.error("❌ Failed to save session")


def _render_load_tab(manager: UnifiedSessionManager) -> None:
    """Render load session tab."""
    st.write("**Load a previously saved workspace**")

    sessions = manager.list_sessions()

    if not sessions:
        st.info("📭 No saved sessions yet. Save one in the Save tab!")
        return

    # Create selectbox with session names
    session_options = {s["name"]: s for s in sessions}
    selected = st.selectbox(
        "Available sessions:", list(session_options.keys()), key="session_load_select"
    )

    # Show session statistics
    session = session_options[selected]
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Campaigns", session["campaigns"])
    with col2:
        st.metric("Products", session["products"])
    with col3:
        st.metric("Content", session["content"])
    with col4:
        st.metric("Videos", session["videos"])

    st.caption(f"Last saved: {session['timestamp']}")

    if st.button("📂 Load This Session", use_container_width=True, type="primary", key="load_btn"):
        if manager.load_session(session["filename"]):
            st.success("✅ Session loaded! Restarting app...")
            st.session_state.show_session_manager = False
            st.rerun()
        else:
            st.error("❌ Failed to load session")


def _render_export_import_tab(manager: UnifiedSessionManager) -> None:
    """Render export/import tab."""
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📤 Export Session")
        sessions = manager.list_sessions()

        if sessions:
            export_session = st.selectbox(
                "Select to export:", [s["name"] for s in sessions], key="session_export_select"
            )

            session_bytes = manager.export_session(
                next(s["filename"] for s in sessions if s["name"] == export_session)
            )

            if session_bytes:
                st.download_button(
                    label="📥 Download Session",
                    data=session_bytes,
                    file_name=f"{export_session}.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_btn",
                )
        else:
            st.info("No sessions to export")

    with col2:
        st.subheader("📥 Import Session")
        uploaded = st.file_uploader("Upload session file:", type="json", key="session_import")

        if uploaded:
            if st.button("📤 Import Session", use_container_width=True, key="import_btn"):
                if manager.import_session(uploaded):
                    st.success("✅ Session imported and loaded!")
                    st.rerun()
                else:
                    st.error("❌ Failed to import session")


def _render_manage_tab(manager: UnifiedSessionManager) -> None:
    """Render manage sessions tab."""
    sessions = manager.list_sessions()

    if not sessions:
        st.info("📭 No saved sessions to manage")
        return

    st.write("**All Saved Sessions**")

    for session in sessions:
        with st.expander(f"📋 {session['name']}"):
            col_info, col_actions = st.columns([2, 1])

            with col_info:
                st.caption(f"**Created:** {session['timestamp']}")
                st.caption(f"**Size:** {session['file_size']} bytes")
                st.caption(
                    f"**Items:** {session['campaigns']} campaigns, {session['products']} products"
                )

            with col_actions:
                if st.button(
                    "🗑️ Delete", key=f"del_{session['filename']}", use_container_width=True
                ):
                    if manager.delete_session(session["filename"]):
                        st.success("Deleted!")
                        st.rerun()


def render_session_manager_ui() -> None:
    """Render inline session manager UI (for settings page)."""
    st.markdown("### 💾 Session Manager")

    if "session_manager" not in st.session_state:
        st.session_state.session_manager = UnifiedSessionManager()

    manager = st.session_state.session_manager

    # Current session info
    session_info = manager.get_session_info()

    if session_info.get("exists"):
        st.success(f"✅ Session Active: {session_info.get('name', 'Unknown')}")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Keys Stored", session_info.get("keys_count", 0))
        with col2:
            st.metric("Campaigns", session_info.get("campaigns", 0))
        with col3:
            st.metric("Products", session_info.get("products", 0))
    else:
        st.info("ℹ️ No active session")

    # Action buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("💾 Save", use_container_width=True):
            if manager.save_session():
                st.success("Saved!")
                st.rerun()

    with col2:
        if st.button("📂 Load", use_container_width=True):
            if manager.load_session():
                st.success("Loaded!")
                st.rerun()

    with col3:
        if st.button("🔄 New", use_container_width=True):
            manager.clear_session()
            st.success("New session!")
            st.rerun()


def initialize_session_persistence() -> None:
    """Initialize session persistence on app startup."""
    if "session_manager" not in st.session_state:
        st.session_state.session_manager = UnifiedSessionManager()

        # Try to load last session automatically
        st.session_state.session_manager.load_session()

        # Initialize tracking if not exists
        defaults = st.session_state.session_manager._get_persistable_keys()
        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value


# ========================================
# FILE TRACKING UTILITIES
# ========================================


def track_generated_file(
    file_path: str,
    file_type: str,
    campaign_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Track a newly generated file in the file library.

    Args:
        file_path: Path to file
        file_type: File type/category
        campaign_name: Associated campaign
        metadata: Additional metadata
    """
    if "generated_files" not in st.session_state:
        st.session_state.generated_files = []

    path_obj = Path(file_path)

    file_info = {
        "path": str(path_obj),
        "name": path_obj.name,
        "type": file_type,
        "size": path_obj.stat().st_size if path_obj.exists() else 0,
        "created": datetime.now().isoformat(),
        "campaign": campaign_name or "unknown",
        "metadata": metadata or {},
    }

    st.session_state.generated_files.append(file_info)

    # Auto-save
    if "session_manager" in st.session_state:
        st.session_state.session_manager.save_session()


def get_files_by_type(file_type: str) -> List[Dict[str, Any]]:
    """Get all files of a specific type."""
    return [f for f in st.session_state.get("generated_files", []) if f["type"] == file_type]


def get_files_by_campaign(campaign_name: str) -> List[Dict[str, Any]]:
    """Get all files from a specific campaign."""
    return [
        f for f in st.session_state.get("generated_files", []) if f["campaign"] == campaign_name
    ]


# Backward compatibility aliases
SessionManager = UnifiedSessionManager
SessionStateManager = UnifiedSessionManager
