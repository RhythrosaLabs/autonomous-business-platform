"""
Cross-Page State Manager
========================
Provides persistent state and background task execution across all Streamlit pages.

This solves the problem where:
1. Switching pages loses current progress
2. Long-running tasks stop when navigating away
3. Page state resets when returning to a page

Architecture:
- Background thread pool for long-running tasks
- Persistent state storage with auto-save
- Real-time progress tracking across pages
- Automatic state restoration on page load
"""

import streamlit as st
import threading
import queue
import time
import json
import os
import uuid
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor, Future

logger = logging.getLogger(__name__)

# Storage paths
STATE_DIR = Path("sessions/page_states")
TASKS_DIR = Path("sessions/background_tasks")
STATE_DIR.mkdir(parents=True, exist_ok=True)
TASKS_DIR.mkdir(parents=True, exist_ok=True)


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackgroundTask:
    """Represents a background task that runs across page navigation."""
    task_id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    progress_message: str = ""
    result: Any = None
    error: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    page_origin: str = ""
    logs: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        data = asdict(self)
        data['status'] = self.status.value
        # Don't serialize the result if it's not JSON-safe
        try:
            json.dumps(data['result'])
        except (TypeError, ValueError):
            data['result'] = str(data['result'])[:500] if data['result'] else None
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'BackgroundTask':
        """Restore from dict."""
        data['status'] = TaskStatus(data.get('status', 'pending'))
        return cls(**data)


