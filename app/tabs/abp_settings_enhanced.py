"""
Enhanced settings page with API validation and connection testing
Integrates validation utilities for better user experience
"""

import streamlit as st
import os
from pathlib import Path
import sys

# Add app/utils to path for imports
utils_path = Path(__file__).parent.parent / "utils"
if str(utils_path) not in sys.path:
    sys.path.insert(0, str(utils_path))

from validation import (
    APIValidator, 
    InputValidator,
    create_test_connection_button,
    display_validation_result
)


def render_api_settings():
    """Render API settings with validation"""
    st.header("🔑 API Credentials")
    st.caption("Configure your API keys with real-time validation")
    
    # Replicate API
    with st.expander("🤖 Replicate API (Required)", expanded=True):
        st.markdown("""
        Required for AI image generation, video creation, and most content generation features.
        
        **Get your key:** [replicate.com/account/api-tokens](https://replicate.com/account/api-tokens)
        """)
        
        replicate_token = st.text_input(
            "Replicate API Token",
            value=st.session_state.get('replicate_token', ''),
            type="password",
            key="replicate_token_input",
            help="Should start with 'r8_'"
        )
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("💾 Save", key="save_replicate"):
                st.session_state.replicate_token = replicate_token
                os.environ['REPLICATE_API_TOKEN'] = replicate_token
                st.success("✅ Saved to session")
        
        with col2:
            result = create_test_connection_button(
                "Replicate",
                APIValidator.test_replicate_token,
                replicate_token,
                key="test_replicate"
            )
    
    # Printify API
    with st.expander("🛍️ Printify API (Optional - for product publishing)"):
        st.markdown("""
        Required for publishing products to Printify and downloading mockups.
        
        **Get your token:** [printify.com/app/account/api](https://printify.com/app/account/api)
        
        **Find Shop ID:** In your Printify URL: `printify.com/app/stores/SHOP_ID/...`
        """)
        
        printify_token = st.text_input(
            "Printify API Token",
            value=st.session_state.get('printify_token', ''),
            type="password",
            key="printify_token_input",
            help="Should start with 'eyJ'"
        )
        
        printify_shop_id = st.text_input(
            "Printify Shop ID",
            value=st.session_state.get('printify_shop_id', ''),
            key="printify_shop_id_input",
            help="Numeric ID from your Printify store URL"
        )
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("💾 Save", key="save_printify"):
                st.session_state.printify_token = printify_token
                st.session_state.printify_shop_id = printify_shop_id
                os.environ['PRINTIFY_API_TOKEN'] = printify_token
                os.environ['PRINTIFY_SHOP_ID'] = printify_shop_id
                st.success("✅ Saved to session")
        
        with col2:
            if printify_token and printify_shop_id:
                result = create_test_connection_button(
                    "Printify",
                    APIValidator.test_printify_token,
                    printify_token,
                    printify_shop_id,
                    key="test_printify"
                )
    
    # Anthropic API
    with st.expander("🤖 Anthropic API (Optional - for Claude AI)"):
        st.markdown("""
        Required for Otto AI assistant and Claude-powered features.
        
        **Get your key:** [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)
        """)
        
        anthropic_token = st.text_input(
            "Anthropic API Key",
            value=st.session_state.get('anthropic_api_key', ''),
            type="password",
            key="anthropic_token_input",
            help="Should start with 'sk-ant-'"
        )
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("💾 Save", key="save_anthropic"):
                st.session_state.anthropic_api_key = anthropic_token
                os.environ['ANTHROPIC_API_KEY'] = anthropic_token
                st.success("✅ Saved to session")
        
        with col2:
            result = create_test_connection_button(
                "Anthropic",
                APIValidator.test_anthropic_token,
                anthropic_token,
                key="test_anthropic"
            )
    
    # Shopify
    with st.expander("🛒 Shopify (Optional - for blog publishing)"):
        st.markdown("""
        Required for publishing blogs and managing Shopify store content.
        
        **Setup Guide:** [Shopify Custom App Setup](../extra-docs/SHOPIFY_SETUP_GUIDE.md)
        """)
        
        shopify_url = st.text_input(
            "Shop URL",
            value=st.session_state.get('shopify_shop_url', ''),
            key="shopify_url_input",
            placeholder="your-store.myshopify.com",
            help="Your Shopify store URL"
        )
        
        shopify_token = st.text_input(
            "Access Token",
            value=st.session_state.get('shopify_access_token', ''),
            type="password",
            key="shopify_token_input",
            help="Admin API access token from custom app"
        )
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("💾 Save", key="save_shopify"):
                st.session_state.shopify_shop_url = shopify_url
                st.session_state.shopify_access_token = shopify_token
                os.environ['SHOPIFY_SHOP_URL'] = shopify_url
                os.environ['SHOPIFY_ACCESS_TOKEN'] = shopify_token
                st.success("✅ Saved to session")
        
        with col2:
            if shopify_url and shopify_token:
                result = create_test_connection_button(
                    "Shopify",
                    APIValidator.test_shopify_credentials,
                    shopify_url,
                    shopify_token,
                    key="test_shopify"
                )
    
    st.divider()
    
    # Batch Test All
    st.subheader("🔍 Test All Connections")
    
    if st.button("🔌 Test All Configured APIs", type="primary"):
        with st.spinner("Testing all connections..."):
            results = {}
            
            # Test Replicate
            if st.session_state.get('replicate_token'):
                result = APIValidator.test_replicate_token(st.session_state.replicate_token)
                results['Replicate'] = result
            
            # Test Printify
            if st.session_state.get('printify_token') and st.session_state.get('printify_shop_id'):
                result = APIValidator.test_printify_token(
                    st.session_state.printify_token,
                    st.session_state.printify_shop_id
                )
                results['Printify'] = result
            
            # Test Anthropic
            if st.session_state.get('anthropic_api_key'):
                result = APIValidator.test_anthropic_token(st.session_state.anthropic_api_key)
                results['Anthropic'] = result
            
            # Test Shopify
            if st.session_state.get('shopify_shop_url') and st.session_state.get('shopify_access_token'):
                result = APIValidator.test_shopify_credentials(
                    st.session_state.shopify_shop_url,
                    st.session_state.shopify_access_token
                )
                results['Shopify'] = result
            
            # Display results
            st.markdown("### Test Results")
            
            all_valid = True
            for api_name, result in results.items():
                if result.is_valid:
                    st.success(f"✅ **{api_name}**: {result.message}")
                else:
                    st.error(f"❌ **{api_name}**: {result.message}")
                    all_valid = False
            
            if all_valid and results:
                st.balloons()
                st.success("🎉 All configured APIs are working!")
            elif not results:
                st.warning("⚠️ No APIs configured yet. Add your API keys above.")


def render_validation_example():
    """Render example of input validation"""
    st.header("✨ Input Validation Examples")
    
    with st.expander("📧 Email Validation"):
        email = st.text_input("Email Address", key="example_email")
        if email:
            result = InputValidator.validate_email(email)
            display_validation_result(result)
    
    with st.expander("🔗 URL Validation"):
        url = st.text_input("Website URL", key="example_url")
        if url:
            result = InputValidator.validate_url(url)
            display_validation_result(result)
    
    with st.expander("📝 Text Validation"):
        text = st.text_area("Text Input", key="example_text")
        min_len = st.number_input("Minimum Length", value=10, min_value=1)
        max_len = st.number_input("Maximum Length", value=1000, min_value=1)
        
        if text:
            result = InputValidator.validate_text(text, min_len, max_len, "Your text")
            display_validation_result(result)


def render():
    """Main render function"""
    st.title("⚙️ Enhanced Settings")
    st.caption("API Configuration with validation and connection testing")
    
    tab1, tab2 = st.tabs(["🔑 API Settings", "✨ Validation Tools"])
    
    with tab1:
        render_api_settings()
    
    with tab2:
        render_validation_example()


if __name__ == "__main__":
    render()
