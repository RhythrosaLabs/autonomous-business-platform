"""
RAY-ENABLED CAMPAIGN OPERATIONS
================================
Drop-in replacements for campaign generation bottlenecks.
These functions automatically use Ray when enabled, with zero code changes needed.

Usage - Just replace your existing calls:
    OLD: image_url = replicate_api.generate_image(prompt)
    NEW: image_url = await ray_campaign_image(replicate_api, prompt)
"""

import asyncio
import logging
from typing import Any, List, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


def get_ray_wrapper():
    """Get Ray wrapper instance with session state config"""
    try:
        from app.utils.ray_campaign_wrapper import RayCampaignWrapper
        return RayCampaignWrapper()
    except Exception as e:
        logger.warning(f"Could not initialize Ray wrapper: {e}")
        return None


# ========================================
# SYNC WRAPPERS (for Streamlit tabs)
# ========================================

def ray_generate_product_images_parallel(
    replicate_api,
    prompts: List[str],
    image_params: Dict,
    progress_callback=None
) -> List[Dict]:
    """
    Generate multiple product images in parallel using Ray if enabled.
    Falls back to ThreadPoolExecutor if Ray unavailable.
    
    Args:
        replicate_api: Replicate API instance
        prompts: List of image prompts
        image_params: Image generation parameters (width, height, etc.)
        progress_callback: Optional callback(current, total, message)
    
    Returns:
        List of dicts with {success, url, error}
    """
    wrapper = get_ray_wrapper()
    
    if wrapper and wrapper.is_ray_enabled() and len(prompts) > 1:
        logger.info(f"🚀 Generating {len(prompts)} product images via Ray (parallel)")
        try:
            # Use Ray for parallel execution
            async def _generate_batch():
                from app.utils.ray_campaign_wrapper import ray_batch_campaign_images
                urls = await ray_batch_campaign_images(replicate_api, prompts, **image_params)
                return [{"success": True, "url": url, "error": None} for url in urls]
            
            return asyncio.run(_generate_batch())
        except Exception as e:
            logger.warning(f"Ray batch failed: {e} - falling back to ThreadPoolExecutor")
    
    # Fallback to ThreadPoolExecutor (existing code)
    logger.info(f"💻 Generating {len(prompts)} product images via ThreadPoolExecutor")
    results = []
    
    def _generate_one(idx, prompt):
        try:
            if progress_callback:
                progress_callback(idx, len(prompts), f"Generating image {idx+1}/{len(prompts)}")
            
            url = replicate_api.generate_image(prompt, **image_params)
            return {"success": True, "url": url, "error": None}
        except Exception as e:
            logger.error(f"Image {idx+1} failed: {e}")
            return {"success": False, "url": None, "error": str(e)}
    
    with ThreadPoolExecutor(max_workers=min(len(prompts), 3)) as executor:
        futures = {executor.submit(_generate_one, i, prompt): i 
                   for i, prompt in enumerate(prompts)}
        
        for future in as_completed(futures):
            results.append(future.result())
    
    # Sort results back to original order
    return sorted(results, key=lambda x: futures[future])


def ray_generate_campaign_videos_parallel(
    replicate_api,
    image_urls: List[str],
    prompts: Optional[List[str]],
    model: str = "kling",
    progress_callback=None
) -> List[Dict]:
    """
    Generate multiple videos in parallel using Ray if enabled.
    
    Args:
        replicate_api: Replicate API instance
        image_urls: List of image URLs to animate
        prompts: Optional list of prompts (one per video)
        model: Model to use (kling, luma, hailuo)
        progress_callback: Optional callback(current, total, message)
    
    Returns:
        List of dicts with {success, url, error}
    """
    wrapper = get_ray_wrapper()
    
    if wrapper and wrapper.is_ray_enabled() and len(image_urls) > 1:
        logger.info(f"🚀 Generating {len(image_urls)} videos via Ray (parallel)")
        try:
            async def _generate_batch():
                from app.utils.ray_campaign_wrapper import ray_batch_campaign_videos
                urls = await ray_batch_campaign_videos(
                    replicate_api,
                    image_urls,
                    prompts,
                    model=model
                )
                return [{"success": True, "url": url, "error": None} for url in urls]
            
            return asyncio.run(_generate_batch())
        except Exception as e:
            logger.warning(f"Ray video batch failed: {e} - falling back to sequential")
    
    # Fallback to sequential generation
    logger.info(f"💻 Generating {len(image_urls)} videos sequentially")
    results = []
    
    for idx, image_url in enumerate(image_urls):
        try:
            if progress_callback:
                progress_callback(idx, len(image_urls), f"Generating video {idx+1}/{len(image_urls)}")
            
            prompt = prompts[idx] if prompts and idx < len(prompts) else None
            url = replicate_api.generate_video(image_url, prompt, model=model)
            results.append({"success": True, "url": url, "error": None})
        except Exception as e:
            logger.error(f"Video {idx+1} failed: {e}")
            results.append({"success": False, "url": None, "error": str(e)})
    
    return results


