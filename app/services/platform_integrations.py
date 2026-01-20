"""
Integration Module for New Platform Features
=============================================

This module integrates the new platform improvements:
1. API Usage Tracker - Track costs via Replicate (centralized AI hub)
2. Session Persistence - Auto-save and crash recovery
3. Performance Boost - Caching, lazy imports, optimizations

Usage in autonomous_business_platform.py:
-----------------------------------------

1. Add this import near the top:
   
   from app.services.platform_integrations import (
       init_all_integrations,
       tracked_replicate_run,
       render_integrations_sidebar
   )

2. After initialize_session_state(), call:
   
   integrations = init_all_integrations()

3. Replace replicate calls:
   
   # Before:
   output = client.run("model/name", input={...})
   
   # After:
   output = tracked_replicate_run(client, "model/name", input_params)

4. In the sidebar section, add:
   
   render_integrations_sidebar()

"""

import streamlit as st
import os
from app.services.secure_config import get_api_key
import time
from typing import Any, Dict, Optional, Callable
from functools import wraps

# Import our new modules
try:
    from api_usage_tracker import (
        APIUsageTracker,
        render_usage_dashboard,
        get_tracker
    )
    API_TRACKER_AVAILABLE = True
except ImportError:
    API_TRACKER_AVAILABLE = False
    def get_tracker():
        return None
    def render_usage_dashboard():
        st.warning("API Usage Tracker not available")

try:
    from session_persistence import (
        SessionPersistence,
        render_session_status,
        render_recovery_dialog
    )
    SESSION_PERSISTENCE_AVAILABLE = True
except ImportError:
    SESSION_PERSISTENCE_AVAILABLE = False
    def render_session_status():
        pass
    def render_recovery_dialog():
        pass

try:
    from performance_boost import (
        init_performance_optimizations,
        render_performance_dashboard,
        render_memory_usage,
        smart_cache,
        cached_data,
        cached_resource,
        LazyImporter,
        BackgroundLoader,
        PerformanceMonitor
    )
    PERFORMANCE_BOOST_AVAILABLE = True
except ImportError:
    PERFORMANCE_BOOST_AVAILABLE = False
    def render_performance_dashboard():
        pass
    def render_memory_usage():
        pass


# =============================================================================
# INITIALIZATION
# =============================================================================

def init_all_integrations() -> Dict[str, Any]:
    """
    Initialize all integration modules
    
    Call this after initialize_session_state() in the main app
    
    Returns:
        Dict containing initialized components
    """
    result = {
        'api_tracker': None,
        'session_persistence': None,
        'performance': None
    }
    
    # Initialize API Usage Tracker
    if API_TRACKER_AVAILABLE:
        try:
            tracker = get_tracker()
            result['api_tracker'] = tracker
            
            # Load persisted usage on startup
            if 'api_tracker_initialized' not in st.session_state:
                st.session_state.api_tracker_initialized = True
                # tracker.load_history()  # If you want to persist across sessions
        except Exception as e:
            st.warning(f"Could not initialize API tracker: {e}")
    
    # Initialize Session Persistence
    if SESSION_PERSISTENCE_AVAILABLE:
        try:
            if 'session_persistence' not in st.session_state:
                persistence = SessionPersistence()
                st.session_state.session_persistence = persistence
                
                # Check for crash recovery on startup
                if persistence.has_recovery_data():
                    st.session_state.show_recovery_dialog = True
            
            result['session_persistence'] = st.session_state.session_persistence
        except Exception as e:
            st.warning(f"Could not initialize session persistence: {e}")
    
    # Initialize Performance Optimizations
    if PERFORMANCE_BOOST_AVAILABLE:
        try:
            if 'performance_initialized' not in st.session_state:
                perf = init_performance_optimizations()
                st.session_state.performance_initialized = True
                result['performance'] = perf
            else:
                result['performance'] = {
                    'lazy': LazyImporter(),
                    'loader': BackgroundLoader(),
                    'monitor': PerformanceMonitor()
                }
        except Exception as e:
            st.warning(f"Could not initialize performance optimizations: {e}")
    
    return result


