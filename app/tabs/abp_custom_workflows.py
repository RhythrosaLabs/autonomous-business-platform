import json
from app.tabs.abp_imports_common import (
    st, json, os, datetime, logging, setup_logger
)

# Maintain backward compatibility alias
dt = datetime
logger = setup_logger(__name__)

from app.services.platform_integrations import tracked_replicate_run
from app.utils.ray_integration_helpers import is_ray_enabled, get_ray_manager_if_enabled
from app.services.tab_job_helpers import (
    submit_workflow_job,
    submit_batch_operation,
    collect_job_results,
    check_jobs_progress,
    are_all_jobs_done,
    wait_for_all_jobs
)
from app.services.global_job_queue import JobType, get_global_job_queue

try:
    from playground_models import (
        IMAGE_MODELS, VIDEO_MODELS, MUSIC_MODELS, SPEECH_MODELS, 
        MODEL_3D, EDITING_MODELS, MARKETING_MODELS, VIDEO_EDITING_MODELS,
        build_model_input
    )
except ImportError:
    # Fallback if playground_models is not available
    IMAGE_MODELS = {}
    VIDEO_MODELS = {}
    MUSIC_MODELS = {}
    SPEECH_MODELS = {}
    MODEL_3D = {}
    EDITING_MODELS = {}
    MARKETING_MODELS = {}
    VIDEO_EDITING_MODELS = {}
    def build_model_input(*args, **kwargs): return {}

try:
    from app.services.platform_helpers import _get_printify_api, _send_design_to_printify
except ImportError:
    def _get_printify_api(): return None
    def _send_design_to_printify(*args, **kwargs): return {}

