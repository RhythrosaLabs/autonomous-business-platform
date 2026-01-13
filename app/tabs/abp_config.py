# ========================================
# APP CONFIGURATION
# ========================================
class AppConfig:
    """Centralized app configuration - edit these values to customize behavior."""
    
    # Rate Limits (seconds between API calls)
    MINIMAX_SPEECH_DELAY = 12  # MiniMax requires ~10s between calls
    REDDIT_POST_DELAY = 5  # Delay between Reddit posts
    DEFAULT_RETRY_DELAY = 2  # Default retry delay for API calls
    MAX_RETRIES = 3  # Default max retries for operations
    
    # UI Dimensions
    TEXT_AREA_HEIGHT_SM = 80
    TEXT_AREA_HEIGHT_MD = 120
    TEXT_AREA_HEIGHT_LG = 200
    IMAGE_PREVIEW_WIDTH = 200
    THUMBNAIL_SIZE = 150
    
    # Limits
    MAX_BATCH_SIZE = 20  # Max items for batch operations
    MAX_UPLOAD_SIZE_MB = 200  # Max file upload size
    MAX_VIDEO_DURATION = 300  # Max video duration in seconds
    
    # Feature Flags
    ENABLE_EXPERIMENTAL_FEATURES = True
    ENABLE_AUTO_SAVE = True
    ENABLE_ANALYTICS = True
    ENABLE_RAY_DISTRIBUTED = True  # Enable Ray distributed computing by default
    
    # Ray Configuration
    RAY_NUM_CPUS = None  # Auto-detect if None
    RAY_NUM_GPUS = None  # Auto-detect if None
    RAY_MEMORY_GB = None  # Auto-detect if None
    
    # Default Values
    DEFAULT_ASPECT_RATIO = "16:9"
    DEFAULT_VIDEO_QUALITY = "HD"
    DEFAULT_IMAGE_FORMAT = "PNG"
