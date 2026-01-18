"""
Compatibility module - redirects to background_tasks.py

This module exists to maintain backward compatibility with imports
that reference 'background_task_manager' instead of 'background_tasks'.
"""

# Re-export everything from background_tasks
from app.services.background_tasks import (
    BackgroundTaskManager,
    log,
    run_background_campaign,
)

# Add any missing exports that modules might expect
def render_compact_progress_indicator():
    """Render a compact progress indicator for background tasks."""
    import streamlit as st
    from app.services.global_job_queue import get_global_job_queue
    
    try:
        queue = get_global_job_queue()
        stats = queue.get_stats()
        
        running = stats.get('running', 0)
        pending = stats.get('pending', 0)
        completed = stats.get('completed', 0)
        
        if running > 0 or pending > 0:
            st.sidebar.markdown(f"""
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 8px 12px; border-radius: 8px; margin: 8px 0;'>
                <div style='color: white; font-size: 12px;'>
                    ⚡ <b>{running}</b> running | 📋 <b>{pending}</b> queued | ✅ <b>{completed}</b> done
                </div>
            </div>
            """, unsafe_allow_html=True)
    except Exception:
        pass  # Silently fail if queue not available


__all__ = [
    'BackgroundTaskManager',
    'log',
    'run_background_campaign',
    'render_compact_progress_indicator',
]
