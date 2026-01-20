import streamlit as st
import os
from pathlib import Path
import requests
import re
import logging

from app.utils.cross_page_state import restore_page_to_session
from app.utils.performance_optimizations import get_replicate_client
from app.services.platform_integrations import tracked_replicate_run
from modules.video_generation import generate_ken_burns_video
from app.services.youtube_upload_service import YouTubeUploadService
from app.services.platform_helpers import _get_replicate_token
from app.utils.ray_integration_helpers import is_ray_enabled, get_ray_manager_if_enabled
from app.services.tab_job_helpers import (
    submit_video_generation_job,
    submit_batch_videos,
    submit_batch_operation,
    collect_job_results,
    check_jobs_progress,
    are_all_jobs_done
)
from app.services.global_job_queue import JobType, get_global_job_queue

logger = logging.getLogger(__name__)

def render_video_producer_tab():
    # Restore any saved Video Producer state
    restore_page_to_session("video_producer", keys_to_restore=[
        'video_producer_results', 'video_product_name', 'video_brand_name',
        'video_target_audience', 'video_style'
    ])
    
    st.markdown("### 🎬 Product Commercial Video Creator")
    st.markdown("Create professional product commercials with AI - automatic script writing, cinematic visuals, voiceover, and music")
    
    # Auto-load API key from .env
    try:
        replicate_token = _get_replicate_token()
        replicate_api_key = replicate_token
    except ValueError:
        st.error("❌ Replicate API Key required. Add REPLICATE_API_TOKEN to your .env file or Settings page.")
        replicate_api_key = None
    
    # Get user inputs
    with st.expander("🛍️ Product Settings", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            if replicate_api_key:
                st.success(f"✅ Replicate API configured (from .env)")
            product_name = st.text_input(
                "Product Name",
                placeholder="e.g., 'EcoClean Detergent' or 'SmartFit Watch'",
                help="The product you're promoting"
            )
            brand_name = st.text_input(
                "Brand Name (Optional)",
                placeholder="e.g., 'EcoHome' or 'TechWear'",
                help="Your brand name for consistency"
            )
        with col2:
            target_audience = st.text_input(
                "Target Audience",
                placeholder="e.g., 'Eco-conscious families' or 'Fitness enthusiasts'",
                help="Who is this ad targeting?"
            )
            
            # Product image upload for image-to-video
            st.markdown("**Product Image (Optional)**")
            uploaded_product_image = st.file_uploader(
                "Upload product photo for video generation",
                type=["png", "jpg", "jpeg", "webp"],
                help="Upload a product image to use as reference for video generation. Works with Kling & Luma models.",
                key="product_image_uploader"
            )
            
            if uploaded_product_image:
                st.image(uploaded_product_image, caption="Product Image Preview", use_container_width=True)
                # Save uploaded image to temp directory
                temp_dir = Path("temp_files")
                temp_dir.mkdir(exist_ok=True)
                product_image_path = temp_dir / f"product_image_{uploaded_product_image.name}"
                with open(product_image_path, "wb") as f:
                    f.write(uploaded_product_image.getbuffer())
                st.success(f"✅ Product image saved: {product_image_path.name}")
            else:
                product_image_path = None
    
    st.markdown("---")
    
    # Video Model Selection
    st.subheader("🎬 Video Generation Model")
    video_model_option = st.selectbox(
        "Select video generation model:",
        [
            "🎞️ Ken Burns Effect (Free, Instant)",
            "⚡ Luma Ray Flash 2 (Fast, 540p)",
            "💨 Luma Ray 2 (High Quality, 540p)",
            "🌟 Kling v2.5 Turbo Pro (Premium)",
            "🎥 OpenAI Sora-2 (Best, Slow)",
            "🌌 Google Veo 3 (Audio, Top Quality)",
            "⚡ Google Veo 3 Fast (Audio, Quick)",
            "🎆 Google Veo 3.1 Fast (Audio, Improved)",
            "🕹️ Google Veo 2 (4K Quality)",
            "🎨 Pixverse v5 (Anime, 1080p/8s)",
            "🎬 Pixverse v4.5 (Fast, 1080p)",
            "🎁 Leonardo Motion 2.0 (480p)",
            "🎉 Minimax Hailuo Fast (Image Only)",
            "🌊 Wan Video 2.5 (Fast T2V)",
            "🌱 Bytedance Seedance Pro (Cinematic)"
        ],
        index=1,
        help="Choose video generation model based on quality, speed, and features"
    )
    
    # Map selection to model flags
    use_ken_burns = "Ken Burns" in video_model_option
    use_luma = "Luma Ray Flash" in video_model_option
    use_luma2 = "Luma Ray 2" in video_model_option
    use_kling = "Kling" in video_model_option
    use_sora = "Sora-2" in video_model_option
    use_veo3 = video_model_option == "🌌 Google Veo 3 (Audio, Top Quality)"
    use_veo3_fast = video_model_option == "⚡ Google Veo 3 Fast (Audio, Quick)"
    use_veo31_fast = "Veo 3.1 Fast" in video_model_option
    use_veo2 = "Veo 2" in video_model_option
    use_pixverse5 = "Pixverse v5" in video_model_option
    use_pixverse45 = "Pixverse v4.5" in video_model_option
    use_leonardo = "Leonardo Motion" in video_model_option
    use_hailuo = "Hailuo" in video_model_option
    use_wan = "Wan Video" in video_model_option
    use_seedance = "Seedance" in video_model_option
    
    # Image-to-video info
    if product_image_path:
        if use_ken_burns:
            st.info("🎬 **Ken Burns Mode**: Will animate your product image with cinematic pan/zoom effects")
        elif use_kling:
            st.success("✅ **Kling Image-to-Video**: Excellent product consistency - uses your image as first frame")
        elif use_luma or use_luma2:
            st.success("✅ **Luma Image-to-Video**: Good product consistency - uses your image as reference")
        elif use_hailuo:
            st.success("✅ **Hailuo**: Image-ONLY model - requires your product image")
        elif use_sora or use_veo3 or use_veo3_fast or use_veo31_fast or use_veo2:
            st.info("🎬 **Premium Image-to-Video**: Will attempt to start from your product image")
        else:
            st.info("🎬 **Image-to-Video Mode**: Will use your product image as starting reference")
        st.caption(f"📸 Using: {product_image_path.name}")
    else:
        if use_ken_burns:
            st.warning("⚠️ **Ken Burns requires a product image** - Upload one above or switch to Luma/Kling for text-to-video")
        elif use_hailuo:
            st.error("❌ **Hailuo requires a product image** - This is an image-only model. Upload image above.")
        else:
            st.caption("💡 Tip: Upload a product image above for image-to-video generation (more consistent product appearance)")
            st.info("**Best models for image-to-video consistency:**\n- 🌟 Kling v2.5 (excellent)\n- ⚡ Luma Ray (good)\n- 🎉 Hailuo (image-only)")
    
    # Video Settings
    st.subheader("🎥 Video Settings")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        video_style = st.selectbox(
            "Visual Style:",
            ["Cinematic", "Modern", "Elegant", "Dynamic", "Minimalist", "Luxury"],
            help="Choose the visual style for your commercial"
        )
        aspect_ratio = st.selectbox(
            "Video Dimensions:",
            ["16:9", "9:16", "1:1", "4:3"],
            help="Choose aspect ratio (16:9 for YouTube, 9:16 for TikTok/Reels)"
        )
    
    with col2:
        # Dynamic controls based on selected model
        if use_hailuo:
            # Hailuo-specific controls
            video_duration = st.slider(
                "Video Duration:",
                min_value=6,
                max_value=10,
                value=6,
                help="Hailuo supports 6-10 second videos"
            )
            video_resolution = st.selectbox(
                "Resolution:",
                ["768p", "1080p"],
                help="1080p limited to 6 seconds"
            )
            num_frames = 120  # Not used for Hailuo
        elif use_sora:
            # Sora-specific controls
            video_duration = st.slider(
                "Video Duration:",
                min_value=2,
                max_value=4,
                value=4,
                help="Sora generates 2-4 second clips"
            )
            st.caption("⚡ Sora: Ultra-high quality, 4s max")
            num_frames = 120
        elif use_pixverse5 or use_pixverse45:
            # Pixverse controls
            video_duration = st.slider(
                "Video Duration:",
                min_value=3,
                max_value=8,
                value=5,
                help="Pixverse: 3-8 second videos"
            )
            num_frames = 120
        elif use_ken_burns:
            num_frames = 120
            st.caption("⚡ Ken Burns uses instant rendering")
        else:
            quality_label = st.selectbox(
                "Video Quality:",
                ["Standard (120 frames)", "High (200 frames)"],
                help="Higher quality = better visuals but slower generation"
            )
            num_frames = 120 if "Standard" in quality_label else 200
        
        camera_movement = st.selectbox(
            "Camera Movement:",
            ["Smooth Pan", "Zoom In", "Zoom Out", "Static", "Dynamic"],
            help="Product showcase camera movement"
        )
    
    with col3:
        selected_voice = st.selectbox(
            "Voiceover Voice:",
            options=["Deep Voice Man", "Friendly Person", "Calm Woman", "Casual Guy", 
                     "Wise Woman", "Inspirational Girl", "Lively Girl", "Patient Man"],
            index=0,
            help="Professional voice for product narration"
        )
        selected_emotion = st.selectbox(
            "Voice Emotion:",
            options=["auto", "happy", "excited", "confident", "calm", "friendly"],
            index=1,
            help="Emotional tone for the commercial"
        )
    
    # Audio Settings
    st.subheader("🔊 Audio Settings")
    col1, col2 = st.columns(2)
    
    with col1:
        include_voiceover = st.checkbox(
            "Include VoiceOver", 
            value=True, 
            help="Professional voiceover narration for the commercial"
        )
        include_music = st.checkbox(
            "Include Background Music",
            value=True,
            help="AI-generated background music"
        )
        auto_publish_youtube = st.checkbox(
            "📺 Auto-publish to YouTube",
            value=False,
            help="Automatically upload final video to YouTube"
        )
    
    with col2:
        video_length_label = st.selectbox(
            "Commercial Length:",
            ["10 seconds", "15 seconds", "20 seconds", "30 seconds"],
            index=1,
            help="Total duration of the product commercial"
        )
        total_video_duration = {"10 seconds": 10, "15 seconds": 15, "20 seconds": 20, "30 seconds": 30}[video_length_label]
    
    # Map video model selection to flags (needed for advanced settings)
    use_ken_burns = "Ken Burns" in video_model_option
    use_luma = "Luma Ray Flash" in video_model_option or "Luma Ray 2" in video_model_option
    use_kling = "Kling" in video_model_option
    use_veo3 = video_model_option == "🌌 Google Veo 3 (Audio, Top Quality)"
    use_veo3_fast = video_model_option == "⚡ Google Veo 3 Fast (Audio, Quick)"
    use_veo3_1 = "Veo 3.1 Fast" in video_model_option
    use_veo2 = "Veo 2" in video_model_option
    use_pixverse = "Pixverse" in video_model_option
    use_leonardo = "Leonardo Motion" in video_model_option
    
    # Advanced Customization Dropdown
    with st.expander("⚙️ Advanced Customization (Optional)", expanded=False):
        st.markdown("### 🎥 Video Model Parameters")
        
        adv_col1, adv_col2 = st.columns(2)
        
        with adv_col1:
            # Video-specific parameters
            if use_kling:
                kling_seed = st.number_input("Kling Seed", min_value=-1, max_value=999999, value=-1, help="Random seed (-1 for random)")
                kling_negative_prompt = st.text_input("Negative Prompt", value="", help="What to avoid in video")
            elif use_leonardo:
                leo_motion_strength = st.slider("Motion Strength", 1, 10, 5, help="Amount of movement in video")
            elif use_pixverse:
                pixverse_seed = st.number_input("Pixverse Seed", min_value=-1, max_value=2147483647, value=-1)
                pixverse_negative_prompt = st.text_input("Negative Prompt", value="")
            elif use_veo3 or use_veo3_fast or use_veo3_1:
                veo_guidance_scale = st.slider("Guidance Scale", 1.0, 10.0, 7.0, step=0.5, help="How closely to follow prompt")
                veo_temperature = st.slider("Temperature", 0.0, 1.0, 0.7, step=0.1, help="Creativity level")
            elif use_luma:
                luma_extend_video = st.checkbox("Extend Video", value=False, help="Generate continuation")
                luma_keyframe_behavior = st.selectbox("Keyframe Behavior", ["frame0", "frame_end"], help="How to use input image")
            elif use_veo2:
                veo2_resolution = st.selectbox("Resolution", ["720p", "1080p"], index=1)
                veo2_guidance = st.slider("Guidance Scale", 1.0, 15.0, 7.5, step=0.5)
        
        with adv_col2:
            # Ken Burns specific
            if use_ken_burns:
                ken_zoom_speed = st.slider("Zoom Speed", 0.5, 3.0, 1.0, step=0.1, help="Speed of zoom animation")
                ken_pan_direction = st.selectbox("Pan Direction", ["auto", "left", "right", "up", "down"], help="Camera movement")
        
        st.markdown("### 🎵 Music Generation Parameters")
        music_col1, music_col2 = st.columns(2)
        
        with music_col1:
            music_style = st.selectbox(
                "Music Style",
                ["Corporate", "Upbeat", "Cinematic", "Energetic", "Calm", "Epic"],
                help="Background music vibe"
            )
            music_tempo = st.selectbox("Tempo", ["Slow", "Medium", "Fast", "Very Fast"], index=1)
        
        with music_col2:
            music_instruments = st.multiselect(
                "Instruments",
                ["Piano", "Guitar", "Drums", "Synth", "Strings", "Bass"],
                default=["Piano", "Synth"],
                help="Preferred instruments"
            )
            music_volume = st.slider("Music Volume", 0.0, 0.5, 0.2, step=0.05, help="Background music volume level")
        
        st.markdown("### ✍️ Script Writing Style")
        writing_col1, writing_col2 = st.columns(2)
        
        with writing_col1:
            script_tone = st.selectbox(
                "Script Tone",
                ["Professional", "Casual", "Enthusiastic", "Authoritative", "Friendly", "Luxury"],
                help="Overall voice of the script"
            )
            script_focus = st.selectbox(
                "Primary Focus",
                ["Product Features", "Benefits", "Problem-Solution", "Lifestyle", "Emotional"],
                help="What to emphasize"
            )
        
        with writing_col2:
            use_questions = st.checkbox("Include Questions", value=True, help="Use rhetorical questions")
            use_stats = st.checkbox("Include Statistics", value=False, help="Add data/numbers")
            cta_style = st.selectbox(
                "Call-to-Action Style",
                ["Direct", "Soft", "Urgent", "Informative"],
                help="How to end the commercial"
            )
    
    # Calculate segments based on duration (5 seconds per segment)
    num_segments = max(2, total_video_duration // 5)
    
    # Main generation section
    st.markdown("---")
    st.markdown("### 🚀 Generate Video")
    
    if not replicate_api_key:
        st.error("❌ Replicate API key required. Add REPLICATE_API_TOKEN to your .env file.")
    elif not product_name:
        st.warning("⚠️ Enter a product name above to start generating")
    
    # Main generation button
    if replicate_api_key and product_name and st.button(f"🎬 Generate {total_video_duration}-second Commercial", use_container_width=True, type="primary", key="generate_video_btn"):
        st.markdown("---")
        st.markdown("## 🎬 Product Commercial Production Pipeline")
        
        try:
            # Initialize Replicate client
            import replicate
            replicate_client = replicate.Client(api_token=replicate_api_key, timeout=120)
            
            # Create temp directory
            temp_dir = Path("temp_files")
            temp_dir.mkdir(exist_ok=True)
            
            # Initialize audio paths
            music_path = None
            voice_path = None
            
            # Step 1: Generate Commercial Script
            st.info(f"Step 1: Writing product commercial script for {total_video_duration}-second ad")
            
            # Product-focused commercial script prompt
            brand_context = f" by {brand_name}" if brand_name else ""
            audience_context = f" targeting {target_audience}" if target_audience else ""
            
            segment_word_ranges = {10: "4-6 words", 15: "5-8 words", 20: "6-10 words", 30: "8-12 words"}
            words_per_segment = segment_word_ranges.get(total_video_duration, "6-10 words")
            
            script_prompt_template = (
                f"You are an expert advertising copywriter. Write a compelling, professional voiceover script for a {total_video_duration}-second product commercial for '{product_name}'{brand_context}{audience_context}. "
                f"\n\nDivide your script into exactly {num_segments} segments of approximately 5 seconds each. Each segment must be {words_per_segment}. "
                f"\n\nCRITICAL REQUIREMENTS:"
                f"\n1. EVERY segment MUST explicitly mention or show the product '{product_name}' - the product is the star"
                f"\n2. Each segment must describe a specific VISUAL of the product (not abstract concepts)"
                f"\n3. Segment 1: Open with product reveal or hero shot"
                f"\n4. Middle segments: Showcase product features, benefits, or use cases"
                f"\n5. Final segment: Strong call-to-action with product"
                f"\n6. Use concrete, visual language that shows the product in action"
                f"\n7. Keep it punchy, direct, and sales-focused"
                f"\n\nLabel each segment clearly as '1:', '2:', '3:', etc."
                f"\n\nExample format:"
                f"\n1: [Product name] revolutionizes [category] with [specific feature]"
                f"\n2: Watch as [product] delivers [specific benefit] instantly"
                f"\n3: From [use case] to [use case], [product] adapts"
                f"\n\nWrite the complete {num_segments}-segment script now:"
            )
            
            # Use tracked API call for cost monitoring
            full_script = tracked_replicate_run(
                replicate_client,
                "meta/meta-llama-3-70b-instruct",
                {"prompt": script_prompt_template, "max_tokens": 1024, "temperature": 0.7},
                operation_name="Script Generation - Commercial"
            )
            script_text = "".join(full_script) if isinstance(full_script, list) else full_script
            
            # Extract segments
            import re
            segments = re.findall(r"\d+:\s*(.+)", script_text)
            if len(segments) < num_segments:
                st.error(f"Failed to extract {num_segments} clear script segments. Please try again.")
                st.stop()
            script_segments = segments[:num_segments]
            
            # Validate product mentions
            product_mentions = sum(1 for seg in script_segments if product_name.lower() in seg.lower())
            if product_mentions < num_segments // 2:
                st.warning(f"⚠️ Script may not focus enough on '{product_name}'. Continuing anyway...")
            
            # Save script
            script_path = temp_dir / "commercial_script.txt"
            with open(script_path, "w") as f:
                f.write(f"Product Commercial Script: {product_name}\n")
                f.write(f"Duration: {total_video_duration} seconds\n")
                f.write(f"Segments: {num_segments}\n\n")
                f.write("\n\n".join([f"Segment {i+1}: {seg}" for i, seg in enumerate(script_segments)]))
            
            st.success(f"✅ Commercial script written ({product_mentions}/{num_segments} segments mention product)")
            with st.expander("📜 View Script", expanded=True):
                for i, seg in enumerate(script_segments, 1):
                    st.write(f"**Segment {i}:** {seg}")
            
            with open(script_path, "r") as f:
                st.download_button(
                    "📜 Download Script",
                    f.read(),
                    "script.txt",
                    mime="text/plain",
                    key="download_script"
                )
            
            # Step 2: Generate Video Segments
            st.info("Step 2: Generating video segments")
            temp_video_paths = []
            
            for i, segment in enumerate(script_segments):
                st.info(f"Generating visuals for segment {i+1}/{num_segments}")
                
                # Determine shot type for product commercial
                if i == 0:
                    shot_type = "hero product reveal shot"
                elif i == 1 and len(script_segments) > 2:
                    shot_type = "product feature showcase"
                elif i == 2 and len(script_segments) > 3:
                    shot_type = "product in use close-up"
                else:
                    shot_type = "dynamic call-to-action shot with product"
                
                # Generate product commercial video segment
                camera_direction = camera_movement.lower().replace(" ", "_")
                
                # For image-to-video: emphasize starting from uploaded image
                if product_image_path and product_image_path.exists():
                    video_prompt = (
                        f"Professional {video_style.lower()} commercial {shot_type} showcasing the EXACT product from the uploaded image. "
                        f"START WITH THE PRODUCT AS SHOWN IN THE IMAGE - maintain its exact appearance. "
                        f"Visual: {segment}. Camera: {camera_direction}, smooth cinematic movement. "
                        f"Lighting: studio quality, product-focused. Style: premium advertising aesthetic. "
                        f"MAINTAIN PRODUCT CONSISTENCY - use the exact product look from the starting image throughout. No text overlays."
                    )
                else:
                    video_prompt = (
                        f"Professional {video_style.lower()} commercial {shot_type} showcasing '{product_name}' product. "
                        f"Visual: {segment}. Camera: {camera_direction}, smooth cinematic movement. "
                        f"Lighting: studio quality, product-focused. Style: premium advertising aesthetic. "
                        f"CRITICAL: Product '{product_name}' must be clearly visible and the main focus. No text overlays."
                    )
                
                try:
                    # Select video model
                    if use_luma:
                        model_name = "luma/ray"
                        model_input = {
                            "prompt": video_prompt,
                            "aspect_ratio": aspect_ratio
                        }
                        # Add product image if uploaded (image-to-video)
                        if product_image_path and product_image_path.exists():
                            st.info(f"🖼️ Using product image for segment {i+1} (Luma image-to-video)")
                            model_input["first_frame_image"] = open(str(product_image_path), "rb")
                    elif use_luma2:
                        model_name = "luma/ray"
                        model_input = {
                            "prompt": video_prompt,
                            "aspect_ratio": aspect_ratio
                        }
                        # Luma Ray supports image-to-video
                        if product_image_path and product_image_path.exists():
                            st.info(f"🖼️ Using product image for segment {i+1} (Luma image-to-video)")
                            model_input["first_frame_image"] = open(str(product_image_path), "rb")
                    elif use_kling:
                        model_name = "kwaivgi/kling-v2.5-turbo-pro"
                        model_input = {
                            "prompt": video_prompt,
                            "aspect_ratio": aspect_ratio,
                            "motion_level": 4
                        }
                        # Add product image if uploaded (image-to-video)
                        if product_image_path and product_image_path.exists():
                            st.info(f"🖼️ Using product image for segment {i+1} (Kling image-to-video)")
                            # Keep file open - Replicate reads it during API call
                            model_input["image"] = open(str(product_image_path), "rb")
                    elif use_sora:
                        model_name = "openai/sora-2"
                        # Enhance prompt if using image to ensure consistency
                        sora_prompt = video_prompt
                        if product_image_path and product_image_path.exists():
                            sora_prompt = video_prompt + " Starting from the exact product shown in the image, maintaining product consistency throughout."
                        
                        model_input = {
                            "prompt": sora_prompt,
                            "duration": 4,
                            "quality": "high",
                            "remove_watermark": True
                        }
                        # Sora-2 DOES support image-to-video!
                        if product_image_path and product_image_path.exists():
                            st.info(f"🖼️ Using product image for segment {i+1} (Sora-2 image-to-video)")
                            model_input["image"] = open(str(product_image_path), "rb")
                    elif use_veo3:
                        model_name = "google/veo-3"
                        model_input = {"prompt": video_prompt}
                        if product_image_path and product_image_path.exists():
                            st.info(f"🖼️ Using product image for segment {i+1} (Veo 3 image-to-video)")
                            model_input["first_frame_image"] = open(str(product_image_path), "rb")
                    elif use_veo3_fast:
                        model_name = "google/veo-3-fast"
                        model_input = {"prompt": video_prompt}
                        if product_image_path and product_image_path.exists():
                            st.info(f"🖼️ Using product image for segment {i+1} (Veo 3 Fast image-to-video)")
                            model_input["first_frame_image"] = open(str(product_image_path), "rb")
                    elif use_veo31_fast:
                        model_name = "google/veo-3.1-fast"
                        model_input = {"prompt": video_prompt}
                        if product_image_path and product_image_path.exists():
                            st.info(f"🖼️ Using product image for segment {i+1} (Veo 3.1 Fast image-to-video)")
                            model_input["first_frame_image"] = open(str(product_image_path), "rb")
                    elif use_veo2:
                        model_name = "google/veo-2"
                        model_input = {"prompt": video_prompt}
                        if product_image_path and product_image_path.exists():
                            st.info(f"🖼️ Using product image for segment {i+1} (Veo 2 image-to-video)")
                            model_input["first_frame_image"] = open(str(product_image_path), "rb")
                    elif use_pixverse5:
                        model_name = "pixverse/pixverse-v5"
                        model_input = {
                            "prompt": video_prompt,
                            "duration": 5,
                            "resolution": "720p"
                        }
                        if product_image_path and product_image_path.exists():
                            st.info(f"🖼️ Using product image for segment {i+1} (Pixverse v5 image-to-video)")
                            model_input["first_frame_image"] = open(str(product_image_path), "rb")
                    elif use_pixverse45:
                        model_name = "pixverse/pixverse-v4.5"
                        model_input = {
                            "prompt": video_prompt,
                            "duration": 5,
                            "resolution": "720p"
                        }
                        if product_image_path and product_image_path.exists():
                            st.info(f"🖼️ Using product image for segment {i+1} (Pixverse v4.5 image-to-video)")
                            model_input["first_frame_image"] = open(str(product_image_path), "rb")
                    elif use_leonardo:
                        model_name = "leonardoai/motion-2.0"
                        # Leonardo Motion accepts: "9:16", "16:9", "2:3", "4:5"
                        leo_aspect = aspect_ratio if aspect_ratio in ["9:16", "16:9", "2:3", "4:5"] else "16:9"
                        model_input = {
                            "prompt": video_prompt,
                            "aspect_ratio": leo_aspect
                        }
                        if product_image_path and product_image_path.exists():
                            st.info(f"🖼️ Using product image for segment {i+1} (Leonardo Motion image-to-video)")
                            model_input["first_frame_image"] = open(str(product_image_path), "rb")
                    elif use_hailuo:
                        # Minimax Hailuo REQUIRES an image (image-only model)
                        if not product_image_path or not product_image_path.exists():
                            st.warning(f"⚠️ Minimax Hailuo requires a product image. Skipping segment {i+1}.")
                            continue
                        model_name = "minimax/hailuo-2.3-fast"
                        st.info(f"🖼️ Using product image for segment {i+1} (Hailuo image-only)")
                        # Hailuo API requires BOTH prompt AND first_frame_image
                        model_input = {
                            "prompt": video_prompt,  # Motion description
                            "first_frame_image": open(str(product_image_path), "rb"),
                            "duration": 6,
                            "resolution": "768p"
                        }
                    elif use_wan:
                        model_name = "wan-video/wan-2.5-t2v-fast"
                        model_input = {"prompt": video_prompt}
                        if product_image_path and product_image_path.exists():
                            st.info(f"🖼️ Using product image for segment {i+1} (Wan Video image-to-video)")
                            model_input["first_frame_image"] = open(str(product_image_path), "rb")
                    elif use_seedance:
                        model_name = "bytedance/seedance-1-pro-fast"
                        model_input = {"prompt": video_prompt}
                        if product_image_path and product_image_path.exists():
                            st.info(f"🖼️ Using product image for segment {i+1} (Seedance image-to-video)")
                            model_input["first_frame_image"] = open(str(product_image_path), "rb")
                    elif use_ken_burns:
                        # Ken Burns effect - requires product image
                        if not product_image_path or not product_image_path.exists():
                            st.warning(f"⚠️ Ken Burns requires a product image. Skipping segment {i+1}.")
                            continue
                        st.info(f"⚡ Generating Ken Burns effect for segment {i+1}")
                        # Automatic zoom pattern: zoom out -> zoom in -> zoom out (creates dynamic motion)
                        zoom_patterns = ["zoom_out", "zoom_in", "zoom_out", "pan_right", "pan_left"]
                        zoom_type = zoom_patterns[i % len(zoom_patterns)]
                        
                        # Use generate_ken_burns_video from modules (returns bool)
                        video_path = temp_dir / f"segment_{i}_kenburns.mp4"
                        success = generate_ken_burns_video(
                            image_path=str(product_image_path),
                            output_path=str(video_path),
                            duration=5,
                            fps=30,
                            resolution="1080p",
                            zoom_type=zoom_type
                        )
                        if success and video_path.exists():
                            temp_video_paths.append(video_path)
                            st.video(str(video_path))
                            with open(video_path, "rb") as f:
                                st.download_button(
                                    f"🎥 Download Segment {i+1}",
                                    f.read(),
                                    f"segment_{i+1}.mp4",
                                    mime="video/mp4",
                                    key=f"download_segment_{i}"
                                )
                        continue
                    else:
                        model_name = "luma/ray-flash-2-540p"
                        model_input = {
                            "prompt": video_prompt,
                            "num_frames": num_frames,
                            "fps": 24
                        }
                        # Add image-to-video support for Luma
                        if product_image_path and product_image_path.exists():
                            st.info(f"🖼️ Using product image for segment {i+1} (Luma image-to-video)")
                            model_input["keyframes"] = {
                                "frame0": {
                                    "type": "image",
                                    "url": open(str(product_image_path), "rb")
                                }
                            }
                    
                    video_uri = tracked_replicate_run(
                        replicate_client,
                        model_name,
                        model_input,
                        operation_name=f"Video Segment {i+1}"
                    )
                    
                    # Download video segment
                    resp = requests.get(video_uri, stream=True)
                    resp.raise_for_status()
                    video_path = temp_dir / f"segment_{i}.mp4"
                    with open(video_path, "wb") as f:
                        for chunk in resp.iter_content(1024 * 32):
                            f.write(chunk)
                    
                    temp_video_paths.append(video_path)
                    st.video(str(video_path))
                    
                    with open(video_path, "rb") as f:
                        st.download_button(
                            f"🎥 Download Segment {i+1}",
                            f.read(),
                            f"segment_{i+1}.mp4",
                            mime="video/mp4",
                            key=f"download_segment_{i}"
                        )
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str or "throttled" in error_str.lower():
                        st.error(f"⏳ **Rate Limit Reached** - Your Replicate account has limited credits (< $5)")
                        st.info(f"💡 **To continue:**\n- Wait 10-15 seconds\n- Click 'Generate Commercial' again\n- OR reduce number of segments\n- OR add more credits to your Replicate account")
                    else:
                        st.error(f"Failed to generate segment {i+1}: {e}")
                    continue
            
            st.success(f"✅ Generated {len(temp_video_paths)} video segments")
            
            # Step 3: Generate Background Music
            if include_music:
                st.info("Step 3: Creating background music")
                try:
                    music_prompt = f"Upbeat, professional background music for a {total_video_duration}-second {video_style.lower()} product commercial for {product_name}. {selected_emotion.capitalize()} tone, non-distracting, modern advertising style."
                    music_uri = tracked_replicate_run(
                        replicate_client,
                        "meta/musicgen",
                        {
                            "prompt": music_prompt,
                            "duration": min(int(total_video_duration), 30),
                            "model_version": "stereo-melody-large",
                            "normalization_strategy": "peak",
                            "output_format": "mp3"
                        },
                        operation_name="Background Music Generation"
                    )
                    music_path = temp_dir / "background_music.mp3"
                    with open(music_path, "wb") as f:
                        resp = requests.get(music_uri, stream=True)
                        resp.raise_for_status()
                        for chunk in resp.iter_content(1024 * 32):
                            f.write(chunk)
                    
                    st.audio(str(music_path))
                    with open(music_path, "rb") as f:
                        st.download_button(
                            "🎵 Download Background Music",
                            f.read(),
                            "background_music.mp3",
                            mime="audio/mp3",
                            key="download_music"
                        )
                except Exception as e:
                    st.warning(f"Background music generation failed: {e}")
            
            # Step 4: Generate Per-Segment Narration and Overlay on Videos
            if include_voiceover:
                st.info(f"Step 4: Generating per-segment narration with {selected_voice} voice")
                try:
                    from moviepy.editor import VideoFileClip, AudioFileClip
                    
                    voice_map = {
                        "Wise Woman": "Wise_Woman",
                        "Friendly Person": "Friendly_Person",
                        "Inspirational Girl": "Inspirational_girl",
                        "Deep Voice Man": "Deep_Voice_Man",
                        "Calm Woman": "Calm_Woman",
                        "Casual Guy": "Casual_Guy",
                        "Lively Girl": "Lively_Girl",
                        "Patient Man": "Patient_Man"
                    }
                    
                    # Generate narration for each segment and overlay on corresponding video
                    narrated_video_paths = []
                    
                    for seg_idx, (video_path, script_segment) in enumerate(zip(temp_video_paths, script_segments)):
                        st.info(f"🎙️ Narrating segment {seg_idx + 1}/{len(script_segments)}")
                        
                        # Generate narration audio for this segment
                        cleaned_narration = re.sub(r'[^\w\s]', '', script_segment)
                        
                        # Map UI emotions to Cartesia valid emotions
                        # Valid: "auto", "happy", "sad", "angry", "fearful", "disgusted", "surprised", "calm", "fluent", "neutral"
                        emotion_map = {
                            "confident": "calm",
                            "excited": "happy",
                            "friendly": "happy",
                            "auto": "auto",
                            "happy": "happy",
                            "calm": "calm"
                        }
                        cartesia_emotion = emotion_map.get(selected_emotion.lower(), "neutral")
                        
                        # Retry logic for rate limiting
                        max_retries = 3
                        retry_delay = 6  # Start with 6 seconds
                        
                        for attempt in range(max_retries):
                            try:
                                voiceover_uri = tracked_replicate_run(
                                    replicate_client,
                                    "minimax/speech-02-hd",
                                    {
                                        "text": cleaned_narration,
                                        "voice_id": voice_map.get(selected_voice, "Friendly_Person"),
                                        "emotion": cartesia_emotion,
                                        "speed": 1.1,
                                        "pitch": 0,
                                        "volume": 1,
                                        "bitrate": 128000,
                                        "channel": "mono",
                                        "sample_rate": 32000,
                                        "language_boost": "English",
                                        "english_normalization": True
                                    },
                                    operation_name=f"Voiceover Segment {seg_idx+1}"
                                )
                                break  # Success, exit retry loop
                            except Exception as e:
                                error_str = str(e)
                                if "429" in error_str or "throttled" in error_str.lower():
                                    if attempt < max_retries - 1:
                                        wait_time = retry_delay * (attempt + 1)
                                        st.warning(f"⏳ Rate limited. Waiting {wait_time}s before retry {attempt + 2}/{max_retries}...")
                                        import time
                                        time.sleep(wait_time)
                                    else:
                                        raise Exception(f"Rate limit exceeded after {max_retries} attempts. Please wait a few minutes.")
                                else:
                                    raise  # Re-raise non-rate-limit errors
                        
                        # Save segment narration
                        segment_voice_path = temp_dir / f"narration_segment_{seg_idx}.mp3"
                        with open(segment_voice_path, "wb") as f:
                            resp = requests.get(voiceover_uri, stream=True)
                            resp.raise_for_status()
                            for chunk in resp.iter_content(1024 * 32):
                                f.write(chunk)
                        
                        # Overlay narration on video segment
                        try:
                            video_clip = VideoFileClip(str(video_path))
                            narration_clip = AudioFileClip(str(segment_voice_path))
                            
                            # Ensure narration plays once then goes silent (no looping)
                            if narration_clip.duration > video_clip.duration:
                                # Trim to video duration with fade-out to prevent abrupt cuts
                                fade_duration = min(0.15, video_clip.duration * 0.05)
                                narration_clip = narration_clip.subclip(0, video_clip.duration)
                                narration_clip = narration_clip.audio_fadeout(fade_duration)
                            elif narration_clip.duration < video_clip.duration:
                                # Pad with silence - narration plays once then SILENT until next segment
                                from moviepy.editor import concatenate_audioclips, AudioClip
                                fade_duration = min(0.1, narration_clip.duration * 0.05)
                                narration_clip = narration_clip.audio_fadeout(fade_duration)
                                
                                # Create silence for remaining duration
                                silence_duration = video_clip.duration - narration_clip.duration
                                silence = AudioClip(lambda t: 0, duration=silence_duration, fps=narration_clip.fps)
                                
                                # Concatenate: narration + silence (plays once, then silent)
                                narration_clip = concatenate_audioclips([narration_clip, silence])
                            
                            # Mix narration with existing video audio (if any)
                            if video_clip.audio:
                                from moviepy.editor import CompositeAudioClip
                                mixed_audio = CompositeAudioClip([
                                    video_clip.audio.volumex(0.3),  # Lower original audio
                                    narration_clip.volumex(1.0)      # Full volume narration
                                ])
                                narrated_clip = video_clip.set_audio(mixed_audio)
                            else:
                                narrated_clip = video_clip.set_audio(narration_clip)
                            
                            # Save narrated video segment
                            narrated_video_path = temp_dir / f"segment_{seg_idx}_narrated.mp4"
                            narrated_clip.write_videofile(
                                str(narrated_video_path),
                                codec="libx264",
                                audio_codec="aac",
                                fps=24,
                                preset="fast",
                                verbose=False,
                                logger=None
                            )
                            
                            # Close clips
                            narrated_clip.close()
                            video_clip.close()
                            narration_clip.close()
                            
                            narrated_video_paths.append(narrated_video_path)
                            st.success(f"✅ Segment {seg_idx + 1} narrated")
                            
                        except Exception as e:
                            st.warning(f"Could not overlay narration on segment {seg_idx + 1}: {e}")
                            narrated_video_paths.append(video_path)  # Use original if overlay fails
                    
                    # Replace temp_video_paths with narrated versions
                    temp_video_paths = narrated_video_paths
                    st.success(f"✅ All {len(narrated_video_paths)} segments narrated!")
                    
                except Exception as e:
                    st.warning(f"Per-segment narration failed: {e}")
            
            # Step 5: Concatenate all video segments into final commercial
            if len(temp_video_paths) > 0:
                st.info("Step 5: Assembling final commercial video")
                try:
                    from moviepy.editor import VideoFileClip, concatenate_videoclips, AudioFileClip
                    
                    # Load all video clips with proper error handling
                    clips = []
                    try:
                        for vid_path in temp_video_paths:
                            try:
                                clip = VideoFileClip(str(vid_path))
                                clips.append(clip)
                            except Exception as e:
                                st.warning(f"Could not load {vid_path.name}: {e}")
                        
                        if not clips:
                            raise Exception("No valid video clips to concatenate")
                        
                        # Concatenate video segments
                        final_clip = concatenate_videoclips(clips, method="compose")
                        
                        # Add background music if generated (narration already overlaid per-segment)
                        if include_music and music_path and music_path.exists():
                            try:
                                music_clip = AudioFileClip(str(music_path))
                                # Loop music if video is longer
                                if music_clip.duration < final_clip.duration:
                                    loops_needed = int(final_clip.duration / music_clip.duration) + 1
                                    from moviepy.editor import concatenate_audioclips
                                    music_clip = concatenate_audioclips([music_clip] * loops_needed)
                                music_clip = music_clip.subclip(0, final_clip.duration)
                                
                                # Mix music with existing audio (narration already in video) at lower volume
                                if final_clip.audio:
                                    from moviepy.editor import CompositeAudioClip
                                    final_audio = CompositeAudioClip([
                                        final_clip.audio,  # Contains per-segment narration
                                        music_clip.volumex(0.2)  # Quiet background music
                                    ])
                                    final_clip = final_clip.set_audio(final_audio)
                                else:
                                    final_clip = final_clip.set_audio(music_clip.volumex(0.4))
                            except Exception as e:
                                st.warning(f"Could not add background music: {e}")
                        
                        # Note: Voiceover already overlaid per-segment in Step 4
                        # Each video segment now contains its corresponding narration
                        
                        # Export final commercial
                        final_video_path = temp_dir / f"{product_name.replace(' ', '_')}_commercial.mp4"
                        final_clip.write_videofile(
                            str(final_video_path),
                            codec="libx264",
                            audio_codec="aac",
                            fps=24,
                            preset="medium"
                        )
                        
                        # Close all clips to prevent broken pipe
                        final_clip.close()
                        for clip in clips:
                            try:
                                clip.close()
                            except Exception:
                                pass  # Ignore errors on close
                        
                        st.success("✅ Final commercial video assembled!")
                        st.video(str(final_video_path))
                        with open(final_video_path, "rb") as f:
                            st.download_button(
                                "🎬 Download Final Commercial",
                                f.read(),
                                f"{product_name.replace(' ', '_')}_commercial.mp4",
                                mime="video/mp4",
                                key="download_final_commercial"
                            )
                    
                    except Exception as concat_error:
                        st.error(f"Video concatenation failed: {concat_error}")
                        # Clean up clips if they exist
                        if 'final_clip' in locals():
                            try:
                                final_clip.close()
                            except Exception:
                                pass
                        if 'clips' in locals():
                            for clip in clips:
                                try:
                                    clip.close()
                                except Exception:
                                    pass
                        
                        # YouTube Auto-Upload
                        if auto_publish_youtube:
                            st.info("📺 Uploading to YouTube...")
                            try:
                                from youtube_upload_service import YouTubeUploadService
                                
                                # Initialize YouTube service
                                yt_service = YouTubeUploadService()
                                
                                if not yt_service.authenticate():
                                    st.error("❌ YouTube authentication failed")
                                    st.info("💡 Run `python setup_youtube.py` to authenticate YouTube API")
                                else:
                                    # Generate viral YouTube metadata
                                    key_benefits = f"Professional {video_style.lower()} commercial showcasing {product_name}"
                                    metadata = yt_service.generate_viral_metadata(
                                        product_name=product_name,
                                        key_benefits=key_benefits,
                                        target_audience=target_audience or "general audience",
                                        ad_tone=video_style
                                    )
                                    
                                    # Upload commercial to YouTube
                                    result = yt_service.upload_commercial(
                                        video_path=str(final_video_path),
                                        product_name=product_name,
                                        metadata=metadata,
                                        privacy="unlisted"
                                    )
                                    
                                    if result and result.get("video_id"):
                                        video_id = result["video_id"]
                                        st.success(f"✅ Uploaded to YouTube!")
                                        st.markdown(f"🎥 **Watch:** https://youtube.com/watch?v={video_id}")
                                        st.code(metadata["title"], language=None)
                                        with st.expander("📝 View YouTube Metadata"):
                                            st.write(f"**Description:**\n{metadata['description']}")
                                            st.write(f"\n**Tags:** {', '.join(metadata['tags'])}")
                                    else:
                                        st.error("YouTube upload failed - check logs")
                                        
                            except Exception as e:
                                st.error(f"YouTube upload error: {e}")
                                st.info("💡 Run `python setup_youtube.py` to authenticate YouTube API")
                    else:
                        st.warning("No valid video clips to concatenate.")
                        
                except Exception as e:
                    st.error(f"Video concatenation failed: {e}")
                    logger.error(f"Concatenation error: {e}", exc_info=True)
                    st.info("💡 You can still download individual segments above and combine manually.")
            else:
                st.warning("No video segments were generated.")
            
        except Exception as e:
            st.error(f"Video generation failed: {e}")
            logger.error(f"Video generation error: {e}", exc_info=True)
