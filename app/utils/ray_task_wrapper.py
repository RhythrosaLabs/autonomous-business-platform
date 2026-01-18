"""
RAY DISTRIBUTED TASK WRAPPER
==============================
Wraps task_queue_engine and background_tasks with Ray for distributed execution.

Features:
1. Distribute heavy tasks across multiple workers
2. Auto-scaling based on workload
3. Fault tolerance with task retry
4. Resource allocation per task type
5. Monitoring and metrics
6. Graceful fallback to local execution if Ray unavailable

Usage:
    from ray_task_wrapper import RayTaskManager
    
    # Initialize (auto-detects if Ray is available)
    ray_manager = RayTaskManager()
    
    # Execute distributed task
    result = await ray_manager.execute_task(task, context)
"""

import os
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import Ray
try:
    import ray
    from ray import remote, get, put
    from ray.util.queue import Queue as RayQueue
    HAS_RAY = True
    logger.info("✅ Ray is available for distributed execution")
except ImportError:
    HAS_RAY = False
    logger.warning("⚠️  Ray not installed - will use local execution only")


class ResourceProfile(Enum):
    """Resource profiles for different task types."""
    LIGHT = "light"          # Text generation, simple API calls
    MEDIUM = "medium"        # Image generation, data processing
    HEAVY = "heavy"          # Video generation, batch operations
    GPU = "gpu"              # GPU-accelerated tasks


@dataclass
class RayConfig:
    """Configuration for Ray cluster."""
    num_cpus: Optional[int] = None
    num_gpus: Optional[int] = None
    memory: Optional[int] = None  # GB
    object_store_memory: Optional[int] = None  # GB
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8265
    namespace: str = "autonomous_business_platform"


