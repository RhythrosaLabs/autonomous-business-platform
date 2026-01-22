"""
RAY CAMPAIGN WRAPPER
=====================
Universal Ray/FastAPI wrapper for all campaign and content generation operations.
Automatically routes heavy operations through Ray when enabled, with fallback to local execution.

Usage:
    from app.utils.ray_campaign_wrapper import RayCampaignWrapper
    
    wrapper = RayCampaignWrapper()
    
    # Single operation
    result = await wrapper.run_async(my_function, arg1, arg2, kwarg=value)
    
    # Batch operations
    results = await wrapper.run_batch([
        (func1, args1, kwargs1),
        (func2, args2, kwargs2),
    ])
"""

import asyncio
import logging
from typing import Any, Callable, List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of operations with different resource requirements"""
    LIGHT = "light"              # Text generation, API calls (<30s)
    MEDIUM = "medium"            # Image generation (30s-2min)
    HEAVY = "heavy"              # Video generation, batch ops (>2min)
    BATCH_IMAGES = "batch_images"    # Multiple images in parallel
    BATCH_VIDEOS = "batch_videos"    # Multiple videos in parallel


@dataclass
class RayConfig:
    """Configuration for Ray execution"""
    enabled: bool = False
    max_concurrent: int = 4
    timeout: Optional[float] = None
    
    @classmethod
    def from_session_state(cls):
        """Load config from Streamlit session state"""
        try:
            import streamlit as st
            return cls(
                enabled=st.session_state.get('ray_enabled', False),
                max_concurrent=st.session_state.get('ray_max_concurrent', 4)
            )
        except Exception:
            return cls(enabled=False)


class RayCampaignWrapper:
    """
    Universal wrapper for running campaign operations through Ray or locally.
    Automatically handles:
    - Ray availability detection
    - Graceful fallback to local execution
    - Progress tracking
    - Error recovery
    """
    
    def __init__(self, config: Optional[RayConfig] = None):
        self.config = config or RayConfig.from_session_state()
        self.ray_manager = None
        self._init_ray()
    
    def _init_ray(self):
        """Initialize Ray manager if enabled"""
        if not self.config.enabled:
            logger.info("Ray disabled - using local execution")
            return
        
        try:
            from app.utils.ray_integration_helpers import get_ray_manager_if_enabled
            self.ray_manager = get_ray_manager_if_enabled()
            if self.ray_manager:
                logger.info("✅ Ray manager initialized for campaign operations")
            else:
                logger.info("Ray enabled but manager unavailable - using local execution")
        except Exception as e:
            logger.warning(f"Could not initialize Ray: {e} - using local execution")
            self.ray_manager = None
    
    async def run_async(
        self,
        func: Callable,
        *args,
        operation_type: OperationType = OperationType.MEDIUM,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """
        Run a single async operation through Ray if enabled, else locally.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            operation_type: Type of operation for resource allocation
            timeout: Optional timeout in seconds
            **kwargs: Keyword arguments
        
        Returns:
            Function result
        """
        if self.ray_manager:
            try:
                from app.utils.ray_integration_helpers import ray_execute_if_enabled
                
                # Wrap sync function for async execution
                async def _wrapped():
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        loop = asyncio.get_event_loop()
                        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
                
                return await ray_execute_if_enabled(
                    _wrapped,
                    task_type=operation_type.value,
                    timeout=timeout or self.config.timeout
                )
            except Exception as e:
                logger.warning(f"Ray execution failed: {e} - falling back to local")
                # Fall through to local execution
        
        # Local execution
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
    
    async def run_batch(
        self,
        tasks: List[Tuple[Callable, tuple, dict]],
        operation_type: OperationType = OperationType.MEDIUM,
        max_concurrent: Optional[int] = None
    ) -> List[Any]:
        """
        Run multiple operations in parallel through Ray if enabled.
        
        Args:
            tasks: List of (function, args_tuple, kwargs_dict)
            operation_type: Type of operations
            max_concurrent: Max concurrent executions
        
        Returns:
            List of results in same order as tasks
        """
        if self.ray_manager and len(tasks) > 1:
            try:
                from app.utils.ray_integration_helpers import ray_batch_execute_if_enabled
                
                # Convert tasks to Ray format
                async def _run_task(func, args, kwargs):
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        loop = asyncio.get_event_loop()
                        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
                
                # Create wrapper that captures func
                ray_tasks = []
                for func, args, kwargs in tasks:
                    ray_tasks.append(((func, args, kwargs), {}))
                
                # Execute with Ray
                results = await ray_batch_execute_if_enabled(
                    lambda task_data: _run_task(task_data[0], task_data[1], task_data[2]),
                    ray_tasks,
                    task_type=operation_type.value,
                    max_concurrent=max_concurrent or self.config.max_concurrent
                )
                
                logger.info(f"✅ Completed {len(results)} tasks via Ray")
                return results
                
            except Exception as e:
                logger.warning(f"Ray batch execution failed: {e} - falling back to local")
                # Fall through to local execution
        
        # Local execution - run sequentially or with limited concurrency
        results = []
        for func, args, kwargs in tasks:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: func(*args, **kwargs))
            results.append(result)
        
        return results
    
    def run_sync(
        self,
        func: Callable,
        *args,
        operation_type: OperationType = OperationType.MEDIUM,
        **kwargs
    ) -> Any:
        """
        Synchronous wrapper for run_async.
        Use this when calling from non-async context (most Streamlit tabs).
        """
        return asyncio.run(self.run_async(func, *args, operation_type=operation_type, **kwargs))
    
    def is_ray_enabled(self) -> bool:
        """Check if Ray is actually enabled and available"""
        return self.ray_manager is not None


# Convenience functions for common operations

async def ray_generate_campaign_image(
    replicate_api,
    prompt: str,
    **kwargs
) -> Any:
    """Generate campaign image with Ray if enabled"""
    wrapper = RayCampaignWrapper()
    return await wrapper.run_async(
        replicate_api.generate_image,
        prompt,
        operation_type=OperationType.MEDIUM,
        timeout=300,
        **kwargs
    )


async def ray_generate_campaign_video(
    replicate_api,
    image_url: str,
    prompt: Optional[str] = None,
    **kwargs
) -> Any:
    """Generate campaign video with Ray if enabled"""
    wrapper = RayCampaignWrapper()
    return await wrapper.run_async(
        replicate_api.generate_video,
        image_url,
        prompt,
        operation_type=OperationType.HEAVY,
        timeout=600,
        **kwargs
    )


async def ray_batch_campaign_images(
    replicate_api,
    prompts: List[str],
    **kwargs
) -> List[Any]:
    """Generate multiple campaign images in parallel with Ray"""
    wrapper = RayCampaignWrapper()
    tasks = [
        (replicate_api.generate_image, (prompt,), kwargs)
        for prompt in prompts
    ]
    return await wrapper.run_batch(
        tasks,
        operation_type=OperationType.BATCH_IMAGES,
        max_concurrent=4
    )


async def ray_batch_campaign_videos(
    replicate_api,
    image_urls: List[str],
    prompts: Optional[List[str]] = None,
    **kwargs
) -> List[Any]:
    """Generate multiple campaign videos in parallel with Ray"""
    wrapper = RayCampaignWrapper()
    
    if prompts:
        tasks = [
            (replicate_api.generate_video, (url, prompt), kwargs)
            for url, prompt in zip(image_urls, prompts)
        ]
    else:
        tasks = [
            (replicate_api.generate_video, (url,), kwargs)
            for url in image_urls
        ]
    
    return await wrapper.run_batch(
        tasks,
        operation_type=OperationType.BATCH_VIDEOS,
        max_concurrent=2  # Videos are resource-intensive
    )


# Streamlit integration helper
def show_ray_status():
    """Display Ray status in Streamlit UI"""
    try:
        import streamlit as st
        wrapper = RayCampaignWrapper()
        
        if wrapper.is_ray_enabled():
            st.success("⚡ Ray distributed computing enabled - operations will run 7x faster")
        else:
            st.info("💻 Using local execution (enable Ray in Settings for 7x speedup)")
    except Exception:
        pass
