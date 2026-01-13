"""
Shortcuts Manager - Persistent storage for Magic Buttons
=========================================================

Provides:
- Save/load shortcuts to disk
- Shortcut validation and migration
- Export/import functionality
"""

import json
import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import streamlit as st

# Default storage path - use a folder for future expansion
SHORTCUTS_DIR = Path(os.path.expanduser("~/.printify_shortcuts"))
SHORTCUTS_FILE = SHORTCUTS_DIR / "shortcuts.json"

# Ensure directory exists on module load
SHORTCUTS_DIR.mkdir(parents=True, exist_ok=True)

# Extended icon options
SHORTCUT_ICONS = [
    # Actions
    "⚡", "🚀", "🎯", "💰", "🔥", "✨", "💎", "⭐", "💫", "🌟",
    # Content
    "🎨", "📦", "🛒", "📱", "📧", "🎬", "🎵", "📊", "📝", "📸",
    # Social
    "🐦", "📷", "▶️", "🔗", "💬", "📣", "📢", "🎤", "🎧", "🎙️",
    # Business
    "💼", "📈", "📉", "💵", "💳", "🏪", "🛍️", "🎁", "🏆", "🥇",
    # Tech
    "🤖", "⚙️", "🔧", "🔨", "🛠️", "💻", "🖥️", "📡", "🔌", "💡",
    # Nature
    "🌈", "🌸", "🌺", "🌻", "🍀", "🌙", "☀️", "⛅", "🌊", "🔮",
    # Food & Drink
    "☕", "🍕", "🍔", "🎂", "🍦", "🍩", "🍪", "🧁", "🍷", "🍸",
    # Animals
    "🦁", "🐯", "🦊", "🐺", "🦄", "🐉", "🦋", "🐝", "🦅", "🐬",
    # Objects
    "💎", "👑", "🎪", "🎭", "🎨", "🎯", "🎲", "🃏", "🎰", "🎮",
    # Misc
    "❤️", "💜", "💙", "💚", "💛", "🧡", "🖤", "🤍", "💖", "💝"
]

# Button color/style options
BUTTON_STYLES = {
    "primary": {"label": "Primary (Purple)", "streamlit_type": "primary", "css_class": "btn-primary"},
    "success": {"label": "Success (Green)", "streamlit_type": "secondary", "css_class": "btn-success"},
    "warning": {"label": "Warning (Orange)", "streamlit_type": "secondary", "css_class": "btn-warning"},
    "danger": {"label": "Danger (Red)", "streamlit_type": "secondary", "css_class": "btn-danger"},
    "info": {"label": "Info (Blue)", "streamlit_type": "secondary", "css_class": "btn-info"},
    "secondary": {"label": "Secondary (Gray)", "streamlit_type": "secondary", "css_class": "btn-secondary"},
    "gradient_purple": {"label": "Gradient Purple", "streamlit_type": "primary", "css_class": "btn-gradient-purple"},
    "gradient_blue": {"label": "Gradient Blue", "streamlit_type": "primary", "css_class": "btn-gradient-blue"},
    "gradient_green": {"label": "Gradient Green", "streamlit_type": "primary", "css_class": "btn-gradient-green"},
    "gradient_orange": {"label": "Gradient Orange", "streamlit_type": "primary", "css_class": "btn-gradient-orange"},
    "outline": {"label": "Outline", "streamlit_type": "secondary", "css_class": "btn-outline"},
    "ghost": {"label": "Ghost (Minimal)", "streamlit_type": "secondary", "css_class": "btn-ghost"},
}

# Button size options
BUTTON_SIZES = {
    "small": {"label": "Small", "padding": "4px 8px", "font_size": "0.8em"},
    "medium": {"label": "Medium", "padding": "8px 16px", "font_size": "1em"},
    "large": {"label": "Large", "padding": "12px 24px", "font_size": "1.2em"},
    "xl": {"label": "Extra Large", "padding": "16px 32px", "font_size": "1.4em"},
}

# Category options with colors
SHORTCUT_CATEGORIES = {
    "🎨 Content Creation": "#9b59b6",
    "📱 Social Media": "#3498db",
    "📦 Products": "#e67e22",
    "📧 Marketing": "#1abc9c",
    "🔄 Automation": "#34495e",
    "📊 Analytics": "#2ecc71",
    "🛒 Sales": "#e74c3c",
    "🎬 Video": "#9b59b6",
    "🎵 Audio": "#f39c12",
    "🔧 Utilities": "#95a5a6",
    "⭐ Favorites": "#f1c40f",
    "🏠 Personal": "#3498db",
}


