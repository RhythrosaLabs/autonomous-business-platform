import streamlit as st
from datetime import datetime
import base64
import asyncio
import logging
import os

# Import models
from playground_models import (
    IMAGE_MODELS, VIDEO_MODELS, EDITING_MODELS, 
    VIDEO_EDITING_MODELS, MODEL_3D
)
from playground_ui_helpers import render_model_parameters, render_file_upload
from unified_storage import auto_save_generated_content

# Import helpers
from platform_helpers import (
    _render_printify_product_config, 
    _get_replicate_token
)
from cross_page_state import get_state_manager, restore_page_to_session
from api_service import ReplicateAPI

# Try to import tracked_replicate_run
try:
    from platform_integrations import tracked_replicate_run
except ImportError:
    def tracked_replicate_run(client, model, input_params, operation_name=None):
        return client.run(model, input=input_params)

# Configure logger
logger = logging.getLogger(__name__)

def render_playground_tab():
    """
    Renders the Playground tab (Tab 8).
    """
    st.markdown('<div class="main-header">🎮 AI Playground</div>', unsafe_allow_html=True)
    st.markdown("### Interactive Model Testing & Experimentation")
    st.caption("Test and experiment with cutting-edge AI models in real-time")
    
    # Restore any saved playground state
    restore_page_to_session("playground", keys_to_restore=[
        'playground_results', 'pg_img_prompt', 'playground_mode_main',
        'pg_img_model', 'pg_edit_source'
    ])
    
    # Initialize session state for playground
    if 'playground_results' not in st.session_state:
        st.session_state.playground_results = []
    
    # Printify Configuration for Playground
    with st.expander("🖨️ Printify Product Configuration", expanded=False):
        st.caption("Configure where to send designs when you click 'Print It!'")
        playground_printify_config, playground_printify_ready, _ = _render_printify_product_config(
            "Playground Printify Target",
            config_key="playground_printify_config",
            allow_auto_toggle=False,
            instructions="Select the product type, provider, and variants for quick printing from Playground"
        )
    
    playground_mode = st.radio("Mode", [
        "🖼️ Image Generation", 
        "✏️ Image Editing", 
        "📺 Ads & Marketing",
        "🎥 Video Generation",
        "🎬 Video Editing",
        "🧊 3D Generation",
        "🎵 Audio Studio",
        "📄 Document Editor",
        "📊 Spreadsheet",
        "💻 Code Playground",
        "🌐 HTML/CSS Playground",
        "🔗 Model Chaining"
    ], horizontal=True, key="playground_mode_main")
    
    if playground_mode == "🖼️ Image Generation":
        st.markdown("---")
        
        col_img1, col_img2 = st.columns([2, 1])
        
        with col_img1:
            img_prompt = st.text_area("Image Prompt", placeholder="A serene mountain landscape at sunset with cherry blossoms...", height=100, key="pg_img_prompt")
            img_upload = st.file_uploader("Optional: Reference Image", type=['jpg', 'png', 'jpeg'], key="pg_img_ref")
            
        with col_img2:
            st.markdown("**⚙️ Model Settings**")
            img_model = st.selectbox("Model", list(IMAGE_MODELS.keys()), 
                format_func=lambda x: IMAGE_MODELS[x]["name"],
                help="Select the image generation model",
                key="pg_img_model")
            
            # Show model description
            st.caption(IMAGE_MODELS[img_model]["description"])
            
        if st.button("🎨 Generate Image", type="primary", use_container_width=True, key="pg_gen_img"):
            if img_prompt:
                with st.spinner("Generating image..."):
                    try:
                        replicate_token = _get_replicate_token()
                        if replicate_token:
                            api = ReplicateAPI(api_token=replicate_token)
                            result = api.generate_image(prompt=img_prompt)
                            st.image(result, caption="Generated Image", use_container_width=True)
                            
                            # Auto-save to library and update Otto's memory
                            auto_save_generated_content(
                                content_url=result,
                                content_type="image",
                                source="playground",
                                prompt=img_prompt,
                                model=IMAGE_MODELS[img_model]["name"]
                            )
                            
                            st.session_state.playground_results.append({
                                'type': 'image',
                                'prompt': img_prompt,
                                'result': result,
                                'timestamp': datetime.now().isoformat()
                            })
                            # Save playground state for cross-page persistence
                            get_state_manager().save_page_state("playground", {
                                'playground_results': st.session_state.playground_results,
                                'last_prompt': img_prompt
                            })
                    except Exception as e:
                        st.error(f"Generation failed: {e}")
            else:
                st.warning("Please enter a prompt")
    
    elif playground_mode == "✏️ Image Editing":
        st.markdown("---")
        st.markdown("#### Edit & Transform Images")
        
        edit_col1, edit_col2 = st.columns([2, 1])
        
        with edit_col1:
            edit_source = st.radio("Source Image", ["Upload Image", "Use URL", "Use Previous Result"], horizontal=True, key="pg_edit_source")
            
            if edit_source == "Upload Image":
                edit_upload = st.file_uploader("Upload Image to Edit", type=['jpg', 'png', 'jpeg', 'webp'], key="pg_edit_upload")
                if edit_upload:
                    st.image(edit_upload, caption="Source Image", use_container_width=True)
            elif edit_source == "Use URL":
                edit_url = st.text_input("Image URL", placeholder="https://...", key="pg_edit_url")
                if edit_url:
                    st.image(edit_url, caption="Source Image", use_container_width=True)
            else:
                # Use previous result
                if st.session_state.playground_results and any(r['type'] == 'image' for r in st.session_state.playground_results):
                    last_image = next(r['result'] for r in reversed(st.session_state.playground_results) if r['type'] == 'image')
                    st.image(last_image, caption="Previous Result", use_container_width=True)
                    edit_url = last_image
                else:
                    st.info("No previous image results to use")
                    edit_url = None
            
            edit_instruction = st.text_area(
                "Edit Instructions",
                placeholder="Make it more vibrant, add a sunset background, remove the person on the left...",
                height=100,
                key="pg_edit_instr"
            )
        
        with edit_col2:
            st.markdown("**⚙️ Edit Settings**")
            edit_model = st.selectbox(
                "Editing Model",
                list(EDITING_MODELS.keys()),
                format_func=lambda x: EDITING_MODELS[x]["name"],
                key="pg_edit_model"
            )
            st.caption(EDITING_MODELS[edit_model]["description"])
            
            edit_strength = st.slider("Edit Strength", 0.1, 1.0, 0.75, 0.05, key="pg_edit_strength")
        
        if st.button("✏️ Apply Edit", type="primary", use_container_width=True, key="pg_apply_edit"):
            source_image = None
            if edit_source == "Upload Image" and edit_upload:
                source_image = f"data:image/png;base64,{base64.b64encode(edit_upload.read()).decode()}"
            elif edit_source == "Use URL" and edit_url:
                source_image = edit_url
            elif edit_source == "Use Previous Result":
                source_image = edit_url
            
            if source_image and edit_instruction:
                with st.spinner("Applying edits..."):
                    try:
                        replicate_token = _get_replicate_token()
                        if replicate_token:
                            import replicate
                            client = replicate.Client(api_token=replicate_token)
                            
                            model_id = EDITING_MODELS[edit_model]["model_id"]
                            
                            # Use tracked API call for cost monitoring
                            output = tracked_replicate_run(
                                client,
                                model_id,
                                {
                                    "image": source_image,
                                    "prompt": edit_instruction,
                                    "strength": edit_strength
                                },
                                operation_name="Image Edit - Playground"
                            )
                            
                            result_url = output[0] if isinstance(output, list) else str(output)
                            st.image(result_url, caption="Edited Image", use_container_width=True)
                            
                            st.session_state.playground_results.append({
                                'type': 'image',
                                'prompt': f"[Edit] {edit_instruction}",
                                'result': result_url,
                                'timestamp': datetime.now().isoformat()
                            })
                            # Save playground state for cross-page persistence
                            get_state_manager().save_page_state("playground", {
                                'playground_results': st.session_state.playground_results,
                                'last_edit_prompt': edit_instruction
                            })
                            
                            # Download button
                            st.markdown(f"[📥 Download Image]({result_url})")
                    except Exception as e:
                        st.error(f"Edit failed: {e}")
            else:
                st.warning("Please provide a source image and edit instructions")
    
    elif playground_mode == "🔗 Model Chaining":
        st.markdown("---")
        st.markdown("#### Chain Multiple AI Models")
        st.caption("Build pipelines that pass output from one model to the next")
        
        # Initialize chain state
        if 'chain_pipeline' not in st.session_state:
            st.session_state.chain_pipeline = []
        if 'chain_results' not in st.session_state:
            st.session_state.chain_results = []
        
        # Add step controls
        chain_col1, chain_col2 = st.columns([3, 1])
        
        with chain_col1:
            new_step_type = st.selectbox(
                "Add Step",
                ["Image Generation", "Image Editing", "Video Generation", "Text Generation"],
                key="pg_chain_new_step"
            )
        
        with chain_col2:
            if st.button("➕ Add Step", use_container_width=True, key="pg_chain_add"):
                new_step = {
                    'id': len(st.session_state.chain_pipeline) + 1,
                    'type': new_step_type,
                    'config': {},
                    'status': 'pending'
                }
                if new_step_type == "Image Generation":
                    new_step['config'] = {'prompt': '', 'model': list(IMAGE_MODELS.keys())[0]}
                elif new_step_type == "Image Editing":
                    new_step['config'] = {'instruction': '', 'model': list(EDITING_MODELS.keys())[0], 'use_previous': True}
                elif new_step_type == "Video Generation":
                    new_step['config'] = {'prompt': '', 'model': list(VIDEO_MODELS.keys())[0], 'use_previous_image': True}
                elif new_step_type == "Text Generation":
                    new_step['config'] = {'prompt': '', 'use_previous_context': True}
                
                st.session_state.chain_pipeline.append(new_step)
                st.rerun()
        
        # Display pipeline
        if st.session_state.chain_pipeline:
            st.markdown("### 🔗 Pipeline Steps")
            
            for idx, step in enumerate(st.session_state.chain_pipeline):
                with st.expander(f"**Step {idx + 1}:** {step['type']}", expanded=True):
                    step_col1, step_col2 = st.columns([4, 1])
                    
                    with step_col1:
                        if step['type'] == "Image Generation":
                            step['config']['prompt'] = st.text_area(
                                "Prompt",
                                value=step['config'].get('prompt', ''),
                                key=f"chain_img_prompt_{idx}",
                                height=80
                            )
                            step['config']['model'] = st.selectbox(
                                "Model",
                                list(IMAGE_MODELS.keys()),
                                format_func=lambda x: IMAGE_MODELS[x]["name"],
                                key=f"chain_img_model_{idx}"
                            )
                        
                        elif step['type'] == "Image Editing":
                            if idx > 0:
                                step['config']['use_previous'] = st.checkbox(
                                    "Use previous step's output",
                                    value=step['config'].get('use_previous', True),
                                    key=f"chain_edit_prev_{idx}"
                                )
                            step['config']['instruction'] = st.text_area(
                                "Edit Instruction",
                                value=step['config'].get('instruction', ''),
                                key=f"chain_edit_instr_{idx}",
                                height=80
                            )
                            step['config']['model'] = st.selectbox(
                                "Model",
                                list(EDITING_MODELS.keys()),
                                format_func=lambda x: EDITING_MODELS[x]["name"],
                                key=f"chain_edit_model_{idx}"
                            )
                        
                        elif step['type'] == "Video Generation":
                            if idx > 0:
                                step['config']['use_previous_image'] = st.checkbox(
                                    "Use previous step's image",
                                    value=step['config'].get('use_previous_image', True),
                                    key=f"chain_vid_prev_{idx}"
                                )
                            step['config']['prompt'] = st.text_area(
                                "Video Prompt/Motion",
                                value=step['config'].get('prompt', ''),
                                key=f"chain_vid_prompt_{idx}",
                                height=80
                            )
                        
                        elif step['type'] == "Text Generation":
                            step['config']['prompt'] = st.text_area(
                                "Text Prompt",
                                value=step['config'].get('prompt', ''),
                                key=f"chain_txt_prompt_{idx}",
                                height=80
                            )
                    
                    with step_col2:
                        status_icon = {'pending': '⏳', 'running': '🔄', 'complete': '✅', 'error': '❌'}.get(step['status'], '⏳')
                        st.markdown(f"**{status_icon}**")
                        
                        if st.button("🗑️", key=f"chain_del_{idx}"):
                            st.session_state.chain_pipeline.pop(idx)
                            st.rerun()
            
            # Run pipeline
            st.markdown("---")
            run_col1, run_col2, run_col3 = st.columns(3)
            
            with run_col1:
                if st.button("▶️ Run Pipeline", type="primary", use_container_width=True, key="pg_chain_run"):
                    st.session_state.chain_results = []
                    replicate_token = _get_replicate_token()
                    
                    if replicate_token:
                        import replicate
                        client = replicate.Client(api_token=replicate_token)
                        api = ReplicateAPI(api_token=replicate_token)
                        
                        progress = st.progress(0)
                        status = st.empty()
                        
                        previous_output = None
                        
                        for idx, step in enumerate(st.session_state.chain_pipeline):
                            step['status'] = 'running'
                            status.info(f"⏳ Running Step {idx + 1}: {step['type']}...")
                            
                            try:
                                if step['type'] == "Image Generation":
                                    result = api.generate_image(prompt=step['config']['prompt'])
                                    previous_output = result
                                    step['output'] = result
                                    st.session_state.chain_results.append({'step': idx + 1, 'type': 'image', 'result': result})
                                
                                elif step['type'] == "Image Editing":
                                    source = previous_output if step['config'].get('use_previous') else None
                                    if source:
                                        model_id = EDITING_MODELS[step['config']['model']]["model_id"]
                                        output = client.run(model_id, input={
                                            "image": source,
                                            "prompt": step['config']['instruction']
                                        })
                                        result = output[0] if isinstance(output, list) else str(output)
                                        previous_output = result
                                        step['output'] = result
                                        st.session_state.chain_results.append({'step': idx + 1, 'type': 'image', 'result': result})
                                
                                elif step['type'] == "Video Generation":
                                    image_input = previous_output if step['config'].get('use_previous_image') else None
                                    result = api.generate_video(
                                        prompt=step['config']['prompt'],
                                        image_url=image_input
                                    )
                                    previous_output = result
                                    step['output'] = result
                                    st.session_state.chain_results.append({'step': idx + 1, 'type': 'video', 'result': result})
                                
                                elif step['type'] == "Text Generation":
                                    result = api.generate_text(prompt=step['config']['prompt'])
                                    previous_output = result
                                    step['output'] = result
                                    st.session_state.chain_results.append({'step': idx + 1, 'type': 'text', 'result': result})
                                
                                step['status'] = 'complete'
                            except Exception as e:
                                step['status'] = 'error'
                                st.error(f"Step {idx + 1} failed: {e}")
                                break
                            
                            progress.progress((idx + 1) / len(st.session_state.chain_pipeline))
                        
                        status.success("✅ Pipeline complete!")
                    else:
                        st.error("Replicate API key required")
            
            with run_col2:
                if st.button("🔄 Reset", use_container_width=True, key="pg_chain_reset"):
                    for step in st.session_state.chain_pipeline:
                        step['status'] = 'pending'
                        step.pop('output', None)
                    st.session_state.chain_results = []
                    st.rerun()
            
            with run_col3:
                if st.button("🗑️ Clear All", use_container_width=True, key="pg_chain_clear"):
                    st.session_state.chain_pipeline = []
                    st.session_state.chain_results = []
                    st.rerun()
            
            # Show results
            if st.session_state.chain_results:
                st.markdown("### 📊 Pipeline Results")
                for res in st.session_state.chain_results:
                    with st.expander(f"Step {res['step']} - {res['type'].title()}", expanded=True):
                        if res['type'] == 'image':
                            st.image(res['result'], use_container_width=True)
                        elif res['type'] == 'video':
                            st.video(res['result'])
                        elif res['type'] == 'text':
                            st.markdown(res['result'])
                
                # Save chain as shortcut
                st.markdown("---")
                from shortcut_saver import render_save_shortcut_button, convert_chain_to_steps
                chain_steps = convert_chain_to_steps([
                    {
                        'model_type': res['type'],
                        'model': 'auto',
                        'prompt': f"Step {res['step']} output"
                    } for res in st.session_state.chain_results
                ])
                render_save_shortcut_button(
                    pipeline_name=f"Model Chain ({len(st.session_state.chain_results)} steps)",
                    pipeline_description=f"AI pipeline with {len(st.session_state.chain_results)} chained models",
                    steps=chain_steps,
                    icon="⛓️",
                    button_key="save_chain_pipeline",
                    expanded=True
                )
        else:
            st.info("👆 Add steps above to build your AI pipeline")
    
    elif playground_mode == "🎬 Video Editing":
        st.markdown("---")
        st.markdown("#### Edit & Transform Videos")
        
        vid_edit_col1, vid_edit_col2 = st.columns([2, 1])
        
        with vid_edit_col1:
            # Model selection first
            vid_edit_model = st.selectbox(
                "Editing Model",
                list(VIDEO_EDITING_MODELS.keys()),
                format_func=lambda x: VIDEO_EDITING_MODELS[x]["name"],
                key="pg_vid_edit_model"
            )
            st.caption(VIDEO_EDITING_MODELS[vid_edit_model]["description"])
            
            vid_source = st.radio("Source Video", ["Upload Video", "Use URL", "Use Previous Result"], horizontal=True, key="pg_vid_edit_source")
            
            video_to_edit = None
            if vid_source == "Upload Video":
                vid_upload = st.file_uploader("Upload Video to Edit", type=['mp4', 'mov', 'avi', 'webm'], key="pg_vid_edit_upload")
                if vid_upload:
                    st.video(vid_upload)
                    video_to_edit = vid_upload
            elif vid_source == "Use URL":
                vid_url = st.text_input("Video URL", placeholder="https://...", key="pg_vid_edit_url")
                if vid_url:
                    st.video(vid_url)
                    video_to_edit = vid_url
            else:
                if st.session_state.playground_results and any(r['type'] == 'video' for r in st.session_state.playground_results):
                    last_video = next(r['result'] for r in reversed(st.session_state.playground_results) if r['type'] == 'video')
                    st.video(last_video)
                    video_to_edit = last_video
                else:
                    st.info("No previous video results to use")
        
        with vid_edit_col2:
            st.markdown("**⚙️ Model Parameters**")
            # Dynamically render model parameters
            model_config = VIDEO_EDITING_MODELS[vid_edit_model]
            param_values = render_model_parameters(vid_edit_model, model_config, key_prefix="pg_vid_edit")
            
            # Render any file uploads needed (besides the main video)
            file_uploads = {}
            for param_name, param_config in model_config.get("parameters", {}).items():
                if param_config.get("type") == "file" and param_name != "video":
                    uploaded = render_file_upload(param_name, param_config, key_prefix="pg_vid_edit")
                    if uploaded:
                        file_uploads[param_name] = uploaded
        
        if st.button("🎬 Apply Video Edit", type="primary", use_container_width=True, key="pg_apply_vid_edit"):
            if not video_to_edit:
                st.warning("⚠️ Please provide a video to edit")
            else:
                # Check required parameters
                required_params = [p for p, cfg in model_config.get("parameters", {}).items() 
                                 if cfg.get("required") and p != "video"]
                missing = [p for p in required_params if p not in param_values and p not in file_uploads]
                
                if missing:
                    st.warning(f"⚠️ Please provide: {', '.join(missing)}")
                else:
                    with st.spinner("Processing video edit (this may take 10-15 minutes)..."):
                        try:
                            replicate_token = _get_replicate_token()
                            if replicate_token:
                                api = ReplicateAPI(api_token=replicate_token)
                                
                                # Build input params
                                input_params = {"video": video_to_edit, **param_values, **file_uploads}
                                
                                # Run the video editing model
                                result = api._run_model(vid_edit_model, input_params)
                                
                                # Handle the result
                                if result:
                                    if isinstance(result, str):
                                        video_url = result
                                    elif isinstance(result, list) and len(result) > 0:
                                        video_url = result[0] if isinstance(result[0], str) else str(result[0])
                                    else:
                                        video_url = str(result)
                                    
                                    st.video(video_url)
                                    st.success("✅ Video edit applied!")
                                    
                                    # Auto-save to library and update Otto's memory
                                    auto_save_generated_content(
                                        content_url=video_url,
                                        content_type="video",
                                        source="playground_editing",
                                        prompt=param_values.get('prompt', 'Video edit'),
                                        model=VIDEO_EDITING_MODELS[vid_edit_model]["name"],
                                        edit_type="video_transformation",
                                        **param_values
                                    )
                                    
                                    # Save to playground results
                                    st.session_state.playground_results.append({
                                        'type': 'video',
                                        'result': video_url,
                                        'prompt': param_values.get('prompt', 'Video edit'),
                                        'model': VIDEO_EDITING_MODELS[vid_edit_model]["name"],
                                        'timestamp': datetime.now().isoformat()
                                    })
                                else:
                                    st.error("❌ Video editing returned no result")
                            else:
                                st.error("❌ Replicate API token not configured")
                        except Exception as e:
                            st.error(f"Video editing failed: {e}")
                            import traceback
                            st.caption(traceback.format_exc())
    
    elif playground_mode == "📺 Ads & Marketing":
        st.markdown("---")
        st.markdown("#### Generate Marketing Ads")
        
        ad_col1, ad_col2 = st.columns([2, 1])
        with ad_col1:
            product_img_url = st.text_input("Product Image URL", placeholder="https://...", key="pg_ad_url")
            ad_prompt = st.text_area("Ad Copy/Theme", placeholder="Summer sale, vibrant colors, call to action...", height=100, key="pg_ad_prompt")
        with ad_col2:
            st.markdown("**⚙️ Ad Settings**")
            ad_model = st.selectbox("Image Model", list(IMAGE_MODELS.keys()),
                format_func=lambda x: IMAGE_MODELS[x]["name"],
                help="Select the image generation model",
                key="pg_ad_model")
            st.caption(IMAGE_MODELS[ad_model]["description"])
            
            ad_style = st.selectbox("Ad Style", ["Modern Minimal", "Bold & Vibrant", "Elegant Luxury", "Playful Fun"], key="pg_ad_style")
            ad_platform = st.selectbox("Platform", ["Instagram", "Facebook", "Twitter", "General"], key="pg_ad_platform")
        
        if st.button("📢 Generate Ad", type="primary", use_container_width=True, key="pg_gen_ad"):
            if product_img_url:
                with st.spinner("Creating ad..."):
                    try:
                        # Generate ad using Flux or image model with ad-specific prompting
                        replicate_token = _get_replicate_token()
                        if replicate_token:
                            api = ReplicateAPI(api_token=replicate_token)
                            
                            # Build ad-specific prompt
                            style_prompts = {
                                "Modern Minimal": "clean, minimalist design, white space, modern typography",
                                "Bold & Vibrant": "bold colors, energetic, dynamic composition, attention-grabbing",
                                "Elegant Luxury": "sophisticated, premium feel, gold accents, elegant typography",
                                "Playful Fun": "colorful, playful, fun elements, friendly design"
                            }
                            
                            platform_sizes = {
                                "Instagram": "1080x1080 square format",
                                "Facebook": "1200x628 landscape format",
                                "Twitter": "1200x675 landscape format",
                                "General": "1080x1080 square format"
                            }
                            
                            full_prompt = f"Professional marketing advertisement, {ad_prompt}, {style_prompts.get(ad_style, '')}, {platform_sizes.get(ad_platform, '')}, product showcase, commercial quality, high resolution"
                            
                            result = api.generate_image(prompt=full_prompt)
                            
                            if result:
                                st.image(result, caption=f"{ad_platform} Ad - {ad_style}")
                                st.success("✅ Ad generated!")
                                
                                # Save to results
                                st.session_state.playground_results.append({
                                    'type': 'ad',
                                    'result': result,
                                    'prompt': ad_prompt,
                                    'style': ad_style,
                                    'platform': ad_platform,
                                    'timestamp': datetime.now().isoformat()
                                })
                        else:
                            st.error("❌ Replicate API token not configured")
                    except Exception as e:
                        st.error(f"Ad generation failed: {e}")
            else:
                st.warning("Please provide a product image URL")
    
    elif playground_mode == "🎥 Video Generation":
        st.markdown("---")
        st.markdown("#### Generate Video Content")
        
        col_vid1, col_vid2 = st.columns([2, 1])
        
        with col_vid1:
            vid_prompt = st.text_area("Video Description", placeholder="A product rotating on a pedestal with dramatic lighting...", height=100, key="pg_vid_prompt")
            vid_ref_image = st.file_uploader("Optional: Reference Image", type=['jpg', 'png', 'jpeg'], key="pg_vid_ref")
        
        with col_vid2:
            st.markdown("**⚙️ Model Settings**")
            vid_model = st.selectbox("Model", list(VIDEO_MODELS.keys()),
                format_func=lambda x: VIDEO_MODELS[x]["name"],
                help="Select the video generation model",
                key="pg_vid_model")
            
            # Show model description
            st.caption(VIDEO_MODELS[vid_model]["description"])
            
            vid_duration = st.slider("Duration (seconds)", 3, 10, 5, key="pg_vid_dur")
            vid_fps = st.slider("FPS", 12, 30, 24, key="pg_vid_fps")
        
        if st.button("🎬 Generate Video", type="primary", use_container_width=True, key="pg_gen_vid"):
            if vid_prompt:
                with st.spinner("Generating video (this may take a few minutes)..."):
                    try:
                        replicate_token = _get_replicate_token()
                        if replicate_token:
                            api = ReplicateAPI(api_token=replicate_token)
                            
                            # Build input params based on model (note: prompt is passed separately)
                            input_params = {}
                            if "duration" in VIDEO_MODELS[vid_model].get("params", {}):
                                input_params["duration"] = vid_duration
                            if "fps" in VIDEO_MODELS[vid_model].get("params", {}):
                                input_params["fps"] = vid_fps
                            if vid_ref_image and "image" in VIDEO_MODELS[vid_model].get("params", {}):
                                input_params["image"] = vid_ref_image
                            
                            result = api.generate_video(prompt=vid_prompt, **input_params)
                            st.video(result)
                            
                            # Auto-save to library and update Otto's memory
                            auto_save_generated_content(
                                content_url=result,
                                content_type="video",
                                source="playground",
                                prompt=vid_prompt,
                                model=VIDEO_MODELS[vid_model]["name"],
                                **input_params
                            )
                            
                            # Save to playground results
                            st.session_state.playground_results.append({
                                'type': 'video',
                                'result': result,
                                'prompt': vid_prompt,
                                'model': VIDEO_MODELS[vid_model]["name"],
                                'timestamp': datetime.now().isoformat()
                            })
                    except Exception as e:
                        st.error(f"Video generation failed: {e}")
            else:
                st.warning("Please enter a video description")
    
    elif playground_mode == "🧊 3D Generation":
        st.markdown("---")
        st.markdown("#### Generate 3D Models")
        
        col_3d1, col_3d2 = st.columns([2, 1])
        
        with col_3d1:
            # Model selection first
            model_3d = st.selectbox(
                "3D Model",
                list(MODEL_3D.keys()),
                format_func=lambda x: MODEL_3D[x]["name"],
                key="pg_3d_model"
            )
            st.caption(MODEL_3D[model_3d]["description"])
            
            # Check what inputs this model needs
            model_config = MODEL_3D[model_3d]
            params = model_config.get("parameters", {})
            
            # Text prompt if available
            if "prompt" in params:
                prompt_3d = st.text_area(
                    "Prompt" + (" *" if params["prompt"].get("required") else ""),
                    placeholder="A detailed 3D model of...",
                    height=100,
                    key="pg_3d_prompt",
                    help=params["prompt"].get("help", "")
                )
            
            # Image upload if available
            if "image" in params:
                image_3d = st.file_uploader(
                    "Image" + (" *" if params["image"].get("required") else ""),
                    type=['jpg', 'png', 'jpeg', 'webp'],
                    key="pg_3d_image",
                    help=params["image"].get("help", "Input image for 3D generation")
                )
                if image_3d:
                    st.image(image_3d, caption="Input Image", use_container_width=True)
        
        with col_3d2:
            st.markdown("**⚙️ Model Parameters**")
            # Dynamically render other parameters
            param_values = render_model_parameters(model_3d, model_config, key_prefix="pg_3d")
        
        if st.button("🧊 Generate 3D Model", type="primary", use_container_width=True, key="pg_gen_3d"):
            # Build input parameters
            input_params = param_values.copy()
            
            # Add prompt if provided
            if "prompt" in params:
                if prompt_3d:
                    input_params["prompt"] = prompt_3d
                elif params["prompt"].get("required"):
                    st.warning("⚠️ Please provide a prompt")
                    st.stop()
            
            # Add image if provided
            if "image" in params:
                if image_3d:
                    input_params["image"] = image_3d
                elif params["image"].get("required"):
                    st.warning("⚠️ Please provide an image")
                    st.stop()
            
            with st.spinner("Generating 3D model (this may take 5-10 minutes)..."):
                try:
                    replicate_token = _get_replicate_token()
                    if replicate_token:
                        api = ReplicateAPI(api_token=replicate_token)
                        
                        # Run the 3D model
                        result = api._run_model(model_3d, input_params)
                        
                        # Handle result - could be GLB, OBJ, or other 3D format
                        model_url = None
                        if result:
                            if isinstance(result, str):
                                model_url = result
                            elif isinstance(result, dict):
                                # Some models return dict with multiple outputs
                                # Try common keys first
                                model_url = (result.get('glb') or 
                                           result.get('gltf') or
                                           result.get('obj') or 
                                           result.get('model') or
                                           result.get('mesh') or
                                           result.get('output'))
                                
                                # If still no URL, try to get first URL-like value
                                if not model_url:
                                    for key, value in result.items():
                                        if isinstance(value, str) and ('http' in value or 'replicate.delivery' in value):
                                            model_url = value
                                            break
                                
                            elif isinstance(result, list) and len(result) > 0:
                                # Handle list of results
                                first = result[0]
                                if isinstance(first, str):
                                    model_url = first
                                elif isinstance(first, dict):
                                    model_url = (first.get('glb') or first.get('mesh') or 
                                               first.get('model') or first.get('output'))
                                else:
                                    model_url = str(first)
                            
                            # Final fallback - shouldn't reach here but just in case
                            if not model_url:
                                st.error(f"❌ Could not extract model URL from result: {result}")
                                st.stop()
                            
                            st.success("✅ 3D model generated!")
                            st.caption(f"Model URL: {model_url[:80]}..." if len(model_url) > 80 else f"Model URL: {model_url}")
                            
                            # Auto-save to library and update Otto's memory
                            auto_save_generated_content(
                                content_url=model_url,
                                content_type="3d",
                                source="playground",
                                prompt=input_params.get('prompt', 'N/A'),
                                model=MODEL_3D[model_3d]["name"],
                                **param_values
                            )
                            
                            # Download the model file so we can display it
                            import requests
                            import tempfile
                            from pathlib import Path
                            
                            try:
                                # Download the model file
                                response = requests.get(model_url, timeout=30)
                                response.raise_for_status()
                                
                                # Determine file extension
                                if model_url.endswith('.glb'):
                                    ext = '.glb'
                                elif model_url.endswith('.gltf'):
                                    ext = '.gltf'
                                elif model_url.endswith('.obj'):
                                    ext = '.obj'
                                else:
                                    ext = '.glb'  # Default
                                
                                # Save to temp file
                                temp_dir = Path(tempfile.gettempdir())
                                model_file = temp_dir / f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
                                model_file.write_bytes(response.content)
                                
                                # Display 3D viewer
                                st.markdown("### 🎮 Interactive 3D Viewer")
                                st.caption("Click and drag to rotate • Scroll to zoom • Right-click to pan")
                                
                                # Create interactive 3D viewer using model-viewer web component
                                viewer_html = f"""
                                <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.3.0/model-viewer.min.js"></script>
                                <style>
                                    model-viewer {{
                                        width: 100%;
                                        height: 600px;
                                        background-color: #f0f0f0;
                                        border-radius: 8px;
                                    }}
                                </style>
                                <model-viewer 
                                    src="{model_url}" 
                                    alt="Generated 3D Model" 
                                    auto-rotate 
                                    camera-controls 
                                    shadow-intensity="1"
                                    exposure="1"
                                    shadow-softness="0.5"
                                    ar
                                    ar-modes="webxr scene-viewer quick-look"
                                    style="width: 100%; height: 600px;">
                                </model-viewer>
                                """
                                st.components.v1.html(viewer_html, height=620)
                                
                                # Download button with actual file
                                with open(model_file, 'rb') as f:
                                    st.download_button(
                                        label=f"📥 Download 3D Model ({ext.upper()})",
                                        data=f.read(),
                                        file_name=f"3d_model_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}",
                                        mime=f"model/{ext[1:]}",
                                        use_container_width=True
                                    )
                                
                            except Exception as download_error:
                                st.warning(f"Could not download model for preview: {download_error}")
                                # Fallback to simple link
                                st.markdown(f"[📥 Download 3D Model]({model_url})")
                            
                            # Try to display if it's a common format
                            if model_url.endswith(('.glb', '.gltf')):
                                st.caption("💡 Tip: You can also view this model in AR on supported devices!")

                            
                            # Save to playground results
                            st.session_state.playground_results.append({
                                'type': '3d',
                                'result': model_url,
                                'prompt': input_params.get('prompt', 'N/A'),
                                'model': MODEL_3D[model_3d]["name"],
                                'timestamp': datetime.now().isoformat()
                            })
                        else:
                            st.error("❌ 3D generation returned no result")
                    else:
                        st.error("❌ Replicate API token not configured")
                except Exception as e:
                    st.error(f"3D generation failed: {e}")
                    import traceback
                    st.caption(traceback.format_exc())
    
    elif playground_mode == "🎵 Audio Studio":
        st.markdown("---")
        try:
            from audio_editor import render_audio_editor_ui
            render_audio_editor_ui()
        except ImportError as e:
            st.error(f"Audio editor not available: {e}")
            st.info("Make sure audio_editor.py is in the project directory")
    
    elif playground_mode == "📄 Document Editor":
        st.markdown("---")
        try:
            from document_editor import render_document_editor_ui
            render_document_editor_ui()
        except ImportError as e:
            st.error(f"Document editor not available: {e}")
            st.info("Make sure document_editor.py is in the project directory")
    
    elif playground_mode == "📊 Spreadsheet":
        st.markdown("---")
        try:
            from spreadsheet_viewer import render_spreadsheet_viewer_ui
            render_spreadsheet_viewer_ui()
        except ImportError as e:
            st.error(f"Spreadsheet viewer not available: {e}")
            st.info("Make sure spreadsheet_viewer.py is in the project directory")
    
    elif playground_mode == "💻 Code Playground":
        st.markdown("---")
        st.markdown("### 💻 Interactive Code Playground")
        st.caption("Write, test, and execute Python code with AI assistance")
        
        code_tabs = st.tabs(["✍️ Code Editor", "🤖 AI Code Helper", "📚 Snippets"])
        
        with code_tabs[0]:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                code_input = st.text_area(
                    "Python Code",
                    height=400,
                    value='# Write your Python code here\nimport math\n\ndef hello():\n    print("Hello from the playground!")\n    return 42\n\nresult = hello()\nprint(f"Result: {result}")',
                    key="code_playground_input"
                )
            
            with col2:
                st.markdown("**🎛️ Execution Options**")
                timeout = st.slider("Timeout (seconds)", 1, 30, 5)
                show_output = st.checkbox("Show output", value=True)
                show_errors = st.checkbox("Show errors", value=True)
                
                if st.button("▶️ Run Code", type="primary", use_container_width=True):
                    if code_input.strip():
                        try:
                            from mcp_pylance_mcp_s import pylanceRunCodeSnippet
                            
                            with st.spinner("🏃 Executing code..."):
                                workspace_root = os.getcwd()
                                result = pylanceRunCodeSnippet(
                                    workspaceRoot=f"file://{workspace_root}",
                                    codeSnippet=code_input,
                                    timeout=timeout
                                )
                                
                                if show_output and result.get('stdout'):
                                    st.success("✅ Execution complete")
                                    st.code(result['stdout'], language="text")
                                
                                if show_errors and result.get('stderr'):
                                    st.error("❌ Errors:")
                                    st.code(result['stderr'], language="text")
                                
                                if not result.get('stdout') and not result.get('stderr'):
                                    st.info("✅ Code executed successfully (no output)")
                        except Exception as e:
                            st.error(f"Execution failed: {e}")
                            # Fallback to exec
                            try:
                                import io
                                import sys
                                
                                output_buffer = io.StringIO()
                                error_buffer = io.StringIO()
                                
                                sys.stdout = output_buffer
                                sys.stderr = error_buffer
                                
                                exec(code_input)
                                
                                sys.stdout = sys.__stdout__
                                sys.stderr = sys.__stderr__
                                
                                output = output_buffer.getvalue()
                                errors = error_buffer.getvalue()
                                
                                if output:
                                    st.success("✅ Output:")
                                    st.code(output, language="text")
                                if errors:
                                    st.error("❌ Errors:")
                                    st.code(errors, language="text")
                            except Exception as exec_error:
                                st.error(f"Execution error: {exec_error}")
                    else:
                        st.warning("Please enter some code")
        
        with code_tabs[1]:
            st.markdown("#### 🤖 AI Code Assistant")
            
            code_task = st.text_area(
                "Describe what you want to build:",
                height=100,
                placeholder="e.g., Create a function that calculates Fibonacci numbers"
            )
            
            if st.button("✨ Generate Code", type="primary"):
                if code_task:
                    replicate_token = _get_replicate_token()
                    if replicate_token:
                        try:
                            replicate_api = ReplicateAPI(replicate_token)
                            with st.spinner("🤖 Generating code..."):
                                prompt = f"Write Python code that: {code_task}\n\nProvide clean, commented code with proper error handling."
                                response = replicate_api.generate_text(prompt, max_tokens=800)
                                st.code(response, language="python")
                                
                                if st.button("📋 Copy to Editor"):
                                    st.session_state.code_playground_input = response
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Code generation failed: {e}")
                    else:
                        st.error("Replicate API token not configured")
        
        with code_tabs[2]:
            st.markdown("#### 📚 Code Snippets Library")
            
            snippets = {
                "Data Processing": "import pandas as pd\n\ndf = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})\nprint(df.describe())",
                "API Request": "import requests\n\nresponse = requests.get('https://api.example.com/data')\ndata = response.json()\nprint(data)",
                "File Operations": "# Read file\nwith open('file.txt', 'r') as f:\n    content = f.read()\n\n# Write file\nwith open('output.txt', 'w') as f:\n    f.write('Hello!')",
                "Data Visualization": "import matplotlib.pyplot as plt\n\nx = [1, 2, 3, 4, 5]\ny = [2, 4, 6, 8, 10]\n\nplt.plot(x, y)\nplt.xlabel('X')\nplt.ylabel('Y')\nplt.title('Sample Plot')\nplt.show()"
            }
            
            selected_snippet = st.selectbox("Select snippet:", list(snippets.keys()))
            st.code(snippets[selected_snippet], language="python")
            
            if st.button("📋 Load Snippet"):
                st.session_state.code_playground_input = snippets[selected_snippet]
                st.rerun()
    
    elif playground_mode == "🌐 HTML/CSS Playground":
        st.markdown("---")
        st.markdown("### 🌐 HTML/CSS Preview Playground")
        st.caption("Write HTML/CSS and see live preview")
        
        html_tabs = st.tabs(["✍️ Editor", "👁️ Preview", "🤖 AI Helper"])
        
        with html_tabs[0]:
            col1, col2 = st.columns(2)
            
            with col1:
                html_input = st.text_area(
                    "HTML",
                    height=400,
                    value='<!DOCTYPE html>\n<html>\n<head>\n  <title>My Page</title>\n</head>\n<body>\n  <h1>Hello World!</h1>\n  <p>Welcome to the HTML playground.</p>\n  <button onclick="alert(\'Hello!\')">Click Me</button>\n</body>\n</html>',
                    key="html_playground_input"
                )
            
            with col2:
                css_input = st.text_area(
                    "CSS",
                    height=400,
                    value='body {\n  font-family: Arial, sans-serif;\n  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);\n  color: white;\n  padding: 20px;\n}\n\nh1 {\n  text-align: center;\n  animation: fadeIn 1s;\n}\n\n@keyframes fadeIn {\n  from { opacity: 0; }\n  to { opacity: 1; }\n}\n\nbutton {\n  background: white;\n  color: #667eea;\n  border: none;\n  padding: 10px 20px;\n  border-radius: 5px;\n  cursor: pointer;\n  font-size: 16px;\n}',
                    key="css_playground_input"
                )
        
        with html_tabs[1]:
            if html_input or css_input:
                combined_html = f"""
                <style>
                {css_input}
                </style>
                {html_input}
                """
                st.markdown("#### 👁️ Live Preview")
                st.components.v1.html(combined_html, height=600, scrolling=True)
                
                st.download_button(
                    "💾 Download HTML",
                    data=combined_html,
                    file_name="playground_output.html",
                    mime="text/html"
                )
        
        with html_tabs[2]:
            st.markdown("#### 🤖 AI HTML/CSS Generator")
            
            web_task = st.text_area(
                "Describe your webpage:",
                height=100,
                placeholder="e.g., Create a landing page for a coffee shop with a hero section and menu"
            )
            
            if st.button("✨ Generate HTML/CSS", type="primary"):
                if web_task:
                    replicate_token = _get_replicate_token()
                    if replicate_token:
                        try:
                            replicate_api = ReplicateAPI(replicate_token)
                            with st.spinner("🤖 Generating HTML/CSS..."):
                                prompt = f"Create HTML and CSS for: {web_task}\n\nProvide complete, modern, responsive HTML with embedded CSS. Use best practices."
                                response = replicate_api.generate_text(prompt, max_tokens=1200)
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.code(response, language="html")
                                with col2:
                                    if st.button("📋 Load to Editor"):
                                        # Try to split HTML and CSS
                                        if '<style>' in response:
                                            parts = response.split('<style>')
                                            if len(parts) > 1:
                                                css_part = parts[1].split('</style>')[0]
                                                html_part = parts[0] + parts[1].split('</style>')[1] if '</style>' in parts[1] else ''
                                                st.session_state.html_playground_input = html_part
                                                st.session_state.css_playground_input = css_part
                                        else:
                                            st.session_state.html_playground_input = response
                                        st.rerun()
                        except Exception as e:
                            st.error(f"HTML generation failed: {e}")
                    else:
                        st.error("Replicate API token not configured")
    
    else:
        st.info(f"🚧 {playground_mode} mode coming soon!")
    
    # Show recent results
    if st.session_state.playground_results:
        st.markdown("---")
        st.markdown("### 📜 Recent Results")
        for i, result in enumerate(reversed(st.session_state.playground_results[-5:])):
            with st.expander(f"{result['type'].title()} - {result.get('timestamp', 'N/A')[:19]}"):
                if result['type'] == 'image' and result.get('result'):
                    st.image(result['result'], use_container_width=True)
                st.caption(f"Prompt: {result.get('prompt', 'N/A')}")
