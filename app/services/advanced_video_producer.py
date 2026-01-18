"""
Advanced Video Production Service
Integrates sophisticated multi-agent video creation with commercial ad capabilities

REFACTORED: Now uses modular functions for AI generation, audio processing, and file operations.
Eliminates code duplication by using modules/ai_generation.py, modules/audio_processing.py, and modules/file_utils.py
"""

import tempfile
from app.services.platform_integrations import tracked_replicate_run
import os
import requests
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from moviepy.editor import (
    VideoFileClip,
    concatenate_videoclips,
    AudioFileClip,
    CompositeAudioClip,
    concatenate_audioclips,
)
import numpy as np
from moviepy.audio.AudioClip import AudioArrayClip

# Import modular functions (Phase 2 optimization)
from modules import (
    # AI Generation
    generate_script_with_llama,
    generate_voiceover_audio,
    generate_background_music,
    VOICE_MAP,
    MUSIC_PROMPTS,
    # Audio Processing  
    prepare_background_music,
    mix_audio_tracks,
    # File Utilities
    download_file,
    create_temp_directory
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ad tone to voice mapping (uses VOICE_MAP from modules)
AD_TONE_VOICE_MAP = {
    "Exciting & Energetic": "Lively_Girl",
    "Warm & Friendly": "Friendly_Person",
    "Professional & Trustworthy": "Deep_Voice_Man",
    "Fun & Playful": "Casual_Guy",
    "Luxury & Premium": "Elegant_Man",
    "Urgent & Action-Driven": "Determined_Man",
}

# Ad tone to music style mapping (maps to MUSIC_PROMPTS from modules)
AD_TONE_MUSIC_MAP = {
    "Exciting & Energetic": "Energetic",
    "Warm & Friendly": "Friendly",
    "Professional & Trustworthy": "Professional",
    "Fun & Playful": "Upbeat",
    "Luxury & Premium": "Luxury",
    "Urgent & Action-Driven": "Cinematic"
}

# Visual styles for different ad tones
VISUAL_STYLES = {
    "Exciting & Energetic": "dynamic, high-energy, vibrant colors, fast-paced, bold movements",
    "Warm & Friendly": "warm lighting, friendly atmosphere, cozy environment, soft tones",
    "Professional & Trustworthy": "clean, professional, modern setting, confident presentation",
    "Fun & Playful": "bright, colorful, animated expressions, joyful energy",
    "Luxury & Premium": "elegant, sophisticated, high-end materials, golden lighting, refined",
    "Urgent & Action-Driven": "dramatic, bold, intense, action-packed, compelling"
}

class AdvancedVideoProducer:
    """Advanced video production with multi-agent AI capabilities"""
    
    def __init__(self, replicate_token: str):
        """Initialize video producer with Replicate API token"""
        from api_service import ReplicateAPI
        self.replicate_api = ReplicateAPI(replicate_token)
        self.replicate_token = replicate_token
        self.output_dir = tempfile.mkdtemp(prefix="video_production_")
    
    def generate_product_ad_script(
        self,
        product_name: str,
        target_audience: str,
        ad_tone: str,
        key_benefits: str,
        call_to_action: str,
        duration: int = 20
    ) -> Tuple[str, List[str]]:
        """
        Generate sophisticated ad script following proven commercial structure
        Returns: (full_script_text, script_segments_list)
        """
        num_segments = duration // 5
        
        script_prompt = f"""You are an expert advertising copywriter creating a {duration}-second commercial script.

Product: {product_name}
Target Audience: {target_audience}
Tone: {ad_tone}
Key Benefits: {key_benefits}
Call to Action: {call_to_action}

Create a {num_segments}-segment script (5 seconds each) following this proven commercial structure:

Segment 1 - HOOK/PROBLEM (5s):
- Grab attention immediately with a relatable problem or exciting hook
- 6-8 words maximum - punchy and memorable
- Create emotional connection or curiosity

Segment 2 - SOLUTION (5s):
- Introduce {product_name} as the perfect solution
- 6-8 words - highlight the "aha" moment
- Show transformation or relief

Segment 3 - CALL TO ACTION (5s):
- Strong, urgent call to action with key benefit: {call_to_action}
- 6-8 words - clear, action-oriented, and compelling
- Create sense of urgency or exclusivity

Each segment must be exactly 6-8 words for perfect 5-second delivery.
Make it persuasive, memorable, and emotionally resonant.
Label each section as '1:', '2:', and '3:'.

Write ONLY the script segments - no additional commentary."""

        try:
            full_script = self.replicate_api.generate_text(
                script_prompt,
                max_tokens=400,
                temperature=0.8
            )
            
            # Extract segments
            script_segments = re.findall(r"\d+:\s*(.+)", full_script)
            
            if len(script_segments) < num_segments:
                raise ValueError(f"Failed to extract {num_segments} script segments")
            
            return full_script, script_segments[:num_segments]
            
        except Exception as e:
            logger.error(f"Script generation failed: {e}")
            raise
    
    def generate_educational_script(
        self,
        topic: str,
        duration: int = 20,
        style: str = "Educational"
    ) -> Tuple[str, List[str]]:
        """
        Generate educational video script with cohesive narrative structure
        Returns: (full_script_text, script_segments_list)
        """
        num_segments = duration // 5
        
        segment_word_ranges = {
            10: "5-8 words",
            15: "6-10 words",
            20: "6-10 words",
            30: "8-12 words"
        }
        word_range = segment_word_ranges.get(duration, "6-10 words")
        
        script_prompt = f"""You are an expert educational video scriptwriter. Create a clear, engaging {duration}-second educational video script about: {topic}

Requirements:
- {num_segments} segments of exactly 5 seconds each
- Each segment: {word_range} for perfect pacing
- Progressive narrative that builds toward compelling conclusion
- Vivid, concrete language that translates to visuals
- Include specific details, numbers, or comparisons
- Engaging, conversational tone that hooks viewers
- Avoid generic statements - be specific and memorable

Structure:
Segment 1: Attention-grabbing opening with the core question/concept
Segment 2: Key insight or surprising fact
Segment 3: Detailed explanation with visual examples
Segment 4: Powerful conclusion with takeaway message

Label each section as '1:', '2:', '3:', '4:'.
Write ONLY the script - no extra commentary."""

        try:
            full_script = self.replicate_api.generate_text(
                script_prompt,
                max_tokens=500,
                temperature=0.75
            )
            
            script_segments = re.findall(r"\d+:\s*(.+)", full_script)
            
            if len(script_segments) < num_segments:
                raise ValueError(f"Failed to extract {num_segments} script segments")
            
            return full_script, script_segments[:num_segments]
            
        except Exception as e:
            logger.error(f"Educational script generation failed: {e}")
            raise
    
    def generate_video_segments(
        self,
        script_segments: List[str],
        video_type: str = "commercial",  # 'commercial' or 'educational'
        product_name: str = "",
        ad_tone: str = "Professional & Trustworthy",
        topic: str = "",
        visual_style: str = "Cinematic",
        product_image: Optional[str] = None,  # Product mockup for image-to-video
        motion_level: int = 2,
        aspect_ratio: str = "16:9",
        kling_params: Optional[dict] = None  # Advanced Kling parameters from UI
    ) -> List[str]:
        """
        Generate video segments with sophisticated prompting for each segment
        Returns list of video file paths
        """
        logger.info(f"🎥 PHASE 1: VIDEO GENERATION - Creating {len(script_segments)} video segments (5 seconds each)")
        logger.info(f"   📹 Style: {ad_tone if video_type == 'commercial' else visual_style}")
        logger.info(f"   ⏱️ Estimated time: ~{len(script_segments) * 30} seconds")
        
        video_paths = []
        style_description = VISUAL_STYLES.get(ad_tone, "professional, appealing")
        
        for i, segment in enumerate(script_segments):
            try:
                # Rate limit: Wait 12 seconds between video requests (Replicate limit: 6/min)
                if i > 0:
                    logger.info(f"   ⏱️ Rate limit cooldown: Waiting 12 seconds before next video...")
                    import time
                    time.sleep(12)
                
                progress_pct = int((i / len(script_segments)) * 100)
                logger.info(f"🎬 Generating video segment {i+1}/{len(script_segments)} ({progress_pct}% complete)...")
                
                # Commercial ad prompting
                if video_type == "commercial":
                    # For product mockups (especially canvas/wall art), focus on environmental showcase
                    if product_image and i == 0:
                        # Hero segment with mockup - describe the environment transformation
                        video_prompt = (
                            f"Transform this canvas wall art into a beautiful home environment scene. "
                            f"Cinematic slow camera movement around the framed artwork displayed on a wall. "
                            f"{style_description} interior design. Professional real estate photography style. "
                            f"Soft natural lighting, elegant modern decor, depth of field blur. "
                            f"Show the artwork enhancing a stylish living space. 4K quality, smooth motion. "
                            f"No text overlays."
                        )
                    elif i == 0:  # Hook without mockup
                        video_prompt = (
                            f"Commercial advertisement opening: {style_description}. "
                            f"Hook scene showing problem or exciting moment for {product_name}. "
                            f"Cinematic shot, professional lighting, 4K quality. "
                            f"Visual narrative: {segment}. No text overlays."
                        )
                    elif i == 1:  # Solution - different environment
                        if product_image:
                            video_prompt = (
                                f"Canvas wall art displayed in a different beautiful setting. "
                                f"Cinematic dolly shot revealing the artwork in a cozy bedroom or office. "
                                f"{style_description} ambiance, warm lighting, lifestyle photography. "
                                f"Show how the art transforms the space. Elegant, aspirational. "
                                f"No text overlays."
                            )
                        else:
                            video_prompt = (
                                f"Commercial advertisement: {style_description}. "
                                f"Product reveal for {product_name}, showing transformation. "
                                f"Hero shot, dynamic presentation, premium quality. "
                                f"Visual narrative: {segment}. No text overlays."
                            )
                    elif i == 2:  # Benefits - close-up details
                        if product_image:
                            video_prompt = (
                                f"Close-up cinematic shot of premium canvas print details. "
                                f"Slow pan across the texture, frame quality, and vivid colors. "
                                f"Museum gallery lighting, shallow depth of field. "
                                f"{style_description} cinematography. High-end product commercial style. "
                                f"No text overlays."
                            )
                        else:
                            video_prompt = (
                                f"Commercial advertisement: {style_description}. "
                                f"Benefits demonstration for {product_name} in real-world use. "
                                f"Lifestyle shot, authentic moments, aspirational. "
                                f"Visual narrative: {segment}. No text overlays."
                            )
                    else:  # Call to Action - final wide shot
                        if product_image:
                            video_prompt = (
                                f"Wide cinematic reveal of the complete room with the canvas art as focal point. "
                                f"Slow dramatic camera pull-back showing the full interior transformation. "
                                f"{style_description} atmosphere, golden hour lighting. "
                                f"Aspirational lifestyle, premium home decor aesthetic. "
                                f"No text overlays."
                            )
                        else:
                            video_prompt = (
                                f"Commercial advertisement finale: {style_description}. "
                                f"Powerful call-to-action scene for {product_name}. "
                                f"Brand showcase, memorable ending, strong visual impact. "
                                f"Visual narrative: {segment}. No text overlays."
                            )
                
                # Educational video prompting
                else:
                    shot_types = [
                        "establishing wide shot",
                        "medium shot focusing on key elements",
                        "detailed close-up shot",
                        "dynamic concluding shot"
                    ]
                    shot_type = shot_types[min(i, len(shot_types)-1)]
                    
                    video_prompt = (
                        f"Cinematic {shot_type} for educational video: '{topic}'. "
                        f"Style: {visual_style.lower()}, professional, well-lit. "
                        f"Visual content: {segment}. "
                        f"Clean, engaging visuals. Smooth purposeful camera movement. No text overlays."
                    )
                
                # Generate video via Replicate Kling model
                logger.info(f"   🎥 Generating 5-second video clip for segment {i+1}...")
                logger.info(f"   🔍 DEBUG: product_image parameter = {product_image}")
                logger.info(f"   🔍 DEBUG: product_image exists? {os.path.exists(product_image) if product_image else 'N/A'}")
                
                # Use lifestyle mockup directly with image-to-video (mockup already shows product in environment!)
                if product_image and os.path.exists(product_image):
                    logger.info(f"   ✅ Using LIFESTYLE MOCKUP for image-to-video (segment {i+1})")
                    logger.info(f"   📸 Mockup path: {product_image}")
                    
                    try:
                        # Use replicate.run() with file object (Replicate handles upload automatically)
                        logger.info(f"   🎬 Converting lifestyle mockup to video with cinematic motion...")
                        
                        import replicate
                        
                        with open(product_image, 'rb') as mockup_file:
                            # Use advanced Kling params if provided
                            if kling_params is None:
                                kling_params = {}
                            
                            input_data = {
                                "prompt": f"Cinematic camera movement, subtle zoom, professional lighting. {video_prompt}",
                                "image": mockup_file,  # Kling uses "image" parameter with file object
                                "aspect_ratio": kling_params.get("aspect_ratio", aspect_ratio),
                                "motion_level": kling_params.get("motion_level", motion_level),
                                "cfg_scale": kling_params.get("cfg_scale", 7.5),
                                "duration": kling_params.get("duration", 5)
                            }
                            
                            # Add optional parameters
                            if kling_params.get("seed", -1) != -1:
                                input_data["seed"] = kling_params["seed"]
                            if kling_params.get("negative_prompt"):
                                input_data["negative_prompt"] = kling_params["negative_prompt"]
                            
                            logger.info(f"   🎥 Calling Kling with mockup as 'image' parameter...")
                            logger.info(f"   Advanced Kling params: cfg_scale={input_data.get('cfg_scale')}, duration={input_data.get('duration')}s")
                            output = replicate.run("kwaivgi/kling-v2.5-turbo-pro", input=input_data)
                        
                        # Extract video URL
                        if hasattr(output, 'url'):
                            video_uri = output.url()
                        elif isinstance(output, str):
                            video_uri = output
                        else:
                            raise Exception(f"Unexpected output format: {type(output)}")
                        
                        logger.info(f"   ✅ Image-to-video complete using ACTUAL product mockup")
                        
                    except Exception as e:
                        logger.error(f"   ❌ Image-to-video FAILED: {e}")
                        logger.info(f"   ⚠️ Falling back to text-to-video (WARNING: will not show actual product!)")
                        # Fall back to text-to-video if image-to-video fails
                        video_uri = self.replicate_api.generate_video(
                            prompt=video_prompt,
                            aspect_ratio=aspect_ratio
                        )
                else:
                    # No product image provided - generate from text only
                    logger.warning(f"   ⚠️ No product mockup provided for segment {i+1} - using text-to-video")
                    video_uri = self.replicate_api.generate_video(
                        prompt=video_prompt,
                        aspect_ratio=aspect_ratio
                    )
                
                logger.info(f"   ✅ Video clip {i+1} generated successfully")
                
                # generate_video() already returns the URL directly
                if not video_uri:
                    raise ValueError("No video output received from Replicate")
                
                # Download video using modular function
                logger.info(f"   ⬇️ Downloading video clip {i+1}...")
                video_path = download_file(video_uri)
                if not video_path:
                    raise ValueError(f"Failed to download video clip {i+1}")
                
                # Process clip to ensure exactly 5 seconds
                logger.info(f"   ✂️ Processing clip {i+1} to 5 seconds...")
                clip = VideoFileClip(video_path)
                if clip.duration >= 5:
                    clip = clip.subclip(0, 5)
                else:
                    # Loop if shorter than 5s
                    loops_needed = int(5 / clip.duration) + 1
                    clip = concatenate_videoclips([clip] * loops_needed).subclip(0, 5)
                
                # Save processed clip
                processed_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                clip.write_videofile(processed_path, codec="libx264", audio=False, verbose=False, logger=None)
                clip.close()
                
                # Clean up original
                try:
                    os.remove(video_path)
                except:
                    pass
                
                video_paths.append(processed_path)
                logger.info(f"Generated video segment {i+1}/{len(script_segments)}")
                
            except Exception as e:
                logger.error(f"Failed to generate segment {i+1}: {e}")
                raise
        
        return video_paths
    
    def generate_voiceover(
        self,
        script_segments: List[str],
        ad_tone: str = "Professional & Trustworthy",
        voice_name: Optional[str] = None,
        voice_params: Optional[dict] = None
    ) -> str:
        """
        Generate professional voiceover with proper tone and pacing.
        
        Args:
            script_segments: List of narration segments
            ad_tone: Overall tone/style
            voice_name: Specific voice preset (overrides default)
            voice_params: Advanced voice parameters from UI
        
        Returns:
            str: Path to audio file
        """
        try:
            logger.info("🎙️ PHASE 2: VOICEOVER GENERATION - Creating professional narration")
            full_narration = " ".join(script_segments)
            logger.info(f"   📝 Narration length: {len(full_narration)} characters")
            logger.info(f"   🎭 Tone: {ad_tone}")
            
            # Voice direction based on tone
            voice_directions = {
                "Exciting & Energetic": "enthusiastic, high-energy, passionate",
                "Warm & Friendly": "warm, conversational, genuine",
                "Professional & Trustworthy": "authoritative, confident, clear",
                "Fun & Playful": "upbeat, cheerful, engaging",
                "Luxury & Premium": "sophisticated, smooth, refined",
                "Urgent & Action-Driven": "urgent, compelling, powerful"
            }
            
            direction = voice_directions.get(ad_tone, "professional, clear")
            
            # Get appropriate voice
            if not voice_name:
                voice_name = AD_TONE_VOICE_MAP.get(ad_tone, "Deep_Voice_Man")
            
            # Use advanced voice params if provided, otherwise use defaults
            if voice_params is None:
                voice_params = {}
            
            # Generate voiceover using ReplicateAPI (handles version resolution)
            logger.info(f"   🎤 Synthesizing speech with voice: {voice_name}...")
            logger.info(f"   Advanced voice params: {voice_params}")
            
            output = self.replicate_api._run_model(
                "minimax/speech-02-hd",
                {
                    "text": f"[{direction} tone] {full_narration}",
                    "voice_id": voice_params.get("voice_id", voice_name),
                    "emotion": voice_params.get("emotion", "auto"),
                    "speed": voice_params.get("speed", 1.0),
                    "pitch": voice_params.get("pitch", 0),
                    "vol": voice_params.get("volume", 1.0),
                    "audio_sample_rate": int(voice_params.get("sample_rate", "32000")),
                    "format": voice_params.get("format", "mp3")
                }
            )
            logger.info("   ✅ Voiceover audio generated successfully")
            
            # Handle different output types
            if isinstance(output, str):
                voiceover_uri = output
            elif hasattr(output, '__iter__') and not isinstance(output, (str, bytes)):
                output_list = list(output)
                voiceover_uri = output_list[0] if output_list else None
            else:
                voiceover_uri = str(output)
            
            if not voiceover_uri:
                raise ValueError("No voiceover output received")
            
            # Download voiceover using modular function
            voice_path = download_file(voiceover_uri)
            if not voice_path:
                raise ValueError("Failed to download voiceover")
                
            logger.info("Voiceover generated successfully")
            return voice_path
            
        except Exception as e:
            logger.error(f"Voiceover generation failed: {e}")
            raise
    
    def generate_background_music(
        self,
        duration: int,
        ad_tone: str = "Professional & Trustworthy",
        product_name: str = "",
        topic: str = ""
    ) -> str:
        """
        Generate appropriate background music for video using modular function.
        Returns path to audio file.
        
        REFACTORED: Now uses generate_background_music() from modules/ai_generation.py
        Eliminates ~100 lines of duplicate Replicate API code.
        """
        # Map ad tone to music style for MUSIC_PROMPTS
        music_style = AD_TONE_MUSIC_MAP.get(ad_tone, "Professional")
        context = product_name if product_name else topic
        
        # Build custom prompt with context
        custom_prompt = f"commercial for {context}" if context else "commercial background"
        
        # Use modular function - it handles all model fallbacks and error handling
        music_path = generate_background_music(
            duration=duration,
            style=music_style,
            custom_prompt=custom_prompt
        )
        
        if not music_path:
            raise Exception("Music generation failed")
            
        return music_path
    
    def assemble_final_video(
        self,
        video_paths: List[str],
        voice_path: str,
        music_path: str,
        target_duration: float = 20.0
    ) -> str:
        """
        Assemble final video with sophisticated audio/video sync
        Uses proven multi-attempt encoding strategy
        Returns path to final video file
        """
        try:
            logger.info("🎬 PHASE 4: FINAL ASSEMBLY - Combining all elements")
            logger.info(f"   📊 Components: {len(video_paths)} video clips + voiceover + music")
            
            # Load and combine video segments
            logger.info(f"   📼 Loading {len(video_paths)} video segments...")
            clips = [VideoFileClip(path) for path in video_paths]
            logger.info("   🔗 Concatenating video clips...")
            final_video = concatenate_videoclips(clips, method="compose")
            logger.info("   ✅ Video segments combined successfully")
            
            # Adjust to target duration
            if final_video.duration > target_duration:
                final_video = final_video.subclip(0, target_duration)
            elif final_video.duration < target_duration:
                final_video = final_video.set_duration(target_duration)
            
            video_duration = final_video.duration
            logger.info(f"   ⏱️ Video duration: {video_duration:.2f}s")
            
            # Load audio clips
            logger.info("   🎙️ Loading voiceover audio...")
            voice_clip = AudioFileClip(voice_path)
            logger.info(f"      ⏱️ Voiceover duration: {voice_clip.duration:.2f}s (target: {video_duration:.2f}s)")
            logger.info("   🎵 Loading background music...")
            music_clip = AudioFileClip(music_path)
            logger.info(f"      ⏱️ Music duration: {music_clip.duration:.2f}s (will loop/trim to fit)")
            
            # Synchronize voice with video duration
            if voice_clip.duration > video_duration:
                logger.info(f"      ✂️ Trimming voiceover by {voice_clip.duration - video_duration:.2f}s")
                voice_clip = voice_clip.subclip(0, video_duration)
            elif voice_clip.duration < video_duration:
                # Pad with silence
                silence_duration = video_duration - voice_clip.duration
                logger.info(f"      🔇 Adding {silence_duration:.2f}s silence after voiceover")
                silence_array = np.zeros((int(silence_duration * 22050), 2))
                silence_clip = AudioArrayClip(silence_array, fps=22050)
                voice_clip = concatenate_audioclips([voice_clip, silence_clip])
            
            # Synchronize music with video duration
            if music_clip.duration > video_duration:
                music_clip = music_clip.subclip(0, video_duration)
            elif music_clip.duration < video_duration:
                # Loop music to fill duration
                loops_needed = int(video_duration / music_clip.duration) + 1
                music_clip = concatenate_audioclips([music_clip] * loops_needed)
                music_clip = music_clip.subclip(0, video_duration)
            
            # Create composite audio (voice at 100%, music at 25%)
            logger.info("   🎚️ Mixing audio tracks (voice + background music)...")
            voice_clip = voice_clip.subclip(0, video_duration)
            music_clip = music_clip.subclip(0, video_duration).volumex(0.25)
            
            final_audio = CompositeAudioClip([voice_clip, music_clip])
            final_audio = final_audio.subclip(0, video_duration)
            
            # Set audio to video
            logger.info("   🔊 Syncing audio with video...")
            final_video = final_video.set_audio(final_audio)
            logger.info("   ✅ Audio-video sync complete")
            
            # Try multiple encoding strategies (proven approach from multi-agent)
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            
            # Attempt 1: Standard encoding
            try:
                logger.info("   💾 Encoding final video (standard quality)...")
                final_video.write_videofile(
                    output_path,
                    codec="libx264",
                    audio_codec="aac",
                    temp_audiofile="temp-audio.m4a",
                    remove_temp=True,
                    fps=24,
                    bitrate="2000k",
                    verbose=False,
                    logger=None,
                    preset='ultrafast'
                )
                encoding_success = True
            except Exception as e:
                logger.warning(f"Standard encoding failed: {str(e)[:100]}")
                encoding_success = False
            
            # Attempt 2: Simplified encoding
            if not encoding_success:
                try:
                    logger.info("   💾 Encoding attempt 2: Simplified encoding...")
                    output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                    final_video.write_videofile(
                        output_path,
                        codec="libx264",
                        audio_codec="aac",
                        fps=24,
                        verbose=False,
                        logger=None,
                        preset='ultrafast',
                        threads=1
                    )
                    encoding_success = True
                except Exception as e:
                    logger.warning(f"Simplified encoding failed: {str(e)[:100]}")
            
            # Attempt 3: Audio-first method (most robust)
            if not encoding_success:
                logger.info("   💾 Encoding attempt 3: Audio-first method (most robust)...")
                
                # Create audio file separately
                temp_audio_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
                final_audio.write_audiofile(temp_audio_path, verbose=False, logger=None)
                
                # Create video without audio
                video_only = final_video.without_audio()
                temp_video_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                video_only.write_videofile(
                    temp_video_path,
                    codec="libx264",
                    fps=24,
                    verbose=False,
                    logger=None,
                    preset='ultrafast'
                )
                
                # Combine video and audio
                final_audio_loaded = AudioFileClip(temp_audio_path)
                temp_video_loaded = VideoFileClip(temp_video_path)
                final_audio_loaded = final_audio_loaded.subclip(0, temp_video_loaded.duration)
                final_combined = temp_video_loaded.set_audio(final_audio_loaded)
                
                output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
                final_combined.write_videofile(
                    output_path,
                    codec="libx264",
                    audio_codec="aac",
                    verbose=False,
                    logger=None,
                    preset='ultrafast'
                )
                
                # Cleanup
                video_only.close()
                temp_video_loaded.close()
                final_audio_loaded.close()
                final_combined.close()
                os.remove(temp_audio_path)
                os.remove(temp_video_path)
                
                encoding_success = True
            
            # Cleanup clips
            try:
                final_video.close()
                voice_clip.close()
                music_clip.close()
                for clip in clips:
                    clip.close()
            except:
                pass
            
            if encoding_success:
                file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                logger.info(f"✅ Video assembly complete! Final video ready.")
                logger.info(f"   📦 Output: {output_path}")
                logger.info(f"   💾 File size: {file_size_mb:.2f} MB")
                return output_path
            else:
                raise Exception("All encoding attempts failed")
                
        except Exception as e:
            logger.error(f"Video assembly failed: {e}")
            raise
    
    def create_product_ad(
        self,
        product_name: str,
        target_audience: str,
        ad_tone: str,
        key_benefits: str,
        call_to_action: str,
        duration: int = 20,
        run_folder: Optional[str] = None,
        voice_params: Optional[dict] = None
    ) -> Tuple[str, List[str], str]:
        """
        Complete end-to-end product ad creation pipeline
        Returns: (script_path, video_segment_paths, final_video_path)
        """
        if run_folder:
            os.makedirs(run_folder, exist_ok=True)
        
        # Step 1: Generate script
        logger.info("Step 1: Generating ad script")
        full_script, script_segments = self.generate_product_ad_script(
            product_name, target_audience, ad_tone, key_benefits, call_to_action, duration
        )
        
        # Save script
        if run_folder:
            script_path = os.path.join(run_folder, "ad_script.txt")
            with open(script_path, 'w') as f:
                f.write(f"Product: {product_name}\n")
                f.write(f"Target: {target_audience}\n")
                f.write(f"Tone: {ad_tone}\n\n")
                f.write("\n\n".join([f"Segment {i+1}: {seg}" for i, seg in enumerate(script_segments)]))
        else:
            script_path = tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode='w').name
            with open(script_path, 'w') as f:
                f.write(full_script)
        
        # Step 2: Generate video segments
        logger.info("Step 2: Generating video segments")
        video_paths = self.generate_video_segments(
            script_segments,
            video_type="commercial",
            product_name=product_name,
            ad_tone=ad_tone
        )
        
        # Step 3: Generate voiceover
        logger.info("Step 3: Generating voiceover")
        voice_path = self.generate_voiceover(script_segments, ad_tone, voice_params=voice_params)
        
        # Step 4: Generate background music
        logger.info("Step 4: Generating background music")
        music_path = self.generate_background_music(duration, ad_tone, product_name)
        
        # Step 5: Assemble final video
        logger.info("Step 5: Assembling final video")
        final_video_path = self.assemble_final_video(
            video_paths, voice_path, music_path, float(duration)
        )
        
        # Move to run folder if specified
        if run_folder:
            final_destination = os.path.join(run_folder, f"{product_name.replace(' ', '_')}_ad.mp4")
            os.rename(final_video_path, final_destination)
            final_video_path = final_destination
        
        return script_path, video_paths, final_video_path
