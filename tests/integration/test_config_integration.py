"""
Integration Tests for Configuration System
"""

import os
import pytest


class TestConfigurationIntegration:
    """Test configuration system integration"""

    def test_settings_from_environment(self, test_env):
        """Test loading settings from environment."""
        os.environ["BACKEND_PORT"] = "9999"
        os.environ["REPLICATE_API_TOKEN"] = "test_token"

        from app.config import get_settings

        settings = get_settings()
        assert settings.server.backend_port == 9999
        assert settings.ai_models.replicate_api_token == "test_token"

    def test_settings_caching(self, test_env):
        """Test that settings are cached."""
        from app.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()

        # Should be same instance due to @lru_cache
        assert settings1 is settings2

    def test_api_key_retrieval_methods(self, test_env):
        """Test different methods of API key retrieval."""
        os.environ["TEST_API_KEY"] = "abc123"

        from app.config import get_settings, get_api_key

        # Method 1: Through settings object
        settings = get_settings()
        key1 = settings.get_api_key("TEST_API_KEY")

        # Method 2: Through helper function
        key2 = get_api_key("TEST_API_KEY")

        assert key1 == key2 == "abc123"
