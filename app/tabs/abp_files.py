from app.tabs.abp_imports_common import (
    st, os, json, asyncio, Path, datetime, requests, setup_logger
)
from app.services.secure_config import get_api_key

# Maintain backward compatibility alias
dt = datetime
logger = setup_logger(__name__)

from app.tabs.abp_utils import cached_scan_files, cached_scan_products
from app.services.tab_job_helpers import (
    submit_batch_operation,
    collect_job_results,
    check_jobs_progress,
    are_all_jobs_done
)
from app.services.global_job_queue import JobType, get_global_job_queue

# Import optional dependencies
try:
    from app.services.ai_twitter_poster import post_to_twitter_ai
    AI_TWITTER_AVAILABLE = True
except ImportError:
    AI_TWITTER_AVAILABLE = False

def format_size(bytes_size):
    """Format file size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

def toggle_favorite(file_path):
    """Toggle favorite status for a file"""
    path_str = str(file_path)
    if path_str in st.session_state.file_favorites:
        st.session_state.file_favorites.remove(path_str)
    else:
        st.session_state.file_favorites.add(path_str)

def render_file_grid(files, key_prefix, cols_count=4):
    """Render files in a clean grid layout"""
    if not files:
        st.info("No files found")
        return
    
    # View mode selector
    view_col1, view_col2, view_col3 = st.columns([1, 1, 8])
    with view_col1:
        if st.button("▦", key=f"grid_view_{key_prefix}", help="Grid View"):
            st.session_state.file_view_mode = "grid"
            st.rerun()
    with view_col2:
        if st.button("☰", key=f"list_view_{key_prefix}", help="List View"):
            st.session_state.file_view_mode = "list"
            st.rerun()
    
    if st.session_state.file_view_mode == "list":
        # List View
        for idx, file_info in enumerate(files):
            is_fav = str(file_info['path']) in st.session_state.file_favorites
            cols = st.columns([0.5, 3, 1, 1, 1, 1, 1])
            
            with cols[0]:
                if st.button("⭐" if is_fav else "☆", key=f"fav_list_{key_prefix}_{idx}", help="Toggle Favorite"):
                    toggle_favorite(file_info['path'])
                    st.rerun()
            
            with cols[1]:
                st.markdown(f"**{file_info['name'][:40]}**{'...' if len(file_info['name']) > 40 else ''}")
            
            with cols[2]:
                st.caption(file_info['campaign'][:15])
            
            with cols[3]:
                st.caption(format_size(file_info['size']))
            
            with cols[4]:
                with open(file_info['path'], 'rb') as f:
                    st.download_button("⬇️", f.read(), file_name=file_info['name'], 
                                     key=f"dl_list_{key_prefix}_{idx}")
            
            with cols[5]:
                if file_info['type'] in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                    if st.button("🐦", key=f"tw_list_{key_prefix}_{idx}", help="Post to Twitter"):
                        st.session_state[f'show_tw_{key_prefix}_{idx}'] = True
            
            with cols[6]:
                if file_info['type'] in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                    if st.button("🎬", key=f"vid_list_{key_prefix}_{idx}", help="Make Video"):
                        st.session_state[f'make_video_{key_prefix}_{idx}'] = file_info['path']
    else:
        # Grid View - clean uniform cards
        for i in range(0, len(files), cols_count):
            cols = st.columns(cols_count)
            for j, col in enumerate(cols):
                if i + j < len(files):
                    file_info = files[i + j]
                    idx = i + j
                    is_fav = str(file_info['path']) in st.session_state.file_favorites
                    
                    with col:
                        # Container for uniform sizing
                        with st.container():
                            # Favorite button in top right
                            fav_col, spacer = st.columns([1, 5])
                            with fav_col:
                                if st.button("⭐" if is_fav else "☆", key=f"fav_{key_prefix}_{idx}"):
                                    toggle_favorite(file_info['path'])
                                    st.rerun()
                            
                            # Image preview with fixed height
                            if file_info['type'] in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                                try:
                                    st.image(str(file_info['path']), use_container_width=True)
                                except:
                                    st.markdown("🖼️ *Preview unavailable*")
                            elif file_info['type'] in ['.mp4', '.mov', '.avi']:
                                st.video(str(file_info['path']))
                            elif file_info['type'] in ['.mp3', '.wav', '.ogg']:
                                st.audio(str(file_info['path']))
                            else:
                                st.markdown(f"📄 **{file_info['type'].upper()}**")
                            
                            # File info
                            st.markdown(f"**{file_info['name'][:25]}**{'...' if len(file_info['name']) > 25 else ''}")
                            st.caption(f"📁 {file_info['campaign'][:15]} • {format_size(file_info['size'])}")
                            
                            # Compact action buttons
                            btn_cols = st.columns(3)
                            with btn_cols[0]:
                                with open(file_info['path'], 'rb') as f:
                                    st.download_button("⬇️", f.read(), file_name=file_info['name'], 
                                                     key=f"dl_{key_prefix}_{idx}")
                            with btn_cols[1]:
                                if file_info['type'] in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                                    if st.button("🐦", key=f"tw_{key_prefix}_{idx}"):
                                        st.session_state[f'show_tw_{key_prefix}_{idx}'] = True
                            with btn_cols[2]:
                                if file_info['type'] in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                                    if st.button("🎬", key=f"vid_{key_prefix}_{idx}"):
                                        st.session_state[f'make_video_{key_prefix}_{idx}'] = file_info['path']


                            
                            # Video creation modal
                            if st.session_state.get(f'make_video_{key_prefix}_{idx}'):
                                with st.expander("🎬 Generate Video from Image", expanded=True):
                                    st.info("Auto-generating video with AI...")
                                    
                                    video_col1, video_col2 = st.columns(2)
                                    with video_col1:
                                        video_model = st.selectbox(
                                            "Video Model",
                                            ["minimax/video-01", "luma/photon-flash", "lightricks/ltx-video"],
                                            key=f"vid_model_{key_prefix}_{idx}"
                                        )
                                    with video_col2:
                                        motion_level = st.slider("Motion", 1, 5, 3, key=f"motion_{key_prefix}_{idx}")
                                    
                                    video_prompt = st.text_input(
                                        "Prompt (optional)",
                                        placeholder="Product showcase with rotation",
                                        key=f"vid_prompt_{key_prefix}_{idx}"
                                    )
                                    
                                    if st.button("�� Generate", key=f"gen_vid_{key_prefix}_{idx}", type="primary"):
                                        try:
                                            from app.services.platform_helpers import _ensure_replicate_client
                                            from pathlib import Path
                                            import requests
                                            from datetime import datetime
                                            
                                            replicate_api, _ = _ensure_replicate_client()
                                            
                                            with st.spinner(f"Generating video..."):
                                                image_path = str(file_info['path'])
                                                prompt = video_prompt if video_prompt.strip() else f"Product video for {file_info['name']}"
                                                
                                                video_url = replicate_api.generate_video(
                                                    prompt=prompt,
                                                    image_path=image_path,
                                                    motion_level=motion_level,
                                                    aspect_ratio="16:9"
                                                )
                                                
                                                if video_url:
                                                    video_response = requests.get(video_url, timeout=120)
                                                    video_response.raise_for_status()
                                                    
                                                    output_dir = Path("file_library") / "generated_videos"
                                                    output_dir.mkdir(parents=True, exist_ok=True)
                                                    
                                                    base_name = Path(file_info['name']).stem
                                                    video_filename = f"{base_name}_video_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                                                    video_path = output_dir / video_filename
                                                    
                                                    with open(video_path, "wb") as f:
                                                        f.write(video_response.content)
                                                    
                                                    st.success("✅ Video generated!")
                                                    st.video(str(video_path))
                                                    st.caption(f"📁 `{video_path}`")
                                                    
                                                    st.session_state[f'make_video_{key_prefix}_{idx}'] = None
                                                    st.rerun()
                                                else:
                                                    st.error("❌ No video URL returned")
                                        except Exception as e:
                                            st.error(f"❌ Failed: {str(e)}")
                                    
                                    if st.button("Cancel", key=f"cancel_vid_{key_prefix}_{idx}"):
                                        st.session_state[f'make_video_{key_prefix}_{idx}'] = None
                                        st.rerun()

def render_file_library_tab():
    st.markdown("### 📁 File & Asset Library")
    st.markdown("Browse all generated files, campaigns, and assets.")
    
    # Performance: Track which sub-tab is active to avoid loading all at once
    if 'files_active_subtab' not in st.session_state:
        st.session_state.files_active_subtab = 0
    
    # Lazy loading: Track which tabs have been explicitly loaded by user
    if 'file_library_loaded_tabs' not in st.session_state:
        st.session_state.file_library_loaded_tabs = set()
    
    # Pagination state
    if 'files_page' not in st.session_state:
        st.session_state.files_page = 0
    ITEMS_PER_PAGE = 20
    
    # Add AI-Generated Library browser at the top (collapsed by default for speed)
    with st.expander("🤖 AI-Generated Content Library", expanded=False):
        # Only load content when expanded (saves initial load time)
        if st.button("🔄 Load Library Contents", key="load_ai_library"):
            st.session_state.show_ai_library = True
        
        if st.session_state.get('show_ai_library', False):
            st.markdown("**Quick access to all AI-generated content with smart search and filtering**")
        
        from pathlib import Path
        import json
        
        library_root = Path("library")
        
        if library_root.exists():
            # Search and filter controls
            search_col1, search_col2, search_col3 = st.columns([2, 1, 1])
            
            with search_col1:
                lib_search = st.text_input("🔍 Search by prompt or filename", placeholder="Search generated content...", key="lib_search")
            
            with search_col2:
                content_type_filter = st.selectbox("Content Type", ["All", "Images", "Videos", "3D Models", "Audio", "Documents", "Campaigns"])
            
            with search_col3:
                source_filter = st.selectbox("Source", ["All", "Playground", "Campaign Generator", "Product Studio"])
            
            # Date filter
            date_col1, date_col2 = st.columns(2)
            with date_col1:
                days_filter = st.selectbox("Time Range", ["All Time", "Today", "Last 7 Days", "Last 30 Days", "Last 90 Days"])
            with date_col2:
                sort_by = st.selectbox("Sort By", ["Newest First", "Oldest First", "Name A-Z", "Name Z-A", "Source"])
            
            # Collect all generated content with metadata
            content_items = []
            
            # Map content types to folders
            type_folders = {
                "Images": "images",
                "Videos": "videos",
                "3D Models": "3d_models",
                "Audio": "audio",
                "Documents": "documents",
                "Campaigns": "campaigns"
            }
            
            folders_to_scan = [type_folders[content_type_filter]] if content_type_filter != "All" else list(type_folders.values())
            
            for folder_name in folders_to_scan:
                folder_path = library_root / folder_name
                if folder_path.exists():
                    # Find all metadata JSON files
                    for meta_file in folder_path.glob("*_metadata.json"):
                        try:
                            with open(meta_file, 'r') as f:
                                metadata = json.load(f)
                                
                                # Get actual file path
                                file_name = metadata.get('filename', '')
                                file_path = folder_path / file_name
                                
                                if file_path.exists():
                                    content_items.append({
                                        'file_path': file_path,
                                        'metadata': metadata,
                                        'folder': folder_name
                                    })
                        except Exception as e:
                            continue
            
            # Apply filters
            filtered_items = content_items
            
            # Search filter
            if lib_search:
                filtered_items = [
                    item for item in filtered_items
                    if lib_search.lower() in item['metadata'].get('prompt', '').lower()
                    or lib_search.lower() in item['file_path'].name.lower()
                ]
            
            # Source filter
            if source_filter != "All":
                source_map = {"Playground": "playground", "Campaign Generator": "campaign", "Product Studio": "product"}
                filtered_items = [
                    item for item in filtered_items
                    if source_map.get(source_filter, '').lower() in item['metadata'].get('source', '').lower()
                ]
            
            # Date filter
            if days_filter != "All Time":
                from datetime import timedelta
                days_map = {"Today": 1, "Last 7 Days": 7, "Last 30 Days": 30, "Last 90 Days": 90}
                cutoff_date = (dt.now() - timedelta(days=days_map[days_filter])).isoformat()
                filtered_items = [
                    item for item in filtered_items
                    if item['metadata'].get('created_at', '') >= cutoff_date
                ]
            
            # Sort
            if sort_by == "Newest First":
                filtered_items.sort(key=lambda x: x['metadata'].get('created_at', ''), reverse=True)
            elif sort_by == "Oldest First":
                filtered_items.sort(key=lambda x: x['metadata'].get('created_at', ''))
            elif sort_by == "Name A-Z":
                filtered_items.sort(key=lambda x: x['file_path'].name.lower())
            elif sort_by == "Name Z-A":
                filtered_items.sort(key=lambda x: x['file_path'].name.lower(), reverse=True)
            elif sort_by == "Source":
                filtered_items.sort(key=lambda x: x['metadata'].get('source', ''))
            
            # Display results
            st.markdown(f"**Found {len(filtered_items)} items** {'(filtered from ' + str(len(content_items)) + ')' if len(filtered_items) != len(content_items) else ''}")
            
            if filtered_items:
                # Display in grid
                cols_per_row = 3
                for idx in range(0, len(filtered_items), cols_per_row):
                    cols = st.columns(cols_per_row)
                    for col_idx, item in enumerate(filtered_items[idx:idx + cols_per_row]):
                        with cols[col_idx]:
                            metadata = item['metadata']
                            file_path = item['file_path']
                            
                            # Display preview
                            if metadata.get('content_type') == 'image':
                                st.image(str(file_path), use_container_width=True)
                            elif metadata.get('content_type') == 'video':
                                st.video(str(file_path))
                            elif metadata.get('content_type') == '3d':
                                st.info(f"🧊 3D Model\n{file_path.name}")
                            else:
                                st.info(f"📄 {file_path.name}")
                            
                            # Metadata
                            st.caption(f"**Source:** {metadata.get('source', 'Unknown')}")
                            if metadata.get('prompt'):
                                st.caption(f"**Prompt:** {metadata.get('prompt', '')[:60]}...")
                            if metadata.get('model'):
                                st.caption(f"**Model:** {metadata.get('model', 'Unknown')}")
                            st.caption(f"**Created:** {metadata.get('created_at', 'Unknown')[:10]}")
                            
                            # Download button
                            if file_path.exists():
                                with open(file_path, 'rb') as f:
                                    st.download_button(
                                        "⬇️ Download",
                                        f.read(),
                                        file_name=file_path.name,
                                        key=f"lib_dl_{idx}_{col_idx}",
                                        use_container_width=True
                                    )
                
                # Bulk actions
                st.markdown("---")
                bulk_col1, bulk_col2 = st.columns(2)
                with bulk_col1:
                    if st.button("📦 Export Metadata (JSON)", use_container_width=True):
                        export_data = [item['metadata'] for item in filtered_items]
                        st.download_button(
                            "⬇️ Download JSON",
                            json.dumps(export_data, indent=2),
                            file_name=f"library_export_{dt.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                with bulk_col2:
                    st.info(f"💾 Total size: {sum(item['metadata'].get('file_size_bytes', 0) for item in filtered_items) / 1024 / 1024:.1f} MB")
            else:
                st.info("No content found matching filters")
        else:
            st.info("Library folder not found. Generate some content to start building your library!")
    
    # Custom CSS for clean grid display
    st.markdown("""
    <style>
    .file-grid-item {
        background: white;
        border-radius: 12px;
        padding: 10px;
        border: 1px solid #e0e0e0;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    .file-grid-item:hover {
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
    }
    .file-image-container {
        width: 100%;
        height: 150px;
        overflow: hidden;
        border-radius: 8px;
        background: #f5f5f5;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .file-image-container img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .file-info {
        padding: 8px 0;
        flex: 1;
    }
    .file-name {
        font-weight: 600;
        font-size: 0.9em;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .file-meta {
        font-size: 0.75em;
        color: #666;
    }
    .favorite-star {
        color: #ffc107;
        cursor: pointer;
    }
    .mini-btn {
        padding: 2px 6px !important;
        font-size: 0.7em !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize favorites in session state
    if 'file_favorites' not in st.session_state:
        st.session_state.file_favorites = set()
    
    # Initialize view mode
    if 'file_view_mode' not in st.session_state:
        st.session_state.file_view_mode = "grid"
    
    # File type filter with Favorites, Knowledge Base, Products, Templates, Conversations, Contacts added
    file_filter_tabs = st.tabs([
        "⭐ Favorites", 
        "📚 Knowledge Base",
        "🛍️ Products",
        "🎨 Templates",
        "💬 Conversations",
        "👥 Contacts",
        "📂 All Files", 
        "🖼️ Images", 
        "🎥 Videos", 
        "📄 Documents", 
        "🎵 Audio", 
        "📦 Campaigns"
    ])
    
    workspace_root = Path.cwd()
    campaigns_dir = workspace_root / "campaigns"
    knowledge_dir = workspace_root / "otto_knowledge"
    products_dir = workspace_root / "products"
    
    # Ensure directories exist
    knowledge_dir.mkdir(exist_ok=True)
    (knowledge_dir / "images").mkdir(exist_ok=True)
    (knowledge_dir / "documents").mkdir(exist_ok=True)
    products_dir.mkdir(exist_ok=True)
    
    def scan_files(file_types=None, include_knowledge=True):
        """Scan workspace for files - uses caching for performance"""
        # Convert file_types to tuple for caching (lists aren't hashable)
        ft = tuple(file_types) if file_types else None
        cached_results = cached_scan_files(str(campaigns_dir), str(knowledge_dir), ft, include_knowledge)
        # Convert path strings back to Path objects for compatibility
        for f in cached_results:
            f['path'] = Path(f['path'])
        return cached_results
    
    # FAVORITES TAB
    with file_filter_tabs[0]:
        if st.session_state.file_favorites:
            st.markdown(f"**Favorite Files:** {len(st.session_state.file_favorites)}")
            
            fav_files = []
            for fav_path in st.session_state.file_favorites:
                p = Path(fav_path)
                if p.exists():
                    fav_files.append({
                        'name': p.name,
                        'path': p,
                        'size': p.stat().st_size,
                        'type': p.suffix.lower(),
                        'campaign': p.parent.name
                    })
            
            if fav_files:
                render_file_grid(fav_files, "fav")
            else:
                st.info("No favorite files found (files may have been deleted)")
        else:
            st.info("No favorites yet. Star files to see them here!")
    
    # KNOWLEDGE BASE TAB
    with file_filter_tabs[1]:
        st.markdown("### 📚 Knowledge Base")
        st.markdown("Manage files that Otto uses for context and learning.")
        
        kb_tabs = st.tabs(["📂 Files", "📤 Upload", "🧠 Memory"])
        
        with kb_tabs[0]:
            # Lazy load - only scan when button clicked
            if st.button("📂 Load Knowledge Base Files", key="load_kb_files", use_container_width=True):
                st.session_state.kb_files_loaded = True
            
            if st.session_state.get('kb_files_loaded', False):
                with st.spinner("Scanning files..."):
                    kb_files = scan_files(include_knowledge=True)
                    kb_only = [f for f in kb_files if "otto_knowledge" in str(f['path'])]
                
                if kb_only:
                    # Pagination
                    total_pages = max(1, (len(kb_only) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
                    page = st.session_state.get('kb_page', 0)
                    start_idx = page * ITEMS_PER_PAGE
                    end_idx = start_idx + ITEMS_PER_PAGE
                    
                    st.caption(f"Showing {start_idx+1}-{min(end_idx, len(kb_only))} of {len(kb_only)} files")
                    render_file_grid(kb_only[start_idx:end_idx], "kb", cols_count=4)
                    
                    # Pagination controls
                    if total_pages > 1:
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col1:
                            if st.button("⬅️ Previous", disabled=page==0, key="kb_prev"):
                                st.session_state.kb_page = max(0, page - 1)
                                st.rerun()
                        with col2:
                            st.caption(f"Page {page+1} of {total_pages}")
                        with col3:
                            if st.button("Next ➡️", disabled=page>=total_pages-1, key="kb_next"):
                                st.session_state.kb_page = min(total_pages-1, page + 1)
                                st.rerun()
                else:
                    st.info("Knowledge base is empty")
        
        with kb_tabs[1]:
            uploaded_files = st.file_uploader("Upload to Knowledge Base", accept_multiple_files=True)
            if uploaded_files:
                for uploaded_file in uploaded_files:
                    # Determine subfolder based on type
                    if uploaded_file.type.startswith('image'):
                        target_dir = knowledge_dir / "images"
                    else:
                        target_dir = knowledge_dir / "documents"
                    
                    target_path = target_dir / uploaded_file.name
                    with open(target_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                st.success(f"✅ Uploaded {len(uploaded_files)} files to Knowledge Base")
                st.rerun()
        
        with kb_tabs[2]:
            st.markdown("#### 🧠 Otto's Memory")
            st.markdown("View what Otto has learned from your files.")
            
            try:
                from app.services.otto_engine import get_knowledge_base
                kb = get_knowledge_base()
                stats = kb.get_stats()
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Documents", stats.get('documents', 0))
                col2.metric("Chunks", stats.get('chunks', 0))
                col3.metric("Last Updated", stats.get('last_updated', 'Never'))
                
                if st.button("🔄 Re-index Knowledge Base"):
                    with st.spinner("Re-indexing..."):
                        kb.reindex()
                    st.success("Knowledge Base updated!")
            except ImportError:
                st.warning("Knowledge Base module not available")

    # PRODUCTS TAB
    with file_filter_tabs[2]:
        st.markdown("### 🛍️ Product Library")
        st.markdown("Manage your generated products and designs.")
        
        prod_tabs = st.tabs(["🖼️ Designs", "👕 Printify Products", "✨ Generate New"])
        
        with prod_tabs[0]:
            # Lazy load products
            if st.button("📂 Load Product Designs", key="load_prod_designs", use_container_width=True):
                st.session_state.prod_designs_loaded = True
            
            if st.session_state.get('prod_designs_loaded', False):
                with st.spinner("Scanning products..."):
                    product_files = cached_scan_products(str(products_dir), str(campaigns_dir))
                    # Convert paths
                    for p in product_files:
                        p['path'] = Path(p['path'])
                
                if product_files:
                    # Pagination
                    total_pages = max(1, (len(product_files) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
                    page = st.session_state.get('prod_page', 0)
                    start_idx = page * ITEMS_PER_PAGE
                    end_idx = start_idx + ITEMS_PER_PAGE
                    
                    st.caption(f"Showing {start_idx+1}-{min(end_idx, len(product_files))} of {len(product_files)} files")
                    render_file_grid(product_files[start_idx:end_idx], "prod_designs", cols_count=4)
                    
                    # Pagination controls
                    if total_pages > 1:
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col1:
                            if st.button("⬅️ Previous", disabled=page==0, key="prod_prev"):
                                st.session_state.prod_page = max(0, page - 1)
                                st.rerun()
                        with col2:
                            st.caption(f"Page {page+1} of {total_pages}")
                        with col3:
                            if st.button("Next ➡️", disabled=page>=total_pages-1, key="prod_next"):
                                st.session_state.prod_page = min(total_pages-1, page + 1)
                                st.rerun()
                else:
                    st.info("No product designs yet")
        
        with prod_tabs[1]:
            st.markdown("#### 👕 Printify Integration")
            try:
                from app.services.api_service import PrintifyAPI as PrintifyClient
                printify_token = st.session_state.get('printify_api_key') or os.getenv('PRINTIFY_API_TOKEN')
                
                if printify_token:
                    client = PrintifyClient(printify_token)
                    shops = client.get_shops()
                    
                    if shops:
                        shop_id = shops[0]['id']
                        products = client.get_products(shop_id)
                        
                        if products:
                            st.markdown(f"Found {len(products)} products in shop '{shops[0]['title']}'")
                            
                            for prod in products[:5]:  # Show first 5
                                with st.expander(f"{prod.get('title', 'Untitled')}"):
                                    col1, col2 = st.columns([1, 3])
                                    with col1:
                                        if prod.get('images'):
                                            st.image(prod['images'][0]['src'], use_container_width=True)
                                    with col2:
                                        st.markdown(f"**Status:** {prod.get('visible', False) and 'Published' or 'Hidden'}")
                                        st.markdown(f"**Created:** {prod.get('created_at', '')[:10]}")
                                        st.markdown(f"[View in Printify](https://printify.com/app/store/products/{prod['id']})")
                        else:
                            st.info("No products found in Printify shop")
                    else:
                        st.warning("No Printify shops found")
                else:
                    st.warning("Printify API key not configured")
            except Exception as e:
                st.error(f"Printify error: {e}")
        
        with prod_tabs[2]:
            st.markdown("#### ✨ Generate New Product")
            
            col1, col2 = st.columns(2)
            with col1:
                product_type = st.selectbox("Product Type", ["T-Shirt", "Hoodie", "Mug", "Poster", "Phone Case", "Tote Bag"], key="prod_gen_type")
                product_idea = st.text_area("Product Idea/Prompt", placeholder="A cute astronaut cat floating in space with pizza...", key="prod_gen_idea")
            
            with col2:
                style_preset = st.selectbox("Style", [
                    "Photorealistic", 
                    "Cartoon", 
                    "Minimalist", 
                    "Vintage", 
                    "Cyberpunk", 
                    "Watercolor", 
                    "Line Art"
                ], key="prod_gen_style")
                
                variations = st.slider("Variations to Generate", 1, 4, 2, key="prod_gen_vars")
            
            if st.button("🚀 Generate Product", use_container_width=True, type="primary", key="gen_product_btn"):
                if product_idea:
                    replicate_token = st.session_state.get('replicate_api_key') or get_api_key('REPLICATE_API_TOKEN')
                    if replicate_token:
                        with st.spinner(f"🎨 Generating {variations} {product_type} variations in parallel..."):
                            try:
                                from app.services.api_service import ReplicateAPI
                                import time
                                api = ReplicateAPI(replicate_token)
                                
                                # Get global job queue
                                queue = get_global_job_queue()
                                job_ids = []
                                
                                # Submit all variations at once
                                for i in range(variations):
                                    # Build prompt based on product type and style
                                    design_prompt = f"{product_idea}, {style_preset.lower()} style, professional product design, high quality, {product_type.lower()}"
                                    
                                    def generate_single_product(prompt=design_prompt, idx=i, prod_dir=products_dir, idea=product_idea):
                                        """Generate a single product variation"""
                                        try:
                                            # Generate image
                                            image_url = api.generate_image(prompt, model="flux")
                                            
                                            if image_url:
                                                # Save to products directory
                                                response = requests.get(image_url)
                                                
                                                safe_name = "".join(c if c.isalnum() else "_" for c in idea[:30])
                                                filename = f"{safe_name}_v{idx+1}_{dt.now().strftime('%H%M%S')}.png"
                                                filepath = prod_dir / filename
                                                
                                                with open(filepath, 'wb') as f:
                                                    f.write(response.content)
                                                
                                                return {
                                                    'url': image_url,
                                                    'path': filepath,
                                                    'filename': filename
                                                }
                                        except Exception as e:
                                            logger.error(f"Error generating variation {idx+1}: {e}")
                                            return None
                                        return None
                                    
                                    job_id = queue.submit_job(
                                        job_type=JobType.PRODUCT_CREATION,
                                        tab_name="Files",
                                        description=f"Product Variation {i+1}/{variations}",
                                        function=generate_single_product,
                                        priority=6
                                    )
                                    job_ids.append(job_id)
                                
                                # Store job IDs for persistence across tab switches
                                st.session_state.files_product_jobs = job_ids
                                st.session_state.files_product_type = product_type
                                st.session_state.files_product_idea = product_idea
                                st.session_state.files_product_style = style_preset
                                st.session_state.files_product_variations = variations
                                
                                st.success(f"✅ Submitted {len(job_ids)} product variation jobs!")
                                st.info("💡 Jobs run in background. You can switch tabs - progress is saved!")
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Generation failed: {e}")
                    else:
                        st.error("❌ Replicate API key required. Add it in Settings.")
                else:
                    st.warning("Please enter a product idea")
            
            # Show progress for running jobs (non-blocking)
            if st.session_state.get('files_product_jobs'):
                job_ids = st.session_state.files_product_jobs
                
                st.markdown("---")
                st.markdown("### ⚙️ Product Generation in Progress")
                
                progress = check_jobs_progress(job_ids)
                total = len(job_ids)
                done = progress['completed'] + progress['failed']
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("🔄 Running", progress['running'])
                with col2:
                    st.metric("✅ Completed", progress['completed'])
                with col3:
                    st.metric("❌ Failed", progress['failed'])
                with col4:
                    st.metric("📊 Progress", f"{done}/{total}")
                
                st.progress(done / total if total > 0 else 0)
                
                if st.button("🔄 Refresh Progress", key="refresh_files_progress"):
                    st.rerun()
                
                if are_all_jobs_done(job_ids):
                    st.success("🎉 All product variations completed!")
                    
                    # Collect results
                    results = collect_job_results(job_ids, timeout=120)
                    results = [r for r in results if r is not None]
                    
                    # Clear job tracking
                    del st.session_state.files_product_jobs
                    for key in ['files_product_type', 'files_product_idea', 'files_product_style', 'files_product_variations']:
                        st.session_state.pop(key, None)
                    
                    # Display all results
                    st.success(f"✅ Generated {len(results)} variations!")
                    
                    for i, result in enumerate(results):
                        if result:
                            st.image(result['url'], caption=f"Variation {i+1}", use_container_width=True)
                    
                    # Offer next steps
                    next_cols = st.columns(3)
                    with next_cols[0]:
                        if st.button("📤 Send to Printify", key="send_printify"):
                            st.info("Go to Product Studio to upload to Printify")
                    with next_cols[1]:
                        if st.button("🎬 Create Video Ad", key="create_video_ad"):
                            st.session_state['video_source_images'] = [r['path'] for r in results if 'path' in r]
                            st.info("Go to Video Producer to create video")
                    with next_cols[2]:
                        if st.button("📱 Social Media Pack", key="create_social"):
                            st.info("Go to Content Generator for social assets")
    
    # TEMPLATES TAB
    with file_filter_tabs[3]:
        st.markdown("### 🎨 Template Library")
        st.markdown("Browse and manage all your templates: brand guidelines, social media kits, video presets, and workflow templates.")
        
        template_tabs = st.tabs(["🎨 Brand Templates", "📱 Social Media Kits", "🎬 Video Templates", "🔧 Workflow Templates", "📄 Document Templates"])
        
        # BRAND TEMPLATES
        with template_tabs[0]:
            st.markdown("#### 🎨 Brand Templates")
            st.markdown("Your saved brand identities with colors, fonts, and style guidelines.")
            
            # Load brand templates
            templates_file = Path("brand_templates.json")
            brand_templates = []
            if templates_file.exists():
                try:
                    with open(templates_file, 'r') as f:
                        data = json.load(f)
                        brand_templates = data.get('templates', [])
                except:
                    pass
            
            if brand_templates:
                for idx, template in enumerate(brand_templates):
                    colors = template.get('colors', {})
                    fonts = template.get('fonts', {})
                    with st.expander(f"🎨 {template.get('name', 'Untitled')} - {template.get('tagline', '')}", expanded=(idx == 0)):
                        cols = st.columns([2, 2, 1])
                        with cols[0]:
                            st.markdown("**Colors**")
                            color_cols = st.columns(3)
                            with color_cols[0]:
                                st.color_picker("Primary", colors.get('primary', '#667eea'), key=f"brand_primary_{idx}", disabled=True)
                            with color_cols[1]:
                                st.color_picker("Secondary", colors.get('secondary', '#764ba2'), key=f"brand_secondary_{idx}", disabled=True)
                            with color_cols[2]:
                                st.color_picker("Accent", colors.get('accent', '#ffd700'), key=f"brand_accent_{idx}", disabled=True)
                        
                        with cols[1]:
                            st.markdown("**Typography**")
                            st.markdown(f"- **Heading Font:** {fonts.get('heading_family', template.get('font_style', 'Modern Sans-Serif'))}")
                            st.markdown(f"- **Body Font:** {fonts.get('body_family', 'System Default')}")
                            st.markdown(f"- **Heading Size:** {fonts.get('heading_size', '24px')}")
                        
                        with cols[2]:
                            if st.button("✏️ Edit", key=f"edit_brand_{idx}"):
                                st.session_state.current_main_tab = 15  # Go to Brand Templates tab
                                st.rerun()
                            if st.button("📋 Copy", key=f"copy_brand_{idx}"):
                                st.session_state[f'copied_brand'] = template
                                st.success("Copied!")
                        
                        st.markdown(f"**Voice:** {template.get('voice', 'Not set')}")
                        st.markdown(f"**CTA:** {template.get('cta_text', 'Not set')}")
            else:
                st.info("No brand templates yet. Create one in the Brand Templates tab!")
                if st.button("🎨 Create Brand Template", key="goto_brand_templates"):
                    st.session_state.current_main_tab = 15
                    st.rerun()
        
        # SOCIAL MEDIA KITS
        with template_tabs[1]:
            st.markdown("#### 📱 Social Media Kit Templates")
            st.markdown("Pre-designed templates for different social platforms.")
            
            social_kits = [
                {"name": "Instagram Feed Post", "size": "1080x1080", "icon": "📸", "desc": "Square post for Instagram feed"},
                {"name": "Instagram Story", "size": "1080x1920", "icon": "📱", "desc": "Vertical story format"},
                {"name": "Instagram Reel Cover", "size": "1080x1920", "icon": "🎬", "desc": "Cover image for Reels"},
                {"name": "Twitter/X Post", "size": "1200x675", "icon": "🐦", "desc": "Optimal size for Twitter images"},
                {"name": "Pinterest Pin", "size": "1000x1500", "icon": "📌", "desc": "Tall format for Pinterest"},
                {"name": "YouTube Thumbnail", "size": "1280x720", "icon": "▶️", "desc": "Video thumbnail"},
                {"name": "TikTok Video", "size": "1080x1920", "icon": "🎵", "desc": "Vertical video format"},
                {"name": "LinkedIn Post", "size": "1200x627", "icon": "💼", "desc": "Professional post image"},
                {"name": "Facebook Cover", "size": "820x312", "icon": "📘", "desc": "Page cover photo"},
            ]
            
            kit_cols = st.columns(3)
            for idx, kit in enumerate(social_kits):
                with kit_cols[idx % 3]:
                    with st.container():
                        st.markdown(f"### {kit['icon']} {kit['name']}")
                        st.caption(f"{kit['size']} • {kit['desc']}")
                        if st.button(f"🎨 Create", key=f"create_social_{idx}", use_container_width=True):
                            st.session_state['social_template_size'] = kit['size']
                            st.session_state['social_template_name'] = kit['name']
                            st.session_state.current_main_tab = 6  # Content Generator
                            st.rerun()
        
        # VIDEO TEMPLATES
        with template_tabs[2]:
            st.markdown("#### 🎬 Video Templates")
            st.markdown("Pre-configured video styles and presets.")
            
            video_templates = [
                {"name": "Product Showcase", "duration": "15-30s", "icon": "📦", "style": "Clean transitions, product focus"},
                {"name": "Social Ad - Energetic", "duration": "10-15s", "icon": "⚡", "style": "Fast cuts, bold text, music-driven"},
                {"name": "Brand Story", "duration": "30-60s", "icon": "📖", "style": "Narrative flow, voiceover-friendly"},
                {"name": "Tutorial/How-To", "duration": "60-120s", "icon": "🎓", "style": "Step-by-step, clear text overlays"},
                {"name": "Testimonial", "duration": "30-45s", "icon": "💬", "style": "Quote emphasis, subtle background"},
                {"name": "Unboxing/Reveal", "duration": "20-40s", "icon": "🎁", "style": "Suspense build, satisfying reveal"},
            ]
            
            for idx, vt in enumerate(video_templates):
                with st.expander(f"{vt['icon']} {vt['name']} ({vt['duration']})"):
                    st.markdown(f"**Style:** {vt['style']}")
                    st.markdown(f"**Duration:** {vt['duration']}")
                    if st.button(f"🎬 Use Template", key=f"use_video_template_{idx}"):
                        st.session_state['video_template'] = vt
                        st.session_state.current_main_tab = 7  # Video Producer
                        st.rerun()
        
        # WORKFLOW TEMPLATES
        with template_tabs[3]:
            st.markdown("#### 🔧 Workflow Templates")
            st.markdown("Pre-built automation workflows.")
            
            workflow_templates = [
                {"name": "Full Product Launch", "steps": 8, "icon": "🚀", "desc": "Design → Mockup → Printify → Social → Video → Post"},
                {"name": "Daily Social Content", "steps": 4, "icon": "📱", "desc": "Generate → Schedule → Post → Track"},
                {"name": "Weekly Campaign", "steps": 6, "icon": "📅", "desc": "Plan → Create Content → Schedule → Execute → Analyze"},
                {"name": "Blog to Social", "steps": 3, "icon": "📝", "desc": "Write Blog → Extract Quotes → Create Social Posts"},
                {"name": "Video Production", "steps": 5, "icon": "🎬", "desc": "Script → Record → Edit → Export → Upload"},
            ]
            
            for idx, wf in enumerate(workflow_templates):
                with st.expander(f"{wf['icon']} {wf['name']} ({wf['steps']} steps)"):
                    st.markdown(f"**Flow:** {wf['desc']}")
                    if st.button(f"🔧 Load Workflow", key=f"load_workflow_{idx}"):
                        st.session_state['loaded_workflow_template'] = wf
                        st.session_state.current_main_tab = 9  # Workflows
                        st.rerun()
        
        # DOCUMENT TEMPLATES
        with template_tabs[4]:
            st.markdown("#### 📄 Document Templates")
            st.markdown("Pre-formatted document templates.")
            
            doc_templates = [
                {"name": "Campaign Brief", "icon": "📋", "desc": "Outline for marketing campaigns"},
                {"name": "Content Calendar", "icon": "📅", "desc": "Weekly/monthly content planning"},
                {"name": "Product Description", "icon": "📦", "desc": "E-commerce product copy template"},
                {"name": "Email Newsletter", "icon": "📧", "desc": "Newsletter structure and sections"},
                {"name": "Social Media Report", "icon": "📊", "desc": "Analytics and performance report"},
            ]
            
            for idx, doc in enumerate(doc_templates):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"{doc['icon']} **{doc['name']}** - {doc['desc']}")
                with col2:
                    if st.button("📄 Use", key=f"use_doc_template_{idx}"):
                        st.session_state['doc_template'] = doc
                        st.info(f"Template '{doc['name']}' ready to use!")
    
    # CONVERSATIONS TAB (index 4) - Chat History Storage
    with file_filter_tabs[4]:
        st.markdown("### 💬 Saved Conversations")
        st.markdown("All your chat conversations with Otto are stored here for easy access and reference.")
        
        # Import chat history manager
        try:
            from app.services.chat_assistant import get_chat_history_manager
            chat_manager = get_chat_history_manager()
            
            # Search and filter
            conv_search = st.text_input("🔍 Search conversations", key="conv_search_lib", placeholder="Search by title or content...")
            
            if conv_search:
                conversations = chat_manager.search_conversations(conv_search)
            else:
                conversations = chat_manager.list_conversations(limit=50)
            
            if conversations:
                st.markdown(f"**📚 {len(conversations)} conversation(s) found**")
                
                # Display as cards
                cols = st.columns(2)
                for idx, conv in enumerate(conversations):
                    with cols[idx % 2]:
                        with st.container():
                            # Format date
                            try:
                                created = datetime.fromisoformat(conv.get('created_at', ''))
                                date_str = created.strftime("%b %d, %Y at %H:%M")
                            except:
                                date_str = "Unknown date"
                            
                            st.markdown(f"""
                            <div style="border:1px solid #333;border-radius:8px;padding:12px;margin-bottom:10px;">
                                <h4 style="margin:0 0 8px 0;">💬 {conv.get('title', 'Untitled')[:40]}</h4>
                                <p style="color:#888;font-size:12px;margin:0 0 8px 0;">📅 {date_str} • {conv.get('message_count', 0)} messages</p>
                                <p style="font-size:11px;color:#666;margin:0;">{conv.get('summary', 'No preview')[:80]}...</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            btn_cols = st.columns(3)
                            with btn_cols[0]:
                                if st.button("📖 Load", key=f"lib_load_conv_{idx}", use_container_width=True):
                                    result = chat_manager.load_conversation(conv['id'])
                                    if result.get('success'):
                                        st.session_state.chat_history = result['conversation']['messages']
                                        st.session_state.current_conversation_id = conv['id']
                                        st.success(f"✅ Loaded: {conv.get('title', 'Conversation')}")
                                    else:
                                        st.error("Failed to load conversation")
                            
                            with btn_cols[1]:
                                if st.button("📋 Export", key=f"lib_export_conv_{idx}", use_container_width=True):
                                    result = chat_manager.load_conversation(conv['id'])
                                    if result.get('success'):
                                        # Create exportable format
                                        export_text = f"# {conv.get('title', 'Conversation')}\\n"
                                        export_text += f"Date: {date_str}\\n\\n"
                                        for msg in result['conversation']['messages']:
                                            role = "You" if msg['role'] == 'user' else "Otto"
                                            export_text += f"**{role}:** {msg['content']}\\n\\n"
                                        st.download_button(
                                            "⬇️ Download",
                                            export_text,
                                            file_name=f"{conv['id']}.md",
                                            mime="text/markdown",
                                            key=f"download_conv_{idx}"
                                        )
                            
                            with btn_cols[2]:
                                if st.button("🗑️ Delete", key=f"lib_del_conv_{idx}", use_container_width=True):
                                    chat_manager.delete_conversation(conv['id'])
                                    st.rerun()
            else:
                st.info("💬 No saved conversations yet")
                st.markdown("""
                **How to save conversations:**
                1. Chat with Otto in the sidebar or Chat tab
                2. Click 💾 **Save** in the Chat History panel
                3. Or conversations auto-save when you start a new chat
                
                All your conversations will appear here!
                """)
        except ImportError as e:
            st.error(f"Chat history module not available: {e}")
    
    # CONTACTS TAB (new)
    with file_filter_tabs[5]:
        st.markdown("### 👥 Contact Library")
        st.caption("Contacts found during AI campaign generation")
        
        # Load contacts from library
        contacts_lib_dir = workspace_root / "library" / "contacts"
        
        if contacts_lib_dir.exists():
            contact_files = sorted(contacts_lib_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
            
            if contact_files:
                st.markdown(f"**📇 {len(contact_files)} Contact Lists Saved**")
                
                # Display contacts grouped by file
                for contact_file in contact_files:
                    try:
                        import json
                        with open(contact_file, 'r') as f:
                            contact_data = json.load(f)
                        
                        campaign_name = contact_data.get('campaign', 'Unknown')[:60]
                        found_at = contact_data.get('found_at', '')[:10]
                        contacts_list = contact_data.get('contacts', [])
                        
                        with st.expander(f"📋 {campaign_name} — {len(contacts_list)} contacts ({found_at})", expanded=False):
                            st.markdown(f"**Product Type:** {contact_data.get('product_type', 'N/A')}")
                            st.markdown(f"**Target Market:** {contact_data.get('target_market', 'N/A')}")
                            st.markdown("---")
                            
                            # Extract emails
                            emails = [c['channel'] for c in contacts_list if c.get('channel_type') == 'email' and '@' in c.get('channel', '')]
                            
                            if emails:
                                st.success(f"📧 **{len(emails)} Email Contacts**")
                                st.code("\\n".join(emails), language=None)
                                
                                # Copy all emails button
                                if st.button(f"📋 Copy All Emails", key=f"copy_emails_{contact_file.stem}"):
                                    st.code("\\n".join(emails))
                                    st.info("✅ Select and copy the emails above")
                            
                            # Show individual contacts
                            st.markdown("#### 👤 Contact Details")
                            for i, contact in enumerate(contacts_list[:10]):  # Show first 10
                                with st.container():
                                    st.markdown(f"**{i+1}. {contact.get('name', 'Unknown')}**")
                                    st.markdown(f"🏢 {contact.get('role', 'N/A')} at {contact.get('company', 'N/A')}")
                                    st.markdown(f"📧 {contact.get('channel', 'N/A')} ({contact.get('channel_type', 'N/A')})")
                                    st.caption(f"💡 {contact.get('rationale', 'N/A')[:100]}")
                                    
                                    if i < len(contacts_list) - 1:
                                        st.markdown("---")
                            
                            if len(contacts_list) > 10:
                                st.caption(f"... and {len(contacts_list) - 10} more contacts")
                            
                            # Download CSV
                            import pandas as pd
                            df = pd.DataFrame(contacts_list)
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label="📥 Download as CSV",
                                data=csv,
                                file_name=f"contacts_{contact_file.stem}.csv",
                                mime="text/csv",
                                key=f"download_csv_{contact_file.stem}"
                            )
                            
                            # Delete button
                            if st.button("🗑️ Delete Contact List", key=f"delete_{contact_file.stem}", type="secondary"):
                                contact_file.unlink()
                                st.success("Deleted!")
                                st.rerun()
                    
                    except Exception as e:
                        st.error(f"Error loading {contact_file.name}: {e}")
            else:
                st.info("📭 No contacts saved yet. Run a campaign with 'AI Insights' enabled to find contacts.")
        else:
            st.info("📭 No contacts library found. Run a campaign with 'AI Insights' enabled to start building your contact library.")
    
    # ALL FILES TAB (shifted from index 5 to 6)
    with file_filter_tabs[6]:
        # Lazy load all files
        if st.button("📂 Load All Files", key="load_all_files", use_container_width=True):
            st.session_state.all_files_loaded = True
        
        if st.session_state.get('all_files_loaded', False):
            with st.spinner("Scanning all files..."):
                all_files = scan_files()
            
            st.markdown(f"**Total Files:** {len(all_files)}")
            
            if all_files:
                search_term = st.text_input("🔍 Search files", key="search_all")
                filtered_files = [f for f in all_files if search_term.lower() in f['name'].lower()] if search_term else all_files
                
                # Pagination
                total_pages = max(1, (len(filtered_files) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
                page = st.session_state.get('all_files_page', 0)
                start_idx = page * ITEMS_PER_PAGE
                end_idx = start_idx + ITEMS_PER_PAGE
                
                st.caption(f"Showing {start_idx+1}-{min(end_idx, len(filtered_files))} of {len(filtered_files)} files")
                render_file_grid(filtered_files[start_idx:end_idx], "all", cols_count=4)
                
                # Pagination controls
                if total_pages > 1:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col1:
                        if st.button("⬅️ Previous", disabled=page==0, key="all_prev"):
                            st.session_state.all_files_page = max(0, page - 1)
                            st.rerun()
                    with col2:
                        st.caption(f"Page {page+1} of {total_pages}")
                    with col3:
                        if st.button("Next ➡️", disabled=page>=total_pages-1, key="all_next"):
                            st.session_state.all_files_page = min(total_pages-1, page + 1)
                            st.rerun()
            else:
                st.info("No files yet. Generate your first campaign to see files here!")
    
    # IMAGES TAB
    with file_filter_tabs[7]:
        tab_key = 'images'
        if tab_key not in st.session_state.file_library_loaded_tabs:
            st.info("🖼️ Click 'Load Images' to browse your image files")
            if st.button("🖼️ Load Images", key=f"load_{tab_key}", use_container_width=True):
                st.session_state.file_library_loaded_tabs.add(tab_key)
                st.rerun()
        else:
            with st.spinner("Scanning images..."):
                image_files = scan_files(['.png', '.jpg', '.jpeg', '.gif', '.webp'])
            
            st.markdown(f"**Image Files:** {len(image_files)}")
            
            if image_files:
                search_term = st.text_input("🔍 Search images", key="search_images")
                filtered = [f for f in image_files if search_term.lower() in f['name'].lower()] if search_term else image_files
                
                # Pagination
                total_pages = max(1, (len(filtered) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
                page = st.session_state.get('images_page', 0)
                start_idx = page * ITEMS_PER_PAGE
                end_idx = start_idx + ITEMS_PER_PAGE
                
                st.caption(f"Showing {start_idx+1}-{min(end_idx, len(filtered))} of {len(filtered)} images")
                render_file_grid(filtered[start_idx:end_idx], "img", cols_count=4)
                
                if total_pages > 1:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col1:
                        if st.button("⬅️ Previous", disabled=page==0, key="img_prev"):
                            st.session_state.images_page = max(0, page - 1)
                            st.rerun()
                    with col2:
                        st.caption(f"Page {page+1} of {total_pages}")
                    with col3:
                        if st.button("Next ➡️", disabled=page>=total_pages-1, key="img_next"):
                            st.session_state.images_page = min(total_pages-1, page + 1)
                            st.rerun()
            else:
                st.info("No images yet")
    
    # VIDEOS TAB
    with file_filter_tabs[8]:
        tab_key = 'videos'
        if tab_key not in st.session_state.file_library_loaded_tabs:
            st.info("🎥 Click 'Load Videos' to browse your video files")
            if st.button("🎥 Load Videos", key=f"load_{tab_key}", use_container_width=True):
                st.session_state.file_library_loaded_tabs.add(tab_key)
                st.rerun()
        else:
            with st.spinner("Scanning videos..."):
                video_files = scan_files(['.mp4', '.mov', '.avi', '.webm'])
            
            st.markdown(f"**Video Files:** {len(video_files)}")
            
            if video_files:
                search_term = st.text_input("🔍 Search videos", key="search_videos")
                filtered = [f for f in video_files if search_term.lower() in f['name'].lower()] if search_term else video_files
                
                # Pagination
                total_pages = max(1, (len(filtered) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
                page = st.session_state.get('videos_page', 0)
                start_idx = page * ITEMS_PER_PAGE
                end_idx = start_idx + ITEMS_PER_PAGE
                
                st.caption(f"Showing {start_idx+1}-{min(end_idx, len(filtered))} of {len(filtered)} videos")
                render_file_grid(filtered[start_idx:end_idx], "vid", cols_count=3)
                
                if total_pages > 1:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col1:
                        if st.button("⬅️ Previous", disabled=page==0, key="vid_prev"):
                            st.session_state.videos_page = max(0, page - 1)
                            st.rerun()
                    with col2:
                        st.caption(f"Page {page+1} of {total_pages}")
                    with col3:
                        if st.button("Next ➡️", disabled=page>=total_pages-1, key="vid_next"):
                            st.session_state.videos_page = min(total_pages-1, page + 1)
                            st.rerun()
            else:
                st.info("No videos yet")
    
    # DOCUMENTS TAB
    with file_filter_tabs[9]:
        tab_key = 'documents'
        if tab_key not in st.session_state.file_library_loaded_tabs:
            st.info("📄 Click 'Load Documents' to browse your document files")
            if st.button("📄 Load Documents", key=f"load_{tab_key}", use_container_width=True):
                st.session_state.file_library_loaded_tabs.add(tab_key)
                st.rerun()
        else:
            with st.spinner("Scanning documents..."):
                doc_files = scan_files(['.txt', '.md', '.pdf', '.csv', '.json'])
            
            st.markdown(f"**Document Files:** {len(doc_files)}")
            
            if doc_files:
                # Pagination
                page = st.session_state.get('docs_page', 0)
                total_pages = max(1, (len(doc_files) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
                start_idx = page * ITEMS_PER_PAGE
                paginated_files = doc_files[start_idx:start_idx + ITEMS_PER_PAGE]
                
                for file_info in paginated_files:
                    is_fav = str(file_info['path']) in st.session_state.file_favorites
                    with st.expander(f"{'⭐ ' if is_fav else ''}📄 {file_info['name']}"):
                        fav_col, content_col = st.columns([1, 10])
                        with fav_col:
                            if st.button("⭐" if is_fav else "☆", key=f"fav_doc_{file_info['path']}"):
                                toggle_favorite(file_info['path'])
                                st.rerun()
                        
                        # Show text preview for readable files
                        if file_info['type'] in ['.txt', '.md', '.csv']:
                            try:
                                with open(file_info['path'], 'r') as f:
                                    content = f.read(500)
                                    st.text(content[:500] + "..." if len(content) > 500 else content)
                            except (UnicodeDecodeError, IOError):
                                st.caption("Binary file")
                        
                        with open(file_info['path'], 'rb') as f:
                            st.download_button("⬇️ Download", f.read(), file_name=file_info['name'],
                                             key=f"dl_doc_{file_info['path']}")
                
                # Pagination controls
                if total_pages > 1:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col1:
                        if st.button("⬅️ Prev", disabled=page<=0, key="docs_prev"):
                            st.session_state.docs_page = max(0, page - 1)
                            st.rerun()
                    with col2:
                        st.caption(f"Page {page+1} of {total_pages}")
                    with col3:
                        if st.button("Next ➡️", disabled=page>=total_pages-1, key="docs_next"):
                            st.session_state.docs_page = min(total_pages-1, page + 1)
                            st.rerun()
            else:
                st.info("No documents yet")
    
    # AUDIO TAB
    with file_filter_tabs[10]:
        tab_key = 'audio'
        if tab_key not in st.session_state.file_library_loaded_tabs:
            st.info("🎵 Click 'Load Audio Files' to browse your audio files")
            if st.button("🎵 Load Audio Files", key=f"load_{tab_key}", use_container_width=True):
                st.session_state.file_library_loaded_tabs.add(tab_key)
                st.rerun()
        else:
            audio_files = scan_files(['.mp3', '.wav', '.ogg', '.m4a'])
            st.markdown(f"**Audio Files:** {len(audio_files)}")
            
            if audio_files:
                # Pagination
                page = st.session_state.get('audio_page', 0)
                total_pages = max(1, (len(audio_files) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
                start_idx = page * ITEMS_PER_PAGE
                paginated_files = audio_files[start_idx:start_idx + ITEMS_PER_PAGE]
                
                for file_info in paginated_files:
                    is_fav = str(file_info['path']) in st.session_state.file_favorites
                    with st.expander(f"{'⭐ ' if is_fav else ''}🎵 {file_info['name']}"):
                        fav_col, _ = st.columns([1, 10])
                        with fav_col:
                            if st.button("⭐" if is_fav else "☆", key=f"fav_audio_{file_info['path']}"):
                                toggle_favorite(file_info['path'])
                                st.rerun()
                        st.audio(str(file_info['path']))
                        with open(file_info['path'], 'rb') as f:
                            st.download_button("⬇️ Download", f.read(), file_name=file_info['name'],
                                             key=f"dl_audio_{file_info['path']}")
                
                # Pagination controls
                if total_pages > 1:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col1:
                        if st.button("⬅️ Prev", disabled=page<=0, key="audio_prev"):
                            st.session_state.audio_page = max(0, page - 1)
                            st.rerun()
                    with col2:
                        st.caption(f"Page {page+1} of {total_pages}")
                    with col3:
                        if st.button("Next ➡️", disabled=page>=total_pages-1, key="audio_next"):
                            st.session_state.audio_page = min(total_pages-1, page + 1)
                            st.rerun()
            else:
                st.info("No audio files yet")
    
    # CAMPAIGNS TAB
    with file_filter_tabs[11]:
        tab_key = 'campaigns'
        if tab_key not in st.session_state.file_library_loaded_tabs:
            st.info("📦 Click 'Load Campaigns' to browse your campaign folders")
            if st.button("📦 Load Campaigns", key=f"load_{tab_key}", use_container_width=True):
                st.session_state.file_library_loaded_tabs.add(tab_key)
                st.rerun()
        else:
            if campaigns_dir.exists():
                campaign_folders = [d for d in campaigns_dir.iterdir() if d.is_dir()]
                st.markdown(f"**Campaigns:** {len(campaign_folders)}")
                
                # Pagination
                page = st.session_state.get('campaigns_page', 0)
                total_pages = max(1, (len(campaign_folders) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
                sorted_campaigns = sorted(campaign_folders, key=lambda x: x.stat().st_mtime, reverse=True)
                start_idx = page * ITEMS_PER_PAGE
                paginated_campaigns = sorted_campaigns[start_idx:start_idx + ITEMS_PER_PAGE]
                
                for campaign in paginated_campaigns:
                    with st.expander(f"📦 {campaign.name}"):
                        files_in_campaign = list(campaign.rglob('*'))
                        files_only = [f for f in files_in_campaign if f.is_file()]
                        
                        st.markdown(f"**Files:** {len(files_only)}")
                        st.caption(f"Created: {datetime.fromtimestamp(campaign.stat().st_mtime).strftime('%Y-%m-%d %H:%M')}")
                        
                        # Show previews
                        for file_path in files_only[:5]:  # Show first 5 files
                            ext = file_path.suffix.lower()
                            st.markdown(f"• `{file_path.name}` ({format_size(file_path.stat().st_size)})")
                        
                        if len(files_only) > 5:
                            st.caption(f"... and {len(files_only) - 5} more files")
                        
                        # Bulk download button
                        if st.button(f"📦 Download Campaign ZIP", key=f"zip_{campaign.name}"):
                            import zipfile
                            import io
                            
                            zip_buffer = io.BytesIO()
                            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                for file_path in files_only:
                                    zip_file.write(file_path, file_path.name)
                            
                            zip_buffer.seek(0)
                            st.download_button(
                                "⬇️ Download ZIP",
                                zip_buffer.read(),
                                file_name=f"{campaign.name}.zip",
                                mime="application/zip",
                                key=f"zip_dl_{campaign.name}"
                            )
                
                # Pagination controls
                if total_pages > 1:
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col1:
                        if st.button("⬅️ Prev", disabled=page<=0, key="campaigns_prev"):
                            st.session_state.campaigns_page = max(0, page - 1)
                            st.rerun()
                    with col2:
                        st.caption(f"Page {page+1} of {total_pages}")
                    with col3:
                        if st.button("Next ➡️", disabled=page>=total_pages-1, key="campaigns_next"):
                            st.session_state.campaigns_page = min(total_pages-1, page + 1)
                            st.rerun()
            else:
                st.info("No campaigns yet")
