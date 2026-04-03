"""
Unit Tests for Error Handling
"""

import pytest

from app.core.exceptions import (
    AppError,
    APIError,
    ValidationError,
    ConfigurationError,
    ErrorSeverity,
    handle_errors,
    validate_input,
    ErrorContext,
)


class TestCustomExceptions:
    """Test custom exception classes"""

    def test_app_error(self):
        """Test base AppError class."""
        error = AppError(
            "Test error", severity=ErrorSeverity.ERROR, user_message="User-friendly message"
        )

        assert error.message == "Test error"
        assert error.user_message == "User-friendly message"
        assert error.severity == ErrorSeverity.ERROR

    def test_validation_error(self):
        """Test ValidationError class."""
        error = ValidationError("Invalid input", details={"field": "email"})

        assert "Invalid input" in str(error)
        assert error.details["field"] == "email"


class TestHandleErrorsDecorator:
    """Test handle_errors decorator"""

    def test_successful_execution(self):
        """Test decorator with successful function."""

        @handle_errors(show_user=False, log_error=False)
        def success_func():
            return "success"

        result = success_func()
        assert result == "success"

    def test_error_handling(self):
        """Test decorator with error."""

        @handle_errors(show_user=False, log_error=False, default_return="default")
        def error_func():
            raise ValueError("Test error")

        result = error_func()
        assert result == "default"

    def test_reraise_option(self):
        """Test decorator with reraise option."""

        @handle_errors(show_user=False, log_error=False, reraise=True)
        def error_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            error_func()


class TestValidateInput:
    """Test input validation function"""

    def test_type_validation(self):
        """Test type validation."""
        validate_input("test", "name", expected_type=str)

        with pytest.raises(ValidationError):
            validate_input(123, "name", expected_type=str)

    def test_min_value_validation(self):
        """Test minimum value validation."""
        validate_input(10, "count", min_value=5)

        with pytest.raises(ValidationError):
            validate_input(3, "count", min_value=5)

    def test_max_value_validation(self):
        """Test maximum value validation."""
        validate_input(10, "count", max_value=20)

        with pytest.raises(ValidationError):
            validate_input(25, "count", max_value=20)

    def test_allowed_values_validation(self):
        """Test allowed values validation."""
        validate_input("red", "color", allowed_values=["red", "blue", "green"])

        with pytest.raises(ValidationError):
            validate_input("yellow", "color", allowed_values=["red", "blue", "green"])


class TestErrorContext:
    """Test ErrorContext context manager"""

    def test_successful_context(self):
        """Test context manager with no errors."""
        with ErrorContext("test operation", show_user=False):
            result = 1 + 1

        assert result == 2

    def test_error_suppression(self):
        """Test error suppression in context."""
        with ErrorContext("test operation", show_user=False, reraise=False):
            raise ValueError("Test error")

        # Should not raise - error is suppressed
