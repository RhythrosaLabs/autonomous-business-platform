"""
Tab Visibility Manager
Allows users to customize which tabs are displayed based on their role or preferences
"""

from typing import Dict, List

import streamlit as st

# Define all available tabs
ALL_TABS = [
    "🏠 Dashboard",
    "⚡ Shortcuts",
    "🤖 Task Queue",
    "🔄 Job Monitor",
    "📦 Product Studio",
    "💾 Digital Products",
    "🎯 Campaign Creator",
    "📝 Content Generator",
    "🎬 Video Producer",
    "🎮 Playground",
    "🔧 Workflows",
    "📅 Calendar",
    "📓 Journal",
    "🔍 Contact Finder",
    "👥 Customers",
    "📊 Analytics",
    "🎨 Brand Templates",
    "💌 Email Outreach",
    "🎵 Music Platforms",
    "📁 File Library",
    "🌐 Browser-Use",
]

# Role-based tab presets
ROLE_PRESETS = {
    "business_owner": {
        "name": "👨‍💼 Business Owner",
        "tabs": [
            "🏠 Dashboard",
            "⚡ Shortcuts",
            "🤖 Task Queue",
            "🔄 Job Monitor",
            "🎯 Campaign Creator",
            "📊 Analytics",
            "💌 Email Outreach",
            "👥 Customers",
            "🤖 Task Queue",
            "📁 File Library",
            "🌐 Browser-Use",
        ],
    },
    "creator": {
        "name": "🎨 Content Creator",
        "tabs": [
            "🏠 Dashboard",
            "📦 Product Studio",
            "📝 Content Generator",
            "🎬 Video Producer",
            "🎮 Playground",
            "🎨 Brand Templates",
            "⚡ Shortcuts",
            "📁 File Library",
            "🌐 Browser-Use",
        ],
    },
    "developer": {
        "name": "⚙️ Developer",
        "tabs": [
            "🏠 Dashboard",
            "⚡ Shortcuts",
            "🤖 Task Queue",
            "🔧 Workflows",
            "🎮 Playground",
            "📝 Content Generator",
            "📊 Analytics",
            "📁 File Library",
            "🌐 Browser-Use",
        ],
    },
    "analyst": {
        "name": "📊 Marketing Analyst",
        "tabs": [
            "🏠 Dashboard",
            "📊 Analytics",
            "👥 Customers",
            "🎯 Campaign Creator",
            "📓 Journal",
            "💌 Email Outreach",
            "📁 File Library",
            "🌐 Browser-Use",
        ],
    },
    "label_owner": {
        "name": "🎵 Label Owner",
        "tabs": [
            "🏠 Dashboard",
            "🎵 Music Platforms",
            "🎬 Video Producer",
            "📝 Content Generator",
            "🎯 Campaign Creator",
            "📊 Analytics",
            "👥 Customers",
            "💌 Email Outreach",
            "🎨 Brand Templates",
            "📁 File Library",
            "🌐 Browser-Use",
        ],
    },
    "online_seller": {
        "name": "🛒 Online Seller",
        "tabs": [
            "🏠 Dashboard",
            "📦 Product Studio",
            "💾 Digital Products",
            "🎯 Campaign Creator",
            "📊 Analytics",
            "👥 Customers",
            "📝 Content Generator",
            "⚡ Shortcuts",
            "🤖 Task Queue",
            "📁 File Library",
            "🌐 Browser-Use",
        ],
    },
    "youtube_bot": {
        "name": "📺 YouTube Bot",
        "tabs": [
            "🏠 Dashboard",
            "🎬 Video Producer",
            "📝 Content Generator",
            "🤖 Task Queue",
            "🔧 Workflows",
            "📅 Calendar",
            "📊 Analytics",
            "⚡ Shortcuts",
            "📁 File Library",
            "🌐 Browser-Use",
        ],
    },
    "otto_only": {"name": "🤖 Otto Only", "tabs": ["🏠 Dashboard"]},
    "all": {"name": "🌟 Show All (Default)", "tabs": ALL_TABS.copy()},
}

# Custom presets storage key
CUSTOM_PRESETS_KEY = "custom_tab_presets"


def initialize_tab_visibility():
    """Initialize tab visibility in session state"""
    if "visible_tabs" not in st.session_state:
        st.session_state.visible_tabs = ALL_TABS.copy()
    else:
        # Auto-add any new tabs that were added to ALL_TABS
        current_visible = set(st.session_state.visible_tabs)
        for tab in ALL_TABS:
            if tab not in current_visible:
                st.session_state.visible_tabs.append(tab)

    if CUSTOM_PRESETS_KEY not in st.session_state:
        st.session_state[CUSTOM_PRESETS_KEY] = {}


def get_visible_tabs() -> List[str]:
    """Get list of currently visible tabs"""
    initialize_tab_visibility()
    return st.session_state.visible_tabs


def set_visible_tabs(tabs: List[str]):
    """Set which tabs should be visible"""
    st.session_state.visible_tabs = tabs


def apply_role_preset(role_key: str):
    """Apply a role-based tab preset"""
    if role_key in ROLE_PRESETS:
        set_visible_tabs(ROLE_PRESETS[role_key]["tabs"].copy())
        st.session_state.current_preset = role_key


