"""
BACKGROUND TASK MANAGER
========================
Manages long-running tasks that persist across Streamlit page changes.
Uses threading and session state persistence to maintain task state.

Key Features:
1. Tasks continue running when user navigates away
2. State persists in a JSON file for recovery
3. Real-time status updates via polling
4. Retry logic with exponential backoff for API failures
5. Thread-safe task queue management
"""

from app.tabs.abp_imports_common import (
    st, threading, time, json, logging, uuid, Path, Dict, List, Any,
    Optional, setup_logger
)

logger = setup_logger(__name__)
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from functools import wraps
import os
from app.services.secure_config import get_api_key

logger = logging.getLogger(__name__)

# Persistent storage for task state
TASK_STATE_FILE = Path(__file__).parent / ".background_tasks_state.json"

# Import streamlit for caching
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False


class TaskState(Enum):
    """Task execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class BackgroundTask:
    """Represents a background task."""
    id: str
    name: str
    description: str
    state: TaskState = TaskState.PENDING
    progress: float = 0.0
    current_step: str = ""
    total_steps: int = 0
    completed_steps: int = 0
    result: Optional[Dict] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    artifacts: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "state": self.state.value if isinstance(self.state, TaskState) else self.state,
            "progress": self.progress,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "logs": self.logs[-50:],  # Keep last 50 logs
            "artifacts": self.artifacts,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'BackgroundTask':
        state = data.get("state", "pending")
        if isinstance(state, str):
            state = TaskState(state)
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            state=state,
            progress=data.get("progress", 0.0),
            current_step=data.get("current_step", ""),
            total_steps=data.get("total_steps", 0),
            completed_steps=data.get("completed_steps", 0),
            result=data.get("result"),
            error=data.get("error"),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            logs=data.get("logs", []),
            artifacts=data.get("artifacts", []),
            metadata=data.get("metadata", {})
        )


def retry_with_backoff(max_retries: int = 5, base_delay: float = 2.0, max_delay: float = 60.0):
    """
    Decorator for retrying API calls with exponential backoff.
    Handles rate limiting and temporary failures.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_str = str(e).lower()
                    
                    # Check if it's a retryable error
                    retryable = any(keyword in error_str for keyword in [
                        'rate limit', 'too many requests', '429', '503', '502',
                        'timeout', 'connection', 'temporary', 'overloaded',
                        'capacity', 'busy', 'retry'
                    ])
                    
                    if not retryable and attempt > 0:
                        # Not a retryable error, fail immediately
                        raise
                    
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        logger.warning(f"⚠️ Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {delay:.1f}s...")
                        time.sleep(delay)
                    else:
                        logger.error(f"❌ All {max_retries} attempts failed: {e}")
            raise last_exception
        return wrapper
    return decorator