class CrossPageStateManager:
    """
    Manages state persistence and background tasks across all Streamlit pages.
    
    Usage:
        # At the top of any page:
        state_manager = get_state_manager()
        state_manager.restore_page_state("page_name")
        
        # To run a long task in background:
        task_id = state_manager.run_background_task(
            name="Generate Campaign",
            func=my_long_function,
            args=(arg1, arg2),
            page="campaign"
        )
        
        # To check task status (from any page):
        status = state_manager.get_task_status(task_id)
        
        # To save page state before navigation:
        state_manager.save_page_state("page_name", {
            'concept': concept_input,
            'progress': 50,
            'results': partial_results
        })
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern to ensure one manager across all pages."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the state manager (only once due to singleton)."""
        if self._initialized:
            return
        
        self._initialized = True
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="bg_task_")
        self._tasks: Dict[str, BackgroundTask] = {}
        self._task_futures: Dict[str, Future] = {}
        self._page_states: Dict[str, Dict[str, Any]] = {}
        self._progress_queues: Dict[str, queue.Queue] = {}
        
        # Load any persisted tasks and states
        self._load_persisted_state()
        
        logger.info("CrossPageStateManager initialized")
    
    def _load_persisted_state(self):
        """Load persisted page states and task info from disk."""
        try:
            # Load page states
            for state_file in STATE_DIR.glob("*.json"):
                try:
                    with open(state_file, 'r') as f:
                        page_name = state_file.stem
                        self._page_states[page_name] = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not load state for {state_file}: {e}")
            
            # Load task metadata (not running tasks - those need to be restarted)
            for task_file in TASKS_DIR.glob("*.json"):
                try:
                    with open(task_file, 'r') as f:
                        task_data = json.load(f)
                        task = BackgroundTask.from_dict(task_data)
                        # Mark incomplete tasks as failed (they were interrupted)
                        if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                            task.status = TaskStatus.FAILED
                            task.error = "Task was interrupted by app restart"
                        self._tasks[task.task_id] = task
                except Exception as e:
                    logger.warning(f"Could not load task {task_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Error loading persisted state: {e}")
    
    def save_page_state(self, page_name: str, state: Dict[str, Any], merge: bool = True):
        """
        Save the current state of a page.
        
        Args:
            page_name: Unique identifier for the page
            state: Dictionary of state to save
            merge: If True, merge with existing state. If False, replace.
        """
        try:
            if merge and page_name in self._page_states:
                self._page_states[page_name].update(state)
            else:
                self._page_states[page_name] = state.copy()
            
            # Add metadata
            self._page_states[page_name]['_last_saved'] = datetime.now().isoformat()
            self._page_states[page_name]['_page_name'] = page_name
            
            # Persist to disk
            state_file = STATE_DIR / f"{page_name}.json"
            
            # Make state JSON-safe
            safe_state = self._make_json_safe(self._page_states[page_name])
            
            with open(state_file, 'w') as f:
                json.dump(safe_state, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving page state for {page_name}: {e}")
    
    def _make_json_safe(self, obj: Any) -> Any:
        """Convert an object to be JSON-serializable."""
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, (list, tuple)):
            return [self._make_json_safe(item) for item in obj]
        if isinstance(obj, dict):
            return {str(k): self._make_json_safe(v) for k, v in obj.items()}
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        # For other objects, try to convert to string
        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return str(obj)[:500]
    
    def restore_page_state(self, page_name: str) -> Dict[str, Any]:
        """
        Restore the saved state for a page.
        
        Args:
            page_name: Unique identifier for the page
            
        Returns:
            Dictionary of saved state, or empty dict if none
        """
        # First check memory
        if page_name in self._page_states:
            return self._page_states[page_name].copy()
        
        # Try loading from disk
        state_file = STATE_DIR / f"{page_name}.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self._page_states[page_name] = state
                    return state.copy()
            except Exception as e:
                logger.error(f"Error loading page state for {page_name}: {e}")
        
        return {}
    
    def clear_page_state(self, page_name: str):
        """
        Clear the saved state for a page.
        
        Args:
            page_name: Unique identifier for the page
        """
        try:
            # Remove from memory
            if page_name in self._page_states:
                del self._page_states[page_name]
            
            # Remove from disk
            state_file = STATE_DIR / f"{page_name}.json"
            if state_file.exists():
                state_file.unlink()
                
            logger.info(f"Cleared page state for {page_name}")
        except Exception as e:
            logger.error(f"Error clearing page state for {page_name}: {e}")
    
    def get_page_value(self, page_name: str, key: str, default: Any = None) -> Any:
        """Get a specific value from a page's saved state."""
        state = self.restore_page_state(page_name)
        return state.get(key, default)
    
    def run_background_task(
        self,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        page: str = "unknown",
        on_progress: Optional[Callable[[str, float, str], None]] = None
    ) -> str:
        """
        Run a function in the background that survives page navigation.
        
        Args:
            name: Human-readable name for the task
            func: Function to execute
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            page: Page that initiated the task
            on_progress: Optional callback(task_id, progress, message)
            
        Returns:
            task_id: Unique identifier to check task status
        """
        task_id = str(uuid.uuid4())[:8]
        kwargs = kwargs or {}
        
        # Create task record
        task = BackgroundTask(
            task_id=task_id,
            name=name,
            page_origin=page,
            status=TaskStatus.PENDING
        )
        self._tasks[task_id] = task
        
        # Create progress queue for this task
        progress_queue = queue.Queue()
        self._progress_queues[task_id] = progress_queue
        
        # Wrapper to track progress and handle completion
        def task_wrapper():
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now().isoformat()
            self._persist_task(task)
            
            try:
                # Inject progress callback if function accepts it
                if 'progress_callback' in func.__code__.co_varnames:
                    def progress_cb(message: str, progress: Optional[float] = None):
                        task.progress_message = message
                        if progress is not None:
                            task.progress = progress
                        task.logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
                        progress_queue.put((progress or task.progress, message))
                        self._persist_task(task)
                        if on_progress:
                            on_progress(task_id, task.progress, message)
                    
                    kwargs['progress_callback'] = progress_cb
                
                # Execute the function
                result = func(*args, **kwargs)
                
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.progress = 100.0
                task.progress_message = "Completed successfully"
                task.completed_at = datetime.now().isoformat()
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = f"{type(e).__name__}: {str(e)}"
                task.completed_at = datetime.now().isoformat()
                task.logs.append(f"[ERROR] {traceback.format_exc()}")
                logger.error(f"Background task {task_id} failed: {e}")
            
            finally:
                self._persist_task(task)
                progress_queue.put(None)  # Signal completion
        
        # Submit to executor
        future = self._executor.submit(task_wrapper)
        self._task_futures[task_id] = future
        
        logger.info(f"Started background task: {name} (ID: {task_id})")
        return task_id
    
    def _persist_task(self, task: BackgroundTask):
        """Save task state to disk."""
        try:
            task_file = TASKS_DIR / f"{task.task_id}.json"
            with open(task_file, 'w') as f:
                json.dump(task.to_dict(), f, indent=2)
        except Exception as e:
            logger.warning(f"Could not persist task {task.task_id}: {e}")
    
    def get_task_status(self, task_id: str) -> Optional[BackgroundTask]:
        """Get the current status of a background task."""
        return self._tasks.get(task_id)
    
    def get_task_progress(self, task_id: str) -> tuple:
        """
        Get the latest progress update for a task.
        
        Returns:
            (progress_float, message) or (None, None) if no updates
        """
        if task_id not in self._progress_queues:
            task = self._tasks.get(task_id)
            if task:
                return (task.progress, task.progress_message)
            return (None, None)
        
        q = self._progress_queues[task_id]
        latest = None
        
        # Drain queue to get latest
        while True:
            try:
                msg = q.get_nowait()
                if msg is None:  # Completion signal
                    break
                latest = msg
            except queue.Empty:
                break
        
        if latest:
            return latest
        
        task = self._tasks.get(task_id)
        if task:
            return (task.progress, task.progress_message)
        return (None, None)
    
    def get_active_tasks(self, page: Optional[str] = None) -> List[BackgroundTask]:
        """Get all active (running/pending) tasks, optionally filtered by page."""
        active = [t for t in self._tasks.values() 
                  if t.status in [TaskStatus.PENDING, TaskStatus.RUNNING]]
        if page:
            active = [t for t in active if t.page_origin == page]
        return active
    
    def get_all_tasks(self, limit: int = 50) -> List[BackgroundTask]:
        """Get all tasks, most recent first."""
        tasks = list(self._tasks.values())
        tasks.sort(key=lambda t: t.created_at or "", reverse=True)
        return tasks[:limit]
    
    def cancel_task(self, task_id: str) -> bool:
        """Attempt to cancel a running task."""
        if task_id in self._task_futures:
            future = self._task_futures[task_id]
            cancelled = future.cancel()
            if cancelled and task_id in self._tasks:
                self._tasks[task_id].status = TaskStatus.CANCELLED
                self._persist_task(self._tasks[task_id])
            return cancelled
        return False
    
    def clear_old_tasks(self, keep_hours: int = 24):
        """Remove tasks older than specified hours."""
        cutoff = datetime.now().timestamp() - (keep_hours * 3600)
        
        to_remove = []
        for task_id, task in self._tasks.items():
            try:
                created = datetime.fromisoformat(task.created_at).timestamp()
                if created < cutoff and task.status not in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                    to_remove.append(task_id)
            except:
                pass
        
        for task_id in to_remove:
            del self._tasks[task_id]
            task_file = TASKS_DIR / f"{task_id}.json"
            if task_file.exists():
                task_file.unlink()


