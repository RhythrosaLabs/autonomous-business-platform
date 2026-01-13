"""
Audio Processing Module
Centralized audio manipulation functions for MoviePy operations.
Handles volume mixing, looping, crossfading, format conversion, and audio composition.
"""

import os
import logging
from typing import List, Optional, Tuple
from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    concatenate_audioclips
)
from pathlib import Path

logger = logging.getLogger(__name__)


def load_audio_clip(audio_path: str) -> Optional[AudioFileClip]:
    """
    Load audio file into MoviePy AudioFileClip.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        AudioFileClip or None if failed
        
    Example:
        >>> audio = load_audio_clip("voiceover.mp3")
        >>> print(f"Duration: {audio.duration}s")
    """
    try:
        if not os.path.exists(audio_path):
            logger.error(f"❌ Audio file not found: {audio_path}")
            return None
        
        audio = AudioFileClip(audio_path)
        logger.info(f"✅ Loaded audio: {audio.duration:.2f}s, {audio.fps}fps")
        return audio
        
    except Exception as e:
        logger.error(f"❌ Failed to load audio from {audio_path}: {e}")
        return None


def adjust_volume(audio: AudioFileClip, volume_factor: float = 1.0) -> AudioFileClip:
    """
    Adjust audio volume by multiplication factor.
    
    Args:
        audio: AudioFileClip to adjust
        volume_factor: Volume multiplier (0.0-2.0+, 1.0=no change)
        
    Returns:
        AudioFileClip with adjusted volume
        
    Example:
        >>> audio = load_audio_clip("music.mp3")
        >>> quiet_audio = adjust_volume(audio, 0.3)  # 30% volume
    """
    try:
        return audio.volumex(volume_factor)
    except Exception as e:
        logger.error(f"❌ Volume adjustment failed: {e}")
        return audio


def loop_audio(audio: AudioFileClip, target_duration: float) -> AudioFileClip:
    """
    Loop audio to match target duration.
    
    Args:
        audio: AudioFileClip to loop
        target_duration: Target duration in seconds
        
    Returns:
        Looped AudioFileClip
        
    Example:
        >>> music = load_audio_clip("short_music.mp3")  # 10 seconds
        >>> long_music = loop_audio(music, 60)  # Loop to 60 seconds
    """
    try:
        if audio.duration >= target_duration:
            # Just trim if already long enough
            return audio.subclip(0, target_duration)
        
        # Calculate how many loops needed
        loops_needed = int(target_duration / audio.duration) + 1
        
        # Use audio_loop (MoviePy built-in)
        looped = audio.audio_loop(duration=target_duration)
        logger.info(f"✅ Looped audio from {audio.duration:.2f}s to {target_duration:.2f}s")
        
        return looped
        
    except Exception as e:
        logger.error(f"❌ Audio looping failed: {e}")
        # Fallback: just return original
        return audio


def trim_audio(audio: AudioFileClip, duration: float) -> AudioFileClip:
    """
    Trim audio to specific duration.
    
    Args:
        audio: AudioFileClip to trim
        duration: Target duration in seconds
        
    Returns:
        Trimmed AudioFileClip
        
    Example:
        >>> long_audio = load_audio_clip("full_song.mp3")
        >>> short_audio = trim_audio(long_audio, 15)  # First 15 seconds
    """
    try:
        if audio.duration <= duration:
            return audio
        
        return audio.subclip(0, duration)
        
    except Exception as e:
        logger.error(f"❌ Audio trimming failed: {e}")
        return audio


def add_fade(
    audio: AudioFileClip,
    fade_in: float = 0.0,
    fade_out: float = 0.0
) -> AudioFileClip:
    """
    Add fade in/out effects to audio.
    
    Args:
        audio: AudioFileClip to fade
        fade_in: Fade in duration in seconds
        fade_out: Fade out duration in seconds
        
    Returns:
        AudioFileClip with fades applied
        
    Example:
        >>> audio = load_audio_clip("music.mp3")
        >>> faded = add_fade(audio, fade_in=1.0, fade_out=2.0)
    """
    try:
        if fade_in > 0:
            audio = audio.audio_fadein(fade_in)
        if fade_out > 0:
            audio = audio.audio_fadeout(fade_out)
        
        logger.info(f"✅ Added fade: in={fade_in}s, out={fade_out}s")
        return audio
        
    except Exception as e:
        logger.error(f"❌ Fade effect failed: {e}")
        return audio


def mix_audio_tracks(
    audio_clips: List[AudioFileClip],
    volumes: Optional[List[float]] = None
) -> CompositeAudioClip:
    """
    Mix multiple audio tracks into composite audio.
    
    Args:
        audio_clips: List of AudioFileClips to mix
        volumes: Optional list of volume multipliers (same length as audio_clips)
        
    Returns:
        CompositeAudioClip with all tracks mixed
        
    Example:
        >>> voice = load_audio_clip("voiceover.mp3")
        >>> music = load_audio_clip("background.mp3")
        >>> mixed = mix_audio_tracks([voice, music], volumes=[1.0, 0.3])
    """
    try:
        if not audio_clips:
            logger.warning("⚠️ No audio clips provided for mixing")
            return None
        
        # Apply volumes if provided
        if volumes:
            if len(volumes) != len(audio_clips):
                logger.warning(f"⚠️ Volume count mismatch: {len(volumes)} vs {len(audio_clips)}")
            else:
                audio_clips = [
                    clip.volumex(vol) for clip, vol in zip(audio_clips, volumes)
                ]
        
        mixed = CompositeAudioClip(audio_clips)
        logger.info(f"✅ Mixed {len(audio_clips)} audio tracks")
        
        return mixed
        
    except Exception as e:
        logger.error(f"❌ Audio mixing failed: {e}")
        return None


