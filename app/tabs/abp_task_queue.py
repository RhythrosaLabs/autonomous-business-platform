import streamlit as st

def render_task_queue_tab(enhanced_available, replicate_api, printify_api, shopify_api, youtube_api):
    """
    Renders the Task Queue tab (Tab 2).
    """
    # Use enhanced task queue if available, otherwise fall back to original
    if enhanced_available:
        try:
            from app.services.task_queue_engine import render_enhanced_task_queue
            render_enhanced_task_queue(
                replicate_api=replicate_api,
                printify_api=printify_api,
                shopify_api=shopify_api,
                youtube_api=youtube_api
            )
        except ImportError:
            st.error("Enhanced Task Queue module not found.")
    else:
        # Fallback to original todo list
        # Assuming render_autonomous_todo is available via import or passed in
        # But render_autonomous_todo is defined in autonomous_business_platform.py
        # We should probably import it or move it.
        # For now, let's assume the caller handles the fallback or we import it if possible.
        # Actually, render_autonomous_todo is a wrapper for chat_assistant.
        
        from app.services.chat_assistant import get_chat_assistant
        get_chat_assistant()['render_autonomous_todo']()