# Singleton accessor
_state_manager_instance = None

def get_state_manager() -> CrossPageStateManager:
    """Get the singleton CrossPageStateManager instance."""
    global _state_manager_instance
    if _state_manager_instance is None:
        _state_manager_instance = CrossPageStateManager()
    return _state_manager_instance


def init_cross_page_state():
    """
    Initialize cross-page state in st.session_state.
    Call this at the start of every page.
    """
    if 'cross_page_manager' not in st.session_state:
        st.session_state.cross_page_manager = get_state_manager()
    
    if 'active_task_ids' not in st.session_state:
        st.session_state.active_task_ids = []
    
    return st.session_state.cross_page_manager


def save_current_page_state(page_name: str, extra_state: Optional[dict] = None):
    """
    Save the current page's state from st.session_state.
    
    Args:
        page_name: Unique page identifier
        extra_state: Additional state to save beyond session_state
    """
    manager = get_state_manager()
    
    # Collect relevant session state keys for this page
    page_state = {}
    
    # Save form inputs and widget states
    for key, value in st.session_state.items():
        # Skip internal Streamlit keys
        if not isinstance(key, str) or key.startswith('_') or key.startswith('FormSubmitter'):
            continue
        # Skip non-serializable objects
        try:
            json.dumps(value)
            page_state[key] = value
        except (TypeError, ValueError):
            # Try to save a representation
            if isinstance(value, Path):
                page_state[key] = str(value)
    
    # Add extra state
    if extra_state:
        page_state.update(extra_state)
    
    manager.save_page_state(page_name, page_state)


