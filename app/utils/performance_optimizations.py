"""
Performance Optimizations for Streamlit App
============================================
Caching, lazy loading, and optimization utilities.
"""

import streamlit as st
import functools
import time
import hashlib
from typing import Any, Callable, Optional, Dict
from pathlib import Path
import logging
import os

logger = logging.getLogger(__name__)

# ============================================
# STREAMLIT CACHING DECORATORS
# ============================================

@st.cache_resource(ttl=3600)
def get_replicate_client(api_token: str):
    """Cache the Replicate client to avoid re-initialization."""
    import replicate
    return replicate.Client(api_token=api_token)


@st.cache_resource(ttl=3600)
def get_youtube_service():
    """Cache YouTube service initialization."""
    try:
        from youtube_upload_service import YouTubeUploadService
        service = YouTubeUploadService()
        return service
    except Exception as e:
        logger.error(f"YouTube service init failed: {e}")
        return None


@st.cache_resource(ttl=3600)
def get_printify_api(api_token: str, shop_id: str):
    """Cache Printify API client."""
    try:
        from app.services.api_service import PrintifyAPI
        return PrintifyAPI(api_token=api_token, shop_id=shop_id)
    except Exception as e:
        logger.error(f"Printify API init failed: {e}")
        return None


@st.cache_resource(ttl=3600)
def get_replicate_api(api_token: str):
    """Cache ReplicateAPI wrapper client for unified API access.
    
    This returns the enhanced ReplicateAPI class from api_service.py
    which provides image, video, text, and speech generation.
    """
    try:
        from app.services.api_service import ReplicateAPI
        return ReplicateAPI(api_token=api_token)
    except Exception as e:
        logger.error(f"ReplicateAPI init failed: {e}")
        return None


@st.cache_resource(ttl=3600)
def get_shopify_api(shop_url: str, access_token: str):
    """Cache Shopify API client."""
    try:
        from shopify_service import ShopifyService
        return ShopifyService(shop_url=shop_url, access_token=access_token)
    except Exception as e:
        logger.error(f"Shopify API init failed: {e}")
        return None


@st.cache_data(ttl=300)
def get_printify_catalog(_api, blueprint_id: int):
    """Cache Printify catalog data (5 minute TTL)."""
    try:
        return _api.get_print_providers(blueprint_id)
    except:
        return []


@st.cache_data(ttl=300)
def get_printify_blueprints(_api):
    """Cache Printify blueprints (5 minute TTL)."""
    try:
        return _api.get_blueprints()
    except:
        return []


@st.cache_data(ttl=60)
def get_shopify_products(_api, limit: int = 50):
    """Cache Shopify products (1 minute TTL)."""
    try:
        return _api.get_products(limit=limit)
    except:
        return []


@st.cache_data(ttl=300)
def get_youtube_channel_stats(_service):
    """Cache YouTube channel stats (5 minute TTL)."""
    try:
        return _service.get_channel_stats()
    except:
        return {}


# ============================================
# LAZY LOADING UTILITIES
# ============================================

class LazyLoader:
    """Lazy load heavy modules only when needed."""
    
    _modules = {}
    
    @classmethod
    def load(cls, module_name: str):
        """Lazily import a module."""
        if module_name not in cls._modules:
            import importlib
            cls._modules[module_name] = importlib.import_module(module_name)
        return cls._modules[module_name]
    
    @classmethod
    def get_pil(cls):
        return cls.load('PIL.Image')
    
    @classmethod
    def get_replicate(cls):
        return cls.load('replicate')
    
    @classmethod
    def get_pandas(cls):
        return cls.load('pandas')
    
    @classmethod
    def get_numpy(cls):
        return cls.load('numpy')


def lazy_import(module_name: str):
    """Decorator for lazy importing modules."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Import the module only when the function is called
            import importlib
            module = importlib.import_module(module_name)
            return func(*args, _lazy_module=module, **kwargs)
        return wrapper
    return decorator


# ============================================
# FRAGMENT-BASED RENDERING
# ============================================

def fragment_render(func: Callable) -> Callable:
    """
    Decorator to render components as fragments.
    This allows partial page updates without full reruns.
    """
    @functools.wraps(func)
    @st.fragment
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


# ============================================
# PERFORMANCE MONITORING
# ============================================

class PerformanceMonitor:
    """Track and report performance metrics."""
    
    _timings: Dict[str, list] = {}
    
    @classmethod
    def start_timer(cls, operation: str) -> float:
        """Start timing an operation."""
        return time.time()
    
    @classmethod
    def end_timer(cls, operation: str, start_time: float):
        """End timing and record."""
        elapsed = time.time() - start_time
        if operation not in cls._timings:
            cls._timings[operation] = []
        cls._timings[operation].append(elapsed)
        
        # Keep only last 100 timings
        if len(cls._timings[operation]) > 100:
            cls._timings[operation] = cls._timings[operation][-100:]
        
        return elapsed
    
    @classmethod
    def get_avg_time(cls, operation: str) -> float:
        """Get average time for an operation."""
        timings = cls._timings.get(operation, [])
        return sum(timings) / len(timings) if timings else 0
    
    @classmethod
    def get_stats(cls) -> Dict:
        """Get all timing stats."""
        return {
            op: {
                'count': len(times),
                'avg': sum(times) / len(times) if times else 0,
                'min': min(times) if times else 0,
                'max': max(times) if times else 0
            }
            for op, times in cls._timings.items()
        }


def timed_operation(operation_name: str):
    """Decorator to time operations."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = PerformanceMonitor.start_timer(operation_name)
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = PerformanceMonitor.end_timer(operation_name, start)
                if elapsed > 1.0:  # Log slow operations
                    logger.warning(f"Slow operation: {operation_name} took {elapsed:.2f}s")
        return wrapper
    return decorator