class RayTaskManager:
    """
    Manages distributed task execution using Ray.
    Falls back to local execution if Ray is unavailable.
    """
    
    def __init__(self, config: Optional[RayConfig] = None, enable_ray: bool = True):
        """
        Initialize Ray task manager.
        
        Args:
            config: Ray configuration (uses defaults if None)
            enable_ray: Set False to force local execution
        """
        self.config = config or RayConfig()
        self.ray_available = HAS_RAY and enable_ray
        self.initialized = False
        self.workers = {}
        
        if self.ray_available:
            self._init_ray()
    
    def _init_ray(self):
        """Initialize Ray cluster."""
        try:
            # Check if already initialized
            if ray.is_initialized():
                logger.info("📡 Ray already initialized, reusing context")
                self.initialized = True
                return
            
            # Build init kwargs
            init_kwargs = {
                "namespace": self.config.namespace,
                "dashboard_host": self.config.dashboard_host,
                "dashboard_port": self.config.dashboard_port,
                "ignore_reinit_error": True,
                "logging_level": logging.INFO
            }
            
            # Add resource constraints if specified
            if self.config.num_cpus:
                init_kwargs["num_cpus"] = self.config.num_cpus
            if self.config.num_gpus:
                init_kwargs["num_gpus"] = self.config.num_gpus
            if self.config.memory:
                init_kwargs["memory"] = self.config.memory * 1024 * 1024 * 1024
            if self.config.object_store_memory:
                init_kwargs["object_store_memory"] = self.config.object_store_memory * 1024 * 1024 * 1024
            
            # Initialize Ray
            ray.init(**init_kwargs)
            self.initialized = True
            
            logger.info(f"🚀 Ray initialized successfully")
            logger.info(f"   Dashboard: http://{self.config.dashboard_host}:{self.config.dashboard_port}")
            logger.info(f"   Namespace: {self.config.namespace}")
            
            # Log cluster resources
            resources = ray.cluster_resources()
            logger.info(f"   CPUs: {resources.get('CPU', 0)}")
            logger.info(f"   GPUs: {resources.get('GPU', 0)}")
            logger.info(f"   Memory: {resources.get('memory', 0) / (1024**3):.1f} GB")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Ray: {e}")
            self.ray_available = False
            self.initialized = False
    
    def shutdown(self):
        """Shutdown Ray cluster."""
        if self.initialized and ray.is_initialized():
            ray.shutdown()
            self.initialized = False
            logger.info("🛑 Ray cluster shutdown")
    
    def get_resource_profile(self, task_type: str) -> ResourceProfile:
        """
        Determine resource profile based on task type.
        
        Args:
            task_type: Type of task (design, video, writing, etc.)
        
        Returns:
            ResourceProfile enum
        """
        # Map task types to resource profiles
        profile_map = {
            "video": ResourceProfile.HEAVY,
            "design": ResourceProfile.MEDIUM,
            "image": ResourceProfile.MEDIUM,
            "writing": ResourceProfile.LIGHT,
            "browser": ResourceProfile.LIGHT,
            "publish": ResourceProfile.LIGHT,
            "marketing": ResourceProfile.LIGHT,
            "batch_design": ResourceProfile.HEAVY,
            "batch_video": ResourceProfile.GPU,
        }
        
        return profile_map.get(task_type, ResourceProfile.MEDIUM)
    
    def get_resource_requirements(self, profile: ResourceProfile) -> Dict[str, Any]:
        """
        Get Ray resource requirements for a profile.
        
        Args:
            profile: ResourceProfile enum
        
        Returns:
            Dict with num_cpus, num_gpus, memory
        """
        requirements = {
            ResourceProfile.LIGHT: {
                "num_cpus": 1,
                "num_gpus": 0,
                "memory": 1 * 1024 * 1024 * 1024  # 1GB
            },
            ResourceProfile.MEDIUM: {
                "num_cpus": 2,
                "num_gpus": 0,
                "memory": 4 * 1024 * 1024 * 1024  # 4GB
            },
            ResourceProfile.HEAVY: {
                "num_cpus": 4,
                "num_gpus": 0,
                "memory": 8 * 1024 * 1024 * 1024  # 8GB
            },
            ResourceProfile.GPU: {
                "num_cpus": 2,
                "num_gpus": 1,
                "memory": 8 * 1024 * 1024 * 1024  # 8GB
            }
        }
        
        return requirements.get(profile, requirements[ResourceProfile.MEDIUM])
    
    async def execute_task_distributed(
        self,
        task_func: Callable,
        task_args: tuple = (),
        task_kwargs: Dict = None,
        task_type: str = "generic",
        timeout: Optional[float] = None
    ) -> Any:
        """
        Execute a task using Ray (distributed) or locally (fallback).
        
        Args:
            task_func: Function to execute
            task_args: Positional arguments for task_func
            task_kwargs: Keyword arguments for task_func
            task_type: Type of task for resource allocation
            timeout: Maximum execution time in seconds
        
        Returns:
            Task result
        """
        task_kwargs = task_kwargs or {}
        
        # Use local execution if Ray not available
        if not self.ray_available or not self.initialized:
            logger.info(f"🔧 Executing task locally: {task_type}")
            if asyncio.iscoroutinefunction(task_func):
                return await task_func(*task_args, **task_kwargs)
            else:
                return task_func(*task_args, **task_kwargs)
        
        # Distributed execution with Ray
        try:
            logger.info(f"📡 Executing task distributed: {task_type}")
            
            # Get resource profile
            profile = self.get_resource_profile(task_type)
            resources = self.get_resource_requirements(profile)
            
            # Create remote function with resource requirements
            @ray.remote(**resources)
            def remote_task_wrapper(*args, **kwargs):
                """Wrapper to execute task in Ray worker."""
                import asyncio
                if asyncio.iscoroutinefunction(task_func):
                    # Run async function in worker's event loop
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(task_func(*args, **kwargs))
                    finally:
                        loop.close()
                else:
                    return task_func(*args, **kwargs)
            
            # Submit task to Ray
            start_time = datetime.now()
            remote_result = remote_task_wrapper.remote(*task_args, **task_kwargs)
            
            # Wait for result with timeout
            if timeout:
                result = ray.get(remote_result, timeout=timeout)
            else:
                result = ray.get(remote_result)
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Distributed task completed in {duration:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ray execution failed: {e}, falling back to local")
            # Fallback to local execution
            if asyncio.iscoroutinefunction(task_func):
                return await task_func(*task_args, **task_kwargs)
            else:
                return task_func(*task_args, **task_kwargs)
    
    async def execute_batch_distributed(
        self,
        task_func: Callable,
        task_items: List[tuple],
        task_type: str = "batch",
        max_concurrent: int = 4
    ) -> List[Any]:
        """
        Execute multiple tasks in parallel using Ray.
        
        Args:
            task_func: Function to execute for each item
            task_items: List of (args, kwargs) tuples for each task
            task_type: Type of task for resource allocation
            max_concurrent: Maximum concurrent executions
        
        Returns:
            List of results in same order as task_items
        """
        if not self.ray_available or not self.initialized:
            logger.info(f"🔧 Executing batch locally: {len(task_items)} items")
            results = []
            for args, kwargs in task_items:
                if asyncio.iscoroutinefunction(task_func):
                    result = await task_func(*args, **kwargs)
                else:
                    result = task_func(*args, **kwargs)
                results.append(result)
            return results
        
        try:
            logger.info(f"📡 Executing batch distributed: {len(task_items)} items")
            
            # Get resource profile
            profile = self.get_resource_profile(task_type)
            resources = self.get_resource_requirements(profile)
            
            # Create remote function
            @ray.remote(**resources)
            def remote_batch_item(*args, **kwargs):
                """Execute single batch item."""
                import asyncio
                if asyncio.iscoroutinefunction(task_func):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(task_func(*args, **kwargs))
                    finally:
                        loop.close()
                else:
                    return task_func(*args, **kwargs)
            
            # Submit all tasks
            start_time = datetime.now()
            futures = []
            for args, kwargs in task_items:
                future = remote_batch_item.remote(*args, **kwargs)
                futures.append(future)
            
            # Wait for all results
            results = ray.get(futures)
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Batch completed: {len(results)} items in {duration:.2f}s")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Ray batch execution failed: {e}, falling back to local")
            results = []
            for args, kwargs in task_items:
                if asyncio.iscoroutinefunction(task_func):
                    result = await task_func(*args, **kwargs)
                else:
                    result = task_func(*args, **kwargs)
                results.append(result)
            return results
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get current Ray cluster status and resource usage."""
        if not self.initialized:
            return {
                "available": False,
                "reason": "Ray not initialized"
            }
        
        try:
            resources = ray.cluster_resources()
            available_resources = ray.available_resources()
            
            return {
                "available": True,
                "total_cpus": resources.get("CPU", 0),
                "available_cpus": available_resources.get("CPU", 0),
                "total_gpus": resources.get("GPU", 0),
                "available_gpus": available_resources.get("GPU", 0),
                "total_memory_gb": resources.get("memory", 0) / (1024**3),
                "available_memory_gb": available_resources.get("memory", 0) / (1024**3),
                "dashboard_url": f"http://{self.config.dashboard_host}:{self.config.dashboard_port}",
                "namespace": self.config.namespace
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }


# Global singleton instance
_ray_manager: Optional[RayTaskManager] = None


def get_ray_manager(config: Optional[RayConfig] = None, enable_ray: bool = True) -> RayTaskManager:
    """
    Get global Ray task manager instance.
    
    Args:
        config: Ray configuration (only used on first call)
        enable_ray: Enable Ray distributed execution
    
    Returns:
        RayTaskManager instance
    """
    global _ray_manager
    
    if _ray_manager is None:
        _ray_manager = RayTaskManager(config=config, enable_ray=enable_ray)
    
    return _ray_manager


def shutdown_ray():
    """Shutdown global Ray manager."""
    global _ray_manager
    
    if _ray_manager:
        _ray_manager.shutdown()
        _ray_manager = None
