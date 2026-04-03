# 🚀 Quick Reference: New Features

## Unified Session Manager

### Basic Usage
```python
from app.services.unified_session_manager import UnifiedSessionManager

# Get manager instance
manager = UnifiedSessionManager()

# Save current state
manager.save_session("my_work")

# Load saved state
manager.load_session("my_work")

# List all sessions
sessions = manager.list_sessions()
for session in sessions:
    print(f"{session['name']}: {session['campaigns']} campaigns")
```

### Advanced Features
```python
# Export for backup
data = manager.export_session("important_work")
with open("backup.json", "wb") as f:
    f.write(data)

# Import from backup
with open("backup.json", "rb") as f:
    manager.import_session(f.read())

# Get session info
info = manager.get_session_info()
print(f"Current session has {info['keys_count']} keys")

# Clear and start fresh
manager.clear_session()
```

---

## Type-Safe Configuration

### Basic Usage
```python
from app.config import get_settings

# Get settings (cached)
settings = get_settings()

# Access API keys (type-safe!)
replicate_key = settings.ai_models.replicate_api_token
anthropic_key = settings.ai_models.anthropic_api_key

# Server settings
host = settings.server.backend_host  # str
port = settings.server.backend_port  # int

# Feature flags
if settings.app.enable_analytics:
    track_event()
```

### Environment-Based Config
```python
from app.config import get_settings

settings = get_settings()

# Check environment
if settings.is_production():
    print("Running in production!")
elif settings.is_development():
    print("Development mode")

# Environment-specific logic
timeout = 30 if settings.is_production() else 5
```

### Backward Compatibility
```python
# Old way still works!
from app.config import get_api_key

api_key = get_api_key("REPLICATE_API_TOKEN")

# Or use the settings object
from app.config import get_settings
settings = get_settings()
api_key = settings.get_api_key("REPLICATE_API_TOKEN")
```

---

## Pre-commit Hooks

### Automatic (Recommended)
```bash
# Make changes
git add .

# Commit (hooks run automatically)
git commit -m "Add new feature"

# Hooks check your code before commit!
# If issues found, they're auto-fixed or reported
```

### Manual Execution
```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
pre-commit run ruff --all-files
pre-commit run isort --all-files

# Run only on staged files
pre-commit run
```

### Skip Hooks (Emergency Only)
```bash
# Skip all hooks
git commit --no-verify -m "Emergency fix"

# Skip specific hooks
SKIP=mypy git commit -m "WIP"
```

### Update Hooks
```bash
# Get latest versions
pre-commit autoupdate

# Reinstall
pre-commit clean
pre-commit install
```

---

## Common Commands

### Start Platform
```bash
# Start both services
bash scripts/start_platform.sh

# Start backend only
bash scripts/start_platform.sh backend

# Start frontend only
bash scripts/start_platform.sh frontend

# Stop all services
bash scripts/start_platform.sh stop
```

### Development Workflow
```bash
# 1. Make changes
vim app/services/my_service.py

# 2. Format code (optional - auto-runs on commit)
black app/services/my_service.py

# 3. Check code (optional - auto-runs on commit)
ruff app/services/my_service.py

# 4. Test locally
pytest tests/

# 5. Commit (hooks auto-run)
git add .
git commit -m "Add new service"

# 6. Push
git push
```

### Troubleshooting
```bash
# Check service status
ps aux | grep streamlit
ps aux | grep uvicorn

# Check logs
tail -f scripts/logs/fastapi.log
tail -f scripts/logs/streamlit.log

# Kill stuck processes
pkill -f streamlit
pkill -f uvicorn

# Restart services
bash scripts/start_platform.sh stop
bash scripts/start_platform.sh
```

---

## File Locations

### Configuration
```
.env                              # Environment variables
app/config/settings.py            # Type-safe settings
.pre-commit-config.yaml          # Hook configuration
pyproject.toml                   # Tool settings
```

### Sessions
```
sessions/current_session.json    # Current session
sessions/*.json                  # Saved sessions
```

### Logs
```
scripts/logs/fastapi.log         # Backend logs
scripts/logs/streamlit.log       # Frontend logs
```

### Services
```
app/services/unified_session_manager.py   # Session manager
app/services/fastapi_backend.py          # API backend
app/config/settings.py                   # Configuration
```

---

## Environment Variables

### Required
```bash
REPLICATE_API_TOKEN=r8_xxx...
ANTHROPIC_API_KEY=sk-ant-xxx...
```

### Optional
```bash
# Server
BACKEND_PORT=8601
FRONTEND_PORT=8501

# Platform integrations
PRINTIFY_API_TOKEN=xxx
SHOPIFY_ACCESS_TOKEN=xxx
TWITTER_API_KEY=xxx
SENDGRID_API_KEY=xxx

# Features
ENABLE_RAY=false
ENABLE_ANALYTICS=true
```

---

## Code Style Guide

### Formatting (Black)
```python
# Good - Black style
def my_function(
    param1: str,
    param2: int,
    param3: Optional[bool] = None,
) -> Dict[str, Any]:
    """Docstring here."""
    return {"result": param1}

# Line length: 100 characters max
```

### Imports (isort)
```python
# Standard library
import os
import sys
from pathlib import Path

# Third party
import streamlit as st
from pydantic import Field

# Local
from app.config import get_settings
from app.services.unified_session_manager import UnifiedSessionManager
```

### Type Hints
```python
from typing import Dict, List, Optional, Any

def process_data(
    items: List[str],
    config: Dict[str, Any],
    max_items: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Process items with config."""
    return [{"item": item} for item in items]
```

---

## Testing

### Run Tests
```bash
# All tests
pytest

# Specific file
pytest tests/test_session_manager.py

# With coverage
pytest --cov=app --cov-report=html

# Verbose
pytest -v
```

### Write Tests
```python
import pytest
from app.services.unified_session_manager import UnifiedSessionManager

def test_save_session():
    """Test session save functionality."""
    manager = UnifiedSessionManager()
    result = manager.save_session("test")
    assert result is True

def test_load_session():
    """Test session load functionality."""
    manager = UnifiedSessionManager()
    manager.save_session("test")
    result = manager.load_session("test")
    assert result is True
```

---

## Tips

### Performance
- Use `@lru_cache` for expensive functions
- Load modules lazily with `get_tab_renderer()`
- Use async for I/O operations

### Code Quality
- Run `pre-commit run --all-files` before big commits
- Use type hints for better IDE support
- Write docstrings for public functions

### Debugging
- Check logs first: `tail -f scripts/logs/*.log`
- Use `st.write()` for quick debugging
- Enable debug mode: `DEBUG=true` in `.env`

---

## Resources

- [IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md) - Full improvement roadmap
- [QUICK_WINS_COMPLETED.md](QUICK_WINS_COMPLETED.md) - Recent changes
- [Black Documentation](https://black.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pre-commit Documentation](https://pre-commit.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
