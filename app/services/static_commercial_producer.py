"""
Static Commercial Producer
Creates professional product commercials using static images with effects, voiceover, and music.
This is MORE RELIABLE than trying to animate product images with AI models.

REFACTORED: Now uses modular functions for AI generation, audio processing, and file operations.
All Replicate API calls, audio mixing, and file I/O are centralized in modules/ directory.
"""

import os
from pathlib import Path
from typing import List, Optional
import cv2
import numpy as np
from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips,
    VideoFileClip,
    TextClip
)
from moviepy.video.fx.fadein import fadein
from moviepy.video.fx.fadeout import fadeout
from moviepy.video.fx.resize import resize
import logging

# Import modular functions to eliminate code duplication
from modules.video_generation import add_cta_card
from modules.ai_generation import (
    generate_script_with_llama,
    parse_script_segments,
    generate_voiceover_audio,
    generate_background_music
)
from modules.audio_processing import prepare_background_music
from modules.file_utils import create_temp_directory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StaticCommercialProducer:
    """
    Creates high-quality commercials from static product images.
    Uses Ken Burns effects, transitions, and professional voiceover.
    """
    
    def __init__(self, replicate_token: str):
        self.replicate_token = replicate_token
        os.environ["REPLICATE_API_TOKEN"] = replicate_token
        self.output_dir = create_temp_directory(prefix="commercial_")

        # Basic templates for structured storyboard-driven compositions
        self.TEMPLATES = {
            '3_scene_basic': [
                {'name': 'hero', 'duration': 5, 'type': 'hero_image'},
                {'name': 'feature', 'duration': 5, 'type': 'detail_image'},
                {'name': 'cta', 'duration': 5, 'type': 'wide_shot'}
            ],
            '4_scene_story': [
                {'name': 'hook', 'duration': 5, 'type': 'hero_image'},
                {'name': 'solution', 'duration': 5, 'type': 'lifestyle'},
                {'name': 'detail', 'duration': 5, 'type': 'detail_image'},
                {'name': 'cta', 'duration': 5, 'type': 'wide_shot'}
            ]
        }
        
    def generate_script(self, campaign_concept: str, product_name: str, product_features: Optional[List[str]] = None) -> tuple[str, List[str]]:
        """
        Generate a concise 15-second commercial script using Llama.
        Returns (full_script, [clip1_text, clip2_text, clip3_text])
        
        REFACTORED: Now uses modules.ai_generation.generate_script_with_llama()
        """
        logger.info("🧠 Generating commercial script with Llama...")
        
        # Ensure scripts only reference explicitly-provided product features and do not invent claims
        features_text = ''
        if product_features:
            features_text = ' FEATURES: ' + ', '.join(product_features)

        prompt = (
            f"Write a professional 15-second commercial script for: {campaign_concept}\n"
            f"Product: {product_name}\n"
            f"ONLY use product information and features explicitly provided. Do not infer or invent any claims beyond these features.{features_text}\n\n"
            "Create exactly 3 short segments (5 seconds each):\n"
            "1. Hook - grab attention with the key benefit\n"
            "2. Feature - highlight what makes it special  \n"
            "3. Call-to-action - tell them what to do\n\n"
            "Each segment should be ONE sentence only (8-12 words max).\n"
            "Format as:\nSegment 1: [text]\nSegment 2: [text]\nSegment 3: [text]\n\n"
            "Be concise, punchy, and compelling."
        )

        # Use modular function for script generation
        full_script = generate_script_with_llama(prompt, max_tokens=150, temperature=0.7)
        logger.info(f"✅ Generated script:\n{full_script}")
        
        # Use modular parser with fallback
        fallback = f"{product_name} - premium quality"
        segments = parse_script_segments(full_script, expected_count=3, fallback_text=fallback)
        
        # Ensure we have exactly 3 segments with proper fallbacks
        if len(segments) != 3:
            segments = [
                f"Discover {product_name} - your perfect solution.",
                f"Premium quality that exceeds expectations.",
                f"Order now and transform your experience."
            ]
        
        return full_script, segments
    
    def generate_voiceover(self, script_segments: List[str], voice_style: str = "Professional") -> List[str]:
        """
        Generate professional voiceover for each segment using Minimax Speech.
        Returns list of audio file paths.
        
        REFACTORED: Now uses modules.ai_generation.generate_voiceover_audio()
        """
        # Use modular function for voiceover generation
        audio_files = generate_voiceover_audio(
            text_segments=script_segments,
            voice_style=voice_style,
            model="minimax/speech-02-hd",
            speed=1.0,
            output_dir=str(self.output_dir)
        )
        
        return audio_files
    
    def generate_background_music(self, duration: float, style: str = "Cinematic", custom_prompt: str = "") -> Optional[str]:
        """
        Generate background music using MusicGen.
        
        REFACTORED: Now uses modules.ai_generation.generate_background_music()
        """
        # Use modular function for music generation
        music_path = generate_background_music(
            duration=duration,
            style=style,
            custom_prompt=custom_prompt,
            model="meta/musicgen",
            output_path=str(self.output_dir / "background_music.mp3")
        )
        
        return music_path
    
    def create_commercial_from_images(
        self,
        image_paths: List[str],
        audio_paths: List[str],
        music_path: Optional[str],
        output_path: str,
        clip_duration: float = 5.0,
        template: str = '3_scene_basic',
        brand_template: Optional[dict] = None,
        allow_substitute_visuals: bool = False,
        max_retries: int = 2
    ) -> str:
        """
        Create a professional commercial video from static images.
        Applies Ken Burns effect (zoom/pan) to each image.
        """
        logger.info("🎬 Creating commercial video...")
        
        video_clips = []
        
        # Map images/audio to template scenes (pad/trim as necessary)
        scenes = self.TEMPLATES.get(template, self.TEMPLATES['3_scene_basic'])
        pairs = []
        for i, scene in enumerate(scenes):
            img = image_paths[i] if i < len(image_paths) else image_paths[0]
            aud = audio_paths[i] if i < len(audio_paths) else audio_paths[0]
            pairs.append((img, aud, scene))

        for idx, (img_path, audio_path, scene) in enumerate(pairs, 1):
            try:
                logger.info(f"  Processing clip {idx}...")
                # Validate image exists
                if not os.path.exists(img_path):
                    msg = f"Image not found for clip {idx}: {img_path}"
                    logger.error(msg)
                    if not allow_substitute_visuals:
                        raise Exception(msg)
                    else:
                        # If substitution allowed, use a placeholder image from brand assets
                        from brand_brain import BrandBrain
                        bb = BrandBrain()
                        placeholder = bb.get_placeholder_image() if hasattr(bb, 'get_placeholder_image') else None
                        if placeholder and os.path.exists(placeholder):
                            img_path = placeholder
                        else:
                            logger.warning("No placeholder available, continuing with audio-only clip")

                # Retry logic for clip generation
                attempt = 0
                while attempt < max_retries:
                    attempt += 1
                    try:
                        # Load audio to get actual duration
                        audio = AudioFileClip(audio_path)
                        actual_duration = audio.duration

                        # Create image clip with Ken Burns effect
                        img_clip = ImageClip(img_path, duration=actual_duration)

                        # Force resize to EXACTLY 1920x1080 (no aspect ratio preservation)
                        img_clip = resize(img_clip, newsize=(1920, 1080))

                        # Apply smooth center zoom effect using OpenCV (guaranteed dead center)
                        # This matches the working auto-pic-vid.py zoom logic
                        def zoom_effect(get_frame, t):
                            import cv2
                            import numpy as np

                            # Get frame at time t
                            frame = get_frame(t)

                            # Get ACTUAL frame dimensions (should be 1920x1080 after resize)
                            frame_height, frame_width = frame.shape[:2]

                            # Calculate zoom factor (1.0 to 1.15 over duration) - SLOW zoom
                            zoom_factor = 1.0 + (0.15 * (t / actual_duration))

                            # Apply zoom using OpenCV (same as working code)
                            zoomed = cv2.resize(frame, None, fx=zoom_factor, fy=zoom_factor, interpolation=cv2.INTER_LINEAR)

                            # Get zoomed dimensions
                            zoomed_height, zoomed_width = zoomed.shape[:2]

                            # Calculate center crop coordinates using ACTUAL frame dimensions
                            # This ensures perfect centering regardless of resize behavior
                            start_x = (zoomed_width - frame_width) // 2
                            start_y = (zoomed_height - frame_height) // 2

                            # Crop back to original frame size, perfectly centered
                            cropped = zoomed[start_y:start_y+frame_height, start_x:start_x+frame_width]

                            return cropped

                        img_clip = img_clip.fl(zoom_effect)

                        # Add fade in/out
                        img_clip = fadein(img_clip, 0.5)
                        img_clip = fadeout(img_clip, 0.5)

                        # Set audio
                        img_clip = img_clip.set_audio(audio)

                        video_clips.append(img_clip)
                        logger.info(f"  ✅ Clip {idx} created ({actual_duration:.1f}s)")
                        break
                    except Exception as e:
                        logger.warning(f"  ⚠️ Clip {idx} generation attempt {attempt} failed: {e}")
                        if attempt >= max_retries:
                            if not allow_substitute_visuals:
                                raise
                            else:
                                logger.warning(f"Substituting visual for clip {idx} due to repeated failures")
                                break
                        else:
                            continue
                
            except Exception as e:
                logger.error(f"  ❌ Clip {idx} failed: {e}")
        
        if not video_clips:
            raise Exception("No video clips were created")
        
        # Concatenate all clips
        logger.info("🔗 Concatenating clips...")
        final_video = concatenate_videoclips(video_clips, method="compose")
        
        # Add branded CTA end card using modular function (eliminates code duplication)
        logger.info("🎯 Adding branded CTA end card...")
        try:
            # Save temp video to add CTA
            temp_video_path = str(self.output_dir / "temp_before_cta.mp4")
            final_video.write_videofile(
                temp_video_path,
                fps=30,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=str(self.output_dir / "temp_audio_cta.m4a"),
                remove_temp=True,
                preset='medium',
                threads=1,
                logger=None
            )
            final_video.close()
            
            # Use modular add_cta_card() function
            video_with_cta = str(self.output_dir / "temp_with_cta.mp4")
            success = add_cta_card(
                video_path=temp_video_path,
                output_path=video_with_cta,
                cta_text="Shop Now!",
                card_duration=3.5
            )
            
            if success:
                logger.info(f"  ✅ CTA card added successfully!")
                # Load video with CTA for final processing
                final_video = VideoFileClip(video_with_cta)
                os.remove(temp_video_path)  # Clean up temp file
            else:
                logger.warning(f"  ⚠️ CTA card addition failed, using video without CTA")
                final_video = VideoFileClip(temp_video_path)
                
        except Exception as e:
            logger.error(f"  ❌ Failed to add CTA end card: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Continue without CTA if it fails
        
        # Add background music if available
        if music_path and os.path.exists(music_path):
            try:
                # Use modular function to prepare background music
                music_clip = prepare_background_music(
                    music_path=music_path,
                    target_duration=final_video.duration,
                    volume=0.3,  # 30% volume
                    fade_in=0.5,
                    fade_out=1.0
                )
                
                if music_clip:
                    # Mix with existing audio
                    final_audio = CompositeAudioClip([final_video.audio, music_clip])
                    final_video = final_video.set_audio(final_audio)
                    
            except Exception as e:
                logger.warning(f"⚠️ Music mixing failed: {e}")
        
        # Write final video
        logger.info(f"💾 Writing video to {output_path}...")
        final_video.write_videofile(
            output_path,
            fps=30,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile=str(self.output_dir / "temp_audio.m4a"),
            remove_temp=True,
            preset='medium',
            threads=1  # Prevent multiprocessing Python launch
        )
        # Apply brand overlay (logo, color bar, aspect ratio) if brand template provided
        try:
            if brand_template:
                from modules.video_generation import apply_brand_overlay
                tmp_branded = str(self.output_dir / "temp_branded.mp4")
                apply_brand_overlay(output_path, tmp_branded, brand_template)
                os.replace(tmp_branded, output_path)
        except Exception as e:
            logger.warning(f"⚠️ Brand overlay failed: {e}")

        logger.info("✅ Commercial complete!")
        return output_path
    
    def create_product_commercial(
        self,
        campaign_concept: str,
        product_name: str,
        mockup_image_paths: List[str],
        output_path: str,
        replicate_token: Optional[str] = None,
        voice_style: str = "Professional",
        music_style: str = "Cinematic",
        music_prompt: str = "",
        product_features: Optional[List[str]] = None,
        allow_substitute_visuals: bool = False,
        template: str = '3_scene_basic',
        brand_template: Optional[dict] = None,
        max_retries: int = 2
    ) -> str:
        """
        Main function: Create a complete commercial from product mockups.
        
        Args:
            campaign_concept: The marketing campaign description
            product_name: Name of the product
            mockup_image_paths: List of 3 product mockup images (lifestyle photos from Printify)
            output_path: Where to save the final video
            voice_style: Professional, Energetic, Luxury, or Friendly
            music_style: Genre of background music
            music_prompt: Additional music description
            
        Returns:
            Path to the final commercial video
        """
        logger.info("🎬 Starting commercial production...")
        logger.info(f"Campaign: {campaign_concept}")
        logger.info(f"Product: {product_name}")
        logger.info(f"Using {len(mockup_image_paths)} mockup images")
        
        # Ensure we have exactly 3 images (pad or trim)
        if len(mockup_image_paths) < 3:
            logger.warning(f"Only {len(mockup_image_paths)} images, duplicating first image")
            while len(mockup_image_paths) < 3:
                mockup_image_paths.append(mockup_image_paths[0])
        elif len(mockup_image_paths) > 3:
            mockup_image_paths = mockup_image_paths[:3]

        # Validate mockup files early to avoid unnecessary network calls
        if not allow_substitute_visuals:
            for p in mockup_image_paths:
                if not os.path.exists(p):
                    raise Exception(f"Image not found for commercial: {p}")
        
        # Step 1: Generate script (must not invent claims beyond product_features)
        if not product_features and not allow_substitute_visuals:
            # If we require fidelity and no features provided, abort early
            raise Exception("Product features must be provided to guarantee product fidelity")

        full_script, script_segments = self.generate_script(campaign_concept, product_name, product_features)
        
        # Step 2: Generate voiceover
        audio_paths = self.generate_voiceover(script_segments, voice_style)
        
        if len(audio_paths) != 3:
            raise Exception(f"Expected 3 audio segments, got {len(audio_paths)}")
        
        # Step 3: Generate background music
        total_duration = sum(AudioFileClip(a).duration for a in audio_paths)
        music_path = self.generate_background_music(total_duration + 2, music_style, music_prompt)
        
        # Step 4: Create final commercial
        final_path = self.create_commercial_from_images(
            mockup_image_paths,
            audio_paths,
            music_path,
            output_path,
            clip_duration=5.0,
            template=template,
            brand_template=brand_template,
            allow_substitute_visuals=allow_substitute_visuals,
            max_retries=max_retries
        )
        
        return final_path


# Convenience function
def create_product_commercial(
    campaign_concept: str,
    product_name: str,
    mockup_images: List[str],
    output_path: str,
    replicate_token: str,
    voice_style: str = "Professional"
) -> str:
    """
    Quick function to create a product commercial.
    
    Args:
        campaign_concept: Marketing campaign description
        product_name: Product name
        mockup_images: List of 3 Printify lifestyle mockup images
        output_path: Where to save video
        replicate_token: Replicate API token
        voice_style: Professional, Energetic, Luxury, or Friendly
    
    Returns:
        Path to final commercial
    """
    producer = StaticCommercialProducer(replicate_token)
    return producer.create_product_commercial(
        campaign_concept,
        product_name,
        mockup_images,
        output_path,
        voice_style
    )
