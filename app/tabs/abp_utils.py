import streamlit as st
import os
from dotenv import load_dotenv

# ========================================
# CACHING & UTILITIES
# ========================================

@st.cache_resource(ttl=300)  # Cache API clients for 5 minutes
def get_cached_replicate_client(api_token: str):
    """Cache Replicate client to avoid recreating on every rerun."""
    try:
        import replicate
        return replicate.Client(api_token=api_token)
    except Exception:
        return None

@st.cache_resource(ttl=300)
def get_cached_replicate_api(api_token: str):
    """Cache ReplicateAPI instance."""
    try:
        from api_service import ReplicateAPI
        return ReplicateAPI(api_token)
    except Exception:
        return None

@st.cache_data(ttl=30)  # Cache file scans for 30 seconds
def cached_scan_files(_campaigns_dir: str, _knowledge_dir: str, file_types: tuple = None, include_knowledge: bool = True):
    """Cached file scanning to avoid repeated filesystem traversal."""
    from pathlib import Path
    from datetime import datetime as dt
    
    campaigns_path = Path(_campaigns_dir)
    knowledge_path = Path(_knowledge_dir)
    all_files = []
    
    # Scan campaigns directory
    if campaigns_path.exists():
        for item in campaigns_path.rglob('*'):
            if item.is_file() and (file_types is None or item.suffix.lower() in file_types):
                try:
                    stat = item.stat()
                    all_files.append({
                        'path': str(item),
                        'name': item.name,
                        'type': item.suffix.lower(),
                        'size': stat.st_size,
                        'modified': dt.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        'campaign': item.parent.name,
                        'source': 'campaign'
                    })
                except (OSError, IOError):
                    pass
    
    # Scan knowledge base
    if include_knowledge and knowledge_path.exists():
        for item in knowledge_path.rglob('*'):
            if item.is_file():
                ext = item.suffix.lower()
                if file_types is None or ext in file_types:
                    try:
                        stat = item.stat()
                        all_files.append({
                            'path': str(item),
                            'name': item.name,
                            'type': ext,
                            'size': stat.st_size,
                            'modified': dt.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                            'campaign': 'Knowledge Base',
                            'source': 'knowledge'
                        })
                    except (OSError, IOError):
                        pass
    
    return sorted(all_files, key=lambda x: x['modified'], reverse=True)

@st.cache_data(ttl=30)
def cached_scan_products(_products_dir: str, _campaigns_dir: str):
    """Cached product file scanning."""
    from pathlib import Path
    from datetime import datetime as dt
    
    products_path = Path(_products_dir)
    campaigns_path = Path(_campaigns_dir)
    product_files = []
    
    if products_path.exists():
        for item in products_path.rglob('*'):
            if item.is_file():
                try:
                    stat = item.stat()
                    product_files.append({
                        'path': str(item),
                        'name': item.name,
                        'type': item.suffix.lower(),
                        'size': stat.st_size,
                        'modified': dt.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        'campaign': item.parent.name if item.parent != products_path else 'Products',
                        'source': 'product'
                    })
                except (OSError, IOError):
                    pass
    
    if campaigns_path.exists():
        for item in campaigns_path.rglob('*product*'):
            if item.is_file():
                try:
                    stat = item.stat()
                    product_files.append({
                        'path': str(item),
                        'name': item.name,
                        'type': item.suffix.lower(),
                        'size': stat.st_size,
                        'modified': dt.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
                        'campaign': item.parent.name,
                        'source': 'campaign_product'
                    })
                except (OSError, IOError):
                    pass
    
    return sorted(product_files, key=lambda x: x['modified'], reverse=True)

@st.cache_data(ttl=60)
def cached_list_campaigns(_campaigns_dir: str):
    """Cache campaign folder listing."""
    from pathlib import Path
    campaigns_path = Path(_campaigns_dir)
    if campaigns_path.exists():
        return [d.name for d in campaigns_path.iterdir() if d.is_dir()]
    return []

def clear_file_cache():
    """Clear file scanning caches - call after file operations."""
    cached_scan_files.clear()
    cached_scan_products.clear()
    cached_list_campaigns.clear()

@st.cache_data(ttl=300)
def get_env_api_keys():
    """Cache environment API keys to avoid repeated os.getenv calls."""
    return {
        'replicate': os.getenv('REPLICATE_API_TOKEN', ''),
        'printify': os.getenv('PRINTIFY_API_KEY', ''),
        'anthropic': os.getenv('ANTHROPIC_API_KEY', ''),
        'openai': os.getenv('OPENAI_API_KEY', ''),
        'shopify_url': os.getenv('SHOPIFY_SHOP_URL', ''),
        'shopify_token': os.getenv('SHOPIFY_ACCESS_TOKEN', ''),
        'youtube': os.getenv('YOUTUBE_API_KEY', ''),
    }
