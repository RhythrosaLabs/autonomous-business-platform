"""
TAB JOB HELPERS
===============
Convenient helpers for each tab to submit jobs to the global queue.
Makes it easy to parallelize operations across all tabs.
"""

from typing import Any, Callable, Dict, Optional
from app.services.global_job_queue import get_global_job_queue, JobType
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# PRODUCTS TAB HELPERS
# ============================================================================

def submit_product_design_job(
    prompt: str,
    api: Any,
    width: int = 1024,
    height: int = 1024,
    priority: int = 5,
    **kwargs
) -> str:
    """Submit a product design generation job."""
    queue = get_global_job_queue()
    
    def generate_design():
        return api.generate_image(
            prompt=prompt,
            width=width,
            height=height,
            **kwargs
        )
    
    return queue.submit_job(
        job_type=JobType.IMAGE_GENERATION,
        tab_name="Products",
        description=f"Generate design: {prompt[:50]}...",
        function=generate_design,
        priority=priority,
        metadata={
            'prompt': prompt,
            'width': width,
            'height': height
        }
    )


def submit_batch_product_designs(
    prompts: list,
    api: Any,
    width: int = 1024,
    height: int = 1024,
    priority: int = 6
) -> list:
    """Submit multiple product designs (returns list of job IDs)."""
    job_ids = []
    
    for i, prompt in enumerate(prompts):
        job_id = submit_product_design_job(
            prompt=prompt,
            api=api,
            width=width,
            height=height,
            priority=priority + (len(prompts) - i) // 10  # Earlier prompts slightly higher priority
        )
        job_ids.append(job_id)
    
    logger.info(f"📦 Submitted {len(job_ids)} product design jobs")
    return job_ids


# ============================================================================
# VIDEO TAB HELPERS
# ============================================================================

def submit_video_generation_job(
    image_url: str,
    prompt: str,
    api: Any,
    duration: int = 5,
    priority: int = 7,
    **kwargs
) -> str:
    """Submit a video generation job."""
    queue = get_global_job_queue()
    
    def generate_video():
        return api.generate_video(
            image_url=image_url,
            prompt=prompt,
            duration=duration,
            **kwargs
        )
    
    return queue.submit_job(
        job_type=JobType.VIDEO_GENERATION,
        tab_name="Video",
        description=f"Generate video: {prompt[:50]}...",
        function=generate_video,
        priority=priority,
        metadata={
            'image_url': image_url,
            'prompt': prompt,
            'duration': duration
        }
    )


def submit_batch_videos(
    image_urls: list,
    prompts: list,
    api: Any,
    duration: int = 5,
    priority: int = 7
) -> list:
    """Submit multiple video generations."""
    job_ids = []
    
    for image_url, prompt in zip(image_urls, prompts):
        job_id = submit_video_generation_job(
            image_url=image_url,
            prompt=prompt,
            api=api,
            duration=duration,
            priority=priority
        )
        job_ids.append(job_id)
    
    logger.info(f"🎬 Submitted {len(job_ids)} video generation jobs")
    return job_ids


# ============================================================================
# CONTENT TAB HELPERS
# ============================================================================

def submit_blog_generation_job(
    topic: str,
    api: Any,
    word_count: int = 1000,
    priority: int = 5,
    **kwargs
) -> str:
    """Submit a blog generation job."""
    queue = get_global_job_queue()
    
    def generate_blog():
        return api.generate_blog(
            topic=topic,
            word_count=word_count,
            **kwargs
        )
    
    return queue.submit_job(
        job_type=JobType.BLOG_GENERATION,
        tab_name="Content",
        description=f"Generate blog: {topic[:50]}...",
        function=generate_blog,
        priority=priority,
        metadata={
            'topic': topic,
            'word_count': word_count
        }
    )


def submit_social_content_job(
    prompt: str,
    api: Any,
    platform: str = "twitter",
    priority: int = 5,
    **kwargs
) -> str:
    """Submit a social media content generation job."""
    queue = get_global_job_queue()
    
    def generate_content():
        return api.generate_social_content(
            prompt=prompt,
            platform=platform,
            **kwargs
        )
    
    return queue.submit_job(
        job_type=JobType.TEXT_GENERATION,
        tab_name="Content",
        description=f"Generate {platform} post: {prompt[:50]}...",
        function=generate_content,
        priority=priority,
        metadata={
            'prompt': prompt,
            'platform': platform
        }
    )


# ============================================================================
# DIGITAL PRODUCTS TAB HELPERS
# ============================================================================

def submit_digital_product_job(
    product_type: str,
    specifications: dict,
    api: Any,
    priority: int = 6,
    **kwargs
) -> str:
    """Submit a digital product generation job."""
    queue = get_global_job_queue()
    
    def generate_product():
        return api.generate_digital_product(
            product_type=product_type,
            specifications=specifications,
            **kwargs
        )
    
    return queue.submit_job(
        job_type=JobType.PRODUCT_CREATION,
        tab_name="Digital Products",
        description=f"Generate {product_type}",
        function=generate_product,
        priority=priority,
        metadata={
            'product_type': product_type,
            'specifications': specifications
        }
    )


# ============================================================================
# CAMPAIGN TAB HELPERS
# ============================================================================

