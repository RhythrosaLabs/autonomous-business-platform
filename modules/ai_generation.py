"""
AI Generation Module
Centralized Replicate API functions for text, speech, music, and video generation.
Eliminates code duplication across static_commercial_producer.py, advanced_video_producer.py,
product_promo_video.py, and autonomous_business_platform.py.
"""

import os
import logging
import replicate
import requests
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Voice mapping for Minimax Speech
VOICE_MAP = {
    "Professional": "Calm_Woman",
    "Energetic": "Lively_Girl", 
    "Luxury": "Elegant_Man",
    "Friendly": "Friendly_Person",
    # Additional voices
    "Female_Calm": "Calm_Woman",
    "Female_Lively": "Lively_Girl",
    "Male_Elegant": "Elegant_Man",
    "Neutral": "Friendly_Person"
}

# Music style prompts for MusicGen
MUSIC_PROMPTS = {
    "Cinematic": "cinematic epic background music, dramatic, inspiring",
    "Electronic": "electronic background music, modern, dynamic",
    "Upbeat": "upbeat energetic background music, happy, positive",
    "Ambient": "ambient atmospheric background music, calm, soothing",
    "Corporate": "corporate inspiring background music, uplifting, confident",
    "Hip Hop": "hip hop beat background music, urban, cool",
    "Jazz": "smooth jazz background music, sophisticated, elegant",
    # Legacy compatibility
    "Professional": "corporate inspiring background music, uplifting, confident",
    "Energetic": "upbeat electronic background music, energetic, exciting",
    "Luxury": "elegant orchestral background music, sophisticated, premium",
    "Friendly": "warm acoustic background music, friendly, inviting"
}


def generate_script_with_llama(
    prompt: str,
    model: str = "meta/meta-llama-3-70b-instruct",
    max_tokens: int = 150,
    temperature: float = 0.7,
    system_prompt: Optional[str] = None
) -> str:
    """
    Generate text script using Llama models.
    
    Args:
        prompt: The generation prompt
        model: Llama model ID (default: meta-llama-3-70b-instruct)
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.0-1.0)
        system_prompt: Optional system prompt for context
        
    Returns:
        Generated text as string
        
    Example:
        >>> script = generate_script_with_llama(
        ...     "Write a 15-second product commercial script",
        ...     temperature=0.8
        ... )
    """
    try:
        logger.info(f"🧠 Generating script with {model}...")
        
        input_params = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        if system_prompt:
            input_params["system_prompt"] = system_prompt
        
        output = replicate.run(model, input=input_params)
        
        full_text = "".join(output).strip()
        logger.info(f"✅ Generated {len(full_text)} characters")
        
        return full_text
        
    except Exception as e:
        logger.error(f"❌ Script generation failed: {e}")
        raise


def parse_script_segments(
    script_text: str,
    expected_count: int = 3,
    fallback_text: str = "Generated content"
) -> List[str]:
    """
    Parse numbered segments from generated script.
    
    Args:
        script_text: Generated script with "Segment 1:", "1:", or similar markers
        expected_count: Number of segments expected
        fallback_text: Text to use if parsing fails
        
    Returns:
        List of segment texts
        
    Example:
        >>> script = "Segment 1: Hook\\nSegment 2: Feature\\nSegment 3: CTA"
        >>> segments = parse_script_segments(script, 3)
        ['Hook', 'Feature', 'CTA']
    """
    segments = []
    
    # Try different parsing patterns
    for line in script_text.split('\n'):
        # Pattern: "Segment X:" or "X:"
        if any(marker in line for marker in ['Segment', '1:', '2:', '3:', '4:', '5:']):
            if ':' in line:
                text = line.split(':', 1)[1].strip()
                if text:
                    segments.append(text)
    
    # Fallback if parsing failed
    if len(segments) != expected_count:
        logger.warning(f"Script parsing found {len(segments)} segments, expected {expected_count}")
        segments = [f"{fallback_text} {i+1}" for i in range(expected_count)]
    
    return segments[:expected_count]


