"""
Error recovery, retry logic, and graceful degradation utilities
Handles transient failures, implements exponential backoff, and provides fallback options
"""

import time
import logging
import functools
import streamlit as st
from typing import Callable, Any, Optional, List, Dict, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class OperationResult:
    """Result of an operation with partial success tracking"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    partial_results: List[Any] = field(default_factory=list)
    failed_items: List[Tuple[Any, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_partial_success(self) -> bool:
        """Check if operation partially succeeded"""
        return bool(self.partial_results) and bool(self.failed_items)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = len(self.partial_results) + len(self.failed_items)
        if total == 0:
            return 0.0
        return len(self.partial_results) / total
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        if self.success:
            return f"✅ Operation completed successfully"
        elif self.is_partial_success:
            return f"⚠️ Partial success: {len(self.partial_results)}/{len(self.partial_results) + len(self.failed_items)} items completed"
        else:
            return f"❌ Operation failed: {self.error}"


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: Tuple = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator for automatic retry with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Callback function called on each retry (retry_num, delay, error)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        if on_retry:
                            on_retry(attempt + 1, delay, e)
                        else:
                            logger.warning(
                                f"Retry {attempt + 1}/{max_retries} for {func.__name__} "
                                f"after {delay}s: {str(e)}"
                            )
                        
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            f"Max retries ({max_retries}) exceeded for {func.__name__}: {str(e)}"
                        )
            
            # All retries failed
            raise last_exception
        
        return wrapper
    return decorator


def safe_execute(
    func: Callable,
    *args,
    fallback_value: Any = None,
    fallback_func: Optional[Callable] = None,
    error_message: str = None,
    show_error: bool = True,
    **kwargs
) -> Tuple[Any, Optional[Exception]]:
    """
    Safely execute a function with error handling and fallback
    
    Args:
        func: Function to execute
        fallback_value: Value to return on error
        fallback_func: Alternative function to call on error
        error_message: Custom error message
        show_error: Whether to display error in Streamlit UI
    
    Returns:
        (result, exception) tuple
    """
    try:
        result = func(*args, **kwargs)
        return result, None
    except Exception as e:
        logger.exception(f"Error in {func.__name__}: {str(e)}")
        
        if show_error:
            msg = error_message or f"Error in {func.__name__}: {str(e)}"
            st.error(msg)
        
        # Try fallback function first
        if fallback_func:
            try:
                result = fallback_func(*args, **kwargs)
                if show_error:
                    st.info("✓ Using fallback method")
                return result, e
            except Exception as fallback_error:
                logger.exception(f"Fallback also failed: {str(fallback_error)}")
        
        return fallback_value, e


class PartialSuccessHandler:
    """Handles operations that can partially succeed"""
    
    def __init__(self, operation_name: str = "Operation"):
        self.operation_name = operation_name
        self.results = []
        self.failures = []
        self.start_time = datetime.now()
    
    def add_success(self, item: Any, result: Any = None):
        """Record successful item"""
        self.results.append((item, result))
    
    def add_failure(self, item: Any, error: str):
        """Record failed item"""
        self.failures.append((item, error))
    
    def get_result(self) -> OperationResult:
        """Get final operation result"""
        total = len(self.results) + len(self.failures)
        
        if total == 0:
            return OperationResult(
                success=False,
                error="No items processed"
            )
        
        success = len(self.failures) == 0
        
        return OperationResult(
            success=success,
            partial_results=self.results,
            failed_items=self.failures,
            metadata={
                'total_items': total,
                'successful': len(self.results),
                'failed': len(self.failures),
                'duration': (datetime.now() - self.start_time).total_seconds(),
                'operation': self.operation_name
            }
        )
    
    def display_summary(self):
        """Display summary in Streamlit"""
        result = self.get_result()
        
        if result.success:
            st.success(f"✅ {self.operation_name} completed: {len(self.results)} items")
        elif result.is_partial_success:
            st.warning(
                f"⚠️ {self.operation_name} partially completed:\n"
                f"• ✅ Succeeded: {len(self.results)}\n"
                f"• ❌ Failed: {len(self.failures)}"
            )
            
            with st.expander("🔍 View Failed Items"):
                for item, error in self.failures:
                    st.error(f"**{item}**: {error}")
        else:
            st.error(f"❌ {self.operation_name} failed: {result.error}")


def api_call_with_fallback(
    primary_func: Callable,
    fallback_funcs: List[Callable],
    func_names: List[str] = None,
    *args,
    **kwargs
) -> OperationResult:
    """
    Try primary API call, fall back to alternatives if it fails
    
    Args:
        primary_func: Primary function to try
        fallback_funcs: List of fallback functions to try in order
        func_names: Names of functions for logging
    
    Returns:
        OperationResult with success/failure info
    """
    if func_names is None:
        func_names = ["Primary"] + [f"Fallback {i+1}" for i in range(len(fallback_funcs))]
    
    # Try primary
    try:
        result = primary_func(*args, **kwargs)
        return OperationResult(
            success=True,
            data=result,
            metadata={'method': func_names[0]}
        )
    except Exception as e:
        logger.warning(f"{func_names[0]} failed: {str(e)}")
        last_error = str(e)
    
    # Try fallbacks
    for i, (fallback_func, name) in enumerate(zip(fallback_funcs, func_names[1:]), 1):
        try:
            result = fallback_func(*args, **kwargs)
            logger.info(f"Succeeded with {name}")
            return OperationResult(
                success=True,
                data=result,
                metadata={'method': name, 'fallback_level': i}
            )
        except Exception as e:
            logger.warning(f"{name} failed: {str(e)}")
            last_error = str(e)
    
    # All failed
    return OperationResult(
        success=False,
        error=f"All methods failed. Last error: {last_error}",
        metadata={'methods_tried': func_names}
    )


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures
    Opens circuit after too many failures, preventing further attempts
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        name: str = "Circuit"
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.name = name
        self.failures = 0
        self.last_failure_time = None
        self.is_open = False
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function through circuit breaker"""
        if self.is_open:
            # Check if timeout expired
            if time.time() - self.last_failure_time > self.timeout:
                logger.info(f"Circuit breaker {self.name} resetting after timeout")
                self.reset()
            else:
                raise Exception(f"Circuit breaker {self.name} is OPEN - too many failures")
        
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e
    
    def on_success(self):
        """Record successful call"""
        self.failures = 0
        self.is_open = False
    
    def on_failure(self):
        """Record failed call"""
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.failures >= self.failure_threshold:
            self.is_open = True
            logger.error(
                f"Circuit breaker {self.name} OPENED after {self.failures} failures"
            )
    
    def reset(self):
        """Manually reset circuit breaker"""
        self.failures = 0
        self.is_open = False
        self.last_failure_time = None