def render_custom_workflows_tab():
    """
    Renders the Custom Workflows tab (Tab 9).
    """
    st.markdown('<div class="main-header">🔧 Custom Workflows</div>', unsafe_allow_html=True)
    st.markdown("### AI-Powered Automation Pipelines")
    
    # Initialize workflow state
    if 'workflows' not in st.session_state:
        st.session_state.workflows = {}
    if 'current_workflow' not in st.session_state:
        st.session_state.current_workflow = None
    if 'workflow_running' not in st.session_state:
        st.session_state.workflow_running = False
    
    # Top action bar
    col_top1, col_top2, col_top3, col_top4 = st.columns([2, 1, 1, 1])
    
    with col_top1:
        workflow_name = st.text_input("Workflow Name", placeholder="e.g., Daily Product Campaign", key="workflow_name_input_exp")
    
    with col_top2:
        if st.button("💾 Save Workflow", use_container_width=True, disabled=not workflow_name):
            if workflow_name and st.session_state.current_workflow:
                st.session_state.workflows[workflow_name] = st.session_state.current_workflow.copy()
                st.success(f"✅ Saved '{workflow_name}'")
    
    with col_top3:
        workflow_file = st.file_uploader("📁 Load", type=['json'], key="workflow_upload_exp", label_visibility="collapsed")
        if workflow_file:
            loaded_workflow = json.load(workflow_file)
            st.session_state.current_workflow = loaded_workflow
            st.success("✅ Workflow loaded")
            st.rerun()
    
    with col_top4:
        if st.session_state.current_workflow:
            workflow_json = json.dumps(st.session_state.current_workflow, indent=2)
            st.download_button("📥 Export", workflow_json, "workflow.json", use_container_width=True)
    
    # Workflow tabs - Added universal Workflow Import tab
    wf_tabs = st.tabs(["🔨 Build", "📚 Templates", "📥 Import Workflow", "📜 History", "⚙️ Saved Workflows"])
    
    # BUILD TAB
    with wf_tabs[0]:
        if st.session_state.current_workflow is None:
            st.session_state.current_workflow = {'steps': [], 'schedule': None, 'outputs': []}
        
        workflow = st.session_state.current_workflow
        
        st.markdown("### 🔗 Workflow Steps")
        
        # Add step buttons
        col_add1, col_add2 = st.columns([1, 3])
        
        with col_add1:
            step_category = st.selectbox(
                "Add Step",
                ["🎨 AI Generation", "✏️ AI Editing", "📤 Distribution", "⏱️ Scheduling", "🔄 Logic"],
                key="step_category_select_exp"
            )
        
        with col_add2:
            if step_category == "🎨 AI Generation":
                step_options = [
                    "Generate Image (AI)",
                    "Generate Video (AI)",
                    "Generate Music (AI)",
                    "Generate Speech (AI)",
                    "Generate 3D Model (AI)"
                ]
            elif step_category == "✏️ AI Editing":
                step_options = [
                    "Edit Image (AI)",
                    "Edit Video (AI)",
                    "Create Ad (AI)",
                    "Enhance/Upscale"
                ]
            elif step_category == "📤 Distribution":
                step_options = [
                    "Upload to Printify",
                    "Post to Twitter",
                    "Post to Instagram",
                    "Upload to YouTube",
                    "Save to Folder"
                ]
            elif step_category == "⏱️ Scheduling":
                step_options = [
                    "Wait/Delay",
                    "Schedule for Later",
                    "Repeat Daily",
                    "Repeat Weekly"
                ]
            else:  # Logic
                step_options = [
                    "Conditional Branch",
                    "Loop/Iterate",
                    "Merge Outputs",
                    "Split Pipeline"
                ]
            
            col_sel, col_btn = st.columns([3, 1])
            with col_sel:
                selected_step = st.selectbox("Step Type", step_options, key="step_type_select_exp", label_visibility="collapsed")
            with col_btn:
                if st.button("➕ Add", use_container_width=True, type="primary", key="add_step_btn_exp"):
                    new_step = {
                        'id': len(workflow['steps']) + 1,
                        'category': step_category,
                        'type': selected_step,
                        'config': {},
                        'enabled': True
                    }
                    workflow['steps'].append(new_step)
                    st.rerun()
        
        st.markdown("---")
        
        # Display workflow steps
        if workflow['steps']:
            for idx, step in enumerate(workflow['steps']):
                with st.expander(
                    f"**Step {idx + 1}:** {step['type']} {'✅' if step['enabled'] else '❌'}",
                    expanded=idx == len(workflow['steps']) - 1
                ):
                    col_cfg1, col_cfg2 = st.columns([4, 1])
                    
                    with col_cfg1:
                        st.markdown(f"**Category:** {step['category']}")
                        
                        # Configure based on step type
                        if "Generate Image" in step['type']:
                            step['config']['model'] = st.selectbox(
                                "Image Model",
                                list(IMAGE_MODELS.keys()),
                                format_func=lambda x: IMAGE_MODELS[x]["name"],
                                key=f"wf_img_model_{idx}_exp"
                            )
                            step['config']['prompt'] = st.text_area(
                                "Prompt",
                                value=step['config'].get('prompt', ''),
                                key=f"wf_img_prompt_{idx}_exp",
                                height=80
                            )
                            step['config']['use_previous_output'] = st.checkbox(
                                "Use previous step's text output as prompt",
                                value=step['config'].get('use_previous_output', False),
                                key=f"wf_img_use_prev_{idx}_exp"
                            )
                        
                        elif "Generate Video" in step['type']:
                            step['config']['model'] = st.selectbox(
                                "Video Model",
                                list(VIDEO_MODELS.keys()),
                                format_func=lambda x: VIDEO_MODELS[x]["name"],
                                key=f"wf_vid_model_{idx}_exp"
                            )
                            step['config']['prompt'] = st.text_area(
                                "Motion Prompt",
                                value=step['config'].get('prompt', ''),
                                key=f"wf_vid_prompt_{idx}_exp",
                                height=80
                            )
                            step['config']['use_previous_image'] = st.checkbox(
                                "Use previous step's image as first frame",
                                value=step['config'].get('use_previous_image', False),
                                key=f"wf_vid_use_img_{idx}_exp"
                            )
                        
                        elif "Generate Music" in step['type']:
                            step['config']['model'] = st.selectbox(
                                "Music Model",
                                list(MUSIC_MODELS.keys()),
                                format_func=lambda x: MUSIC_MODELS[x]["name"],
                                key=f"wf_music_model_{idx}_exp"
                            )
                            step['config']['prompt'] = st.text_input(
                                "Music Description",
                                value=step['config'].get('prompt', ''),
                                key=f"wf_music_prompt_{idx}_exp",
                                placeholder="upbeat electronic dance music"
                            )
                            step['config']['duration'] = st.slider(
                                "Duration (seconds)",
                                5, 60, step['config'].get('duration', 30),
                                key=f"wf_music_dur_{idx}_exp"
                            )
                        
                        elif "Generate Speech" in step['type']:
                            step['config']['model'] = st.selectbox(
                                "Speech Model",
                                list(SPEECH_MODELS.keys()),
                                format_func=lambda x: SPEECH_MODELS[x]["name"],
                                key=f"wf_speech_model_{idx}_exp"
                            )
                            step['config']['text'] = st.text_area(
                                "Text to Speak",
                                value=step['config'].get('text', ''),
                                key=f"wf_speech_text_{idx}_exp",
                                height=80
                            )
                            step['config']['use_previous_text'] = st.checkbox(
                                "Use previous step's output as text",
                                value=step['config'].get('use_previous_text', False),
                                key=f"wf_speech_use_prev_{idx}_exp"
                            )
                        
                        elif "Generate 3D" in step['type']:
                            step['config']['model'] = st.selectbox(
                                "3D Model",
                                list(MODEL_3D.keys()),
                                format_func=lambda x: MODEL_3D[x]["name"],
                                key=f"wf_3d_model_{idx}_exp"
                            )
                            step['config']['prompt'] = st.text_input(
                                "Description",
                                value=step['config'].get('prompt', ''),
                                key=f"wf_3d_prompt_{idx}_exp"
                            )
                            step['config']['use_previous_image'] = st.checkbox(
                                "Use previous step's image",
                                value=step['config'].get('use_previous_image', False),
                                key=f"wf_3d_use_img_{idx}_exp"
                            )
                        
                        elif "Edit Image" in step['type']:
                            step['config']['model'] = st.selectbox(
                                "Editing Model",
                                list(EDITING_MODELS.keys()),
                                format_func=lambda x: EDITING_MODELS[x]["name"],
                                key=f"wf_edit_model_{idx}_exp"
                            )
                            step['config']['instruction'] = st.text_area(
                                "Edit Instruction",
                                value=step['config'].get('instruction', ''),
                                key=f"wf_edit_instr_{idx}_exp",
                                placeholder="make it more vibrant and colorful"
                            )
                        
                        elif "Create Ad" in step['type']:
                            step['config']['model'] = st.selectbox(
                                "Ad Model",
                                list(MARKETING_MODELS.keys()),
                                format_func=lambda x: MARKETING_MODELS[x]["name"],
                                key=f"wf_ad_model_{idx}_exp"
                            )
                            step['config']['product_name'] = st.text_input(
                                "Product Name",
                                value=step['config'].get('product_name', ''),
                                key=f"wf_ad_name_{idx}_exp"
                            )
                        
                        elif "Upload to Printify" in step['type']:
                            step['config']['product_type'] = st.selectbox(
                                "Product Type",
                                ["T-Shirt", "Mug", "Poster", "Phone Case", "Hoodie", "Tote Bag"],
                                key=f"wf_print_type_{idx}_exp"
                            )
                            step['config']['auto_publish'] = st.checkbox(
                                "Auto-publish to store",
                                value=step['config'].get('auto_publish', False),
                                key=f"wf_print_pub_{idx}_exp"
                            )
                        
                        elif "Post to Twitter" in step['type']:
                            step['config']['tweet_text'] = st.text_area(
                                "Tweet Text",
                                value=step['config'].get('tweet_text', ''),
                                key=f"wf_tweet_text_{idx}_exp",
                                height=100,
                                placeholder="Check out this amazing product! #AI #Generated"
                            )
                            step['config']['attach_media'] = st.checkbox(
                                "Attach previous step's media",
                                value=step['config'].get('attach_media', True),
                                key=f"wf_tweet_media_{idx}_exp"
                            )
                        
                        elif "Upload to YouTube" in step['type']:
                            step['config']['title'] = st.text_input(
                                "Video Title",
                                value=step['config'].get('title', ''),
                                key=f"wf_yt_title_{idx}_exp"
                            )
                            step['config']['description'] = st.text_area(
                                "Description",
                                value=step['config'].get('description', ''),
                                key=f"wf_yt_desc_{idx}_exp",
                                height=100
                            )
                            step['config']['privacy'] = st.selectbox(
                                "Privacy",
                                ["public", "unlisted", "private"],
                                key=f"wf_yt_privacy_{idx}_exp"
                            )
                        
                        elif "Wait/Delay" in step['type']:
                            step['config']['delay_seconds'] = st.number_input(
                                "Delay (seconds)",
                                min_value=1,
                                max_value=3600,
                                value=step['config'].get('delay_seconds', 60),
                                key=f"wf_delay_{idx}_exp"
                            )
                        
                        elif "Schedule for Later" in step['type']:
                            step['config']['scheduled_time'] = st.time_input(
                                "Time to Run",
                                key=f"wf_sched_time_{idx}_exp"
                            )
                            step['config']['scheduled_date'] = st.date_input(
                                "Date",
                                key=f"wf_sched_date_{idx}_exp"
                            )
                        
                        elif "Conditional Branch" in step['type']:
                            step['config']['condition'] = st.selectbox(
                                "If",
                                ["Previous step succeeded", "Previous step failed", "Output contains text", "Output is image"],
                                key=f"wf_cond_{idx}_exp"
                            )
                            step['config']['then_action'] = st.text_input(
                                "Then (step ID to jump to)",
                                value=step['config'].get('then_action', ''),
                                key=f"wf_then_{idx}_exp"
                            )
                        
                        elif "Enhance" in step['type'] or "Upscale" in step['type']:
                            step['config']['scale'] = st.selectbox(
                                "Upscale Factor",
                                [2, 4],
                                index=0 if step['config'].get('scale', 2) == 2 else 1,
                                key=f"wf_upscale_{idx}_exp"
                            )
                            st.caption("Uses previous step's image as input")
                        
                        elif "Save to Folder" in step['type']:
                            step['config']['folder_path'] = st.text_input(
                                "Folder Path",
                                value=step['config'].get('folder_path', './outputs'),
                                key=f"wf_folder_{idx}_exp"
                            )
                            step['config']['filename'] = st.text_input(
                                "Filename (without extension)",
                                value=step['config'].get('filename', ''),
                                key=f"wf_filename_{idx}_exp",
                                placeholder="Leave blank for auto-generated name"
                            )
                    
                    with col_cfg2:
                        step['enabled'] = st.checkbox(
                            "Enabled",
                            value=step['enabled'],
                            key=f"wf_enabled_{idx}_exp"
                        )
                        if st.button("🔼", key=f"wf_up_{idx}_exp", disabled=idx == 0, use_container_width=True):
                            workflow['steps'][idx], workflow['steps'][idx-1] = workflow['steps'][idx-1], workflow['steps'][idx]
                            st.rerun()
                        if st.button("🔽", key=f"wf_down_{idx}_exp", disabled=idx == len(workflow['steps'])-1, use_container_width=True):
                            workflow['steps'][idx], workflow['steps'][idx+1] = workflow['steps'][idx+1], workflow['steps'][idx]
                            st.rerun()
                        if st.button("❌", key=f"wf_del_{idx}_exp", use_container_width=True):
                            workflow['steps'].pop(idx)
                            st.rerun()
            
            st.markdown("---")
            
            # Show reset button if workflow is stuck
            if st.session_state.get('workflow_running', False):
                if st.button("🔄 Reset (Workflow Stuck?)", type="secondary", help="Click if workflow button is disabled"):
                    st.session_state.workflow_running = False
                    st.rerun()
            
            # Run workflow button
            col_run1, col_run2, col_run3 = st.columns([2, 1, 1])
            
            with col_run1:
                # Background execution option
                bg_workflow = st.checkbox(
                    "🌐 Run in background",
                    value=True,
                    key="bg_workflow_option",
                    help="Continue running while navigating other pages"
                )
                
                # Ensure workflow_running isn't stuck
                if 'workflow_running' not in st.session_state:
                    st.session_state.workflow_running = False
                
                if st.button("▶️ Run Workflow (Ultra Smart)", type="primary", use_container_width=True, disabled=st.session_state.workflow_running, key="run_workflow_exp"):
                    st.session_state.workflow_running = True
                    workflow['outputs'] = []
                    
                    if bg_workflow:
                        # Execute in background
                        try:
                            from app.services.background_tasks import BackgroundTaskManager, get_task_manager
                            
                            task_mgr = get_task_manager()  # Use cached manager
                            
                            # Create task
                            task = task_mgr.create_task(
                                name=f"🔧 {workflow_name or 'Workflow'}",
                                description=f"Running workflow with {len([s for s in workflow.get('steps', []) if s.get('enabled', True)])} steps"
                            )
                            
                            # Define the task function
                            def run_workflow_async(task, stop_flag, update_callback):
                                try:
                                    from ultra_smart_executor import UltraSmartExecutor
                                    executor = UltraSmartExecutor()
                                    
                                    steps = workflow.get('steps', [])
                                    enabled_steps = [s for s in steps if s.get('enabled', True)]
                                    task.total_steps = len(enabled_steps)
                                    
                                    results = []
                                    for step_idx, step in enumerate(enabled_steps):
                                        if stop_flag.is_set():
                                            break
                                        
                                        current_step = step_idx + 1
                                        task.completed_steps = current_step
                                        task.progress = current_step / len(enabled_steps)
                                        task.current_step = f"Step {current_step}/{len(enabled_steps)}: {step['type']}"
                                        task.logs.append(f"Starting {step['type']}")
                                        update_callback()
                                        
                                        # Execute step
                                        capability, expected_output = executor._analyze_step_intent(step)
                                        enriched_config = executor._enrich_config(step, capability)
                                        result = executor._execute_with_recovery(
                                            step_idx + 1, step['type'], enriched_config,
                                            capability, expected_output
                                        )
                                        
                                        results.append({
                                            'step': step['type'],
                                            'output_url': result.output_url,
                                            'status': result.status.value
                                        })
                                        task.logs.append(f"Completed {step['type']}: {result.status.value}")
                                        update_callback()
                                    
                                    return {'results': results, 'completed': len(results)}
                                except Exception as e:
                                    task.logs.append(f"ERROR: {str(e)}")
                                    raise
                            
                            # Start the task
                            task_mgr.start_task(task.id, run_workflow_async)
                            
                            st.success(f"✅ Workflow started in background! Task ID: {task.id}")
                            st.info("💡 Check the progress indicator at the top. You can navigate away and it will keep running.")
                            st.session_state.workflow_running = False
                            st.rerun()
                            
                        except ImportError as ie:
                            st.warning(f"⚠️ Background execution not available: {ie}")
                            bg_workflow = False
                        except Exception as e:
                            import traceback
                            st.error(f"❌ Failed to start background task: {e}")
                            st.error(f"**Traceback:** ```\n{traceback.format_exc()}\n```")
                            bg_workflow = False
                    
                    if not bg_workflow:
                        # Execute in foreground with progress display
                        try:
                            # Use Ultra Smart Executor for maximum intelligence
                            from ultra_smart_executor import UltraSmartExecutor, StepStatus, get_execution_summary
                            
                            executor = UltraSmartExecutor()
                            
                            # Progress display
                            progress_bar = st.progress(0)
                            status_container = st.container()
                            results_display = st.container()
                            
                            # Execute with ultra smart executor
                            results = []
                            steps = workflow.get('steps', [])
                            enabled_steps = [s for s in steps if s.get('enabled', True)]
                            
                            # Show disabled steps info
                            disabled_count = len(steps) - len(enabled_steps)
                            if disabled_count > 0:
                                with status_container:
                                    st.info(f"⏭️ {disabled_count} step(s) disabled by user")
                            
                            for step_idx, step in enumerate(enabled_steps):
                                progress_bar.progress((step_idx) / max(len(enabled_steps), 1))
                                
                                with st.status(f"🧠 Step {step_idx + 1}: {step['type']}...", expanded=True) as status:
                                    # Analyze intent first
                                    capability, expected_output = executor._analyze_step_intent(step)
                                    st.caption(f"Intent: {capability} → {expected_output.value if hasattr(expected_output, 'value') else expected_output}")
                                    
                                    # Enrich config with context
                                    enriched_config = executor._enrich_config(step, capability)
                                    if enriched_config.get('_auto_filled'):
                                        st.caption(f"🔗 Auto-filled: {enriched_config['_auto_filled']}")
                                
                                # Execute with multi-level recovery
                                import time
                                start_time = time.time()
                                result = executor._execute_with_recovery(
                                    step_idx + 1, step['type'], enriched_config, 
                                    capability, expected_output
                                )
                                result.execution_time = time.time() - start_time
                                
                                results.append(result)
                                executor.context.add_output(result)
                                
                                # Display result based on status
                                if result.status == StepStatus.SUCCESS:
                                    st.success(f"✅ {result.message}")
                                    status.update(label=f"✅ Step {step_idx + 1} complete!", state="complete")
                                elif result.status == StepStatus.WORKAROUND:
                                    st.warning(f"🔄 {result.message}")
                                    if result.workaround_used:
                                        st.caption(f"💡 Workaround: {result.workaround_used}")
                                    status.update(label=f"🔄 Step {step_idx + 1} (workaround)", state="complete")
                                elif result.status == StepStatus.ADAPTED:
                                    st.info(f"🔧 {result.message}")
                                    if result.adaptation_notes:
                                        st.caption(f"📝 {result.adaptation_notes}")
                                    status.update(label=f"🔧 Step {step_idx + 1} (adapted)", state="complete")
                                else:
                                    st.error(f"❌ {result.message}")
                                    status.update(label=f"❌ Step {step_idx + 1} failed", state="error")
                                
                                # Show fallbacks tried if any
                                if result.fallbacks_tried:
                                    st.caption(f"🔄 Tried {len(result.fallbacks_tried)} fallback(s)")
                                
                                # Display output
                                output_type = result.output_type.value if hasattr(result.output_type, 'value') else str(result.output_type)
                                if result.output_url:
                                    if output_type == 'image':
                                        st.image(result.output_url)
                                    elif output_type == 'video':
                                        st.video(result.output_url)
                                    elif output_type == 'audio':
                                        st.audio(result.output_url)
                                    
                                    workflow['outputs'].append({
                                        'step': step_idx + 1,
                                        'type': output_type,
                                        'url': result.output_url,
                                        'model': result.model_used
                                    })
                                
                                st.caption(f"⏱️ {result.execution_time:.1f}s")
                            
                            progress_bar.progress(1.0)
                            
                            # Get comprehensive summary
                            summary = get_execution_summary(results)
                            success_count = summary['success']
                            workaround_count = summary['workaround']
                            adapted_count = summary['adapted']
                            failed_count = summary['failed']
                            
                            # Display enhanced summary
                            if failed_count == 0:
                                total_successful = success_count + workaround_count + adapted_count
                                st.success(f"🎉 Workflow completed! {success_count} perfect, {workaround_count} workarounds, {adapted_count} adapted")
                                st.balloons()
                                
                                # Show execution stats
                                with st.expander("📊 Execution Statistics"):
                                    stat_cols = st.columns(4)
                                    with stat_cols[0]:
                                        st.metric("Total Time", f"{summary['total_time']:.1f}s")
                                    with stat_cols[1]:
                                        st.metric("Avg/Step", f"{summary['avg_time_per_step']:.1f}s")
                                    with stat_cols[2]:
                                        st.metric("Success Rate", f"{summary['success_rate']*100:.0f}%")
                                    with stat_cols[3]:
                                        st.metric("Models Used", len(summary['models_used']))
                                    
                                    if summary['models_used']:
                                        st.caption(f"Models: {', '.join(summary['models_used'][:5])}")
                                
                                # Save as Shortcut button
                                st.markdown("---")
                                from shortcut_saver import render_save_shortcut_button, convert_workflow_to_steps
                                workflow_steps = convert_workflow_to_steps({
                                    'name': workflow['name'],
                                    'steps': [{'name': step.get('name', ''), 'type': 'generate', 'action': '/image', 'prompt': step.get('prompt', '')} for step in workflow.get('steps', [])]
                                })
                                render_save_shortcut_button(
                                    pipeline_name=workflow['name'],
                                    pipeline_description=f"Workflow with {len(workflow_steps)} steps",
                                    steps=workflow_steps,
                                    icon="🔄",
                                    button_key=f"save_workflow_{workflow['name']}",
                                    expanded=True
                                )
                            else:
                                st.warning(f"⚠️ Workflow finished: {failed_count} issues, {success_count + workaround_count + adapted_count} completed")
                            
                        except ImportError as ie:
                            st.error(f"Ultra Smart executor not available: {ie}")
                            st.info("Falling back to basic execution...")
                        except Exception as e:
                            st.error(f"Workflow error: {e}")
                            import traceback
                            st.code(traceback.format_exc())
                        finally:
                            st.session_state.workflow_running = False
            
            with col_run2:
                enabled_count = sum(1 for s in workflow['steps'] if s['enabled'])
                st.caption(f"{enabled_count}/{len(workflow['steps'])} steps enabled")
            
            with col_run3:
                if st.button("🗑️ Clear All", use_container_width=True, key="clear_all_exp"):
                    st.session_state.current_workflow = {'steps': [], 'schedule': None, 'outputs': []}
                    st.rerun()
        
        else:
            st.info("💡 **Get Started:** Select a step category above and click 'Add' to build your workflow")
            
            st.markdown("### 🌟 What You Can Build")
            
            ex_col1, ex_col2, ex_col3 = st.columns(3)
            
            with ex_col1:
                st.markdown("""
                **🎨 Content Creation**
                - Generate product images
                - Create marketing videos
                - Design social media ads
                - Produce 3D visualizations
                """)
            
            with ex_col2:
                st.markdown("""
                **📤 Auto-Distribution**
                - Post to social media
                - Upload to marketplaces
                - Publish to YouTube
                - Email campaigns
                """)
            
            with ex_col3:
                st.markdown("""
                **⏱️ Automation**
                - Schedule campaigns
                - Repeat daily/weekly
                - Conditional logic
                - Multi-platform sync
                """)
    
    # TEMPLATES TAB
    with wf_tabs[1]:
        st.markdown("### 📚 Workflow Templates")
        st.caption("Pre-built workflows for common marketing tasks")
        
        # Import and display workflow templates
        try:
            from workflow_templates import WORKFLOW_TEMPLATES, WorkflowTemplateManager
            
            template_manager = WorkflowTemplateManager()
            
            # Template categories
            template_categories = {}
            for tid, template in WORKFLOW_TEMPLATES.items():
                cat = template.get('category', 'general')
                if cat not in template_categories:
                    template_categories[cat] = []
                template_categories[cat].append((tid, template))
            
            for category, templates in template_categories.items():
                st.markdown(f"#### {category.replace('_', ' ').title()}")
                
                cols = st.columns(2)
                for i, (tid, template) in enumerate(templates):
                    with cols[i % 2]:
                        with st.container(border=True):
                            st.markdown(f"**{template['name']}**")
                            st.caption(template.get('description', ''))
                            st.markdown(f"⏱️ ~{template.get('estimated_time', '?')} min • {len(template.get('steps', []))} steps")
                            
                            col_use, col_view = st.columns(2)
                            with col_use:
                                if st.button("▶️ Use", key=f"use_template_{tid}", use_container_width=True):
                                    # Load template into current workflow
                                    st.session_state.current_workflow = template_manager.instantiate_template(tid)
                                    st.success(f"✅ Loaded {template['name']}")
                                    st.rerun()
                            with col_view:
                                if st.button("👁️ View", key=f"view_template_{tid}", use_container_width=True):
                                    st.session_state[f'viewing_template_{tid}'] = True
                            
                            if st.session_state.get(f'viewing_template_{tid}'):
                                st.markdown("**Steps:**")
                                for step in template.get('steps', []):
                                    st.markdown(f"• {step.get('name', step.get('type', '?'))}")
                
                st.markdown("---")
        except ImportError:
            st.info("Workflow templates module not available")
        
        st.markdown("---")
        st.markdown("#### 🔗 Model Chaining (Legacy)")
        
        # Ensure chain_pipeline is initialized
        if 'chain_pipeline' not in st.session_state:
            st.session_state.chain_pipeline = []
        if 'chain_results' not in st.session_state:
            st.session_state.chain_results = []
        
        # Display and configure each step
        for step_idx in range(len(st.session_state.chain_pipeline)):
            step = st.session_state.chain_pipeline[step_idx]
            
            with st.expander(
                f"**Step {step_idx + 1}:** {step['type']} → {step.get('output', '?')}",
                expanded=step_idx == len(st.session_state.chain_pipeline) - 1
            ):
                col_step1, col_step2 = st.columns([3, 1])
                
                with col_step1:
                    # Step type selector
                    step_type_options = [
                        "Image Generation",
                        "Image Editing", 
                        "Ads & Marketing",
                        "Video Generation",
                        "Video Editing",
                        "3D Generation",
                        "Music Generation",
                        "Speech Synthesis"
                    ]
                    
                    new_step_type = st.selectbox(
                        "Step Type",
                        step_type_options,
                        index=step_type_options.index(step['type']) if step['type'] in step_type_options else 0,
                        key=f"chain_step_type_{step_idx}"
                    )
                    
                    # Update step type if changed
                    if new_step_type != step['type']:
                        step['type'] = new_step_type
                        # Reset model selection when type changes
                        if new_step_type == "Image Generation":
                            step['model'] = list(IMAGE_MODELS.keys())[0]
                            step['output'] = 'image'
                        elif new_step_type == "Image Editing":
                            step['model'] = list(EDITING_MODELS.keys())[0]
                            step['output'] = 'image'
                        elif new_step_type == "Ads & Marketing":
                            step['model'] = list(MARKETING_MODELS.keys())[0]
                            step['output'] = 'image'
                        elif new_step_type == "Video Generation":
                            step['model'] = list(VIDEO_MODELS.keys())[0]
                            step['output'] = 'video'
                        elif new_step_type == "Video Editing":
                            step['model'] = list(VIDEO_EDITING_MODELS.keys())[0]
                            step['output'] = 'video'
                        elif new_step_type == "3D Generation":
                            step['model'] = list(MODEL_3D.keys())[0]
                            step['output'] = '3d_model'
                        elif new_step_type == "Music Generation":
                            step['model'] = list(MUSIC_MODELS.keys())[0]
                            step['output'] = 'audio'
                        elif new_step_type == "Speech Synthesis":
                            step['model'] = list(SPEECH_MODELS.keys())[0]
                            step['output'] = 'audio'
                        step['params'] = {}
                
                with col_step2:
                    if st.button("❌ Remove", key=f"chain_remove_{step_idx}", use_container_width=True):
                        st.session_state.chain_pipeline.pop(step_idx)
                        st.rerun()
                
                # Model selector based on step type
                if step['type'] == "Image Generation":
                    models_dict = IMAGE_MODELS
                elif step['type'] == "Image Editing":
                    models_dict = EDITING_MODELS
                elif step['type'] == "Ads & Marketing":
                    models_dict = MARKETING_MODELS
                elif step['type'] == "Video Generation":
                    models_dict = VIDEO_MODELS
                elif step['type'] == "Video Editing":
                    models_dict = VIDEO_EDITING_MODELS
                elif step['type'] == "3D Generation":
                    models_dict = MODEL_3D
                elif step['type'] == "Music Generation":
                    models_dict = MUSIC_MODELS
                elif step['type'] == "Speech Synthesis":
                    models_dict = SPEECH_MODELS
                else:
                    models_dict = IMAGE_MODELS
                
                # Model selection
                selected_model = st.selectbox(
                    "Model",
                    list(models_dict.keys()),
                    format_func=lambda x: models_dict[x]["name"],
                    key=f"chain_model_{step_idx}",
                    index=list(models_dict.keys()).index(step['model']) if step['model'] in models_dict else 0
                )
                step['model'] = selected_model
                
                model_config = models_dict[selected_model]
                st.caption(f"💡 {model_config['description']}")
                
                # Input source indicator
                if step_idx == 0:
                    st.info("📥 **Input:** Manual input (you provide the starting point)")
                else:
                    prev_output = st.session_state.chain_pipeline[step_idx - 1].get('output', 'unknown')
                    st.info(f"📥 **Input:** Output from Step {step_idx} ({prev_output})")
                
                # Dynamic parameters
                st.markdown("**Parameters:**")
                step_params = {}
                
                for param_name, param_config in model_config["parameters"].items():
                    param_key = f"chain_param_{step_idx}_{param_name}"
                    
                    # Skip file uploads for chained steps (use previous output)
                    if param_config["type"] == "file" and step_idx > 0:
                        st.caption(f"🔗 `{param_name}` will use output from previous step")
                        continue
                    
                    # Generate label
                    label = param_name.replace("_", " ").title()
                    
                    if param_config["type"] == "select":
                        step_params[param_name] = st.selectbox(
                            label,
                            options=param_config["options"],
                            index=param_config["options"].index(param_config["default"]) if param_config["default"] in param_config["options"] else 0,
                            key=param_key,
                            help=param_config.get("help", "")
                        )
                    
                    elif param_config["type"] == "slider":
                        step_params[param_name] = st.slider(
                            label,
                            min_value=param_config["min"],
                            max_value=param_config["max"],
                            value=param_config["default"],
                            step=param_config.get("step", 1),
                            key=param_key,
                            help=param_config.get("help", "")
                        )
                    
                    elif param_config["type"] == "number":
                        step_params[param_name] = st.number_input(
                            label,
                            min_value=param_config.get("min", 0),
                            max_value=param_config.get("max", 999999),
                            value=param_config["default"],
                            key=param_key,
                            help=param_config.get("help", "")
                        )
                    
                    elif param_config["type"] == "checkbox":
                        step_params[param_name] = st.checkbox(
                            label,
                            value=param_config["default"],
                            key=param_key,
                            help=param_config.get("help", "")
                        )
                    
                    elif param_config["type"] == "text":
                        step_params[param_name] = st.text_input(
                            label,
                            value=param_config["default"],
                            key=param_key,
                            help=param_config.get("help", "")
                        )
                    
                    elif param_config["type"] == "file" and step_idx == 0:
                        # Only show file upload for first step
                        st.markdown(f"**{label}**")
                        if param_config.get("help"):
                            st.caption(param_config.get("help"))
                        uploaded = st.file_uploader(
                            label,
                            type=["png", "jpg", "jpeg", "webp", "mp4"],
                            key=param_key,
                            label_visibility="collapsed"
                        )
                        if uploaded:
                            step_params[param_name] = uploaded
                
                step['params'] = step_params
        
        # Run pipeline button
        if st.session_state.chain_pipeline:
            st.markdown("---")
            col_run1, col_run2 = st.columns([3, 1])
            
            with col_run1:
                if st.button("▶️ Execute Pipeline", type="primary", use_container_width=True, key="run_chain"):
                    # Get Replicate token
                    replicate_token = get_api_key('REPLICATE_API_TOKEN', 'Replicate') or ''
                    if not replicate_token:
                        replicate_token = os.getenv('REPLICATE_API_TOKEN', '').strip()
                    
                    if not replicate_token:
                        st.error("❌ No Replicate API token found. Add it in Settings.")
                    else:
                        import replicate
                        import tempfile
                        import requests
                        
                        st.session_state.chain_results = []
                        previous_output = None
                        
                        # Execute each step
                        for step_idx, step in enumerate(st.session_state.chain_pipeline):
                            with st.status(f"⚙️ Step {step_idx + 1}: {step['type']}...", expanded=True) as status:
                                try:
                                    st.write(f"Model: {step['model']}")
                                    
                                    # Get model config
                                    if step['type'] == "Image Generation":
                                        models_dict = IMAGE_MODELS
                                    elif step['type'] == "Image Editing":
                                        models_dict = EDITING_MODELS
                                    elif step['type'] == "Ads & Marketing":
                                        models_dict = MARKETING_MODELS
                                    elif step['type'] == "Video Generation":
                                        models_dict = VIDEO_MODELS
                                    elif step['type'] == "Video Editing":
                                        models_dict = VIDEO_EDITING_MODELS
                                    elif step['type'] == "3D Generation":
                                        models_dict = MODEL_3D
                                    elif step['type'] == "Music Generation":
                                        models_dict = MUSIC_MODELS
                                    elif step['type'] == "Speech Synthesis":
                                        models_dict = SPEECH_MODELS
                                    
                                    model_config = models_dict[step['model']]
                                    
                                    # Build input from params
                                    model_input = {}
                                    for param_name, param_value in step['params'].items():
                                        # Handle file uploads
                                        if hasattr(param_value, 'read'):
                                            # Save to temp file
                                            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{param_value.name.split('.')[-1]}") as tmp:
                                                tmp.write(param_value.read())
                                                model_input[param_name] = open(tmp.name, 'rb')
                                        else:
                                            model_input[param_name] = param_value
                                    
                                    # If not first step, add previous output
                                    if step_idx > 0 and previous_output:
                                        # Find the file parameter
                                        for param_name, param_config in model_config["parameters"].items():
                                            if param_config["type"] == "file":
                                                model_input[param_name] = previous_output
                                                st.write(f"📥 Using output from previous step")
                                                break
                                    
                                    # Handle seed = 0
                                    if "seed" in model_input and model_input["seed"] == 0:
                                        model_input.pop("seed")
                                    
                                    st.write("🚀 Running model...")
                                    
                                    # Run the model
                                    output = replicate.run(step['model'], input=model_input)
                                    
                                    # Handle output
                                    if isinstance(output, list):
                                        output_url = output[0] if output else None
                                    else:
                                        output_url = output
                                    
                                    if output_url:
                                        previous_output = str(output_url)
                                        
                                        # Store result
                                        result = {
                                            'step': step_idx + 1,
                                            'type': step['type'],
                                            'model': step['model'],
                                            'output_type': step['output'],
                                            'url': previous_output,
                                            'params': step['params']
                                        }
                                        st.session_state.chain_results.append(result)
                                        
                                        # Display output
                                        if step['output'] == 'image':
                                            st.image(previous_output, caption=f"Step {step_idx + 1} output")
                                        elif step['output'] == 'video':
                                            st.video(previous_output)
                                        elif step['output'] == 'audio':
                                            st.audio(previous_output)
                                        elif step['output'] == '3d_model':
                                            st.success(f"✅ 3D Model generated: {previous_output}")
                                            st.caption("💡 Download the file to view in 3D software")
                                        
                                        status.update(label=f"✅ Step {step_idx + 1} complete!", state="complete")
                                    else:
                                        st.error("No output received")
                                        status.update(label=f"❌ Step {step_idx + 1} failed", state="error")
                                        break
                                
                                except Exception as e:
                                    st.error(f"Error: {str(e)}")
                                    status.update(label=f"❌ Step {step_idx + 1} failed", state="error")
                                    break
                        
                        if len(st.session_state.chain_results) == len(st.session_state.chain_pipeline):
                            st.success("🎉 Pipeline completed successfully!")
                            st.balloons()
            
            with col_run2:
                st.caption(f"{len(st.session_state.chain_pipeline)} steps")
        
        else:
            st.info("💡 Click **Add Step** to start building your pipeline")
            
            # Show example pipelines
            st.markdown("### 🔮 Example Pipelines")
            
            ex_col1, ex_col2 = st.columns(2)
            
            with ex_col1:
                with st.expander("🎨 Image → 3D → Video"):
                    st.markdown("""
                    **Create 3D animated content:**
                    1. Image Generation (Flux)
                    2. 3D Generation (Hunyuan 3D)
                    3. Video Generation (Kling v2.5)
                    
                    *Use case: Product visualization*
                    """)
                
                with st.expander("🎵 Image → Music → Video"):
                    st.markdown("""
                    **Create video with soundtrack:**
                    1. Image Generation (SDXL)
                    2. Music Generation (MusicGen)
                    3. Video Generation (Pixverse)
                    
                    *Use case: Social media content*
                    """)
            
            with ex_col2:
                with st.expander("🗣️ Text → Speech → Video"):
                    st.markdown("""
                    **Create narrated content:**
                    1. Image Generation (Imagen)
                    2. Speech Synthesis (Minimax)
                    3. Video Generation (Veo 3)
                    
                    *Use case: Explainer videos*
                    """)
                
                with st.expander("🎯 Logo → Ad → Music"):
                    st.markdown("""
                    **Complete ad campaign:**
                    1. Image Editing (Flux Editing)
                    2. Ads & Marketing (Ad Products)
                    3. Music Generation (Stable Audio)
                    
                    *Use case: Product marketing*
                    """)
        
        # Results section
        if st.session_state.chain_results:
            st.markdown("---")
            st.markdown("### 📊 Pipeline Results")
            
            for idx, result in enumerate(st.session_state.chain_results):
                with st.expander(f"**Step {result['step']}:** {result['type']} ({result['output_type']})", expanded=idx == len(st.session_state.chain_results) - 1):
                    col_res1, col_res2 = st.columns([3, 1])
                    
                    with col_res1:
                        if result['output_type'] == 'image':
                            st.image(result['url'])
                        elif result['output_type'] == 'video':
                            st.video(result['url'])
                        elif result['output_type'] == 'audio':
                            st.audio(result['url'])
                        elif result['output_type'] == '3d_model':
                            st.markdown(f"**3D Model File:** [{result['url']}]({result['url']})")
                            st.caption("💡 Click to download the 3D model file")
                    
                    with col_res2:
                        st.markdown(f"**Model:** `{result['model']}`")
                        st.markdown(f"**Type:** {result['output_type']}")
                        
                        # Download button
                        file_ext = {
                            'image': 'png',
                            'video': 'mp4',
                            'audio': 'mp3',
                            '3d_model': 'glb'
                        }.get(result['output_type'], 'bin')
                        
                        st.download_button(
                            "📥 Download",
                            result['url'],
                            f"chain_step_{result['step']}.{file_ext}",
                            key=f"chain_dl_{idx}",
                            use_container_width=True
                        )
    
    # UNIVERSAL WORKFLOW IMPORT TAB
    with wf_tabs[2]:
        st.markdown("### 📥 Universal Workflow Import (Enhanced)")
        st.markdown("Import workflows from multiple automation platforms with intelligent conversion")
        
        # Use enhanced converter
        try:
            from enhanced_workflow_converter import (
                EnhancedUniversalConverter, WorkflowPlatform, 
                convert_any_workflow, detect_workflow_platform, analyze_workflow as enhanced_analyze
            )
            USE_ENHANCED = True
        except ImportError:
            from workflow_converter import SUPPORTED_PLATFORMS, analyze_workflow, convert_workflow
            USE_ENHANCED = False
        
        st.markdown("#### 🌐 Supported Platforms")
        
        # Enhanced platform display
        ENHANCED_PLATFORMS = [
            {"name": "ComfyUI", "icon": "🎨", "description": "AI image generation workflows", "export_help": "Save workflow as API format (JSON)"},
            {"name": "n8n", "icon": "🔄", "description": "General automation workflows", "export_help": "Download workflow from n8n editor"},
            {"name": "Node-RED", "icon": "🔴", "description": "IoT & event-driven flows", "export_help": "Export from menu → Export → Clipboard"},
            {"name": "Home Assistant", "icon": "🏠", "description": "Smart home automations", "export_help": "Copy YAML from automation editor"},
            {"name": "Make.com", "icon": "⚡", "description": "Business automation scenarios", "export_help": "Export blueprint as JSON"},
            {"name": "Activepieces", "icon": "🧩", "description": "Open-source automation", "export_help": "Export flow from editor"},
            {"name": "Windmill", "icon": "💨", "description": "Developer automation", "export_help": "Export script/flow as JSON"},
            {"name": "Pipedream", "icon": "🔗", "description": "API workflow platform", "export_help": "Export workflow definition"},
        ]
        
        # Display platforms in a grid
        platform_cols = st.columns(4)
        for idx, platform in enumerate(ENHANCED_PLATFORMS):
            with platform_cols[idx % 4]:
                with st.container(border=True):
                    st.markdown(f"**{platform['icon']} {platform['name']}**")
                    st.caption(platform['description'])
                    with st.expander("How to export", expanded=False):
                        st.caption(platform['export_help'])
        
        st.markdown("---")
        
        # Enhanced info box
        st.info("""
        🧠 **Enhanced Workflow Import:**
        - **Auto-detection** of platform from workflow structure
        - **Semantic understanding** of workflow intent
        - **Intelligent mapping** to equivalent capabilities
        - **Multi-level fallbacks** for unsupported features
        
        📌 **Steps:**
        1. Export your workflow from any supported platform
        2. Upload the JSON/YAML file or paste content below
        3. Click "Analyze" to preview, then "Convert & Load"
        """)
        
        # File uploader
        workflow_file = st.file_uploader(
            "Upload Workflow File",
            type=['json', 'yaml', 'yml'],
            key="universal_workflow_upload",
            help="Upload a .json or .yaml file exported from any supported platform"
        )
        
        # Or paste JSON/YAML
        with st.expander("📋 Or Paste Workflow Content Directly"):
            workflow_text = st.text_area(
                "Paste workflow JSON/YAML here",
                height=200,
                key="universal_workflow_paste",
                placeholder='Paste your workflow JSON or YAML content here...'
            )
        
        col_analyze, col_convert = st.columns(2)
        
        # Store analysis results in session state
        if 'workflow_analysis' not in st.session_state:
            st.session_state.workflow_analysis = None
        if 'workflow_converted' not in st.session_state:
            st.session_state.workflow_converted = None
        
        with col_analyze:
            if st.button("🔍 Analyze Workflow", use_container_width=True, key="analyze_workflow_btn"):
                workflow_content = None
                
                if workflow_file is not None:
                    try:
                        content = workflow_file.read().decode('utf-8')
                        workflow_file.seek(0)
                        
                        # Try JSON first, then YAML
                        try:
                            workflow_content = json.loads(content)
                        except json.JSONDecodeError:
                            try:
                                import yaml
                                workflow_content = yaml.safe_load(content)
                            except:
                                st.error("Could not parse file as JSON or YAML")
                    except Exception as e:
                        st.error(f"Error reading file: {e}")
                elif workflow_text:
                    try:
                        workflow_content = json.loads(workflow_text)
                    except json.JSONDecodeError:
                        try:
                            import yaml
                            workflow_content = yaml.safe_load(workflow_text)
                        except:
                            st.error("Could not parse content as JSON or YAML")
                else:
                    st.warning("Please upload a file or paste workflow content")
                
                if workflow_content:
                    try:
                        with st.spinner("🧠 Analyzing workflow with enhanced intelligence..."):
                            if USE_ENHANCED:
                                converted, analysis = convert_any_workflow(workflow_content)
                                platform_name = analysis.platform.value
                                st.session_state.workflow_analysis = {
                                    'platform': platform_name,
                                    'platform_display': platform_name.replace('-', ' ').title(),
                                    'node_count': analysis.node_count,
                                    'has_ai_generation': analysis.has_ai_generation,
                                    'has_video_generation': analysis.has_video_generation,
                                    'description': analysis.description,
                                    'prompts': analysis.prompts,
                                    'triggers': analysis.triggers,
                                    'complexity': analysis.complexity_score,
                                    'suggestions': analysis.optimization_suggestions,
                                }
                                st.session_state.workflow_converted = converted
                            else:
                                analysis = analyze_workflow(workflow_content)
                                st.session_state.workflow_analysis = analysis
                            st.session_state.workflow_raw = workflow_content
                        
                        platform_display = st.session_state.workflow_analysis.get('platform_display', 'Unknown')
                        st.success(f"✅ Detected: **{platform_display}** workflow!")
                    except Exception as e:
                        st.error(f"Error analyzing workflow: {e}")
                        import traceback
                        st.code(traceback.format_exc())
        
        with col_convert:
            if st.button("🔄 Convert to Our Format", type="primary", use_container_width=True, key="convert_workflow_btn"):
                workflow_content = st.session_state.get('workflow_raw')
                
                if not workflow_content:
                    if workflow_file is not None:
                        try:
                            workflow_file.seek(0)
                            content = workflow_file.read().decode('utf-8')
                            try:
                                workflow_content = json.loads(content)
                            except:
                                import yaml
                                workflow_content = yaml.safe_load(content)
                        except:
                            pass
                    elif workflow_text:
                        try:
                            workflow_content = json.loads(workflow_text)
                        except:
                            try:
                                import yaml
                                workflow_content = yaml.safe_load(workflow_text)
                            except:
                                pass
                
                if not workflow_content:
                    st.warning("Please upload a file or paste content first")
                else:
                    try:
                        with st.spinner("Converting workflow..."):
                            if USE_ENHANCED:
                                converted, analysis = convert_any_workflow(workflow_content)
                                info = {
                                    'platform': analysis.platform.value,
                                    'platform_display': analysis.platform.value.replace('-', ' ').title(),
                                    'node_count': analysis.node_count,
                                    'description': analysis.description,
                                    'prompts': analysis.prompts,
                                }
                            else:
                                from workflow_converter import convert_workflow
                                converted, info = convert_workflow(workflow_content)
                            st.session_state.workflow_converted = converted
                            st.session_state.workflow_analysis = info
                        
                        if converted.get('error'):
                            st.error(f"Conversion error: {converted['error']}")
                        else:
                            st.success(f"✅ Converted! {len(converted.get('steps', []))} steps created from **{info.get('platform_display', 'Unknown')}**")
                    except Exception as e:
                        st.error(f"Error converting workflow: {e}")
        
        # Display analysis results
        if st.session_state.workflow_analysis:
            st.markdown("---")
            st.markdown("### 📊 Workflow Analysis")
            
            analysis = st.session_state.workflow_analysis
            
            # Platform badge
            platform_display = analysis.get('platform_display', 'Unknown')
            st.markdown(f"**Platform Detected:** `{platform_display}`")
            
            if analysis.get('error'):
                st.error(f"Analysis error: {analysis['error']}")
            else:
                # Summary
                if analysis.get('summary'):
                    for item in analysis['summary']:
                        st.markdown(f"• {item}")
                
                # Node details
                nodes = analysis.get('nodes', [])
                if nodes:
                    st.markdown(f"**Found {len(nodes)} nodes/steps:**")
                    
                    # Group by type
                    type_groups = {}
                    for node in nodes:
                        node_type = node.get('type', 'unknown')
                        if node_type not in type_groups:
                            type_groups[node_type] = []
                        type_groups[node_type].append(node)
                    
                    for node_type, group_nodes in type_groups.items():
                        with st.expander(f"**{node_type.replace('_', ' ').title()}** ({len(group_nodes)})", expanded=False):
                            for node in group_nodes:
                                st.markdown(f"• `{node.get('name', 'Unnamed')}` - {node.get('platform_type', 'N/A')}")
                
                # Show prompts if available (for AI workflows)
                prompts = analysis.get('prompts', {})
                if prompts:
                    # Handle prompts being either a dict or a list
                    if isinstance(prompts, dict):
                        col_p1, col_p2 = st.columns(2)
                        with col_p1:
                            if prompts.get('positive'):
                                st.text_area("Positive Prompt", prompts['positive'], height=100, disabled=True, key="imported_pos_prompt")
                        with col_p2:
                            if prompts.get('negative'):
                                st.text_area("Negative Prompt", prompts['negative'], height=100, disabled=True, key="imported_neg_prompt")
                    elif isinstance(prompts, list) and prompts:
                        # Show list of prompts
                        st.markdown("**Extracted Prompts:**")
                        for i, prompt in enumerate(prompts[:5]):  # Show first 5
                            if prompt:
                                st.text_area(f"Prompt {i+1}", str(prompt)[:500], height=80, disabled=True, key=f"imported_prompt_{i}")
        
        # ComfyUI-specific Model Detection Section
        if st.session_state.workflow_analysis and st.session_state.workflow_analysis.get('platform') == 'comfyui':
            st.markdown("---")
            st.markdown("### 🔧 ComfyUI Model Requirements")
            
            with st.spinner("Analyzing required models..."):
                try:
                    from comfyui_model_manager import ComfyUIModelManager, analyze_comfyui_models
                    
                    workflow_raw = st.session_state.get('workflow_raw', {})
                    model_analysis = analyze_comfyui_models(workflow_raw)
                    
                    st.session_state.comfyui_model_analysis = model_analysis
                except Exception as e:
                    st.error(f"Error analyzing models: {e}")
                    model_analysis = None
            
            if model_analysis:
                # Summary
                st.markdown("#### Required Models")
                for summary_item in model_analysis.get('summary', []):
                    st.markdown(summary_item)
                
                # Available vs Missing
                available = model_analysis.get('available_models', [])
                missing = model_analysis.get('missing_models', [])
                
                col_avail, col_miss = st.columns(2)
                
                with col_avail:
                    if available:
                        st.success(f"**✅ {len(available)} Models Available**")
                        for model in available:
                            st.markdown(f"• `{model.name}` ({model.type.value})")
                    else:
                        st.info("No models found locally yet")
                
                with col_miss:
                    if missing:
                        st.warning(f"**📥 {len(missing)} Models Need Download**")
                        for model in missing:
                            source = "HuggingFace" if model.huggingface_repo else "Civitai" if model.civitai_id else "URL" if model.source_url else "Unknown"
                            st.markdown(f"• `{model.name}` ({model.type.value}) - {source}")
                    else:
                        st.success("All models available!")
                
                # Custom Nodes
                custom_nodes = model_analysis.get('custom_nodes', [])
                if custom_nodes:
                    st.markdown("#### 🔧 Required Custom Nodes")
                    for node in custom_nodes:
                        st.markdown(f"• **{node}**")
                
                # Download Section
                if missing:
                    st.markdown("---")
                    st.markdown("#### 📥 Download Missing Models")
                    
                    # HuggingFace token input
                    hf_token = st.text_input(
                        "HuggingFace Token (for gated models)",
                        type="password",
                        key="hf_token_input",
                        help="Required for some models like FLUX. Get one at huggingface.co/settings/tokens"
                    )
                    
                    # Civitai token input  
                    civitai_key = st.text_input(
                        "Civitai API Key (optional)",
                        type="password",
                        key="civitai_key_input",
                        help="For downloading from Civitai. Get one at civitai.com/user/account"
                    )
                    
                    # Model download path
                    models_path = st.text_input(
                        "Models Download Path",
                        value="./comfyui_models",
                        key="models_path_input",
                        help="Where to save downloaded models"
                    )
                    
                    col_dl1, col_dl2 = st.columns(2)
                    
                    with col_dl1:
                        if st.button("📥 Download All Missing Models", type="primary", use_container_width=True, key="download_all_models"):
                            # Set environment variables
                            if hf_token:
                                os.environ["HF_TOKEN"] = hf_token
                            if civitai_key:
                                os.environ["CIVITAI_API_KEY"] = civitai_key
                            
                            manager = ComfyUIModelManager(models_path=models_path)
                            
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            
                            total_models = len(missing)
                            completed = 0
                            
                            for model in missing:
                                status_text.text(f"Downloading: {model.name}...")
                                success = manager.download_model(model)
                                completed += 1
                                progress_bar.progress(completed / total_models)
                                
                                if success:
                                    st.success(f"✅ Downloaded: {model.name}")
                                else:
                                    progress_info = manager.download_progress.get(model.name)
                                    error_msg = progress_info.error_message if progress_info else "Unknown error"
                                    st.error(f"❌ Failed: {model.name} - {error_msg}")
                            
                            status_text.text("Download complete!")
                            st.balloons()
                    
                    with col_dl2:
                        st.markdown("**Or download manually:**")
                        for model in missing:
                            if model.huggingface_repo:
                                st.markdown(f"• [{model.name}](https://huggingface.co/{model.huggingface_repo})")
                            elif model.civitai_id:
                                st.markdown(f"• [{model.name}](https://civitai.com/models/{model.civitai_id})")
                            elif model.source_url:
                                st.markdown(f"• [{model.name}]({model.source_url})")
                            else:
                                st.markdown(f"• {model.name} (search online)")
                
                # Execution Options
                st.markdown("---")
                st.markdown("#### 🚀 Run This Workflow")
                
                execution_mode = st.radio(
                    "Execution Mode",
                    ["🌐 Remote (Replicate API)", "💻 Local (ComfyUI)"],
                    key="comfy_exec_mode",
                    horizontal=True
                )
                
                if "Remote" in execution_mode:
                    st.info("""
                    **Remote execution** uses Replicate's cloud GPUs to run your workflow.
                    - ✅ No local GPU required
                    - ✅ No model downloads needed
                    - ✅ Works immediately
                    - ⚠️ May not support all custom nodes
                    - ⚠️ Approximates the workflow using equivalent models
                    """)
                    
                    if st.button("▶️ Run via Replicate", type="primary", use_container_width=True, key="run_comfy_remote"):
                        with st.spinner("Running workflow remotely..."):
                            try:
                                from comfyui_model_manager import ComfyUIExecutor, ComfyUIModelManager
                                
                                manager = ComfyUIModelManager()
                                executor = ComfyUIExecutor(manager)
                                result = executor.execute_remotely(workflow_raw)
                                
                                if result["status"] == "complete":
                                    st.success("✅ Workflow completed!")
                                    outputs = result.get("outputs", {})
                                    images = outputs.get("images", [])
                                    for img_url in images:
                                        st.image(img_url)
                                else:
                                    st.error(f"Execution failed: {result.get('error', 'Unknown error')}")
                            except Exception as e:
                                st.error(f"Error: {e}")
                
                else:
                    st.info("""
                    **Local execution** runs on your local ComfyUI installation.
                    - ✅ Full compatibility with all nodes
                    - ✅ Exact same results as ComfyUI
                    - ⚠️ Requires ComfyUI running locally
                    - ⚠️ Requires models downloaded
                    """)
                    
                    comfyui_url = st.text_input(
                        "ComfyUI URL",
                        value="http://127.0.0.1:8188",
                        key="comfyui_url_input"
                    )
                    
                    col_check, col_run = st.columns(2)
                    
                    with col_check:
                        if st.button("🔌 Check Connection", use_container_width=True, key="check_comfy_conn"):
                            try:
                                import requests
                                response = requests.get(f"{comfyui_url}/system_stats", timeout=5)
                                if response.status_code == 200:
                                    st.success("✅ ComfyUI is running!")
                                    stats = response.json()
                                    st.json(stats)
                                else:
                                    st.warning(f"ComfyUI responded with status {response.status_code}")
                            except requests.exceptions.ConnectionError:
                                st.error("❌ Cannot connect to ComfyUI. Make sure it's running.")
                            except Exception as e:
                                st.error(f"Error: {e}")
                    
                    with col_run:
                        if st.button("▶️ Run Locally", type="primary", use_container_width=True, key="run_comfy_local"):
                            os.environ["COMFYUI_URL"] = comfyui_url
                            
                            with st.spinner("Running workflow on local ComfyUI..."):
                                try:
                                    from comfyui_model_manager import ComfyUIExecutor, ComfyUIModelManager
                                    
                                    manager = ComfyUIModelManager()
                                    executor = ComfyUIExecutor(manager)
                                    result = executor.execute_locally(workflow_raw)
                                    
                                    if result["status"] == "complete":
                                        st.success("✅ Workflow completed!")
                                        outputs = result.get("outputs", {})
                                        st.json(outputs)
                                    elif result["status"] == "timeout":
                                        st.warning("⏱️ Workflow is still running. Check ComfyUI for results.")
                                    else:
                                        st.error(f"Execution failed: {result.get('error', 'Unknown error')}")
                                except Exception as e:
                                    st.error(f"Error: {e}")
        
        # Display converted workflow
        if st.session_state.workflow_converted:
            st.markdown("---")
            st.markdown("### ✅ Converted Workflow")
            
            converted = st.session_state.workflow_converted
            steps = converted.get('steps', [])
            
            if steps:
                st.success(f"Created {len(steps)} workflow steps:")
                
                for step in steps:
                    with st.expander(f"**Step {step['id']}:** {step['type']}", expanded=False):
                        st.markdown(f"**Category:** {step['category']}")
                        st.markdown(f"**Description:** {step.get('description', 'N/A')}")
                        
                        if step.get('original_type'):
                            st.caption(f"Original node type: `{step['original_type']}`")
                        
                        if step.get('config'):
                            st.markdown("**Configuration:**")
                            st.json(step['config'])
                
                # Actions
                st.markdown("---")
                col_use, col_dl, col_edit = st.columns(3)
                
                with col_use:
                    if st.button("▶️ Use This Workflow", type="primary", use_container_width=True, key="use_imported_workflow"):
                        workflow_to_load = {
                            'steps': converted.get('steps', []),
                            'schedule': converted.get('schedule'),
                            'outputs': converted.get('outputs', [])
                        }
                        st.session_state.current_workflow = workflow_to_load
                        st.success("✅ Loaded into workflow builder!")
                        st.balloons()
                        st.rerun()
                
                with col_dl:
                    workflow_json_str = json.dumps(converted, indent=2)
                    st.download_button(
                        "📥 Download Converted",
                        workflow_json_str,
                        "converted_workflow.json",
                        mime="application/json",
                        use_container_width=True,
                        key="dl_imported_workflow"
                    )
                
                with col_edit:
                    if st.button("✏️ Edit Before Using", use_container_width=True, key="edit_imported_workflow"):
                        st.session_state.current_workflow = converted
                        st.info("Workflow loaded - switch to 'Build' tab to edit")
            else:
                st.warning("No steps could be extracted from this workflow")
                st.info("The workflow may use unsupported nodes or have an unusual structure")
        
        # Platform-specific resources section
        st.markdown("---")
        st.markdown("### 🌟 Find Workflows to Import")
        st.caption("Visit these sites to find workflows for each platform:")
        
        col_res1, col_res2, col_res3, col_res4 = st.columns(4)
        
        with col_res1:
            st.markdown("""
            **🎨 ComfyUI**
            - [ComfyWorkflows.com](https://comfyworkflows.com)
            - [Civitai Workflows](https://civitai.com/models?type=Workflows)
            - [OpenArt Workflows](https://openart.ai/workflows)
            """)
        
        with col_res2:
            st.markdown("""
            **⚡ n8n**
            - [n8n Templates](https://n8n.io/workflows/)
            - [n8n Community](https://community.n8n.io)
            """)
        
        with col_res3:
            st.markdown("""
            **🔴 Node-RED**
            - [Node-RED Flows](https://flows.nodered.org)
            - [Node-RED Forum](https://discourse.nodered.org)
            """)
        
        with col_res4:
            st.markdown("""
            **🏠 Home Assistant**
            - [HA Blueprints](https://community.home-assistant.io/c/blueprints-exchange)
            - [HA Community](https://community.home-assistant.io)
            """)
    
    # HISTORY TAB
    with wf_tabs[3]:
        st.markdown("### 📜 Workflow Run History")
        
        if 'workflow_history' not in st.session_state:
            st.session_state.workflow_history = []
        
        if not st.session_state.workflow_history:
            st.info("No workflow runs yet. Execute a workflow to see history here.")
        else:
            # Clear history button
            if st.button("🗑️ Clear History", key="clear_wf_history"):
                st.session_state.workflow_history = []
                st.rerun()
            
            for entry in reversed(st.session_state.workflow_history[-20:]):
                with st.expander(f"🕐 {entry.get('timestamp', 'Unknown')} - {entry.get('name', 'Workflow')}", expanded=False):
                    st.markdown(f"**Status:** {entry.get('status', 'Unknown')}")
                    st.markdown(f"**Steps completed:** {entry.get('steps_completed', 0)}/{entry.get('total_steps', 0)}")
                    if entry.get('outputs'):
                        st.markdown("**Outputs:**")
                        for output in entry['outputs']:
                            st.markdown(f"• {output}")
    
    # SAVED WORKFLOWS TAB
    with wf_tabs[4]:
        st.markdown("### ⚙️ Saved Workflows")
        
        if not st.session_state.workflows:
            st.info("No saved workflows yet. Build and save a workflow to see it here.")
        else:
            for wf_name, wf_data in st.session_state.workflows.items():
                with st.container(border=True):
                    col_wf1, col_wf2 = st.columns([3, 1])
                    
                    with col_wf1:
                        st.markdown(f"**{wf_name}**")
                        steps_count = len(wf_data.get('steps', []))
                        st.caption(f"{steps_count} steps")
                    
                    with col_wf2:
                        col_load, col_del = st.columns(2)
                        with col_load:
                            if st.button("📂", key=f"load_wf_{wf_name}", help="Load workflow"):
                                st.session_state.current_workflow = wf_data.copy()
                                st.success(f"Loaded '{wf_name}'")
                                st.rerun()
                        with col_del:
                            if st.button("🗑️", key=f"del_wf_{wf_name}", help="Delete workflow"):
                                del st.session_state.workflows[wf_name]
                                st.rerun()
    
    # Results History (shared across tabs)
    if st.session_state.playground_results:
        st.markdown("---")
        st.markdown("### 📜 Generation History")
        
        for idx, result in enumerate(st.session_state.playground_results[:10]):  # Show last 10
            with st.expander(f"{result['type'].capitalize()} - {result['model']}", expanded=idx==0):
                col_res1, col_res2 = st.columns([2, 1])
                with col_res1:
                    if result['type'] == 'image':
                        st.image(result['url'], caption=result['prompt'][:100])
                    else:
                        st.video(result['url'])
                with col_res2:
                    st.markdown(f"**Model:** `{result['model']}`")
                    st.markdown(f"**Prompt:** {result['prompt'][:150]}...")
                    
                    # Download button
                    st.download_button(
                        "📥 Download",
                        result['url'],
                        f"playground_{result['type']}_{idx}.{'png' if result['type'] == 'image' else 'mp4'}",
                        key=f"dl_{idx}",
                        use_container_width=True
                    )
                    
                    # Image-specific actions
                    if result['type'] == 'image':
                        # Print It! button
                        printify_api_client = _get_printify_api()
                        playground_config = st.session_state.get('playground_printify_config', {})
                        config_ready = bool(
                            playground_config.get('blueprint_id') and 
                            playground_config.get('provider_id') and 
                            playground_config.get('variant_ids')
                        )
                        
                        if st.button(
                            "🖨️ Print It!",
                            key=f"print_{idx}",
                            use_container_width=True,
                            disabled=not (printify_api_client and config_ready),
                            help="Send this design to Printify" if config_ready else "Configure Printify settings above first"
                        ):
                            if not printify_api_client:
                                st.error("❌ Configure Printify credentials in Settings first")
                            elif not config_ready:
                                st.error("❌ Configure Printify product settings above first")
                            else:
                                import tempfile
                                import requests
                                import os
                                try:
                                    with st.spinner("📤 Sending to Printify..."):
                                        # Download image
                                        img_response = requests.get(result['url'], timeout=30)
                                        img_response.raise_for_status()
                                        
                                        # Save to temp file
                                        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_file:
                                            tmp_file.write(img_response.content)
                                            tmp_path = tmp_file.name
                                        
                                        # Send to Printify
                                        from app.services.platform_helpers import _send_design_to_printify
                                        variation_label = f"Playground - {result['model'][:30]}"
                                        printify_result = _send_design_to_printify(
                                            tmp_path,
                                            result['prompt'],
                                            playground_config,
                                            variation_label
                                        )
                                        
                                        # Clean up temp file
                                        os.unlink(tmp_path)
                                        
                                        product_id = printify_result.get('product_id')
                                        if product_id:
                                            st.success(f"✅ Sent to Printify! Product ID: {product_id}")
                                            st.info("🔗 Check your Printify dashboard to customize and publish")
                                        else:
                                            st.warning("⚠️ Sent but no product ID returned. Check Printify dashboard.")
                                
                                except Exception as e:
                                    st.error(f"❌ Failed to send to Printify: {str(e)}")
                                    if "blueprint" in str(e).lower() or "provider" in str(e).lower():
                                        st.info("💡 Configure Printify product settings in the expander above")
                        
                        # Make Video button
                        if st.button(
                            "🎬 Make Video",
                            key=f"video_{idx}",
                            use_container_width=True,
                            help="Generate a video using this image"
                        ):
                            st.session_state[f'make_video_{idx}'] = True
                        
                        # Video generation modal
                        if st.session_state.get(f'make_video_{idx}', False):
                            st.markdown("---")
                            st.markdown("**🎬 Generate Video from Image**")
                            
                            video_model_choice = st.selectbox(
                                "Video Model",
                                list(VIDEO_MODELS.keys()),
                                format_func=lambda x: VIDEO_MODELS[x]["name"],
                                key=f"vid_model_{idx}"
                            )
                            
                            video_prompt = st.text_input(
                                "Video Prompt (optional)",
                                value=result['prompt'],
                                key=f"vid_prompt_{idx}",
                                help="Describe the motion/animation"
                            )
                            
                            # Show model-specific parameters
                            vid_gen_params = {}
                            model_config = VIDEO_MODELS[video_model_choice]
                            for param_name, param_config in model_config["parameters"].items():
                                if param_config["type"] == "file":
                                    continue  # Skip file upload (we're using the image)
                                
                                # Generate label from parameter name
                                label = param_name.replace("_", " ").title()
                                
                                if param_config["type"] == "select":
                                    vid_gen_params[param_name] = st.selectbox(
                                        label,
                                        options=param_config["options"],
                                        index=param_config["options"].index(param_config["default"]),
                                        key=f"vid_gen_{idx}_{param_name}",
                                        help=param_config.get("help", "")
                                    )
                                elif param_config["type"] == "slider":
                                    vid_gen_params[param_name] = st.slider(
                                        label,
                                        min_value=param_config["min"],
                                        max_value=param_config["max"],
                                        value=param_config["default"],
                                        step=param_config.get("step", 1),
                                        key=f"vid_gen_{idx}_{param_name}",
                                        help=param_config.get("help", "")
                                    )
                                elif param_config["type"] == "checkbox":
                                    vid_gen_params[param_name] = st.checkbox(
                                        label,
                                        value=param_config["default"],
                                        key=f"vid_gen_{idx}_{param_name}",
                                        help=param_config.get("help", "")
                                    )
                                elif param_config["type"] == "number":
                                    vid_gen_params[param_name] = st.number_input(
                                        label,
                                        min_value=param_config.get("min", 0),
                                        max_value=param_config.get("max", 999999),
                                        value=param_config["default"],
                                        key=f"vid_gen_{idx}_{param_name}",
                                        help=param_config.get("help", "")
                                    )
                            
                            col_gen1, col_gen2 = st.columns(2)
                            with col_gen1:
                                if st.button("✨ Generate Video", key=f"gen_vid_{idx}", type="primary", use_container_width=True):
                                    try:
                                        with st.spinner(f"🎬 Generating video... This may take 1-3 minutes"):
                                            replicate_token = get_api_key('REPLICATE_API_TOKEN', 'Replicate') or ''
                                            if not replicate_token:
                                                replicate_token = os.getenv('REPLICATE_API_TOKEN', '').strip()
                                            
                                            if not replicate_token:
                                                st.error("❌ No Replicate API token found. Add it in Settings.")
                                                st.stop()
                                            
                                            import replicate
                                            
                                            # Build model input
                                            model_input = build_model_input(video_model_choice, "video", vid_gen_params)
                                            if video_prompt:
                                                model_input["prompt"] = video_prompt
                                            
                                            # Add the source image
                                            model_config = VIDEO_MODELS[video_model_choice]
                                            for param_name, param_config in model_config["parameters"].items():
                                                if param_config["type"] == "file":
                                                    model_input[param_name] = result['url']
                                                    break
                                            
                                            # Handle seed = 0
                                            if "seed" in model_input and model_input["seed"] == 0:
                                                model_input.pop("seed")
                                            
                                            # Run model
                                            output = replicate.run(video_model_choice, input=model_input)
                                            
                                            # Handle output
                                            if isinstance(output, list):
                                                output_url = output[0] if output else None
                                            else:
                                                output_url = output
                                            
                                            if output_url:
                                                st.session_state.playground_results.insert(0, {
                                                    'type': 'video',
                                                    'url': str(output_url),
                                                    'model': video_model_choice,
                                                    'prompt': video_prompt,
                                                    'source_image': result['url']
                                                })
                                                st.success("✅ Video generated!")
                                                st.video(str(output_url))
                                                st.session_state[f'make_video_{idx}'] = False
                                                st.rerun()
                                            else:
                                                st.error("No output received from model")
                                    
                                    except Exception as e:
                                        st.error(f"❌ Video generation failed: {str(e)}")
                                        if "credit" in str(e).lower():
                                            st.warning("💳 Insufficient Replicate credits")
                            
                            with col_gen2:
                                if st.button("❌ Cancel", key=f"cancel_vid_{idx}", use_container_width=True):
                                    st.session_state[f'make_video_{idx}'] = False
                                    st.rerun()