# ============================================
# SESSION STATE OPTIMIZATION
# ============================================

def init_session_state_fast():
    """
    Fast session state initialization.
    Only initialize what's needed immediately, defer the rest.
    """
    # Critical state - always needed
    critical_state = {
        'initialized': True,
        'api_keys': {},
        'fullscreen_chat_mode': False,
        'enable_experimental_features': False,
    }
    
    for key, value in critical_state.items():
        if key not in st.session_state:
            st.session_state[key] = value


def init_session_state_deferred():
    """
    Deferred session state - initialize on first use.
    """
    deferred_state = {
        'campaign_history': [],
        'product_studio_results': [],
        'content_generation_history': [],
        'video_producer_runs': [],
        'image_generation_history': [],
        'audio_generation_history': [],
        'campaign_stats': [],
        'products_created': [],
        'workflow_running': False,
        'logs': [],
        'generated_images': [],
        'generated_videos': [],
        'chain_pipeline': [],
        'chain_results': [],
        'playground_results': [],
    }
    
    for key, value in deferred_state.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_or_init(key: str, default_factory: Callable):
    """Get session state or initialize with factory function."""
    if key not in st.session_state:
        st.session_state[key] = default_factory()
    return st.session_state[key]


# ============================================
# IMAGE OPTIMIZATION
# ============================================

@st.cache_data(ttl=3600)
def optimize_image_for_display(image_data: bytes, max_size: tuple = (800, 800)) -> bytes:
    """Optimize image for web display."""
    from PIL import Image
    import io
    
    img = Image.open(io.BytesIO(image_data))
    
    # Convert to RGB if needed
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    # Resize if too large
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    
    # Compress
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=85, optimize=True)
    return output.getvalue()


def create_thumbnail(image_path: str, size: tuple = (200, 200)) -> str:
    """Create a thumbnail for faster loading."""
    from PIL import Image
    
    thumb_dir = Path(image_path).parent / '.thumbnails'
    thumb_dir.mkdir(exist_ok=True)
    
    thumb_path = thumb_dir / f"thumb_{Path(image_path).name}"
    
    if not thumb_path.exists():
        img = Image.open(image_path)
        img.thumbnail(size, Image.Resampling.LANCZOS)
        img.save(thumb_path, quality=75)
    
    return str(thumb_path)


# ============================================
# BATCH OPERATIONS
# ============================================

def batch_process(items: list, processor: Callable, batch_size: int = 10):
    """Process items in batches to avoid memory issues."""
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = [processor(item) for item in batch]
        results.extend(batch_results)
    return results


# ============================================
# RENDER OPTIMIZATION SETTINGS UI
# ============================================

def render_performance_settings():
    """Render performance settings in the sidebar."""
    with st.expander("⚡ Performance Settings", expanded=False):
        st.caption("Optimize app performance")
        
        # Show cache stats
        if st.button("📊 Show Cache Stats"):
            stats = PerformanceMonitor.get_stats()
            if stats:
                for op, data in stats.items():
                    st.write(f"**{op}**: {data['count']} calls, avg {data['avg']:.3f}s")
            else:
                st.info("No performance data collected yet")
        
        # Clear caches
        if st.button("🗑️ Clear All Caches"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("Caches cleared!")
        
        # Memory mode
        low_memory = st.checkbox(
            "Low Memory Mode",
            value=st.session_state.get('low_memory_mode', False),
            help="Reduce memory usage by limiting cached items"
        )
        st.session_state['low_memory_mode'] = low_memory
        
        st.markdown("---")
        
        # Ray Distributed Computing
        try:
            from abp_ray_cluster import render_ray_cluster_ui
            render_ray_cluster_ui()
        except ImportError:
            st.caption("💡 Ray distributed computing available - check main settings")
        
        st.markdown("---")
        
        # Global Job Queue Monitor
        try:
            from abp_job_monitor import show_job_monitor_widget
            show_job_monitor_widget(location="sidebar")
        except ImportError:
            pass


# ============================================
# STARTUP OPTIMIZATION
# ============================================

def optimize_startup():
    """Run startup optimizations."""
    # Set environment variables for performance
    os.environ.setdefault('STREAMLIT_SERVER_HEADLESS', 'true')
    os.environ.setdefault('STREAMLIT_BROWSER_GATHER_USAGE_STATS', 'false')
    
    # Pre-warm critical caches
    init_session_state_fast()


# ============================================
# CONDITIONAL RENDERING
# ============================================

def render_if_visible(container_key: str):
    """Decorator to only render component if it's likely visible."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if this container was recently accessed
            last_access = st.session_state.get(f'_last_access_{container_key}', 0)
            current_time = time.time()
            
            # Update access time
            st.session_state[f'_last_access_{container_key}'] = current_time
            
            # Render the component
            return func(*args, **kwargs)
        return wrapper
    return decorator
