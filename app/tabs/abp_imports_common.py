"""
Centralized imports module for the Autonomous Business Platform.

This module consolidates commonly used imports across the codebase to:
1. Reduce redundant import statements (993+ estimated redundant imports)
2. Improve import consistency and maintainability
3. Provide a single point of reference for standard library and third-party dependencies
4. Enable easier updates to dependencies across the entire project

Usage:
    Instead of importing individually:
        from pathlib import Path
        from datetime import datetime
        from typing import Dict, List
    
    Use the centralized imports:
        from abp_imports_common import Path, datetime, Dict, List

Organized by category for clarity.
"""

# ============================================================================
# STANDARD LIBRARY - Core functionality
# ============================================================================
import os
import sys
import json
import re
import time
import uuid
import logging
import asyncio
import threading
import random
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import pickle
import tempfile
import base64
import hashlib
import platform
from io import BytesIO

# ============================================================================
# STANDARD LIBRARY - Type hints and functional programming
# ============================================================================
from typing import (
    Any, Dict, List, Tuple, Optional, Set, Union, Callable,
    Iterator, Generator, Protocol, Type, TypeVar, Generic,
    Sequence, Mapping, Iterable, Pattern
)
from dataclasses import dataclass, field, asdict
from enum import Enum
from functools import wraps, lru_cache, partial
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# ============================================================================
# THIRD-PARTY - Web and API
# ============================================================================
import streamlit as st
import requests

# ============================================================================
# THIRD-PARTY - Data processing and ML
# ============================================================================
try:
    from PIL import Image, ImageFilter, ImageOps, ImageEnhance
except ImportError:
    Image = None

try:
    import replicate
except ImportError:
    replicate = None

# ============================================================================
# LOCAL - Project modules (conditionally imported to avoid circular deps)
# ============================================================================
# These are imported on-demand in functions that use them to avoid circular imports
# Usage: from abp_imports_common import lazy_import
# result = lazy_import('platform_integrations')

def lazy_import(module_name: str) -> Any:
    """
    Safely import local project modules on-demand to avoid circular imports.
    
    Args:
        module_name: Name of the module to import (e.g., 'platform_integrations')
    
    Returns:
        The imported module, or None if import fails
    
    Example:
        >>> platform_integrations = lazy_import('platform_integrations')
        >>> if platform_integrations:
        ...     result = platform_integrations.some_function()
    """
    try:
        return __import__(module_name)
    except ImportError:
        logging.warning(f"Failed to import {module_name}")
        return None


# ============================================================================
# UTILITY FUNCTIONS - Common patterns used across the codebase
# ============================================================================

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Set up a logger with consistent formatting across the project.
    
    Args:
        name: Logger name (typically __name__)
        level: Logging level (default: logging.INFO)
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
    return logger


def get_project_root() -> Path:
    """
    Get the root directory of the project.
    
    Returns:
        Path object pointing to project root
    """
    return Path(__file__).parent.resolve()


def get_cache_dir() -> Path:
    """
    Get or create the cache directory for the project.
    
    Returns:
        Path object pointing to .cache directory
    """
    cache_dir = get_project_root() / '.cache'
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


def safe_dict_get(d: Dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Safely get nested dictionary values using dot notation.
    
    Args:
        d: Dictionary to traverse
        path: Dot-separated path (e.g., 'config.database.host')
        default: Default value if path not found
    
    Returns:
        Value at path or default
    
    Example:
        >>> config = {'db': {'host': 'localhost'}}
        >>> safe_dict_get(config, 'db.host', 'unknown')
        'localhost'
    """
    keys = path.split('.')
    for key in keys:
        if isinstance(d, dict):
            d = d.get(key)
            if d is None:
                return default
        else:
            return default
    return d


# ============================================================================
# VERSION INFO
# ============================================================================

__version__ = "1.0.0"
__author__ = "ABP Development Team"
__project_root__ = get_project_root()

# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    # Standard library - Core
    'os', 'sys', 'json', 're', 'time', 'uuid', 'logging', 'asyncio', 'threading',
    'random', 'shutil', 'Path', 'datetime', 'timedelta', 'pickle', 'tempfile', 'base64',
    'hashlib', 'platform', 'io', 'BytesIO',
    
    # Standard library - Types
    'Any', 'Dict', 'List', 'Tuple', 'Optional', 'Set', 'Union', 'Callable',
    'Iterator', 'Generator', 'Protocol', 'Type', 'TypeVar', 'Generic',
    'Sequence', 'Mapping', 'Iterable', 'Pattern',
    'dataclass', 'field', 'asdict', 'Enum',
    'wraps', 'lru_cache', 'partial',
    'ThreadPoolExecutor', 'ProcessPoolExecutor',
    
    # Third-party
    'st', 'requests', 'Image', 'ImageFilter', 'ImageOps', 'ImageEnhance',
    'replicate',
    
    # Utilities
    'lazy_import', 'setup_logger', 'get_project_root', 'get_cache_dir',
    'safe_dict_get',
    
    # Version info
    '__version__', '__author__', '__project_root__',
]
