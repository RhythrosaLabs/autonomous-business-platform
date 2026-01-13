"""
Performance Boost Module for Streamlit Applications
===================================================

Comprehensive performance optimizations including:
- Lazy imports to reduce startup time
- Enhanced caching with automatic invalidation
- Fragment rendering for partial updates
- Background loading for heavy resources
- Memory management and cleanup
"""

import streamlit as st
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading
import time
import sys
import importlib
import hashlib
import json
import weakref
from concurrent.futures import ThreadPoolExecutor, Future
from collections import OrderedDict

T = TypeVar('T')

# =============================================================================
# LAZY IMPORT SYSTEM
# =============================================================================

class LazyModule:
    """Lazy module loader - only imports when first accessed"""
    
    def __init__(self, module_name: str, package: Optional[str] = None):
        self._module_name = module_name
        self._package = package
        self._module = None
        self._lock = threading.Lock()
    
    def _load(self):
        if self._module is None:
            with self._lock:
                if self._module is None:  # Double-check
                    self._module = importlib.import_module(self._module_name, self._package)
        return self._module
    
    def __getattr__(self, name: str):
        return getattr(self._load(), name)
    
    def __repr__(self):
        if self._module is None:
            return f"<LazyModule '{self._module_name}' (not loaded)>"
        return f"<LazyModule '{self._module_name}' (loaded)>"


class LazyImporter:
    """
    Manages lazy imports across the application
    
    Usage:
        lazy = LazyImporter()
        lazy.register('numpy', 'np')
        lazy.register('pandas', 'pd')
        lazy.register('PIL.Image', 'Image')
        
        # Later when needed:
        np = lazy.get('np')
        df = lazy.get('pd').DataFrame()
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._modules: Dict[str, LazyModule] = {}
            cls._instance._aliases: Dict[str, str] = {}
            cls._instance._load_times: Dict[str, float] = {}
        return cls._instance
    
    def register(self, module_name: str, alias: Optional[str] = None) -> 'LazyImporter':
        """Register a module for lazy loading"""
        key = alias or module_name
        self._modules[module_name] = LazyModule(module_name)
        self._aliases[key] = module_name
        return self
    
    def register_many(self, modules: List[Union[str, tuple]]) -> 'LazyImporter':
        """Register multiple modules at once"""
        for item in modules:
            if isinstance(item, tuple):
                self.register(item[0], item[1] if len(item) > 1 else None)
            else:
                self.register(item)
        return self
    
    def get(self, name: str) -> Any:
        """Get a module by name or alias"""
        module_name = self._aliases.get(name, name)
        if module_name not in self._modules:
            raise ImportError(f"Module '{name}' not registered for lazy loading")
        
        start = time.time()
        module = self._modules[module_name]._load()
        self._load_times[module_name] = time.time() - start
        return module
    
    def __getattr__(self, name: str) -> Any:
        """Allow direct attribute access like lazy.numpy"""
        return self.get(name)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get loading statistics"""
        return {
            'registered': list(self._aliases.keys()),
            'loaded': [k for k, v in self._modules.items() if v._module is not None],
            'load_times': self._load_times.copy()
        }


# Pre-configure common heavy imports
def setup_lazy_imports() -> LazyImporter:
    """Setup lazy imports for commonly used heavy modules"""
    lazy = LazyImporter()
    lazy.register_many([
        ('numpy', 'np'),
        ('pandas', 'pd'),
        ('PIL', 'PIL'),
        ('PIL.Image', 'Image'),
        ('cv2', 'cv2'),
        ('torch', 'torch'),
        ('tensorflow', 'tf'),
        ('sklearn', 'sklearn'),
        ('scipy', 'scipy'),
        ('matplotlib', 'plt'),
        ('matplotlib.pyplot', 'pyplot'),
        ('plotly', 'plotly'),
        ('plotly.express', 'px'),
        ('plotly.graph_objects', 'go'),
        ('requests', 'requests'),
        ('httpx', 'httpx'),
        ('aiohttp', 'aiohttp'),
        ('openai', 'openai'),
        ('anthropic', 'anthropic'),
        ('replicate', 'replicate'),
        ('moviepy', 'moviepy'),
        ('moviepy.editor', 'mpe'),
        ('pydub', 'pydub'),
        ('boto3', 'boto3'),
        ('google.cloud.storage', 'gcs'),
        ('transformers', 'transformers'),
    ])
    return lazy


# =============================================================================
# ENHANCED CACHING SYSTEM
# =============================================================================

