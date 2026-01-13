"""
Video Export Utilities
Handles batch export, platform presets, error handling with retry logic
"""

import os
import time
import logging
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tempfile
from moviepy.editor import VideoFileClip
from PIL import Image

logger = logging.getLogger(__name__)


# Platform-specific video settings
PLATFORM_PRESETS = {
    "youtube": {
        "name": "YouTube",
        "aspect_ratio": "16:9",
        "resolution": "1080p",
        "fps": 30,
        "dimensions": (1920, 1080),
        "bitrate": "8000k",
        "format": "mp4"
    },
    "instagram": {
        "name": "Instagram",
        "aspect_ratio": "1:1",
        "resolution": "1080p",
        "fps": 30,
        "dimensions": (1080, 1080),
        "bitrate": "5000k",
        "format": "mp4"
    },
    "tiktok": {
        "name": "TikTok",
        "aspect_ratio": "9:16",
        "resolution": "1080p",
        "fps": 30,
        "dimensions": (1080, 1920),
        "bitrate": "6000k",
        "format": "mp4"
    },
    "twitter": {
        "name": "Twitter",
        "aspect_ratio": "16:9",
        "resolution": "720p",
        "fps": 30,
        "dimensions": (1280, 720),
        "bitrate": "5000k",
        "format": "mp4"
    }
}


def get_resolution_dimensions(resolution: str, aspect_ratio: str = "16:9") -> Tuple[int, int]:
    """
    Get video dimensions based on resolution and aspect ratio.
    
    Args:
        resolution: "720p", "1080p", or "4K"
        aspect_ratio: "16:9", "9:16", "1:1", "4:3"
        
    Returns:
        Tuple of (width, height)
    """
    if resolution == "720p":
        if aspect_ratio == "16:9":
            return (1280, 720)
        elif aspect_ratio == "9:16":
            return (720, 1280)
        elif aspect_ratio == "1:1":
            return (720, 720)
        elif aspect_ratio == "4:3":
            return (960, 720)
    elif resolution == "1080p":
        if aspect_ratio == "16:9":
            return (1920, 1080)
        elif aspect_ratio == "9:16":
            return (1080, 1920)
        elif aspect_ratio == "1:1":
            return (1080, 1080)
        elif aspect_ratio == "4:3":
            return (1440, 1080)
    elif resolution == "4K":
        if aspect_ratio == "16:9":
            return (3840, 2160)
        elif aspect_ratio == "9:16":
            return (2160, 3840)
        elif aspect_ratio == "1:1":
            return (2160, 2160)
        elif aspect_ratio == "4:3":
            return (2880, 2160)
    
    # Default fallback
    return (1920, 1080)


def get_bitrate_value(quality: str, resolution: str) -> str:
    """
    Get video bitrate based on quality setting and resolution.
    
    Args:
        quality: "Low", "Medium", "High"
        resolution: "720p", "1080p", "4K"
        
    Returns:
        Bitrate string (e.g., "5000k")
    """
    bitrate_map = {
        "720p": {"Low": "2500k", "Medium": "4000k", "High": "6000k"},
        "1080p": {"Low": "5000k", "Medium": "8000k", "High": "12000k"},
        "4K": {"Low": "15000k", "Medium": "25000k", "High": "40000k"}
    }
    
    return bitrate_map.get(resolution, {}).get(quality, "8000k")


