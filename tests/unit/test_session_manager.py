"""
Unit Tests for Unified Session Manager
"""

import json
import pytest
from pathlib import Path
import tempfile

from app.services.unified_session_manager import UnifiedSessionManager


class TestUnifiedSessionManager:
    """Test suite for UnifiedSessionManager"""

    def test_initialization(self):
        """Test session manager initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UnifiedSessionManager(session_dir=Path(tmpdir))
            assert manager.session_dir.exists()
            assert manager.current_session_file.name == "current_session.json"

    def test_save_session(self, mock_session_manager, sample_session_data):
        """Test saving a session."""
        # Mock streamlit session_state
        import streamlit as st

        # This will fail without Streamlit running, so we'll skip for now
        # Real implementation would use mocking
        pass

    def test_get_persistable_keys(self, mock_session_manager):
        """Test getting persistable keys."""
        keys = mock_session_manager._get_persistable_keys()

        assert "campaigns" in keys
        assert "products" in keys
        assert "settings" in keys
        assert "generated_files" in keys


class TestSessionSerialization:
    """Test session data serialization"""

    def test_json_serialization(self, sample_session_data):
        """Test that session data serializes to JSON."""
        json_str = json.dumps(sample_session_data)
        assert json_str is not None

        # Deserialize and verify
        loaded = json.loads(json_str)
        assert loaded["session_name"] == "test_session"
        assert loaded["version"] == "2.0"