# =============================================================================
# RATE LIMITER FOR LOW-CREDIT ACCOUNTS
# =============================================================================

class ReplicateRateLimiter:
    """
    Intelligent rate limiter for Replicate API when account has low credits.
    
    When account has <$5 credit, Replicate throttles to 6 requests/minute.
    This class batches and throttles requests to stay under the limit.
    """
    
    def __init__(self, requests_per_minute: int = 6):
        self.requests_per_minute = requests_per_minute
        self.min_interval = 60.0 / requests_per_minute  # ~10 seconds for 6/min
        self.last_request_time = 0
        self.pending_requests = []
        self.is_rate_limited = False
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limit"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_interval:
            wait_time = self.min_interval - time_since_last
            import streamlit as st
            
            if self.is_rate_limited:
                st.info(f"⏳ Rate limited - waiting {wait_time:.1f}s before next request...")
            
            time.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    def mark_rate_limited(self):
        """Mark that we've hit the rate limit"""
        self.is_rate_limited = True
        self.last_request_time = time.time()
    
    def mark_success(self):
        """Mark that a request succeeded"""
        self.is_rate_limited = False


# Global rate limiter instance
_rate_limiter = ReplicateRateLimiter()

def get_rate_limiter() -> ReplicateRateLimiter:
    """Get the global rate limiter instance"""
    return _rate_limiter


# =============================================================================
# TRACKED API CALLS
# =============================================================================

def tracked_replicate_run(
    client: Any,
    model: str,
    input_params: Dict[str, Any],
    operation_name: Optional[str] = None,
    apply_rate_limit: bool = True
) -> Any:
    """
    Run a Replicate model with automatic usage tracking and rate limiting
    
    Args:
        client: Replicate client
        model: Model identifier (e.g., "stability-ai/sdxl")
        input_params: Model input parameters
        operation_name: Optional description for logging
        apply_rate_limit: Whether to apply rate limiting (default: True)
        
    Returns:
        Model output
    """
    tracker = get_tracker() if API_TRACKER_AVAILABLE else None
    monitor = PerformanceMonitor() if PERFORMANCE_BOOST_AVAILABLE else None
    rate_limiter = get_rate_limiter()
    
    # Apply rate limiting if enabled
    if apply_rate_limit:
        rate_limiter.wait_if_needed()
    
    start_time = time.time()
    
    try:
        # Run the model
        output = client.run(model, input=input_params)
        
        # Mark success
        if apply_rate_limit:
            rate_limiter.mark_success()
        
        # Track successful call
        if tracker:
            tracker.track_call(
                provider='replicate',
                model=model,
                endpoint=operation_name or 'model_run',
                duration_ms=int((time.time() - start_time) * 1000),
                success=True,
                metadata={
                    'input_params': str(input_params)[:500],  # Truncate for storage
                }
            )
        
        return output
        
    except Exception as e:
        error_str = str(e)
        
        # Detect rate limit errors
        if "429" in error_str or "throttled" in error_str.lower():
            if apply_rate_limit:
                rate_limiter.mark_rate_limited()
                st.warning(f"⚠️ Rate limited by Replicate. Waiting before retry...")
        
        # Track failed call too
        if tracker:
            tracker.track_call(
                provider='replicate',
                model=model,
                endpoint=operation_name or 'model_run_failed',
                duration_ms=int((time.time() - start_time) * 1000),
                success=False,
                error=error_str[:200]
            )
        raise


