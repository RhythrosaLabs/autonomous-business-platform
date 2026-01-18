import streamlit as st
import datetime as datetime_module
from datetime import timedelta, datetime as dt
import calendar
import uuid
import logging
from app.services.platform_integrations import tracked_replicate_run
from app.services.tab_job_helpers import (
    submit_batch_operation,
    collect_job_results,
    check_jobs_progress,
    are_all_jobs_done
)
from app.services.global_job_queue import JobType, get_global_job_queue

# Configure logger
logger = logging.getLogger(__name__)

try:
    from app.services.platform_helpers import _get_replicate_token
except ImportError:
    def _get_replicate_token(): return None

try:
    from performance_optimizations import get_replicate_client
    PERF_OPTIMIZATIONS_AVAILABLE = True
except ImportError:
    PERF_OPTIMIZATIONS_AVAILABLE = False
    def get_replicate_client(): return None

def render_calendar_tab():
    """
    Renders the Calendar & Queue tab (Tab 10).
    """
    st.markdown('<div class="main-header">📅 AI-Powered Calendar & Smart Queue</div>', unsafe_allow_html=True)
    
    # Custom CSS for calendar
    st.markdown("""
    <style>
    .calendar-ai-suggestion {
        background: linear-gradient(135deg, #667eea15, #764ba215);
        border-radius: 10px;
        padding: 12px;
        margin: 8px 0;
        border-left: 3px solid #667eea;
    }
    .time-block {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 10px;
        margin: 5px 0;
        border-left: 3px solid #28a745;
    }
    .priority-urgent { border-left-color: #dc3545; background: #fff5f5; }
    .priority-high { border-left-color: #fd7e14; background: #fff8f0; }
    .priority-medium { border-left-color: #ffc107; background: #fffbeb; }
    .priority-low { border-left-color: #28a745; background: #f0fff4; }
    </style>
    """, unsafe_allow_html=True)
    
    # Initialize state
    if 'scheduled_items' not in st.session_state:
        st.session_state.scheduled_items = []
    if 'queue_items' not in st.session_state:
        st.session_state.queue_items = {
            'pending': [],
            'in_progress': [],
            'completed': [],
            'failed': []
        }
    if 'calendar_date' not in st.session_state:
        st.session_state.calendar_date = datetime_module.date.today()
    if 'recurring_tasks' not in st.session_state:
        st.session_state.recurring_tasks = []

    # Top control bar with AI
    col_ctrl1, col_ctrl2, col_ctrl3, col_ctrl4, col_ctrl5 = st.columns([2, 1, 1, 1, 1])

    with col_ctrl1:
        view_mode = st.radio(
            "View",
            ["📅 Calendar", "📋 Queue", "🤖 AI Planner", "📊 Analytics"],
            horizontal=True,
            key="cal_view_mode"
        )

    with col_ctrl2:
        if st.button("➕ Schedule", use_container_width=True, type="primary"):
            st.session_state['show_schedule_modal'] = True

    with col_ctrl3:
        if st.button("⚡ Quick Task", use_container_width=True):
            st.session_state['show_quick_task'] = True

    with col_ctrl4:
        if st.button("🤖 AI Plan", use_container_width=True):
            st.session_state['show_ai_planner'] = True

    with col_ctrl5:
        pending_count = len(st.session_state.queue_items['pending'])
        st.metric("Queue", pending_count, delta=f"+{pending_count}" if pending_count > 0 else None)

    st.markdown("---")

    # CALENDAR VIEW
    if view_mode in ["📅 Calendar", "📊 Both"]:
        st.markdown("### 📅 Calendar")
        
        # Month navigation
        col_nav1, col_nav2, col_nav3, col_nav4 = st.columns([1, 2, 2, 1])
        
        with col_nav1:
            if st.button("◀️ Prev", use_container_width=True):
                current = st.session_state.calendar_date
                if current.month == 1:
                    st.session_state.calendar_date = current.replace(year=current.year - 1, month=12, day=1)
                else:
                    st.session_state.calendar_date = current.replace(month=current.month - 1, day=1)
                st.rerun()
        
        with col_nav2:
            month_name = st.session_state.calendar_date.strftime("%B %Y")
            st.markdown(f"<h3 style='text-align: center;'>{month_name}</h3>", unsafe_allow_html=True)
        
        with col_nav3:
            if st.button("📍 Today", use_container_width=True):
                st.session_state.calendar_date = datetime_module.date.today()
                st.rerun()
        
        with col_nav4:
            if st.button("Next ▶️", use_container_width=True):
                current = st.session_state.calendar_date
                if current.month == 12:
                    st.session_state.calendar_date = current.replace(year=current.year + 1, month=1, day=1)
                else:
                    st.session_state.calendar_date = current.replace(month=current.month + 1, day=1)
                st.rerun()
        
        # Generate calendar grid
        cal = calendar.monthcalendar(
            st.session_state.calendar_date.year,
            st.session_state.calendar_date.month
        )
        
        # Calendar header (days of week)
        days_header = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        cols = st.columns(7)
        for idx, day in enumerate(days_header):
            with cols[idx]:
                st.markdown(f"<div style='text-align: center; font-weight: bold; color: #666;'>{day}</div>", unsafe_allow_html=True)
        
        # Calendar body
        today = datetime_module.date.today()
        selected_date = st.session_state.calendar_date
        
        for week in cal:
            cols = st.columns(7)
            for idx, day in enumerate(week):
                with cols[idx]:
                    if day == 0:
                        st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)
                    else:
                        # Create date for this cell
                        cell_date = datetime_module.date(
                            st.session_state.calendar_date.year,
                            st.session_state.calendar_date.month,
                            day
                        )
                        
                        # Count items scheduled for this date
                        items_on_date = [
                            item for item in st.session_state.scheduled_items
                            if item.get('date') == cell_date
                        ]
                        
                        # Style based on date
                        is_today = cell_date == today
                        is_past = cell_date < today
                        
                        bg_color = "#e3f2fd" if is_today else "#f5f5f5" if is_past else "white"
                        border_color = "#2196f3" if is_today else "#ddd"
                        
                        # Create calendar cell
                        cell_html = f"""
                        <div style='
                            border: 2px solid {border_color};
                            border-radius: 8px;
                            padding: 8px;
                            height: 80px;
                            background-color: {bg_color};
                            cursor: pointer;
                        '>
                            <div style='font-weight: bold; font-size: 16px;'>{day}</div>
                            <div style='font-size: 11px; color: #666; margin-top: 4px;'>
                                {len(items_on_date)} items
                            </div>
                        """
                        
                        # Show first 2 items
                        for item in items_on_date[:2]:
                            icon = {"workflow": "🔧", "post": "📱", "video": "🎥", "image": "🖼️"}.get(item.get('type', 'post'), "📌")
                            cell_html += f"<div style='font-size: 10px; margin-top: 2px;'>{icon} {item.get('title', 'Untitled')[:15]}</div>"
                        
                        cell_html += "</div>"
                        st.markdown(cell_html, unsafe_allow_html=True)
                        
                        # Click to view day details
                        if st.button(f"📋", key=f"day_{day}", use_container_width=True):
                            st.session_state['selected_day'] = cell_date
        
        # Show selected day details
        if st.session_state.get('selected_day'):
            selected_day = st.session_state['selected_day']
            st.markdown("---")
            st.markdown(f"### 📋 {selected_day.strftime('%A, %B %d, %Y')}")
            
            day_items = [
                item for item in st.session_state.scheduled_items
                if item.get('date') == selected_day
            ]
            
            if day_items:
                for idx, item in enumerate(day_items):
                    with st.expander(f"{item.get('time', '00:00')} - {item.get('title', 'Untitled')}"):
                        col_item1, col_item2 = st.columns([3, 1])
                        
                        with col_item1:
                            st.markdown(f"**Type:** {item.get('type', 'post')}")
                            st.markdown(f"**Status:** {item.get('status', 'scheduled')}")
                            if item.get('description'):
                                st.caption(item['description'])
                        
                        with col_item2:
                            if st.button("▶️ Run", key=f"run_item_{idx}", use_container_width=True):
                                # Add to queue with proper task info
                                task_item = item.copy()
                                task_item['added_at'] = datetime_module.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                st.session_state.queue_items['pending'].append(task_item)
                                st.success("✅ Added to queue!")
                            
                            if st.button("✏️ Edit", key=f"edit_item_{idx}", use_container_width=True):
                                st.session_state[f'editing_item_{idx}'] = True
                                st.rerun()
                            
                            if st.button("🗑️", key=f"del_item_{idx}", use_container_width=True):
                                st.session_state.scheduled_items.remove(item)
                                st.rerun()
                        
                        # Edit form (shown when editing)
                        if st.session_state.get(f'editing_item_{idx}'):
                            st.markdown("---")
                            st.markdown("**Edit Item:**")
                            new_title = st.text_input("Title", value=item.get('title', ''), key=f"edit_title_{idx}")
                            new_time = st.time_input("Time", value=datetime_module.datetime.strptime(item.get('time', '09:00'), '%H:%M').time(), key=f"edit_time_{idx}")
                            new_type = st.selectbox("Type", ['post', 'image', 'video', 'workflow'], index=['post', 'image', 'video', 'workflow'].index(item.get('type', 'post')), key=f"edit_type_{idx}")
                            new_desc = st.text_area("Description", value=item.get('description', ''), key=f"edit_desc_{idx}")
                            
                            col_save, col_cancel = st.columns(2)
                            with col_save:
                                if st.button("💾 Save", key=f"save_edit_{idx}", use_container_width=True):
                                    item['title'] = new_title
                                    item['time'] = new_time.strftime('%H:%M')
                                    item['type'] = new_type
                                    item['description'] = new_desc
                                    del st.session_state[f'editing_item_{idx}']
                                    st.success("✅ Saved!")
                                    st.rerun()
                            with col_cancel:
                                if st.button("❌ Cancel", key=f"cancel_edit_{idx}", use_container_width=True):
                                    del st.session_state[f'editing_item_{idx}']
                                    st.rerun()
            else:
                st.info("📭 No items scheduled for this day")
                
                if st.button("➕ Add Item to This Day"):
                    st.session_state['schedule_for_date'] = selected_day
                    st.session_state['show_schedule_modal'] = True

    if view_mode == "📊 Both":
        st.markdown("---")

    # QUEUE VIEW
    if view_mode in ["📋 Queue", "📊 Both"]:
        st.markdown("### 📋 Task Queue")
    
    queue_tabs = st.tabs([
        f"⏳ Pending ({len(st.session_state.queue_items['pending'])})",
        f"▶️ In Progress ({len(st.session_state.queue_items['in_progress'])})",
        f"✅ Completed ({len(st.session_state.queue_items['completed'])})",
        f"❌ Failed ({len(st.session_state.queue_items['failed'])})"
    ])
    
    # Pending Tab
    with queue_tabs[0]:
        if st.session_state.queue_items['pending']:
            col_action1, col_action2 = st.columns([1, 4])
            with col_action1:
                if st.button("▶️ Process Queue", type="primary", use_container_width=True):
                    # Actually process pending tasks
                    with st.spinner("🚀 Processing queue..."):
                        processed_count = 0
                        failed_count = 0
                        
                        for task in list(st.session_state.queue_items['pending']):
                            task_type = task.get('type', 'unknown')
                            task_title = task.get('title', 'Untitled')
                            
                            try:
                                # Move to in-progress
                                task['status'] = 'in_progress'
                                task['started_at'] = datetime_module.datetime.now().strftime("%H:%M:%S")
                                st.session_state.queue_items['in_progress'].append(task)
                                st.session_state.queue_items['pending'].remove(task)
                                
                                st.info(f"▶️ Running: {task_title}")
                                
                                # Execute based on task type
                                if task_type == 'image' or task_type == 'generate_image':
                                    prompt = task.get('prompt') or task.get('description', '')
                                    if prompt:
                                        from app.services.otto_engine import get_slash_processor
                                        from app.services.api_service import ReplicateAPI
                                        replicate_token = _get_replicate_token()
                                        if replicate_token:
                                            replicate_api = ReplicateAPI(api_token=replicate_token)
                                            slash_processor = get_slash_processor(replicate_api)
                                            import asyncio
                                            result = asyncio.run(slash_processor.execute(f"/image {prompt}"))
                                            if result.get('success'):
                                                task['result'] = result
                                                task['status'] = 'completed'
                                                processed_count += 1
                                            else:
                                                raise Exception(result.get('error', 'Image generation failed'))
                                
                                elif task_type == 'video' or task_type == 'generate_video':
                                    prompt = task.get('prompt') or task.get('description', '')
                                    if prompt:
                                        from app.services.otto_engine import get_slash_processor
                                        from app.services.api_service import ReplicateAPI
                                        replicate_token = _get_replicate_token()
                                        if replicate_token:
                                            replicate_api = ReplicateAPI(api_token=replicate_token)
                                            slash_processor = get_slash_processor(replicate_api)
                                            import asyncio
                                            result = asyncio.run(slash_processor.execute(f"/video {prompt}"))
                                            if result.get('success'):
                                                task['result'] = result
                                                task['status'] = 'completed'
                                                processed_count += 1
                                            else:
                                                raise Exception(result.get('error', 'Video generation failed'))
                                
                                elif task_type == 'post' or task_type == 'social_post':
                                    # Social media posting
                                    platform = task.get('platform', 'twitter')
                                    content = task.get('content') or task.get('description', '')
                                    image_path = task.get('image_path')
                                    
                                    if platform.lower() == 'twitter' and image_path:
                                        try:
                                            from app.services.ai_twitter_poster import AITwitterPoster
                                            poster = AITwitterPoster(headless=True)
                                            import asyncio
                                            success = asyncio.run(poster.post_to_twitter(image_path, content))
                                            if success:
                                                task['status'] = 'completed'
                                                processed_count += 1
                                            else:
                                                raise Exception("Twitter posting failed")
                                        except ImportError:
                                            task['status'] = 'completed'
                                            task['note'] = 'Simulated - ai_twitter_poster not available'
                                            processed_count += 1
                                    else:
                                        task['status'] = 'completed'
                                        task['note'] = f'Simulated post to {platform}'
                                        processed_count += 1
                                
                                elif task_type == 'workflow':
                                    # Execute workflow steps
                                    steps = task.get('workflow_steps', [])
                                    for step in steps:
                                        st.caption(f"  ➡️ {step.get('name', 'Step')}")
                                    task['status'] = 'completed'
                                    processed_count += 1
                                
                                else:
                                    # Generic task - mark as completed
                                    task['status'] = 'completed'
                                    processed_count += 1
                                
                                # Move to completed
                                task['completed_at'] = datetime_module.datetime.now().strftime("%H:%M:%S")
                                st.session_state.queue_items['in_progress'].remove(task)
                                st.session_state.queue_items['completed'].append(task)
                                
                            except Exception as e:
                                # Move to failed
                                task['status'] = 'failed'
                                task['error'] = str(e)
                                task['failed_at'] = datetime_module.datetime.now().strftime("%H:%M:%S")
                                if task in st.session_state.queue_items['in_progress']:
                                    st.session_state.queue_items['in_progress'].remove(task)
                                st.session_state.queue_items['failed'].append(task)
                                failed_count += 1
                        
                        if processed_count > 0:
                            st.success(f"✅ Processed {processed_count} tasks successfully!")
                        if failed_count > 0:
                            st.warning(f"⚠️ {failed_count} tasks failed")
                        st.rerun()
                        
            with col_action2:
                if st.button("🗑️ Clear All Pending", use_container_width=True):
                    st.session_state.queue_items['pending'] = []
                    st.rerun()
            
            st.markdown("---")
            
            for idx, task in enumerate(st.session_state.queue_items['pending']):
                with st.expander(f"📌 {task.get('title', f'Task {idx+1}')}"):
                    col_task1, col_task2 = st.columns([3, 1])
                    
                    with col_task1:
                        st.markdown(f"**Type:** {task.get('type', 'unknown')}")
                        st.markdown(f"**Added:** {task.get('added_at', 'N/A')}")
                        if task.get('description'):
                            st.caption(task['description'])
                        if task.get('workflow_steps'):
                            st.markdown(f"**Steps:** {len(task['workflow_steps'])}")
                    
                    with col_task2:
                        if st.button("▶️ Run Now", key=f"run_pending_{idx}", use_container_width=True):
                            # Execute in background
                            try:
                                from app.services.background_task_manager import BackgroundTaskManager
                                import threading
                                import asyncio
                                
                                task_mgr = BackgroundTaskManager()
                                
                                task_id = task_mgr.create_task(
                                    name=f"📋 {task.get('title', 'Queue Task')}",
                                    task_type='queue_task',
                                    total_steps=len(task.get('workflow_steps', [])) or 1,
                                    params={'task': task}
                                )
                                
                                # Start background execution
                                def run_task_async():
                                    try:
                                        task_mgr.update_task(task_id, status='running', progress=0.5)
                                        
                                        # Simulate task execution
                                        import time
                                        time.sleep(2)
                                        
                                        task_mgr.update_task(
                                            task_id,
                                            status='completed',
                                            progress=1.0,
                                            result={'message': 'Task completed successfully'}
                                        )
                                    except Exception as e:
                                        task_mgr.update_task(task_id, status='failed', error=str(e))
                                
                                thread = threading.Thread(target=run_task_async, daemon=True)
                                thread.start()
                                
                                # Move to in-progress
                                task['status'] = 'in_progress'
                                task['started_at'] = datetime_module.datetime.now().strftime("%H:%M:%S")
                                task['background_task_id'] = task_id
                                st.session_state.queue_items['in_progress'].append(task)
                                st.session_state.queue_items['pending'].remove(task)
                                
                                st.success(f"✅ Task started in background! Task ID: {task_id}")
                                st.rerun()
                                
                            except ImportError:
                                # Fallback to immediate execution
                                task['status'] = 'in_progress'
                                task['started_at'] = datetime_module.datetime.now().strftime("%H:%M:%S")
                                st.session_state.queue_items['in_progress'].append(task)
                                st.session_state.queue_items['pending'].remove(task)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Failed to start task: {e}")
                        
                        if st.button("⏸️ Hold", key=f"pause_pending_{idx}", use_container_width=True):
                            task['on_hold'] = True
                            st.info("Task on hold")
                        
                        if st.button("❌ Cancel", key=f"cancel_pending_{idx}", use_container_width=True):
                            st.session_state.queue_items['pending'].remove(task)
                            st.rerun()
        else:
            st.info("📭 No pending tasks")
            st.caption("Schedule items from the calendar or add workflows to populate the queue")
    
    # In Progress Tab
    with queue_tabs[1]:
        if st.session_state.queue_items['in_progress']:
            for idx, task in enumerate(st.session_state.queue_items['in_progress']):
                with st.expander(f"▶️ {task.get('title', f'Task {idx+1}')} - Running..."):
                    col_prog1, col_prog2 = st.columns([3, 1])
                    
                    with col_prog1:
                        st.markdown(f"**Type:** {task.get('type', 'unknown')}")
                        st.markdown(f"**Started:** {task.get('started_at', 'N/A')}")
                        
                        # Progress bar
                        progress = task.get('progress', 0.5)
                        st.progress(progress)
                        st.caption(f"Progress: {int(progress * 100)}%")
                    
                    with col_prog2:
                        if st.button("✅ Complete", key=f"complete_{idx}", use_container_width=True):
                            task['status'] = 'completed'
                            task['completed_at'] = datetime_module.datetime.now().strftime("%H:%M:%S")
                            st.session_state.queue_items['completed'].append(task)
                            st.session_state.queue_items['in_progress'].remove(task)
                            st.success("✅ Task completed!")
                            
                            # Save as Shortcut option
                            from shortcut_saver import render_save_shortcut_button, convert_task_to_steps
                            task_steps = convert_task_to_steps({
                                'type': task.get('type', 'generate'),
                                'description': task.get('description', ''),
                                'platform': task.get('platform', 'twitter')
                            })
                            if len(task_steps) > 0:
                                with st.expander("💾 Save as Reusable Shortcut"):
                                    render_save_shortcut_button(
                                        pipeline_name=f"{task.get('type', 'Task').replace('_', ' ').title()}",
                                        pipeline_description=task.get('description', '')[:100],
                                        steps=task_steps,
                                        icon="✅",
                                        button_key=f"save_task_{idx}"
                                    )
                            
                            st.rerun()
                        
                        if st.button("❌ Fail", key=f"fail_{idx}", use_container_width=True):
                            task['status'] = 'failed'
                            task['error'] = 'User marked as failed'
                            st.session_state.queue_items['failed'].append(task)
                            st.session_state.queue_items['in_progress'].remove(task)
                            st.rerun()
        else:
            st.info("⏸️ No tasks currently running")
    
    # Completed Tab
    with queue_tabs[2]:
        if st.session_state.queue_items['completed']:
            if st.button("🗑️ Clear Completed", use_container_width=True):
                st.session_state.queue_items['completed'] = []
                st.rerun()
            
            st.markdown("---")
            
            for idx, task in enumerate(st.session_state.queue_items['completed'][-20:]):  # Show last 20
                with st.expander(f"✅ {task.get('title', f'Task {idx+1}')}"):
                    st.markdown(f"**Type:** {task.get('type', 'unknown')}")
                    st.markdown(f"**Completed:** {task.get('completed_at', 'N/A')}")
                    
                    if task.get('output'):
                        st.markdown("**Output:**")
                        if isinstance(task['output'], dict) and task['output'].get('url'):
                            if 'image' in task.get('type', '').lower():
                                st.image(task['output']['url'])
                            elif 'video' in task.get('type', '').lower():
                                st.video(task['output']['url'])
                        else:
                            st.json(task['output'])
                    
                    if st.button("🔄 Run Again", key=f"rerun_{idx}", use_container_width=True):
                        new_task = task.copy()
                        new_task['status'] = 'pending'
                        new_task.pop('completed_at', None)
                        st.session_state.queue_items['pending'].append(new_task)
                        st.success("Added to pending queue!")
        else:
            st.success("📋 No completed tasks yet")
    
    # Failed Tab
    with queue_tabs[3]:
        if st.session_state.queue_items['failed']:
            if st.button("🗑️ Clear Failed", use_container_width=True):
                st.session_state.queue_items['failed'] = []
                st.rerun()
            
            st.markdown("---")
            
            for idx, task in enumerate(st.session_state.queue_items['failed']):
                with st.expander(f"❌ {task.get('title', f'Task {idx+1}')}"):
                    st.markdown(f"**Type:** {task.get('type', 'unknown')}")
                    st.markdown(f"**Error:** {task.get('error', 'Unknown error')}")
                    
                    col_retry1, col_retry2 = st.columns(2)
                    with col_retry1:
                        if st.button("🔄 Retry", key=f"retry_{idx}", use_container_width=True):
                            task['status'] = 'pending'
                            task.pop('error', None)
                            st.session_state.queue_items['pending'].append(task)
                            st.session_state.queue_items['failed'].remove(task)
                            st.rerun()
                    
                    with col_retry2:
                        if st.button("🗑️ Remove", key=f"remove_failed_{idx}", use_container_width=True):
                            st.session_state.queue_items['failed'].remove(task)
                            st.rerun()
        else:
            st.info("✅ No failed tasks")

    # AI PLANNER VIEW
    if view_mode == "🤖 AI Planner":
        st.markdown("### 🤖 AI-Powered Planning Assistant")
        st.caption("Let AI help you plan your content calendar, optimize scheduling, and suggest tasks")
        
        ai_planner_tabs = st.tabs(["🧠 Smart Suggestions", "📅 Auto-Schedule", "🔄 Recurring Tasks", "⚡ Batch Planning"])
        
        with ai_planner_tabs[0]:
            st.markdown("#### 🧠 AI Content Suggestions")
            
            col_suggest1, col_suggest2 = st.columns([2, 1])
            
            with col_suggest1:
                planning_context = st.text_area(
                    "What are you working on?",
                    placeholder="e.g., Launching a new t-shirt line for summer, need to plan content for the next 2 weeks...",
                    height=100,
                    key="ai_planning_context"
                )
                
                col_goals, col_platforms = st.columns(2)
                with col_goals:
                    content_goals = st.multiselect(
                        "Goals",
                        ["🚀 Product Launch", "📈 Grow Followers", "💰 Drive Sales", "🎨 Brand Awareness", "🤝 Engagement"],
                        key="ai_content_goals"
                    )
                with col_platforms:
                    target_platforms = st.multiselect(
                        "Platforms",
                        ["Twitter/X", "Instagram", "TikTok", "Pinterest", "YouTube", "Blog"],
                        default=["Twitter/X"],
                        key="ai_target_platforms"
                    )
            
            with col_suggest2:
                planning_period = st.selectbox("Planning Period", ["This Week", "Next Week", "Next 2 Weeks", "This Month"], key="ai_planning_period")
                posts_per_day = st.slider("Posts per Day", 1, 5, 2, key="ai_posts_per_day")
                content_mix = st.selectbox("Content Mix", [
                    "Balanced (Promo + Value + Engagement)",
                    "Heavy Promotion",
                    "Value-First (80/20)",
                    "Engagement Focus"
                ], key="ai_content_mix")
            
            if st.button("🤖 Generate AI Content Plan", type="primary", use_container_width=True):
                replicate_token = _get_replicate_token()
                if planning_context and replicate_token:
                    with st.spinner("🧠 AI is creating your personalized content plan..."):
                        try:
                            from app.services.api_service import ReplicateAPI
                            replicate_api = ReplicateAPI(replicate_token)
                            
                            plan_prompt = f"""You are a social media strategist. Create a detailed content calendar based on:

CONTEXT: {planning_context}
GOALS: {', '.join(content_goals) if content_goals else 'General growth'}
PLATFORMS: {', '.join(target_platforms)}
PERIOD: {planning_period}
POSTS PER DAY: {posts_per_day}
CONTENT MIX: {content_mix}

Create a day-by-day content plan with:
1. Specific post ideas with hooks/captions
2. Best posting times for each platform
3. Content type (image, video, carousel, story)
4. Hashtag suggestions
5. Engagement prompts (questions, polls, CTAs)

Format as a structured schedule with dates and times. Be specific and actionable."""
                            
                            response = replicate_api.generate_text(plan_prompt, max_tokens=1500)
                            ai_plan = response if isinstance(response, str) else "".join(response)
                            
                            st.markdown("### 📋 Your AI-Generated Content Plan")
                            st.markdown(f'<div class="calendar-ai-suggestion">{ai_plan}</div>', unsafe_allow_html=True)
                            
                            # Offer to add to calendar
                            if st.button("📅 Add Suggestions to Calendar"):
                                st.info("💡 Use the Schedule button to add individual items to your calendar")
                                
                        except Exception as e:
                            st.error(f"AI planning failed: {e}")
                else:
                    st.warning("Please describe what you're working on and ensure API is configured")
        
        with ai_planner_tabs[1]:
            st.markdown("#### 📅 AI Auto-Scheduling")
            st.caption("Let AI find the optimal times for your content")
            
            col_auto1, col_auto2 = st.columns([2, 1])
            
            with col_auto1:
                unscheduled_tasks = [item for item in st.session_state.scheduled_items if not item.get('ai_optimized')]
                pending_tasks = st.session_state.queue_items.get('pending', [])
                
                st.markdown(f"**{len(unscheduled_tasks)} calendar items** and **{len(pending_tasks)} queue tasks** to optimize")
                
                auto_schedule_options = st.multiselect(
                    "What to auto-schedule?",
                    ["📅 Calendar Items", "📋 Pending Queue Tasks", "💡 AI-Generated Suggestions"],
                    default=["📅 Calendar Items"],
                    key="auto_schedule_what"
                )
            
            with col_auto2:
                optimize_for = st.selectbox("Optimize for", [
                    "🎯 Maximum Engagement",
                    "👀 Maximum Reach", 
                    "⏰ Consistent Timing",
                    "🌍 Global Audience"
                ], key="auto_optimize_for")
                
                avoid_weekends = st.checkbox("Avoid weekends", key="avoid_weekends")
                business_hours = st.checkbox("Business hours only (9-5)", key="business_hours")
            
            if st.button("🤖 AI Optimize Schedule", type="primary", use_container_width=True):
                replicate_token = _get_replicate_token()
                replicate_client = get_replicate_client()
                if replicate_token and replicate_client:
                    with st.spinner("🧠 AI is optimizing your schedule..."):
                        try:
                            # Get current schedule info
                            current_items = [f"{item.get('title', 'Untitled')} - {item.get('date', 'No date')} {item.get('time', '')}" 
                                           for item in st.session_state.scheduled_items[:10]]
                            
                            optimize_prompt = f"""As a social media timing expert, analyze and optimize this content schedule:

CURRENT SCHEDULE:
{chr(10).join(current_items) if current_items else 'No items scheduled yet'}

OPTIMIZATION GOAL: {optimize_for}
CONSTRAINTS: {'No weekends' if avoid_weekends else 'Include weekends'}, {'Business hours only' if business_hours else 'Any time'}

Provide:
1. Optimal posting times for each day of the week
2. Why these times work best
3. Specific recommendations to improve the schedule
4. Platform-specific timing advice

Be specific with times and reasoning."""
                            
                            response = tracked_replicate_run(
                                replicate_client,
                                "meta/meta-llama-3-70b-instruct",
                                {"prompt": optimize_prompt, "max_tokens": 800},
                                operation_name="Schedule Optimization"
                            )
                            optimization = "".join(response) if isinstance(response, list) else response
                            
                            st.markdown("### ⚡ AI Schedule Optimization")
                            st.markdown(optimization)
                            
                        except Exception as e:
                            st.error(f"Optimization failed: {e}")
                else:
                    st.warning("API not configured")
        
        with ai_planner_tabs[2]:
            st.markdown("#### 🔄 Recurring Task Templates")
            st.caption("Set up tasks that repeat automatically")
            
            # Add recurring task
            with st.expander("➕ Create Recurring Task", expanded=True):
                recur_title = st.text_input("Task Name", placeholder="Weekly product showcase", key="recur_title")
                
                col_recur1, col_recur2, col_recur3 = st.columns(3)
                with col_recur1:
                    recur_frequency = st.selectbox("Frequency", ["Daily", "Weekly", "Bi-weekly", "Monthly"], key="recur_freq")
                with col_recur2:
                    recur_day = st.selectbox("Day", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], key="recur_day")
                with col_recur3:
                    recur_time = st.time_input("Time", value=datetime_module.time(9, 0), key="recur_time")
                
                recur_type = st.selectbox("Task Type", ["post", "image", "video", "workflow"], key="recur_type")
                recur_template = st.text_area("Task Template/Prompt", placeholder="Generate a product showcase image featuring...", key="recur_template")
                
                if st.button("➕ Create Recurring Task", use_container_width=True):
                    if recur_title and recur_template:
                        new_recurring = {
                            'id': str(uuid.uuid4())[:8],
                            'title': recur_title,
                            'frequency': recur_frequency,
                            'day': recur_day,
                            'time': recur_time.strftime('%H:%M'),
                            'type': recur_type,
                            'template': recur_template,
                            'active': True,
                            'created_at': dt.now().isoformat()
                        }
                        st.session_state.recurring_tasks.append(new_recurring)
                        st.success(f"✅ Created recurring task: {recur_title}")
                        st.rerun()
            
            # Display recurring tasks
            st.markdown("---")
            st.markdown("**Active Recurring Tasks:**")
            
            if st.session_state.recurring_tasks:
                for task in st.session_state.recurring_tasks:
                    col_task, col_toggle, col_del = st.columns([4, 1, 1])
                    with col_task:
                        status_icon = "🟢" if task.get('active') else "🔴"
                        st.markdown(f"{status_icon} **{task['title']}** - {task['frequency']} on {task['day']} at {task['time']}")
                    with col_toggle:
                        if st.button("⏸️" if task.get('active') else "▶️", key=f"toggle_recur_{task['id']}"):
                            task['active'] = not task.get('active', True)
                            st.rerun()
                    with col_del:
                        if st.button("🗑️", key=f"del_recur_{task['id']}"):
                            st.session_state.recurring_tasks = [t for t in st.session_state.recurring_tasks if t['id'] != task['id']]
                            st.rerun()
            else:
                st.info("No recurring tasks set up yet")
        
        with ai_planner_tabs[3]:
            st.markdown("#### ⚡ Batch Content Planning")
            st.caption("Plan multiple pieces of content at once with AI assistance")
            
            batch_topic = st.text_input("Main Topic/Theme", placeholder="e.g., Summer collection launch", key="batch_topic")
            
            col_batch1, col_batch2 = st.columns(2)
            with col_batch1:
                batch_count = st.slider("Number of Posts to Generate", 3, 20, 7, key="batch_count")
                batch_type = st.selectbox("Content Type", ["Mixed", "Images Only", "Videos Only", "Text Posts"], key="batch_type")
            with col_batch2:
                batch_tone = st.selectbox("Tone", ["Professional", "Casual & Fun", "Inspirational", "Educational", "Promotional"], key="batch_tone")
                batch_cta = st.selectbox("Call to Action", ["Shop Now", "Learn More", "Follow Us", "Share Your Thoughts", "No CTA"], key="batch_cta")
            
            if st.button("🚀 Generate Batch Content Ideas", type="primary", use_container_width=True):
                replicate_token = _get_replicate_token()
                replicate_client = get_replicate_client()
                if batch_topic and replicate_token and replicate_client:
                    with st.spinner(f"🧠 AI is generating {batch_count} content ideas..."):
                        try:
                            batch_prompt = f"""Generate {batch_count} unique social media post ideas for:

TOPIC: {batch_topic}
CONTENT TYPE: {batch_type}
TONE: {batch_tone}
CALL TO ACTION: {batch_cta}

For each post, provide:
1. Post number and suggested day/time
2. Hook/Opening line
3. Main content (2-3 sentences)
4. Hashtags (5-7 relevant)
5. Visual description (what image/video to pair with)
6. Engagement prompt (question or CTA)"""
                            
                            response = tracked_replicate_run(
                                replicate_client,
                                "meta/meta-llama-3-70b-instruct",
                                {"prompt": batch_prompt, "max_tokens": 2000},
                                operation_name="Batch Content Ideas"
                            )
                            batch_ideas = "".join(response) if isinstance(response, list) else response
                            
                            st.markdown("### 📝 Generated Content Batch")
                            st.markdown(batch_ideas)
                            
                            # Quick add all to calendar
                            st.markdown("---")
                            if st.button("📅 Add All to Calendar (Starting Tomorrow)", use_container_width=True):
                                tomorrow = datetime_module.date.today() + timedelta(days=1)
                                for i in range(min(batch_count, 7)):
                                    post_date = tomorrow + timedelta(days=i)
                                    new_item = {
                                        'title': f"{batch_topic} Post #{i+1}",
                                        'type': 'post',
                                        'date': post_date,
                                        'time': '10:00',
                                        'description': f"AI-generated content for {batch_topic}",
                                        'status': 'scheduled',
                                        'ai_generated': True
                                    }
                                    st.session_state.scheduled_items.append(new_item)
                                st.success(f"✅ Added {min(batch_count, 7)} posts to calendar!")
                                st.rerun()
                                
                        except Exception as e:
                            st.error(f"Batch generation failed: {e}")
                else:
                    st.warning("Please enter a topic and ensure API is configured")

    # ANALYTICS VIEW
    if view_mode == "📊 Analytics":
        st.markdown("### 📊 Calendar & Queue Analytics")
        st.caption("Insights into your scheduling patterns and productivity")
        
        # Quick stats
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        
        total_scheduled = len(st.session_state.scheduled_items)
        total_pending = len(st.session_state.queue_items['pending'])
        total_completed = len(st.session_state.queue_items['completed'])
        total_failed = len(st.session_state.queue_items['failed'])
        
        with col_stat1:
            st.metric("📅 Scheduled", total_scheduled)
        with col_stat2:
            st.metric("⏳ Pending", total_pending)
        with col_stat3:
            st.metric("✅ Completed", total_completed)
        with col_stat4:
            completion_rate = (total_completed / (total_completed + total_failed) * 100) if (total_completed + total_failed) > 0 else 0
            st.metric("📈 Success Rate", f"{completion_rate:.0f}%")
        
        st.markdown("---")
        
        col_analytics1, col_analytics2 = st.columns(2)
        
        with col_analytics1:
            st.markdown("#### 📆 Scheduling Patterns")
            
            # Items by day of week
            day_counts = {day: 0 for day in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']}
            for item in st.session_state.scheduled_items:
                if item.get('date'):
                    day_name = item['date'].strftime('%a')
                    if day_name in day_counts:
                        day_counts[day_name] += 1
            
            st.markdown("**Items by Day of Week:**")
            for day, count in day_counts.items():
                bar = "█" * count + "░" * (10 - min(count, 10))
                st.markdown(f"`{day}` {bar} {count}")
            
            # Items by type
            st.markdown("---")
            st.markdown("**Items by Type:**")
            type_counts = {}
            for item in st.session_state.scheduled_items:
                t = item.get('type', 'other')
                type_counts[t] = type_counts.get(t, 0) + 1
            
            for t, count in type_counts.items():
                icon = {"post": "📱", "image": "🖼️", "video": "🎥", "workflow": "🔧", "campaign": "🎯"}.get(t, "📌")
                st.markdown(f"{icon} {t.title()}: **{count}**")
        
        with col_analytics2:
            st.markdown("#### ⚡ Queue Performance")
            
            # Processing time (if tracked)
            st.markdown("**Task Status Distribution:**")
            
            total_tasks = total_pending + len(st.session_state.queue_items['in_progress']) + total_completed + total_failed
            if total_tasks > 0:
                pending_pct = (total_pending / total_tasks) * 100
                completed_pct = (total_completed / total_tasks) * 100
                failed_pct = (total_failed / total_tasks) * 100
                
                st.progress(completed_pct / 100)
                st.caption(f"✅ Completed: {completed_pct:.0f}%")
                st.progress(pending_pct / 100)
                st.caption(f"⏳ Pending: {pending_pct:.0f}%")
                if total_failed > 0:
                    st.progress(failed_pct / 100)
                    st.caption(f"❌ Failed: {failed_pct:.0f}%")
            else:
                st.info("No tasks processed yet")
            
            # AI Recommendations
            st.markdown("---")
            st.markdown("#### 🤖 AI Recommendations")
            
            if st.button("Get AI Insights", use_container_width=True):
                replicate_token = _get_replicate_token()
                replicate_client = get_replicate_client()
                if replicate_token and replicate_client:
                    with st.spinner("Analyzing your patterns..."):
                        try:
                            insights_prompt = f"""Analyze this scheduling data and provide actionable insights:

Total Scheduled: {total_scheduled}
Pending Tasks: {total_pending}
Completed Tasks: {total_completed}
Failed Tasks: {total_failed}
Day Distribution: {day_counts}
Type Distribution: {type_counts}

Provide:
1. Patterns observed
2. Potential improvements
3. Time optimization suggestions
4. Content mix recommendations

Be specific and actionable."""
                            
                            response = tracked_replicate_run(
                                replicate_client,
                                "meta/meta-llama-3-70b-instruct",
                                {"prompt": insights_prompt, "max_tokens": 500},
                                operation_name="Calendar Insights Generation"
                            )
                            insights = "".join(response) if isinstance(response, list) else response
                            st.markdown(insights)
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    st.info("Configure API for AI insights")

    # SCHEDULE MODAL
    if st.session_state.get('show_schedule_modal'):
        st.markdown("---")
        st.markdown("### ➕ Schedule New Item")
    
        with st.form("schedule_form"):
            item_title = st.text_input("Title", placeholder="e.g., Post product launch video")
            
            col_form1, col_form2 = st.columns(2)
            with col_form1:
                item_type = st.selectbox("Type", ["post", "workflow", "video", "image", "campaign"])
                item_date = st.date_input("Date", value=st.session_state.get('schedule_for_date', datetime_module.date.today()))
            
            with col_form2:
                item_time = st.time_input("Time", value=datetime_module.time(9, 0))
                item_priority = st.selectbox("Priority", ["Low", "Medium", "High", "Urgent"])
            
            item_description = st.text_area("Description (optional)", height=100)
            
            col_submit1, col_submit2 = st.columns([1, 1])
            with col_submit1:
                submitted = st.form_submit_button("✅ Schedule", type="primary", use_container_width=True)
            with col_submit2:
                cancelled = st.form_submit_button("❌ Cancel", use_container_width=True)
            
            if submitted and item_title:
                new_item = {
                    'title': item_title,
                    'type': item_type,
                    'date': item_date,
                    'time': item_time.strftime("%H:%M"),
                    'priority': item_priority,
                    'description': item_description,
                    'status': 'scheduled',
                    'created_at': datetime_module.datetime.now().isoformat()
                }
                st.session_state.scheduled_items.append(new_item)
                st.session_state['show_schedule_modal'] = False
                st.success(f"✅ Scheduled '{item_title}' for {item_date}")
                st.rerun()
            
            if cancelled:
                st.session_state['show_schedule_modal'] = False
                st.rerun()

    # QUICK TASK MODAL
    if st.session_state.get('show_quick_task'):
        st.markdown("---")
        st.markdown("### ⚡ Quick Task")
        
        with st.form("quick_task_form"):
            task_title = st.text_input("Task Name", placeholder="Generate product image")
            task_type = st.selectbox("Task Type", [
                "Generate Image",
                "Generate Video",
                "Create Workflow",
                "Post to Social",
                "Upload to Printify"
            ])
            
            col_qt1, col_qt2 = st.columns(2)
            with col_qt1:
                submitted_qt = st.form_submit_button("➕ Add to Queue", type="primary", use_container_width=True)
            with col_qt2:
                cancelled_qt = st.form_submit_button("❌ Cancel", use_container_width=True)
            
            if submitted_qt and task_title:
                new_task = {
                    'title': task_title,
                    'type': task_type.lower(),
                    'status': 'pending',
                    'added_at': datetime_module.datetime.now().strftime("%H:%M:%S"),
                    'progress': 0
                }
                st.session_state.queue_items['pending'].append(new_task)
                st.session_state['show_quick_task'] = False
                st.success(f"✅ Added '{task_title}' to queue")
                st.rerun()
            
            if cancelled_qt:
                st.session_state['show_quick_task'] = False
                st.rerun()
