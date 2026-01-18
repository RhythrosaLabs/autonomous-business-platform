"""Intelligent promotional video assembly using Replicate multi-modal stack."""

from __future__ import annotations

import os
import re
import requests
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from app.services.api_service import ReplicateAPI

# Lazy imports for moviepy to avoid pygame/SDL initialization issues on macOS
# These will be imported when actually needed in the functions
AudioFileClip = None
CompositeAudioClip = None
VideoFileClip = None
concatenate_audioclips = None
concatenate_videoclips = None
AudioClip = None

def _ensure_moviepy():
    """Lazy import moviepy to avoid SDL thread issues on macOS."""
    global AudioFileClip, CompositeAudioClip, VideoFileClip, concatenate_audioclips, concatenate_videoclips, AudioClip
    if AudioFileClip is None:
        try:
            from moviepy.editor import (
                AudioFileClip as _AudioFileClip,
                CompositeAudioClip as _CompositeAudioClip,
                VideoFileClip as _VideoFileClip,
                concatenate_audioclips as _concatenate_audioclips,
                concatenate_videoclips as _concatenate_videoclips,
            )
            from moviepy.audio.AudioClip import AudioClip as _AudioClip
            AudioFileClip = _AudioFileClip
            CompositeAudioClip = _CompositeAudioClip
            VideoFileClip = _VideoFileClip
            concatenate_audioclips = _concatenate_audioclips
            concatenate_videoclips = _concatenate_videoclips
            AudioClip = _AudioClip
        except ImportError as exc:
            raise ImportError("moviepy is required for promo video generation") from exc

try:
    from replicate.client import Client
except ImportError as exc:  # pragma: no cover - runtime dependency check
    raise ImportError("replicate SDK is required for promo video generation") from exc


SEGMENT_DURATION_SECONDS = 5
DEFAULT_SEGMENT_COUNT = 3
BACKGROUND_MUSIC_MODEL = "meta/musicgen"


def sanitize_for_api(text: str) -> str:
    """Strip non-ASCII characters to keep Replicate models happy."""
    if not isinstance(text, str):
        text = str(text or "")
    return text.encode("ascii", "ignore").decode("ascii")


def _ensure_out_dir(out_dir: str) -> Path:
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _download_asset(url: str, target_path: Path) -> Path:
    response = requests.get(url, stream=True, timeout=180)
    response.raise_for_status()
    with open(target_path, "wb") as handle:
        for chunk in response.iter_content(1024 * 32):
            handle.write(chunk)
    return target_path


def _extract_segments(script_text: str, expected: int) -> List[str]:
    matches = re.findall(r"^(?:\s*)(\d+)[:\-)]\s*(.+)$", script_text, re.MULTILINE)
    if matches:
        ordered = sorted(((int(idx), seg.strip()) for idx, seg in matches if seg.strip()), key=lambda item: item[0])
        segments = [seg for _, seg in ordered][:expected]
        if len(segments) == expected:
            return segments
    cleaned = [part.strip() for part in re.split(r"\n\s*\n+", script_text) if part.strip()]
    return cleaned[:expected]


def _pick_voice(title: str) -> Tuple[str, Optional[str]]:
    """Select appropriate voice based on product type."""
    lowered = title.lower()
    if any(token in lowered for token in ["luxury", "elegant", "premium", "sophisticated"]):
        return "Elegant_Man", "auto"
    elif any(token in lowered for token in ["kids", "children", "toy", "fun", "playful"]):
        return "Lively_Girl", "happy"
    elif any(token in lowered for token in ["tech", "modern", "innovation", "smart"]):
        return "Determined_Man", "auto"
    elif any(token in lowered for token in ["wellness", "health", "yoga", "meditation"]):
        return "Calm_Woman", "auto"
    elif any(token in lowered for token in ["adventure", "outdoor", "sport", "active"]):
        return "Casual_Guy", "auto"
    else:
        return "Friendly_Person", "auto"


def _camera_direction_for_segment(index: int) -> str:
    directions = [
        "hero product shot with dynamic lighting",
        "lifestyle close-up showing usage",
        "bold closing shot with logo emphasis",
    ]
    return directions[index] if index < len(directions) else "smooth cinematic shot"


def _music_prompt(title: str) -> str:
    return (
        f"Upbeat, modern, and catchy background music for a commercial advertisement about '{title}'. "
        "Energetic and positive tone. Light electronic beat with uplifting melody. "
        "Professional commercial quality, seamless loop, non-distracting."
    )