class BackgroundTaskManager:
    """
    Singleton manager for background tasks.
    Persists state to disk and manages thread execution.
    Uses Streamlit cache_resource to survive page reloads.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._tasks: Dict[str, BackgroundTask] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._stop_flags: Dict[str, threading.Event] = {}
        self._state_lock = threading.Lock()
        
        # Load persisted state
        self._load_state()
        logger.info("✅ BackgroundTaskManager initialized")
    
    def _load_state(self):
        """Load task state from disk."""
        try:
            if TASK_STATE_FILE.exists():
                with open(TASK_STATE_FILE, 'r') as f:
                    data = json.load(f)
                for task_data in data.get("tasks", []):
                    task = BackgroundTask.from_dict(task_data)
                    # Mark running tasks as failed (they were interrupted)
                    if task.state == TaskState.RUNNING:
                        task.state = TaskState.FAILED
                        task.error = "Task was interrupted (app restart)"
                    self._tasks[task.id] = task
                logger.info(f"📂 Loaded {len(self._tasks)} tasks from disk")
        except Exception as e:
            logger.warning(f"Could not load task state: {e}")

        # After loading, attempt to recover interrupted tasks
        try:
            self._recover_interrupted_tasks()
        except Exception as e:
            logger.warning(f"Could not auto-recover interrupted tasks: {e}")
        
        # Clean up stuck tasks
        try:
            self.cleanup_stuck_tasks(timeout_minutes=5)
        except Exception as e:
            logger.warning(f"Could not cleanup stuck tasks: {e}")
    
    def _save_state(self):
        """Save task state to disk."""
        try:
            with self._state_lock:
                data = {
                    "tasks": [task.to_dict() for task in self._tasks.values()],
                    "updated_at": datetime.now().isoformat()
                }
                with open(TASK_STATE_FILE, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Could not save task state: {e}")
    
    def create_task(self, name: str, description: str = "", metadata: Dict = None) -> BackgroundTask:
        """Create a new background task."""
        task_id = str(uuid.uuid4())[:8]
        task = BackgroundTask(
            id=task_id,
            name=name,
            description=description,
            metadata=metadata or {}
        )
        with self._state_lock:
            self._tasks[task_id] = task
            self._stop_flags[task_id] = threading.Event()
        self._save_state()
        logger.info(f"📋 Created task: {task_id} - {name}")
        return task
    
    def start_task(self, task_id: str, target: Callable, *args, **kwargs):
        """Start a task in a background thread."""
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        # Store metadata about target and kwargs so task can be resumed after restart
        try:
            task.metadata = task.metadata or {}
            task.metadata['background_target'] = getattr(target, '__name__', str(target))
            task.metadata['background_module'] = getattr(target, '__module__', '')
            # Only store JSON-serializable kwargs
            try:
                task.metadata['background_kwargs'] = json.loads(json.dumps(kwargs))
            except Exception:
                # Fallback: store representative string
                task.metadata['background_kwargs'] = {k: str(v) for k, v in kwargs.items()}
            # Initialize recovery attempt counters if not present
            task.metadata.setdefault('recovery_attempts', task.metadata.get('recovery_attempts', 0))
            task.metadata.setdefault('max_recovery_attempts', task.metadata.get('max_recovery_attempts', 1))
            self._save_state()
        except Exception as e:
            logger.warning(f"Could not save task metadata for {task_id}: {e}")
        
        def task_wrapper():
            try:
                # Clear previous error when retrying / starting
                task.error = None
                task.state = TaskState.RUNNING
                task.started_at = datetime.now().isoformat()
                self._save_state()
                
                # Pass task and stop flag to the target function
                result = target(
                    task=task,
                    stop_flag=self._stop_flags[task_id],
                    update_callback=lambda: self._save_state(),
                    *args,
                    **kwargs
                )
                
                task.result = result
                task.error = None
                task.state = TaskState.COMPLETED
                task.completed_at = datetime.now().isoformat()
                task.progress = 1.0
                self._save_state()
                logger.info(f"✅ Task {task_id} completed successfully")
                
            except Exception as e:
                task.state = TaskState.FAILED
                task.error = str(e)
                task.completed_at = datetime.now().isoformat()
                task.logs.append(f"ERROR: {e}")
                task.logs.append(traceback.format_exc())
                self._save_state()
                logger.error(f"❌ Task {task_id} failed: {e}")
        
        # Use non-daemon thread so it persists across Streamlit page changes
        thread = threading.Thread(target=task_wrapper, daemon=False)
        self._threads[task_id] = thread
        thread.start()
        logger.info(f"🚀 Started task {task_id} in background thread (non-daemon)")


    def _resolve_target(self, module_name: str, target_name: str) -> Optional[Callable]:
        """Resolve a callable by module and name. Returns None if not found."""
        try:
            import importlib
            if not module_name:
                module_name = __name__
            module = importlib.import_module(module_name)
            return getattr(module, target_name)
        except Exception as e:
            logger.warning(f"Could not resolve target {target_name} from {module_name}: {e}")
            return None

    def _recover_interrupted_tasks(self):
        """Scan for tasks that were interrupted by a restart and try to resume them.

        This reads metadata saved with the task (background_target/module/kwargs)
        and attempts to restart the same function. Respects `max_recovery_attempts`.
        """
        for task in list(self._tasks.values()):
            if task.state == TaskState.FAILED and task.error and 'interrupted' in str(task.error).lower():
                meta = task.metadata or {}
                bg_target = meta.get('background_target')
                bg_module = meta.get('background_module', __name__)
                attempts = int(meta.get('recovery_attempts', 0))
                max_attempts = int(meta.get('max_recovery_attempts', 1))

                if not bg_target:
                    logger.info(f"Skipping recovery for {task.id}: no background_target metadata")
                    continue

                if attempts >= max_attempts:
                    logger.info(f"Max recovery attempts reached for {task.id} ({attempts}/{max_attempts})")
                    continue

                # Resolve function
                func = self._resolve_target(bg_module, bg_target)
                if not func:
                    logger.info(f"Skipping recovery for {task.id}: could not resolve function {bg_target}")
                    continue

                # Increase attempt counter and persist
                task.metadata['recovery_attempts'] = attempts + 1
                self._save_state()

                logger.info(f"🔁 Attempting to recover interrupted task {task.id} (attempt {attempts+1}/{max_attempts})")
                try:
                    kwargs = meta.get('background_kwargs', {}) or {}
                    # Start the task again in background
                    self.start_task(task.id, func, **kwargs)
                except Exception as e:
                    logger.error(f"Failed to restart interrupted task {task.id}: {e}")
    
    def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """Get a task by ID."""
        return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[BackgroundTask]:
        """Get all tasks."""
        return list(self._tasks.values())
    
    def get_running_tasks(self) -> List[BackgroundTask]:
        """Get all currently running tasks."""
        running = [t for t in self._tasks.values() if t.state == TaskState.RUNNING]
        
        # Check if threads are actually alive
        for task in running:
            thread = self._threads.get(task.id)
            if thread:
                is_alive = thread.is_alive()
                if not is_alive:
                    logger.warning(f"⚠️ Task {task.id} marked as running but thread is DEAD")
                    task.state = TaskState.FAILED
                    task.error = "Thread died unexpectedly"
                    self._save_state()
        
        return [t for t in self._tasks.values() if t.state == TaskState.RUNNING]
    
    def cleanup_stuck_tasks(self, timeout_minutes: int = 10):
        """Clean up tasks that are stuck with no progress."""
        from datetime import datetime, timedelta
        cleaned = 0
        for task in list(self._tasks.values()):
            if task.state in [TaskState.RUNNING, TaskState.PENDING]:
                if task.started_at:
                    try:
                        started = datetime.fromisoformat(task.started_at)
                        if task.progress == 0 and (datetime.now() - started) > timedelta(minutes=timeout_minutes):
                            task.state = TaskState.FAILED
                            task.error = f"Task timeout - no progress after {timeout_minutes} minutes"
                            task.completed_at = datetime.now().isoformat()
                            cleaned += 1
                            logger.warning(f"Cleaned up stuck task {task.id}")
                    except:
                        pass
        if cleaned > 0:
            self._save_state()
            logger.info(f"🧹 Cleaned up {cleaned} stuck tasks")
        return cleaned
    
    def stop_task(self, task_id: str):
        """Request a task to stop."""
        if task_id in self._stop_flags:
            self._stop_flags[task_id].set()
            task = self._tasks.get(task_id)
            if task:
                task.state = TaskState.CANCELLED
                task.logs.append("Task cancelled by user")
                self._save_state()
            logger.info(f"🛑 Requested stop for task {task_id}")

        def manual_retry_task(self, task_id: str, override_kwargs: Dict = None, reset_attempts: bool = False,
                              max_attempts: Optional[int] = None):
            """Manually retry/resume a failed task using stored metadata.

            Parameters:
                task_id: ID of the failed task
                override_kwargs: Optional dict to override saved background kwargs
                reset_attempts: If True, reset `recovery_attempts` to 0 before retry
                max_attempts: Optionally set a new `max_recovery_attempts` value
            """
            task = self._tasks.get(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            if task.state not in (TaskState.FAILED, TaskState.CANCELLED):
                raise ValueError("Can only retry tasks that are FAILED or CANCELLED")

            meta = task.metadata or {}
            bg_target = meta.get('background_target')
            bg_module = meta.get('background_module', __name__)

            if not bg_target:
                raise ValueError("Task has no background_target metadata to retry")

            if reset_attempts:
                meta['recovery_attempts'] = 0

            if max_attempts is not None:
                meta['max_recovery_attempts'] = int(max_attempts)

            # Update kwargs
            if override_kwargs is not None:
                try:
                    # Try to ensure serialization
                    meta['background_kwargs'] = json.loads(json.dumps(override_kwargs))
                except Exception:
                    meta['background_kwargs'] = {k: str(v) for k, v in override_kwargs.items()}

            # Persist metadata changes
            task.metadata = meta
            self._save_state()

            func = self._resolve_target(bg_module, bg_target)
            if not func:
                raise RuntimeError(f"Could not resolve function {bg_target} in {bg_module}")

            # Start the task again
            self.start_task(task.id, func, **(meta.get('background_kwargs', {}) or {}))

    
    def update_task_progress(self, task_id: str, progress: float, current_step: str = "", 
                             completed_steps: int = None, total_steps: int = None):
        """Update task progress."""
        task = self._tasks.get(task_id)
        if task:
            task.progress = min(1.0, max(0.0, progress))
            if current_step:
                task.current_step = current_step
            if completed_steps is not None:
                task.completed_steps = completed_steps
            if total_steps is not None:
                task.total_steps = total_steps
            self._save_state()
    
    def add_task_log(self, task_id: str, message: str):
        """Add a log message to a task."""
        task = self._tasks.get(task_id)
        if task:
            timestamp = datetime.now().strftime("%H:%M:%S")
            task.logs.append(f"[{timestamp}] {message}")
            # Keep only last 100 logs
            if len(task.logs) > 100:
                task.logs = task.logs[-100:]
            self._save_state()
    
    def add_task_artifact(self, task_id: str, artifact: Dict):
        """Add an artifact to a task."""
        task = self._tasks.get(task_id)
        if task:
            task.artifacts.append(artifact)
            self._save_state()
    
    def clear_completed_tasks(self):
        """Remove completed and failed tasks."""
        with self._state_lock:
            to_remove = [
                tid for tid, task in self._tasks.items()
                if task.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]
            ]
            for tid in to_remove:
                del self._tasks[tid]
                self._stop_flags.pop(tid, None)
                self._threads.pop(tid, None)
            self._save_state()
            logger.info(f"🧹 Cleared {len(to_remove)} completed tasks")


def get_task_manager() -> BackgroundTaskManager:
    """Get the singleton task manager instance.
    Uses Streamlit cache_resource to persist across page reloads."""
    if HAS_STREAMLIT:
        try:
            return _get_cached_task_manager()
        except:
            pass
    return BackgroundTaskManager()

if HAS_STREAMLIT:
    @st.cache_resource
    def _get_cached_task_manager() -> BackgroundTaskManager:
        """Cached task manager that persists across Streamlit reruns."""
        logger.info("🔄 Creating NEW cached BackgroundTaskManager instance")
        return BackgroundTaskManager()
else:
    def _get_cached_task_manager() -> BackgroundTaskManager:
        return BackgroundTaskManager()


def render_task_status_widget():
    """Render a compact task status widget for the sidebar."""
    manager = get_task_manager()
    running = manager.get_running_tasks()
    
    if running:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔄 Active Tasks")
        
        for task in running[:3]:  # Show max 3
            with st.sidebar.container():
                st.markdown(f"**{task.name}**")
                st.progress(task.progress, text=task.current_step or "Working...")
                if task.completed_steps and task.total_steps:
                    st.caption(f"Step {task.completed_steps}/{task.total_steps}")
        
        if len(running) > 3:
            st.sidebar.caption(f"+ {len(running) - 3} more tasks running...")

    # NOTE: Recent failures are shown in the main status area (Dashboard) to keep sidebar compact.


def render_task_monitor_page():
    """Render a full task monitoring page."""
    st.header("📊 Background Task Monitor")
    
    manager = get_task_manager()
    tasks = manager.get_all_tasks()
    
    # Controls
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🔄 Refresh"):
            st.rerun()
    with col2:
        if st.button("🧹 Clear Completed"):
            manager.clear_completed_tasks()
            st.rerun()
    with col3:
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh (5s)", value=False)
        if auto_refresh:
            time.sleep(5)
            st.rerun()
    
    if not tasks:
        st.info("No background tasks. Start a campaign or generation to see tasks here.")
        return
    
    # Running tasks
    running = [t for t in tasks if t.state == TaskState.RUNNING]
    if running:
        st.subheader(f"🔄 Running ({len(running)})")
        for task in running:
            with st.expander(f"**{task.name}** - {task.progress*100:.0f}%", expanded=True):
                st.progress(task.progress)
                st.caption(task.current_step or "Processing...")
                
                if task.completed_steps and task.total_steps:
                    st.write(f"Step {task.completed_steps}/{task.total_steps}")
                
                # Logs
                if task.logs:
                    st.markdown("**Recent Logs:**")
                    log_text = "\n".join(task.logs[-10:])
                    st.code(log_text, language=None)
                
                # Stop button
                if st.button(f"🛑 Stop", key=f"stop_{task.id}"):
                    manager.stop_task(task.id)
                    st.rerun()
    
    # Completed tasks
    completed = [t for t in tasks if t.state == TaskState.COMPLETED]
    if completed:
        st.subheader(f"✅ Completed ({len(completed)})")
        for task in completed[-5:]:  # Last 5
            with st.expander(f"**{task.name}** - {task.completed_at or 'Unknown'}"):
                st.success("Task completed successfully!")
                if task.artifacts:
                    st.markdown("**Artifacts:**")
                    for artifact in task.artifacts:
                        st.write(f"- {artifact.get('name', 'Unknown')}: {artifact.get('type', 'file')}")
    
    # Failed tasks
    failed = [t for t in tasks if t.state == TaskState.FAILED]
    if failed:
        st.subheader(f"❌ Failed ({len(failed)})")
        for task in failed[-3:]:  # Last 3
            with st.expander(f"**{task.name}** - FAILED"):
                st.error(task.error or "Unknown error")
                if task.logs:
                    st.markdown("**Error Logs:**")
                    st.code("\n".join(task.logs[-20:]), language=None)

                # Retry / Resume UI
                with st.expander("🔁 Retry / Resume", expanded=False):
                    st.markdown("You can retry this task. Optionally edit the background kwargs and reset attempts.")
                    try:
                        existing_kwargs = task.metadata.get('background_kwargs', {}) if task.metadata else {}
                        kwargs_text = st.text_area(f"Override kwargs (JSON)", value=json.dumps(existing_kwargs, indent=2), height=120, key=f"kwargs_{task.id}")
                    except Exception:
                        kwargs_text = st.text_area(f"Override kwargs (JSON)", value="{}", height=120, key=f"kwargs_{task.id}")

                    reset_attempts = st.checkbox("Reset recovery attempts", value=False, key=f"reset_{task.id}")
                    max_attempts = st.number_input("Max recovery attempts", min_value=1, max_value=10, value=int(task.metadata.get('max_recovery_attempts', 1) if task.metadata else 1), key=f"max_{task.id}")

                    if st.button("🔁 Retry Task", key=f"retry_{task.id}"):
                        try:
                            parsed_kwargs = {}
                            try:
                                parsed_kwargs = json.loads(kwargs_text or "{}")
                            except Exception as e:
                                st.error(f"Invalid JSON for kwargs: {e}")
                                st.rerun()

                            manager.manual_retry_task(task.id, override_kwargs=parsed_kwargs, reset_attempts=reset_attempts, max_attempts=int(max_attempts))
                            st.success("Retry initiated — task restarted in background.")
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"Could not retry task: {e}")


# === CAMPAIGN GENERATION WITH BACKGROUND TASKS ===

def run_campaign_in_background(
    task: BackgroundTask,
    stop_flag: threading.Event,
    update_callback: Callable,
    campaign_config: Dict
):
    """
    Run campaign generation as a background task.
    This is called by the BackgroundTaskManager in a separate thread.
    
    Unlike the Streamlit version, this runs headlessly without UI updates.
    Progress is tracked via the task object and logs.
    """
    import os
    from pathlib import Path
    
    manager = get_task_manager()
    
    def log(msg: str):
        manager.add_task_log(task.id, msg)
        logger.info(f"[Task {task.id}] {msg}")
        update_callback()
    
    def progress(value: float, step: str = "", completed: int = None, total: int = None):
        manager.update_task_progress(task.id, value, step, completed, total)
        update_callback()
    
    def check_cancelled():
        if stop_flag.is_set():
            log("Task cancelled by user")
            raise Exception("Task cancelled")
    
    log("🚀 Starting background campaign generation...")
    progress(0.02, "Initializing...", 0, 10)
    
    try:
        # Extract config
        concept_input = campaign_config.get('concept_input', '')
        target_audience = campaign_config.get('target_audience', '')
        price_range = campaign_config.get('price_range', '$20-$40')
        campaign_enabled = campaign_config.get('campaign_enabled', True)
        product_enabled = campaign_config.get('product_enabled', True)
        blog_enabled = campaign_config.get('blog_enabled', False)
        video_enabled = campaign_config.get('video_enabled', False)
        social_enabled = campaign_config.get('social_enabled', False)
        num_products = campaign_config.get('num_products', 1)
        fast_mode = campaign_config.get('fast_mode', True)
        
        log(f"📋 Concept: {concept_input[:80]}...")
        log(f"🎯 Target: {target_audience}")
        log(f"💰 Price: {price_range}")
        
        check_cancelled()
        
        # Get Replicate API token - try multiple fallbacks so background threads work
        replicate_token = get_api_key('REPLICATE_API_TOKEN')

        # Fallback 1: Try Streamlit session_state (when running inside streamlit)
        try:
            import streamlit as _st
            if not replicate_token:
                api_keys = getattr(_st.session_state, 'api_keys', None)
                if api_keys and isinstance(api_keys, dict):
                    replicate_token = api_keys.get('replicate') or replicate_token
        except Exception:
            # Not running inside Streamlit or session_state missing
            pass

        # Fallback 2: Load from .env file if available (use python-dotenv)
        if not replicate_token:
            try:
                from dotenv import load_dotenv
                env_path = Path(__file__).parent / '.env'
                if env_path.exists():
                    load_dotenv(env_path)
                    replicate_token = get_api_key('REPLICATE_API_TOKEN') or replicate_token
                    if replicate_token:
                        log("✅ Loaded REPLICATE_API_TOKEN from .env file")
            except Exception as e:
                log(f"⚠️ Could not load .env for Replicate token: {e}")

        if not replicate_token:
            raise Exception("REPLICATE_API_TOKEN not found in environment")
        
        from app.services.api_service import ReplicateAPI
        replicate_api = ReplicateAPI(replicate_token)
        log("✅ Replicate API connected")
        
        progress(0.05, "Creating campaign directory...", 1, 10)
        check_cancelled()
        
        # Create campaign directory
        from app.services.platform_helpers import create_campaign_directory, _slugify
        campaign_dir = create_campaign_directory(concept_input)
        log(f"📁 Campaign directory: {campaign_dir}")
        
        results = {
            'campaign_plan': None,
            'products': [],
            'blog_posts': [],
            'videos': [],
            'social_posts': [],
            'campaign_dir': str(campaign_dir),
        }

        # If previous steps already produced products (e.g., resuming a campaign or running video-only stage),
        # try to load products.json or similar artifacts from the campaign directory so we can pick up where
        # the pipeline left off. This helps tests and resume scenarios where product generation was already done.
        try:
            for candidate in ('products.json', 'campaign_products.json', 'results.json', 'campaign_results.json'):
                candidate_path = campaign_dir / candidate
                if candidate_path.exists():
                    try:
                        with open(candidate_path, 'r') as f:
                            loaded = json.load(f)
                        # loaded may be a dict containing 'products' or a list of products
                        if isinstance(loaded, dict) and 'products' in loaded:
                            results['products'] = loaded.get('products') or []
                        elif isinstance(loaded, list):
                            results['products'] = loaded
                        else:
                            # unknown shape, ignore
                            pass
                        log(f"✅ Loaded {len(results['products'])} existing products from {candidate}")
                        break
                    except Exception as e:
                        log(f"⚠️ Could not load existing products from {candidate}: {e}")
        except Exception:
            # Best effort only
            pass
        
        # Step 1: Generate Campaign Plan
        if campaign_enabled:
            progress(0.1, "Generating campaign plan...", 2, 10)
            check_cancelled()
            
            try:
                from .campaign_generator_service import EnhancedCampaignGenerator
                generator = EnhancedCampaignGenerator(replicate_api)
                
                # Generate campaign concept and plan
                concept, analyzed_concept = generator.generate_campaign_concept(
                    product_description=concept_input,
                    target_audience=target_audience,
                    budget="500",  # Default budget
                    platforms=["Instagram", "TikTok", "Pinterest"]
                )
                results['campaign_plan'] = {
                    'concept': concept,
                    'analyzed_concept': analyzed_concept
                }
                log(f"✅ Campaign concept generated: {len(concept)} chars")
                
                # Save concept
                concept_path = campaign_dir / "campaign_concept.txt"
                with open(concept_path, 'w') as f:
                    f.write(concept)
                log(f"   📄 Saved: campaign_concept.txt")
                
                analyzed_path = campaign_dir / "analyzed_concept.txt"
                with open(analyzed_path, 'w') as f:
                    f.write(analyzed_concept)
                log(f"   📄 Saved: analyzed_concept.txt")
                    
            except Exception as e:
                log(f"⚠️ Campaign plan error: {e}")
        
        # Step 2: Generate Products
        if product_enabled:
            progress(0.25, f"Generating {num_products} products...", 3, 10)
            check_cancelled()
            
            for i in range(num_products):
                check_cancelled()
                progress(0.25 + (i * 0.15 / num_products), f"Generating product {i+1}/{num_products}...", 3, 10)
                
                try:
                    # Generate product image
                    product_prompt = f"{concept_input}, high quality product design, professional"
                    log(f"🎨 Generating product {i+1}: {product_prompt[:50]}...")
                    
                    image_output = replicate_api.generate_image(
                        prompt=product_prompt,
                        width=1024,
                        height=1024
                    )
                    
                    if image_output:
                        # Download and save image
                        import requests
                        image_url = image_output[0] if isinstance(image_output, list) else image_output
                        
                        products_dir = campaign_dir / "products"
                        products_dir.mkdir(exist_ok=True)
                        
                        image_path = products_dir / f"product_{i+1}.png"
                        response = requests.get(image_url, timeout=60)
                        if response.status_code == 200:
                            with open(image_path, 'wb') as f:
                                f.write(response.content)
                            
                            results['products'].append({
                                'title': f"{concept_input} - Design {i+1}",
                                'image_file': str(image_path),
                                'image_url': image_url
                            })
                            log(f"   ✅ Product {i+1} saved: {image_path.name}")
                            
                            # Add as artifact
                            manager.add_task_artifact(task.id, {
                                'name': f'Product {i+1}',
                                'type': 'image',
                                'path': str(image_path)
                            })
                        else:
                            log(f"   ⚠️ Failed to download product {i+1} image")
                    else:
                        log(f"   ⚠️ No image generated for product {i+1}")
                        
                except Exception as e:
                    log(f"   ❌ Product {i+1} error: {e}")

        # Step 2.5: Generate Videos for products (if enabled)
        if video_enabled:
            progress(0.55, "Generating product videos...", 4, 10)
            check_cancelled()

            try:
                from concurrent.futures import ThreadPoolExecutor, as_completed
                from static_commercial_producer import StaticCommercialProducer

                video_dir = campaign_dir / "videos"
                video_dir.mkdir(exist_ok=True)

                # Use a small threadpool to render videos concurrently but not overload local resources
                with ThreadPoolExecutor(max_workers=2) as ex:
                    futures = []
                    for pidx, prod in enumerate(results['products']):
                        check_cancelled()
                        mockups = prod.get('lifestyle_mockups') or prod.get('all_mockups') or []
                        # If a dedicated product mockup for video was set earlier, prefer it
                        if prod.get('video_mockup'):
                            mockups = [prod.get('video_mockup')] + mockups

                        out_path = video_dir / f"product_{pidx+1}_commercial.mp4"

                        # Prepare args for submission
                        producer = StaticCommercialProducer(replicate_token)

                        product_features = prod.get('features') or prod.get('attributes') or []
                        brand_template = campaign_config.get('brand_template') if isinstance(campaign_config, dict) else None

                        def render_job(prod_idx=pidx, mockups=mockups, out=str(out_path), features=product_features, brand=brand_template):
                            try:
                                # Enforce fidelity: do not allow substitute visuals in autonomous mode
                                result = producer.create_product_commercial(
                                    campaign_concept=concept_input,
                                    product_name=prod.get('title', concept_input),
                                    mockup_image_paths=mockups[:3],
                                    output_path=out,
                                    product_features=features,
                                    allow_substitute_visuals=False,
                                    template=campaign_config.get('video_template', '3_scene_basic') if isinstance(campaign_config, dict) else '3_scene_basic',
                                    brand_template=brand,
                                    max_retries=2
                                )
                                return (True, out)
                            except Exception as e:
                                return (False, str(e))

                        futures.append(ex.submit(render_job))

                    for f in as_completed(futures):
                        ok, res = f.result()
                        if ok:
                            manager.add_task_artifact(task.id, {
                                'name': os.path.basename(res),
                                'type': 'video',
                                'path': res
                            })
                            log(f"   ✅ Video generated: {res}")
                        else:
                            log(f"   ❌ Video generation failed: {res}")

            except Exception as e:
                log(f"⚠️ Video generation stage error: {e}")
        
        # Step 3: Generate Blog Post
        if blog_enabled:
            progress(0.5, "Generating blog post...", 5, 10)
            check_cancelled()
            
            try:
                from .blog_generator import generate_product_blog
                
                # Create blogs directory
                blogs_dir = campaign_dir / "blogs"
                blogs_dir.mkdir(exist_ok=True)
                
                # generate_product_blog returns (html_path, pdf_path)
                html_path, pdf_path = generate_product_blog(
                    product_name=concept_input,
                    product_description=f"A unique {concept_input} designed for {target_audience}. High-quality print-on-demand product.",
                    tone="Professional",
                    output_dir=str(blogs_dir)
                )
                
                if html_path:
                    results['blog_posts'].append({
                        'html_path': html_path,
                        'pdf_path': pdf_path
                    })
                    log(f"✅ Blog post generated: {html_path}")
                    
                    # Add as artifact
                    manager.add_task_artifact(task.id, {
                        'name': 'Blog Post',
                        'type': 'html',
                        'path': html_path
                    })
                    
            except Exception as e:
                log(f"⚠️ Blog generation error: {e}")
        
        # Step 4: Generate Social Media Content
        if social_enabled:
            progress(0.7, "Generating social media content...", 7, 10)
            check_cancelled()
            
            try:
                social_dir = campaign_dir / "social_media"
                social_dir.mkdir(exist_ok=True)
                
                # Generate social post text
                social_prompt = f"Write 3 social media posts promoting: {concept_input}. Target audience: {target_audience}. Include hashtags."
                social_text = replicate_api.generate_text(prompt=social_prompt, max_tokens=500)
                
                if social_text:
                    social_path = social_dir / "social_posts.txt"
                    with open(social_path, 'w') as f:
                        f.write(social_text)
                    results['social_posts'].append({
                        'content': social_text,
                        'path': str(social_path)
                    })
                    log(f"✅ Social media content generated")
                    
            except Exception as e:
                log(f"⚠️ Social media error: {e}")
        
        # Step 5: Finalize
        progress(0.9, "Finalizing campaign...", 9, 10)
        check_cancelled()
        
        # Save campaign summary
        summary = {
            'concept': concept_input,
            'target_audience': target_audience,
            'price_range': price_range,
            'products_generated': len(results['products']),
            'blog_generated': len(results['blog_posts']) > 0,
            'social_generated': len(results['social_posts']) > 0,
            'campaign_dir': str(campaign_dir),
            'completed_at': datetime.now().isoformat()
        }
        
        summary_path = campaign_dir / "campaign_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        log(f"📊 Campaign Summary:")
        log(f"   Products: {summary['products_generated']}")
        log(f"   Blog: {'Yes' if summary['blog_generated'] else 'No'}")
        log(f"   Social: {'Yes' if summary['social_generated'] else 'No'}")
        
        progress(1.0, "Campaign complete!", 10, 10)
        log(f"🎉 Campaign generation complete!")
        log(f"📁 Files saved to: {campaign_dir}")
        
        return {
            "status": "success",
            "message": "Campaign generated successfully",
            "campaign_dir": str(campaign_dir),
            "results": summary
        }
        
    except Exception as e:
        log(f"❌ Error: {e}")
        import traceback
        log(traceback.format_exc())
        raise


def _dummy_recovery_task(**kwargs):
    """A tiny no-op task used in tests and to verify recovery logic."""
    import time
    logger.info(f"Running dummy recovery task with kwargs={kwargs}")
    time.sleep(0.2)
    return {"recovered": True, "kwargs": kwargs}


def start_background_campaign(campaign_config: Dict) -> str:
    """
    Start a campaign generation task in the background.
    Returns the task ID for tracking.
    
    Usage:
        task_id = start_background_campaign({
            'concept_input': 'Cosmic Cat Artwork',
            'target_audience': 'Cat lovers',
            'num_products': 3,
            ...
        })
        
        # Later, check status:
        task = get_task_manager().get_task(task_id)
        print(f"Progress: {task.progress * 100}%")
    """
    manager = get_task_manager()
    
    concept = campaign_config.get('concept_input', 'Campaign')[:50]
    task = manager.create_task(
        name=f"Campaign: {concept}",
        description=f"Generating campaign for: {concept}",
        metadata=campaign_config
    )
    
    manager.start_task(
        task.id,
        run_campaign_in_background,
        campaign_config=campaign_config
    )
    
    logger.info(f"🚀 Started background campaign task: {task.id}")
    return task.id
