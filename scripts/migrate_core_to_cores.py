#!/usr/bin/env python3
"""
Migration script: core/ -> cores/
Replaces all imports from 'core.' to 'cores.' in Python files.
"""

import os
import re
import sys
from pathlib import Path

# Directories to skip
SKIP_DIRS = {".venv", "__pycache__", ".git", "node_modules", "dist", "build", ".pytest_cache"}

# Files to skip (binary, generated, etc.)
SKIP_FILES = {"test_imports.py"}  # Known to have issues


def should_process_file(filepath: Path) -> bool:
    """Check if file should be processed."""
    # Skip if in excluded directory
    for part in filepath.parts:
        if part in SKIP_DIRS:
            return False
    # Skip if in excluded files
    if filepath.name in SKIP_FILES:
        return False
    # Only process .py files
    return filepath.suffix == ".py"


def migrate_file(filepath: Path) -> tuple[bool, int]:
    """
    Migrate a single file.
    Returns (changed, num_replacements)
    """
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return False, 0

    original = content
    replacements = 0

    # Replace 'from cores.' with 'from cores.'
    # Use word boundary to avoid partial matches
    content, n1 = re.subn(r"\bfrom core\.", "from cores.", content)
    replacements += n1

    # Replace 'import cores.' with 'import cores.'
    content, n2 = re.subn(r"\bimport core\.", "import cores.", content)
    replacements += n2

    if content != original:
        try:
            filepath.write_text(content, encoding="utf-8")
            return True, replacements
        except Exception as e:
            print(f"Error writing {filepath}: {e}")
            return False, 0

    return False, 0


def main():
    root = Path("/home/adriel/projects/Rastro")

    # Find all Python files
    py_files = []
    for filepath in root.rglob("*.py"):
        if should_process_file(filepath):
            py_files.append(filepath)

    print(f"Found {len(py_files)} Python files to process")

    total_changed = 0
    total_replacements = 0
    changed_files = []

    for filepath in py_files:
        changed, num = migrate_file(filepath)
        if changed:
            total_changed += 1
            total_replacements += num
            rel_path = filepath.relative_to(root)
            changed_files.append((str(rel_path), num))
            print(f"  Changed: {rel_path} ({num} replacements)")

    print(f"\n=== Summary ===")
    print(f"Files changed: {total_changed}")
    print(f"Total replacements: {total_replacements}")

    # Save changed files list for reference
    with open("migration_log.txt", "w") as f:
        for rel_path, num in changed_files:
            f.write(f"{rel_path}: {num}\n")


if __name__ == "__main__":
    main()