def load_shortcuts() -> List[Dict[str, Any]]:
    """Load shortcuts from disk"""
    try:
        if SHORTCUTS_FILE.exists():
            with open(SHORTCUTS_FILE, 'r') as f:
                data = json.load(f)
                return data.get('shortcuts', [])
    except Exception as e:
        print(f"Error loading shortcuts: {e}")
    return []


def save_shortcuts(shortcuts: List[Dict[str, Any]]) -> bool:
    """Save shortcuts to disk"""
    try:
        data = {
            'version': '1.0',
            'updated_at': datetime.now().isoformat(),
            'shortcuts': shortcuts
        }
        with open(SHORTCUTS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving shortcuts: {e}")
        return False


def init_shortcuts():
    """Initialize shortcuts from disk into session state"""
    if 'magic_shortcuts' not in st.session_state:
        st.session_state.magic_shortcuts = load_shortcuts()
    if 'shortcut_results' not in st.session_state:
        st.session_state.shortcut_results = {}


def add_shortcut(shortcut: Dict[str, Any]) -> bool:
    """Add a shortcut and save to disk"""
    if 'magic_shortcuts' not in st.session_state:
        st.session_state.magic_shortcuts = []
    
    st.session_state.magic_shortcuts.append(shortcut)
    return save_shortcuts(st.session_state.magic_shortcuts)


def update_shortcut(shortcut_id: str, updates: Dict[str, Any]) -> bool:
    """Update a shortcut and save to disk"""
    for shortcut in st.session_state.magic_shortcuts:
        if shortcut.get('id') == shortcut_id:
            shortcut.update(updates)
            return save_shortcuts(st.session_state.magic_shortcuts)
    return False


def delete_shortcut(shortcut_id: str) -> bool:
    """Delete a shortcut and save to disk"""
    st.session_state.magic_shortcuts = [
        s for s in st.session_state.magic_shortcuts 
        if s.get('id') != shortcut_id
    ]
    return save_shortcuts(st.session_state.magic_shortcuts)


def export_shortcuts() -> str:
    """Export shortcuts as JSON string"""
    return json.dumps(st.session_state.magic_shortcuts, indent=2)


def import_shortcuts(json_str: str) -> int:
    """Import shortcuts from JSON string, returns count imported"""
    try:
        imported = json.loads(json_str)
        if isinstance(imported, list):
            # Add unique IDs to avoid conflicts
            import uuid
            for shortcut in imported:
                shortcut['id'] = str(uuid.uuid4())[:8]
                shortcut['imported_at'] = datetime.now().isoformat()
            
            st.session_state.magic_shortcuts.extend(imported)
            save_shortcuts(st.session_state.magic_shortcuts)
            return len(imported)
    except Exception as e:
        print(f"Error importing shortcuts: {e}")
    return 0


def get_shortcut_css() -> str:
    """Get CSS for custom button styles"""
    return """
    <style>
    /* Custom button styles for shortcuts */
    .btn-gradient-purple {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border: none !important;
        color: white !important;
    }
    .btn-gradient-blue {
        background: linear-gradient(135deg, #5ee7df 0%, #b490ca 100%) !important;
        border: none !important;
        color: white !important;
    }
    .btn-gradient-green {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%) !important;
        border: none !important;
        color: white !important;
    }
    .btn-gradient-orange {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%) !important;
        border: none !important;
        color: white !important;
    }
    .btn-success {
        background-color: #28a745 !important;
        border-color: #28a745 !important;
    }
    .btn-warning {
        background-color: #ffc107 !important;
        border-color: #ffc107 !important;
        color: #212529 !important;
    }
    .btn-danger {
        background-color: #dc3545 !important;
        border-color: #dc3545 !important;
    }
    .btn-info {
        background-color: #17a2b8 !important;
        border-color: #17a2b8 !important;
    }
    .btn-outline {
        background-color: transparent !important;
        border: 2px solid #667eea !important;
        color: #667eea !important;
    }
    .btn-ghost {
        background-color: transparent !important;
        border: none !important;
        color: #667eea !important;
        text-decoration: underline;
    }
    
    /* Shortcut card styling */
    .shortcut-card {
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
        transition: all 0.3s ease;
    }
    .shortcut-card:hover {
        border-color: rgba(102, 126, 234, 0.3);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
    }
    .shortcut-icon {
        font-size: 2em;
        margin-bottom: 8px;
    }
    .shortcut-title {
        font-weight: 600;
        font-size: 1.1em;
        margin-bottom: 4px;
    }
    .shortcut-description {
        font-size: 0.85em;
        color: #888;
        margin-bottom: 8px;
    }
    .shortcut-stats {
        font-size: 0.75em;
        color: #666;
    }
    </style>
    """


def render_icon_picker(key: str = "icon_picker") -> str:
    """Render an icon picker grid"""
    st.markdown("**Choose an Icon:**")
    
    # Group icons by category
    icon_groups = {
        "Actions": SHORTCUT_ICONS[0:10],
        "Content": SHORTCUT_ICONS[10:20],
        "Social": SHORTCUT_ICONS[20:30],
        "Business": SHORTCUT_ICONS[30:40],
        "Tech": SHORTCUT_ICONS[40:50],
        "Nature": SHORTCUT_ICONS[50:60],
        "Food": SHORTCUT_ICONS[60:70],
        "Animals": SHORTCUT_ICONS[70:80],
        "Objects": SHORTCUT_ICONS[80:90],
        "Hearts": SHORTCUT_ICONS[90:100],
    }
    
    selected_icon = st.session_state.get(f'{key}_selected', '⚡')
    
    # Show current selection
    st.markdown(f"Selected: **{selected_icon}**")
    
    # Create icon grid with tabs for categories
    icon_tabs = st.tabs(list(icon_groups.keys()))
    
    for tab, (group_name, icons) in zip(icon_tabs, icon_groups.items()):
        with tab:
            cols = st.columns(10)
            for idx, icon in enumerate(icons):
                with cols[idx % 10]:
                    if st.button(icon, key=f"{key}_{group_name}_{idx}", help=f"Select {icon}"):
                        st.session_state[f'{key}_selected'] = icon
                        st.rerun()
    
    return st.session_state.get(f'{key}_selected', '⚡')


def render_style_picker(key: str = "style_picker") -> str:
    """Render a button style picker with previews"""
    st.markdown("**Choose a Style:**")
    
    style_options = list(BUTTON_STYLES.keys())
    style_labels = [BUTTON_STYLES[s]["label"] for s in style_options]
    
    selected_idx = st.selectbox(
        "Button Style",
        range(len(style_options)),
        format_func=lambda i: style_labels[i],
        key=f"{key}_select"
    )
    
    selected_style = style_options[selected_idx]
    
    # Show preview
    st.markdown("**Preview:**")
    style_info = BUTTON_STYLES[selected_style]
    
    # Create a styled preview div
    preview_html = f"""
    <div style="
        display: inline-block;
        padding: 8px 16px;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
        {'background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;' if 'gradient_purple' in selected_style else ''}
        {'background: linear-gradient(135deg, #5ee7df 0%, #b490ca 100%); color: white;' if 'gradient_blue' in selected_style else ''}
        {'background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white;' if 'gradient_green' in selected_style else ''}
        {'background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white;' if 'gradient_orange' in selected_style else ''}
        {'background-color: #667eea; color: white;' if selected_style == 'primary' else ''}
        {'background-color: #28a745; color: white;' if selected_style == 'success' else ''}
        {'background-color: #ffc107; color: #212529;' if selected_style == 'warning' else ''}
        {'background-color: #dc3545; color: white;' if selected_style == 'danger' else ''}
        {'background-color: #17a2b8; color: white;' if selected_style == 'info' else ''}
        {'background-color: #6c757d; color: white;' if selected_style == 'secondary' else ''}
        {'background-color: transparent; border: 2px solid #667eea; color: #667eea;' if selected_style == 'outline' else ''}
        {'background-color: transparent; color: #667eea; text-decoration: underline;' if selected_style == 'ghost' else ''}
    ">
        ⚡ Sample Button
    </div>
    """
    st.markdown(preview_html, unsafe_allow_html=True)
    
    return selected_style


def render_size_picker(key: str = "size_picker") -> str:
    """Render a button size picker"""
    size_options = list(BUTTON_SIZES.keys())
    size_labels = [BUTTON_SIZES[s]["label"] for s in size_options]
    
    selected_idx = st.selectbox(
        "Button Size",
        range(len(size_options)),
        format_func=lambda i: size_labels[i],
        index=1,  # Default to medium
        key=f"{key}_select"
    )
    
    return size_options[selected_idx]


class ShortcutsManager:
    """
    Class-based wrapper for shortcuts management.
    Provides the same functionality as the module-level functions
    but encapsulated in a class for cleaner code organization.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        if storage_path is None:
            self.storage_path = SHORTCUTS_FILE
        elif isinstance(storage_path, str):
            self.storage_path = Path(storage_path) / "shortcuts.json"
        else:
            self.storage_path = storage_path
        # Ensure parent directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load_shortcuts(self) -> List[Dict[str, Any]]:
        """Load shortcuts from disk"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    return data.get('shortcuts', [])
        except Exception as e:
            print(f"Error loading shortcuts: {e}")
        return []
    
    def save_shortcut(self, shortcut: Dict[str, Any]) -> bool:
        """Add or update a shortcut and save to disk"""
        shortcuts = self.load_shortcuts()
        
        # Generate ID if not present
        if not shortcut.get('id'):
            import uuid
            shortcut['id'] = str(uuid.uuid4())[:8]
        
        # Check if shortcut already exists (update) or is new (add)
        existing_idx = next(
            (i for i, s in enumerate(shortcuts) if s.get('id') == shortcut.get('id')),
            None
        )
        
        if existing_idx is not None:
            shortcuts[existing_idx] = shortcut
        else:
            shortcuts.append(shortcut)
        
        return self._save_to_disk(shortcuts)
    
    def delete_shortcut(self, shortcut_id: str) -> bool:
        """Delete a shortcut by ID"""
        shortcuts = self.load_shortcuts()
        shortcuts = [s for s in shortcuts if s.get('id') != shortcut_id]
        return self._save_to_disk(shortcuts)
    
    def export_shortcuts(self) -> str:
        """Export all shortcuts as JSON string"""
        shortcuts = self.load_shortcuts()
        data = {
            'version': '1.0',
            'exported_at': datetime.now().isoformat(),
            'shortcuts': shortcuts
        }
        return json.dumps(data, indent=2)
    
    def import_shortcuts(self, json_str: str, merge: bool = True, replace: bool = False) -> int:
        """
        Import shortcuts from JSON string.
        
        Args:
            json_str: JSON string with shortcuts data
            merge: If True, add new shortcuts, skip duplicates by name
            replace: If True, replace all existing shortcuts
        
        Returns:
            Number of shortcuts imported
        """
        try:
            data = json.loads(json_str)
            
            # Handle different JSON structures
            if isinstance(data, dict) and 'shortcuts' in data:
                imported = data['shortcuts']
            elif isinstance(data, list):
                imported = data
            else:
                return 0
            
            if replace:
                # Replace all shortcuts
                for shortcut in imported:
                    shortcut['id'] = str(uuid.uuid4())[:8]
                    shortcut['imported_at'] = datetime.now().isoformat()
                self._save_to_disk(imported)
                return len(imported)
            
            # Merge logic
            existing = self.load_shortcuts()
            existing_names = {s.get('name') for s in existing}
            added_count = 0
            
            for shortcut in imported:
                if merge and shortcut.get('name') in existing_names:
                    continue  # Skip duplicates
                
                shortcut['id'] = str(uuid.uuid4())[:8]
                shortcut['imported_at'] = datetime.now().isoformat()
                existing.append(shortcut)
                added_count += 1
            
            self._save_to_disk(existing)
            return added_count
            
        except Exception as e:
            print(f"Error importing shortcuts: {e}")
            return 0
    
    def _save_to_disk(self, shortcuts: List[Dict[str, Any]]) -> bool:
        """Internal method to save shortcuts to disk"""
        try:
            data = {
                'version': '1.0',
                'updated_at': datetime.now().isoformat(),
                'shortcuts': shortcuts
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving shortcuts: {e}")
            return False


# Ensure ShortcutsManager is exported
__all__ = [
    'ShortcutsManager',
    'load_shortcuts',
    'save_shortcuts', 
    'init_shortcuts',
    'add_shortcut',
    'update_shortcut',
    'delete_shortcut',
    'export_shortcuts',
    'import_shortcuts',
    'get_shortcut_css',
    'render_icon_picker',
    'render_style_picker',
    'render_size_picker',
    'SHORTCUT_ICONS',
    'BUTTON_STYLES',
    'BUTTON_SIZES',
    'SHORTCUT_CATEGORIES',
    'SHORTCUTS_FILE'
]