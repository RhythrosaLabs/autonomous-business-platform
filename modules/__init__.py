"""
Modules Package
Modular components for the autonomous business platform
"""

# Set up ffmpeg path from imageio-ffmpeg before any moviepy imports
try:
    import os
    import imageio_ffmpeg
    os.environ['IMAGEIO_FFMPEG_EXE'] = imageio_ffmpeg.get_ffmpeg_exe()
except (ImportError, RuntimeError):
    pass  # ffmpeg not available, audio/video features may be limited

# UI Components
from .ui_components import (
    render_header,
    render_sidebar_stats,
    render_about_page,
    render_command_reference,
    render_feature_card,
    render_progress_indicator,
    render_metric_card,
    render_success_message,
    render_error_message,
    render_info_box,
    render_warning_box
)

# Video Generation
from .video_generation import (
    generate_ken_burns_video,
    generate_sora_video,
    generate_kling_video,
    add_cta_card,
    orchestrate_video_generation,
    VideoGenerationError
)

# Model Selection
from .model_selection_ui import (
    render_model_selection_ui,
    render_model_info_card,
    get_selected_models
)

# Quality Settings
from .quality_settings_ui import (
    render_quality_settings_ui,
    render_platform_presets_ui,
    render_prompt_templates_ui,
    render_advanced_video_settings,
    get_combined_quality_config,
    apply_preset_to_quality
)

# AI Generation (Replicate API)
from .ai_generation import (
    generate_script_with_llama,
    parse_script_segments,
    generate_voiceover_audio,
    generate_background_music,
    generate_video_with_model,
    generate_image_with_flux,
    VOICE_MAP,
    MUSIC_PROMPTS
)

# Audio Processing - wrap in try/except for missing ffmpeg
try:
    from .audio_processing import (
        load_audio_clip,
        adjust_volume,
        loop_audio,
        trim_audio,
        add_fade,
        mix_audio_tracks,
        concatenate_audio,
        prepare_background_music,
        export_audio,
        get_audio_duration,
        normalize_audio_volume
    )
    AUDIO_PROCESSING_AVAILABLE = True
except (ImportError, RuntimeError) as e:
    # ffmpeg not installed or other import error
    AUDIO_PROCESSING_AVAILABLE = False
    # Create dummy functions
    def load_audio_clip(*args, **kwargs): raise RuntimeError("ffmpeg not installed. Run: brew install ffmpeg")
    def adjust_volume(*args, **kwargs): raise RuntimeError("ffmpeg not installed. Run: brew install ffmpeg")
    def loop_audio(*args, **kwargs): raise RuntimeError("ffmpeg not installed. Run: brew install ffmpeg")
    def trim_audio(*args, **kwargs): raise RuntimeError("ffmpeg not installed. Run: brew install ffmpeg")
    def add_fade(*args, **kwargs): raise RuntimeError("ffmpeg not installed. Run: brew install ffmpeg")
    def mix_audio_tracks(*args, **kwargs): raise RuntimeError("ffmpeg not installed. Run: brew install ffmpeg")
    def concatenate_audio(*args, **kwargs): raise RuntimeError("ffmpeg not installed. Run: brew install ffmpeg")
    def prepare_background_music(*args, **kwargs): raise RuntimeError("ffmpeg not installed. Run: brew install ffmpeg")
    def export_audio(*args, **kwargs): raise RuntimeError("ffmpeg not installed. Run: brew install ffmpeg")
    def get_audio_duration(*args, **kwargs): raise RuntimeError("ffmpeg not installed. Run: brew install ffmpeg")
    def normalize_audio_volume(*args, **kwargs): raise RuntimeError("ffmpeg not installed. Run: brew install ffmpeg")

# File Utilities
from .file_utils import (
    download_file,
    save_text_file,
    save_binary_file,
    create_temp_directory,
    cleanup_directory,
    cleanup_files,
    ensure_directory_exists,
    get_file_size,
    list_files_in_directory,
    sanitize_filename,
    copy_file
)

__all__ = [
    # UI Components
    'render_header',
    'render_sidebar_stats',
    'render_about_page',
    'render_command_reference',
    'render_feature_card',
    'render_progress_indicator',
    'render_metric_card',
    'render_success_message',
    'render_error_message',
    'render_info_box',
    'render_warning_box',
    
    # Video Generation
    'generate_ken_burns_video',
    'generate_sora_video',
    'generate_kling_video',
    'add_cta_card',
    'orchestrate_video_generation',
    'VideoGenerationError',
    
    # Model Selection
    'render_model_selection_ui',
    'render_model_info_card',
    'get_selected_models',
    
    # Quality Settings
    'render_quality_settings_ui',
    'render_platform_presets_ui',
    'render_prompt_templates_ui',
    'render_advanced_video_settings',
    'get_combined_quality_config',
    'apply_preset_to_quality',
    
    # AI Generation
    'generate_script_with_llama',
    'parse_script_segments',
    'generate_voiceover_audio',
    'generate_background_music',
    'generate_video_with_model',
    'generate_image_with_flux',
    'VOICE_MAP',
    'MUSIC_PROMPTS',
    
    # Audio Processing
    'load_audio_clip',
    'adjust_volume',
    'loop_audio',
    'trim_audio',
    'add_fade',
    'mix_audio_tracks',
    'concatenate_audio',
    'prepare_background_music',
    'export_audio',
    'get_audio_duration',
    'normalize_audio_volume',
    
    # File Utilities
    'download_file',
    'save_text_file',
    'save_binary_file',
    'create_temp_directory',
    'cleanup_directory',
    'cleanup_files',
    'ensure_directory_exists',
    'get_file_size',
    'list_files_in_directory',
    'sanitize_filename',
    'copy_file',
]
