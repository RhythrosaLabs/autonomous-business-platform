"""
Session State Manager
Saves and loads the complete app state including:
- Current tab
- All campaigns
- All products
- All content
- All videos
- Sidebar state
- Shortcuts
- Workflows
- Chat history
- Settings
"""

import streamlit as st
import json
import os
from datetime import datetime
from pathlib import Path
import pickle
from typing import Dict, Any

class SessionStateManager:
    """Manages saving and loading complete app sessions"""
    
    SESSION_DIR = Path.home() / ".printify_sessions"
    
    def __init__(self):
        """Initialize session directory"""
        self.SESSION_DIR.mkdir(exist_ok=True)
    
    def get_session_list(self) -> list:
        """Get all saved sessions"""
        if not self.SESSION_DIR.exists():
            return []
        
        sessions = []
        for session_file in sorted(self.SESSION_DIR.glob("*.session"), reverse=True):
            try:
                with open(session_file, 'rb') as f:
                    session_data = pickle.load(f)
                sessions.append({
                    'name': session_file.stem,
                    'timestamp': session_data.get('timestamp', 'Unknown'),
                    'tab': session_data.get('current_tab', 'Unknown'),
                    'campaigns': len(session_data.get('campaigns', [])),
                    'products': len(session_data.get('products', [])),
                    'content': len(session_data.get('content', [])),
                })
            except Exception as e:
                st.warning(f"Error reading session {session_file.stem}: {str(e)}")
        
        return sessions
    
    def _get_state_keys(self) -> Dict[str, Any]:
        """Return mapping of session keys to default values."""
        return {
            'campaigns': [], 'products': [], 'content': [], 'videos': [],
            'current_main_tab': 0, 'current_subtab': {}, 'sidebar_expanded': True,
            'shortcuts': {}, 'workflows': [], 'brand_settings': {},
            'brand_colors': {}, 'brand_templates': {}, 'chat_history': [],
            'chat_sessions': {}, 'batch_jobs': {}, 'file_library_filter': 'all',
            'current_file_tab': 0
        }

    def save_session(self, session_name: str = None) -> bool:
        """Save current app state"""
        try:
            if not session_name:
                session_name = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            session_name = "".join(c for c in session_name if c.isalnum() or c in ('_', '-'))
            
            session_data = {
                'timestamp': datetime.now().isoformat(),
                'session_name': session_name,
                'settings': {
                    'theme': st.session_state.get('theme', 'light'),
                    'notifications_enabled': st.session_state.get('notifications_enabled', True),
                    'auto_save': st.session_state.get('auto_save', False),
                }
            }
            
            # Save all standard keys
            for key, default in self._get_state_keys().items():
                # Map current_main_tab to current_tab for backward compatibility if needed
                save_key = 'current_tab' if key == 'current_main_tab' else key
                session_data[save_key] = st.session_state.get(key, default)
            
            session_file = self.SESSION_DIR / f"{session_name}.session"
            with open(session_file, 'wb') as f:
                pickle.dump(session_data, f)
            
            return True
        except Exception as e:
            st.error(f"Failed to save session: {str(e)}")
            return False
    
    def load_session(self, session_name: str) -> bool:
        """Load a saved session"""
        try:
            session_file = self.SESSION_DIR / f"{session_name}.session"
            if not session_file.exists():
                st.error(f"Session '{session_name}' not found")
                return False
            
            with open(session_file, 'rb') as f:
                session_data = pickle.load(f)
            
            # Restore standard keys
            for key, default in self._get_state_keys().items():
                # Handle key mapping
                load_key = 'current_tab' if key == 'current_main_tab' else key
                st.session_state[key] = session_data.get(load_key, default)
            
            # Restore settings
            settings = session_data.get('settings', {})
            st.session_state['theme'] = settings.get('theme', 'light')
            st.session_state['notifications_enabled'] = settings.get('notifications_enabled', True)
            st.session_state['auto_save'] = settings.get('auto_save', False)
            
            return True
        except Exception as e:
            st.error(f"Failed to load session: {str(e)}")
            return False
    
    def delete_session(self, session_name: str) -> bool:
        """
        Delete a saved session
        
        Args:
            session_name: Name of session to delete (without .session extension)
        
        Returns:
            bool: True if deleted successfully
        """
        try:
            session_file = self.SESSION_DIR / f"{session_name}.session"
            
            if session_file.exists():
                session_file.unlink()
                return True
            else:
                st.warning(f"Session '{session_name}' not found")
                return False
        
        except Exception as e:
            st.error(f"Failed to delete session: {str(e)}")
            return False
    
    def export_session(self, session_name: str, export_path: str = None) -> bytes:
        """
        Export session as downloadable file
        
        Args:
            session_name: Name of session to export
            export_path: Optional custom export path
        
        Returns:
            bytes: Session file bytes for download
        """
        try:
            session_file = self.SESSION_DIR / f"{session_name}.session"
            
            if not session_file.exists():
                st.error(f"Session '{session_name}' not found")
                return None
            
            with open(session_file, 'rb') as f:
                return f.read()
        
        except Exception as e:
            st.error(f"Failed to export session: {str(e)}")
            return None
    
    def import_session(self, session_file_bytes: bytes, session_name: str) -> bool:
        """
        Import session from uploaded file
        
        Args:
            session_file_bytes: Bytes of session file
            session_name: Name for imported session
        
        Returns:
            bool: True if imported successfully
        """
        try:
            # Sanitize session name
            session_name = "".join(c for c in session_name if c.isalnum() or c in ('_', '-'))
            
            session_file = self.SESSION_DIR / f"{session_name}.session"
            
            with open(session_file, 'wb') as f:
                f.write(session_file_bytes)
            
            return True
        
        except Exception as e:
            st.error(f"Failed to import session: {str(e)}")
            return False
    
    def get_session_info(self, session_name: str) -> dict:
        """
        Get detailed info about a session
        
        Args:
            session_name: Name of session
        
        Returns:
            dict: Session metadata and statistics
        """
        try:
            session_file = self.SESSION_DIR / f"{session_name}.session"
            
            if not session_file.exists():
                return None
            
            with open(session_file, 'rb') as f:
                session_data = pickle.load(f)
            
            return {
                'name': session_name,
                'timestamp': session_data.get('timestamp', 'Unknown'),
                'current_tab': session_data.get('current_tab', 'Unknown'),
                'campaigns': len(session_data.get('campaigns', [])),
                'products': len(session_data.get('products', [])),
                'content': len(session_data.get('content', [])),
                'videos': len(session_data.get('videos', [])),
                'shortcuts': len(session_data.get('shortcuts', {})),
                'workflows': len(session_data.get('workflows', [])),
                'chat_sessions': len(session_data.get('chat_sessions', {})),
            }
        
        except Exception as e:
            st.error(f"Failed to get session info: {str(e)}")
            return None