def submit_campaign_generation_job(
    campaign_type: str,
    parameters: dict,
    api: Any,
    priority: int = 8,
    **kwargs
) -> str:
    """Submit a campaign generation job."""
    queue = get_global_job_queue()
    
    def generate_campaign():
        return api.generate_campaign(
            campaign_type=campaign_type,
            parameters=parameters,
            **kwargs
        )
    
    return queue.submit_job(
        job_type=JobType.CAMPAIGN_GENERATION,
        tab_name="Campaigns",
        description=f"Generate {campaign_type} campaign",
        function=generate_campaign,
        priority=priority,
        metadata={
            'campaign_type': campaign_type,
            'parameters': parameters
        }
    )


# ============================================================================
# WORKFLOWS TAB HELPERS
# ============================================================================

def submit_workflow_job(
    workflow_name: str,
    workflow_func: Callable,
    args: tuple = (),
    kwargs: dict = None,
    priority: int = 7,
    metadata: dict = None
) -> str:
    """Submit a custom workflow job."""
    queue = get_global_job_queue()
    
    return queue.submit_job(
        job_type=JobType.WORKFLOW_EXECUTION,
        tab_name="Workflows",
        description=f"Execute workflow: {workflow_name}",
        function=workflow_func,
        args=args,
        kwargs=kwargs or {},
        priority=priority,
        metadata=metadata or {'workflow_name': workflow_name}
    )


# ============================================================================
# GENERIC BATCH HELPER
# ============================================================================

def submit_batch_operation(
    tab_name: str,
    operation_name: str,
    items: list,
    process_func: Callable,
    job_type: JobType = JobType.BATCH_OPERATION,
    priority: int = 6
) -> list:
    """
    Submit a batch operation (multiple items processed in parallel).
    
    Args:
        tab_name: Name of the tab
        operation_name: Description of the operation
        items: List of items to process
        process_func: Function to process each item (takes item as arg)
        job_type: Type of job
        priority: Base priority
    
    Returns:
        List of job IDs
    """
    queue = get_global_job_queue()
    job_ids = []
    
    for i, item in enumerate(items):
        job_id = queue.submit_job(
            job_type=job_type,
            tab_name=tab_name,
            description=f"{operation_name} [{i+1}/{len(items)}]",
            function=process_func,
            args=(item,),
            priority=priority,
            metadata={
                'batch_index': i,
                'batch_total': len(items),
                'operation': operation_name
            }
        )
        job_ids.append(job_id)
    
    logger.info(f"📊 Submitted batch: {len(job_ids)} jobs for {operation_name}")
    return job_ids


# ============================================================================
# RESULT COLLECTION HELPERS
# ============================================================================

def collect_job_results(job_ids: list, timeout: float = None) -> list:
    """
    Collect results from multiple jobs.
    
    Args:
        job_ids: List of job IDs
        timeout: Optional timeout per job in seconds
    
    Returns:
        List of results (in same order as job_ids)
    """
    queue = get_global_job_queue()
    results = []
    
    for job_id in job_ids:
        try:
            result = queue.get_job_result(job_id, timeout=timeout)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to get result for job {job_id}: {e}")
            results.append(None)
    
    return results


def wait_for_all_jobs(job_ids: list, check_interval: float = 1.0, max_wait: float = 300.0) -> Dict[str, Any]:
    """
    Wait for all jobs to complete.
    
    Args:
        job_ids: List of job IDs to wait for
        check_interval: How often to check status (seconds)
        max_wait: Maximum time to wait (seconds)
    
    Returns:
        Dictionary with results and statistics
    """
    import time
    from app.services.global_job_queue import JobStatus
    
    queue = get_global_job_queue()
    start_time = time.time()
    
    completed_results = {}
    failed_jobs = []
    
    while time.time() - start_time < max_wait:
        all_done = True
        
        for job_id in job_ids:
            if job_id in completed_results or job_id in failed_jobs:
                continue
            
            job = queue.get_job(job_id)
            if not job:
                continue
            
            status = queue.get_job_status(job_id)
            
            if status == JobStatus.COMPLETED:
                completed_results[job_id] = queue.get_job_result(job_id)
            elif status == JobStatus.FAILED:
                failed_jobs.append(job_id)
            else:
                all_done = False
        
        if all_done:
            break
        
        time.sleep(check_interval)
    
    return {
        'completed': completed_results,
        'failed': failed_jobs,
        'total': len(job_ids),
        'success_rate': len(completed_results) / len(job_ids) if job_ids else 0,
        'duration': time.time() - start_time
    }


# ============================================================================
# STATUS CHECK HELPERS
# ============================================================================

def check_jobs_progress(job_ids: list) -> Dict[str, int]:
    """
    Check progress of multiple jobs.
    
    Returns:
        Dictionary with counts of each status
    """
    from app.services.global_job_queue import JobStatus
    
    queue = get_global_job_queue()
    
    status_counts = {
        'queued': 0,
        'running': 0,
        'completed': 0,
        'failed': 0,
        'cancelled': 0
    }
    
    for job_id in job_ids:
        status = queue.get_job_status(job_id)
        if status:
            status_counts[status.value] += 1
    
    return status_counts


def are_all_jobs_done(job_ids: list) -> bool:
    """Check if all jobs are completed or failed."""
    from app.services.global_job_queue import JobStatus
    
    queue = get_global_job_queue()
    
    for job_id in job_ids:
        status = queue.get_job_status(job_id)
        if status in [JobStatus.QUEUED, JobStatus.RUNNING]:
            return False
    
    return True
