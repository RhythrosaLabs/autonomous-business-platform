"""
Performance Optimization Utilities
Caching, parallelization, and background job management
"""

import streamlit as st
from functools import wraps
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time
from typing import Callable, Any, List
import logging

logger = logging.getLogger(__name__)

# Global thread pool for background tasks
executor = ThreadPoolExecutor(max_workers=5)


# ============================================
# CACHING DECORATORS
# ============================================

@st.cache_resource(show_spinner=False)
def get_replicate_api(token: str):
    """Cached Replicate API client - reused across pages"""
    from api_service import ReplicateAPI
    return ReplicateAPI(token)


@st.cache_resource(show_spinner=False)
def get_printify_api(token: str, shop_id: str):
    """Cached Printify API client - reused across pages"""
    if not token or not shop_id:
        return None
    from api_service import PrintifyAPI
    return PrintifyAPI(token)


@st.cache_resource(show_spinner=False)
def get_shopify_api(shop_url: str, access_token: str):
    """Cached Shopify API client"""
    if not shop_url or not access_token:
        return None
    from shopify_service import ShopifyAPI
    return ShopifyAPI(shop_url, access_token)


@st.cache_resource(show_spinner=False)
def get_youtube_service():
    """Cached YouTube service"""
    from youtube_upload_service import YouTubeUploadService
    return YouTubeUploadService()


@st.cache_data(ttl=3600, show_spinner=False)
def load_campaign_metadata(campaign_dir: str):
    """Cache campaign metadata for 1 hour"""
    import json
    from pathlib import Path
    
    metadata_file = Path(campaign_dir) / "campaign_metadata.json"
    if metadata_file.exists():
        return json.loads(metadata_file.read_text())
    return {}


@st.cache_data(ttl=7200, show_spinner=False)
def get_printify_blueprints(token: str):
    """Cache Printify blueprints for 2 hours (rarely changes)"""
    from api_service import PrintifyAPI
    api = PrintifyAPI(token)
    return api.get_blueprints()


# ============================================
# RETRY LOGIC
# ============================================

def retry_on_failure(max_retries=3, delay=1, exponential_backoff=True):
    """Decorator to retry failed API calls"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed after {max_retries} attempts: {e}")
                        raise
                    
                    wait_time = delay * (2 ** attempt if exponential_backoff else 1)
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
        return wrapper
    return decorator


# ============================================
# PARALLEL EXECUTION
# ============================================

async def run_parallel_async(tasks: List[Callable]):
    """Run multiple async tasks in parallel"""
    return await asyncio.gather(*tasks, return_exceptions=True)


def run_parallel_sync(funcs: List[Callable], *args_list) -> List[Any]:
    """
    Run multiple synchronous functions in parallel using ThreadPoolExecutor
    
    Args:
        funcs: List of functions to execute
        args_list: List of argument tuples for each function
    
    Returns:
        List of results (same order as input)
    """
    futures = []
    for func, args in zip(funcs, args_list):
        future = executor.submit(func, *args)
        futures.append(future)
    
    results = []
    for future in futures:
        try:
            results.append(future.result())
        except Exception as e:
            logger.error(f"Parallel execution error: {e}")
            results.append(None)
    
    return results


def run_in_background(func: Callable, *args, **kwargs):
    """
    Run a function in background thread, return Future
    
    Usage:
        future = run_in_background(generate_video, mockups, output_path)
        # Do other stuff...
        result = future.result()  # Wait for completion
    """
    return executor.submit(func, *args, **kwargs)


# ============================================
# CHECKPOINTING
# ============================================

class CheckpointManager:
    """Manage checkpoints for long-running workflows"""
    
    def __init__(self, campaign_dir):
        from pathlib import Path
        self.campaign_dir = Path(campaign_dir)
        self.checkpoint_dir = self.campaign_dir / ".checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, phase: str, data: dict):
        """Save checkpoint for a phase"""
        import json
        checkpoint_file = self.checkpoint_dir / f"{phase}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Checkpoint saved: {phase}")
    
    def load(self, phase: str) -> dict:
        """Load checkpoint for a phase"""
        import json
        checkpoint_file = self.checkpoint_dir / f"{phase}.json"
        if checkpoint_file.exists():
            with open(checkpoint_file) as f:
                return json.load(f)
        return {}
    
    def exists(self, phase: str) -> bool:
        """Check if checkpoint exists"""
        checkpoint_file = self.checkpoint_dir / f"{phase}.json"
        return checkpoint_file.exists()
    
    def clear_all(self):
        """Clear all checkpoints"""
        import shutil
        if self.checkpoint_dir.exists():
            shutil.rmtree(self.checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)


# ============================================
# PROGRESS TRACKING
# ============================================

class ProgressTracker:
    """Track progress of multi-step operations"""
    
    def __init__(self, total_steps: int, status_container=None):
        self.total_steps = total_steps
        self.current_step = 0
        self.status_container = status_container or st
        self.progress_bar = self.status_container.progress(0)
        self.status_text = self.status_container.empty()
    
    def update(self, step_name: str):
        """Update progress"""
        self.current_step += 1
        progress = self.current_step / self.total_steps
        self.progress_bar.progress(progress)
        self.status_text.markdown(
            f"**Step {self.current_step}/{self.total_steps}:** {step_name}"
        )
    
    def complete(self):
        """Mark as complete"""
        self.progress_bar.progress(1.0)
        self.status_text.markdown("✅ **Complete!**")


# ============================================
# LAZY LOADING
# ============================================

class LazyLoader:
    """Lazy load heavy modules only when needed"""
    
    def __init__(self, module_name: str):
        self.module_name = module_name
        self._module = None
    
    def __getattr__(self, name):
        if self._module is None:
            import importlib
            self._module = importlib.import_module(self.module_name)
        return getattr(self._module, name)


# Lazy loaders for heavy modules
moviepy = LazyLoader('moviepy.editor')
PIL_Image = LazyLoader('PIL.Image')


# ============================================
# MEMORY MANAGEMENT
# ============================================

def keep_in_memory(data: dict) -> dict:
    """
    Keep generated assets in memory instead of writing to disk immediately
    Only write to disk at the end
    """
    memory_cache = st.session_state.get('memory_cache', {})
    memory_cache.update(data)
    st.session_state.memory_cache = memory_cache
    return memory_cache


def flush_to_disk(campaign_dir, memory_cache: dict):
    """Write all cached data to disk at once"""
    from pathlib import Path
    import json
    
    for file_path, content in memory_cache.items():
        full_path = Path(campaign_dir) / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        if isinstance(content, bytes):
            full_path.write_bytes(content)
        elif isinstance(content, dict) or isinstance(content, list):
            full_path.write_text(json.dumps(content, indent=2))
        else:
            full_path.write_text(str(content))
    
    logger.info(f"Flushed {len(memory_cache)} files to disk")
