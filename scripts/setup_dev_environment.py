#!/usr/bin/env python3
"""Setup development environment with pre-commit hooks."""

import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"Running: {description}")
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return False


def install_pre_commit() -> bool:
    """Install pre-commit hooks."""
    commands = [
        (["pip", "install", "pre-commit"], "Installing pre-commit"),
        (["pre-commit", "install"], "Installing pre-commit hooks"),
        (["pre-commit", "install", "--hook-type", "commit-msg"], "Installing commit-msg hook"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    
    return True


def install_dev_dependencies() -> bool:
    """Install development dependencies."""
    commands = [
        (["pip", "install", "black", "isort", "flake8", "mypy", "bandit"], "Installing code quality tools"),
        (["pip", "install", "pytest", "pytest-asyncio"], "Installing testing tools"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    
    return True


def create_git_hooks() -> bool:
    """Create additional git hooks for development."""
    hooks_dir = Path(".git/hooks")
    hooks_dir.mkdir(exist_ok=True)
    
    # Create pre-push hook to run tests
    pre_push_hook = hooks_dir / "pre-push"
    pre_push_content = """#!/bin/sh
# Run tests before pushing
echo "Running tests before push..."
python -m pytest tests/ -v
if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Push aborted."
    exit 1
fi
echo "✅ Tests passed. Proceeding with push."
"""
    
    try:
        with open(pre_push_hook, 'w') as f:
            f.write(pre_push_content)
        pre_push_hook.chmod(0o755)
        print("✅ Created pre-push hook")
        return True
    except Exception as e:
        print(f"❌ Failed to create pre-push hook: {e}")
        return False


def main():
    """Main setup function."""
    print("🚀 Setting up KillTheNoise development environment...")
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Error: pyproject.toml not found. Run this script from the project root.")
        sys.exit(1)
    
    # Install dependencies
    if not install_dev_dependencies():
        print("❌ Failed to install development dependencies")
        sys.exit(1)
    
    # Install pre-commit hooks
    if not install_pre_commit():
        print("❌ Failed to install pre-commit hooks")
        sys.exit(1)
    
    # Create additional git hooks
    if not create_git_hooks():
        print("❌ Failed to create git hooks")
        sys.exit(1)
    
    print("\n🎉 Development environment setup complete!")
    print("\nNext steps:")
    print("1. Run 'pre-commit run --all-files' to check existing code")
    print("2. Run 'python -m pytest tests/' to run tests")
    print("3. Read .cursorrules for coding standards")
    print("4. Start coding with confidence! 🚀")


if __name__ == "__main__":
    main() 