def batch_process_with_recovery(
    items: List[Any],
    process_func: Callable,
    operation_name: str = "Batch Operation",
    show_progress: bool = True,
    continue_on_error: bool = True
) -> OperationResult:
    """
    Process items in batch with error recovery
    
    Args:
        items: List of items to process
        process_func: Function to process each item
        operation_name: Name for progress display
        show_progress: Show progress bar
        continue_on_error: Continue processing if one item fails
    
    Returns:
        OperationResult with partial success tracking
    """
    handler = PartialSuccessHandler(operation_name)
    
    progress_bar = None
    if show_progress:
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    for i, item in enumerate(items):
        try:
            result = process_func(item)
            handler.add_success(item, result)
            
            if show_progress:
                progress = (i + 1) / len(items)
                progress_bar.progress(progress)
                status_text.text(f"Processing {i + 1}/{len(items)}: ✓ {item}")
        
        except Exception as e:
            error_msg = str(e)
            handler.add_failure(item, error_msg)
            logger.error(f"Failed to process {item}: {error_msg}")
            
            if show_progress:
                status_text.text(f"Processing {i + 1}/{len(items)}: ✗ {item}")
            
            if not continue_on_error:
                break
    
    if show_progress:
        progress_bar.empty()
        status_text.empty()
    
    return handler.get_result()
