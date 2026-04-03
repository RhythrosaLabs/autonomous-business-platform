"""
Error Handling Module

Provides standardized error handling, custom exceptions,
and error reporting functionality across the application.
"""

import logging
import traceback
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, Type, Union

import streamlit as st

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AppError(Exception):
    """Base application error class"""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        user_message: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message)
        self.message = message
        self.severity = severity
        self.user_message = user_message or message
        self.details = details or {}


class ConfigurationError(AppError):
    """Configuration-related errors"""

    pass


class APIError(AppError):
    """API-related errors"""

    pass


class ValidationError(AppError):
    """Data validation errors"""

    pass


class ServiceError(AppError):
    """Service-level errors"""

    pass


def handle_errors(
    *,
    show_user: bool = True,
    log_error: bool = True,
    reraise: bool = False,
    default_return: Any = None,
    error_types: tuple = (Exception,),
) -> Callable:
    """
    Decorator for standardized error handling.

    Args:
        show_user: Whether to show error to user in UI
        log_error: Whether to log the error
        reraise: Whether to re-raise the exception
        default_return: Value to return on error
        error_types: Tuple of exception types to catch

    Returns:
        Decorated function with error handling

    Example:
        @handle_errors(show_user=True, log_error=True)
        def my_function():
            # code that might raise errors
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except error_types as e:
                # Handle our custom errors
                if isinstance(e, AppError):
                    severity = e.severity
                    user_message = e.user_message
                    log_message = f"{func.__name__}: {e.message}"
                    details = e.details
                else:
                    severity = ErrorSeverity.ERROR
                    user_message = f"An error occurred: {str(e)}"
                    log_message = f"{func.__name__}: {str(e)}"
                    details = {"traceback": traceback.format_exc()}

                # Log the error
                if log_error:
                    if severity == ErrorSeverity.CRITICAL:
                        logger.critical(log_message, extra=details)
                    elif severity == ErrorSeverity.ERROR:
                        logger.error(log_message, extra=details)
                    elif severity == ErrorSeverity.WARNING:
                        logger.warning(log_message)
                    else:
                        logger.info(log_message)

                # Show to user
                if show_user:
                    display_error(
                        user_message, severity, details if isinstance(e, AppError) else None
                    )

                # Re-raise if requested
                if reraise:
                    raise

                return default_return

        return wrapper

    return decorator


def display_error(
    message: str,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    details: Optional[dict] = None,
) -> None:
    """
    Display error to user in Streamlit UI.

    Args:
        message: Error message to display
        severity: Error severity level
        details: Optional additional details
    """
    if severity == ErrorSeverity.CRITICAL:
        st.error(f"🚨 Critical Error: {message}")
    elif severity == ErrorSeverity.ERROR:
        st.error(f"❌ Error: {message}")
    elif severity == ErrorSeverity.WARNING:
        st.warning(f"⚠️ Warning: {message}")
    else:
        st.info(f"ℹ️ {message}")

    # Show details in expander if provided
    if details:
        with st.expander("🔍 Technical Details"):
            st.json(details)


def safe_execute(
    func: Callable,
    *args,
    error_message: str = "Operation failed",
    default_return: Any = None,
    **kwargs,
) -> Any:
    """
    Safely execute a function with error handling.

    Args:
        func: Function to execute
        *args: Positional arguments for func
        error_message: Custom error message
        default_return: Value to return on error
        **kwargs: Keyword arguments for func

    Returns:
        Function result or default_return on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"{error_message}: {str(e)}")
        display_error(f"{error_message}: {str(e)}")
        return default_return


class ErrorContext:
    """
    Context manager for error handling.

    Example:
        with ErrorContext("Processing data"):
            # code that might raise errors
            process_data()
    """

    def __init__(
        self,
        operation: str,
        show_user: bool = True,
        log_error: bool = True,
        reraise: bool = False,
    ):
        self.operation = operation
        self.show_user = show_user
        self.log_error = log_error
        self.reraise = reraise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            if self.log_error:
                logger.error(f"Error in {self.operation}: {str(exc_val)}")

            if self.show_user:
                display_error(f"Error in {self.operation}: {str(exc_val)}")

            if self.reraise:
                return False  # Re-raise exception

            return True  # Suppress exception

        return True


def validate_input(
    value: Any,
    value_name: str,
    expected_type: Optional[Type] = None,
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    allowed_values: Optional[list] = None,
) -> None:
    """
    Validate input with common checks.

    Args:
        value: Value to validate
        value_name: Name of the value (for error messages)
        expected_type: Expected type
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        allowed_values: List of allowed values

    Raises:
        ValidationError: If validation fails
    """
    if expected_type is not None and not isinstance(value, expected_type):
        raise ValidationError(
            f"Invalid type for {value_name}",
            user_message=f"{value_name} must be of type {expected_type.__name__}",
            details={
                "received_type": type(value).__name__,
                "expected_type": expected_type.__name__,
            },
        )

    if min_value is not None and value < min_value:
        raise ValidationError(
            f"{value_name} below minimum",
            user_message=f"{value_name} must be at least {min_value}",
            details={"value": value, "min_value": min_value},
        )

    if max_value is not None and value > max_value:
        raise ValidationError(
            f"{value_name} above maximum",
            user_message=f"{value_name} must be at most {max_value}",
            details={"value": value, "max_value": max_value},
        )

    if allowed_values is not None and value not in allowed_values:
        raise ValidationError(
            f"Invalid value for {value_name}",
            user_message=f"{value_name} must be one of: {', '.join(map(str, allowed_values))}",
            details={"value": value, "allowed_values": allowed_values},
        )
