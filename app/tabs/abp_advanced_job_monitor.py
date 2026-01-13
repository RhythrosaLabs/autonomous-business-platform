"""
Advanced Job Monitor Tab
Comprehensive job tracking, Ray dashboard integration, and performance analytics
"""

from abp_imports_common import st, datetime, Path
import time
from typing import Dict, List, Any
from tab_job_helpers import (
    check_jobs_progress,
    are_all_jobs_done,
    collect_job_results,
    get_global_job_queue
)
from global_job_queue import JobStatus, JobType


def render_advanced_job_monitor_tab():
    """Render comprehensive job monitoring interface."""
    st.markdown("### 🔍 Advanced Job Monitor")
    st.markdown("Real-time job tracking, Ray cluster stats, and performance analytics")
    
    # Top metrics bar
    queue = get_global_job_queue()
    all_jobs = list(queue.jobs.values())
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total = len(all_jobs)
        st.metric("📊 Total Jobs", total)
    
    with col2:
        running = sum(1 for j in all_jobs if j.status == JobStatus.RUNNING)
        st.metric("⚡ Running", running, delta=None if running == 0 else "Active")
    
    with col3:
        queued = sum(1 for j in all_jobs if j.status == JobStatus.QUEUED)
        st.metric("⏳ Queued", queued)
    
    with col4:
        completed = sum(1 for j in all_jobs if j.status == JobStatus.COMPLETED)
        success_rate = (completed / total * 100) if total > 0 else 0
        st.metric("✅ Completed", completed, delta=f"{success_rate:.0f}%")
    
    with col5:
        failed = sum(1 for j in all_jobs if j.status == JobStatus.FAILED)
        st.metric("❌ Failed", failed, delta="-" if failed > 0 else None)
    
    # Tabs for different views
    monitor_tabs = st.tabs([
        "🎯 Active Jobs",
        "📊 All Jobs",
        "📈 Analytics",
        "🖥️ Ray Dashboard",
        "⚙️ Settings"
    ])
    
    # TAB 1: Active Jobs (Running + Queued)
    with monitor_tabs[0]:
        st.markdown("#### ⚡ Currently Active Jobs")
        
        active_jobs = [j for j in all_jobs if j.status in [JobStatus.RUNNING, JobStatus.QUEUED]]
        
        if not active_jobs:
            st.info("🎉 No active jobs! All systems idle.")
        else:
            # Auto-refresh toggle
            auto_refresh = st.checkbox("🔄 Auto-refresh every 2 seconds", value=True, key="auto_refresh_active")
            
            for job in sorted(active_jobs, key=lambda x: x.created_at, reverse=True):
                with st.expander(
                    f"{'⚡' if job.status == JobStatus.RUNNING else '⏳'} {job.description} - {job.tab_name}",
                    expanded=True
                ):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.caption(f"**Job ID:** `{job.id[:8]}...`")
                        st.caption(f"**Type:** {job.job_type.value}")
                        st.caption(f"**Status:** {job.status.value.upper()}")
                        
                        # Progress bar
                        progress = job.progress
                        st.progress(progress, text=f"{progress*100:.0f}% complete")
                        
                        # Timing info
                        elapsed = (datetime.now() - job.started_at).total_seconds() if job.started_at else 0
                        st.caption(f"⏱️ Elapsed: {elapsed:.1f}s")
                    
                    with col2:
                        st.caption(f"**Priority:** {job.priority}/10")
                        
                        # Resource allocation (if available)
                        from global_job_queue import RESOURCE_PROFILES
                        resources = RESOURCE_PROFILES.get(job.job_type, {})
                        if resources:
                            st.caption(f"**CPUs:** {resources.get('num_cpus', 1)}")
                            st.caption(f"**RAM:** {resources.get('memory', 0) / 1_000_000:.0f}MB")
            
            if auto_refresh:
                time.sleep(2)
                st.rerun()
    
    # TAB 2: All Jobs (with filters)
    with monitor_tabs[1]:
        st.markdown("#### 📋 Job History & Management")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            filter_tab = st.selectbox(
                "Filter by Tab",
                ["All"] + list(set(j.tab_name for j in all_jobs)),
                key="filter_tab"
            )
        
        with col2:
            filter_status = st.selectbox(
                "Filter by Status",
                ["All", "Running", "Queued", "Completed", "Failed"],
                key="filter_status"
            )
        
        with col3:
            filter_type = st.selectbox(
                "Filter by Type",
                ["All"] + [jt.value for jt in JobType],
                key="filter_type"
            )
        
        # Apply filters
        filtered_jobs = all_jobs
        if filter_tab != "All":
            filtered_jobs = [j for j in filtered_jobs if j.tab_name == filter_tab]
        if filter_status != "All":
            status_map = {
                "Running": JobStatus.RUNNING,
                "Queued": JobStatus.QUEUED,
                "Completed": JobStatus.COMPLETED,
                "Failed": JobStatus.FAILED
            }
            filtered_jobs = [j for j in filtered_jobs if j.status == status_map[filter_status]]
        if filter_type != "All":
            filtered_jobs = [j for j in filtered_jobs if j.job_type.value == filter_type]
        
        st.caption(f"Showing {len(filtered_jobs)} of {len(all_jobs)} jobs")
        
        # Display jobs in table
        if filtered_jobs:
            for job in sorted(filtered_jobs, key=lambda x: x.created_at, reverse=True)[:50]:
                status_emoji = {
                    JobStatus.RUNNING: "⚡",
                    JobStatus.QUEUED: "⏳",
                    JobStatus.COMPLETED: "✅",
                    JobStatus.FAILED: "❌",
                    JobStatus.CANCELLED: "🚫"
                }.get(job.status, "❓")
                
                with st.expander(f"{status_emoji} {job.description} - {job.created_at.strftime('%H:%M:%S')}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.caption(f"**ID:** `{job.id[:16]}`")
                        st.caption(f"**Tab:** {job.tab_name}")
                        st.caption(f"**Type:** {job.job_type.value}")
                        st.caption(f"**Created:** {job.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        if job.started_at:
                            st.caption(f"**Started:** {job.started_at.strftime('%H:%M:%S')}")
                        if job.completed_at:
                            st.caption(f"**Completed:** {job.completed_at.strftime('%H:%M:%S')}")
                            duration = job.duration()
                            st.caption(f"**Duration:** {duration:.2f}s")
                    
                    with col2:
                        st.caption(f"**Status:** {job.status.value.upper()}")
                        st.caption(f"**Priority:** {job.priority}")
                        st.caption(f"**Progress:** {job.progress*100:.0f}%")
                        
                        if job.error:
                            st.error(f"Error: {job.error[:100]}...")
                        
                        if job.result and job.status == JobStatus.COMPLETED:
                            if st.button("📄 View Result", key=f"view_{job.id}"):
                                st.json(str(job.result)[:500])
        else:
            st.info("No jobs match the current filters")
    
    # TAB 3: Analytics
    with monitor_tabs[2]:
        st.markdown("#### 📈 Performance Analytics")
        
        if not all_jobs:
            st.info("No job data yet. Run some operations to see analytics!")
        else:
            # Job type distribution
            st.markdown("**Job Distribution by Type**")
            type_counts = {}
            for job in all_jobs:
                type_name = job.job_type.value
                type_counts[type_name] = type_counts.get(type_name, 0) + 1
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.bar_chart(type_counts)
            with col2:
                for job_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
                    st.caption(f"**{job_type}:** {count}")
            
            st.markdown("---")
            
            # Performance metrics
            st.markdown("**⚡ Performance Metrics**")
            
            completed_jobs = [j for j in all_jobs if j.status == JobStatus.COMPLETED and j.duration()]
            
            if completed_jobs:
                col1, col2, col3 = st.columns(3)
                
                durations = [j.duration() for j in completed_jobs]
                avg_duration = sum(durations) / len(durations)
                min_duration = min(durations)
                max_duration = max(durations)
                
                with col1:
                    st.metric("⏱️ Avg Duration", f"{avg_duration:.2f}s")
                with col2:
                    st.metric("🚀 Fastest Job", f"{min_duration:.2f}s")
                with col3:
                    st.metric("🐌 Slowest Job", f"{max_duration:.2f}s")
                
                # Success rate by tab
                st.markdown("**📊 Success Rate by Tab**")
                tab_stats = {}
                for job in all_jobs:
                    if job.tab_name not in tab_stats:
                        tab_stats[job.tab_name] = {"total": 0, "completed": 0, "failed": 0}
                    tab_stats[job.tab_name]["total"] += 1
                    if job.status == JobStatus.COMPLETED:
                        tab_stats[job.tab_name]["completed"] += 1
                    elif job.status == JobStatus.FAILED:
                        tab_stats[job.tab_name]["failed"] += 1
                
                for tab_name, stats in sorted(tab_stats.items()):
                    success_rate = (stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                    col1.caption(f"**{tab_name}**")
                    col2.caption(f"Total: {stats['total']}")
                    col3.caption(f"✅ {stats['completed']}")
                    col4.caption(f"❌ {stats['failed']} ({success_rate:.0f}%)")
            else:
                st.info("No completed jobs yet")
    
    # TAB 4: Ray Dashboard Integration
    with monitor_tabs[3]:
        st.markdown("#### 🖥️ Ray Cluster Dashboard")
        
        st.markdown("""
        The Ray dashboard provides detailed insights into:
        - **Worker utilization** across CPU cores
        - **Memory usage** per worker
        - **Task execution timeline**
        - **Actor lifecycle tracking**
        - **Resource allocation** in real-time
        """)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**📍 Quick Links:**")
            st.markdown("- [Ray Dashboard](http://127.0.0.1:8265) - Main dashboard")
            st.markdown("- [Jobs View](http://127.0.0.1:8265/#/jobs) - Job timeline")
            st.markdown("- [Cluster View](http://127.0.0.1:8265/#/cluster) - Resource usage")
        
        with col2:
            st.markdown("**🔧 Ray Status:**")
            try:
                import ray
                if ray.is_initialized():
                    st.success("✅ Ray cluster is active")
                    resources = ray.available_resources()
                    st.caption(f"CPUs available: {resources.get('CPU', 0):.1f}")
                    st.caption(f"Memory available: {resources.get('memory', 0) / 1e9:.1f}GB")
                else:
                    st.warning("⚠️ Ray not initialized")
            except:
                st.error("❌ Ray not available")
        
        # Embed Ray dashboard
        st.markdown("---")
        if st.checkbox("📺 Embed Ray Dashboard", value=False, key="embed_ray"):
            st.components.v1.iframe("http://127.0.0.1:8265", height=800, scrolling=True)
    
    # TAB 5: Settings & Actions
    with monitor_tabs[4]:
        st.markdown("#### ⚙️ Job Monitor Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🧹 Cleanup Actions**")
            
            if st.button("🗑️ Clear Completed Jobs", use_container_width=True):
                completed_count = 0
                for job_id in list(queue.jobs.keys()):
                    if queue.jobs[job_id].status == JobStatus.COMPLETED:
                        del queue.jobs[job_id]
                        completed_count += 1
                st.success(f"Cleared {completed_count} completed jobs")
                st.rerun()
            
            if st.button("❌ Clear Failed Jobs", use_container_width=True):
                failed_count = 0
                for job_id in list(queue.jobs.keys()):
                    if queue.jobs[job_id].status == JobStatus.FAILED:
                        del queue.jobs[job_id]
                        failed_count += 1
                st.success(f"Cleared {failed_count} failed jobs")
                st.rerun()
            
            if st.button("🧹 Clear All Job History", type="secondary", use_container_width=True):
                total_count = len(queue.jobs)
                queue.jobs.clear()
                st.success(f"Cleared {total_count} jobs from history")
                st.rerun()
        
        with col2:
            st.markdown("**📊 Export Options**")
            
            if st.button("📥 Export Job History (JSON)", use_container_width=True):
                import json
                export_data = {
                    "exported_at": datetime.now().isoformat(),
                    "total_jobs": len(all_jobs),
                    "jobs": [job.to_dict() for job in all_jobs]
                }
                st.download_button(
                    "💾 Download JSON",
                    data=json.dumps(export_data, indent=2),
                    file_name=f"job_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            
            if st.button("📊 Export Analytics (CSV)", use_container_width=True):
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["Job ID", "Tab", "Type", "Status", "Created", "Duration", "Priority"])
                
                for job in all_jobs:
                    writer.writerow([
                        job.id[:8],
                        job.tab_name,
                        job.job_type.value,
                        job.status.value,
                        job.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        f"{job.duration():.2f}s" if job.duration() else "N/A",
                        job.priority
                    ])
                
                st.download_button(
                    "💾 Download CSV",
                    data=output.getvalue(),
                    file_name=f"job_analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        st.markdown("---")
        st.markdown("**🔧 Advanced Options**")
        
        max_jobs = st.slider(
            "Max concurrent jobs (requires restart)",
            min_value=5,
            max_value=50,
            value=10,
            help="Maximum number of jobs running simultaneously"
        )
        
        st.caption(f"Current setting: {queue.max_concurrent_jobs} concurrent jobs")
