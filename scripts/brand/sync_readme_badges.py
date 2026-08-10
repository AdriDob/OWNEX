#!/usr/bin/env python3
"""Sync OWNEX README badges with the single source of truth.

Rewrites the hardcoded version and test-count badges in README.md from:
  - VERSION.txt            (release version)
  - `pytest --collect-only` (authoritative collected test count)

Idempotent. Never executes tests, just collects metadata.
Exit code non-zero only on IO errors.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"


def count_test_functions() -> int:
    """Authoritative count via `pytest --collect-only -q` summary line."""
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        ).stdout
        m = re.search(r"(\d{1,3}(?:,\d{3})*|\d+) tests collected", out)
        if m:
            return int(m.group(1).replace(",", ""))
    except Exception:
        pass
    # fallback: count test defs (functions + methods)
    total = 0
    for path in (ROOT / "tests").rglob("test_*.py"):
        text = path.read_text(errors="ignore")
        total += len(re.findall(r"(?:async\s+)?def\s+test_", text))
    return total


def main() -> int:
    version = (ROOT / "VERSION.txt").read_text().strip()
    tests = count_test_functions()
    tests_fmt = f"{tests:,}"

    text = README.read_text()
    updated = text
    updated = re.sub(r"badge/version-[^/]*", f"badge/version-{version}", updated)
    updated = re.sub(r"badge/tests-[^/]*", f"badge/tests-{tests}%2B", updated)
    updated = re.sub(r"\|\s*Tests\s*\|\s*[\d,]+(?:\+)?\s*pytest", f"| Tests | {tests_fmt}+ pytest", updated)

    if updated == text:
        print(f"README badges already in sync (version={version}, tests={tests}+)")
        return 0

    README.write_text(updated)
    print(f"README badges synced: version={version}, tests={tests}+")
    return 0


if __name__ == "__main__":
    sys.exit(main())