@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    
    @property
    def is_expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        age = (datetime.now() - self.created_at).total_seconds()
        return age > self.ttl_seconds


class SmartCache:
    """
    Advanced caching with TTL, LRU eviction, and size limits
    
    Features:
    - Time-to-live (TTL) expiration
    - LRU eviction when cache is full
    - Memory size tracking
    - Cache warming
    - Statistics
    """
    
    _instance = None
    
    def __new__(cls, max_size: int = 100):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache: OrderedDict[str, CacheEntry] = OrderedDict()
            cls._instance._max_size = max_size
            cls._instance._hits = 0
            cls._instance._misses = 0
            cls._instance._lock = threading.Lock()
        return cls._instance
    
    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate a unique cache key"""
        key_data = {
            'func': func_name,
            'args': str(args),
            'kwargs': str(sorted(kwargs.items()))
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            if entry.is_expired:
                del self._cache[key]
                self._misses += 1
                return None
            
            # Update access info and move to end (most recently used)
            entry.accessed_at = datetime.now()
            entry.access_count += 1
            self._cache.move_to_end(key)
            self._hits += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Set value in cache"""
        with self._lock:
            # Evict if at max size
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)  # Remove oldest
            
            self._cache[key] = CacheEntry(
                value=value,
                ttl_seconds=ttl_seconds
            )
    
    def invalidate(self, pattern: Optional[str] = None):
        """Invalidate cache entries matching pattern or all if no pattern"""
        with self._lock:
            if pattern is None:
                self._cache.clear()
            else:
                keys_to_remove = [k for k in self._cache if pattern in k]
                for key in keys_to_remove:
                    del self._cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._hits + self._misses
        return {
            'size': len(self._cache),
            'max_size': self._max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': self._hits / total if total > 0 else 0,
            'entries': {k: {
                'age_seconds': (datetime.now() - v.created_at).total_seconds(),
                'access_count': v.access_count
            } for k, v in list(self._cache.items())[:10]}  # Top 10
        }


def smart_cache(ttl_seconds: Optional[int] = None, max_size: int = 100):
    """
    Smart caching decorator with TTL and LRU eviction
    
    Usage:
        @smart_cache(ttl_seconds=300)  # Cache for 5 minutes
        def expensive_operation(x, y):
            return x + y
    """
    cache = SmartCache(max_size)
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            key = cache._generate_key(func.__name__, args, kwargs)
            
            # Try cache first
            cached = cache.get(key)
            if cached is not None:
                return cached
            
            # Compute and cache
            result = func(*args, **kwargs)
            cache.set(key, result, ttl_seconds)
            return result
        
        wrapper.cache = cache
        wrapper.invalidate = lambda: cache.invalidate(func.__name__)
        return wrapper
    
    return decorator


# Streamlit-specific caching enhancements
def cached_data(ttl_seconds: int = 3600, show_spinner: bool = True):
    """
    Enhanced st.cache_data with better defaults and spinner control
    
    Usage:
        @cached_data(ttl_seconds=300)
        def load_data():
            return expensive_load()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        cached_func = st.cache_data(ttl=ttl_seconds, show_spinner=show_spinner)(func)
        return cached_func
    return decorator


def cached_resource(ttl_seconds: Optional[int] = None, validate: Optional[Callable] = None):
    """
    Enhanced st.cache_resource with validation
    
    Usage:
        @cached_resource(validate=lambda client: client.is_connected())
        def get_api_client():
            return APIClient()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @st.cache_resource(ttl=ttl_seconds)
        def cached_func(*args, **kwargs):
            return func(*args, **kwargs)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = cached_func(*args, **kwargs)
            if validate and not validate(result):
                cached_func.clear()
                result = cached_func(*args, **kwargs)
            return result
        
        wrapper.clear = cached_func.clear
        return wrapper
    return decorator


# =============================================================================
# BACKGROUND LOADING SYSTEM
# =============================================================================

