from app.tabs.abp_imports_common import (
    st, time, datetime, Path, json, os, setup_logger
)

# Maintain backward compatibility alias
dt = datetime
logger = setup_logger(__name__)

def render_campaign_complete_summary(
    results,
    campaign_dir,
    total_time,
    num_products,
    concept_input,
    target_audience,
    price_range,
    fast_mode,
    campaign_enabled,
    product_enabled,
    blog_enabled,
    video_enabled,
    social_enabled,
    cross_page_mgr,
    save_campaign_metadata_func,
    progress_bar=None,
    status_text=None,
    elapsed_display=None,
    eta_display=None
):
    """
    Renders the summary and results after a campaign generation is complete.
    """
    
    if progress_bar:
        progress_bar.progress(1.0)
    if status_text:
        status_text.markdown("**✅ Campaign Generation Complete!**")
    if elapsed_display:
        elapsed_display.markdown(f"⏱️ **{total_time:.0f}s total**")
    if eta_display:
        eta_display.markdown("🎉 **Done!**")

    st.markdown("---")
    
    # Performance summary
    perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)
    with perf_col1:
        st.metric("⏱️ Total Time", f"{total_time:.0f}s")
    with perf_col2:
        successful_products = len([p for p in results.get('products', []) if p.get('status') == 'created'])
        st.metric("📦 Products", f"{successful_products}/{num_products}")
    with perf_col3:
        st.metric("🎬 Videos", len(results.get('videos', [])))
    with perf_col4:
        mode_label = "⚡ Fast" if results.get('fast_mode') else "✨ Quality"
        st.metric("Mode", mode_label)
    
    st.success("🎉 Campaign generation complete!")
    st.session_state.generated_assets.setdefault('campaigns', []).append(str(campaign_dir))
    
    # Store in session for future reference
    st.session_state['last_campaign_results'] = results
    st.session_state['last_campaign_dir'] = str(campaign_dir)
    
    # Update cross-page state with completion
    if 'active_campaign' in st.session_state:
        st.session_state['active_campaign'].update({
            'status': 'completed',
            'current_step': st.session_state['active_campaign'].get('total_steps', 10), # Fallback
            'progress_message': 'Campaign Complete!',
            'elapsed_seconds': total_time,
            'campaign_dir': str(campaign_dir),
            'results_summary': {
                'products_count': len(results.get('products', [])),
                'products_successful': successful_products,
                'blog_posts_count': len(results.get('blog_posts', [])),
                'videos_count': len(results.get('videos', [])),
                'social_platforms': list(results.get('social_media_images', {}).keys()) if results.get('social_media_images') else []
            }
        })
        if cross_page_mgr:
            cross_page_mgr.save_page_state("main_dashboard", st.session_state['active_campaign'])

    campaign_metadata = {
        'concept': concept_input,
        'target_audience': target_audience,
        'price_range': price_range,
        'timestamp': dt.now().isoformat(),
        'generation_time_seconds': total_time,
        'fast_mode': fast_mode,
        'workflows_enabled': {
            'campaign_strategy': campaign_enabled,
            'products': product_enabled,
            'blog': blog_enabled,
            'video': video_enabled,
            'social': social_enabled
        },
        'results': {
            'products_count': len(results.get('products', [])),
            'products_successful': successful_products,
            'blog_posts_count': len(results.get('blog_posts', [])),
            'videos_count': len(results.get('videos', [])),
            'social_platforms': list(results.get('social_media_images', {}).keys()) if results.get('social_media_images') else []
        }
    }
    
    if save_campaign_metadata_func:
        save_campaign_metadata_func(campaign_dir, campaign_metadata)

    st.balloons()

    # Enhanced Summary with Quick Actions
    st.markdown("### ✅ Campaign Summary")
    
    # Count enhanced assets
    static_ads_count = len(results.get('social_ads', []))
    video_ads_count = len(results.get('social_video_ads', []))
    bonus_video_count = sum(1 for v in results.get('videos', []) if v.get('type') == 'product_video_ads')
    
    # Visual summary cards
    summary_col1, summary_col2 = st.columns(2)
    
    with summary_col1:
        st.markdown("#### 📊 Generated Assets")
        assets_data = {
            "📦 Products": successful_products,
            "📰 Blog Posts": len(results.get('blog_posts', [])),
            "🎬 Videos": len(results.get('videos', [])),
            "📱 Social Posts": len(results.get('social_posts', [])),
            "📸 Static Ads": static_ads_count,
        }
        for asset_name, count in assets_data.items():
            if count > 0:
                st.markdown(f"- {asset_name}: **{count}** ✅")
    
    with summary_col2:
        st.markdown("#### 🚀 Published To")
        published = []
        if results.get('shopify_blog_url'):
            published.append(f"📰 Shopify Blog: [View]({results['shopify_blog_url']})")
        if results.get('youtube_video_id'):
            published.append(f"🎬 YouTube: [Watch](https://youtube.com/watch?v={results['youtube_video_id']})")
        if results.get('twitter_posts'):
            success_count = sum(1 for t in results['twitter_posts'] if t.get('status') == 'success')
            published.append(f"🐦 Twitter: {success_count} posts")
        if results.get('multi_platform_posts'):
            mp_results = results['multi_platform_posts']
            if mp_results.get('instagram', {}).get('status') == 'success':
                published.append("📸 Instagram: Posted")
            if mp_results.get('facebook', {}).get('status') == 'success':
                published.append("👥 Facebook: Posted")
            if mp_results.get('tiktok', {}).get('status') == 'success':
                published.append("🎵 TikTok: Posted")
            if mp_results.get('pinterest', {}).get('status') == 'success':
                published.append("📌 Pinterest: Pinned")
            reddit_posts = [k for k, v in mp_results.items() if k.startswith('reddit_') and v.get('status') == 'success']
            if reddit_posts:
                published.append(f"🤖 Reddit: {len(reddit_posts)} posts")
        if any(p.get('printify_id') for p in results.get('products', [])):
            published.append("📦 Printify: Products created")
        if results.get('digital_products'):
            dp_count = len(results['digital_products'])
            published.append(f"💾 Digital Products: {dp_count} listed")
        
        if published:
            for pub in published:
                st.markdown(f"- {pub}")
        else:
            st.info("No auto-publishing was enabled")
    
    # Quick Actions
    st.markdown("---")
    st.markdown("#### ⚡ Quick Actions")
    qa_col1, qa_col2, qa_col3, qa_col4 = st.columns(4)
    
    with qa_col1:
        if st.button("📂 Open Campaign Folder", key="open_campaign_folder"):
            import subprocess
            try:
                subprocess.run(['open', str(campaign_dir)])
            except Exception as e:
                st.error(f"Could not open folder: {e}")
    
    with qa_col2:
        # Create combined ZIP of all assets
        if st.button("📥 Download All", key="download_all_assets"):
            with st.spinner("Creating ZIP archive..."):
                try:
                    import zipfile
                    import io
                    
                    # Create in-memory ZIP file
                    zip_buffer = io.BytesIO()
                    
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        # Walk through the campaign directory
                        if campaign_dir.exists():
                            for file_path in campaign_dir.rglob('*'):
                                if file_path.is_file():
                                    # Get relative path for the archive
                                    arcname = file_path.relative_to(campaign_dir)
                                    zip_file.write(file_path, arcname)
                        
                        # Also add any generated images from session state
                        if results.get('products'):
                            for idx, prod in enumerate(results['products']):
                                if prod.get('local_path') and Path(prod['local_path']).exists():
                                    zip_file.write(prod['local_path'], f"products/product_{idx+1}.png")
                        
                        # Add blog images
                        if results.get('blog_posts'):
                            for idx, blog in enumerate(results['blog_posts']):
                                if blog.get('image_path') and Path(blog['image_path']).exists():
                                    zip_file.write(blog['image_path'], f"blog_posts/blog_{idx+1}_image.png")
                    
                    zip_buffer.seek(0)
                    
                    st.download_button(
                        label="💾 Save ZIP File",
                        data=zip_buffer.getvalue(),
                        file_name=f"campaign_{campaign_dir.name}_{dt.now().strftime('%Y%m%d')}.zip",
                        mime="application/zip",
                        key="download_zip_file"
                    )
                    st.success(f"✅ ZIP archive created!")
                except Exception as e:
                    st.error(f"Error creating ZIP: {e}")
    
    with qa_col3:
        if st.button("🔄 Run Again", key="run_again"):
            st.rerun()
    
    with qa_col4:
        if st.button("📊 View Analytics", key="view_analytics"):
            st.session_state.selected_tab = 7  # Analytics tab

    with st.expander("📂 View Generated Files"):
        st.code(
            f"Campaign Directory: {campaign_dir}/\n"
            f"├── campaign_metadata.json\n"
            f"├── campaign_strategy.txt {f'✅' if campaign_enabled else ''}\n"
            f"├── products/\n"
            f"│   └── {successful_products} product images\n"
            f"├── blog_posts/\n"
            f"│   └── {len(results.get('blog_posts', []))} blog posts + images\n"
            f"├── videos/\n"
            f"│   ├── video_script.txt\n"
            f"│   ├── promo_video.mp4 {f'✅' if results.get('videos') else '⏳'}\n"
            f"│   └── {bonus_video_count} bonus product video ads 🎬\n"
            f"└── social_media/\n"
            f"    ├── {len(results.get('social_posts', []))} platform post files\n"
            f"    ├── {static_ads_count} professional static ads 📸\n"
            f"    └── {video_ads_count} animated video ads 🎥\n",
            language=""
        )

    summary_entry = {
        'concept': concept_input,
        'timestamp': dt.now().strftime("%Y-%m-%d %H:%M"),
        'generation_time': f"{total_time:.0f}s",
        'products': successful_products,
        'blogs': len([b for b in results.get('blog_posts', []) if 'content' in b or 'html' in b]),
        'video': bool(results.get('videos')),
        'social': bool(results.get('social_posts')),
        'campaign_dir': str(campaign_dir),
        'results': results,
    }

    st.session_state.current_campaign = summary_entry
    st.session_state.campaign_history.append(summary_entry)
