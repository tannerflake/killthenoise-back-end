#!/usr/bin/env python3
"""Check that Python files don't exceed 200 lines."""

import sys
from pathlib import Path


def check_file_length(file_path: str) -> bool:
    """Check if a file exceeds 200 lines."""
    path = Path(file_path)
    
    if not path.exists():
        print(f"Error: File {file_path} does not exist")
        return False
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        line_count = len(lines)
        max_lines = 200
        
        if line_count > max_lines:
            print(
                f"Error: {file_path} has {line_count} lines "
                f"(exceeds limit of {max_lines})"
            )
            return False
        
        return True
        
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return False


def main():
    """Main function to check file lengths."""
    if len(sys.argv) < 2:
        print("Usage: python check_file_length.py <file1> [file2] ...")
        sys.exit(1)
    
    failed = False
    
    for file_path in sys.argv[1:]:
        if not check_file_length(file_path):
            failed = True
    
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main() 