"""
GLOBAL RAY JOB QUEUE
====================
Enables multiple tabs to submit work simultaneously and process in parallel.
Users can generate products, videos, content, etc. all at once without blocking.

Architecture:
- Central job queue backed by Ray
- Each tab submits jobs to queue
- Ray distributes work across workers
- Results stored and retrieved per job
- Real-time status updates
"""

import logging
import uuid
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)

# Try to import Ray
try:
    import ray
    from ray import remote, get, put
    HAS_RAY = True
except ImportError:
    HAS_RAY = False


class JobStatus(Enum):
    """Job status in the queue."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(Enum):
    """Types of jobs that can be queued."""
    IMAGE_GENERATION = "image_generation"
    VIDEO_GENERATION = "video_generation"
    TEXT_GENERATION = "text_generation"
    PRODUCT_CREATION = "product_creation"
    CAMPAIGN_GENERATION = "campaign_generation"
    BLOG_GENERATION = "blog_generation"
    WORKFLOW_EXECUTION = "workflow_execution"
    BATCH_OPERATION = "batch_operation"


# Resource profiles for different job types
RESOURCE_PROFILES = {
    JobType.VIDEO_GENERATION: {
        "num_cpus": 2,
        "memory": 4_000_000_000,  # 4GB
        "description": "Heavy video generation tasks"
    },
    JobType.IMAGE_GENERATION: {
        "num_cpus": 1,
        "memory": 2_000_000_000,  # 2GB
        "description": "Image generation tasks"
    },
    JobType.TEXT_GENERATION: {
        "num_cpus": 0.5,
        "memory": 512_000_000,  # 512MB
        "description": "Text/LLM generation tasks"
    },
    JobType.CAMPAIGN_GENERATION: {
        "num_cpus": 1,
        "memory": 1_000_000_000,  # 1GB
        "description": "Campaign/spreadsheet generation"
    },
    JobType.PRODUCT_CREATION: {
        "num_cpus": 1,
        "memory": 1_500_000_000,  # 1.5GB
        "description": "Product design creation"
    },
    JobType.BLOG_GENERATION: {
        "num_cpus": 0.5,
        "memory": 512_000_000,  # 512MB
        "description": "Blog content generation"
    },
    JobType.BATCH_OPERATION: {
        "num_cpus": 0.5,
        "memory": 256_000_000,  # 256MB
        "description": "Lightweight batch operations"
    },
    JobType.WORKFLOW_EXECUTION: {
        "num_cpus": 1,
        "memory": 1_000_000_000,  # 1GB
        "description": "Workflow execution tasks"
    }
}


@dataclass
class Job:
    """Represents a job in the global queue."""
    id: str
    job_type: JobType
    tab_name: str
    description: str
    function: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    status: JobStatus = JobStatus.QUEUED
    priority: int = 5  # 1-10, higher = more priority
    result: Any = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    metadata: Dict = field(default_factory=dict)
    
    def duration(self) -> Optional[float]:
        """Get job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'job_type': self.job_type.value,
            'tab_name': self.tab_name,
            'description': self.description,
            'status': self.status.value,
            'priority': self.priority,
            'result': str(self.result) if self.result else None,
            'error': self.error,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'progress': self.progress,
            'duration': self.duration(),
            'metadata': self.metadata
        }


