"""
Session Persistence Manager

Auto-saves work in progress and recovers on reload:
- Workflow states
- Form inputs
- Generated content
- Configuration
- Chat history

Features:
- Automatic background saving
- Recovery prompts on reload
- Version history
- Conflict resolution
"""

import os
import json
import time
import hashlib
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class SessionSnapshot:
    """A snapshot of session state"""
    id: str
    timestamp: str
    data: Dict
    description: str = ""
    auto_saved: bool = True
    size_bytes: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SessionSnapshot':
        return cls(**data)


class SessionPersistence:
    """
    Manages automatic session persistence.
    """
    
    # Keys to persist (whitelist approach for safety)
    PERSIST_KEYS = {
        # Workflow state
        'current_workflow',
        'workflow_steps',
        'workflow_outputs',
        
        # Content creation
        'current_campaign',
        'campaign_plan',
        'generated_images',
        'generated_videos',
        'generated_content',
        
        # Form inputs that took effort
        'product_description',
        'brand_concept',
        'target_audience',
        'marketing_prompt',
        'video_script',
        
        # AI chat history
        'chat_messages',
        'otto_chat_history',
        
        # Important settings
        'selected_model',
        'selected_style',
        'brand_colors',
        'brand_name',
        
        # File selections
        'uploaded_files',
        'selected_template',
        
        # Playground state
        'playground_settings',
        'playground_history',
    }
    
    # Keys to never persist (blacklist for security)
    NEVER_PERSIST = {
        'api_keys',
        'password',
        'token',
        'secret',
        'credential',
    }
    
    def __init__(self, storage_path: str = None, auto_save_interval: int = 30):
        self.storage_path = Path(storage_path or os.path.expanduser("~/.printify_sessions"))
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.auto_save_interval = auto_save_interval
        self.last_save_time = 0
        self.last_save_hash = ""
        self._lock = threading.Lock()
        
        # Session history
        self.snapshots: List[SessionSnapshot] = []
        self.max_snapshots = 20
        
        # Load existing session
        self._load_session_index()
    
    def _get_session_file(self) -> Path:
        """Get the current session file"""
        return self.storage_path / "current_session.json"
    
    def _get_index_file(self) -> Path:
        """Get the session index file"""
        return self.storage_path / "session_index.json"
    
    def _load_session_index(self):
        """Load the session index"""
        try:
            index_file = self._get_index_file()
            if index_file.exists():
                with open(index_file, 'r') as f:
                    data = json.load(f)
                    self.snapshots = [SessionSnapshot.from_dict(s) for s in data.get('snapshots', [])]
        except Exception as e:
            logger.warning(f"Could not load session index: {e}")
            self.snapshots = []
    
    def _save_session_index(self):
        """Save the session index"""
        try:
            index_file = self._get_index_file()
            with open(index_file, 'w') as f:
                json.dump({
                    'snapshots': [s.to_dict() for s in self.snapshots[-self.max_snapshots:]],
                    'last_updated': datetime.now().isoformat(),
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save session index: {e}")
    
    def _should_persist_key(self, key: str) -> bool:
        """Check if a key should be persisted"""
        key_lower = key.lower()
        
        # Never persist sensitive keys
        for blocked in self.NEVER_PERSIST:
            if blocked in key_lower:
                return False
        
        # Check whitelist
        return key in self.PERSIST_KEYS or any(pk in key for pk in self.PERSIST_KEYS)
    
    def _compute_hash(self, data: Dict) -> str:
        """Compute a hash of the data for change detection"""
        return hashlib.md5(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:16]
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize a value for JSON storage"""
        if value is None:
            return None
        
        # Handle common types
        if isinstance(value, (str, int, float, bool)):
            return value
        
        if isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        
        if isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        
        # Try to convert to dict
        if hasattr(value, '__dict__'):
            return {"_type": type(value).__name__, "_data": self._serialize_value(value.__dict__)}
        
        # Last resort: string conversion
        try:
            return str(value)
        except:
            return None
    
    def extract_persistable_state(self, session_state: Dict) -> Dict:
        """Extract state that should be persisted"""
        persistable = {}
        
        for key, value in session_state.items():
            if self._should_persist_key(key):
                try:
                    serialized = self._serialize_value(value)
                    if serialized is not None:
                        persistable[key] = serialized
                except Exception as e:
                    logger.debug(f"Could not serialize {key}: {e}")
        
        return persistable
    
    def should_auto_save(self, session_state: Dict) -> bool:
        """Check if we should auto-save now"""
        now = time.time()
        
        # Rate limit saves
        if now - self.last_save_time < self.auto_save_interval:
            return False
        
        # Check if data changed
        persistable = self.extract_persistable_state(session_state)
        current_hash = self._compute_hash(persistable)
        
        if current_hash == self.last_save_hash:
            return False
        
        return True
    
    def save_session(self, session_state: Dict, description: str = "", force: bool = False) -> Optional[SessionSnapshot]:
        """
        Save the current session state.
        
        Args:
            session_state: The Streamlit session state
            description: Optional description for this snapshot
            force: Force save even if no changes detected
        
        Returns:
            The created snapshot, or None if nothing to save
        """
        if not force and not self.should_auto_save(session_state):
            return None
        
        with self._lock:
            persistable = self.extract_persistable_state(session_state)
            
            if not persistable:
                return None
            
            # Create snapshot
            snapshot_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot = SessionSnapshot(
                id=snapshot_id,
                timestamp=datetime.now().isoformat(),
                data=persistable,
                description=description or f"Auto-save at {datetime.now().strftime('%H:%M:%S')}",
                auto_saved=not force,
                size_bytes=len(json.dumps(persistable))
            )
            
            # Save to file
            try:
                session_file = self._get_session_file()
                with open(session_file, 'w') as f:
                    json.dump(snapshot.to_dict(), f, indent=2)
                
                # Add to history
                self.snapshots.append(snapshot)
                self._save_session_index()
                
                # Update tracking
                self.last_save_time = time.time()
                self.last_save_hash = self._compute_hash(persistable)
                
                logger.info(f"Session saved: {snapshot.id} ({snapshot.size_bytes} bytes)")
                return snapshot
                
            except Exception as e:
                logger.error(f"Failed to save session: {e}")
                return None
    
    def load_session(self) -> Optional[SessionSnapshot]:
        """Load the most recent session"""
        try:
            session_file = self._get_session_file()
            if session_file.exists():
                with open(session_file, 'r') as f:
                    data = json.load(f)
                    return SessionSnapshot.from_dict(data)
        except Exception as e:
            logger.warning(f"Could not load session: {e}")
        return None
    
    def restore_session(self, session_state: Any, snapshot: SessionSnapshot = None) -> int:
        """
        Restore session state from a snapshot.
        
        Args:
            session_state: The Streamlit session state to restore into
            snapshot: Snapshot to restore (or most recent if None)
        
        Returns:
            Number of keys restored
        """
        if snapshot is None:
            snapshot = self.load_session()
        
        if snapshot is None:
            return 0
        
        restored_count = 0
        
        for key, value in snapshot.data.items():
            try:
                session_state[key] = value
                restored_count += 1
            except Exception as e:
                logger.warning(f"Could not restore {key}: {e}")
        
        logger.info(f"Restored {restored_count} session keys")
        return restored_count
    
    def get_recovery_info(self) -> Optional[Dict]:
        """Get info about recoverable session"""
        snapshot = self.load_session()
        
        if snapshot is None:
            return None
        
        # Check if session is recent enough to prompt for recovery
        snapshot_time = datetime.fromisoformat(snapshot.timestamp)
        age = datetime.now() - snapshot_time
        
        if age > timedelta(hours=24):
            return None
        
        return {
            "timestamp": snapshot.timestamp,
            "age_minutes": int(age.total_seconds() / 60),
            "age_display": self._format_age(age),
            "keys": list(snapshot.data.keys()),
            "key_count": len(snapshot.data),
            "size_bytes": snapshot.size_bytes,
            "description": snapshot.description,
        }
    
    def _format_age(self, age: timedelta) -> str:
        """Format age in human-readable form"""
        seconds = int(age.total_seconds())
        
        if seconds < 60:
            return "just now"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = seconds // 86400
            return f"{days} day{'s' if days != 1 else ''} ago"
    
    def get_snapshot_history(self, limit: int = 10) -> List[Dict]:
        """Get recent snapshot history"""
        history = []
        
        for snapshot in reversed(self.snapshots[-limit:]):
            history.append({
                "id": snapshot.id,
                "timestamp": snapshot.timestamp,
                "description": snapshot.description,
                "key_count": len(snapshot.data),
                "size_bytes": snapshot.size_bytes,
                "auto_saved": snapshot.auto_saved,
            })
        
        return history
    
    def load_snapshot_by_id(self, snapshot_id: str) -> Optional[SessionSnapshot]:
        """Load a specific snapshot by ID"""
        for snapshot in self.snapshots:
            if snapshot.id == snapshot_id:
                # Load full data from file if needed
                snapshot_file = self.storage_path / f"snapshot_{snapshot_id}.json"
                if snapshot_file.exists():
                    with open(snapshot_file, 'r') as f:
                        return SessionSnapshot.from_dict(json.load(f))
                return snapshot
        return None
    
    def create_named_snapshot(self, session_state: Dict, name: str) -> SessionSnapshot:
        """Create a named snapshot (like a save point)"""
        return self.save_session(session_state, description=name, force=True)
    
    def clear_session(self):
        """Clear saved session"""
        with self._lock:
            session_file = self._get_session_file()
            if session_file.exists():
                session_file.unlink()
            self.last_save_hash = ""


# Global instance
_persistence: Optional[SessionPersistence] = None


def get_persistence() -> SessionPersistence:
    """Get the global persistence instance"""
    global _persistence
    if _persistence is None:
        _persistence = SessionPersistence()
    return _persistence


# Streamlit integration
def auto_save_session(session_state: Any) -> bool:
    """
    Call this periodically to auto-save session.
    Returns True if save occurred.
    """
    persistence = get_persistence()
    snapshot = persistence.save_session(dict(session_state))
    return snapshot is not None


def check_session_recovery(session_state: Any) -> Optional[Dict]:
    """
    Check if there's a session to recover.
    Call this on app startup.
    """
    # Skip if already checked
    if session_state.get('_recovery_checked'):
        return None
    
    session_state['_recovery_checked'] = True
    
    persistence = get_persistence()
    return persistence.get_recovery_info()


def restore_session(session_state: Any) -> int:
    """Restore the last saved session"""
    persistence = get_persistence()
    return persistence.restore_session(session_state)


def render_recovery_prompt():
    """Render the session recovery prompt in Streamlit"""
    import streamlit as st
    
    recovery_info = check_session_recovery(st.session_state)
    
    if recovery_info and not st.session_state.get('_recovery_dismissed'):
        with st.container():
            st.info(f"""
            💾 **Unsaved work found** from {recovery_info['age_display']}
            
            Found {recovery_info['key_count']} items including: {', '.join(recovery_info['keys'][:5])}{'...' if len(recovery_info['keys']) > 5 else ''}
            """)
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.button("✅ Restore", type="primary", key="restore_session_btn"):
                    count = restore_session(st.session_state)
                    st.session_state['_recovery_dismissed'] = True
                    st.success(f"Restored {count} items!")
                    st.rerun()
            
            with col2:
                if st.button("❌ Discard", key="discard_session_btn"):
                    st.session_state['_recovery_dismissed'] = True
                    get_persistence().clear_session()
                    st.rerun()


def render_session_manager():
    """Render session management UI"""
    import streamlit as st
    
    persistence = get_persistence()
    
    st.markdown("### 💾 Session Management")
    
    # Current session info
    col1, col2 = st.columns(2)
    
    with col1:
        persistable = persistence.extract_persistable_state(dict(st.session_state))
        st.metric("Items to Save", len(persistable))
    
    with col2:
        if persistence.last_save_time > 0:
            age = time.time() - persistence.last_save_time
            st.metric("Last Save", persistence._format_age(timedelta(seconds=age)))
        else:
            st.metric("Last Save", "Never")
    
    # Manual save
    col_save, col_clear = st.columns(2)
    
    with col_save:
        save_name = st.text_input("Save name (optional)", key="session_save_name")
        if st.button("💾 Save Now", use_container_width=True, key="manual_save_btn"):
            snapshot = persistence.save_session(
                dict(st.session_state), 
                description=save_name or "Manual save",
                force=True
            )
            if snapshot:
                st.success(f"Saved! ({snapshot.size_bytes} bytes)")
            else:
                st.warning("Nothing to save")
    
    with col_clear:
        st.markdown("")
        st.markdown("")
        if st.button("🗑️ Clear Saved Session", use_container_width=True, key="clear_session_btn"):
            persistence.clear_session()
            st.success("Session cleared!")
    
    # History
    st.markdown("#### 📜 Save History")
    history = persistence.get_snapshot_history(10)
    
    if history:
        for item in history:
            col_info, col_action = st.columns([4, 1])
            
            with col_info:
                icon = "💾" if item["auto_saved"] else "📌"
                time_str = datetime.fromisoformat(item["timestamp"]).strftime("%Y-%m-%d %H:%M")
                st.markdown(f"{icon} **{item['description']}** - {time_str} ({item['key_count']} items)")
            
            with col_action:
                if st.button("Restore", key=f"restore_{item['id']}"):
                    snapshot = persistence.load_snapshot_by_id(item['id'])
                    if snapshot:
                        persistence.restore_session(st.session_state, snapshot)
                        st.success("Restored!")
                        st.rerun()
    else:
        st.info("No save history yet")
    
    # Settings
    with st.expander("⚙️ Settings"):
        new_interval = st.slider(
            "Auto-save interval (seconds)",
            min_value=10,
            max_value=300,
            value=persistence.auto_save_interval,
            step=10,
            key="autosave_interval"
        )
        if new_interval != persistence.auto_save_interval:
            persistence.auto_save_interval = new_interval
        
        st.markdown("**Keys being tracked:**")
        st.caption(", ".join(sorted(persistence.PERSIST_KEYS)))
