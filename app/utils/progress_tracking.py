"""
Advanced progress tracking with cancellation support and ETA estimation
Provides detailed progress feedback with pause/resume/cancel capabilities
"""

import time
import streamlit as st
from typing import Optional, Callable, Any, List, Dict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading


class ProgressStatus(Enum):
    """Progress operation status"""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressStep:
    """Individual step in a progress operation"""
    name: str
    weight: float = 1.0  # Relative weight for progress calculation
    status: ProgressStatus = ProgressStatus.NOT_STARTED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Get step duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return None


class CancellableProgress:
    """
    Progress tracker with cancellation, pause/resume, and ETA estimation
    Thread-safe for background operations
    """
    
    def __init__(
        self,
        total_steps: int = 100,
        operation_name: str = "Operation",
        show_eta: bool = True,
        show_details: bool = True
    ):
        self.total_steps = total_steps
        self.operation_name = operation_name
        self.show_eta = show_eta
        self.show_details = show_details
        
        self.current_step = 0
        self.status = ProgressStatus.NOT_STARTED
        self.start_time = None
        self.pause_time = None
        self.total_pause_duration = 0.0
        
        self.steps: List[ProgressStep] = []
        self.current_step_obj: Optional[ProgressStep] = None
        
        self._cancel_flag = threading.Event()
        self._pause_flag = threading.Event()
        
        # UI elements
        self.progress_bar = None
        self.status_text = None
        self.eta_text = None
        self.details_container = None
        self.control_cols = None
    
    def initialize_ui(self):
        """Initialize Streamlit UI elements"""
        # Main progress bar
        self.progress_bar = st.progress(0)
        
        # Status and ETA row
        col1, col2 = st.columns([3, 1])
        with col1:
            self.status_text = st.empty()
        with col2:
            if self.show_eta:
                self.eta_text = st.empty()
        
        # Control buttons
        self.control_cols = st.columns([1, 1, 1, 2])
        
        # Details section
        if self.show_details:
            self.details_container = st.expander("📊 Progress Details", expanded=False)
    
    def add_step(self, name: str, weight: float = 1.0) -> ProgressStep:
        """Add a named step to track"""
        step = ProgressStep(name=name, weight=weight)
        self.steps.append(step)
        return step
    
    def start(self):
        """Start the operation"""
        self.status = ProgressStatus.RUNNING
        self.start_time = datetime.now()
        self._cancel_flag.clear()
        self._pause_flag.clear()
        
        if self.status_text:
            self.status_text.info(f"🚀 Starting {self.operation_name}...")
    
    def update(
        self,
        step: int = None,
        message: str = None,
        increment: int = 1
    ):
        """Update progress"""
        if self._cancel_flag.is_set():
            return
        
        # Handle pause
        while self._pause_flag.is_set() and not self._cancel_flag.is_set():
            time.sleep(0.1)
        
        if step is not None:
            self.current_step = step
        else:
            self.current_step += increment
        
        progress = min(self.current_step / self.total_steps, 1.0)
        
        # Update progress bar
        if self.progress_bar:
            self.progress_bar.progress(progress)
        
        # Update status text
        if self.status_text:
            status_msg = message or f"{self.operation_name}: {int(progress * 100)}%"
            self.status_text.info(status_msg)
        
        # Update ETA
        if self.show_eta and self.eta_text and progress > 0:
            eta = self._calculate_eta(progress)
            if eta:
                self.eta_text.metric("ETA", eta)
        
        # Update details
        if self.show_details and self.details_container:
            self._update_details()
    
    def start_step(self, step_name: str) -> ProgressStep:
        """Start a named step"""
        step = self.add_step(step_name)
        step.status = ProgressStatus.RUNNING
        step.start_time = datetime.now()
        self.current_step_obj = step
        
        self.update(message=f"⚙️ {step_name}...")
        return step
    
    def complete_step(self, result: Any = None):
        """Complete current step"""
        if self.current_step_obj:
            self.current_step_obj.status = ProgressStatus.COMPLETED
            self.current_step_obj.end_time = datetime.now()
            self.current_step_obj.result = result
    
    def fail_step(self, error: str):
        """Mark current step as failed"""
        if self.current_step_obj:
            self.current_step_obj.status = ProgressStatus.FAILED
            self.current_step_obj.end_time = datetime.now()
            self.current_step_obj.error = error
    
    def pause(self):
        """Pause the operation"""
        self._pause_flag.set()
        self.pause_time = datetime.now()
        self.status = ProgressStatus.PAUSED
        
        if self.status_text:
            self.status_text.warning(f"⏸️ {self.operation_name} paused")
    
    def resume(self):
        """Resume the operation"""
        if self.pause_time:
            pause_duration = (datetime.now() - self.pause_time).total_seconds()
            self.total_pause_duration += pause_duration
            self.pause_time = None
        
        self._pause_flag.clear()
        self.status = ProgressStatus.RUNNING
        
        if self.status_text:
            self.status_text.info(f"▶️ {self.operation_name} resumed")
    
    def cancel(self):
        """Cancel the operation"""
        self._cancel_flag.set()
        self.status = ProgressStatus.CANCELLED
        
        if self.status_text:
            self.status_text.error(f"🛑 {self.operation_name} cancelled")
    
    def complete(self, message: str = None):
        """Mark operation as completed"""
        self.status = ProgressStatus.COMPLETED
        self.current_step = self.total_steps
        
        if self.progress_bar:
            self.progress_bar.progress(1.0)
        
        if self.status_text:
            final_msg = message or f"✅ {self.operation_name} completed!"
            self.status_text.success(final_msg)
        
        # Show final duration
        if self.eta_text and self.start_time:
            duration = self._get_active_duration()
            self.eta_text.metric("Duration", f"{duration:.1f}s")
    
    def fail(self, error: str):
        """Mark operation as failed"""
        self.status = ProgressStatus.FAILED
        
        if self.status_text:
            self.status_text.error(f"❌ {self.operation_name} failed: {error}")
    
    def is_cancelled(self) -> bool:
        """Check if operation was cancelled"""
        return self._cancel_flag.is_set()
    
    def is_paused(self) -> bool:
        """Check if operation is paused"""
        return self._pause_flag.is_set()
    
    def render_controls(self):
        """Render pause/resume/cancel buttons"""
        if not self.control_cols:
            return
        
        with self.control_cols[0]:
            if self.status == ProgressStatus.RUNNING:
                if st.button("⏸️ Pause", key=f"{self.operation_name}_pause"):
                    self.pause()
                    st.rerun()
        
        with self.control_cols[1]:
            if self.status == ProgressStatus.PAUSED:
                if st.button("▶️ Resume", key=f"{self.operation_name}_resume"):
                    self.resume()
                    st.rerun()
        
        with self.control_cols[2]:
            if self.status in [ProgressStatus.RUNNING, ProgressStatus.PAUSED]:
                if st.button("🛑 Cancel", key=f"{self.operation_name}_cancel"):
                    self.cancel()
                    st.rerun()
    
    def _calculate_eta(self, progress: float) -> Optional[str]:
        """Calculate estimated time remaining"""
        if not self.start_time or progress <= 0:
            return None
        
        elapsed = self._get_active_duration()
        estimated_total = elapsed / progress
        remaining = estimated_total - elapsed
        
        if remaining < 0:
            return "Almost done..."
        elif remaining < 60:
            return f"{int(remaining)}s"
        elif remaining < 3600:
            minutes = int(remaining / 60)
            seconds = int(remaining % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(remaining / 3600)
            minutes = int((remaining % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    def _get_active_duration(self) -> float:
        """Get active duration excluding pauses"""
        if not self.start_time:
            return 0.0
        
        total_elapsed = (datetime.now() - self.start_time).total_seconds()
        return total_elapsed - self.total_pause_duration
    
    def _update_details(self):
        """Update detailed progress information"""
        if not self.details_container or not self.steps:
            return
        
        with self.details_container:
            for i, step in enumerate(self.steps, 1):
                status_icon = {
                    ProgressStatus.NOT_STARTED: "⚪",
                    ProgressStatus.RUNNING: "🔵",
                    ProgressStatus.PAUSED: "🟡",
                    ProgressStatus.COMPLETED: "✅",
                    ProgressStatus.FAILED: "❌",
                    ProgressStatus.CANCELLED: "🛑"
                }.get(step.status, "⚪")
                
                duration_str = ""
                if step.duration:
                    duration_str = f" ({step.duration:.1f}s)"
                
                st.text(f"{status_icon} {i}. {step.name}{duration_str}")
                
                if step.error:
                    st.caption(f"   Error: {step.error}")
    
    def cleanup(self):
        """Clean up UI elements"""
        if self.progress_bar:
            self.progress_bar.empty()
        if self.status_text:
            self.status_text.empty()
        if self.eta_text:
            self.eta_text.empty()


def create_progress_tracker(
    operation_name: str = "Operation",
    total_steps: int = 100,
    show_controls: bool = True
) -> CancellableProgress:
    """
    Create and initialize a progress tracker with UI
    
    Args:
        operation_name: Name of the operation
        total_steps: Total number of steps
        show_controls: Show pause/resume/cancel controls
    
    Returns:
        CancellableProgress instance
    """
    tracker = CancellableProgress(
        total_steps=total_steps,
        operation_name=operation_name
    )
    tracker.initialize_ui()
    
    if show_controls:
        tracker.render_controls()
    
    return tracker


def run_with_progress(
    func: Callable,
    operation_name: str = "Operation",
    total_steps: int = 100,
    *args,
    **kwargs
) -> Any:
    """
    Run a function with progress tracking
    
    The function should accept a 'progress' parameter of type CancellableProgress
    and call progress.update() and check progress.is_cancelled()
    """
    progress = create_progress_tracker(operation_name, total_steps)
    progress.start()
    
    try:
        result = func(*args, progress=progress, **kwargs)
        
        if progress.is_cancelled():
            progress.complete("Operation was cancelled")
            return None
        else:
            progress.complete()
            return result
    
    except Exception as e:
        progress.fail(str(e))
        raise e