def render_session_manager_modal():
    """Render session manager modal dialog"""
    manager = SessionStateManager()
    
    # Get sessions list
    sessions = manager.get_session_list()
    
    # Create tabs for better organization
    tab1, tab2, tab3 = st.tabs(["💾 Save Session", "📂 Load Session", "⚙️ Manage"])
    
    with tab1:
        st.write("**Save your current workspace state**")
        session_name = st.text_input("Session name (optional):", 
                                     placeholder="Leave blank for auto-timestamp", 
                                     key="session_save_input")
        if st.button("💾 Save Current Session", use_container_width=True, key="save_btn"):
            if manager.save_session(session_name):
                st.success("✅ Session saved successfully!")
                st.session_state.show_session_manager = False
                st.rerun()
    
    with tab2:
        st.write("**Load a previously saved workspace**")
        if sessions:
            session_options = {s['name']: s for s in sessions}
            selected = st.selectbox("Available sessions:", 
                                   list(session_options.keys()),
                                   key="session_load_select")
            
            session = session_options[selected]
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Campaigns", session['campaigns'])
            with col2:
                st.metric("Products", session['products'])
            with col3:
                st.metric("Content", session['content'])
            with col4:
                st.metric("Videos", session['videos'])
            
            st.caption(f"Last saved: {session['timestamp']}")
            
            if st.button("📂 Load This Session", use_container_width=True, type="primary", key="load_btn"):
                if manager.load_session(selected):
                    st.success("✅ Session loaded! Restarting app...")
                    st.session_state.show_session_manager = False
                    st.rerun()
        else:
            st.info("📭 No saved sessions yet. Save one in the Save tab!")
    
    with tab3:
        st.write("**Manage your saved sessions**")
        
        col_delete, col_export = st.columns(2)
        
        with col_delete:
            st.subheader("Delete Session")
            if sessions:
                delete_session = st.selectbox("Select to delete:", 
                                             [s['name'] for s in sessions],
                                             key="session_delete_select")
                if st.button("🗑️ Delete", use_container_width=True, key="delete_btn"):
                    if manager.delete_session(delete_session):
                        st.success("✅ Session deleted")
                        st.rerun()
            else:
                st.info("No sessions to delete")
        
        with col_export:
            st.subheader("Export/Import")
            if sessions:
                export_session = st.selectbox("Select to export:", 
                                             [s['name'] for s in sessions],
                                             key="session_export_select")
                session_bytes = manager.export_session(export_session)
                if session_bytes:
                    st.download_button(
                        label="📥 Download Session",
                        data=session_bytes,
                        file_name=f"{export_session}.session",
                        mime="application/octet-stream",
                        use_container_width=True,
                        key="download_btn"
                    )
            
            uploaded = st.file_uploader("📤 Import session file:", type="session", key="session_import")
            if uploaded:
                if st.button("📤 Import Session", use_container_width=True, key="import_btn"):
                    import_name = uploaded.name.replace('.session', '')
                    if manager.import_session(uploaded.read(), import_name):
                        st.success("✅ Session imported!")
                        st.rerun()
