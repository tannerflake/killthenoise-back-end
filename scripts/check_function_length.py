#!/usr/bin/env python3
"""Check that Python functions don't exceed 50 lines."""

import ast
import sys
from pathlib import Path
from typing import List, Tuple


def get_function_lengths(file_path: str) -> List[Tuple[str, int, int]]:
    """Get all function names and their line counts from a Python file."""
    path = Path(file_path)
    
    if not path.exists():
        print(f"Error: File {file_path} does not exist")
        return []
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Calculate function length (end_lineno - lineno + 1)
                start_line = node.lineno
                end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line
                length = end_line - start_line + 1
                
                functions.append((node.name, start_line, length))
        
        return functions
        
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []


def check_function_lengths(file_path: str) -> bool:
    """Check if any functions in a file exceed 50 lines."""
    functions = get_function_lengths(file_path)
    max_lines = 50
    failed = False
    
    for func_name, start_line, length in functions:
        if length > max_lines:
            print(
                f"Error: Function '{func_name}' in {file_path} "
                f"(line {start_line}) has {length} lines "
                f"(exceeds limit of {max_lines})"
            )
            failed = True
    
    return not failed


def main():
    """Main function to check function lengths."""
    if len(sys.argv) < 2:
        print("Usage: python check_function_length.py <file1> [file2] ...")
        sys.exit(1)
    
    failed = False
    
    for file_path in sys.argv[1:]:
        if not check_function_lengths(file_path):
            failed = True
    
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main() 