def generate_voiceover_audio(
    text_segments: List[str],
    voice_style: str = "Professional",
    model: str = "minimax/speech-02-hd",
    speed: float = 1.0,
    output_dir: Optional[str] = None
) -> List[str]:
    """
    Generate professional voiceover audio for text segments using Minimax Speech.
    
    Args:
        text_segments: List of text strings to convert to speech
        voice_style: Voice style from VOICE_MAP
        model: Speech model ID (speech-02-hd or speech-02-turbo)
        speed: Speech speed multiplier (0.5-2.0)
        output_dir: Directory to save audio files (uses temp if None)
        
    Returns:
        List of paths to generated audio files
        
    Example:
        >>> segments = ["Hook text", "Feature text", "CTA text"]
        >>> audio_paths = generate_voiceover_audio(segments, "Energetic")
        ['voice_1.mp3', 'voice_2.mp3', 'voice_3.mp3']
    """
    try:
        logger.info(f"🎙️ Generating voiceover with {model}...")
        
        voice_name = VOICE_MAP.get(voice_style, "Calm_Woman")
        audio_files = []
        
        # Use output_dir or create temp directory
        import tempfile
        from pathlib import Path
        if output_dir:
            save_dir = Path(output_dir)
        else:
            save_dir = Path(tempfile.mkdtemp(prefix="voiceover_"))
        save_dir.mkdir(parents=True, exist_ok=True)
        
        for idx, text in enumerate(text_segments, 1):
            try:
                logger.info(f"  Segment {idx}: '{text[:50]}...'")
                
                output = replicate.run(
                    model,
                    input={
                        "text": text,
                        "voice_id": voice_name,
                        "speed": speed
                    }
                )
                
                # Download audio
                if output:
                    audio_url = output if isinstance(output, str) else str(output)
                    response = requests.get(audio_url, timeout=60)
                    
                    if response.status_code == 200:
                        audio_path = save_dir / f"voice_segment_{idx}.mp3"
                        with open(audio_path, 'wb') as f:
                            f.write(response.content)
                        audio_files.append(str(audio_path))
                        logger.info(f"  ✅ Segment {idx} saved to {audio_path}")
                    else:
                        logger.error(f"  ❌ Failed to download segment {idx} (HTTP {response.status_code})")
                        
            except Exception as e:
                logger.error(f"  ❌ Segment {idx} failed: {e}")
        
        logger.info(f"✅ Generated {len(audio_files)}/{len(text_segments)} audio files")
        return audio_files
        
    except Exception as e:
        logger.error(f"❌ Voiceover generation failed: {e}")
        raise


def generate_background_music(
    duration: float,
    style: str = "Cinematic",
    custom_prompt: str = "",
    model: str = "meta/musicgen",
    output_path: Optional[str] = None
) -> Optional[str]:
    """
    Generate background music using MusicGen.
    
    Args:
        duration: Duration in seconds (max 30 for musicgen)
        style: Music style from MUSIC_PROMPTS
        custom_prompt: Additional prompt text to append
        model: Music generation model ID
        output_path: Where to save the music file (uses temp if None)
        
    Returns:
        Path to generated music file, or None if failed
        
    Example:
        >>> music = generate_background_music(
        ...     duration=15,
        ...     style="Corporate",
        ...     custom_prompt="uplifting, confident"
        ... )
    """
    try:
        logger.info(f"🎵 Generating {duration}s background music ({style})...")
        
        # Build prompt
        base_prompt = MUSIC_PROMPTS.get(style, MUSIC_PROMPTS["Cinematic"])
        prompt = f"{base_prompt}, {custom_prompt}" if custom_prompt else base_prompt
        
        # Generate music
        output = replicate.run(
            model,
            input={
                "prompt": prompt,
                "duration": min(int(duration), 30),  # MusicGen max is 30s
                "model_version": "stereo-melody-large"
            }
        )
        
        if not output:
            logger.warning("⚠️ No output from music generation")
            return None
        
        # Download music
        music_url = output if isinstance(output, str) else str(output)
        response = requests.get(music_url, timeout=120)
        
        if response.status_code != 200:
            logger.error(f"❌ Failed to download music (HTTP {response.status_code})")
            return None
        
        # Save to file
        if output_path:
            save_path = output_path
        else:
            import tempfile
            from pathlib import Path
            temp_dir = Path(tempfile.mkdtemp(prefix="music_"))
            save_path = str(temp_dir / "background_music.mp3")
        
        with open(save_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"✅ Music saved to {save_path}")
        return save_path
        
    except Exception as e:
        logger.error(f"❌ Music generation failed: {e}")
        return None