def tracked_replicate_text_generation(
    client: Any,
    model: str,
    prompt: str,
    apply_rate_limit: bool = True,
    **kwargs
) -> str:
    """
    Run text generation via Replicate with rate limiting
    
    Args:
        client: Replicate client
        model: Replicate model ID (e.g., 'meta/llama-2-70b')
        prompt: Input prompt
        apply_rate_limit: Whether to apply rate limiting (default: True)
        **kwargs: Additional model parameters
        
    Returns:
        Generated text
    """
    tracker = get_tracker() if API_TRACKER_AVAILABLE else None
    rate_limiter = get_rate_limiter()
    
    # Apply rate limiting if enabled
    if apply_rate_limit:
        rate_limiter.wait_if_needed()
    
    start_time = time.time()
    
    try:
        # Run Replicate model
        output = client.run(
            model,
            input={
                'prompt': prompt,
                **kwargs
            }
        )
        
        # Mark success
        if apply_rate_limit:
            rate_limiter.mark_success()
        
        # Convert output to string if needed
        if isinstance(output, list):
            result = ''.join(str(item) for item in output)
        else:
            result = str(output)
        
        # Track successful call
        if tracker:
            tracker.track_call(
                provider='replicate',
                model=model,
                endpoint='text_generation',
                duration_ms=int((time.time() - start_time) * 1000),
                success=True
            )
        
        return result
        
    except Exception as e:
        if tracker:
            tracker.track_call(
                provider='replicate',
                model=model,
                endpoint='text_generation_failed',
                success=False,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000)
            )
        raise


# Note: All AI requests now route through Replicate as centralized hub
# This includes text generation, image generation, and other AI models
# Use tracked_replicate_run or tracked_replicate_text_generation instead


# =============================================================================
# SIDEBAR RENDERING
# =============================================================================

def render_integrations_sidebar():
    """
    Render the integrated features in the sidebar
    
    Add this to the sidebar section of your main app
    """
    st.markdown("---")
    st.markdown("### 📊 Platform Status")
    
    # API Usage Summary
    if API_TRACKER_AVAILABLE:
        with st.expander("💰 API Usage", expanded=False):
            tracker = get_tracker()
            if tracker:
                # get_summary returns a UsageSummary dataclass
                summary = tracker.get_summary(period="day")
                
                # Today's spending
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        "Today's Cost",
                        f"${summary.total_cost:.2f}",
                        help="API costs for today"
                    )
                with col2:
                    st.metric(
                        "Calls",
                        summary.total_calls,
                        help="Total API calls today"
                    )
                
                # Budget status
                budget_used = summary.total_cost
                budget_limit = tracker.daily_budget
                budget_pct = (budget_used / budget_limit * 100) if budget_limit else 0
                
                if budget_pct > 80:
                    st.warning(f"⚠️ {budget_pct:.0f}% of daily budget used")
                
                # Quick view by service (uses cost_by_provider dict)
                if summary.cost_by_provider:
                    st.caption("By Service:")
                    for provider, cost in summary.cost_by_provider.items():
                        calls = summary.calls_by_provider.get(provider, 0)
                        st.write(f"• {provider.title()}: ${cost:.2f} ({calls} calls)")
                
                if st.button("📊 Full Dashboard", key="open_usage_dashboard"):
                    st.session_state.show_usage_dashboard = True
    
    # Session Status
    if SESSION_PERSISTENCE_AVAILABLE:
        with st.expander("💾 Session", expanded=False):
            persistence = st.session_state.get('session_persistence')
            if persistence:
                status = persistence.get_status()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Drafts", status.get('draft_count', 0))
                with col2:
                    last_save = status.get('last_save', 'Never')
                    if last_save != 'Never':
                        last_save = last_save.strftime('%H:%M')
                    st.metric("Last Save", last_save)
                
                if status.get('unsaved_changes', False):
                    st.info("📝 Unsaved changes")
                    if st.button("💾 Save Now", key="manual_save"):
                        persistence.save_session()
                        st.success("Saved!")
    
    # Performance Metrics
    if PERFORMANCE_BOOST_AVAILABLE:
        with st.expander("⚡ Performance", expanded=False):
            monitor = PerformanceMonitor()
            report = monitor.get_report()
            
            if report['total_operations'] > 0:
                st.metric("Operations", report['total_operations'])
                
                # Show slowest operations
                if 'slowest_operations' in report:
                    st.caption("Slowest:")
                    for name, duration in report['slowest_operations'][:3]:
                        st.write(f"• {name}: {duration:.0f}ms")
            else:
                st.info("No metrics yet")


def render_recovery_check():
    """
    Check for crash recovery and show dialog if needed
    
    Call this early in the app rendering
    """
    if SESSION_PERSISTENCE_AVAILABLE:
        if st.session_state.get('show_recovery_dialog', False):
            render_recovery_dialog()


