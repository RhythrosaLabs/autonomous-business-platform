"""
Session State Persistence Manager
Automatically saves and loads session state for continuity across app restarts.
"""

import streamlit as st
import json
import os
from pathlib import Path
from datetime import datetime
import atexit
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

SESSION_DIR = Path("sessions")
CURRENT_SESSION_FILE = SESSION_DIR / "current_session.json"
AUTO_SAVE_INTERVAL = 60  # seconds


class SessionManager:
    """Manages session state persistence with auto-save functionality."""
    
    def __init__(self):
        """Initialize session manager and create session directory."""
        SESSION_DIR.mkdir(exist_ok=True)
        self.session_path = CURRENT_SESSION_FILE
        
        # Register auto-save on exit
        atexit.register(self.auto_save_on_exit)
    
    def save_session(self, session_name: str = None) -> bool:
        """
        Save current session state to JSON file.
        
        Args:
            session_name: Optional custom name for the session.
                         If None, uses timestamp.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Prepare session data
            session_data = {
                'timestamp': datetime.now().isoformat(),
                'session_name': session_name or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'state': {}
            }
            
            # Keys to persist (exclude streamlit internal keys)
            persistable_keys = [
                'campaigns',
                'current_campaign',
                'api_keys',
                'settings',
                'chat_history',
                'workflow_definitions',
                'saved_agents',
                'recent_files',
                'printify_shop_id',
                'shopify_store',
                'youtube_authenticated',
                'generated_files',  # NEW: Track all generated files
                'file_library_index',  # NEW: File library metadata
                'campaign_history',  # NEW: Complete campaign history
                'last_file_scan'  # NEW: Last time files were scanned
            ]
            
            # Save each key from session state
            for key in persistable_keys:
                if key in st.session_state:
                    value = st.session_state[key]
                    
                    # Handle special cases
                    if key == 'campaigns' and isinstance(value, list):
                        # Only save campaign metadata, not full objects
                        session_data['state'][key] = [
                            {
                                'name': c.get('name'),
                                'timestamp': c.get('timestamp'),
                                'path': c.get('path')
                            } for c in value if isinstance(c, dict)
                        ]
                    else:
                        # Try to serialize the value
                        try:
                            json.dumps(value)  # Test if serializable
                            session_data['state'][key] = value
                        except (TypeError, ValueError):
                            logger.warning(f"Skipping non-serializable key: {key}")
            
            # Write to file
            with open(self.session_path, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            logger.info(f"Session saved: {session_name or 'auto-save'}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False
    
    def load_session(self, session_file: Path = None) -> bool:
        """
        Load session state from JSON file.
        
        Args:
            session_file: Optional path to specific session file.
                         If None, loads from CURRENT_SESSION_FILE.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            file_to_load = session_file or self.session_path
            
            if not file_to_load.exists():
                logger.info("No existing session found")
                return False
            
            with open(file_to_load, 'r') as f:
                session_data = json.load(f)
            
            # Restore state
            state = session_data.get('state', {})
            for key, value in state.items():
                st.session_state[key] = value
            
            logger.info(f"Session loaded: {session_data.get('session_name', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return False
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all saved sessions.
        
        Returns:
            List of session metadata dicts
        """
        sessions = []
        
        for session_file in SESSION_DIR.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)
                
                sessions.append({
                    'name': data.get('session_name', session_file.stem),
                    'timestamp': data.get('timestamp'),
                    'path': str(session_file),
                    'file_size': session_file.stat().st_size
                })
            except Exception as e:
                logger.error(f"Error reading session {session_file}: {e}")
        
        # Sort by timestamp, newest first
        sessions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return sessions
    
    def delete_session(self, session_path: str) -> bool:
        """
        Delete a saved session file.
        
        Args:
            session_path: Path to the session file to delete
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            Path(session_path).unlink()
            logger.info(f"Session deleted: {session_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False
    
    def export_session(self, session_name: str) -> bytes:
        """
        Export session as downloadable JSON.
        
        Args:
            session_name: Name for the exported session
        
        Returns:
            bytes: JSON data as bytes
        """
        self.save_session(session_name)
        
        with open(self.session_path, 'rb') as f:
            return f.read()
    
    def import_session(self, uploaded_file) -> bool:
        """
        Import session from uploaded JSON file.
        
        Args:
            uploaded_file: Streamlit UploadedFile object
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Read uploaded file
            session_data = json.load(uploaded_file)
            
            # Save to new file
            import_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            import_path = SESSION_DIR / f"imported_{import_time}.json"
            
            with open(import_path, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            # Load the imported session
            return self.load_session(import_path)
            
        except Exception as e:
            logger.error(f"Failed to import session: {e}")
            return False
    
    def auto_save_on_exit(self):
        """Auto-save session when application exits."""
        try:
            self.save_session("auto_save_on_exit")
            logger.info("Auto-save on exit completed")
        except Exception as e:
            logger.error(f"Auto-save on exit failed: {e}")
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Get information about current session.
        
        Returns:
            Dict with session metadata
        """
        if not self.session_path.exists():
            return {'exists': False}
        
        try:
            with open(self.session_path, 'r') as f:
                data = json.load(f)
            
            return {
                'exists': True,
                'name': data.get('session_name'),
                'timestamp': data.get('timestamp'),
                'keys_count': len(data.get('state', {})),
                'file_size': self.session_path.stat().st_size
            }
        except Exception as e:
            logger.error(f"Error getting session info: {e}")
            return {'exists': False, 'error': str(e)}


def render_session_manager_ui():
    """Render session manager UI in the app."""
    st.markdown("### 💾 Session Manager")
    
    # Initialize manager
    if 'session_manager' not in st.session_state:
        st.session_state.session_manager = SessionManager()
    
    manager = st.session_state.session_manager
    
    # Current session info
    session_info = manager.get_session_info()
    
    if session_info.get('exists'):
        st.success(f"✅ Session Active")
        st.caption(f"Last saved: {session_info.get('timestamp', 'Unknown')}")
        st.caption(f"Keys stored: {session_info.get('keys_count', 0)}")
    else:
        st.info("ℹ️ No active session")
    
    # Action buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("💾 Save Session", use_container_width=True):
            session_name = f"manual_save_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if manager.save_session(session_name):
                st.success("Session saved!")
                st.rerun()
            else:
                st.error("Failed to save session")
    
    with col2:
        if st.button("📂 Load Session", use_container_width=True):
            if manager.load_session():
                st.success("Session loaded!")
                st.rerun()
            else:
                st.warning("No session to load")
    
    with col3:
        if st.button("🔄 New Session", use_container_width=True):
            # Clear session state (keep only essentials)
            keys_to_keep = ['session_manager']
            keys_to_delete = [k for k in st.session_state.keys() if k not in keys_to_keep]
            for key in keys_to_delete:
                del st.session_state[key]
            st.success("New session started!")
            st.rerun()
    
    # Export/Import section
    with st.expander("📤 Export / Import"):
        st.markdown("**Export Current Session**")
        export_name = st.text_input("Session name:", value=f"session_{datetime.now().strftime('%Y%m%d')}")
        
        if st.button("Export as JSON"):
            session_data = manager.export_session(export_name)
            st.download_button(
                label="Download Session File",
                data=session_data,
                file_name=f"{export_name}.json",
                mime="application/json"
            )
        
        st.markdown("**Import Session**")
        uploaded_session = st.file_uploader("Upload session JSON:", type=['json'], key="session_import")
        
        if uploaded_session:
            if st.button("Import Session"):
                if manager.import_session(uploaded_session):
                    st.success("Session imported successfully!")
                    st.rerun()
                else:
                    st.error("Failed to import session")
    
    # Saved sessions list
    with st.expander("📚 Saved Sessions"):
        sessions = manager.list_sessions()
        
        if not sessions:
            st.info("No saved sessions found")
        else:
            for session in sessions:
                col_a, col_b, col_c = st.columns([3, 1, 1])
                
                with col_a:
                    st.markdown(f"**{session['name']}**")
                    st.caption(f"{session['timestamp']} • {session['file_size']} bytes")
                
                with col_b:
                    if st.button("Load", key=f"load_{session['name']}"):
                        if manager.load_session(Path(session['path'])):
                            st.success("Loaded!")
                            st.rerun()
                
                with col_c:
                    if st.button("Delete", key=f"del_{session['name']}"):
                        if manager.delete_session(session['path']):
                            st.success("Deleted!")
                            st.rerun()


def initialize_session_persistence():
    """Initialize session persistence on app startup."""
    if 'session_manager' not in st.session_state:
        st.session_state.session_manager = SessionManager()
        
        # Try to load last session automatically
        st.session_state.session_manager.load_session()
        
        # Initialize file tracking if not exists
        if 'generated_files' not in st.session_state:
            st.session_state.generated_files = []
        
        if 'file_library_index' not in st.session_state:
            st.session_state.file_library_index = {}
        
        if 'campaign_history' not in st.session_state:
            st.session_state.campaign_history = []
        
        # Scan for existing files and add to library
        scan_and_index_files()


def scan_and_index_files():
    """Scan campaigns directory and index all files."""
    from pathlib import Path
    from datetime import datetime
    
    campaigns_dir = Path("campaigns")
    if not campaigns_dir.exists():
        return
    
    # Track files we've already indexed
    indexed_paths = set(f['path'] for f in st.session_state.get('generated_files', []))
    new_files_count = 0
    
    # Scan all files
    for file_path in campaigns_dir.rglob('*'):
        if file_path.is_file():
            file_path_str = str(file_path)
            
            # Skip if already indexed
            if file_path_str in indexed_paths:
                continue
            
            # Add to file library
            file_info = {
                'path': file_path_str,
                'name': file_path.name,
                'type': file_path.suffix.lower(),
                'size': file_path.stat().st_size,
                'created': datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
                'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                'campaign': file_path.parent.name if file_path.parent != campaigns_dir else 'root',
                'indexed_at': datetime.now().isoformat()
            }
            
            st.session_state.generated_files.append(file_info)
            new_files_count += 1
    
    # Update last scan time
    st.session_state.last_file_scan = datetime.now().isoformat()
    
    if new_files_count > 0:
        logger.info(f"Indexed {new_files_count} new files")


def track_generated_file(file_path: str, file_type: str, campaign_name: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
    """
    Track a newly generated file in the file library.
    
    Args:
        file_path: Absolute or relative path to file
        file_type: File type/category (image, video, document, etc.)
        campaign_name: Associated campaign name
        metadata: Additional metadata dict
    """
    from pathlib import Path
    from datetime import datetime
    
    if 'generated_files' not in st.session_state:
        st.session_state.generated_files = []
    
    path_obj = Path(file_path)
    
    file_info = {
        'path': str(path_obj),
        'name': path_obj.name,
        'type': file_type,
        'size': path_obj.stat().st_size if path_obj.exists() else 0,
        'created': datetime.now().isoformat(),
        'modified': datetime.now().isoformat(),
        'campaign': campaign_name or 'unknown',
        'metadata': metadata or {},
        'indexed_at': datetime.now().isoformat()
    }
    
    st.session_state.generated_files.append(file_info)
    
    # Auto-save session to persist file tracking
    if 'session_manager' in st.session_state:
        st.session_state.session_manager.save_session()


def get_files_by_type(file_type: str) -> list:
    """Get all files of a specific type from library."""
    if 'generated_files' not in st.session_state:
        return []
    
    return [f for f in st.session_state.generated_files if f['type'] == file_type]


def get_files_by_campaign(campaign_name: str) -> list:
    """Get all files from a specific campaign."""
    if 'generated_files' not in st.session_state:
        return []
    
    return [f for f in st.session_state.generated_files if f['campaign'] == campaign_name]
