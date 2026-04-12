import logging
import os

import streamlit as st

# Configure logger
logger = logging.getLogger(__name__)


def render_analytics_tab():
    """
    Renders the Analytics tab (Tab 14).
    """
    st.markdown("### 📊 Real-Time Business Analytics")
    st.markdown("Live data from Shopify, Printify, and YouTube")

    # Create analytics tabs
    analytics_tabs = st.tabs(
        ["📊 Overview", "🛍️ Shopify", "📦 Printify", "📺 YouTube", "🐦 Twitter"]
    )

    # ========================================
    # OVERVIEW TAB
    # ========================================
    with analytics_tabs[0]:
        st.markdown("#### 🎯 Business Overview")

        # Initialize/check API connections
        shopify_connected = False
        printify_connected = False
        youtube_connected = False

        # Check Shopify - try to get it or check credentials
        if "shopify_api" not in st.session_state or st.session_state.shopify_api is None:
            # Try to initialize from credentials
            if os.getenv("SHOPIFY_SHOP_URL") and os.getenv("SHOPIFY_ACCESS_TOKEN"):
                try:
                    from app.services.shopify_service import ShopifyAPI

                    st.session_state.shopify_api = ShopifyAPI()
                    shopify_connected = st.session_state.shopify_api.connected
                except Exception as e:
                    logger.error(f"Failed to initialize Shopify: {e}")
                    shopify_connected = False
            else:
                shopify_connected = False
        else:
            shopify_connected = st.session_state.shopify_api and getattr(
                st.session_state.shopify_api, "connected", False
            )

        # Check Printify - try to get it or check credentials
        if "printify_api" not in st.session_state or st.session_state.printify_api is None:
            # Try to initialize from credentials
            if os.getenv("PRINTIFY_API_TOKEN"):
                try:
                    from app.services.api_service import PrintifyAPI

                    st.session_state.printify_api = PrintifyAPI(
                        api_token=os.getenv("PRINTIFY_API_TOKEN"),
                        shop_id=os.getenv("PRINTIFY_SHOP_ID"),
                    )
                    # Test connection
                    shops = st.session_state.printify_api.get_shops()
                    printify_connected = bool(shops)
                except Exception as e:
                    logger.error(f"Failed to initialize Printify: {e}")
                    printify_connected = False
            else:
                printify_connected = False
        else:
            printify_connected = bool(st.session_state.printify_api)

        # Check YouTube - try to get it or check token file
        if "youtube_service" not in st.session_state or st.session_state.youtube_service is None:
            # Try to initialize from token.pickle
            if os.path.exists("token.pickle"):
                try:
                    from app.services.youtube_upload_service import YouTubeUploadService

                    st.session_state.youtube_service = YouTubeUploadService()
                    youtube_connected = st.session_state.youtube_service.is_authenticated
                except Exception as e:
                    logger.error(f"Failed to initialize YouTube: {e}")
                    youtube_connected = False
            else:
                youtube_connected = False
        else:
            youtube_connected = st.session_state.youtube_service and getattr(
                st.session_state.youtube_service, "authenticated", False
            )

        # Debug: Show connection status
        with st.expander("🔍 Debug: Connection Status", expanded=False):
            st.write("**Session State APIs:**")
            st.write(
                f"- Shopify API: {'✅ Connected' if shopify_connected else '❌ Not connected'}"
            )
            st.write(
                f"- Printify API: {'✅ Connected' if printify_connected else '❌ Not connected'}"
            )
            st.write(
                f"- YouTube Service: {'✅ Connected' if youtube_connected else '❌ Not connected'}"
            )

            st.write("\n**Environment Variables:**")
            st.write(
                f"- SHOPIFY_SHOP_URL: {'✅ Set' if os.getenv('SHOPIFY_SHOP_URL') else '❌ Not set'}"
            )
            st.write(
                f"- SHOPIFY_ACCESS_TOKEN: {'✅ Set' if os.getenv('SHOPIFY_ACCESS_TOKEN') else '❌ Not set'}"
            )
            st.write(
                f"- PRINTIFY_API_TOKEN: {'✅ Set' if os.getenv('PRINTIFY_API_TOKEN') else '❌ Not set'}"
            )
            st.write(
                f"- PRINTIFY_SHOP_ID: {'✅ Set' if os.getenv('PRINTIFY_SHOP_ID') else '❌ Not set'}"
            )
            st.write(
                f"- client_secret.json: {'✅ Exists' if os.path.exists('client_secret.json') else '❌ Not found'}"
            )
            st.write(
                f"- token.pickle: {'✅ Exists' if os.path.exists('token.pickle') else '❌ Not found'}"
            )

        # Fetch data from all platforms
        shopify_data = None
        printify_data = None
        youtube_data = None

        # Check if analytics jobs are running
        if "analytics_fetch_jobs" not in st.session_state:
            st.session_state.analytics_fetch_jobs = []

        if st.session_state.analytics_fetch_jobs:
            # Jobs already submitted, check progress
            from app.services.tab_job_helpers import (
                are_all_jobs_done,
                check_jobs_progress,
                collect_job_results,
            )

            job_ids = st.session_state.analytics_fetch_jobs
            progress = check_jobs_progress(job_ids)

            with st.spinner(
                f"⚡ Fetching analytics in parallel: {progress['completed']}/{len(job_ids)} complete..."
            ):
                if are_all_jobs_done(job_ids):
                    results = collect_job_results(job_ids)
                    shopify_data = results[0] if len(results) > 0 else None
                    printify_data = results[1] if len(results) > 1 else None
                    youtube_data = results[2] if len(results) > 2 else None
                    st.session_state.analytics_fetch_jobs = []
                else:
                    if st.button("🔄 Refresh Analytics", key="refresh_analytics"):
                        st.rerun()
                    st.stop()
        else:
            # Submit parallel fetch jobs
            from app.services.global_job_queue import JobType, get_global_job_queue

            queue = get_global_job_queue()
            job_ids = []

            # Job 1: Get Shopify data
            if shopify_connected and st.session_state.get("shopify_api"):
                _shopify_api = st.session_state.shopify_api

                def fetch_shopify(api=_shopify_api):
                    try:
                        return api.get_comprehensive_analytics()
                    except Exception as e:
                        logger.error(f"Shopify error: {e}")
                        return {"error": str(e)}

                job_ids.append(
                    queue.submit_job(
                        job_type=JobType.BATCH_OPERATION,
                        tab_name="Analytics",
                        description="Fetch Shopify Analytics",
                        function=fetch_shopify,
                        priority=7,
                    )
                )
            else:
                job_ids.append(None)  # Placeholder

            # Job 2: Get Printify data
            if printify_connected and st.session_state.get("printify_api"):
                _printify_api = st.session_state.printify_api

                def fetch_printify(api=_printify_api):
                    try:
                        shops = api.get_shops()
                        if shops:
                            shop_id = str(shops[0].get("id"))
                            products = api.get_shop_products(shop_id=shop_id, limit=50)
                            return {
                                "shop_count": len(shops),
                                "product_count": len(products),
                                "products": products,
                            }
                        return None
                    except Exception as e:
                        logger.error(f"Printify error: {e}")
                        return {"error": str(e)}

                job_ids.append(
                    queue.submit_job(
                        job_type=JobType.BATCH_OPERATION,
                        tab_name="Analytics",
                        description="Fetch Printify Data",
                        function=fetch_printify,
                        priority=7,
                    )
                )
            else:
                job_ids.append(None)

            # Job 3: Get YouTube data
            if youtube_connected and st.session_state.get("youtube_service"):
                _youtube_svc = st.session_state.youtube_service

                def fetch_youtube(yt=_youtube_svc):
                    try:
                        upload_history = yt.get_upload_history(limit=50)
                        if upload_history:
                            total_views = sum(v.get("view_count", 0) for v in upload_history)
                            total_likes = sum(v.get("like_count", 0) for v in upload_history)
                            return {
                                "video_count": len(upload_history),
                                "total_views": total_views,
                                "total_likes": total_likes,
                                "videos": upload_history,
                            }
                        return None
                    except Exception as e:
                        logger.error(f"YouTube error: {e}")
                        return {"error": str(e)}

                job_ids.append(
                    queue.submit_job(
                        job_type=JobType.BATCH_OPERATION,
                        tab_name="Analytics",
                        description="Fetch YouTube Stats",
                        function=fetch_youtube,
                        priority=7,
                    )
                )
            else:
                job_ids.append(None)

            # Filter out None placeholders
            st.session_state.analytics_fetch_jobs = [j for j in job_ids if j]

            if st.session_state.analytics_fetch_jobs:
                st.info(
                    f"⚡ Fetching analytics from {len(st.session_state.analytics_fetch_jobs)} sources in parallel..."
                )
                import time

                time.sleep(0.5)
                st.rerun()
            else:
                # No services connected
                pass

        # Display unified metrics
        st.markdown("#### 📈 Key Metrics")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if shopify_data and not shopify_data.get("error"):
                revenue = shopify_data.get("revenue", {}).get("recent_orders_total", 0)
                st.metric("💰 Shopify Revenue", f"${revenue:,.2f}")
            else:
                st.metric("💰 Shopify Revenue", "Not Connected", delta=None)

        with col2:
            if shopify_data and not shopify_data.get("error"):
                orders = shopify_data.get("orders", {}).get("total_count", 0)
                st.metric("📦 Total Orders", f"{orders:,}")
            else:
                st.metric("📦 Total Orders", "Not Connected", delta=None)

        with col3:
            if printify_data:
                products = printify_data.get("product_count", 0)
                st.metric("🎨 Printify Products", f"{products:,}")
            else:
                st.metric("🎨 Printify Products", "Not Connected", delta=None)

        with col4:
            if youtube_data:
                views = youtube_data.get("total_views", 0)
                st.metric("📺 YouTube Views", f"{views:,}")
            else:
                st.metric("📺 YouTube Views", "Not Connected", delta=None)

        st.markdown("---")

        # Second row of metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if shopify_data and not shopify_data.get("error"):
                products = shopify_data.get("products", {}).get("total_count", 0)
                st.metric("🛍️ Shopify Products", f"{products:,}")
            else:
                st.metric("🛍️ Shopify Products", "-")

        with col2:
            if shopify_data and not shopify_data.get("error"):
                customers = shopify_data.get("customers", {}).get("total_count", 0)
                st.metric("👥 Customers", f"{customers:,}")
            else:
                st.metric("👥 Customers", "-")

        with col3:
            if printify_data:
                shops = printify_data.get("shop_count", 0)
                st.metric("🏪 Printify Shops", f"{shops:,}")
            else:
                st.metric("🏪 Printify Shops", "-")

        with col4:
            if youtube_data:
                videos = youtube_data.get("video_count", 0)
                st.metric("🎬 YouTube Videos", f"{videos:,}")
            else:
                st.metric("🎬 YouTube Videos", "-")

        st.markdown("---")

        # Platform status
        st.markdown("#### 🔌 Platform Connections")

        col1, col2, col3 = st.columns(3)

        with col1:
            if shopify_connected and shopify_data and not shopify_data.get("error"):
                shop_name = shopify_data.get("shop", {}).get("name", "Unknown")
                st.success(f"✅ Shopify: {shop_name}")
                st.caption("Publishing blogs successfully")
            elif shopify_connected:
                st.success("✅ Shopify: Connected")
                st.caption("Credentials configured, ready to publish")
            else:
                st.error("❌ Shopify: Not Connected")
                st.caption("Add to .env: SHOPIFY_SHOP_URL, SHOPIFY_ACCESS_TOKEN")

        with col2:
            if printify_connected and printify_data:
                st.success(f"✅ Printify: {printify_data.get('product_count', 0)} products")
                st.caption("Ready to create products")
            elif printify_connected:
                st.success("✅ Printify: Connected")
                st.caption("API token configured")
            else:
                st.error("❌ Printify: Not Connected")
                st.caption("Add to .env: PRINTIFY_API_TOKEN, PRINTIFY_SHOP_ID")

        with col3:
            if youtube_connected and youtube_data:
                st.success(f"✅ YouTube: {youtube_data.get('video_count', 0)} videos")
                st.caption("Uploading videos successfully")
            elif youtube_connected:
                st.success("✅ YouTube: Authenticated")
                st.caption("OAuth token valid, ready to upload")
            else:
                st.error("❌ YouTube: Not Connected")
                st.caption("Add client_secret.json and authenticate")

    # ========================================
    # SHOPIFY TAB
    # ========================================
    with analytics_tabs[1]:
        st.markdown("#### 🛍️ Shopify Store Analytics")

        if not st.session_state.shopify_api:
            st.warning("⚠️ Shopify not connected")
            st.info(
                "Configure Shopify credentials in **Settings → Integrations** to see live analytics"
            )
            st.code(
                "SHOPIFY_SHOP_URL=yourstore.myshopify.com\nSHOPIFY_ACCESS_TOKEN=shpat_xxxxx",
                language="bash",
            )
        else:
            try:
                with st.spinner("Loading Shopify analytics..."):
                    analytics = st.session_state.shopify_api.get_comprehensive_analytics()

                if analytics.get("error"):
                    st.error(f"❌ Failed to load Shopify data: {analytics['error']}")
                else:
                    # Shop info
                    shop = analytics.get("shop", {})
                    st.markdown(f"### 🏪 {shop.get('name', 'Your Store')}")
                    st.caption(
                        f"Domain: {shop.get('domain', 'N/A')} • Currency: {shop.get('currency', 'USD')}"
                    )

                    # Key metrics
                    col1, col2, col3, col4 = st.columns(4)

                    products = analytics.get("products", {})
                    orders = analytics.get("orders", {})
                    customers = analytics.get("customers", {})
                    revenue = analytics.get("revenue", {})

                    with col1:
                        st.metric("📦 Products", f"{products.get('total_count', 0):,}")
                    with col2:
                        st.metric("🛒 Total Orders", f"{orders.get('total_count', 0):,}")
                    with col3:
                        st.metric("👥 Customers", f"{customers.get('total_count', 0):,}")
                    with col4:
                        st.metric("💰 Revenue", f"${revenue.get('recent_orders_total', 0):,.2f}")

                    st.markdown("---")

                    # Order breakdown
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📂 Open Orders", orders.get("open_count", 0))
                    with col2:
                        st.metric("✅ Fulfilled", orders.get("closed_count", 0))
                    with col3:
                        collections = analytics.get("collections", {})
                        st.metric("📚 Collections", collections.get("total_count", 0))

                    # Top products
                    st.markdown("---")
                    st.markdown("#### 🔥 Top Selling Products (Last 30 Days)")

                    top_products = analytics.get("top_products", [])
                    if top_products:
                        for i, product in enumerate(top_products[:5], 1):
                            col1, col2, col3 = st.columns([3, 1, 1])
                            with col1:
                                st.markdown(f"**{i}. {product.get('title', 'Unknown')}**")
                            with col2:
                                st.markdown(f"Sold: **{product.get('quantity_sold', 0)}**")
                            with col3:
                                st.markdown(f"Revenue: **${product.get('revenue', 0):,.2f}**")
                    else:
                        st.info("No sales data available for the last 30 days")

                    # Quick actions
                    st.markdown("---")
                    st.markdown("#### 💬 Quick Actions")
                    st.info(
                        "Ask the Chat Assistant for detailed analytics:\n- 'Show me recent orders'\n- 'What are my best sellers?'\n- 'How many customers do I have?'"
                    )

            except Exception as e:
                st.error(f"❌ Error loading Shopify analytics: {e}")
                st.exception(e)

    # ========================================
    # PRINTIFY TAB
    # ========================================
    with analytics_tabs[2]:
        st.markdown("#### 📦 Printify Product Analytics")

        if not st.session_state.printify_api:
            st.warning("⚠️ Printify not connected")
            st.info("Add your Printify API token in **Settings → API Keys** to see product data")
            st.code(
                "PRINTIFY_API_TOKEN=your_token_here\nPRINTIFY_SHOP_ID=your_shop_id", language="bash"
            )
        else:
            try:
                with st.spinner("Loading Printify products..."):
                    from app.services.api_service import PrintifyAPI

                    api = st.session_state.printify_api

                    # Get shops
                    shops = api.get_shops()

                    if not shops:
                        st.warning("No Printify shops found")
                    else:
                        # Shop selector if multiple
                        if len(shops) > 1:
                            shop_names = [
                                f"{s.get('title', 'Unknown')} (ID: {s.get('id')})" for s in shops
                            ]
                            selected_shop_idx = st.selectbox(
                                "Select Shop",
                                range(len(shops)),
                                format_func=lambda i: shop_names[i],
                            )
                            shop = shops[selected_shop_idx]
                        else:
                            shop = shops[0]

                        shop_id = shop.get("id")
                        shop_title = shop.get("title", "Unknown")

                        st.markdown(f"### 🏪 {shop_title}")

                        # Get products
                        products = api.get_shop_products(shop_id=shop_id, limit=50)

                        # Metrics
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.metric(" Total Products", len(products))

                        with col2:
                            published = sum(1 for p in products if not p.get("is_deleted", False))
                            st.metric("✅ Published", published)

                        with col3:
                            # Count variants
                            total_variants = sum(len(p.get("variants", [])) for p in products)
                            st.metric("🎨 Total Variants", total_variants)

                        with col4:
                            # Count with mockups
                            with_images = sum(1 for p in products if p.get("images", []))
                            st.metric("📸 With Images", with_images)

                        st.markdown("---")

                        # Products list
                        st.markdown("#### 📋 Product Catalog")

                        if products:
                            # Search and filter
                            search = st.text_input("🔍 Search products", key="printify_search")

                            filtered_products = (
                                [
                                    p
                                    for p in products
                                    if search.lower() in p.get("title", "").lower()
                                ]
                                if search
                                else products
                            )

                            st.markdown(f"Showing {len(filtered_products)} products")

                            # Display products
                            for product in filtered_products[:20]:  # Limit to 20 for performance
                                with st.expander(f"📦 {product.get('title', 'Untitled Product')}"):
                                    col1, col2 = st.columns([1, 2])

                                    with col1:
                                        images = product.get("images", [])
                                        if images:
                                            st.image(images[0].get("src"), use_container_width=True)
                                        else:
                                            st.info("No image")

                                    with col2:
                                        st.markdown(f"**Product ID:** `{product.get('id')}`")
                                        st.markdown(
                                            f"**Blueprint:** {product.get('blueprint_id', 'N/A')}"
                                        )
                                        st.markdown(
                                            f"**Variants:** {len(product.get('variants', []))}"
                                        )
                                        st.markdown(
                                            f"**Created:** {product.get('created_at', 'N/A')[:10]}"
                                        )

                                        tags = product.get("tags", [])
                                        if tags:
                                            st.markdown(f"**Tags:** {', '.join(tags)}")
                        else:
                            st.info("No products found in this shop")

                        # Quick actions
                        st.markdown("---")
                        st.markdown("#### 💡 Quick Actions")
                        st.info(
                            "Generate products in **Product Studio** tab or **Campaign Creator**"
                        )

            except Exception as e:
                st.error(f"❌ Error loading Printify data: {e}")
                st.exception(e)

    # ========================================
    # YOUTUBE TAB
    # ========================================
    with analytics_tabs[3]:
        st.markdown("#### 📺 YouTube Channel Analytics")

        if not st.session_state.youtube_service:
            st.warning("⚠️ YouTube not connected")
            st.info("Configure YouTube OAuth in **Settings → YouTube** to see video analytics")
            st.markdown("**Steps:**")
            st.markdown("1. Download `client_secret.json` from Google Cloud Console")
            st.markdown("2. Place it in the project root directory")
            st.markdown("3. Authenticate via Settings → YouTube")
        else:
            try:
                with st.spinner("Loading YouTube analytics..."):
                    from app.services.youtube_upload_service import YouTubeUploadService

                    yt = st.session_state.youtube_service

                    # Check authentication
                    creds_status = yt.check_credentials()

                    if not creds_status["authenticated"]:
                        st.error("❌ YouTube not authenticated")
                        st.info("Go to Settings → YouTube to authenticate")
                    else:
                        # Get upload history
                        videos = yt.get_upload_history(limit=50)

                        if not videos:
                            st.info("No videos uploaded yet")
                            st.markdown("Upload your first video in **Video Producer** tab")
                        else:
                            # Calculate metrics
                            total_views = sum(v.get("view_count", 0) for v in videos)
                            total_likes = sum(v.get("like_count", 0) for v in videos)
                            total_comments = sum(v.get("comment_count", 0) for v in videos)

                            # Metrics
                            col1, col2, col3, col4 = st.columns(4)

                            with col1:
                                st.metric("🎬 Videos", len(videos))
                            with col2:
                                st.metric("👀 Total Views", f"{total_views:,}")
                            with col3:
                                st.metric("👍 Total Likes", f"{total_likes:,}")
                            with col4:
                                st.metric("💬 Comments", f"{total_comments:,}")

                            st.markdown("---")

                            # Video list
                            st.markdown("#### 📹 Recent Videos")

                            for video in videos[:10]:  # Show recent 10
                                with st.expander(f"🎥 {video.get('title', 'Untitled')}"):
                                    col1, col2 = st.columns([1, 2])

                                    with col1:
                                        if video.get("thumbnail_url"):
                                            st.image(
                                                video["thumbnail_url"], use_container_width=True
                                            )

                                    with col2:
                                        st.markdown(f"**Video ID:** `{video.get('id')}`")
                                        st.markdown(
                                            f"**Published:** {video.get('published_at', 'N/A')[:10]}"
                                        )
                                        st.markdown(f"**Views:** {video.get('view_count', 0):,}")
                                        st.markdown(f"**Likes:** {video.get('like_count', 0):,}")
                                        st.markdown(
                                            f"**Comments:** {video.get('comment_count', 0):,}"
                                        )

                                        video_url = (
                                            f"https://www.youtube.com/watch?v={video.get('id')}"
                                        )
                                        st.markdown(f"[🔗 Watch on YouTube]({video_url})")

                            # Quick actions
                            st.markdown("---")
                            st.markdown("#### 💡 Quick Actions")
                            st.info("Create and upload videos in **Video Producer** tab")

            except Exception as e:
                st.error(f"❌ Error loading YouTube data: {e}")
                st.exception(e)

    # ========================================
    # TWITTER TAB
    # ========================================
    with analytics_tabs[4]:
        st.markdown("#### 🐦 Twitter Analytics & Post History")

        # Check Twitter credentials
        twitter_username = os.getenv("TWITTER_USERNAME")
        twitter_password = os.getenv("TWITTER_PASSWORD")

        if not twitter_username or not twitter_password:
            st.warning("⚠️ Twitter credentials not configured")
            st.info("Add your Twitter credentials in **Settings → Integrations**")
            st.markdown("**Required in .env:**")
            st.code(
                """
TWITTER_USERNAME=your_username
TWITTER_PASSWORD=your_password
            """
            )
        else:
            st.success(f"✅ Connected as: @{twitter_username}")

            # Twitter posting history from campaign results
            if "campaign_history" in st.session_state and st.session_state.campaign_history:
                # Extract Twitter posts from campaigns
                all_twitter_posts = []

                for campaign in st.session_state.campaign_history:
                    campaign_results = campaign.get("results", {})
                    twitter_posts = campaign_results.get("twitter_posts", [])

                    for post in twitter_posts:
                        post_info = {
                            "campaign": campaign.get("concept", "Unknown")[:50],
                            "timestamp": campaign.get("timestamp", "N/A"),
                            "image": post.get("image"),
                            "caption": post.get("caption", ""),
                            "status": post.get("status", "unknown"),
                        }
                        all_twitter_posts.append(post_info)

                if all_twitter_posts:
                    # Metrics
                    total_posts = len(all_twitter_posts)
                    successful_posts = sum(1 for p in all_twitter_posts if p["status"] == "success")
                    failed_posts = sum(1 for p in all_twitter_posts if p["status"] != "success")
                    success_rate = (successful_posts / total_posts * 100) if total_posts > 0 else 0

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("📤 Total Posts", total_posts)
                    with col2:
                        st.metric("✅ Successful", successful_posts)
                    with col3:
                        st.metric("❌ Failed", failed_posts)
                    with col4:
                        st.metric("📊 Success Rate", f"{success_rate:.1f}%")

                    st.markdown("---")

                    # Post history
                    st.markdown("#### 📋 Post History")

                    for post in all_twitter_posts[:20]:  # Show last 20
                        with st.expander(
                            f"{'✅' if post['status'] == 'success' else '❌'} {post['campaign']} - {post['timestamp']}"
                        ):
                            col1, col2 = st.columns([1, 2])

                            with col1:
                                if post["image"] and os.path.exists(post["image"]):
                                    st.image(post["image"], use_container_width=True)
                                else:
                                    st.info("Image not found")

                            with col2:
                                st.markdown("**Caption:**")
                                st.text(post["caption"])
                                st.markdown(f"**Status:** {post['status'].upper()}")
                                st.markdown(f"**Campaign:** {post['campaign']}")
                else:
                    st.info("No Twitter posts yet")
                    st.markdown("**Enable Twitter auto-posting:**")
                    st.markdown("1. Go to **Autonomous Campaign** tab")
                    st.markdown("2. Check **🐦 Auto-Post to Twitter** under Marketing Automation")
                    st.markdown("3. Generate a campaign")
            else:
                st.info("No campaign data available")
                st.markdown("Create your first campaign with Twitter auto-posting enabled!")

            st.markdown("---")

            # Twitter account status
            st.markdown("#### 🔧 Account Status")

            with st.expander("📊 Current Configuration"):
                st.markdown(f"**Username:** @{twitter_username}")
                st.markdown(f"**Password:** {'•' * len(twitter_password)}")
                st.markdown(f"**Shop URL:** {os.getenv('SHOPIFY_SHOP_URL', 'Not configured')}")

                st.markdown("**⚠️ Known Issue:**")
                st.warning(
                    "Twitter may show 'Could not log you in now' error if account needs verification. Check terminal logs for details."
                )

                st.markdown("**💡 Troubleshooting:**")
                st.markdown("1. Verify your Twitter account via email/phone")
                st.markdown("2. Check that credentials are correct in .env")
                st.markdown("3. Try logging in manually at twitter.com first")
                st.markdown("4. Watch terminal logs when posting to see exact error")
