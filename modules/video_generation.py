"""
Video Generation Module
Core video generation logic for Ken Burns, Sora, and Kling
"""

import streamlit as st
import logging
import os
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import time

logger = logging.getLogger(__name__)


class VideoGenerationError(Exception):
    """Custom exception for video generation errors."""
    pass


def generate_ken_burns_video(
    image_path: str,
    output_path: str,
    duration: int = 10,
    fps: int = 30,
    resolution: str = "1080p",
    zoom_type: str = "zoom_in"
) -> bool:
    """
    Generate Ken Burns style video from image.
    
    Args:
        image_path: Path to source image
        output_path: Path for output video
        duration: Video duration in seconds
        fps: Frames per second
        resolution: Output resolution (720p, 1080p, 4K)
        zoom_type: Type of zoom effect (zoom_in, zoom_out, pan_right, pan_left)
        
    Returns:
        bool: Success status
    """
    try:
        import cv2
        from moviepy.editor import ImageSequenceClip
        import numpy as np
        
        logger.info(f"Generating Ken Burns video: {image_path} -> {output_path}")
        
        # Read source image
        img = cv2.imread(image_path)
        if img is None:
            raise VideoGenerationError(f"Failed to read image: {image_path}")
        
        h, w = img.shape[:2]
        
        # Get resolution dimensions
        res_map = {
            "720p": (1280, 720),
            "1080p": (1920, 1080),
            "4K": (3840, 2160)
        }
        target_w, target_h = res_map.get(resolution, (1920, 1080))
        
        # Generate frames
        frames = []
        total_frames = duration * fps
        
        # Always center on image center for best results
        center_x, center_y = w // 2, h // 2
        
        for i in range(total_frames):
            progress = i / total_frames
            
            # Calculate zoom with smooth easing (ease-in-out)
            # Use cubic easing for smoother motion
            if progress < 0.5:
                eased_progress = 2 * progress * progress
            else:
                eased_progress = 1 - pow(-2 * progress + 2, 2) / 2
            
            # Calculate zoom/pan - always centered for professional look
            if zoom_type == "zoom_in":
                scale = 1.0 + eased_progress * 0.4  # Smooth zoom from 1.0x to 1.4x
            elif zoom_type == "zoom_out":
                scale = 1.4 - eased_progress * 0.4  # Smooth zoom from 1.4x to 1.0x
            elif zoom_type == "pan_right":
                scale = 1.2
                # Slight pan right while maintaining center focus
                center_x = int(w // 2 + (w * 0.15 * eased_progress))
            elif zoom_type == "pan_left":
                scale = 1.2
                # Slight pan left while maintaining center focus
                center_x = int(w // 2 - (w * 0.15 * eased_progress))
            else:
                scale = 1.0
            
            # Calculate crop box (perfectly centered)
            crop_w = int(w / scale)
            crop_h = int(h / scale)
            
            # Ensure crop stays centered and within bounds
            x1 = max(0, min(w - crop_w, center_x - crop_w // 2))
            y1 = max(0, min(h - crop_h, center_y - crop_h // 2))
            x2 = min(w, x1 + crop_w)
            y2 = min(h, y1 + crop_h)
            
            # Crop and resize
            cropped = img[y1:y2, x1:x2]
            frame = cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
            
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame_rgb)
        
        # Create video with MoviePy (threads=1 to avoid multiprocessing issues)
        clip = ImageSequenceClip(frames, fps=fps)
        clip.write_videofile(
            output_path,
            codec='libx264',
            audio=False,
            threads=1,
            logger=None
        )
        
        logger.info(f"Ken Burns video generated successfully: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Ken Burns generation failed: {e}", exc_info=True)
        raise VideoGenerationError(f"Ken Burns generation failed: {e}")


def generate_sora_video(
    prompt: str,
    output_path: str,
    duration: int = 10,
    resolution: str = "1080p"
) -> bool:
    """
    Generate video using Sora-2 via Replicate Predictions API.
    
    Args:
        prompt: Text prompt for video generation
        output_path: Path for output video
        duration: Video duration in seconds
        resolution: Output resolution
        
    Returns:
        bool: Success status
    """
    try:
        import replicate
        
        logger.info(f"Generating Sora video with prompt: {prompt[:100]}...")
        
        # Get Sora-2 model version
        model = replicate.models.get("minimax/video-01-live")
        version = model.versions.list()[0]
        
        # Create prediction
        prediction = replicate.predictions.create(
            version=version.id,
            input={
                "prompt": prompt,
                "prompt_optimizer": True
            }
        )
        
        # Wait for completion (with timeout)
        max_wait = 300  # 5 minutes
        start_time = time.time()
        
        while prediction.status not in ["succeeded", "failed", "canceled"]:
            if time.time() - start_time > max_wait:
                raise VideoGenerationError("Sora generation timeout")
            
            time.sleep(5)
            prediction.reload()
            
            # Update progress in Streamlit
            if hasattr(st, 'session_state'):
                elapsed = int(time.time() - start_time)
                st.session_state['generation_progress'] = f"⏳ Generating ({elapsed}s)..."
        
        if prediction.status != "succeeded":
            raise VideoGenerationError(f"Sora generation failed: {prediction.status}")
        
        # Download video
        video_url = prediction.output
        if not video_url:
            raise VideoGenerationError("No video URL in Sora output")
        
        import requests
        response = requests.get(video_url, timeout=60)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"Sora video downloaded: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Sora generation failed: {e}", exc_info=True)
        raise VideoGenerationError(f"Sora generation failed: {e}")


def generate_kling_video(
    prompt: str,
    output_path: str,
    duration: int = 10,
    resolution: str = "1080p"
) -> bool:
    """
    Generate video using Kling via Replicate Predictions API.
    
    Args:
        prompt: Text prompt for video generation
        output_path: Path for output video
        duration: Video duration in seconds
        resolution: Output resolution
        
    Returns:
        bool: Success status
    """
    try:
        import replicate
        
        logger.info(f"Generating Kling video with prompt: {prompt[:100]}...")
        
        # Get Kling model version
        model = replicate.models.get("fofr/kling")
        version = model.versions.list()[0]
        
        # Create prediction
        prediction = replicate.predictions.create(
            version=version.id,
            input={
                "prompt": prompt,
                "duration": str(duration)
            }
        )
        
        # Wait for completion
        max_wait = 300
        start_time = time.time()
        
        while prediction.status not in ["succeeded", "failed", "canceled"]:
            if time.time() - start_time > max_wait:
                raise VideoGenerationError("Kling generation timeout")
            
            time.sleep(5)
            prediction.reload()
            
            if hasattr(st, 'session_state'):
                elapsed = int(time.time() - start_time)
                st.session_state['generation_progress'] = f"⏳ Generating ({elapsed}s)..."
        
        if prediction.status != "succeeded":
            raise VideoGenerationError(f"Kling generation failed: {prediction.status}")
        
        # Download video
        video_url = prediction.output
        if not video_url:
            raise VideoGenerationError("No video URL in Kling output")
        
        import requests
        response = requests.get(video_url, timeout=60)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"Kling video downloaded: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Kling generation failed: {e}", exc_info=True)
        raise VideoGenerationError(f"Kling generation failed: {e}")


def add_cta_card(
    video_path: str,
    output_path: str,
    cta_text: str = "Shop Now!",
    card_duration: float = 3.5
) -> bool:
    """
    Add CTA end card to video.
    
    Args:
        video_path: Path to input video
        output_path: Path for output video with CTA
        cta_text: Call-to-action text
        card_duration: Duration of CTA card in seconds
        
    Returns:
        bool: Success status
    """
    try:
        from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ColorClip
        
        logger.info(f"Adding CTA card to video: {video_path}")
        
        # Load video
        video = VideoFileClip(video_path)
        w, h = video.size
        
        # Create CTA card background
        bg_clip = ColorClip(size=(w, h), color=(0, 0, 0)).set_duration(card_duration)
        
        # Create CTA text
        txt_clip = TextClip(
            cta_text,
            fontsize=min(w, h) // 10,
            color='white',
            font='Arial-Bold',
            method='caption',
            size=(w * 0.8, None)
        ).set_position('center').set_duration(card_duration)
        
        # Composite CTA card
        cta_card = CompositeVideoClip([bg_clip, txt_clip])
        
        # Concatenate video + CTA
        from moviepy.editor import concatenate_videoclips
        final_video = concatenate_videoclips([video, cta_card])
        
        # Write output (threads=1)
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            threads=1,
            logger=None
        )
        
        # Cleanup
        video.close()
        final_video.close()
        
        logger.info(f"CTA card added successfully: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"CTA card addition failed: {e}", exc_info=True)
        raise VideoGenerationError(f"CTA card addition failed: {e}")


    def apply_brand_overlay(video_path: str, output_path: str, brand_template: Dict) -> bool:
        """Apply brand overlay (logo and color bar) to a video.

        This places a small logo in the top-right and a color accent bar at the bottom
        using the primary brand color. It preserves the original audio/video.
        """
        try:
            from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, ColorClip
            logger.info(f"Applying brand overlay to {video_path}")

            if not os.path.exists(video_path):
                raise VideoGenerationError("Source video not found for branding")

            video = VideoFileClip(video_path)
            w, h = video.size

            overlays = [video]

            # Logo overlay (if provided)
            logo_path = None
            if brand_template:
                logo_path = brand_template.get('logo')
                primary_color = brand_template.get('colors', {}).get('primary', '#000000')
            else:
                primary_color = '#000000'

            if logo_path and os.path.exists(logo_path):
                logo = ImageClip(logo_path).set_duration(video.duration)
                # Scale logo to 8% of width
                logo = logo.resize(width=int(w * 0.08))
                logo = logo.set_pos(('right', 'top')).margin(right=20, top=20)
                overlays.append(logo)

            # Bottom color bar
            try:
                # Convert hex color to RGB tuple
                hexc = primary_color.lstrip('#')
                rgb = tuple(int(hexc[i:i+2], 16) for i in (0, 2, 4))
            except Exception:
                rgb = (0, 0, 0)

            bar_height = int(h * 0.06)
            color_bar = ColorClip(size=(w, bar_height), color=rgb).set_duration(video.duration)
            color_bar = color_bar.set_pos(('center', h - bar_height))
            overlays.append(color_bar)

            final = CompositeVideoClip(overlays)
            final.write_videofile(output_path, codec='libx264', audio_codec='aac', threads=1, logger=None)

            # Cleanup
            video.close()
            final.close()
            logger.info(f"Brand overlay applied: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Brand overlay failed: {e}", exc_info=True)
            raise VideoGenerationError(f"Brand overlay failed: {e}")


def orchestrate_video_generation(
    model_type: str,
    prompt: str,
    image_path: Optional[str],
    output_dir: str,
    quality_config: Dict,
    add_cta: bool = True,
    cta_text: str = "Shop Now!"
) -> Tuple[str, Dict]:
    """
    Orchestrate complete video generation workflow.
    
    Args:
        model_type: Video model type (ken_burns, sora, kling)
        prompt: Text prompt for generation
        image_path: Image path (for Ken Burns)
        output_dir: Output directory
        quality_config: Quality settings
        add_cta: Whether to add CTA card
        cta_text: CTA text
        
    Returns:
        tuple: (video_path, metadata)
    """
    try:
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate base filename
        timestamp = int(time.time())
        base_name = f"{model_type}_{timestamp}"
        temp_path = os.path.join(output_dir, f"{base_name}_temp.mp4")
        final_path = os.path.join(output_dir, f"{base_name}.mp4")
        
        # Generate video based on model type
        if model_type == "ken_burns":
            if not image_path:
                raise VideoGenerationError("Image path required for Ken Burns")
            
            success = generate_ken_burns_video(
                image_path=image_path,
                output_path=temp_path,
                duration=quality_config.get("duration", 10),
                fps=quality_config.get("fps", 30),
                resolution=quality_config.get("resolution", "1080p"),
                zoom_type=quality_config.get("zoom_type", "zoom_in")
            )
            
        elif model_type == "sora":
            success = generate_sora_video(
                prompt=prompt,
                output_path=temp_path,
                duration=quality_config.get("duration", 10),
                resolution=quality_config.get("resolution", "1080p")
            )
            
        elif model_type == "kling":
            success = generate_kling_video(
                prompt=prompt,
                output_path=temp_path,
                duration=quality_config.get("duration", 10),
                resolution=quality_config.get("resolution", "1080p")
            )
        else:
            raise VideoGenerationError(f"Unknown model type: {model_type}")
        
        if not success:
            raise VideoGenerationError("Video generation returned False")
        
        # Add CTA card if requested
        if add_cta:
            add_cta_card(temp_path, final_path, cta_text)
            os.remove(temp_path)  # Remove temp file
        else:
            os.rename(temp_path, final_path)
        
        # Collect metadata
        metadata = {
            "model": model_type,
            "prompt": prompt,
            "resolution": quality_config.get("resolution"),
            "fps": quality_config.get("fps"),
            "duration": quality_config.get("duration"),
            "has_cta": add_cta,
            "timestamp": timestamp,
            "file_path": final_path
        }
        
        return final_path, metadata
        
    except Exception as e:
        logger.error(f"Video orchestration failed: {e}", exc_info=True)
        raise VideoGenerationError(f"Video orchestration failed: {e}")