def generate_video_with_model(
    prompt: str,
    model: str = "minimax/video-01",
    duration: Optional[int] = None,
    output_path: Optional[str] = None,
    **kwargs
) -> Optional[str]:
    """
    Generate video using Replicate video models (Minimax, Luma, etc).
    
    Args:
        prompt: Video generation prompt
        model: Video model ID
        duration: Video duration (model-dependent)
        output_path: Where to save video (uses temp if None)
        **kwargs: Additional model-specific parameters
        
    Returns:
        Path to generated video file, or None if failed
        
    Example:
        >>> video = generate_video_with_model(
        ...     "Product showcase with smooth camera movement",
        ...     model="minimax/video-01",
        ...     duration=5
        ... )
    """
    try:
        logger.info(f"🎬 Generating video with {model}...")
        
        input_params = {"prompt": prompt}
        if duration:
            input_params["duration"] = duration
        input_params.update(kwargs)
        
        output = replicate.run(model, input=input_params)
        
        if not output:
            logger.warning("⚠️ No output from video generation")
            return None
        
        # Extract video URL
        video_url = None
        if isinstance(output, str) and output.startswith('http'):
            video_url = output
        elif isinstance(output, dict) and 'video' in output:
            video_url = output['video']
        elif hasattr(output, '__iter__'):
            for item in output:
                if isinstance(item, str) and item.startswith('http'):
                    video_url = item
                    break
        
        if not video_url:
            logger.error("❌ Could not extract video URL from output")
            return None
        
        # Download video
        logger.info(f"⬇️ Downloading video from {video_url[:50]}...")
        response = requests.get(video_url, timeout=300)
        
        if response.status_code != 200:
            logger.error(f"❌ Failed to download video (HTTP {response.status_code})")
            return None
        
        # Save to file
        if output_path:
            save_path = output_path
        else:
            import tempfile
            from pathlib import Path
            temp_dir = Path(tempfile.mkdtemp(prefix="video_"))
            save_path = str(temp_dir / "generated_video.mp4")
        
        with open(save_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"✅ Video saved to {save_path}")
        return save_path
        
    except Exception as e:
        logger.error(f"❌ Video generation failed: {e}")
        return None


def generate_image_with_flux(
    prompt: str,
    model: str = "black-forest-labs/flux-schnell",
    width: int = 1024,
    height: int = 1024,
    output_path: Optional[str] = None,
    **kwargs
) -> Optional[str]:
    """
    Generate image using Flux models.
    
    Args:
        prompt: Image generation prompt
        model: Flux model ID (flux-schnell or flux-dev)
        width: Image width
        height: Image height
        output_path: Where to save image (uses temp if None)
        **kwargs: Additional model-specific parameters
        
    Returns:
        Path to generated image file, or None if failed
        
    Example:
        >>> image = generate_image_with_flux(
        ...     "Professional product photo on white background",
        ...     width=1920,
        ...     height=1080
        ... )
    """
    try:
        logger.info(f"🖼️ Generating image with {model}...")
        
        input_params = {
            "prompt": prompt,
            "width": width,
            "height": height
        }
        input_params.update(kwargs)
        
        output = replicate.run(model, input=input_params)
        
        if not output:
            logger.warning("⚠️ No output from image generation")
            return None
        
        # Extract image URL
        image_url = None
        if isinstance(output, str) and output.startswith('http'):
            image_url = output
        elif hasattr(output, '__iter__'):
            for item in output:
                if isinstance(item, str) and item.startswith('http'):
                    image_url = item
                    break
        
        if not image_url:
            logger.error("❌ Could not extract image URL from output")
            return None
        
        # Download image
        response = requests.get(image_url, timeout=60)
        
        if response.status_code != 200:
            logger.error(f"❌ Failed to download image (HTTP {response.status_code})")
            return None
        
        # Save to file
        if output_path:
            save_path = output_path
        else:
            import tempfile
            from pathlib import Path
            temp_dir = Path(tempfile.mkdtemp(prefix="image_"))
            save_path = str(temp_dir / "generated_image.png")
        
        with open(save_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"✅ Image saved to {save_path}")
        return save_path
        
    except Exception as e:
        logger.error(f"❌ Image generation failed: {e}")
        return None