class GlobalJobQueue:
    """
    Global job queue backed by Ray for parallel execution across all tabs.
    
    Features:
    - Submit jobs from any tab
    - Automatic prioritization
    - Parallel execution with Ray
    - Result retrieval per job ID
    - Progress tracking
    - Resource-aware scheduling
    """
    
    def __init__(self, max_concurrent_jobs: int = 10):
        """
        Initialize global job queue.
        
        Args:
            max_concurrent_jobs: Maximum jobs running simultaneously
        """
        self.max_concurrent_jobs = max_concurrent_jobs
        self.jobs: Dict[str, Job] = {}
        self.ray_available = HAS_RAY
        self._running_futures = {}
        
        if self.ray_available:
            self._init_ray()
        
        logger.info(f"✅ Global Job Queue initialized (Ray: {self.ray_available})")
    
    def _init_ray(self):
        """Initialize Ray if not already initialized."""
        try:
            if not ray.is_initialized():
                ray.init(
                    namespace="global_job_queue",
                    ignore_reinit_error=True,
                    logging_level=logging.INFO
                )
                logger.info("🚀 Ray initialized for global job queue")
        except Exception as e:
            logger.error(f"Failed to initialize Ray: {e}")
            self.ray_available = False
    
    def submit_job(
        self,
        job_type: JobType,
        tab_name: str,
        description: str,
        function: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: int = 5,
        metadata: Dict = None
    ) -> str:
        """
        Submit a job to the global queue.
        
        Args:
            job_type: Type of job
            tab_name: Tab submitting the job
            description: Human-readable description
            function: Function to execute
            args: Positional arguments
            kwargs: Keyword arguments
            priority: Job priority (1-10)
            metadata: Additional metadata
        
        Returns:
            Job ID for tracking
        """
        job_id = str(uuid.uuid4())
        kwargs = kwargs or {}
        metadata = metadata or {}
        
        job = Job(
            id=job_id,
            job_type=job_type,
            tab_name=tab_name,
            description=description,
            function=function,
            args=args,
            kwargs=kwargs,
            priority=priority,
            metadata=metadata
        )
        
        self.jobs[job_id] = job
        
        # Start execution if Ray available
        if self.ray_available:
            self._execute_job_async(job)
        else:
            # Execute locally in background
            self._execute_job_local(job)
        
        logger.info(f"📥 Job submitted: {job_id} ({tab_name}: {description})")
        return job_id
    
    def _execute_job_async(self, job: Job):
        """Execute job using Ray (non-blocking) with resource profiling."""
        # Get resource requirements for this job type
        resources = RESOURCE_PROFILES.get(job.job_type, {
            "num_cpus": 1,
            "memory": 1_000_000_000
        })
        
        @ray.remote(
            num_cpus=resources.get("num_cpus", 1),
            memory=resources.get("memory", 1_000_000_000)
        )
        def execute_job_remote(func, args, kwargs):
            """Remote execution wrapper with resource allocation."""
            try:
                if asyncio.iscoroutinefunction(func):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(func(*args, **kwargs))
                    finally:
                        loop.close()
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                raise e
        
        # Submit to Ray
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now()
        
        # Log resource allocation
        logger.info(f"🎯 Job {job.id[:8]} allocated: {resources.get('num_cpus')} CPUs, "
                   f"{resources.get('memory') / 1_000_000:.0f}MB RAM")
        
        future = execute_job_remote.remote(job.function, job.args, job.kwargs)
        self._running_futures[job.id] = future
        
        # Check result asynchronously (non-blocking)
        # The result will be available when user calls get_job_result()
    
    def _execute_job_local(self, job: Job):
        """Execute job locally (fallback when Ray unavailable)."""
        import threading
        
        def run_job():
            try:
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now()
                
                if asyncio.iscoroutinefunction(job.function):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(job.function(*job.args, **job.kwargs))
                    finally:
                        loop.close()
                else:
                    result = job.function(*job.args, **job.kwargs)
                
                job.result = result
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now()
                job.progress = 1.0
                
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = str(e)
                job.completed_at = datetime.now()
                logger.error(f"Job {job.id} failed: {e}")
        
        thread = threading.Thread(target=run_job, daemon=True)
        thread.start()
    
    def get_job_status(self, job_id: str) -> Optional[JobStatus]:
        """Get current status of a job."""
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        # Check if Ray job completed
        if self.ray_available and job_id in self._running_futures:
            try:
                # Non-blocking check
                future = self._running_futures[job_id]
                ready, _ = ray.wait([future], timeout=0)
                
                if ready:
                    # Job completed, get result
                    try:
                        result = ray.get(future)
                        job.result = result
                        job.status = JobStatus.COMPLETED
                        job.completed_at = datetime.now()
                        job.progress = 1.0
                        del self._running_futures[job_id]
                    except Exception as e:
                        job.status = JobStatus.FAILED
                        job.error = str(e)
                        job.completed_at = datetime.now()
                        del self._running_futures[job_id]
            except Exception as e:
                logger.error(f"Error checking job status: {e}")
        
        return job.status
    
    def get_job_result(self, job_id: str, timeout: float = None) -> Any:
        """
        Get result of a completed job.
        
        Args:
            job_id: Job ID
            timeout: Wait timeout in seconds (None = don't wait)
        
        Returns:
            Job result or None if not ready
        """
        job = self.jobs.get(job_id)
        if not job:
            return None
        
        # If using Ray and job still running, optionally wait
        if self.ray_available and job_id in self._running_futures:
            future = self._running_futures[job_id]
            
            try:
                if timeout:
                    result = ray.get(future, timeout=timeout)
                else:
                    # Check if ready without waiting
                    ready, _ = ray.wait([future], timeout=0)
                    if not ready:
                        return None
                    result = ray.get(future)
                
                job.result = result
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now()
                job.progress = 1.0
                del self._running_futures[job_id]
                
            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = str(e)
                job.completed_at = datetime.now()
                del self._running_futures[job_id]
                raise e
        
        return job.result
    
    def get_job(self, job_id: str) -> Optional[Job]:
        """Get full job object."""
        return self.jobs.get(job_id)
    
    def get_all_jobs(
        self,
        tab_name: Optional[str] = None,
        status: Optional[JobStatus] = None
    ) -> List[Job]:
        """
        Get all jobs, optionally filtered.
        
        Args:
            tab_name: Filter by tab name
            status: Filter by status
        
        Returns:
            List of jobs
        """
        jobs = list(self.jobs.values())
        
        if tab_name:
            jobs = [j for j in jobs if j.tab_name == tab_name]
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        # Sort by priority (high to low), then created_at
        jobs.sort(key=lambda j: (-j.priority, j.created_at))
        
        return jobs
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued or running job."""
        job = self.jobs.get(job_id)
        if not job:
            return False
        
        if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
            return False
        
        # Cancel Ray job if running
        if self.ray_available and job_id in self._running_futures:
            try:
                ray.cancel(self._running_futures[job_id])
                del self._running_futures[job_id]
            except:
                pass
        
        job.status = JobStatus.CANCELLED
        job.completed_at = datetime.now()
        
        logger.info(f"❌ Job cancelled: {job_id}")
        return True
    
    def clear_completed_jobs(self, tab_name: Optional[str] = None):
        """Clear completed/failed jobs."""
        to_remove = []
        
        for job_id, job in self.jobs.items():
            if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                if tab_name is None or job.tab_name == tab_name:
                    to_remove.append(job_id)
        
        for job_id in to_remove:
            del self.jobs[job_id]
        
        logger.info(f"🧹 Cleared {len(to_remove)} completed jobs")
    
    def get_queue_stats(self) -> Dict:
        """Get queue statistics."""
        queued = sum(1 for j in self.jobs.values() if j.status == JobStatus.QUEUED)
        running = sum(1 for j in self.jobs.values() if j.status == JobStatus.RUNNING)
        completed = sum(1 for j in self.jobs.values() if j.status == JobStatus.COMPLETED)
        failed = sum(1 for j in self.jobs.values() if j.status == JobStatus.FAILED)
        
        # Get per-tab counts
        tab_counts = {}
        for job in self.jobs.values():
            tab_counts[job.tab_name] = tab_counts.get(job.tab_name, 0) + 1
        
        return {
            'total_jobs': len(self.jobs),
            'queued': queued,
            'running': running,
            'completed': completed,
            'failed': failed,
            'ray_available': self.ray_available,
            'max_concurrent': self.max_concurrent_jobs,
            'tab_counts': tab_counts
        }


# Global singleton instance
_global_queue: Optional[GlobalJobQueue] = None


def get_global_job_queue(max_concurrent: int = 10) -> GlobalJobQueue:
    """
    Get or create the global job queue instance.
    
    Args:
        max_concurrent: Maximum concurrent jobs (only used on first call)
    
    Returns:
        GlobalJobQueue instance
    """
    global _global_queue
    
    if _global_queue is None:
        _global_queue = GlobalJobQueue(max_concurrent_jobs=max_concurrent)
    
    return _global_queue