def render_full_usage_dashboard():
    """
    Render the full API usage dashboard as a modal/popup
    """
    if st.session_state.get('show_usage_dashboard', False):
        st.markdown("---")
        st.markdown("## 📊 API Usage Dashboard")
        
        render_usage_dashboard()
        
        if st.button("Close Dashboard", key="close_usage_dashboard"):
            st.session_state.show_usage_dashboard = False
            st.rerun()


# =============================================================================
# CACHING HELPERS FOR COMMON OPERATIONS
# =============================================================================

if PERFORMANCE_BOOST_AVAILABLE:
    @cached_data(ttl_seconds=300)
    def get_model_list_cached(service: str) -> list:
        """Cache model lists for 5 minutes"""
        # This would be implemented based on your actual model list source
        return []
    
    @cached_resource()
    def get_replicate_client_cached():
        """Cache the Replicate client (centralized AI hub)"""
        import replicate
        return replicate.Client(api_token=get_api_key('REPLICATE_API_TOKEN'))


# =============================================================================
# AUTO-SAVE DECORATOR FOR FORMS
# =============================================================================

def auto_save_form(form_key: str):
    """
    Decorator to auto-save form inputs
    
    Usage:
        @auto_save_form('campaign_form')
        def render_campaign_form():
            title = st.text_input("Title", value=get_draft('campaign_form', 'title', ''))
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Auto-save after rendering
            if SESSION_PERSISTENCE_AVAILABLE:
                persistence = st.session_state.get('session_persistence')
                if persistence:
                    persistence.drafts.save_draft(
                        form_key,
                        st.session_state.get(form_key, {})
                    )
            
            return result
        return wrapper
    return decorator


def get_draft(form_key: str, field: str, default: Any = None) -> Any:
    """Get a saved draft value for a form field"""
    if SESSION_PERSISTENCE_AVAILABLE:
        persistence = st.session_state.get('session_persistence')
        if persistence:
            draft = persistence.drafts.get_draft(form_key)
            if draft and field in draft:
                return draft[field]
    return default


# =============================================================================
# EXAMPLE INTEGRATION CODE
# =============================================================================

INTEGRATION_EXAMPLE = '''
# Add these imports near the top of autonomous_business_platform.py:

from app.services.platform_integrations import (
    init_all_integrations,
    tracked_replicate_run,
    tracked_replicate_text_generation,
    render_integrations_sidebar,
    render_recovery_check,
    render_full_usage_dashboard,
    get_draft,
    auto_save_form
)

# After initialize_session_state():

integrations = init_all_integrations()

# Replace Replicate calls like this:

# Before:
output = client.run("stability-ai/sdxl:...", input=model_input)

# After:
output = tracked_replicate_run(
    client, 
    "stability-ai/sdxl:...", 
    model_input,
    operation_name="Generate product image"
)

# In the sidebar section (with st.sidebar:), add:

render_integrations_sidebar()

# At the start of rendering (after the sidebar), add:

render_recovery_check()

# And at the end of the main content area:

render_full_usage_dashboard()
'''


if __name__ == "__main__":
    st.set_page_config(page_title="Integrations Demo", layout="wide")
    
    st.title("🔌 Platform Integrations Demo")
    
    # Initialize
    integrations = init_all_integrations()
    
    st.markdown("### Available Integrations")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if API_TRACKER_AVAILABLE:
            st.success("✅ API Usage Tracker")
        else:
            st.error("❌ API Usage Tracker")
    
    with col2:
        if SESSION_PERSISTENCE_AVAILABLE:
            st.success("✅ Session Persistence")
        else:
            st.error("❌ Session Persistence")
    
    with col3:
        if PERFORMANCE_BOOST_AVAILABLE:
            st.success("✅ Performance Boost")
        else:
            st.error("❌ Performance Boost")
    
    st.markdown("---")
    
    # Show integration code
    st.markdown("### Integration Code")
    st.code(INTEGRATION_EXAMPLE, language="python")
    
    # Render sidebar
    render_integrations_sidebar()