def generate_product_promo_video(
    title: str,
    description: str,
    image_url: Optional[str],
    out_dir: str,
    replicate_token: Optional[str] = None,
    total_duration: int = SEGMENT_DURATION_SECONDS * DEFAULT_SEGMENT_COUNT,
    segment_count: int = DEFAULT_SEGMENT_COUNT,
) -> Optional[str]:
    """Generate a persuasive multi-segment advertisement video for the product."""
    
    # Lazy load moviepy to avoid SDL/pygame thread issues on macOS
    _ensure_moviepy()

    out_path = _ensure_out_dir(out_dir)

    token = (replicate_token or os.getenv("REPLICATE_API_TOKEN", "")).strip()
    if not token:
        return None

    replicate_api = ReplicateAPI(token)
    replicate_client = Client(api_token=token)

    segment_count = max(1, segment_count)
    segment_duration = max(3, int(total_duration / max(segment_count, 1)) or SEGMENT_DURATION_SECONDS)
    total_duration = segment_duration * segment_count

    launch_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_slug = re.sub(r"[^A-Za-z0-9_-]+", "_", title.strip().replace(" ", "_")).lower() or "product"

    script_prompt = (
        f"You are an expert video scriptwriter. Write a compelling, persuasive script for a {total_duration}-second "
        f"**advertisement** about '{title}'. The product description is: {description or title}. "
        f"The video will be {total_duration} seconds long; divide your script into {segment_count} segments of approximately {segment_duration} seconds each. "
        f"Each segment should be approximately 15-25 words, providing detailed and continuous narration to fill its {segment_duration}-second duration with spoken content, not silence. "
        f"Label each section clearly as '1:', '2:', '3:', etc. "
        f"Focus on benefits, problem-solution, and a clear call to action. Each segment should highlight a key feature, benefit, or evoke a positive emotion. "
        f"The final segment should include a strong call to action (e.g., 'Learn more', 'Shop now', 'Visit us today'). "
        f"Use a professional, enticing, and slightly urgent tone. Avoid generic statements. Make sure the {segment_count} segments tell a cohesive, progressive story."
    )

    script_text = replicate_api.generate_text(
        prompt=sanitize_for_api(script_prompt),
        max_tokens=700,
        temperature=0.6,
    )
    segments = _extract_segments(script_text, segment_count)
    if len(segments) < segment_count:
        return None

    script_file = out_path / f"{safe_slug}_script_{launch_ts}.txt"
    script_file.write_text("\n\n".join(segments), encoding="utf-8")

    voice_text = sanitize_for_api(" ".join(segments))
    voice_name, voice_emotion = _pick_voice(title)

    voice_url = replicate_api.generate_speech(
        text=voice_text,
        voice=voice_name,
        emotion=voice_emotion,
        format="mp3",
    )
    voice_path = _download_asset(voice_url, out_path / f"{safe_slug}_voiceover_{launch_ts}.mp3")

    segment_paths: List[Path] = []
    for idx, segment_text in enumerate(segments):
        visual_prompt = (
            f"Dynamic, visually appealing shots for a product/service advertisement about '{title}'. "
            f"Highlight features. Style: modern, vibrant, clean, commercial-ready. "
            f"Camera movement: engaging, product-focused. No text overlays. "
            f"Camera directive: {_camera_direction_for_segment(idx)}. "
            f"Segment focus: {segment_text}. "
            f"Professional commercial quality, well-lit, high production value."
        )

        prompt_input = sanitize_for_api(visual_prompt)
        use_image = image_url if idx == 0 and isinstance(image_url, str) and image_url.startswith("http") else None
        video_url = replicate_api.generate_video(
            prompt=prompt_input,
            image_url=use_image,
            fps=24,
            duration=segment_duration,
            resolution="720p",
        )
        segment_file = out_path / f"{safe_slug}_segment_{idx + 1}_{launch_ts}.mp4"
        segment_paths.append(_download_asset(video_url, segment_file))

    clips: List[VideoFileClip] = []
    voice_clip: Optional[AudioFileClip] = None
    music_clip: Optional[AudioFileClip] = None
    final_video: Optional[VideoFileClip] = None
    try:
        for path in segment_paths:
            clip = VideoFileClip(str(path))
            if clip.duration > segment_duration + 0.5:  # keep runtime tight if model overshoots
                clip = clip.subclip(0, segment_duration)
            clips.append(clip)
        if not clips:
            return None
        final_video = concatenate_videoclips(clips, method="compose")
        final_video = final_video.set_duration(total_duration)

        voice_clip = AudioFileClip(str(voice_path))
        if voice_clip.duration < total_duration:
            pad_needed = total_duration - voice_clip.duration
            sr = int(voice_clip.fps or 44100)
            channels = getattr(voice_clip, "nchannels", 1) or 1
            if channels > 1:
                silence_audio = AudioClip(lambda t: [0] * channels, duration=pad_needed, fps=sr)
            else:
                silence_audio = AudioClip(lambda t: 0, duration=pad_needed, fps=sr)
            voice_clip = concatenate_audioclips([voice_clip, silence_audio])
        voice_clip = voice_clip.set_duration(total_duration)

        music_path: Optional[Path] = None
        try:
            music_prompt = sanitize_for_api(_music_prompt(title))
            music_output = replicate_client.run(
                BACKGROUND_MUSIC_MODEL,
                input={
                    "prompt": music_prompt,
                    "duration": total_duration,
                },
            )
            music_url = replicate_api._first_url_from_output(music_output)
            if not music_url:
                raise ValueError("No music URL returned from Replicate")
            music_path = _download_asset(music_url, out_path / f"{safe_slug}_music_{launch_ts}.mp3")
            music_clip = AudioFileClip(str(music_path))
            if music_clip.duration < total_duration:
                loops = int(total_duration / max(music_clip.duration, 0.1)) + 1
                music_clip = concatenate_audioclips([music_clip] * loops)
            music_clip = music_clip.subclip(0, total_duration).audio_fadein(0.4).audio_fadeout(1.8).volumex(0.35)
            voice_clip = voice_clip.volumex(1.15)
            final_audio = CompositeAudioClip([music_clip, voice_clip])
        except Exception:
            final_audio = CompositeAudioClip([voice_clip])
            music_path = None

        final_audio = final_audio.set_duration(total_duration)
        final_video = final_video.set_audio(final_audio)

        output_path = out_path / f"{safe_slug}_promo_{launch_ts}.mp4"
        final_video.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            fps=24,
            temp_audiofile=str(out_path / "temp_audio.m4a"),
            remove_temp=True,
            verbose=False,
            logger=None,
        )

        return str(output_path)
    finally:
        for clip in clips:
            try:
                clip.close()
            except Exception:
                pass
        if voice_clip is not None:
            try:
                voice_clip.close()
            except Exception:
                pass
        if music_clip is not None:
            try:
                music_clip.close()
            except Exception:
                pass
        if final_video is not None:
            try:
                final_video.close()
            except Exception:
                pass
