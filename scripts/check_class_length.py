#!/usr/bin/env python3
"""Check that Python classes don't exceed 150 lines."""

import ast
import sys
from pathlib import Path
from typing import List, Tuple


def get_class_lengths(file_path: str) -> List[Tuple[str, int, int]]:
    """Get all class names and their line counts from a Python file."""
    path = Path(file_path)
    
    if not path.exists():
        print(f"Error: File {file_path} does not exist")
        return []
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Calculate class length (end_lineno - lineno + 1)
                start_line = node.lineno
                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                length = end_line - start_line + 1
                
                classes.append((node.name, start_line, length))
        
        return classes
        
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []


def check_class_lengths(file_path: str) -> bool:
    """Check if any classes in a file exceed 150 lines."""
    classes = get_class_lengths(file_path)
    max_lines = 150
    failed = False
    
    for class_name, start_line, length in classes:
        if length > max_lines:
            print(
                f"Error: Class '{class_name}' in {file_path} "
                f"(line {start_line}) has {length} lines "
                f"(exceeds limit of {max_lines})"
            )
            failed = True
    
    return not failed


def main():
    """Main function to check class lengths."""
    if len(sys.argv) < 2:
        print("Usage: python check_class_length.py <file1> [file2] ...")
        sys.exit(1)
    
    failed = False
    
    for file_path in sys.argv[1:]:
        if not check_class_lengths(file_path):
            failed = True
    
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main() 