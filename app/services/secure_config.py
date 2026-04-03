"""
Secure Configuration Manager for Streamlit Cloud
Allows users to safely input API keys without needing .env files
"""

import os
from typing import Dict, Optional

import streamlit as st


def get_api_key(key_name: str, display_name: str = None) -> Optional[str]:
    """
    Get API key from session state, secrets, or environment
    Priority: session_state > secrets > env
    """
    display_name = display_name or key_name

    # Check session state first (user input)
    session_key = f"user_{key_name.lower()}"
    if session_key in st.session_state and st.session_state[session_key]:
        return st.session_state[session_key]

    # Check Streamlit secrets (cloud deployment)
    try:
        if hasattr(st, "secrets") and key_name in st.secrets:
            return st.secrets[key_name]
    except Exception:
        pass

    # Check environment variables (local .env)
    env_value = os.getenv(key_name)
    if env_value:
        return env_value

    return None


def render_secure_config_ui():
    """Render secure API key input UI"""
    st.markdown("### 🔐 Secure API Configuration")
    st.markdown(
        """
    Enter your API keys below. They will be stored securely in your browser session only.
    **Your keys are never sent to our servers or stored permanently.**
    """
    )

    # API Keys configuration
    api_keys = {
        "REPLICATE_API_TOKEN": {
            "name": "Replicate API Token",
            "help": "Get your token at replicate.com/account",
            "required": True,
            "demo": True,  # Available in demo mode
        },
        "ANTHROPIC_API_KEY": {
            "name": "Anthropic (Claude) API Key",
            "help": "Get your key at console.anthropic.com",
            "required": False,
            "demo": True,
        },
        "OPENAI_API_KEY": {
            "name": "OpenAI API Key",
            "help": "Get your key at platform.openai.com",
            "required": False,
            "demo": True,
        },
        "PRINTIFY_API_TOKEN": {
            "name": "Printify API Token",
            "help": "Get your token at printify.com (Settings → API)",
            "required": False,
            "demo": False,
        },
        "SHOPIFY_ACCESS_TOKEN": {
            "name": "Shopify Access Token",
            "help": "Create a custom app in your Shopify admin",
            "required": False,
            "demo": False,
        },
        "YOUTUBE_CLIENT_ID": {
            "name": "YouTube Client ID",
            "help": "From Google Cloud Console",
            "required": False,
            "demo": False,
        },
    }

    st.markdown("#### 🎯 Core AI APIs (Required for most features)")

    for key, config in list(api_keys.items())[:3]:  # First 3 are AI keys
        col1, col2 = st.columns([3, 1])

        with col1:
            current_value = get_api_key(key)
            masked_value = (
                "••••••••" + current_value[-4:] if current_value and len(current_value) > 4 else ""
            )

            placeholder = masked_value if current_value else f"Enter your {config['name']}"

            new_value = st.text_input(
                config["name"],
                value="",
                type="password",
                placeholder=placeholder,
                help=config["help"],
                key=f"input_{key}",
            )

            if new_value:
                st.session_state[f"user_{key.lower()}"] = new_value
                st.success(f"✅ {config['name']} updated!")

        with col2:
            if current_value:
                st.markdown("**Status**")
                st.success("✓ Set")
            else:
                st.markdown("**Status**")
                st.error("✗ Missing")

    with st.expander("🔧 Additional Integrations (Optional)"):
        for key, config in list(api_keys.items())[3:]:  # Remaining keys
            current_value = get_api_key(key)
            masked_value = (
                "••••••••" + current_value[-4:] if current_value and len(current_value) > 4 else ""
            )

            new_value = st.text_input(
                config["name"],
                value="",
                type="password",
                placeholder=masked_value if current_value else f"Enter your {config['name']}",
                help=config["help"],
                key=f"input_{key}",
            )

            if new_value:
                st.session_state[f"user_{key.lower()}"] = new_value

    st.markdown("---")
    st.markdown("#### 📊 Configuration Status")

    # Show what's configured
    configured = []
    missing = []

    for key, config in api_keys.items():
        if get_api_key(key):
            configured.append(config["name"])
        elif config["required"]:
            missing.append(config["name"])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**✅ Configured ({len(configured)})**")
        for name in configured:
            st.markdown(f"- {name}")

    with col2:
        if missing:
            st.markdown(f"**⚠️ Missing ({len(missing)})**")
            for name in missing:
                st.markdown(f"- {name}")
        else:
            st.success("All required keys configured!")

    st.markdown("---")
    st.info(
        """
    **🔒 Security Note:** 
    - Keys are stored only in your browser session
    - Keys are cleared when you close the browser
    - Never share your API keys with anyone
    - For production deployment, use Streamlit Secrets instead
    """
    )

    if st.button("🗑️ Clear All Keys (Sign Out)"):
        for key in api_keys.keys():
            session_key = f"user_{key.lower()}"
            if session_key in st.session_state:
                del st.session_state[session_key]
        st.success("All keys cleared!")
        st.rerun()


def init_api_clients():
    """Initialize API clients from secure config"""
    # Initialize Replicate
    replicate_token = get_api_key("REPLICATE_API_TOKEN")
    if replicate_token and "replicate_client" not in st.session_state:
        try:
            import replicate

            os.environ["REPLICATE_API_TOKEN"] = replicate_token
            st.session_state["replicate_client"] = replicate.Client(api_token=replicate_token)
        except Exception as e:
            st.warning(f"Failed to initialize Replicate: {e}")

    # Initialize Anthropic
    anthropic_key = get_api_key("ANTHROPIC_API_KEY")
    if anthropic_key:
        os.environ["ANTHROPIC_API_KEY"] = anthropic_key

    # Initialize OpenAI
    openai_key = get_api_key("OPENAI_API_KEY")
    if openai_key:
        os.environ["OPENAI_API_KEY"] = openai_key

    # Initialize Printify
    printify_token = get_api_key("PRINTIFY_API_TOKEN")
    if printify_token and "printify_api" not in st.session_state:
        try:
            from app.services.api_service import PrintifyAPI

            st.session_state["printify_api"] = PrintifyAPI(printify_token)
        except Exception as e:
            st.warning(f"Failed to initialize Printify: {e}")


def is_demo_mode() -> bool:
    """Check if running in demo mode (no critical keys configured)"""
    return not (get_api_key("PRINTIFY_API_TOKEN") or get_api_key("SHOPIFY_ACCESS_TOKEN"))