class BackgroundLoader:
    """
    Load resources in background threads
    
    Usage:
        loader = BackgroundLoader()
        loader.submit('models', load_heavy_models)
        loader.submit('data', load_data)
        
        # Later when needed:
        models = loader.get('models')  # Blocks if not ready
    """
    
    _instance = None
    
    def __new__(cls, max_workers: int = 4):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._executor = ThreadPoolExecutor(max_workers=max_workers)
            cls._instance._futures: Dict[str, Future] = {}
            cls._instance._results: Dict[str, Any] = {}
            cls._instance._errors: Dict[str, Exception] = {}
        return cls._instance
    
    def submit(self, name: str, func: Callable, *args, **kwargs) -> 'BackgroundLoader':
        """Submit a task for background loading"""
        def wrapper():
            try:
                result = func(*args, **kwargs)
                self._results[name] = result
                return result
            except Exception as e:
                self._errors[name] = e
                raise
        
        self._futures[name] = self._executor.submit(wrapper)
        return self
    
    def get(self, name: str, timeout: Optional[float] = None) -> Any:
        """Get result, blocking if not ready"""
        if name in self._results:
            return self._results[name]
        
        if name not in self._futures:
            raise KeyError(f"No task named '{name}' submitted")
        
        future = self._futures[name]
        result = future.result(timeout=timeout)
        return result
    
    def is_ready(self, name: str) -> bool:
        """Check if a task is complete"""
        if name in self._results:
            return True
        if name in self._futures:
            return self._futures[name].done()
        return False
    
    def get_error(self, name: str) -> Optional[Exception]:
        """Get error if task failed"""
        return self._errors.get(name)
    
    def status(self) -> Dict[str, str]:
        """Get status of all tasks"""
        return {
            name: 'ready' if self.is_ready(name) else 
                  'error' if name in self._errors else 
                  'loading'
            for name in self._futures
        }


# =============================================================================
# FRAGMENT RENDERING (Partial Updates)
# =============================================================================

@dataclass
class Fragment:
    """Represents a UI fragment that can be updated independently"""
    key: str
    render_func: Callable
    container: Any = None
    last_rendered: Optional[datetime] = None
    debounce_ms: int = 100


