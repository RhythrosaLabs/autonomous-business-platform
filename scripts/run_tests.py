#!/usr/bin/env python3
"""
Test Runner Script

Run all tests with various options.
"""

import sys
import subprocess
from pathlib import Path


def run_tests(args=None):
    """
    Run pytest with given arguments.

    Args:
        args: List of additional pytest arguments
    """
    cmd = ["pytest"]

    if args:
        cmd.extend(args)
    else:
        # Default: run all tests with coverage
        cmd.extend(
            [
                "-v",  # Verbose
                "--tb=short",  # Short traceback
                "--cov=app",  # Coverage for app directory
                "--cov-report=html",  # HTML coverage report
                "--cov-report=term",  # Terminal coverage report
            ]
        )

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run tests")
    parser.add_argument("pytest_args", nargs="*", help="Additional pytest arguments")
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("--fast", action="store_true", help="Run fast tests only (skip slow tests)")

    args = parser.parse_args()

    pytest_args = list(args.pytest_args)

    if args.unit:
        pytest_args.append("tests/unit")
    elif args.integration:
        pytest_args.append("tests/integration")

    if args.fast:
        pytest_args.extend(["-m", "not slow"])

    sys.exit(run_tests(pytest_args))


if __name__ == "__main__":
    main()