def retry_with_exponential_backoff(
    func,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential calculation
        exceptions: Tuple of exceptions to catch
        
    Returns:
        Result of the function
    """
    delay = initial_delay
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            if attempt == max_retries:
                logger.error(f"❌ Failed after {max_retries} retries: {e}")
                raise
            
            wait_time = min(delay, max_delay)
            logger.warning(f"⚠️ Attempt {attempt + 1} failed: {e}")
            logger.info(f"⏳ Retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
            delay *= exponential_base


def convert_video_for_platform(
    input_video_path: str,
    output_path: str,
    platform: str,
    fps: Optional[int] = None,
    bitrate: Optional[str] = None
) -> str:
    """
    Convert video to platform-specific format.
    
    Args:
        input_video_path: Path to source video
        output_path: Path for output video
        platform: Platform name (youtube, instagram, tiktok, twitter)
        fps: Override FPS (uses preset if None)
        bitrate: Override bitrate (uses preset if None)
        
    Returns:
        Path to converted video
    """
    if platform not in PLATFORM_PRESETS:
        raise ValueError(f"Unknown platform: {platform}")
    
    preset = PLATFORM_PRESETS[platform]
    target_dims = preset["dimensions"]
    target_fps = fps or preset["fps"]
    target_bitrate = bitrate or preset["bitrate"]
    
    logger.info(f"🎬 Converting video for {preset['name']}")
    logger.info(f"   Resolution: {target_dims[0]}x{target_dims[1]}")
    logger.info(f"   FPS: {target_fps}")
    logger.info(f"   Bitrate: {target_bitrate}")
    
    def convert():
        clip = VideoFileClip(input_video_path)
        
        # Resize to target dimensions
        clip_resized = clip.resize(target_dims)
        
        # Write with platform-specific settings
        clip_resized.write_videofile(
            output_path,
            fps=target_fps,
            bitrate=target_bitrate,
            codec='libx264',
            audio_codec='aac',
            threads=1,
            logger=None
        )
        
        clip.close()
        clip_resized.close()
        
        return output_path
    
    # Retry with exponential backoff
    return retry_with_exponential_backoff(
        convert,
        max_retries=3,
        exceptions=(Exception,)
    )


def batch_export_all_platforms(
    source_video_path: str,
    output_dir: str,
    base_filename: str,
    platforms: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    Export video for multiple platforms at once.
    
    Args:
        source_video_path: Path to source video
        output_dir: Directory for output videos
        base_filename: Base name for output files
        platforms: List of platforms (None = all platforms)
        
    Returns:
        Dict mapping platform name to output path
    """
    if platforms is None:
        platforms = list(PLATFORM_PRESETS.keys())
    
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    for platform in platforms:
        if platform not in PLATFORM_PRESETS:
            logger.warning(f"⚠️ Skipping unknown platform: {platform}")
            continue
        
        preset = PLATFORM_PRESETS[platform]
        output_filename = f"{base_filename}_{platform}.mp4"
        output_path = str(output_dir_path / output_filename)
        
        logger.info(f"📤 Exporting for {preset['name']}...")
        
        try:
            converted_path = convert_video_for_platform(
                source_video_path,
                output_path,
                platform
            )
            results[platform] = converted_path
            logger.info(f"✅ {preset['name']}: {output_filename}")
            
        except Exception as e:
            logger.error(f"❌ Failed to export for {preset['name']}: {e}")
            results[platform] = None
    
    return results


def create_batch_export_zip(
    video_paths: Dict[str, str],
    output_zip_path: str
) -> str:
    """
    Create a ZIP file containing all exported videos.
    
    Args:
        video_paths: Dict mapping platform to video path
        output_zip_path: Path for output ZIP file
        
    Returns:
        Path to ZIP file
    """
    logger.info(f"📦 Creating ZIP archive: {output_zip_path}")
    
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for platform, video_path in video_paths.items():
            if video_path and os.path.exists(video_path):
                arcname = os.path.basename(video_path)
                zipf.write(video_path, arcname)
                logger.info(f"   ✅ Added: {arcname}")
    
    logger.info(f"✅ ZIP created: {output_zip_path}")
    return output_zip_path


def enhance_error_message(error: Exception, context: str = "") -> str:
    """
    Generate a user-friendly error message with troubleshooting tips.
    
    Args:
        error: The exception that occurred
        context: Context about what was being done
        
    Returns:
        Enhanced error message
    """
    error_msg = str(error)
    
    # Common error patterns and solutions
    if "API" in error_msg or "401" in error_msg or "403" in error_msg:
        return f"""
🔑 **API Authentication Error**
{context}

**Issue:** {error_msg}

**Solutions:**
1. Check your API keys in .env file
2. Verify keys are valid and not expired
3. Ensure you have sufficient API credits
4. Check if the service is experiencing downtime
"""
    
    elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
        return f"""
⏱️ **Timeout Error**
{context}

**Issue:** {error_msg}

**Solutions:**
1. Check your internet connection
2. Try again - the service may be slow
3. Reduce video duration or complexity
4. Use a faster model (e.g., Ken Burns instead of Sora)
"""
    
    elif "memory" in error_msg.lower() or "ram" in error_msg.lower():
        return f"""
💾 **Memory Error**
{context}

**Issue:** {error_msg}

**Solutions:**
1. Close other applications
2. Reduce video resolution (use 720p instead of 1080p)
3. Generate fewer clips at once
4. Restart the application
"""
    
    elif "file not found" in error_msg.lower() or "no such file" in error_msg.lower():
        return f"""
📁 **File Not Found Error**
{context}

**Issue:** {error_msg}

**Solutions:**
1. Ensure all required files exist
2. Check file paths are correct
3. Verify you have read/write permissions
4. Make sure previous steps completed successfully
"""
    
    else:
        return f"""
❌ **Error Occurred**
{context}

**Issue:** {error_msg}

**Try:**
1. Check the error details above
2. Retry the operation
3. Contact support if the issue persists
"""


if __name__ == "__main__":
    # Test the utilities
    print("🎬 Video Export Utilities")
    print("\n📋 Platform Presets:")
    for platform, preset in PLATFORM_PRESETS.items():
        print(f"   {preset['name']}: {preset['dimensions']} @ {preset['fps']}fps")
    
    print("\n✅ Utilities loaded successfully!")