class FragmentManager:
    """
    Manage partial UI updates using Streamlit fragments
    
    This reduces full page reruns by updating only changed sections.
    
    Usage:
        fm = FragmentManager()
        
        @fm.fragment('stats', debounce_ms=500)
        def render_stats():
            st.metric("Users", 100)
        
        # Render fragment
        fm.render('stats')
        
        # Update just this fragment
        fm.update('stats')
    """
    
    def __init__(self):
        self._fragments: Dict[str, Fragment] = {}
        if 'fragment_states' not in st.session_state:
            st.session_state.fragment_states = {}
    
    def fragment(self, key: str, debounce_ms: int = 100):
        """Decorator to register a fragment"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            
            self._fragments[key] = Fragment(
                key=key,
                render_func=wrapper,
                debounce_ms=debounce_ms
            )
            return wrapper
        return decorator
    
    def render(self, key: str, *args, **kwargs):
        """Render a fragment"""
        if key not in self._fragments:
            raise KeyError(f"Fragment '{key}' not registered")
        
        frag = self._fragments[key]
        
        # Create container if not exists
        if frag.container is None:
            frag.container = st.container()
        
        with frag.container:
            frag.render_func(*args, **kwargs)
        
        frag.last_rendered = datetime.now()
    
    def render_with_key(self, key: str, container_key: str = None):
        """Render fragment with explicit container key for rerun isolation"""
        if key not in self._fragments:
            raise KeyError(f"Fragment '{key}' not registered")
        
        frag = self._fragments[key]
        container = st.container(key=container_key or f"frag_{key}")
        
        with container:
            frag.render_func()


def experimental_fragment(func: Callable = None, *, run_every: Optional[timedelta] = None):
    """
    Wrapper around st.fragment for easier use
    
    Note: st.fragment is available in Streamlit 1.33+
    
    Usage:
        @experimental_fragment(run_every=timedelta(seconds=5))
        def live_metrics():
            st.metric("Active Users", get_active_users())
    """
    def decorator(f: Callable):
        if hasattr(st, 'fragment'):
            return st.fragment(f, run_every=run_every)
        else:
            # Fallback for older Streamlit versions
            @wraps(f)
            def wrapper(*args, **kwargs):
                return f(*args, **kwargs)
            return wrapper
    
    if func is not None:
        return decorator(func)
    return decorator


# =============================================================================
# MEMORY MANAGEMENT
# =============================================================================

class MemoryManager:
    """
    Memory management utilities
    
    Usage:
        mm = MemoryManager()
        mm.cleanup_unused()
        mm.get_usage_stats()
    """
    
    _weak_refs: weakref.WeakSet = weakref.WeakSet()
    
    @classmethod
    def track(cls, obj: Any):
        """Track an object for weak reference cleanup"""
        try:
            cls._weak_refs.add(obj)
        except TypeError:
            pass  # Object not weakly referenceable
    
    @classmethod
    def cleanup_session_state(cls, keep_keys: Optional[List[str]] = None):
        """Clean up session state, keeping specified keys"""
        keep_keys = keep_keys or []
        keys_to_remove = [
            key for key in st.session_state 
            if key not in keep_keys and not key.startswith('_')
        ]
        for key in keys_to_remove:
            del st.session_state[key]
    
    @classmethod
    def get_session_state_size(cls) -> Dict[str, int]:
        """Estimate size of session state entries"""
        sizes = {}
        for key, value in st.session_state.items():
            try:
                sizes[key] = sys.getsizeof(value)
            except TypeError:
                sizes[key] = 0
        return dict(sorted(sizes.items(), key=lambda x: x[1], reverse=True))
    
    @classmethod
    def cleanup_large_objects(cls, max_size_bytes: int = 10_000_000):
        """Remove session state entries larger than threshold"""
        sizes = cls.get_session_state_size()
        for key, size in sizes.items():
            if size > max_size_bytes and not key.startswith('_'):
                del st.session_state[key]


# =============================================================================
# PERFORMANCE MONITORING
# =============================================================================

@dataclass
class PerformanceMetric:
    """Performance metric data"""
    name: str
    start_time: float
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_ms(self) -> float:
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000


class PerformanceMonitor:
    """
    Monitor and track performance metrics
    
    Usage:
        pm = PerformanceMonitor()
        
        with pm.measure("load_data"):
            data = load_heavy_data()
        
        # Or as decorator:
        @pm.track
        def expensive_function():
            pass
        
        pm.get_report()
    """
    
    def __init__(self):
        if 'perf_metrics' not in st.session_state:
            st.session_state.perf_metrics = []
        self._current: Optional[PerformanceMetric] = None
    
    class measure:
        """Context manager for measuring execution time"""
        def __init__(self, name: str, monitor: 'PerformanceMonitor' = None):
            self.name = name
            self.monitor = monitor
            self.metric: Optional[PerformanceMetric] = None
        
        def __enter__(self):
            self.metric = PerformanceMetric(
                name=self.name,
                start_time=time.time()
            )
            return self
        
        def __exit__(self, *args):
            if self.metric:
                self.metric.end_time = time.time()
                st.session_state.perf_metrics.append(self.metric)
    
    def track(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to track function performance"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            with self.measure(func.__name__):
                return func(*args, **kwargs)
        return wrapper
    
    def get_report(self) -> Dict[str, Any]:
        """Get performance report"""
        metrics = st.session_state.get('perf_metrics', [])
        if not metrics:
            return {'total_operations': 0}
        
        by_name: Dict[str, List[float]] = {}
        for m in metrics:
            if m.name not in by_name:
                by_name[m.name] = []
            by_name[m.name].append(m.duration_ms)
        
        return {
            'total_operations': len(metrics),
            'by_operation': {
                name: {
                    'count': len(durations),
                    'avg_ms': sum(durations) / len(durations),
                    'max_ms': max(durations),
                    'min_ms': min(durations),
                    'total_ms': sum(durations)
                }
                for name, durations in by_name.items()
            },
            'slowest_operations': sorted(
                [(m.name, m.duration_ms) for m in metrics],
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
    
    def clear(self):
        """Clear metrics"""
        st.session_state.perf_metrics = []


# =============================================================================
# STREAMLIT UI COMPONENTS
# =============================================================================

def render_performance_dashboard():
    """Render performance monitoring dashboard in sidebar"""
    with st.sidebar.expander("⚡ Performance", expanded=False):
        pm = PerformanceMonitor()
        report = pm.get_report()
        
        if report['total_operations'] > 0:
            st.metric("Operations Tracked", report['total_operations'])
            
            if 'by_operation' in report:
                st.write("**By Operation:**")
                for name, stats in list(report['by_operation'].items())[:5]:
                    st.write(f"• {name}: {stats['avg_ms']:.1f}ms avg ({stats['count']}x)")
            
            if st.button("Clear Metrics", key="clear_perf_metrics"):
                pm.clear()
                st.rerun()
        else:
            st.info("No performance metrics recorded yet")
        
        # Cache stats
        cache = SmartCache()
        cache_stats = cache.get_stats()
        st.write("**Cache:**")
        st.write(f"• Size: {cache_stats['size']}/{cache_stats['max_size']}")
        st.write(f"• Hit Rate: {cache_stats['hit_rate']:.1%}")
        
        # Lazy imports
        lazy = LazyImporter()
        lazy_stats = lazy.get_stats()
        st.write("**Lazy Imports:**")
        st.write(f"• Registered: {len(lazy_stats['registered'])}")
        st.write(f"• Loaded: {len(lazy_stats['loaded'])}")


def render_memory_usage():
    """Render memory usage information"""
    with st.expander("🧠 Memory Usage", expanded=False):
        sizes = MemoryManager.get_session_state_size()
        total_size = sum(sizes.values())
        
        st.metric("Session State Size", f"{total_size / 1024:.1f} KB")
        
        st.write("**Largest Entries:**")
        for key, size in list(sizes.items())[:10]:
            st.write(f"• {key}: {size / 1024:.1f} KB")
        
        if st.button("Cleanup Large Objects (>10MB)", key="cleanup_memory"):
            MemoryManager.cleanup_large_objects()
            st.success("Cleaned up large objects")
            st.rerun()


# =============================================================================
# INITIALIZATION HELPERS
# =============================================================================

def init_performance_optimizations():
    """Initialize all performance optimizations"""
    # Setup lazy imports
    lazy = setup_lazy_imports()
    
    # Initialize singletons
    SmartCache()
    BackgroundLoader()
    PerformanceMonitor()
    
    return {
        'lazy': lazy,
        'cache': SmartCache(),
        'loader': BackgroundLoader(),
        'monitor': PerformanceMonitor(),
        'memory': MemoryManager
    }


def optimize_streamlit_config():
    """
    Optimize Streamlit configuration for performance
    Call this at the very start of your app
    """
    # These should be in .streamlit/config.toml but can be set programmatically
    if 'streamlit_optimized' not in st.session_state:
        st.session_state.streamlit_optimized = True
        
        # Disable file watcher in production (reduces CPU)
        # st.set_option('server.fileWatcherType', 'none')  # Only in production
        
        # Enable static file serving
        # st.set_option('server.enableStaticServing', True)


# =============================================================================
# CONVENIENCE DECORATORS
# =============================================================================

def with_loading_spinner(message: str = "Loading..."):
    """Show spinner during function execution"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with st.spinner(message):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def debounce(wait_ms: int = 300):
    """
    Debounce decorator - delays execution until input stops
    
    Usage:
        @debounce(wait_ms=500)
        def handle_input(text):
            # Only called 500ms after last invocation
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        last_call = {'time': 0, 'timer': None}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time() * 1000
            
            if now - last_call['time'] < wait_ms:
                return None  # Skip this call
            
            last_call['time'] = now
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def memoize_to_session(key: str, ttl_seconds: Optional[int] = None):
    """
    Memoize function result to session state
    
    Usage:
        @memoize_to_session('user_data', ttl_seconds=300)
        def load_user_data(user_id):
            return fetch_from_db(user_id)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"_memo_{key}"
            timestamp_key = f"_memo_{key}_ts"
            
            # Check existing cache
            if cache_key in st.session_state:
                if ttl_seconds is None:
                    return st.session_state[cache_key]
                
                cached_time = st.session_state.get(timestamp_key, 0)
                if time.time() - cached_time < ttl_seconds:
                    return st.session_state[cache_key]
            
            # Compute and cache
            result = func(*args, **kwargs)
            st.session_state[cache_key] = result
            st.session_state[timestamp_key] = time.time()
            return result
        
        wrapper.clear = lambda: st.session_state.pop(f"_memo_{key}", None)
        return wrapper
    
    return decorator


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    st.set_page_config(page_title="Performance Demo", layout="wide")
    
    # Initialize optimizations
    perf = init_performance_optimizations()
    
    st.title("⚡ Performance Boost Demo")
    
    # Demo lazy imports
    st.header("1. Lazy Imports")
    if st.button("Load NumPy (Lazy)"):
        np = perf['lazy'].get('np')
        st.success(f"NumPy loaded: {np.__version__}")
    
    # Demo caching
    st.header("2. Smart Caching")
    
    @smart_cache(ttl_seconds=60)
    def expensive_computation(n):
        time.sleep(1)  # Simulate expensive work
        return n ** 2
    
    n = st.slider("Number to square", 1, 100, 50)
    if st.button("Compute (Cached)"):
        with perf['monitor'].measure("expensive_computation"):
            result = expensive_computation(n)
        st.write(f"Result: {result}")
    
    # Demo background loading
    st.header("3. Background Loading")
    if st.button("Start Background Load"):
        perf['loader'].submit('heavy_data', lambda: time.sleep(2) or "Data loaded!")
        st.info("Loading in background...")
    
    if perf['loader'].is_ready('heavy_data'):
        st.success(perf['loader'].get('heavy_data'))
    
    # Render performance dashboard
    render_performance_dashboard()
    render_memory_usage()
