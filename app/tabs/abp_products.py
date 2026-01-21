import streamlit as st
import os
from pathlib import Path
from datetime import datetime as dt
import requests
import json

from cross_page_state import restore_page_to_session
from platform_helpers import (
    _render_printify_product_config,
    _ensure_replicate_client,
    _get_replicate_token,
    _slugify,
    _printify_selection_ready,
    _send_design_to_printify
)
from platform_integrations import tracked_replicate_run
from tab_job_helpers import (
    submit_batch_product_designs,
    collect_job_results,
    check_jobs_progress,
    are_all_jobs_done
)
from global_job_queue import JobType

# Style and color prompts for Product Studio
STYLE_PROMPTS = {
    "Minimalist": "clean, simple, minimal design, modern aesthetic, white space",
    "Vintage": "retro, vintage style, aged look, classic design, nostalgic",
    "Abstract": "abstract art, geometric patterns, modern art style, artistic",
    "Watercolor": "watercolor painting, soft artistic style, dreamy",
    "Bold & Graphic": "bold graphics, strong lines, pop art style, eye-catching",
    "Hand-drawn": "hand-drawn illustration, sketch style, artistic feel",
    "Photography": "professional product photography, realistic, high quality",
    "3D Render": "3D rendered, digital art, modern CGI style, dimensional",
    "Cyberpunk": "cyberpunk aesthetic, neon lights, futuristic, tech noir",
    "Kawaii": "cute kawaii style, adorable, japanese illustration, chibi",
    "Gothic": "dark gothic style, dramatic, mysterious, elegant darkness",
    "Boho": "bohemian style, free spirit, earthy, organic patterns",
    "Art Deco": "art deco style, 1920s glamour, geometric elegance, golden age",
    "Vaporwave": "vaporwave aesthetic, retro 80s, synthwave, nostalgic digital",
    "Line Art": "clean line art, elegant strokes, modern illustration",
    "Graffiti": "street art style, urban graffiti, bold expression"
}

COLOR_PROMPTS = {
    "Vibrant": "vibrant colors, bold color palette, saturated, energetic",
    "Pastel": "soft pastel colors, gentle tones, dreamy palette",
    "Monochrome": "black and white, grayscale, minimalist palette, elegant",
    "Earth Tones": "natural earth tones, browns and greens, organic",
    "Neon": "neon colors, bright glowing effects, electric",
    "Jewel Tones": "rich jewel tones, deep colors, luxurious",
    "Neutral": "neutral colors, beige, cream, soft palette, understated",
    "Sunset": "warm sunset colors, orange, pink, golden hour palette",
    "Ocean": "ocean blues and teals, aquatic palette, serene",
    "Forest": "deep forest greens, natural woodland palette, organic",
    "Candy": "bright candy colors, playful, fun and sweet palette",
    "Metallic": "metallic sheen, gold, silver, bronze accents, luxe"
}

# AI-powered design enhancement prompts
DESIGN_ENHANCERS = {
    "Print-Ready": "high resolution, clean edges, suitable for printing, sharp details",
    "Transparent BG": "isolated design, transparent background ready, clean cutout",
    "Seamless Tile": "seamless pattern, tileable design, repeating pattern",
    "T-Shirt Ready": "centered composition, t-shirt print design, wearable art",
    "Poster Ready": "vertical composition, poster-worthy, wall art quality",
    "Logo Style": "logo design, brandable, scalable vector style, iconic"
}

