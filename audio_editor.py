"""
Audio Editor
============
Produce, generate, and modify audio files including TTS and text-to-music.
"""

import io
import os
import tempfile
import logging
from platform_integrations import tracked_replicate_run
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
import subprocess
import json

logger = logging.getLogger(__name__)

# Check for FFmpeg (used for audio processing)
def check_ffmpeg() -> bool:
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except:
        return False

FFMPEG_AVAILABLE = check_ffmpeg()


class AudioEditor:
    """Audio editor with AI-powered generation and editing."""
    
    # Voice presets for TTS
    VOICE_PRESETS = {
        'male_narrator': {'name': 'Male Narrator', 'voice_id': 'narrator_male', 'description': 'Deep, authoritative male voice'},
        'female_narrator': {'name': 'Female Narrator', 'voice_id': 'narrator_female', 'description': 'Clear, professional female voice'},
        'young_male': {'name': 'Young Male', 'voice_id': 'young_male', 'description': 'Energetic young male voice'},
        'young_female': {'name': 'Young Female', 'voice_id': 'young_female', 'description': 'Friendly young female voice'},
        'british_male': {'name': 'British Male', 'voice_id': 'british_male', 'description': 'Sophisticated British accent'},
        'british_female': {'name': 'British Female', 'voice_id': 'british_female', 'description': 'Elegant British accent'},
    }
    
    # Music style presets
    MUSIC_STYLES = {
        'upbeat_commercial': 'Upbeat, energetic background music for commercials',
        'cinematic_epic': 'Epic cinematic orchestral music',
        'chill_ambient': 'Relaxing ambient electronic music',
        'corporate': 'Professional corporate background music',
        'indie_acoustic': 'Warm acoustic indie folk style',
        'electronic_edm': 'High energy electronic dance music',
        'jazz_smooth': 'Smooth jazz with saxophone',
        'hip_hop_beat': 'Modern hip hop instrumental beat',
        'lo_fi_study': 'Lo-fi hip hop chill study music',
        'rock_energetic': 'Energetic rock instrumental',
    }
    
    def __init__(self, api_service=None, output_dir: Optional[Path] = None):
        self.api_service = api_service
        self.output_dir = output_dir or Path(tempfile.gettempdir()) / "audio_editor"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _run_ffmpeg(self, args: List[str], timeout: int = 120) -> Tuple[bool, str]:
        """Run FFmpeg command."""
        if not FFMPEG_AVAILABLE:
            raise RuntimeError("FFmpeg not installed")
        
        cmd = ['ffmpeg', '-y'] + args
        logger.info(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
        except Exception as e:
            return False, str(e)
    
    def get_audio_info(self, audio_path: str) -> Dict:
        """Get audio metadata."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            
            audio_stream = next((s for s in data.get('streams', []) if s['codec_type'] == 'audio'), {})
            
            return {
                'duration': float(data.get('format', {}).get('duration', 0)),
                'codec': audio_stream.get('codec_name', 'unknown'),
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': int(audio_stream.get('channels', 0)),
                'bitrate': int(data.get('format', {}).get('bit_rate', 0)),
            }
        except Exception as e:
            logger.error(f"Failed to get audio info: {e}")
            return {}
    
    # ===== Basic Audio Operations =====
    
    def trim(self, audio_path: str, start: float, end: float, output_path: str = None) -> str:
        """Trim audio to specified time range."""
        output_path = output_path or str(self.output_dir / f"trimmed_{datetime.now().strftime('%H%M%S')}.mp3")
        
        duration = end - start
        success, msg = self._run_ffmpeg([
            '-i', audio_path,
            '-ss', str(start),
            '-t', str(duration),
            '-c', 'copy',
            output_path
        ])
        
        if not success:
            raise RuntimeError(f"Trim failed: {msg}")
        
        return output_path
    
    def concatenate(self, audio_paths: List[str], output_path: str = None) -> str:
        """Concatenate multiple audio files."""
        output_path = output_path or str(self.output_dir / f"concat_{datetime.now().strftime('%H%M%S')}.mp3")
        
        list_file = self.output_dir / "concat_list.txt"
        with open(list_file, 'w') as f:
            for path in audio_paths:
                f.write(f"file '{path}'\n")
        
        success, msg = self._run_ffmpeg([
            '-f', 'concat',
            '-safe', '0',
            '-i', str(list_file),
            '-c', 'copy',
            output_path
        ])
        
        if not success:
            raise RuntimeError(f"Concatenation failed: {msg}")
        
        return output_path
    
    def adjust_volume(self, audio_path: str, volume: float, output_path: str = None) -> str:
        """Adjust audio volume. volume > 1 increases, < 1 decreases."""
        output_path = output_path or str(self.output_dir / f"volume_{datetime.now().strftime('%H%M%S')}.mp3")
        
        success, msg = self._run_ffmpeg([
            '-i', audio_path,
            '-filter:a', f'volume={volume}',
            output_path
        ])
        
        if not success:
            raise RuntimeError(f"Volume adjustment failed: {msg}")
        
        return output_path
    
    def change_speed(self, audio_path: str, speed: float, output_path: str = None) -> str:
        """Change audio playback speed without changing pitch."""
        output_path = output_path or str(self.output_dir / f"speed_{datetime.now().strftime('%H%M%S')}.mp3")
        
        # atempo filter supports 0.5 to 2.0
        filters = []
        tempo = speed
        while tempo > 2.0:
            filters.append('atempo=2.0')
            tempo /= 2.0
        while tempo < 0.5:
            filters.append('atempo=0.5')
            tempo *= 2.0
        filters.append(f'atempo={tempo}')
        
        success, msg = self._run_ffmpeg([
            '-i', audio_path,
            '-filter:a', ','.join(filters),
            output_path
        ])
        
        if not success:
            raise RuntimeError(f"Speed change failed: {msg}")
        
        return output_path
    
    def fade(self, audio_path: str, fade_in: float = 0, fade_out: float = 0,
            output_path: str = None) -> str:
        """Apply fade in/out effects."""
        output_path = output_path or str(self.output_dir / f"faded_{datetime.now().strftime('%H%M%S')}.mp3")
        
        info = self.get_audio_info(audio_path)
        duration = info.get('duration', 0)
        
        filters = []
        if fade_in > 0:
            filters.append(f'afade=t=in:st=0:d={fade_in}')
        if fade_out > 0:
            start = max(0, duration - fade_out)
            filters.append(f'afade=t=out:st={start}:d={fade_out}')
        
        if not filters:
            return audio_path
        
        success, msg = self._run_ffmpeg([
            '-i', audio_path,
            '-af', ','.join(filters),
            output_path
        ])
        
        if not success:
            raise RuntimeError(f"Fade effect failed: {msg}")
        
        return output_path
    
    def mix_audio(self, audio_paths: List[str], volumes: List[float] = None,
                 output_path: str = None) -> str:
        """Mix multiple audio tracks together."""
        output_path = output_path or str(self.output_dir / f"mixed_{datetime.now().strftime('%H%M%S')}.mp3")
        
        if volumes is None:
            volumes = [1.0] * len(audio_paths)
        
        # Build filter complex
        inputs = ' '.join([f'-i "{p}"' for p in audio_paths])
        vol_filters = ''.join([f'[{i}:a]volume={v}[a{i}];' for i, v in enumerate(volumes)])
        mix_inputs = ''.join([f'[a{i}]' for i in range(len(audio_paths))])
        
        filter_complex = f'{vol_filters}{mix_inputs}amix=inputs={len(audio_paths)}:duration=longest[out]'
        
        # Can't use _run_ffmpeg directly due to complex input handling
        cmd = f'ffmpeg -y {inputs} -filter_complex "{filter_complex}" -map "[out]" "{output_path}"'
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise RuntimeError(result.stderr)
        except Exception as e:
            raise RuntimeError(f"Mix failed: {e}")
        
        return output_path
    
    def convert_format(self, audio_path: str, format: str, output_path: str = None) -> str:
        """Convert audio to different format."""
        output_path = output_path or str(self.output_dir / f"converted_{datetime.now().strftime('%H%M%S')}.{format}")
        
        codecs = {
            'mp3': 'libmp3lame',
            'wav': 'pcm_s16le',
            'aac': 'aac',
            'ogg': 'libvorbis',
            'flac': 'flac'
        }
        
        codec = codecs.get(format, 'copy')
        
        success, msg = self._run_ffmpeg([
            '-i', audio_path,
            '-acodec', codec,
            output_path
        ])
        
        if not success:
            raise RuntimeError(f"Conversion failed: {msg}")
        
        return output_path
    
    # ===== AI-Powered Features =====
    
    def text_to_speech(self, text: str, voice: str = 'narrator_male',
                      output_path: str = None) -> str:
        """Generate speech from text using AI."""
        if not self.api_service:
            raise ValueError("API service required for TTS")
        
        output_path = output_path or str(self.output_dir / f"tts_{datetime.now().strftime('%H%M%S')}.mp3")
        
        try:
            import replicate
            import requests
            
            # Create a client for tracking
            api_token = os.getenv("REPLICATE_API_TOKEN", "")
            replicate_client = replicate.Client(api_token=api_token) if hasattr(replicate, 'Client') else None
            
            # Use Coqui XTTS model - reliable TTS
            if replicate_client:
                output = tracked_replicate_run(
                    replicate_client,
                    "lucataco/xtts-v2:684bc3855b37866c0c65add2ff39c78f3dea3f4ff103a436465326e0f438d58e",
                    {
                        "text": text,
                        "speaker": "https://replicate.delivery/pbxt/Jt79w0xsT64R1JsiJ0LQZI8Wd5qhzqJ1Dq1zB5fzFtbXRFn/male.wav",
                        "language": "en"
                    },
                    operation_name="Text to Speech Generation"
                )
            else:
                api_token = os.getenv("REPLICATE_API_TOKEN", "")

                replicate_client = replicate.Client(api_token=api_token) if hasattr(replicate, "Client") else None

                if replicate_client:

                    output = tracked_replicate_run(

                        replicate_client,

                        "lucataco/xtts-v2:684bc3855b37866c0c65add2ff39c78f3dea3f4ff103a436465326e0f438d55e",

                        {
                        "text": text,
                        "speaker": "https://replicate.delivery/pbxt/Jt79w0xsT64R1JsiJ0LQZI8Wd5qhzqJ1Dq1zB5fzFtbXRFn/male.wav",
                        "language": "en"
                    },

                        operation_name="API Call"

                    )

                else:

                    output = replicate.run("lucataco/xtts-v2:684bc3855b37866c0c65add2ff39c78f3dea3f4ff103a436465326e0f438d55e", input={
                        "text": text,
                        "speaker": "https://replicate.delivery/pbxt/Jt79w0xsT64R1JsiJ0LQZI8Wd5qhzqJ1Dq1zB5fzFtbXRFn/male.wav",
                        "language": "en"
                    })
            
            # Download result
            result_url = str(output) if output else None
            if result_url:
                response = requests.get(result_url, timeout=60)
                with open(output_path, 'wb') as f:
                    f.write(response.content)
            
            return output_path
            
        except Exception as e:
            logger.error(f"TTS failed: {e}")
            raise
    
    def generate_music(self, prompt: str, duration: int = 10, 
                      style: str = None, output_path: str = None) -> str:
        """Generate music from text prompt using AI."""
        if not self.api_service:
            raise ValueError("API service required for music generation")
        
        output_path = output_path or str(self.output_dir / f"music_{datetime.now().strftime('%H%M%S')}.mp3")
        
        # Enhance prompt with style
        if style and style in self.MUSIC_STYLES:
            prompt = f"{prompt}. Style: {self.MUSIC_STYLES[style]}"
        
        try:
            import replicate
            import requests
            
            api_token = os.getenv("REPLICATE_API_TOKEN", "")

            
            replicate_client = replicate.Client(api_token=api_token) if hasattr(replicate, "Client") else None

            
            if replicate_client:

            
                output = tracked_replicate_run(

            
                    replicate_client,

            
                    "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb",

            
                    {
                    "prompt": prompt,
                    "duration": duration,
                    "model_version": "stereo-melody-large"
                },

            
                    operation_name="API Call"

            
                )

            
            else:

            
                output = replicate.run("meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb", input={
                    "prompt": prompt,
                    "duration": duration,
                    "model_version": "stereo-melody-large"
                })
            
            # Download result
            response = requests.get(output, timeout=120)
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Music generation failed: {e}")
            raise
    
    def generate_sound_effect(self, description: str, output_path: str = None) -> str:
        """Generate sound effect from description."""
        if not self.api_service:
            raise ValueError("API service required for sound generation")
        
        output_path = output_path or str(self.output_dir / f"sfx_{datetime.now().strftime('%H%M%S')}.mp3")
        
        try:
            import replicate
            import requests
            
            output = replicate.run(
                "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb",
                input={
                    "prompt": f"sound effect: {description}",
                    "duration": 5,
                    "model_version": "stereo-melody-large"
                }
            )
            
            response = requests.get(output, timeout=60)
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Sound effect generation failed: {e}")
            raise


def render_audio_editor_ui():
    """Render audio editor UI in Streamlit."""
    import streamlit as st
    
    st.markdown("### 🎵 Audio Editor")
    
    if not FFMPEG_AVAILABLE:
        st.warning("⚠️ FFmpeg not installed. Some features may be limited.")
    
    # Get API service
    from platform_helpers import _get_replicate_token
    token = _get_replicate_token()
    api = None
    if token:
        from api_service import ReplicateAPI
        api = ReplicateAPI(api_token=token)
    
    editor = AudioEditor(api_service=api)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Edit Audio", "Text to Speech", "Generate Music", "Sound Effects"])
    
    with tab1:
        st.markdown("#### Edit Audio File")
        
        uploaded = st.file_uploader("Upload Audio", type=['mp3', 'wav', 'aac', 'ogg', 'flac'])
        
        if uploaded:
            temp_path = str(editor.output_dir / uploaded.name)
            with open(temp_path, 'wb') as f:
                f.write(uploaded.read())
            
            # Show audio info
            info = editor.get_audio_info(temp_path)
            if info:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Duration", f"{info.get('duration', 0):.1f}s")
                with col2:
                    st.metric("Sample Rate", f"{info.get('sample_rate', 0)} Hz")
                with col3:
                    st.metric("Channels", info.get('channels', 0))
            
            st.audio(temp_path)
            
            # Edit options
            action = st.selectbox("Action", [
                "Trim", "Adjust Volume", "Change Speed", "Fade Effects", "Convert Format"
            ])
            
            if action == "Trim":
                col1, col2 = st.columns(2)
                with col1:
                    start = st.number_input("Start (seconds)", 0.0, info.get('duration', 60.0), 0.0)
                with col2:
                    end = st.number_input("End (seconds)", 0.0, info.get('duration', 60.0), info.get('duration', 10.0))
                
                if st.button("Trim Audio", type="primary"):
                    with st.spinner("Trimming..."):
                        try:
                            output = editor.trim(temp_path, start, end)
                            st.success("Audio trimmed!")
                            st.audio(output)
                            with open(output, 'rb') as f:
                                st.download_button("Download", f.read(), "trimmed.mp3")
                        except Exception as e:
                            st.error(f"Failed: {e}")
            
            elif action == "Adjust Volume":
                volume = st.slider("Volume", 0.1, 3.0, 1.0, 0.1)
                
                if st.button("Apply Volume", type="primary"):
                    with st.spinner("Adjusting..."):
                        try:
                            output = editor.adjust_volume(temp_path, volume)
                            st.success("Volume adjusted!")
                            st.audio(output)
                            with open(output, 'rb') as f:
                                st.download_button("Download", f.read(), "volume_adjusted.mp3")
                        except Exception as e:
                            st.error(f"Failed: {e}")
            
            elif action == "Change Speed":
                speed = st.slider("Speed", 0.5, 2.0, 1.0, 0.1)
                
                if st.button("Apply Speed", type="primary"):
                    with st.spinner("Processing..."):
                        try:
                            output = editor.change_speed(temp_path, speed)
                            st.success("Speed changed!")
                            st.audio(output)
                            with open(output, 'rb') as f:
                                st.download_button("Download", f.read(), "speed_changed.mp3")
                        except Exception as e:
                            st.error(f"Failed: {e}")
            
            elif action == "Fade Effects":
                col1, col2 = st.columns(2)
                with col1:
                    fade_in = st.number_input("Fade In (seconds)", 0.0, 10.0, 0.0)
                with col2:
                    fade_out = st.number_input("Fade Out (seconds)", 0.0, 10.0, 0.0)
                
                if st.button("Apply Fade", type="primary"):
                    with st.spinner("Applying fade..."):
                        try:
                            output = editor.fade(temp_path, fade_in, fade_out)
                            st.success("Fade applied!")
                            st.audio(output)
                            with open(output, 'rb') as f:
                                st.download_button("Download", f.read(), "faded.mp3")
                        except Exception as e:
                            st.error(f"Failed: {e}")
            
            elif action == "Convert Format":
                format = st.selectbox("Output Format", ["mp3", "wav", "aac", "ogg", "flac"])
                
                if st.button("Convert", type="primary"):
                    with st.spinner("Converting..."):
                        try:
                            output = editor.convert_format(temp_path, format)
                            st.success(f"Converted to {format}!")
                            st.audio(output)
                            with open(output, 'rb') as f:
                                st.download_button("Download", f.read(), f"converted.{format}")
                        except Exception as e:
                            st.error(f"Failed: {e}")
    
    with tab2:
        st.markdown("#### Text to Speech")
        
        text = st.text_area("Enter text to convert to speech", height=150, key="tts_text")
        
        voice = st.selectbox(
            "Voice",
            list(editor.VOICE_PRESETS.keys()),
            format_func=lambda x: f"{editor.VOICE_PRESETS[x]['name']} - {editor.VOICE_PRESETS[x]['description']}"
        )
        
        if st.button("🎤 Generate Speech", type="primary", use_container_width=True, key="gen_speech_btn"):
            if not api:
                st.error("Add Replicate API key in Settings for TTS")
            elif not text:
                st.warning("Please enter some text to convert")
            else:
                with st.spinner("Generating speech..."):
                    try:
                        output = editor.text_to_speech(text, voice)
                        st.success("Speech generated!")
                        st.audio(output)
                        with open(output, 'rb') as f:
                            st.download_button("Download", f.read(), "speech.mp3")
                    except Exception as e:
                        st.error(f"Failed: {e}")
    
    with tab3:
        st.markdown("#### Generate Music")
        
        prompt = st.text_area(
            "Describe the music you want",
            placeholder="Upbeat electronic music with a catchy melody...",
            height=100,
            key="music_prompt"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            style = st.selectbox("Style Preset", ["custom"] + list(editor.MUSIC_STYLES.keys()), key="music_style")
        with col2:
            duration = st.slider("Duration (seconds)", 5, 30, 10, key="music_duration")
        
        if style != "custom":
            st.caption(f"Style: {editor.MUSIC_STYLES.get(style, '')}")
        
        if st.button("🎵 Generate Music", type="primary", use_container_width=True, key="gen_music_btn"):
            if not api:
                st.error("Add Replicate API key in Settings for music generation")
            elif not prompt:
                st.warning("Please describe the music you want")
            else:
                with st.spinner("Generating music... This may take a minute"):
                    try:
                        style_to_use = style if style != "custom" else None
                        output = editor.generate_music(prompt, duration, style_to_use)
                        st.success("Music generated!")
                        st.audio(output)
                        with open(output, 'rb') as f:
                            st.download_button("Download", f.read(), "generated_music.mp3")
                    except Exception as e:
                        st.error(f"Failed: {e}")
    
    with tab4:
        st.markdown("#### Generate Sound Effects")
        
        description = st.text_input(
            "Describe the sound effect",
            placeholder="Thunder rumbling in the distance...",
            key="sfx_description"
        )
        
        # Quick presets
        st.markdown("**Quick Presets:**")
        presets = [
            "Door opening and closing",
            "Footsteps on gravel",
            "Rain falling",
            "Car engine starting",
            "Glass breaking",
            "Applause"
        ]
        
        cols = st.columns(3)
        selected_preset = None
        for i, preset in enumerate(presets):
            with cols[i % 3]:
                if st.button(preset, key=f"sfx_preset_{i}"):
                    selected_preset = preset
        
        final_description = selected_preset or description
        
        if st.button("🔊 Generate Sound Effect", type="primary", use_container_width=True, key="gen_sfx_btn"):
            if not api:
                st.error("Add Replicate API key in Settings for sound generation")
            elif not final_description:
                st.warning("Please describe the sound effect or select a preset")
            else:
                with st.spinner("Generating sound effect..."):
                    try:
                        output = editor.generate_sound_effect(final_description)
                        st.success("Sound effect generated!")
                        st.audio(output)
                        with open(output, 'rb') as f:
                            st.download_button("Download", f.read(), "sound_effect.mp3")
                    except Exception as e:
                        st.error(f"Failed: {e}")