def save_custom_preset(name: str, tabs: List[str]):
    """Save a custom tab preset"""
    if CUSTOM_PRESETS_KEY not in st.session_state:
        st.session_state[CUSTOM_PRESETS_KEY] = {}

    st.session_state[CUSTOM_PRESETS_KEY][name] = {"name": name, "tabs": tabs.copy()}


def load_custom_preset(name: str):
    """Load a custom preset"""
    if name in st.session_state.get(CUSTOM_PRESETS_KEY, {}):
        preset = st.session_state[CUSTOM_PRESETS_KEY][name]
        set_visible_tabs(preset["tabs"].copy())
        st.session_state.current_preset = f"custom_{name}"


def delete_custom_preset(name: str):
    """Delete a custom preset"""
    if name in st.session_state.get(CUSTOM_PRESETS_KEY, {}):
        del st.session_state[CUSTOM_PRESETS_KEY][name]


def render_tab_preferences():
    """Render tab visibility preferences UI"""
    st.markdown("### 📑 Tab Visibility Preferences")
    st.markdown("Customize which tabs appear in your navigation")

    # Show current preset
    current_preset = st.session_state.get("current_preset", "all")
    if current_preset in ROLE_PRESETS:
        st.info(f"**Current:** {ROLE_PRESETS[current_preset]['name']}")
    elif current_preset.startswith("custom_"):
        preset_name = current_preset.replace("custom_", "")
        st.info(f"**Current:** Custom - {preset_name}")

    st.divider()

    # Role presets
    st.markdown("#### 🎯 Role-Based Presets")
    st.caption("Quick presets based on your role")

    preset_cols = st.columns(2)
    for idx, (role_key, preset) in enumerate(ROLE_PRESETS.items()):
        with preset_cols[idx % 2]:
            is_active = st.session_state.get("current_preset") == role_key
            button_type = "primary" if is_active else "secondary"

            if st.button(
                preset["name"] + (" ✓" if is_active else ""),
                use_container_width=True,
                type=button_type,
                key=f"preset_{role_key}",
            ):
                apply_role_preset(role_key)
                st.success(f"Applied {preset['name']} preset!")
                st.rerun()

    st.divider()

    # Custom tab selection
    st.markdown("#### ✏️ Custom Selection")
    st.caption("Choose exactly which tabs you want to see")

    initialize_tab_visibility()
    current_visible = st.session_state.visible_tabs

    # Create columns for checkboxes
    col1, col2 = st.columns(2)

    new_visible = []
    for idx, tab in enumerate(ALL_TABS):
        with col1 if idx % 2 == 0 else col2:
            if st.checkbox(tab, value=tab in current_visible, key=f"tab_check_{idx}"):
                new_visible.append(tab)

    # Update button
    if st.button("💾 Apply Custom Selection", type="primary", use_container_width=True):
        if len(new_visible) == 0:
            st.error("❌ Please select at least one tab!")
        else:
            set_visible_tabs(new_visible)
            st.session_state.current_preset = "custom"
            st.success(f"✅ Updated! Now showing {len(new_visible)} tabs")
            st.rerun()

    st.divider()

    # Save/Load custom presets
    st.markdown("#### 💾 Save Custom Presets")
    st.caption("Save your current selection for later")

    col_save, col_name = st.columns([2, 1])
    with col_save:
        preset_name = st.text_input(
            "Preset name", placeholder="e.g., My Workflow", label_visibility="collapsed"
        )
    with col_name:
        if st.button("💾 Save", use_container_width=True, disabled=not preset_name):
            save_custom_preset(preset_name, current_visible)
            st.success(f"Saved '{preset_name}'!")
            st.rerun()

    # Load custom presets
    custom_presets = st.session_state.get(CUSTOM_PRESETS_KEY, {})
    if custom_presets:
        st.markdown("**Your Saved Presets:**")
        for name, preset in custom_presets.items():
            col_load, col_del = st.columns([3, 1])
            with col_load:
                if st.button(
                    f"📂 {name} ({len(preset['tabs'])} tabs)",
                    use_container_width=True,
                    key=f"load_{name}",
                ):
                    load_custom_preset(name)
                    st.success(f"Loaded '{name}'!")
                    st.rerun()
            with col_del:
                if st.button("🗑️", key=f"del_{name}", help=f"Delete {name}"):
                    delete_custom_preset(name)
                    st.rerun()

    st.divider()

    # Reset to default
    if st.button("🔄 Reset to All Tabs", use_container_width=True):
        apply_role_preset("all")
        st.success("Reset to showing all tabs!")
        st.rerun()


def get_filtered_tabs(all_tabs_list: List[str]) -> List[str]:
    """
    Filter a list of tabs based on user's visibility preferences

    Args:
        all_tabs_list: Complete list of tab names

    Returns:
        Filtered list of only visible tabs in the order they appear in visible_tabs
    """
    initialize_tab_visibility()
    visible = get_visible_tabs()

    # Return only tabs that are in visible_tabs AND exist in all_tabs_list
    # Preserve the order from visible_tabs
    return [tab for tab in visible if tab in all_tabs_list]