def restore_page_to_session(page_name: str, keys_to_restore: Optional[List[str]] = None):
    """
    Restore saved page state back into st.session_state.
    
    Args:
        page_name: Unique page identifier
        keys_to_restore: Specific keys to restore. If None, restores all.
    """
    manager = get_state_manager()
    saved_state = manager.restore_page_state(page_name)
    
    for key, value in saved_state.items():
        if isinstance(key, str) and key.startswith('_'):
            continue
        if keys_to_restore is None or key in keys_to_restore:
            if key not in st.session_state:
                st.session_state[key] = value


def render_active_tasks_sidebar():
    """
    Render a sidebar section showing active background tasks.
    Call this from any page to show running tasks.
    """
    manager = get_state_manager()
    active_tasks = manager.get_active_tasks()
    
    if active_tasks:
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 🔄 Background Tasks")
            
            for task in active_tasks:
                with st.container():
                    status_icon = "🔄" if task.status == TaskStatus.RUNNING else "⏳"
                    st.markdown(f"{status_icon} **{task.name}**")
                    
                    if task.progress > 0:
                        st.progress(task.progress / 100.0)
                    
                    if task.progress_message:
                        st.caption(task.progress_message[:50])
                    
                    st.caption(f"From: {task.page_origin}")
                    
                    if st.button("View Details", key=f"view_{task.task_id}"):
                        st.session_state[f'show_task_{task.task_id}'] = True


def render_task_monitor():
    """
    Render a full task monitor panel.
    Shows all tasks with detailed progress and logs.
    """
    manager = get_state_manager()
    
    st.markdown("## 📊 Task Monitor")
    
    # Tab for active vs completed
    tab1, tab2 = st.tabs(["🔄 Active Tasks", "✅ Completed Tasks"])
    
    with tab1:
        active_tasks = manager.get_active_tasks()
        if not active_tasks:
            st.info("No active tasks running")
        else:
            for task in active_tasks:
                with st.expander(f"{task.name} ({task.task_id})", expanded=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if task.progress > 0:
                            st.progress(task.progress / 100.0)
                        st.markdown(f"**Status:** {task.status.value}")
                        st.markdown(f"**Progress:** {task.progress_message}")
                        st.markdown(f"**Started:** {task.started_at or 'Pending'}")
                    with col2:
                        if st.button("Cancel", key=f"cancel_{task.task_id}"):
                            manager.cancel_task(task.task_id)
                            st.rerun()
                    
                    if task.logs:
                        st.markdown("**Recent Logs:**")
                        for log in task.logs[-5:]:
                            st.caption(log)
    
    with tab2:
        all_tasks = manager.get_all_tasks(limit=20)
        completed = [t for t in all_tasks if t.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]]
        
        if not completed:
            st.info("No completed tasks yet")
        else:
            for task in completed:
                status_icon = "✅" if task.status == TaskStatus.COMPLETED else "❌"
                with st.expander(f"{status_icon} {task.name} - {task.completed_at}", expanded=False):
                    st.markdown(f"**Status:** {task.status.value}")
                    if task.error:
                        st.error(task.error)
                    if task.result:
                        st.json(task.result if isinstance(task.result, dict) else {"result": str(task.result)[:500]})