def concatenate_audio(
    audio_clips: List[AudioFileClip],
    crossfade: float = 0.0
) -> AudioFileClip:
    """
    Concatenate audio clips in sequence.
    
    Args:
        audio_clips: List of AudioFileClips to concatenate
        crossfade: Crossfade duration between clips in seconds
        
    Returns:
        Single AudioFileClip with all clips concatenated
        
    Example:
        >>> clip1 = load_audio_clip("part1.mp3")
        >>> clip2 = load_audio_clip("part2.mp3")
        >>> full = concatenate_audio([clip1, clip2], crossfade=0.5)
    """
    try:
        if not audio_clips:
            logger.warning("⚠️ No audio clips provided for concatenation")
            return None
        
        if crossfade > 0:
            # Apply crossfade between clips
            for i in range(len(audio_clips) - 1):
                audio_clips[i] = audio_clips[i].audio_fadeout(crossfade)
                audio_clips[i + 1] = audio_clips[i + 1].audio_fadein(crossfade)
        
        concatenated = concatenate_audioclips(audio_clips)
        logger.info(f"✅ Concatenated {len(audio_clips)} audio clips")
        
        return concatenated
        
    except Exception as e:
        logger.error(f"❌ Audio concatenation failed: {e}")
        return None


def prepare_background_music(
    music_path: str,
    target_duration: float,
    volume: float = 0.3,
    fade_in: float = 0.5,
    fade_out: float = 1.0
) -> Optional[AudioFileClip]:
    """
    Prepare background music: load, loop to duration, adjust volume, add fades.
    Common operation for video production workflows.
    
    Args:
        music_path: Path to music file
        target_duration: Target duration in seconds
        volume: Volume factor (default 0.3 = 30%)
        fade_in: Fade in duration in seconds
        fade_out: Fade out duration in seconds
        
    Returns:
        Processed AudioFileClip ready for mixing
        
    Example:
        >>> music = prepare_background_music(
        ...     "background.mp3",
        ...     target_duration=30,
        ...     volume=0.25
        ... )
    """
    try:
        logger.info(f"🎵 Preparing background music: {music_path}")
        
        # Load audio
        music = load_audio_clip(music_path)
        if not music:
            return None
        
        # Loop to duration
        music = loop_audio(music, target_duration)
        
        # Adjust volume
        music = adjust_volume(music, volume)
        
        # Add fades
        music = add_fade(music, fade_in=fade_in, fade_out=fade_out)
        
        logger.info(f"✅ Background music ready: {music.duration:.2f}s at {volume*100:.0f}% volume")
        return music
        
    except Exception as e:
        logger.error(f"❌ Background music preparation failed: {e}")
        return None


def export_audio(
    audio: AudioFileClip,
    output_path: str,
    fps: int = 44100,
    codec: str = 'libmp3lame',
    bitrate: str = '192k'
) -> bool:
    """
    Export audio clip to file.
    
    Args:
        audio: AudioFileClip to export
        output_path: Where to save audio file
        fps: Audio sample rate (default 44100)
        codec: Audio codec (default libmp3lame for MP3)
        bitrate: Audio bitrate (default 192k)
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> mixed = mix_audio_tracks([voice, music])
        >>> export_audio(mixed, "final_audio.mp3", bitrate='256k')
    """
    try:
        logger.info(f"💾 Exporting audio to {output_path}...")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        audio.write_audiofile(
            output_path,
            fps=fps,
            codec=codec,
            bitrate=bitrate,
            verbose=False,
            logger=None
        )
        
        logger.info(f"✅ Audio exported successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Audio export failed: {e}")
        return False


def get_audio_duration(audio_path: str) -> Optional[float]:
    """
    Get duration of audio file without loading full clip.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Duration in seconds, or None if failed
        
    Example:
        >>> duration = get_audio_duration("voiceover.mp3")
        >>> print(f"Audio is {duration:.1f} seconds long")
    """
    try:
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        audio.close()
        return duration
        
    except Exception as e:
        logger.error(f"❌ Failed to get audio duration: {e}")
        return None


def normalize_audio_volume(audio: AudioFileClip) -> AudioFileClip:
    """
    Normalize audio to peak at 0dB (maximum volume without clipping).
    
    Args:
        audio: AudioFileClip to normalize
        
    Returns:
        Normalized AudioFileClip
        
    Note:
        This is a simple peak normalization. For production use, consider
        using external tools like ffmpeg-normalize for better results.
        
    Example:
        >>> audio = load_audio_clip("quiet_recording.mp3")
        >>> loud_audio = normalize_audio_volume(audio)
    """
    try:
        # Get maximum amplitude
        max_amp = audio.max_volume()
        
        if max_amp > 0:
            # Normalize to peak at 1.0 (0dB)
            normalized = audio.volumex(1.0 / max_amp)
            logger.info(f"✅ Normalized audio (peak was {max_amp:.2f})")
            return normalized
        else:
            logger.warning("⚠️ Audio has no signal (max amplitude is 0)")
            return audio
            
    except Exception as e:
        logger.error(f"❌ Audio normalization failed: {e}")
        return audio
