#!/usr/bin/env python3
"""Test runner script for KillTheNoise backend."""

import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"Running: {description}")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return False


def main():
    """Main test runner function."""
    print("🧪 Running KillTheNoise Backend Tests")
    print("=" * 50)

    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print(
            "❌ Error: pyproject.toml not found. Run this script from the project root."
        )
        sys.exit(1)

    # Run different types of tests
    test_commands = [
        (["python3", "-m", "pytest", "tests/", "-v"], "Unit and Integration Tests"),
        (
            ["python3", "-m", "pytest", "tests/test_api_endpoints.py", "-v"],
            "API Endpoint Tests",
        ),
        (
            ["python3", "-m", "pytest", "tests/test_services.py", "-v"],
            "Service Layer Tests",
        ),
        (
            ["python3", "-m", "pytest", "tests/test_models.py", "-v"],
            "Database Model Tests",
        ),
        (
            [
                "python3",
                "-m",
                "pytest",
                "tests/",
                "--cov=app",
                "--cov-report=term-missing",
            ],
            "Tests with Coverage",
        ),
    ]

    all_passed = True

    for command, description in test_commands:
        if not run_command(command, description):
            all_passed = False
            print(f"\n⚠️  {description} failed. Continuing with other tests...\n")

    # Run code quality checks
    print("\n🔍 Running Code Quality Checks")
    print("-" * 30)

    quality_commands = [
        (["black", "--check", "app/", "tests/"], "Code Formatting Check"),
        (["isort", "--check-only", "app/", "tests/"], "Import Sorting Check"),
        (["flake8", "app/", "tests/"], "Linting Check"),
        (["mypy", "app/"], "Type Checking"),
    ]

    for command, description in quality_commands:
        if not run_command(command, description):
            all_passed = False
            print(f"\n⚠️  {description} failed. Continuing with other checks...\n")

    # Summary
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests and checks passed!")
        print("✅ Your code is ready for production!")
    else:
        print("❌ Some tests or checks failed.")
        print("🔧 Please fix the issues before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    main()
