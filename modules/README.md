# Modules Directory

Modular components for the Autonomous Business Platform.

## Purpose

This directory contains refactored, reusable modules extracted from the main `autonomous_business_platform.py` file to improve:
- **Maintainability**: Smaller, focused modules easier to understand and debug
- **Reusability**: Components can be imported and used across different tabs
- **Testability**: Individual modules can be unit tested in isolation
- **Scalability**: New features added as new modules without bloating main file

## Module Structure

### 1. `ui_components.py` (227 lines)
Reusable UI elements for consistent interface design.

**Functions:**
- `render_header()` - App header with title and description
- `render_sidebar_stats()` - Sidebar metrics and status
- `render_about_page()` - About page content
- `render_command_reference()` - Command reference guide
- `render_feature_card()` - Feature highlight cards
- `render_progress_indicator()` - Progress bars and spinners
- `render_metric_card()` - Metric display cards
- `render_success_message()` - Success notifications
- `render_error_message()` - Error notifications
- `render_info_box()` - Info messages
- `render_warning_box()` - Warning messages

### 2. `model_selection_ui.py` (238 lines)
AI model selection interface with 3 modes.

**Functions:**
- `render_model_selection_ui()` - Main model selection interface
- `_render_recommended_mode()` - Auto AI-powered selection
- `_render_manual_mode()` - Manual checkbox selection
- `_render_fallback_mode()` - Smart retry chain
- `render_model_info_card()` - Model details card
- `get_selected_models()` - Extract selected models from config

**Modes:**
- **Recommended**: AI selects best model based on prompt
- **Manual**: User selects models via checkboxes
- **Fallback**: Automatic retry with fallback models

### 3. `quality_settings_ui.py` (227 lines)
Video quality and platform settings interface.

**Functions:**
- `render_quality_settings_ui()` - Resolution, FPS, bitrate controls
- `render_platform_presets_ui()` - Platform-specific presets (YouTube, Instagram, TikTok, Twitter)
- `render_prompt_templates_ui()` - Prompt template library
- `render_advanced_video_settings()` - Voice, tone, music settings
- `get_combined_quality_config()` - Get all quality settings at once
- `apply_preset_to_quality()` - Apply platform preset to quality config

**Platform Presets:**
- YouTube: 16:9, 1080p, 30fps
- Instagram: 1:1, 1080p, 30fps
- TikTok: 9:16, 1080p, 30fps
- Twitter: 16:9, 720p, 30fps

### 4. `video_generation.py` (450+ lines)
Core video generation logic for all models.

**Functions:**
- `generate_ken_burns_video()` - Ken Burns effect with OpenCV
- `generate_sora_video()` - Sora-2 via Replicate Predictions API
- `generate_kling_video()` - Kling via Replicate Predictions API
- `add_cta_card()` - Add 3.5s CTA end card
- `orchestrate_video_generation()` - Complete generation workflow

**Features:**
- Center-crop zoom for perfect Ken Burns effects
- Predictions API for Sora/Kling (with version resolution)
- MoviePy with threads=1 (prevents multiprocessing issues)
- Automatic CTA card addition
- Quality settings integration

## Usage

### Import modules:
```python
from modules import (
    render_header,
    render_model_selection_ui,
    render_quality_settings_ui,
    orchestrate_video_generation
)
```

### Use in Streamlit:
```python
# Render header
render_header("My App", "Description")

# Get model selection
model_config = render_model_selection_ui()

# Get quality settings
quality_config = render_quality_settings_ui()

# Generate video
video_path, metadata = orchestrate_video_generation(
    model_type="sora",
    prompt="Amazing product video",
    image_path=None,
    output_dir="./output",
    quality_config=quality_config,
    add_cta=True,
    cta_text="Shop Now!"
)
```

## Integration with Main File

The main `autonomous_business_platform.py` file (currently 6189 lines) will be refactored to:
1. Import functions from `modules/`
2. Replace inline code with module calls
3. Pass `st.session_state` and configs between modules
4. Target: Reduce main file to ~1000 lines

## Next Steps

- [ ] Create `campaign_ui.py` for campaign generator interface
- [ ] Refactor main file to use modules
- [ ] Add unit tests for each module
- [ ] Create integration tests
- [ ] Document module APIs
- [ ] Add type hints everywhere

## Benefits

**Before Modularization:**
- ❌ 6189-line monolithic file
- ❌ Hard to find specific functionality
- ❌ Difficult to test individual components
- ❌ Code duplication across tabs
- ❌ Merge conflicts in collaborative work

**After Modularization:**
- ✅ Clean separation of concerns (~200-450 lines per module)
- ✅ Easy to locate and modify specific features
- ✅ Individual modules can be unit tested
- ✅ Reusable UI components across tabs
- ✅ Multiple developers can work on different modules
- ✅ Main file reduced to ~1000 lines (routing + initialization)

## Error Handling

All modules include comprehensive error handling:
- Custom exceptions (e.g., `VideoGenerationError`)
- Detailed logging with `logging` module
- Try/except blocks with context
- Error messages passed to UI components

## Dependencies

Modules depend on:
- `streamlit` - Web framework
- `moviepy` - Video editing
- `opencv-cv2` - Image processing
- `replicate` - AI model API
- `prompt_templates` - Template library
- `ai_model_manager` - Model management
- `video_export_utils` - Export utilities

## Notes

- All video generation uses `threads=1` in MoviePy to prevent multiprocessing issues
- Ken Burns uses OpenCV center-crop for perfect zoom centering
- Sora/Kling use Predictions API (not replicate.run())
- CTA cards are 3.5s duration with black background
- Platform presets automatically configure resolution/FPS/aspect ratio
