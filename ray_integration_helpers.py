"""
RAY INTEGRATION HELPERS
========================
Convenient wrappers to integrate Ray distributed computing across all tabs.
These helpers make it easy to add Ray support to any operation.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple
import asyncio

logger = logging.getLogger(__name__)

# Global flag to check if Ray is enabled in session
_ray_enabled_cache = None


def is_ray_enabled() -> bool:
    """Check if Ray is enabled in Streamlit session state."""
    global _ray_enabled_cache
    
    # Try to import streamlit
    try:
        import streamlit as st
        if hasattr(st, 'session_state'):
            # Check session state first, then config default
            if 'ray_enabled' in st.session_state:
                return st.session_state.ray_enabled
            # Use config default
            try:
                from abp_config import AppConfig
                return AppConfig.ENABLE_RAY_DISTRIBUTED
            except:
                return True  # Default to enabled if config unavailable
    except:
        pass
    
    # Fallback to cached value or True (enabled by default)
    if _ray_enabled_cache is not None:
        return _ray_enabled_cache
    return True  # Default enabled


def get_ray_manager_if_enabled():
    """Get Ray manager if enabled, otherwise return None."""
    if not is_ray_enabled():
        return None
    
    try:
        from ray_task_wrapper import get_ray_manager
        return get_ray_manager(enable_ray=True)
    except Exception as e:
        logger.warning(f"⚠️ Ray manager unavailable: {e}")
        return None


async def ray_execute_if_enabled(
    func: Callable,
    *args,
    task_type: str = "medium",
    timeout: Optional[float] = None,
    **kwargs
) -> Any:
    """
    Execute function with Ray if enabled, otherwise execute locally.
    
    Args:
        func: Function to execute
        *args: Positional arguments
        task_type: Resource profile (light/medium/heavy/gpu)
        timeout: Timeout in seconds
        **kwargs: Keyword arguments
    
    Returns:
        Function result
    """
    ray_manager = get_ray_manager_if_enabled()
    
    if ray_manager:
        try:
            return await ray_manager.execute_task_distributed(
                task_func=func,
                task_args=args,
                task_kwargs=kwargs,
                task_type=task_type,
                timeout=timeout
            )
        except Exception as e:
            logger.warning(f"⚠️ Ray execution failed, using local: {e}")
    
    # Local execution (fallback or default)
    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)


async def ray_batch_execute_if_enabled(
    func: Callable,
    items: List[Tuple[tuple, dict]],
    task_type: str = "batch",
    max_concurrent: int = 4
) -> List[Any]:
    """
    Execute batch of tasks with Ray if enabled.
    
    Args:
        func: Function to execute for each item
        items: List of (args, kwargs) tuples
        task_type: Resource profile
        max_concurrent: Maximum concurrent executions
    
    Returns:
        List of results
    """
    ray_manager = get_ray_manager_if_enabled()
    
    if ray_manager:
        try:
            return await ray_manager.execute_batch_distributed(
                task_func=func,
                task_items=items,
                task_type=task_type,
                max_concurrent=max_concurrent
            )
        except Exception as e:
            logger.warning(f"⚠️ Ray batch execution failed, using local: {e}")
    
    # Local execution (fallback or default)
    results = []
    for args, kwargs in items:
        if asyncio.iscoroutinefunction(func):
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        results.append(result)
    
    return results


# ============================================================================
# Specific Operation Wrappers
# ============================================================================

async def ray_generate_image(
    replicate_api,
    prompt: str,
    model: Optional[str] = None,
    **kwargs
) -> Any:
    """Generate image with Ray distribution."""
    
    async def _generate():
        if model:
            import replicate
            return replicate.run(model, input={"prompt": prompt, **kwargs})
        else:
            return replicate_api.generate_image(prompt, **kwargs)
    
    return await ray_execute_if_enabled(
        _generate,
        task_type="design",
        timeout=300
    )


async def ray_generate_video(
    replicate_api,
    image_url: str,
    prompt: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> Any:
    """Generate video with Ray distribution."""
    
    async def _generate():
        if model:
            import replicate
            input_data = {"image": image_url, **kwargs}
            if prompt:
                input_data["prompt"] = prompt
            return replicate.run(model, input=input_data)
        else:
            return replicate_api.generate_video(image_url, prompt, **kwargs)
    
    return await ray_execute_if_enabled(
        _generate,
        task_type="video",
        timeout=600
    )


async def ray_generate_text(
    replicate_api,
    prompt: str,
    max_tokens: int = 500,
    **kwargs
) -> str:
    """Generate text with Ray distribution (light task)."""
    
    async def _generate():
        return replicate_api.generate_text(prompt, max_tokens=max_tokens, **kwargs)
    
    return await ray_execute_if_enabled(
        _generate,
        task_type="light",
        timeout=120
    )


async def ray_batch_generate_images(
    replicate_api,
    prompts: List[str],
    model: Optional[str] = None,
    **kwargs
) -> List[Any]:
    """Batch generate images with Ray distribution."""
    
    async def _generate_one(prompt: str):
        if model:
            import replicate
            return replicate.run(model, input={"prompt": prompt, **kwargs})
        else:
            return replicate_api.generate_image(prompt, **kwargs)
    
    items = [((prompt,), {}) for prompt in prompts]
    
    return await ray_batch_execute_if_enabled(
        _generate_one,
        items,
        task_type="batch_design",
        max_concurrent=4
    )


async def ray_batch_generate_videos(
    replicate_api,
    image_urls: List[str],
    prompts: Optional[List[str]] = None,
    model: Optional[str] = None,
    **kwargs
) -> List[Any]:
    """Batch generate videos with Ray distribution."""
    
    async def _generate_one(image_url: str, prompt: Optional[str] = None):
        if model:
            import replicate
            input_data = {"image": image_url, **kwargs}
            if prompt:
                input_data["prompt"] = prompt
            return replicate.run(model, input=input_data)
        else:
            return replicate_api.generate_video(image_url, prompt, **kwargs)
    
    if prompts:
        items = [((url, prompt), {}) for url, prompt in zip(image_urls, prompts)]
    else:
        items = [((url,), {}) for url in image_urls]
    
    return await ray_batch_execute_if_enabled(
        _generate_one,
        items,
        task_type="batch_videos",
        max_concurrent=2  # Videos are heavy
    )


# ============================================================================
# Sync Wrappers (for non-async contexts)
# ============================================================================

def ray_generate_image_sync(
    replicate_api,
    prompt: str,
    model: Optional[str] = None,
    **kwargs
) -> Any:
    """Synchronous wrapper for image generation."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            ray_generate_image(replicate_api, prompt, model, **kwargs)
        )
    finally:
        loop.close()


def ray_generate_video_sync(
    replicate_api,
    image_url: str,
    prompt: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> Any:
    """Synchronous wrapper for video generation."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            ray_generate_video(replicate_api, image_url, prompt, model, **kwargs)
        )
    finally:
        loop.close()


def ray_generate_text_sync(
    replicate_api,
    prompt: str,
    max_tokens: int = 500,
    **kwargs
) -> str:
    """Synchronous wrapper for text generation."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            ray_generate_text(replicate_api, prompt, max_tokens, **kwargs)
        )
    finally:
        loop.close()


# ============================================================================
# Decorator for automatic Ray integration
# ============================================================================

def with_ray_distribution(task_type: str = "medium", timeout: Optional[float] = None):
    """
    Decorator to automatically add Ray distribution to a function.
    
    Usage:
        @with_ray_distribution(task_type="video", timeout=600)
        async def generate_video(image_url, prompt):
            # Your existing code
            return result
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            return await ray_execute_if_enabled(
                func,
                *args,
                task_type=task_type,
                timeout=timeout,
                **kwargs
            )
        return wrapper
    return decorator
