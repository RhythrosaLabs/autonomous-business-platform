"""
Enhanced Video Editor
=====================
Advanced video editing tools with AI-powered features.
"""

import io
import os
import tempfile
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
import subprocess
import json

logger = logging.getLogger(__name__)

# Check for FFmpeg
def check_ffmpeg() -> bool:
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except:
        return False

FFMPEG_AVAILABLE = check_ffmpeg()


class VideoEditor:
    """Enhanced video editor with AI integration."""
    
    # Transition types
    TRANSITIONS = {
        'fade': 'Fade in/out',
        'dissolve': 'Cross dissolve',
        'wipe': 'Wipe transition',
        'zoom': 'Zoom transition',
        'slide': 'Slide transition'
    }
    
    # Video effects
    EFFECTS = {
        'slow_motion': {'name': 'Slow Motion', 'description': 'Slow down footage'},
        'fast_motion': {'name': 'Fast Motion', 'description': 'Speed up footage'},
        'reverse': {'name': 'Reverse', 'description': 'Play backwards'},
        'loop': {'name': 'Loop', 'description': 'Create looping video'},
        'stabilize': {'name': 'Stabilize', 'description': 'Reduce camera shake'},
    }
    
    # Preset aspect ratios
    ASPECT_RATIOS = {
        '16:9': (1920, 1080),
        '9:16': (1080, 1920),
        '1:1': (1080, 1080),
        '4:5': (1080, 1350),
        '4:3': (1440, 1080),
        '21:9': (2560, 1080)
    }
    
    def __init__(self, api_service=None, output_dir: Optional[Path] = None):
        self.api_service = api_service
        self.output_dir = output_dir or Path(tempfile.gettempdir()) / "video_editor"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _run_ffmpeg(self, args: List[str], timeout: int = 300) -> Tuple[bool, str]:
        """Run FFmpeg command."""
        if not FFMPEG_AVAILABLE:
            raise RuntimeError("FFmpeg not installed")
        
        cmd = ['ffmpeg', '-y'] + args
        logger.info(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)
    
    def get_video_info(self, video_path: str) -> Dict:
        """Get video metadata using FFprobe."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            data = json.loads(result.stdout)
            
            video_stream = next((s for s in data.get('streams', []) if s['codec_type'] == 'video'), {})
            audio_stream = next((s for s in data.get('streams', []) if s['codec_type'] == 'audio'), {})
            
            return {
                'duration': float(data.get('format', {}).get('duration', 0)),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'fps': eval(video_stream.get('r_frame_rate', '30/1')),
                'codec': video_stream.get('codec_name', 'unknown'),
                'has_audio': bool(audio_stream),
                'audio_codec': audio_stream.get('codec_name', ''),
                'bitrate': int(data.get('format', {}).get('bit_rate', 0)),
                'size': int(data.get('format', {}).get('size', 0))
            }
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return {}
    
    # ===== Basic Operations =====
    
    def trim(self, video_path: str, start: float, end: float, output_path: str = None) -> str:
        """Trim video to specified time range."""
        output_path = output_path or str(self.output_dir / f"trimmed_{datetime.now().strftime('%H%M%S')}.mp4")
        
        duration = end - start
        success, msg = self._run_ffmpeg([
            '-i', video_path,
            '-ss', str(start),
            '-t', str(duration),
            '-c', 'copy',
            output_path
        ])
        
        if not success:
            raise RuntimeError(f"Trim failed: {msg}")
        
        return output_path
    
    def concatenate(self, video_paths: List[str], output_path: str = None) -> str:
        """Concatenate multiple videos."""
        output_path = output_path or str(self.output_dir / f"concat_{datetime.now().strftime('%H%M%S')}.mp4")
        
        # Create file list
        list_file = self.output_dir / "concat_list.txt"
        with open(list_file, 'w') as f:
            for path in video_paths:
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
    
    def resize(self, video_path: str, width: int, height: int, output_path: str = None) -> str:
        """Resize video to specified dimensions."""
        output_path = output_path or str(self.output_dir / f"resized_{datetime.now().strftime('%H%M%S')}.mp4")
        
        success, msg = self._run_ffmpeg([
            '-i', video_path,
            '-vf', f'scale={width}:{height}',
            '-c:a', 'copy',
            output_path
        ])
        
        if not success:
            raise RuntimeError(f"Resize failed: {msg}")
        
        return output_path
    
    def change_speed(self, video_path: str, speed: float, output_path: str = None) -> str:
        """Change video playback speed."""
        output_path = output_path or str(self.output_dir / f"speed_{datetime.now().strftime('%H%M%S')}.mp4")
        
        # PTS adjustment: lower = faster
        pts = 1.0 / speed
        atempo = speed
        
        # atempo only supports 0.5 to 2.0, chain for larger changes
        atempo_filters = []
        while atempo > 2.0:
            atempo_filters.append('atempo=2.0')
            atempo /= 2.0
        while atempo < 0.5:
            atempo_filters.append('atempo=0.5')
            atempo *= 2.0
        atempo_filters.append(f'atempo={atempo}')
        
        video_filter = f'setpts={pts}*PTS'
        audio_filter = ','.join(atempo_filters)
        
        success, msg = self._run_ffmpeg([
            '-i', video_path,
            '-filter_complex', f'[0:v]{video_filter}[v];[0:a]{audio_filter}[a]',
            '-map', '[v]',
            '-map', '[a]',
            output_path
        ])
        
        if not success:
            raise RuntimeError(f"Speed change failed: {msg}")
        
        return output_path
    
    def reverse(self, video_path: str, output_path: str = None) -> str:
        """Reverse video playback."""
        output_path = output_path or str(self.output_dir / f"reversed_{datetime.now().strftime('%H%M%S')}.mp4")
        
        success, msg = self._run_ffmpeg([
            '-i', video_path,
            '-vf', 'reverse',
            '-af', 'areverse',
            output_path
        ])
        
        if not success:
            raise RuntimeError(f"Reverse failed: {msg}")
        
        return output_path
    
    def add_audio(self, video_path: str, audio_path: str, output_path: str = None,
                 mix: bool = False, audio_volume: float = 1.0) -> str:
        """Add or replace audio track."""
        output_path = output_path or str(self.output_dir / f"with_audio_{datetime.now().strftime('%H%M%S')}.mp4")
        
        if mix:
            # Mix audio tracks
            success, msg = self._run_ffmpeg([
                '-i', video_path,
                '-i', audio_path,
                '-filter_complex', f'[0:a][1:a]amix=inputs=2:duration=first[a]',
                '-map', '0:v',
                '-map', '[a]',
                '-c:v', 'copy',
                output_path
            ])
        else:
            # Replace audio
            success, msg = self._run_ffmpeg([
                '-i', video_path,
                '-i', audio_path,
                '-c:v', 'copy',
                '-map', '0:v',
                '-map', '1:a',
                '-shortest',
                output_path
            ])
        
        if not success:
            raise RuntimeError(f"Add audio failed: {msg}")
        
        return output_path
    
    def extract_audio(self, video_path: str, output_path: str = None) -> str:
        """Extract audio from video."""
        output_path = output_path or str(self.output_dir / f"audio_{datetime.now().strftime('%H%M%S')}.mp3")
        
        success, msg = self._run_ffmpeg([
            '-i', video_path,
            '-vn',
            '-acodec', 'libmp3lame',
            '-q:a', '2',
            output_path
        ])
        
        if not success:
            raise RuntimeError(f"Audio extraction failed: {msg}")
        
        return output_path
    
    def extract_frames(self, video_path: str, fps: float = 1, output_pattern: str = None) -> List[str]:
        """Extract frames from video."""
        output_pattern = output_pattern or str(self.output_dir / "frame_%04d.png")
        
        success, msg = self._run_ffmpeg([
            '-i', video_path,
            '-vf', f'fps={fps}',
            output_pattern
        ])
        
        if not success:
            raise RuntimeError(f"Frame extraction failed: {msg}")
        
        # Find extracted frames
        import glob
        pattern_dir = Path(output_pattern).parent
        pattern_name = Path(output_pattern).name.replace('%04d', '*')
        frames = sorted(glob.glob(str(pattern_dir / pattern_name)))
        
        return frames
    
    def add_text_overlay(self, video_path: str, text: str, position: str = 'bottom',
                        font_size: int = 24, color: str = 'white',
                        output_path: str = None) -> str:
        """Add text overlay to video."""
        output_path = output_path or str(self.output_dir / f"text_{datetime.now().strftime('%H%M%S')}.mp4")
        
        positions = {
            'top': 'x=(w-text_w)/2:y=50',
            'center': 'x=(w-text_w)/2:y=(h-text_h)/2',
            'bottom': 'x=(w-text_w)/2:y=h-th-50',
        }
        
        pos = positions.get(position, positions['bottom'])
        
        success, msg = self._run_ffmpeg([
            '-i', video_path,
            '-vf', f"drawtext=text='{text}':fontsize={font_size}:fontcolor={color}:{pos}",
            '-c:a', 'copy',
            output_path
        ])
        
        if not success:
            raise RuntimeError(f"Text overlay failed: {msg}")
        
        return output_path
    
    # ===== AI-Powered Features =====
    
    def generate_video_from_image(self, image_path: str, prompt: str = "",
                                  duration: int = 5) -> str:
        """Generate video from image using AI."""
        if not self.api_service:
            raise ValueError("API service required for video generation")
        
        try:
            import replicate
            import base64
            import requests
            
            # Read and encode image
            with open(image_path, 'rb') as f:
                img_data = f.read()
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            data_url = f"data:image/png;base64,{img_base64}"
            
            output = replicate.run(
                "kwaivgi/kling-v2.5-turbo-pro",
                input={
                    "image": data_url,
                    "prompt": prompt or "subtle camera movement",
                    "duration": duration
                }
            )
            
            # Download result
            result_url = output if isinstance(output, str) else output[0]
            response = requests.get(result_url, timeout=120)
            
            output_path = str(self.output_dir / f"generated_{datetime.now().strftime('%H%M%S')}.mp4")
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            raise
    
    def generate_video_from_text(self, prompt: str, duration: int = 5) -> str:
        """Generate video from text prompt using AI."""
        if not self.api_service:
            raise ValueError("API service required for video generation")
        
        try:
            import replicate
            import requests
            
            output = replicate.run(
                "kwaivgi/kling-v2.5-turbo-pro",
                input={
                    "prompt": prompt,
                    "duration": duration
                }
            )
            
            result_url = output if isinstance(output, str) else output[0]
            response = requests.get(result_url, timeout=120)
            
            output_path = str(self.output_dir / f"text_gen_{datetime.now().strftime('%H%M%S')}.mp4")
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            raise


def render_video_editor_ui():
    """Render enhanced video editor UI in Streamlit."""
    import streamlit as st
    
    st.markdown("### 🎬 Enhanced Video Editor")
    
    if not FFMPEG_AVAILABLE:
        st.error("⚠️ FFmpeg not installed. Please install FFmpeg for video editing features.")
        st.code("brew install ffmpeg  # macOS")
        return
    
    # Get API service
    from app.services.platform_helpers import _get_replicate_token
    token = _get_replicate_token()
    api = None
    if token:
        from app.services.api_service import ReplicateAPI
        api = ReplicateAPI(api_token=token)
    
    editor = VideoEditor(api_service=api)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Edit Video", "Generate Video", "Combine Videos", "Extract"])
    
    with tab1:
        st.markdown("#### Edit Existing Video")
        
        uploaded = st.file_uploader("Upload Video", type=['mp4', 'mov', 'avi', 'webm'])
        
        if uploaded:
            # Save uploaded file
            temp_path = str(editor.output_dir / f"upload_{uploaded.name}")
            with open(temp_path, 'wb') as f:
                f.write(uploaded.read())
            
            # Get video info
            info = editor.get_video_info(temp_path)
            
            if info:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Duration", f"{info['duration']:.1f}s")
                with col2:
                    st.metric("Resolution", f"{info['width']}x{info['height']}")
                with col3:
                    st.metric("FPS", f"{info['fps']:.1f}")
                with col4:
                    st.metric("Has Audio", "Yes" if info['has_audio'] else "No")
            
            st.video(temp_path)
            
            # Editing options
            edit_action = st.selectbox("Action", [
                "Trim", "Resize", "Change Speed", "Reverse", 
                "Add Text", "Add Audio"
            ])
            
            if edit_action == "Trim":
                col1, col2 = st.columns(2)
                with col1:
                    start = st.number_input("Start (seconds)", 0.0, info.get('duration', 60.0), 0.0)
                with col2:
                    end = st.number_input("End (seconds)", 0.0, info.get('duration', 60.0), info.get('duration', 10.0))
                
                if st.button("Trim Video", type="primary"):
                    with st.spinner("Trimming..."):
                        try:
                            output = editor.trim(temp_path, start, end)
                            st.success("Video trimmed!")
                            st.video(output)
                            with open(output, 'rb') as f:
                                st.download_button("Download", f.read(), "trimmed.mp4")
                        except Exception as e:
                            st.error(f"Failed: {e}")
            
            elif edit_action == "Resize":
                ratio = st.selectbox("Aspect Ratio", list(editor.ASPECT_RATIOS.keys()))
                width, height = editor.ASPECT_RATIOS[ratio]
                st.caption(f"Output: {width}x{height}")
                
                if st.button("Resize Video", type="primary"):
                    with st.spinner("Resizing..."):
                        try:
                            output = editor.resize(temp_path, width, height)
                            st.success("Video resized!")
                            st.video(output)
                            with open(output, 'rb') as f:
                                st.download_button("Download", f.read(), "resized.mp4")
                        except Exception as e:
                            st.error(f"Failed: {e}")
            
            elif edit_action == "Change Speed":
                speed = st.slider("Speed Multiplier", 0.25, 4.0, 1.0, 0.25)
                
                if st.button("Apply Speed Change", type="primary"):
                    with st.spinner("Processing..."):
                        try:
                            output = editor.change_speed(temp_path, speed)
                            st.success(f"Speed changed to {speed}x!")
                            st.video(output)
                            with open(output, 'rb') as f:
                                st.download_button("Download", f.read(), "speed_changed.mp4")
                        except Exception as e:
                            st.error(f"Failed: {e}")
            
            elif edit_action == "Reverse":
                if st.button("Reverse Video", type="primary"):
                    with st.spinner("Reversing..."):
                        try:
                            output = editor.reverse(temp_path)
                            st.success("Video reversed!")
                            st.video(output)
                            with open(output, 'rb') as f:
                                st.download_button("Download", f.read(), "reversed.mp4")
                        except Exception as e:
                            st.error(f"Failed: {e}")
            
            elif edit_action == "Add Text":
                text = st.text_input("Text to overlay")
                position = st.selectbox("Position", ["bottom", "center", "top"])
                font_size = st.slider("Font Size", 12, 72, 32)
                
                if text and st.button("Add Text Overlay", type="primary"):
                    with st.spinner("Adding text..."):
                        try:
                            output = editor.add_text_overlay(temp_path, text, position, font_size)
                            st.success("Text added!")
                            st.video(output)
                            with open(output, 'rb') as f:
                                st.download_button("Download", f.read(), "with_text.mp4")
                        except Exception as e:
                            st.error(f"Failed: {e}")
            
            elif edit_action == "Add Audio":
                audio_file = st.file_uploader("Upload Audio", type=['mp3', 'wav', 'aac'])
                mix = st.checkbox("Mix with existing audio")
                
                if audio_file and st.button("Add Audio", type="primary"):
                    audio_path = str(editor.output_dir / audio_file.name)
                    with open(audio_path, 'wb') as f:
                        f.write(audio_file.read())
                    
                    with st.spinner("Adding audio..."):
                        try:
                            output = editor.add_audio(temp_path, audio_path, mix=mix)
                            st.success("Audio added!")
                            st.video(output)
                            with open(output, 'rb') as f:
                                st.download_button("Download", f.read(), "with_audio.mp4")
                        except Exception as e:
                            st.error(f"Failed: {e}")
    
    with tab2:
        st.markdown("#### Generate Video with AI")
        
        if not api:
            st.warning("Add Replicate API key for AI video generation")
        else:
            gen_mode = st.radio("Generation Mode", ["From Text", "From Image"])
            
            if gen_mode == "From Text":
                prompt = st.text_area("Describe the video", placeholder="A sunset over the ocean with gentle waves...")
                duration = st.slider("Duration (seconds)", 2, 10, 5)
                
                if prompt and st.button("Generate Video", type="primary"):
                    with st.spinner("Generating video... This may take a few minutes"):
                        try:
                            output = editor.generate_video_from_text(prompt, duration)
                            st.success("Video generated!")
                            st.video(output)
                            with open(output, 'rb') as f:
                                st.download_button("Download", f.read(), "generated.mp4")
                        except Exception as e:
                            st.error(f"Generation failed: {e}")
            
            else:  # From Image
                image_file = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'])
                prompt = st.text_input("Motion description", placeholder="gentle zoom in with camera pan")
                duration = st.slider("Duration (seconds)", 2, 10, 5, key="img_duration")
                
                if image_file and st.button("Generate Video from Image", type="primary"):
                    img_path = str(editor.output_dir / image_file.name)
                    with open(img_path, 'wb') as f:
                        f.write(image_file.read())
                    
                    with st.spinner("Generating video from image..."):
                        try:
                            output = editor.generate_video_from_image(img_path, prompt, duration)
                            st.success("Video generated!")
                            st.video(output)
                            with open(output, 'rb') as f:
                                st.download_button("Download", f.read(), "image_to_video.mp4")
                        except Exception as e:
                            st.error(f"Generation failed: {e}")
    
    with tab3:
        st.markdown("#### Combine Multiple Videos")
        
        video_files = st.file_uploader(
            "Upload Videos to Combine",
            type=['mp4', 'mov'],
            accept_multiple_files=True
        )
        
        if video_files and len(video_files) >= 2:
            st.info(f"Will combine {len(video_files)} videos in order")
            
            if st.button("Combine Videos", type="primary"):
                with st.spinner("Combining videos..."):
                    try:
                        paths = []
                        for i, vf in enumerate(video_files):
                            path = str(editor.output_dir / f"combine_{i}_{vf.name}")
                            with open(path, 'wb') as f:
                                f.write(vf.read())
                            paths.append(path)
                        
                        output = editor.concatenate(paths)
                        st.success("Videos combined!")
                        st.video(output)
                        with open(output, 'rb') as f:
                            st.download_button("Download", f.read(), "combined.mp4")
                    except Exception as e:
                        st.error(f"Failed: {e}")
        elif video_files:
            st.warning("Upload at least 2 videos to combine")
    
    with tab4:
        st.markdown("#### Extract Content from Video")
        
        extract_video = st.file_uploader("Upload Video", type=['mp4', 'mov', 'avi'], key="extract_upload")
        
        if extract_video:
            temp_path = str(editor.output_dir / f"extract_{extract_video.name}")
            with open(temp_path, 'wb') as f:
                f.write(extract_video.read())
            
            extract_type = st.radio("Extract", ["Audio", "Frames"])
            
            if extract_type == "Audio":
                if st.button("Extract Audio"):
                    with st.spinner("Extracting audio..."):
                        try:
                            output = editor.extract_audio(temp_path)
                            st.success("Audio extracted!")
                            st.audio(output)
                            with open(output, 'rb') as f:
                                st.download_button("Download MP3", f.read(), "audio.mp3")
                        except Exception as e:
                            st.error(f"Failed: {e}")
            
            else:  # Frames
                fps = st.slider("Frames per second", 0.5, 10.0, 1.0, 0.5)
                
                if st.button("Extract Frames"):
                    with st.spinner("Extracting frames..."):
                        try:
                            frames = editor.extract_frames(temp_path, fps)
                            st.success(f"Extracted {len(frames)} frames!")
                            
                            # Show first few frames
                            cols = st.columns(min(len(frames), 5))
                            for i, frame in enumerate(frames[:5]):
                                with cols[i]:
                                    st.image(frame, caption=f"Frame {i+1}")
                        except Exception as e:
                            st.error(f"Failed: {e}")
