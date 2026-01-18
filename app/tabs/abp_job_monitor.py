"""
JOB MONITOR UI
==============
Real-time monitoring of all jobs across all tabs.
Shows active operations, progress, and allows cancellation.
"""

import streamlit as st
from typing import Optional
from app.services.global_job_queue import get_global_job_queue, JobStatus, JobType
from datetime import datetime
import time


def render_job_monitor():
    """Render the global job monitor UI."""
    st.subheader("🔄 Global Job Monitor")
    st.caption("Monitor all operations across all tabs in real-time")
    
    # Get queue
    queue = get_global_job_queue()
    
    # Stats row
    stats = queue.get_queue_stats()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Jobs", stats['total_jobs'])
    
    with col2:
        st.metric("Running", stats['running'], 
                 delta=None if stats['running'] == 0 else "Active")
    
    with col3:
        st.metric("Queued", stats['queued'])
    
    with col4:
        st.metric("Completed", stats['completed'])
    
    with col5:
        st.metric("Failed", stats['failed'],
                 delta="Error" if stats['failed'] > 0 else None)
    
    # Ray status
    st.info(f"{'🚀 Ray Distributed Computing: **Enabled**' if stats['ray_available'] else '⚠️ Ray: **Disabled** (running locally)'}")
    
    # Filters
    st.markdown("---")
    filter_col1, filter_col2, filter_col3 = st.columns([2, 2, 1])
    
    with filter_col1:
        tab_filter = st.selectbox(
            "Filter by Tab",
            ["All"] + list(stats['tab_counts'].keys()),
            key="job_monitor_tab_filter"
        )
    
    with filter_col2:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Running", "Queued", "Completed", "Failed"],
            key="job_monitor_status_filter"
        )
    
    with filter_col3:
        if st.button("🧹 Clear Completed", use_container_width=True):
            queue.clear_completed_jobs()
            st.success("Cleared completed jobs")
            st.rerun()
    
    # Get filtered jobs
    status_map = {
        "All": None,
        "Running": JobStatus.RUNNING,
        "Queued": JobStatus.QUEUED,
        "Completed": JobStatus.COMPLETED,
        "Failed": JobStatus.FAILED
    }
    
    jobs = queue.get_all_jobs(
        tab_name=None if tab_filter == "All" else tab_filter,
        status=status_map[status_filter]
    )
    
    if not jobs:
        st.info("No jobs to display. Submit operations from any tab to see them here.")
        return
    
    # Display jobs
    st.markdown("### Active Jobs")
    
    for job in jobs:
        # Update status (checks Ray completion)
        current_status = queue.get_job_status(job.id)
        
        # Status color
        status_colors = {
            JobStatus.QUEUED: "🟡",
            JobStatus.RUNNING: "🔵",
            JobStatus.COMPLETED: "🟢",
            JobStatus.FAILED: "🔴",
            JobStatus.CANCELLED: "⚫"
        }
        
        status_icon = status_colors.get(job.status, "⚪")
        
        with st.expander(
            f"{status_icon} [{job.tab_name}] {job.description}",
            expanded=(job.status == JobStatus.RUNNING)
        ):
            # Job details
            detail_col1, detail_col2 = st.columns(2)
            
            with detail_col1:
                st.write(f"**Job ID:** `{job.id[:8]}...`")
                st.write(f"**Type:** {job.job_type.value}")
                st.write(f"**Status:** {job.status.value}")
                st.write(f"**Priority:** {job.priority}/10")
            
            with detail_col2:
                st.write(f"**Created:** {job.created_at.strftime('%H:%M:%S')}")
                if job.started_at:
                    st.write(f"**Started:** {job.started_at.strftime('%H:%M:%S')}")
                if job.completed_at:
                    st.write(f"**Completed:** {job.completed_at.strftime('%H:%M:%S')}")
                if job.duration():
                    st.write(f"**Duration:** {job.duration():.1f}s")
            
            # Progress bar
            if job.status == JobStatus.RUNNING:
                st.progress(job.progress, text=f"Progress: {job.progress*100:.0f}%")
            
            # Error display
            if job.error:
                st.error(f"**Error:** {job.error}")
            
            # Result preview
            if job.result and job.status == JobStatus.COMPLETED:
                with st.container():
                    st.success("✅ Completed")
                    # Try to display result intelligently
                    result_str = str(job.result)
                    if len(result_str) > 200:
                        st.code(result_str[:200] + "...", language="text")
                    else:
                        st.code(result_str, language="text")
            
            # Metadata
            if job.metadata:
                with st.expander("📋 Metadata"):
                    st.json(job.metadata)
            
            # Actions
            action_col1, action_col2 = st.columns(2)
            
            with action_col1:
                if job.status in [JobStatus.QUEUED, JobStatus.RUNNING]:
                    if st.button(f"❌ Cancel", key=f"cancel_{job.id}"):
                        if queue.cancel_job(job.id):
                            st.success("Job cancelled")
                            st.rerun()
            
            with action_col2:
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    if st.button(f"🗑️ Remove", key=f"remove_{job.id}"):
                        del queue.jobs[job.id]
                        st.success("Job removed")
                        st.rerun()


def show_job_monitor_widget(location: str = "sidebar"):
    """
    Show a compact job monitor widget.
    
    Args:
        location: "sidebar" or "main"
    """
    queue = get_global_job_queue()
    stats = queue.get_queue_stats()
    
    container = st.sidebar if location == "sidebar" else st
    
    with container:
        with st.container():
            st.markdown("#### 🔄 Jobs")
            
            if stats['running'] > 0:
                st.success(f"✨ {stats['running']} running")
            
            if stats['queued'] > 0:
                st.info(f"⏳ {stats['queued']} queued")
            
            if stats['failed'] > 0:
                st.error(f"❌ {stats['failed']} failed")
            
            if stats['running'] == 0 and stats['queued'] == 0:
                st.caption("No active jobs")
            
            # Quick access to full monitor
            if st.button("📊 View All Jobs", use_container_width=True, key=f"view_jobs_{location}"):
                st.session_state.selected_section = "Job Monitor"
                st.rerun()


def get_tab_job_stats(tab_name: str) -> dict:
    """
    Get job statistics for a specific tab.
    
    Args:
        tab_name: Name of the tab
    
    Returns:
        Dictionary with running, queued, completed counts
    """
    queue = get_global_job_queue()
    tab_jobs = queue.get_all_jobs(tab_name=tab_name)
    
    return {
        'total': len(tab_jobs),
        'running': sum(1 for j in tab_jobs if j.status == JobStatus.RUNNING),
        'queued': sum(1 for j in tab_jobs if j.status == JobStatus.QUEUED),
        'completed': sum(1 for j in tab_jobs if j.status == JobStatus.COMPLETED),
        'failed': sum(1 for j in tab_jobs if j.status == JobStatus.FAILED)
    }


def show_tab_job_badge(tab_name: str):
    """
    Show job badge for a tab (for navigation).
    
    Args:
        tab_name: Name of the tab
    """
    stats = get_tab_job_stats(tab_name)
    
    if stats['running'] > 0:
        return f"🔵 {stats['running']}"
    elif stats['queued'] > 0:
        return f"🟡 {stats['queued']}"
    
    return ""
