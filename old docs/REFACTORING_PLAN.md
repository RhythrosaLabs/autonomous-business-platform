# Refactoring Plan for Autonomous Business Platform (Clean Repo)

## Current Issues
1. **55 symlinks in root** pointing to `app/tabs/` files
2. **69 real Python files scattered in root** that should be organized
3. **Imports use root-level symlinks** instead of proper module paths
4. **Mixed structure** - some files in `app/` folders, others loose in root

## Target Structure (Best Practices)
```
autonomous_business_platform/
├── autonomous_business_platform.py  (main entry point)
├── requirements.txt
├── .python-version
├── packages.txt
├── README.md
├── STREAMLIT_DEPLOYMENT.md
│
├── app/
│   ├── __init__.py
│   │
│   ├── tabs/                 # All UI tab modules
│   │   ├── __init__.py
│   │   ├── dashboard.py
│   │   ├── campaigns.py
│   │   ├── products.py
│   │   └── ... (all other tabs)
│   │
│   ├── services/             # Business logic & API integrations
│   │   ├── __init__.py
│   │   ├── api_service.py
│   │   ├── shopify_service.py
│   │   ├── credential_manager.py
│   │   ├── secure_config.py
│   │   └── ... (AI services, background tasks, etc)
│   │
│   ├── utils/                # Utility functions
│   │   ├── __init__.py
│   │   ├── prompt_templates.py
│   │   ├── video_export_utils.py
│   │   └── performance_optimizations.py
│   │
│   ├── models/               # Data models & schemas
│   │   ├── __init__.py
│   │   └── ... (if any)
│   │
│   └── core/                 # Core business logic
│       ├── __init__.py
│       ├── campaign_engine.py
│       ├── content_generator.py
│       └── ... (major features)
│
├── config/                   # Configuration files
│   └── brand_templates.json
│
├── static/                   # Static assets
│   └── assets/
│
├── tests/                    # Test files
│   └── ...
│
└── docs/                     # Documentation
    └── ...
```

## Refactoring Steps

### Phase 1: Remove Symlinks (Safe - No Code Changes)
- Delete all 55 symlinks from root
- Files already exist in `app/tabs/` so nothing breaks

### Phase 2: Organize Root-Level Service Files
Move scattered service files to proper locations:
- `ai_twitter_poster.py` → `app/services/`
- `background_task_manager.py` → `app/services/`
- `blog_generator.py` → `app/services/`
- `digital_product_generator.py` → `app/services/`
- `multi_platform_poster.py` → `app/services/`
- `social_media_ad_service.py` → `app/services/`
- And ~60 more similar files

### Phase 3: Update Import Statements
Update `autonomous_business_platform.py`:
```python
# OLD
from abp_sidebar import render_sidebar
from abp_config import AppConfig

# NEW
from app.tabs.sidebar import render_sidebar
from app.tabs.config import AppConfig
```

### Phase 4: Rename Tab Files (Remove `abp_` Prefix)
- `app/tabs/abp_dashboard.py` → `app/tabs/dashboard.py`
- `app/tabs/abp_sidebar.py` → `app/tabs/sidebar.py`
- Cleaner imports, less redundant naming

### Phase 5: Test Everything
- Run locally on port 8502
- Verify all tabs load
- Check all features work
- Fix any import issues

### Phase 6: Deploy
- Commit changes
- Push to GitHub
- Verify Streamlit Cloud deployment

## Safety Measures
✅ Work on printify_clean only (not printify)
✅ Test after each major change
✅ Keep git commits granular for easy rollback
✅ Backup before starting