# Decorator for background execution
def run_in_background(name: Optional[str] = None, page: str = "unknown"):
    """
    Decorator to run a function in the background.
    
    Usage:
        @run_in_background(name="Generate Products", page="campaign")
        def generate_products(concept, num_products):
            ...
            return results
        
        # Returns task_id immediately
        task_id = generate_products(concept, 5)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            task_name = name or func.__name__
            manager = get_state_manager()
            return manager.run_background_task(
                name=task_name,
                func=func,
                args=args,
                kwargs=kwargs,
                page=page
            )
        return wrapper
    return decorator


def render_campaign_status_banner():
    """
    Render a banner showing the status of any active or recently completed campaign.
    Returns True if there's an active campaign running, False otherwise.
    """
    import streamlit as st
    
    # Check for active campaign in session state
    active_campaign = st.session_state.get('active_campaign', {})
    
    if not active_campaign:
        # Try to restore from saved state
        manager = get_state_manager()
        saved_state = manager.restore_page_state("main_dashboard")
        if saved_state:
            active_campaign = saved_state
            st.session_state['active_campaign'] = active_campaign
    
    if not active_campaign:
        return False
    
    status = active_campaign.get('status', '')
    
    if status == 'completed':
        # Don't show completion banner at top - it's shown in dashboard stats
        return False
    
    elif status == 'running':
        # Check for timeout (if running for more than 5 minutes without update)
        import datetime as dt
        if 'campaign_start_time' in active_campaign:
            start_time = dt.datetime.fromisoformat(active_campaign['campaign_start_time'])
            elapsed = (dt.datetime.now() - start_time).total_seconds()
            if elapsed > 300:  # 5 minutes timeout
                st.session_state.pop('active_campaign', None)
                manager = get_state_manager()
                manager.clear_page_state("main_dashboard")
                return False
        
        # Show progress banner with WORKING dismiss button
        col1, col2 = st.columns([5, 1])
        with col1:
            current_step = active_campaign.get('current_step', 0)
            total_steps = active_campaign.get('total_steps', 1)
            progress = current_step / max(total_steps, 1)
            
            st.info(f"""
                🔄 **Campaign In Progress**
                - Concept: {active_campaign.get('concept', 'Unknown')[:50]}...
                - Progress: Step {current_step}/{total_steps} - {active_campaign.get('progress_message', '')}
            """)
            st.progress(progress)
            st.caption(f"⏱️ Elapsed: {active_campaign.get('elapsed_seconds', 0):.0f}s")
        
        with col2:
            # Use form to ensure button actually works
            with st.form(key="dismiss_campaign_form"):
                if st.form_submit_button("✖️", help="Dismiss this notification"):
                    st.session_state.pop('active_campaign', None)
                    manager = get_state_manager()
                    manager.clear_page_state("main_dashboard")
                    st.rerun()
        
        return True
    
    elif status == 'failed':
        # Show error banner
        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.error(f"""
                    ❌ **Campaign Failed**
                    - Concept: {active_campaign.get('concept', 'Unknown')[:50]}...
                    - Error: {active_campaign.get('error', 'Unknown error')}
                """)
            with col2:
                if st.button("✖️ Dismiss", key="dismiss_failed_campaign"):
                    st.session_state.pop('active_campaign', None)
                    manager = get_state_manager()
                    manager.clear_page_state("main_dashboard")
                    st.rerun()
        return False
    
    return False


    # Also show recent failures in the status area (compact)
    try:
        from background_tasks import get_task_manager, TaskState
        manager = get_task_manager()
        failed_tasks = [t for t in manager.get_all_tasks() if t.state == TaskState.FAILED]
        if failed_tasks:
            with st.container():
                st.markdown("---")
                st.markdown("### ❌ Recent Task Failures")
                for t in failed_tasks[:5]:
                    col1, col2, col3 = st.columns([6, 3, 2])
                    with col1:
                        st.markdown(f"**{t.name}**")
                        if t.logs:
                            st.caption(t.logs[-1][:140])
                        else:
                            st.caption(t.error or "Unknown error")
                    with col2:
                        if t.artifacts:
                            st.write(f"Artifacts: {len(t.artifacts)}")
                    with col3:
                        if st.button("🔁 Retry", key=f"status_retry_{t.id}"):
                            try:
                                manager.manual_retry_task(t.id, reset_attempts=True)
                                st.success("Retry initiated — task restarted in background.")
                                st.experimental_rerun()
                            except Exception as e:
                                st.error(f"Could not retry task: {e}")
    except Exception:
        # If anything goes wrong displaying failures, don't block the status banner
        pass