def render_product_studio_tab():
    # Restore any saved Product Studio state
    restore_page_to_session("product_studio", keys_to_restore=[
        'product_studio_results', 'product_studio_design_prompt', 
        'product_studio_style', 'product_studio_color_scheme'
    ])
    
    st.markdown("### 🎨 AI Design Studio")
    st.markdown("Generate print-ready artwork designs. These designs can then be sent to Printify to print on products.")

    col1, col2 = st.columns([1.1, 0.9])

    with col1:
        st.markdown("#### Design Parameters")

        design_prompt = st.text_area(
            "Design Description",
            placeholder="e.g., Minimalist mountain landscape logo, Retro 80s geometric pattern, Cute kawaii cat illustration",
            height=120,
            help="Describe the design/artwork itself - NOT a product mockup. AI will generate just the design."
        )
        
        # AI Prompt Enhancement
        ai_enhance_col1, ai_enhance_col2 = st.columns([1, 1])
        with ai_enhance_col1:
            if st.button("✨ AI Enhance Prompt", use_container_width=True, help="Let AI improve your design description"):
                if design_prompt.strip():
                    try:
                        replicate_token = _get_replicate_token()
                    except ValueError:
                        replicate_token = None
                    if replicate_token:
                        with st.spinner("🧠 Enhancing your prompt..."):
                            try:
                                import replicate
                                client = replicate.Client(api_token=replicate_token)
                                enhance_prompt = f"""You are an expert graphic designer. Enhance this design prompt to create better AI-generated artwork:

Original: {design_prompt}

Make it more detailed and specific for print-on-demand products. Add:
- Specific artistic elements
- Composition details
- Mood/atmosphere
- Technical quality terms

Return ONLY the enhanced prompt, nothing else. Keep under 100 words."""
                                response = tracked_replicate_run(client, "meta/meta-llama-3-8b-instruct", {"prompt": enhance_prompt, "max_tokens": 150}, operation_name="Design Prompt Enhancement")
                                enhanced = "".join(response).strip() if isinstance(response, list) else response
                                st.session_state['enhanced_design_prompt'] = enhanced
                            except Exception as e:
                                st.error(f"Enhancement failed: {e}")
                    else:
                        st.warning("Add API key in Settings or set REPLICATE_API_TOKEN environment variable")
                else:
                    st.warning("Enter a prompt first")
        
        with ai_enhance_col2:
            if st.button("🎲 Random Trending Idea", use_container_width=True, help="Get AI-generated trending design ideas"):
                try:
                    replicate_token = _get_replicate_token()
                except ValueError:
                    replicate_token = None
                if replicate_token:
                    with st.spinner("🔥 Finding trending ideas..."):
                        try:
                            import replicate
                            client = replicate.Client(api_token=replicate_token)
                            trending_prompt = """Generate ONE unique, trending design idea for print-on-demand products in 2024.
Consider: current pop culture, memes, aesthetic trends, seasonal themes.
Be specific and visual. Format: Just the design concept in 20 words or less."""
                            response = tracked_replicate_run(client, "meta/meta-llama-3-8b-instruct", {"prompt": trending_prompt, "max_tokens": 50}, operation_name="Trending Design Ideas")
                            idea = "".join(response).strip() if isinstance(response, list) else response
                            st.session_state['enhanced_design_prompt'] = idea
                        except Exception as e:
                            st.error(f"Failed: {e}")
                else:
                    st.warning("Add API key in Settings or set REPLICATE_API_TOKEN environment variable")
        
        # Show enhanced prompt if available
        if st.session_state.get('enhanced_design_prompt'):
            st.info(f"✨ **Enhanced:** {st.session_state['enhanced_design_prompt']}")
            if st.button("📋 Use This Prompt", use_container_width=True):
                st.session_state['use_enhanced_prompt'] = True
                st.rerun()
        
        # Design enhancer selection
        design_enhancer = st.selectbox("🎯 Design Output Type", ["None"] + list(DESIGN_ENHANCERS.keys()),
                                        help="Optimize the design for specific use cases")

        style = st.selectbox("Art Style", list(STYLE_PROMPTS.keys()))
        color_scheme = st.selectbox("Color Palette", list(COLOR_PROMPTS.keys()))
        variation_count = st.slider("Design Variations", min_value=1, max_value=4, value=2)

        aspect_choice = st.selectbox(
            "Aspect Ratio",
            [
                "Square (1:1)",
                "Portrait (4:5)",
                "Portrait Tall (3:4)",
                "Landscape (16:9)"
            ],
            index=0
        )

        ratio_map = {
            "Square (1:1)": (1024, 1024, "1:1"),
            "Portrait (4:5)": (1024, 1280, "4:5"),
            "Portrait Tall (3:4)": (960, 1280, "3:4"),
            "Landscape (16:9)": (1280, 720, "16:9")
        }
        width, height, aspect_ratio = ratio_map[aspect_choice]

        st.markdown("---")
        printify_config, printify_ready, printify_api_client = _render_printify_product_config(
            "Printify Product Target",
            config_key="product_studio_printify_config",
            allow_auto_toggle=True,
            instructions="Choose the blueprint, provider, and variants you'll send each generated design to."
        )

        generate_designs = st.button("🎨 Generate Designs", use_container_width=True)

    with col2:
        st.markdown("#### Latest Output")
        latest_results = st.session_state.product_studio_results
        if latest_results:
            latest = latest_results[0]
            st.caption(
                f"{latest['timestamp']} • {latest['style']} • {latest['color_scheme']}"
            )
            for idx, variation in enumerate(latest['variations'], start=1):
                st.image(variation['image_path'], caption=f"Variation {idx}")
                with st.expander(f"Prompt {idx}", expanded=False):
                    st.code(variation['prompt'])
                with open(variation['image_path'], "rb") as img_file:
                    st.download_button(
                        f"Download Variation {idx}",
                        data=img_file.read(),
                        file_name=Path(variation['image_path']).name,
                        mime="image/png",
                        key=f"design_studio_download_{latest['timestamp']}_{idx}"
                    )
            st.markdown(f"Saved to `{latest['output_dir']}`")
        else:
            st.info("Run the generator to see your generated designs here.")

    if generate_designs:
        if not design_prompt.strip():
            st.warning("Describe the concept so the AI knows what to create.")
        else:
            try:
                replicate_api, _ = _ensure_replicate_client()
            except ValueError as exc:
                st.error(str(exc))
            else:
                run_root = Path("campaigns") / "design_studio"
                run_root.mkdir(parents=True, exist_ok=True)
                timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
                slug = _slugify(design_prompt[:50])
                session_dir = run_root / f"{timestamp}_{slug}"
                session_dir.mkdir(parents=True, exist_ok=True)

                # Use enhanced prompt if available and selected
                if st.session_state.get('use_enhanced_prompt') and st.session_state.get('enhanced_design_prompt'):
                    base_prompt = st.session_state['enhanced_design_prompt']
                    st.session_state['use_enhanced_prompt'] = False
                    st.info(f"✨ Using enhanced prompt: {base_prompt[:100]}...")
                else:
                    base_prompt = design_prompt.strip()

                st.markdown("---")
                st.markdown("#### Generation Progress")

                # Build all prompts first
                all_prompts = []
                for idx in range(variation_count):
                    prompt_parts = [
                        base_prompt,
                        STYLE_PROMPTS.get(style, ""),
                        COLOR_PROMPTS.get(color_scheme, ""),
                    ]
                    # Add design enhancer if selected
                    if design_enhancer and design_enhancer != "None":
                        prompt_parts.append(DESIGN_ENHANCERS.get(design_enhancer, ""))
                    else:
                        prompt_parts.append("design artwork, isolated on white background, clean edges")
                    prompt_parts.append("professional graphic design, print-ready, high detail, commercial quality")
                    prompt_parts.append(f"creative variation {idx + 1}")
                    final_prompt = ", ".join(filter(None, prompt_parts))
                    all_prompts.append(final_prompt)

                # Submit all jobs to queue in parallel
                st.info(f"🚀 Submitting {variation_count} designs to job queue for parallel execution...")
                
                # Get advanced image parameters
                advanced_model_params = st.session_state.get('advanced_model_params', {})
                img_params = advanced_model_params.get("image", {})
                
                # Submit batch jobs
                from global_job_queue import get_global_job_queue
                queue = get_global_job_queue()
                
                job_ids = []
                for idx, prompt in enumerate(all_prompts):
                    def generate_single_design(prompt=prompt, idx=idx):
                        image_url = replicate_api.generate_image(
                            prompt,
                            width=width,
                            height=height,
                            aspect_ratio=aspect_ratio,
                            output_format=img_params.get("output_format", "png"),
                            output_quality=img_params.get("output_quality", 90),
                            guidance_scale=img_params.get("guidance", 3.5),
                            num_inference_steps=img_params.get("steps", 28),
                            seed=img_params.get("seed", -1),
                            speed_mode=img_params.get("speed_mode", "Extra Juiced 🔥 (more speed)")
                        )
                        if not image_url:
                            raise RuntimeError("Replicate returned no image URL.")
                        response = requests.get(image_url, timeout=60)
                        response.raise_for_status()
                        output_path = session_dir / f"{slug}_v{idx + 1}.png"
                        with open(output_path, "wb") as f:
                            f.write(response.content)
                        return {
                            "prompt": prompt,
                            "image_path": str(output_path),
                            "image_url": image_url
                        }
                    
                    job_id = queue.submit_job(
                        job_type=JobType.IMAGE_GENERATION,
                        tab_name="Products",
                        description=f"Design variation {idx+1}/{variation_count}",
                        function=generate_single_design,
                        priority=6,
                        metadata={'variation': idx+1, 'total': variation_count}
                    )
                    job_ids.append(job_id)
                
                # Store job IDs in session for persistence across tab switches
                st.session_state.product_design_jobs = job_ids
                st.session_state.product_design_session_dir = str(session_dir)
                st.session_state.product_design_timestamp = timestamp
                st.session_state.product_design_style = style
                st.session_state.product_design_color_scheme = color_scheme
                st.session_state.product_design_aspect_ratio = aspect_ratio
                st.session_state.product_design_base_prompt = base_prompt
                
                st.success(f"✅ Submitted {len(job_ids)} design jobs for parallel execution!")
                st.info("💡 Jobs are running in the background. You can switch tabs - progress is saved!")
                st.rerun()  # Rerun to show progress section
    
    # ==========================================
    # SHOW RUNNING JOBS PROGRESS (Non-blocking)
    # ==========================================
    if st.session_state.get('product_design_jobs'):
        job_ids = st.session_state.product_design_jobs
        
        st.markdown("---")
        st.markdown("### ⚙️ Design Generation in Progress")
        
        # Check progress
        progress = check_jobs_progress(job_ids)
        total = len(job_ids)
        done = progress['completed'] + progress['failed']
        
        # Progress UI
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
        with col1:
            st.metric("🔄 Running", progress['running'])
        with col2:
            st.metric("✅ Completed", progress['completed'])
        with col3:
            st.metric("❌ Failed", progress['failed'])
        with col4:
            st.metric("📊 Progress", f"{done}/{total}")
        with col5:
            if st.button("🔄 Refresh", key="refresh_design_progress", use_container_width=True):
                st.rerun()
        
        st.progress(done / total if total > 0 else 0)
        
        # Auto-refresh hint
        if done < total:
            st.info("💡 Click 'Refresh' to update progress, or navigate away - your jobs will keep running!")
        
        # Check if all done
        if are_all_jobs_done(job_ids):
            st.success("🎉 All designs completed!")
            
            # Collect results
            results = collect_job_results(job_ids)
            variations = [r for r in results if r is not None]
            
            # Restore session data
            timestamp = st.session_state.get('product_design_timestamp', dt.now().strftime("%Y%m%d_%H%M%S"))
            session_dir = st.session_state.get('product_design_session_dir', '')
            style = st.session_state.get('product_design_style', '')
            color_scheme = st.session_state.get('product_design_color_scheme', '')
            aspect_ratio = st.session_state.get('product_design_aspect_ratio', '1:1')
            base_prompt = st.session_state.get('product_design_base_prompt', '')
            
            # Clear job tracking
            del st.session_state.product_design_jobs
            for key in ['product_design_session_dir', 'product_design_timestamp', 
                       'product_design_style', 'product_design_color_scheme',
                       'product_design_aspect_ratio', 'product_design_base_prompt']:
                st.session_state.pop(key, None)

            if variations:
                run_info = {
                    "timestamp": timestamp,
                    "style": style,
                    "color_scheme": color_scheme,
                    "aspect_ratio": aspect_ratio,
                    "output_dir": str(session_dir),
                    "variations": variations,
                    "base_prompt": base_prompt
                }
                st.session_state.product_studio_results.insert(0, run_info)
                asset_bucket = st.session_state.generated_assets.setdefault('product_designs', [])
                asset_bucket.extend(var['image_path'] for var in variations)
                
                # Display generated designs immediately
                st.markdown("---")
                st.markdown("### ✅ Generated Designs")
                st.success(f"Created {len(variations)} design variation(s)!")
                
                # Show all variations with download and Printify publish buttons
                for idx, variation in enumerate(variations, start=1):
                    st.markdown(f"#### Variation {idx}")
                    col_img, col_actions = st.columns([2, 1])
                    with col_img:
                        st.image(variation['image_path'], caption=f"Design Variation {idx}", use_container_width=True)
                    with col_actions:
                            st.markdown("**Prompt:**")
                            st.caption(variation['prompt'])
                            
                            # Download button
                            with open(variation['image_path'], "rb") as img_file:
                                st.download_button(
                                    f"⬇️ Download PNG",
                                    data=img_file.read(),
                                    file_name=Path(variation['image_path']).name,
                                    mime="image/png",
                                    key=f"dl_design_{timestamp}_{idx}",
                                    use_container_width=True
                                )
                            
                            st.caption("Use the Printify selection above to create a ready-to-sell product.")
                            if st.button(
                                f"🚀 Create Printify Product",
                                key=f"printify_publish_{timestamp}_{idx}",
                                use_container_width=True,
                                disabled=not printify_api_client
                            ):
                                try:
                                    if not printify_api_client:
                                        raise RuntimeError("Printify credentials not configured. Add PRINTIFY_API_TOKEN and PRINTIFY_SHOP_ID in Settings.")
                                    if not _printify_selection_ready(printify_config):
                                        raise RuntimeError("Select a product type, provider, and at least one variant above before publishing.")

                                    variation_label = f"{(base_prompt or design_prompt or 'Design')[:40]} - Variation {idx}"
                                    with st.spinner("📤 Uploading design and creating product on Printify..."):
                                        result = _send_design_to_printify(
                                            variation['image_path'],
                                            variation['prompt'],
                                            printify_config,
                                            variation_label
                                        )

                                    product_id = result.get('product_id') or 'draft product'
                                    if result.get('published'):
                                        st.success(f"✅ Published to Printify (ID: {product_id})")
                                    else:
                                        st.success(f"✅ Created Printify draft (ID: {product_id})")
                                except Exception as e:
                                    st.error(f"❌ Failed to publish: {e}")

                    auto_config = st.session_state.get('product_studio_printify_config', {})
                    auto_ready = bool(
                        printify_api_client and auto_config.get('auto_send') and _printify_selection_ready(auto_config)
                    )

                    if auto_config.get('auto_send') and not auto_ready:
                        st.warning("Auto-publish is enabled, but the Printify selection is incomplete.")

                    if auto_ready:
                        st.markdown("---")
                        st.markdown("#### 🚀 Auto-Publishing to Printify")
                        published_designs = {
                            product.get('design_path')
                            for product in st.session_state.get('printify_products', [])
                            if product.get('design_path')
                        }

                        for idx, variation in enumerate(variations, start=1):
                            if variation['image_path'] in published_designs:
                                st.info(f"Variation {idx} already published to Printify.")
                                continue

                            status_placeholder = st.empty()
                            try:
                                variation_label = f"{(base_prompt or design_prompt or 'Design')[:40]} - Variation {idx}"
                                with st.spinner(f"Publishing variation {idx} to Printify..."):
                                    result = _send_design_to_printify(
                                        variation['image_path'],
                                        variation['prompt'],
                                        auto_config,
                                        variation_label
                                    )
                                product_id = result.get('product_id') or 'draft product'
                                status_placeholder.success(
                                    f"Variation {idx}: Published product {product_id} ({len(auto_config.get('variant_ids', []))} variant(s))"
                                )
                                published_designs.add(variation['image_path'])
                            except Exception as auto_error:
                                status_placeholder.error(f"Variation {idx}: {auto_error}")
                    
                    st.info(f"📁 All files saved to: `{session_dir}`")
                    st.toast(f"Generated {len(variations)} design(s).")
                else:
                    st.warning("No designs were saved. Check the error above and try again.")

    if len(st.session_state.product_studio_results) > 1:
        with st.expander("Previous Design Studio runs", expanded=False):
            for run in st.session_state.product_studio_results[1:6]:
                st.markdown(
                    f"**{run['timestamp']}** • {run['style']} • {run['color_scheme']}"
                )
                st.markdown(f"Saved in `{run['output_dir']}`")
    
    # Show recently uploaded Printify designs
    if 'printify_uploads' in st.session_state and st.session_state.printify_uploads:
        st.markdown("---")
        st.markdown("### 📤 Recent Printify Uploads")
        with st.expander("View uploaded designs", expanded=False):
            for upload in st.session_state.printify_uploads[-5:]:  # Show last 5
                col_thumb, col_details = st.columns([1, 2])
                with col_thumb:
                    design_path = upload.get('design_path', '')
                    if design_path:
                        if Path(design_path).exists():
                            st.image(design_path, width=100)
                        else:
                            # Show placeholder if file was moved/deleted but still show upload record
                            st.caption("🖼️ Design")
                            st.caption("_(file moved)_")
                    else:
                        st.caption("🖼️ Design")
                with col_details:
                    st.markdown(f"**Upload ID:** `{upload['upload_id']}`")
                    st.caption(f"{upload['timestamp']}")
                    st.caption(f"Prompt: {upload['prompt'][:80]}...")
                    if design_path:
                        st.caption(f"📁 `{design_path}`")

    if st.session_state.get('printify_products'):
        st.markdown("---")
        st.markdown("### 🛒 Recent Printify Products")
        with st.expander("View latest products", expanded=False):
            for product in reversed(st.session_state.printify_products[-5:]):
                col_thumb, col_details = st.columns([1, 2])
                with col_thumb:
                    design_path = product.get('design_path')
                    if design_path:
                        if Path(design_path).exists():
                            st.image(design_path, width=100)
                        else:
                            # Show placeholder even if file doesn't exist
                            st.caption("🖼️ Design")
                            st.caption("_(file moved)_")
                    else:
                        st.caption("🖼️ Design")
                with col_details:
                    title = product.get('title') or "Printify Product"
                    product_id = product.get('product_id') or "draft"
                    st.markdown(f"**{title}**")
                    st.caption(f"Product ID: {product_id} • {product.get('timestamp', '')}")
                    st.caption(
                        f"Blueprint: {product.get('blueprint_id', 'N/A')} • Variants: {len(product.get('variant_ids', []) or [])}"
                    )
                    if design_path:
                        st.caption(f"📁 `{design_path}`")
                    if product.get('published'):
                        st.success("Published to store")
                    else:
                        st.info("Draft on Printify")
