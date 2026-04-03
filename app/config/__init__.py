"""
Unified Configuration Module for Autonomous Business Platform

This module provides a single source of truth for all configuration,
centralizing API keys, server settings, and application preferences.
"""

from .settings import Settings, get_settings, get_api_key

__all__ = ["Settings", "get_settings", "get_api_key"]
