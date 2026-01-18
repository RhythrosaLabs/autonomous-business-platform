from abp_imports_common import (
    st, os, json, Path, datetime, setup_logger
)

# Maintain backward compatibility alias
dt = datetime
logger = setup_logger(__name__)

from app.utils.ray_integration_helpers import ray_generate_image_sync, is_ray_enabled
from app.services.tab_job_helpers import (
    submit_digital_product_job,
    submit_batch_operation,
    collect_job_results,
    check_jobs_progress,
    are_all_jobs_done
)
from app.services.global_job_queue import JobType, get_global_job_queue

def render_digital_products_tab():
    """
    Renders the Digital Products tab (Tab 4).
    """
    st.markdown('<div class="main-header">💾 Digital Products</div>', unsafe_allow_html=True)
    st.markdown("### Create and sell digital downloads: ebooks, courses, templates, and more")
    
    try:
        from app.services.digital_products_service import (
            DigitalProductsService, 
            DigitalProductGenerator,
            DIGITAL_PRODUCT_TYPES
        )
        DIGITAL_SERVICE_AVAILABLE = True
    except ImportError:
        DIGITAL_SERVICE_AVAILABLE = False
        DIGITAL_PRODUCT_TYPES = {}
    
    if not DIGITAL_SERVICE_AVAILABLE:
        st.warning("⚠️ Digital products service not fully available. Some features may be limited.")
    
    # Initialize service
    try:
        service = DigitalProductsService()
    except:
        service = None
    
    dp_tabs = st.tabs(["🎨 AI Generate", "📤 Upload", "📦 My Products", "📊 Stats"])
    
    with dp_tabs[0]:
        st.markdown("### 🎨 AI-Generate Digital Products")
        st.markdown("Create complete digital products with AI: ebooks, coloring books, courses, comics")
        
        # Product type selection
        product_types = {
            "📚 E-Book": "ebook",
            "🎨 Coloring Book": "coloring_book", 
            "📖 Children's Book": "childrens_book",
            "🎓 Online Course": "course",
            "📰 Digital Magazine": "magazine",
            "🗓️ Planner/Journal": "planner"
        }
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            selected_type = st.selectbox("Product Type", list(product_types.keys()), key="dp_type_main")
            product_title = st.text_input("Title/Topic", placeholder="e.g., 'Beginner's Guide to Meditation'", key="dp_title_main")
            target_audience = st.text_input("Target Audience", placeholder="e.g., 'busy professionals, ages 25-45'", key="dp_audience_main")
        
        with col2:
            num_pages = st.slider("Number of Pages/Sections", 5, 50, 20, key="dp_pages_main")
            style_prompt = st.text_input("Style/Theme", placeholder="e.g., 'modern minimalist, calming blue tones'", key="dp_style_main")
            price = st.number_input("Price ($)", min_value=0.0, max_value=999.0, value=9.99, step=0.99, key="dp_price_main")
        
        if st.button("🚀 Generate Digital Product", type="primary", use_container_width=True, key="generate_dp_main"):
            if product_title:
                with st.spinner(f"Generating {selected_type}... This may take a few minutes..."):
                    st.info("📝 AI is creating your complete digital product...")
                    progress = st.progress(0)
                    
                    try:
                        # Try using the digital products service
                        from app.services.digital_products_service import DigitalProductsService
                        dps = DigitalProductsService()
                        
                        progress.progress(20)
                        
                        # Generate based on type
                        logger.info(f"Starting digital product generation: {selected_type} - {product_title}")
                        product_result = dps.generate_digital_product(
                            product_type=product_types[selected_type],
                            title=product_title,
                            target_audience=target_audience,
                            num_pages=num_pages,
                            style=style_prompt
                        )
                        
                        logger.info(f"Generation returned: {type(product_result)}")
                        if product_result:
                            logger.info(f"Result keys: {product_result.keys() if isinstance(product_result, dict) else 'not a dict'}")
                        
                        progress.progress(80)
                        
                        if product_result:
                            # Store the generated product
                            if 'digital_products' not in st.session_state:
                                st.session_state.digital_products = []
                            
                            new_product = {
                                'id': len(st.session_state.digital_products) + 1,
                                'title': product_title,
                                'type': selected_type,
                                'description': f"AI-generated {selected_type} for {target_audience}",
                                'price': price,
                                'pages': num_pages,
                                'result': product_result,
                                'created_at': dt.now().isoformat()
                            }
                            st.session_state.digital_products.append(new_product)
                            
                            progress.progress(100)
                            st.success(f"✅ {selected_type} '{product_title}' generated successfully!")
                            
                            # Show what was generated
                            if isinstance(product_result, dict):
                                st.info(f"📁 Generated files: {', '.join([k for k,v in product_result.items() if v and '_path' in k])}")
                            
                            st.balloons()
                        else:
                            st.error(f"❌ Generation completed but returned: {product_result}")
                            st.error("Check terminal logs for details")
                    except ImportError:
                        # Fallback: Simple placeholder generation
                        progress.progress(50)
                        
                        if 'digital_products' not in st.session_state:
                            st.session_state.digital_products = []
                        
                        new_product = {
                            'id': len(st.session_state.digital_products) + 1,
                            'title': product_title,
                            'type': selected_type,
                            'description': f"{selected_type} for {target_audience}. Style: {style_prompt}",
                            'price': price,
                            'pages': num_pages,
                            'status': 'outline_ready',
                            'created_at': dt.now().isoformat()
                        }
                        st.session_state.digital_products.append(new_product)
                        
                        progress.progress(100)
                        st.success(f"✅ {selected_type} '{product_title}' outline created!")
                        st.info("💡 Full generation requires digital_products_service.py module")
                    except Exception as e:
                        st.error(f"Generation error: {e}")
            else:
                st.warning("Please enter a title/topic for your digital product")
    
    with dp_tabs[1]:
        st.markdown("### 📤 Upload Existing Digital Product")
        
        uploaded_file = st.file_uploader(
            "Choose a digital file",
            type=['pdf', 'epub', 'mp3', 'wav', 'zip', 'png', 'jpg', 'psd', 'mp4'],
            key="dp_upload_main"
        )
        
        if uploaded_file:
            st.success(f"✅ Uploaded: {uploaded_file.name}")
            
            upload_title = st.text_input("Product Title", key="dp_upload_title")
            upload_desc = st.text_area("Description", key="dp_upload_desc")
            upload_price = st.number_input("Price ($)", min_value=0.0, value=9.99, key="dp_upload_price")
            
            if st.button("📦 Create Listing", type="primary", key="create_dp_listing"):
                if upload_title.strip():
                    # Initialize digital products list if not exists
                    if 'digital_products' not in st.session_state:
                        st.session_state.digital_products = []
                    
                    # Create product entry
                    new_product = {
                        'id': len(st.session_state.digital_products) + 1,
                        'title': upload_title,
                        'description': upload_desc,
                        'price': upload_price,
                        'filename': uploaded_file.name,
                        'file_size': uploaded_file.size,
                        'file_type': uploaded_file.type,
                        'created_at': dt.now().isoformat()
                    }
                    st.session_state.digital_products.append(new_product)
                    st.success(f"✅ Digital product '{upload_title}' created!")
                    st.rerun()
                else:
                    st.warning("Please enter a product title")
    
    with dp_tabs[2]:
        st.markdown("### 📦 My Digital Products")
        
        # List products
        if 'digital_products' not in st.session_state:
            st.session_state.digital_products = []
        
        # Also load from library if available
        try:
            from pathlib import Path
            library_path = Path("library/digital_products")
            if library_path.exists():
                # Load products from library metadata
                for product_file in library_path.glob("*.json"):
                    try:
                        import json
                        with open(product_file, 'r') as f:
                            metadata = json.load(f)
                            # Add to session if not already there
                            if not any(p.get('id') == metadata.get('id') for p in st.session_state.digital_products):
                                st.session_state.digital_products.append(metadata)
                    except:
                        pass
        except:
            pass
        
        if st.session_state.digital_products:
            # Search and filter
            search_col, filter_col = st.columns([2, 1])
            with search_col:
                search_query = st.text_input("🔍 Search products", placeholder="Search by title or type...")
            with filter_col:
                filter_type = st.selectbox("Filter by Type", ["All"] + list(set(p.get('type', 'Unknown') for p in st.session_state.digital_products)))
            
            # Filter products
            filtered_products = st.session_state.digital_products
            if search_query:
                filtered_products = [p for p in filtered_products if search_query.lower() in p.get('title', '').lower()]
            if filter_type != "All":
                filtered_products = [p for p in filtered_products if p.get('type') == filter_type]
            
            # Sort options
            sort_by = st.selectbox("Sort by", ["Newest First", "Oldest First", "Price: High to Low", "Price: Low to High", "Title A-Z"])
            
            if sort_by == "Newest First":
                filtered_products = sorted(filtered_products, key=lambda p: p.get('created_at', ''), reverse=True)
            elif sort_by == "Oldest First":
                filtered_products = sorted(filtered_products, key=lambda p: p.get('created_at', ''))
            elif sort_by == "Price: High to Low":
                filtered_products = sorted(filtered_products, key=lambda p: p.get('price', 0), reverse=True)
            elif sort_by == "Price: Low to High":
                filtered_products = sorted(filtered_products, key=lambda p: p.get('price', 0))
            elif sort_by == "Title A-Z":
                filtered_products = sorted(filtered_products, key=lambda p: p.get('title', '').lower())
            
            st.markdown(f"**Showing {len(filtered_products)} of {len(st.session_state.digital_products)} products**")
            
            # Display products
            for idx, product in enumerate(filtered_products):
                with st.expander(f"{product.get('type', '📄')} {product.get('title', 'Untitled')} - ${product.get('price', 0):.2f}", expanded=False):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Description:** {product.get('description', 'No description')}")
                        st.write(f"**Pages:** {product.get('pages', 'N/A')}")
                        st.write(f"**Created:** {product.get('created_at', 'N/A')[:19]}")
                        
                        if product.get('downloads'):
                            st.write(f"**Downloads:** {product.get('downloads', 0)}")
                        if product.get('revenue'):
                            st.write(f"**Revenue:** ${product.get('revenue', 0):.2f}")
                    
                    with col2:
                        # Preview if available
                        if product.get('result') and isinstance(product.get('result'), dict):
                            if product['result'].get('preview_image'):
                                st.image(product['result']['preview_image'], caption="Preview", use_container_width=True)
                    
                    # Action buttons
                    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
                    
                    with btn_col1:
                        if product.get('result') and isinstance(product.get('result'), dict):
                            file_path = product['result'].get('file_path')
                            if file_path and Path(file_path).exists():
                                with open(file_path, 'rb') as f:
                                    st.download_button(
                                        "📥 Download",
                                        f.read(),
                                        file_name=Path(file_path).name,
                                        mime="application/pdf",
                                        key=f"download_dp_{idx}"
                                    )
                    
                    with btn_col2:
                        if st.button("📊 View Stats", key=f"stats_dp_{idx}"):
                            with st.expander("📊 Product Statistics", expanded=True):
                                st.write(f"**Product:** {product.get('title')}")
                                st.write(f"**Type:** {product.get('type')}")
                                st.write(f"**Price:** ${product.get('price', 0):.2f}")
                                st.write(f"**Downloads:** {product.get('downloads', 0)}")
                                st.write(f"**Revenue:** ${product.get('revenue', 0):.2f}")
                                st.write(f"**Created:** {product.get('created_at', 'N/A')[:19]}")
                                if product.get('views'):
                                    conversion = (product.get('downloads', 0) / product.get('views')) * 100
                                    st.write(f"**Conversion Rate:** {conversion:.1f}%")
                    
                    with btn_col3:
                        if st.button("✏️ Edit", key=f"edit_dp_{idx}"):
                            st.session_state[f'editing_product_{idx}'] = not st.session_state.get(f'editing_product_{idx}', False)
                        
                        if st.session_state.get(f'editing_product_{idx}', False):
                            with st.form(key=f"edit_form_{idx}"):
                                new_title = st.text_input("Title", value=product.get('title', ''))
                                new_price = st.number_input("Price ($)", value=float(product.get('price', 0)), min_value=0.0, step=0.99)
                                new_desc = st.text_area("Description", value=product.get('description', ''))
                                
                                if st.form_submit_button("💾 Save Changes"):
                                    # Update product
                                    for p in st.session_state.digital_products:
                                        if p.get('id') == product.get('id'):
                                            p['title'] = new_title
                                            p['price'] = new_price
                                            p['description'] = new_desc
                                            p['updated_at'] = dt.now().isoformat()
                                            break
                                    st.session_state[f'editing_product_{idx}'] = False
                                    st.success("Product updated!")
                                    st.rerun()
                    
                    with btn_col4:
                        if st.button("🗑️ Delete", key=f"delete_dp_{idx}"):
                            # Remove from session state
                            st.session_state.digital_products = [
                                p for p in st.session_state.digital_products 
                                if p.get('id') != product.get('id')
                            ]
                            # Also delete files if they exist
                            if product.get('result') and isinstance(product.get('result'), dict):
                                file_path = product['result'].get('file_path')
                                if file_path:
                                    try:
                                        Path(file_path).unlink(missing_ok=True)
                                    except:
                                        pass
                            st.success("Product deleted!")
                            st.rerun()
            
            # Bulk actions
            st.markdown("---")
            st.markdown("### 🔧 Bulk Actions")
            bulk_col1, bulk_col2 = st.columns(2)
            with bulk_col1:
                if st.button("📦 Export All Metadata", use_container_width=True):
                    import json
                    from datetime import datetime as dt
                    export_data = json.dumps(st.session_state.digital_products, indent=2)
                    st.download_button(
                        "📥 Download JSON",
                        export_data,
                        file_name=f"digital_products_export_{dt.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
            with bulk_col2:
                if st.button("🗑️ Clear All Products", use_container_width=True):
                    if st.session_state.get('confirm_clear_products'):
                        st.session_state.digital_products = []
                        st.session_state.confirm_clear_products = False
                        st.success("All products cleared!")
                        st.rerun()
                    else:
                        st.session_state.confirm_clear_products = True
                        st.warning("⚠️ Click again to confirm deletion")
        else:
            st.info("No digital products yet. Create one using AI or upload your own!")
    
    with dp_tabs[3]:
        st.markdown("### 📊 Digital Products Analytics")
        
        if 'digital_products' not in st.session_state:
            st.session_state.digital_products = []
        
        products = st.session_state.digital_products
        
        # Calculate stats
        total_products = len(products)
        total_downloads = sum(p.get('downloads', 0) for p in products)
        total_revenue = sum(p.get('revenue', 0) for p in products)
        avg_price = sum(p.get('price', 0) for p in products) / total_products if total_products > 0 else 0
        
        # Overview metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Products", total_products)
        with col2:
            st.metric("Total Downloads", total_downloads)
        with col3:
            st.metric("Revenue", f"${total_revenue:.2f}")
        with col4:
            st.metric("Avg Price", f"${avg_price:.2f}")
        
        if products:
            st.markdown("---")
            
            # Top performers
            st.markdown("### 🏆 Top Performers")
            top_col1, top_col2 = st.columns(2)
            
            with top_col1:
                st.markdown("**Most Downloaded**")
                top_downloads = sorted(products, key=lambda p: p.get('downloads', 0), reverse=True)[:5]
                for i, product in enumerate(top_downloads, 1):
                    st.write(f"{i}. {product.get('title', 'Untitled')} - {product.get('downloads', 0)} downloads")
            
            with top_col2:
                st.markdown("**Highest Revenue**")
                top_revenue = sorted(products, key=lambda p: p.get('revenue', 0), reverse=True)[:5]
                for i, product in enumerate(top_revenue, 1):
                    st.write(f"{i}. {product.get('title', 'Untitled')} - ${product.get('revenue', 0):.2f}")
            
            st.markdown("---")
            
            # Product type breakdown
            st.markdown("### 📋 Product Type Breakdown")
            
            from collections import Counter
            type_counts = Counter(p.get('type', 'Unknown') for p in products)
            type_revenue = {}
            for ptype in type_counts.keys():
                type_revenue[ptype] = sum(p.get('revenue', 0) for p in products if p.get('type') == ptype)
            
            type_col1, type_col2 = st.columns(2)
            
            with type_col1:
                st.markdown("**By Count**")
                for ptype, count in type_counts.most_common():
                    st.write(f"• {ptype}: {count} products")
            
            with type_col2:
                st.markdown("**By Revenue**")
                for ptype, revenue in sorted(type_revenue.items(), key=lambda x: x[1], reverse=True):
                    st.write(f"• {ptype}: ${revenue:.2f}")
            
            st.markdown("---")
            
            # Recent activity
            st.markdown("### 📅 Recent Activity")
            recent_products = sorted(products, key=lambda p: p.get('created_at', ''), reverse=True)[:10]
            
            for product in recent_products:
                with st.expander(f"{product.get('title', 'Untitled')} - {product.get('created_at', 'N/A')[:10]}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Type:** {product.get('type', 'Unknown')}")
                        st.write(f"**Price:** ${product.get('price', 0):.2f}")
                    with col2:
                        st.write(f"**Downloads:** {product.get('downloads', 0)}")
                        st.write(f"**Pages:** {product.get('pages', 'N/A')}")
                    with col3:
                        st.write(f"**Revenue:** ${product.get('revenue', 0):.2f}")
                        conversion = (product.get('downloads', 0) / product.get('views', 1)) * 100 if product.get('views', 0) > 0 else 0
                        st.write(f"**Conversion:** {conversion:.1f}%")
            
            st.markdown("---")
            
            # Customer insights
            st.markdown("### 👥 Customer Insights")
            
            # Simulate customer data (in real implementation, this would come from actual sales)
            total_customers = sum(p.get('downloads', 0) for p in products)  # Simplified
            repeat_customers = int(total_customers * 0.2)  # Estimate
            
            insight_col1, insight_col2, insight_col3 = st.columns(3)
            
            with insight_col1:
                st.metric("Total Customers", total_customers)
            with insight_col2:
                st.metric("Repeat Customers", repeat_customers)
            with insight_col3:
                repeat_rate = (repeat_customers / total_customers * 100) if total_customers > 0 else 0
                st.metric("Repeat Rate", f"{repeat_rate:.1f}%")
            
            st.info("💡 **Tip:** Integrate with payment processors and download tracking to get detailed customer analytics!")
        else:
            st.info("Create some digital products to see analytics!")
