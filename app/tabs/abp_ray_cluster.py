"""
RAY CLUSTER UI COMPONENT
=========================
Streamlit UI for monitoring and controlling Ray distributed execution.
"""

import streamlit as st
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def render_ray_cluster_ui():
    """Render Ray cluster status and controls."""
    
    st.markdown("### 🚀 Distributed Computing (Ray)")
    
    # Check if Ray is available
    try:
        from ray_task_wrapper import get_ray_manager, HAS_RAY
        
        if not HAS_RAY:
            st.warning("⚠️ Ray is not installed. Install with: `pip install 'ray[default]>=2.9.0'`")
            st.info("Ray enables distributed task execution across multiple CPU/GPU workers for faster processing of heavy workloads (video generation, batch operations).")
            return
        
        # Initialize session state (enabled by default)
        if 'ray_enabled' not in st.session_state:
            from abp_config import AppConfig
            st.session_state.ray_enabled = AppConfig.ENABLE_RAY_DISTRIBUTED
        
        # Enable/Disable toggle
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.info("🔬 **Experimental Feature**: Distribute heavy tasks (video, batch operations) across workers")
        
        with col2:
            enable_ray = st.toggle(
                "Enable Ray",
                value=st.session_state.ray_enabled,
                key="ray_toggle",
                help="Enable distributed task execution using Ray"
            )
        
        # Update state
        if enable_ray != st.session_state.ray_enabled:
            st.session_state.ray_enabled = enable_ray
            st.rerun()
        
        if enable_ray:
            # Get Ray manager
            try:
                ray_manager = get_ray_manager(enable_ray=True)
                status = ray_manager.get_cluster_status()
                
                if status.get("available"):
                    st.success("✅ Ray cluster is running")
                    
                    # Resource metrics
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "Available CPUs",
                            f"{status['available_cpus']:.0f}/{status['total_cpus']:.0f}",
                            help="CPU cores available for task execution"
                        )
                    
                    with col2:
                        st.metric(
                            "Available GPUs",
                            f"{status['available_gpus']:.0f}/{status['total_gpus']:.0f}",
                            help="GPU devices available for task execution"
                        )
                    
                    with col3:
                        st.metric(
                            "Memory",
                            f"{status['available_memory_gb']:.1f}/{status['total_memory_gb']:.1f} GB",
                            help="Available system memory"
                        )
                    
                    with col4:
                        if st.button("📊 Open Dashboard", use_container_width=True):
                            st.link_button(
                                "Ray Dashboard",
                                status['dashboard_url'],
                                help="Open Ray's web dashboard for detailed monitoring"
                            )
                    
                    # Resource profile information
                    with st.expander("ℹ️ Resource Profiles"):
                        st.markdown("""
                        Ray automatically allocates resources based on task type:
                        
                        - **Light** (1 CPU, 1GB): Text generation, API calls
                        - **Medium** (2 CPUs, 4GB): Image generation, data processing
                        - **Heavy** (4 CPUs, 8GB): Video generation, batch operations
                        - **GPU** (2 CPUs, 1 GPU, 8GB): GPU-accelerated tasks
                        """)
                    
                    # Usage hints
                    with st.expander("💡 Usage Tips"):
                        st.markdown("""
                        - Ray automatically distributes tasks when you use the Task Queue
                        - Video generation and batch operations benefit most from Ray
                        - Monitor the dashboard to see task distribution in real-time
                        - Ray will gracefully fallback to local execution if workers are busy
                        """)
                
                else:
                    st.error(f"❌ Ray cluster error: {status.get('error', 'Unknown error')}")
                    st.info("Ray will fallback to local execution")
            
            except Exception as e:
                st.error(f"❌ Failed to initialize Ray: {e}")
                st.info("Tasks will run locally without distribution")
        
        else:
            st.info("ℹ️ Ray is disabled. Tasks will run locally on this machine.")
    
    except ImportError as e:
        st.error(f"❌ Ray module import error: {e}")
        st.info("Install Ray with: `pip install 'ray[default]>=2.9.0'`")


def get_ray_status() -> dict:
    """Get current Ray status for use in other components."""
    try:
        from ray_task_wrapper import get_ray_manager, HAS_RAY
        
        if not HAS_RAY:
            return {"available": False, "reason": "Ray not installed"}
        
        if not st.session_state.get('ray_enabled', False):
            return {"available": False, "reason": "Ray disabled by user"}
        
        ray_manager = get_ray_manager(enable_ray=True)
        return ray_manager.get_cluster_status()
    
    except Exception as e:
        return {"available": False, "error": str(e)}


def should_use_ray() -> bool:
    """Check if Ray should be used for task execution."""
    status = get_ray_status()
    return status.get("available", False)
