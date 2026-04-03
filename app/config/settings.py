"""
Centralized Settings Management

Provides type-safe configuration with validation and environment-based settings.
Uses Pydantic for validation and supports multiple config sources.
"""

import os
from typing import Optional
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class ServerSettings(BaseSettings):
    """Server-related configuration"""

    # FastAPI Backend
    backend_host: str = Field(default="0.0.0.0", env="BACKEND_HOST")
    backend_port: int = Field(default=8601, env="BACKEND_PORT")

    # Streamlit Frontend
    frontend_host: str = Field(default="0.0.0.0", env="FRONTEND_HOST")
    frontend_port: int = Field(default=8501, env="FRONTEND_PORT")

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class AIModelSettings(BaseSettings):
    """AI Model API configuration"""

    # API Keys
    replicate_api_token: Optional[str] = Field(default=None, env="REPLICATE_API_TOKEN")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    google_api_key: Optional[str] = Field(default=None, env="GOOGLE_API_KEY")
    stabilityai_api_key: Optional[str] = Field(default=None, env="STABILITYAI_API_KEY")
    huggingface_token: Optional[str] = Field(default=None, env="HUGGINGFACE_TOKEN")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class PlatformSettings(BaseSettings):
    """Platform integration configuration"""

    # E-commerce
    printify_api_token: Optional[str] = Field(default=None, env="PRINTIFY_API_TOKEN")
    printify_shop_id: Optional[str] = Field(default=None, env="PRINTIFY_SHOP_ID")
    shopify_shop_url: Optional[str] = Field(default=None, env="SHOPIFY_SHOP_URL")
    shopify_access_token: Optional[str] = Field(default=None, env="SHOPIFY_ACCESS_TOKEN")

    # Social Media
    twitter_api_key: Optional[str] = Field(default=None, env="TWITTER_API_KEY")
    twitter_api_secret: Optional[str] = Field(default=None, env="TWITTER_API_SECRET")
    twitter_access_token: Optional[str] = Field(default=None, env="TWITTER_ACCESS_TOKEN")
    twitter_access_secret: Optional[str] = Field(default=None, env="TWITTER_ACCESS_TOKEN_SECRET")

    facebook_access_token: Optional[str] = Field(default=None, env="FACEBOOK_ACCESS_TOKEN")
    instagram_access_token: Optional[str] = Field(default=None, env="INSTAGRAM_ACCESS_TOKEN")

    # Email
    sendgrid_api_key: Optional[str] = Field(default=None, env="SENDGRID_API_KEY")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class AppSettings(BaseSettings):
    """Application-level settings"""

    # Feature Flags
    enable_ray: bool = Field(default=False, env="ENABLE_RAY")
    enable_analytics: bool = Field(default=True, env="ENABLE_ANALYTICS")
    enable_monitoring: bool = Field(default=True, env="ENABLE_MONITORING")

    # Paths
    output_dir: str = Field(default="outputs", env="OUTPUT_DIR")
    temp_dir: str = Field(default="temp_files", env="TEMP_DIR")
    upload_dir: str = Field(default="temp_uploads", env="UPLOAD_DIR")

    # Limits
    max_upload_size_mb: int = Field(default=100, env="MAX_UPLOAD_SIZE_MB")
    job_timeout_seconds: int = Field(default=3600, env="JOB_TIMEOUT_SECONDS")

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


class Settings(BaseSettings):
    """Main settings class combining all configuration"""

    server: ServerSettings = Field(default_factory=ServerSettings)
    ai_models: AIModelSettings = Field(default_factory=AIModelSettings)
    platforms: PlatformSettings = Field(default_factory=PlatformSettings)
    app: AppSettings = Field(default_factory=AppSettings)

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.server.environment.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.server.environment.lower() == "development"

    def get_api_key(self, key_name: str) -> Optional[str]:
        """
        Get API key by name with fallback to os.getenv

        This method provides backward compatibility with existing code
        that uses get_api_key() or os.getenv() patterns.
        """
        # Try to get from structured settings first
        key_lower = key_name.lower()

        # AI Model keys
        if key_lower == "replicate_api_token":
            return self.ai_models.replicate_api_token
        elif key_lower == "anthropic_api_key":
            return self.ai_models.anthropic_api_key
        elif key_lower == "openai_api_key":
            return self.ai_models.openai_api_key
        elif key_lower == "google_api_key":
            return self.ai_models.google_api_key
        elif key_lower == "stabilityai_api_key":
            return self.ai_models.stabilityai_api_key
        elif key_lower == "huggingface_token":
            return self.ai_models.huggingface_token

        # Platform keys
        elif key_lower == "printify_api_token":
            return self.platforms.printify_api_token
        elif key_lower == "shopify_access_token":
            return self.platforms.shopify_access_token
        elif key_lower == "twitter_api_key":
            return self.platforms.twitter_api_key
        elif key_lower == "sendgrid_api_key":
            return self.platforms.sendgrid_api_key

        # Fallback to environment variable
        return os.getenv(key_name)


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance

    This function is cached to ensure we only load settings once,
    improving performance and ensuring consistency.
    """
    return Settings()


# Convenience functions for backward compatibility
def get_api_key(key_name: str) -> Optional[str]:
    """
    Get API key with fallback

    This provides backward compatibility with the old secure_config pattern.
    """
    settings = get_settings()
    return settings.get_api_key(key_name)
