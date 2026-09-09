#!/usr/bin/env python3
"""
Fix patch strings in test files: core. -> cores.
"""

import os
import re
from pathlib import Path

SKIP_DIRS = {".venv", "__pycache__", ".git", "node_modules", "dist", "build", ".pytest_cache"}


def should_process_file(filepath: Path) -> bool:
    for part in filepath.parts:
        if part in SKIP_DIRS:
            return False
    return filepath.suffix == ".py" and "test" in str(filepath)


def fix_patch_strings(filepath: Path) -> tuple[bool, int]:
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return False, 0

    original = content
    replacements = 0

    # Fix patch strings: @patch("cores.xxx") -> @patch("cores.xxx")
    # Also fix with patch("cores.xxx") as mock:
    # And monkeypatch.setattr("cores.xxx", ...)

    # Pattern 1: @patch("cores.xxx")
    content, n1 = re.subn(r'@patch\("core\.', '@patch("cores.', content)
    replacements += n1

    # Pattern 2: with patch("cores.xxx")
    content, n2 = re.subn(r'with patch\("core\.', 'with patch("cores.', content)
    replacements += n2

    # Pattern 3: monkeypatch.setattr("cores.xxx"
    content, n3 = re.subn(r'monkeypatch\.setattr\("core\.', 'monkeypatch.setattr("cores.', content)
    replacements += n3

    # Pattern 4: @patch.object with core.
    content, n4 = re.subn(r"@patch\.object\(core\.", "@patch.object(cores.", content)
    replacements += n4

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

    py_files = []
    for filepath in root.rglob("*.py"):
        if should_process_file(filepath):
            py_files.append(filepath)

    print(f"Found {len(py_files)} test files to process")

    total_changed = 0
    total_replacements = 0
    changed_files = []

    for filepath in py_files:
        changed, num = fix_patch_strings(filepath)
        if changed:
            total_changed += 1
            total_replacements += num
            rel_path = filepath.relative_to(root)
            changed_files.append((str(rel_path), num))
            print(f"  Changed: {rel_path} ({num} replacements)")

    print(f"\n=== Summary ===")
    print(f"Files changed: {total_changed}")
    print(f"Total replacements: {total_replacements}")


if __name__ == "__main__":
    main()