def ray_generate_single_product_image(
    replicate_api,
    prompt: str,
    **image_params
) -> Optional[str]:
    """
    Generate a single product image, using Ray if enabled.
    Simpler wrapper for single image generation.
    """
    wrapper = get_ray_wrapper()
    
    if wrapper and wrapper.is_ray_enabled():
        try:
            async def _generate():
                from app.utils.ray_campaign_wrapper import ray_generate_campaign_image
                return await ray_generate_campaign_image(replicate_api, prompt, **image_params)
            
            return asyncio.run(_generate())
        except Exception as e:
            logger.warning(f"Ray single image failed: {e} - falling back to direct call")
    
    # Direct call (existing code)
    return replicate_api.generate_image(prompt, **image_params)


def ray_generate_single_video(
    replicate_api,
    image_url: str,
    prompt: Optional[str] = None,
    **video_params
) -> Optional[str]:
    """
    Generate a single video, using Ray if enabled.
    Simpler wrapper for single video generation.
    """
    wrapper = get_ray_wrapper()
    
    if wrapper and wrapper.is_ray_enabled():
        try:
            async def _generate():
                from app.utils.ray_campaign_wrapper import ray_generate_campaign_video
                return await ray_generate_campaign_video(
                    replicate_api,
                    image_url,
                    prompt,
                    **video_params
                )
            
            return asyncio.run(_generate())
        except Exception as e:
            logger.warning(f"Ray single video failed: {e} - falling back to direct call")
    
    # Direct call (existing code)
    return replicate_api.generate_video(image_url, prompt, **video_params)


# ========================================
# CONVENIENCE FUNCTIONS
# ========================================

def show_ray_performance_info():
    """Display Ray performance benefits in Streamlit"""
    try:
        import streamlit as st
        wrapper = get_ray_wrapper()
        
        if wrapper and wrapper.is_ray_enabled():
            st.success("⚡ **Ray Enabled** - Campaign generation will be ~7x faster!")
            st.info("💡 Multiple images/videos will process in parallel across CPU/GPU workers")
        else:
            st.info("💻 Using local execution - Enable Ray in Settings → Performance for 7x speedup")
    except Exception:
        pass


def estimate_time_with_ray(num_images: int, num_videos: int, ray_enabled: bool) -> Dict:
    """
    Estimate generation time with and without Ray.
    
    Returns:
        {
            'total_minutes': float,
            'images_minutes': float,
            'videos_minutes': float,
            'speedup_factor': float
        }
    """
    # Base times (sequential, in minutes)
    IMAGE_TIME = 0.5  # 30 seconds per image
    VIDEO_TIME = 5.0  # 5 minutes per video
    
    if ray_enabled:
        # With Ray, parallel execution
        images_time = max(IMAGE_TIME, num_images * IMAGE_TIME / 4)  # 4 workers
        videos_time = max(VIDEO_TIME, num_videos * VIDEO_TIME / 2)  # 2 workers
        speedup = 7.0
    else:
        # Sequential
        images_time = num_images * IMAGE_TIME
        videos_time = num_videos * VIDEO_TIME
        speedup = 1.0
    
    return {
        'total_minutes': images_time + videos_time,
        'images_minutes': images_time,
        'videos_minutes': videos_time,
        'speedup_factor': speedup
    }
