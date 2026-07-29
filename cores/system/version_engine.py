"""OWNEX Version Engine — single source of truth for platform versioning.

Unified system that reads from VERSION.txt and can sync to all project files:
  - pyproject.toml           (project.version)
  - frontend/package.json    (version field)
  - core/__init__.py          (__version__)
  - apps/*/manifest.py        (version field in IAppPlugin)
  - apps/*/__init__.py        (__version__ where present)

Usage:
    >>> from core.system.version_engine import VersionEngine
    >>> ve = VersionEngine()
    >>> ve.get_version()          # "4.6.0"
    >>> ve.bump("patch")          # "4.6.1"
    >>> ve.bump("minor")          # "4.7.0"
    >>> ve.bump("major")          # "5.0.0"
    >>> ve.sync_all()             # writes to all tracked files
"""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

# ── paths ──────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION.txt"
PYPROJECT_TOML = PROJECT_ROOT / "pyproject.toml"
FRONTEND_PACKAGE_JSON = PROJECT_ROOT / "frontend" / "package.json"
CHANGELOG_FILE = PROJECT_ROOT / "CHANGELOG.md"

# Files with __version__ that should sync to platform version
VERSION_INIT_FILES: list[Path] = [
    PROJECT_ROOT / "core" / "__init__.py",
]

# App manifests whose version should sync (apps/ subdirectory)
APP_MANIFEST_DIR = PROJECT_ROOT / "apps"

# Files to track for changes — read from VERSION.txt by external consumers
VERSION_CONSUMER_FILES: list[Path] = [
    PROJECT_ROOT / "pyproject.toml",
    PROJECT_ROOT / "frontend" / "package.json",
    PROJECT_ROOT / "core" / "__init__.py",
]

# Pattern for pyproject.toml version field
_RE_PYPROJECT_VERSION = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)
# Pattern for __version__ = "X.Y.Z"
_RE_VERSION_ASSIGN = re.compile(r'^__version__\s*=\s*"([^"]+)"', re.MULTILINE)
# Pattern for version field in IAppPlugin manifest calls / JSON
_RE_MANIFEST_VERSION = re.compile(
    r'(version\s*[=:]\s*)"([^"]+)"',
)
# Pattern for frontend package.json version
_RE_PKG_VERSION = re.compile(r'"version":\s*"([^"]+)"')


class VersionError(Exception):
    """Raised on invalid version operations."""


class Version:
    """Semver 2.0 container with comparison helpers."""

    def __init__(self, major: int = 0, minor: int = 0, patch: int = 0, pre: str | None = None) -> None:
        self.major = major
        self.minor = minor
        self.patch = patch
        self.pre = pre

    @classmethod
    def parse(cls, s: str) -> Version:
        """Parse '4.6.0' or '4.6.0-dev' or '4.6.0-alpha.1'."""
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)([-+].+)?$", s.strip())
        if not m:
            raise VersionError(f"Cannot parse version string: {s!r}")
        major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
        pre = m.group(4) or None
        if pre and pre.startswith("+"):
            pre = None  # build metadata — ignore
        return cls(major, minor, patch, pre)

    def bump(self, part: str, pre: str | None = None) -> Version:
        """Return a new Version bumped by *part* ('major', 'minor', 'patch')."""
        if part == "major":
            return Version(self.major + 1, 0, 0, pre)
        elif part == "minor":
            return Version(self.major, self.minor + 1, 0, pre)
        elif part == "patch":
            return Version(self.major, self.minor, self.patch + 1, pre)
        raise VersionError(f"Unknown bump part: {part!r} (use major/minor/patch)")

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre:
            return f"{base}{self.pre}"
        return base

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch, self.pre) == (other.major, other.minor, other.patch, other.pre)

    def __lt__(self, other: Version) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __repr__(self) -> str:
        return f"Version({str(self)!r})"


class VersionEngine:
    """Manages the single source of truth for OWNEX versioning."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root or PROJECT_ROOT)
        self._version_file = self.root / "VERSION.txt"
        self._cached_version: Version | None = None

    # ── read / write VERSION.txt ─────────────────────────────────────────

    def read_raw(self) -> str:
        """Read VERSION.txt and return the raw string (stripped)."""
        if not self._version_file.exists():
            raise VersionError(
                f"VERSION.txt not found at {self._version_file}. Create it with the current version (e.g. '4.6.0')."
            )
        return self._version_file.read_text(encoding="utf-8").strip()

    def write_raw(self, raw: str) -> None:
        """Write raw string to VERSION.txt."""
        self._version_file.write_text(raw.strip() + "\n", encoding="utf-8")
        self._cached_version = None

    def get_version(self) -> Version:
        """Parse and return the current platform version."""
        if self._cached_version is None:
            self._cached_version = Version.parse(self.read_raw())
        return self._cached_version

    def set_version(self, v: Version) -> None:
        """Write a Version object to VERSION.txt."""
        self.write_raw(str(v))

    # ── bump ─────────────────────────────────────────────────────────────

    def bump(self, part: str, pre: str | None = None, auto_sync: bool = False) -> Version:
        """Bump the version and optionally sync all files.

        Args:
            part: 'major', 'minor', or 'patch'
            pre: optional pre-release suffix (e.g. '-dev', '-alpha.1')
            auto_sync: if True, also sync to pyproject.toml, package.json, etc.

        Returns:
            The new Version.
        """
        current = self.get_version()
        new_ver = current.bump(part, pre)
        self.set_version(new_ver)
        if auto_sync:
            self.sync_all()
        return new_ver

    # ── sync helpers ─────────────────────────────────────────────────────

    def _replace_in_file(self, path: Path, pattern: re.Pattern, replacement: str) -> bool:
        """Replace first match of *pattern* in *path* with *replacement*.
        Returns True if a change was made.
        """
        if not path.exists():
            return False
        old_text = path.read_text(encoding="utf-8")
        new_text, count = pattern.subn(replacement, old_text, count=1)
        if count == 0:
            return False
        if new_text != old_text:
            path.write_text(new_text, encoding="utf-8")
            return True
        return False

    def _replace_version_field(self, path: Path, new_version: str) -> bool:
        """Generic: replace version=\"X.Y.Z\" or version: \"X.Y.Z\" in a file."""
        if not path.exists():
            return False
        old_text = path.read_text(encoding="utf-8")
        new_text = _RE_MANIFEST_VERSION.sub(
            lambda m: f'{m.group(1)}"{new_version}"',
            old_text,
        )
        if new_text != old_text:
            path.write_text(new_text, encoding="utf-8")
            return True
        return False

    # ── sync targets ─────────────────────────────────────────────────────

    def sync_pyproject(self) -> bool:
        """Sync pyproject.toml version to VERSION.txt."""
        ver = str(self.get_version())
        return self._replace_in_file(
            PYPROJECT_TOML,
            _RE_PYPROJECT_VERSION,
            f'version = "{ver}"',
        )

    def sync_frontend(self) -> bool:
        """Sync frontend/package.json version to VERSION.txt."""
        ver = str(self.get_version())
        return self._replace_in_file(
            FRONTEND_PACKAGE_JSON,
            _RE_PKG_VERSION,
            f'"version": "{ver}"',
        )

    def sync_core_init(self) -> bool:
        """Sync core/__init__.py __version__ to VERSION.txt."""
        ver = str(self.get_version())
        result = False
        for path in VERSION_INIT_FILES:
            if self._replace_in_file(path, _RE_VERSION_ASSIGN, f'__version__ = "{ver}"'):
                result = True
        return result

    def sync_app_manifests(self, target_apps: list[str] | None = None) -> dict[str, bool]:
        """Sync version in all app manifests under apps/.

        Args:
            target_apps: if provided, only sync these app IDs (e.g. ['forge', 'vault']).
                         If None, syncs ALL apps.

        Returns:
            Dict of app_name -> changed (True/False)
        """
        ver = str(self.get_version())
        results: dict[str, bool] = {}
        app_dir = self.root / "apps"
        if not app_dir.is_dir():
            return results

        for child in sorted(app_dir.iterdir()):
            if not child.is_dir():
                continue
            app_name = child.name
            if target_apps and app_name not in target_apps:
                results[app_name] = False
                continue
            manifest_path = child / "manifest.py"
            if not manifest_path.exists():
                results[app_name] = False
                continue
            changed = self._replace_version_field(manifest_path, ver)
            results[app_name] = changed

            # Also check __init__.py for the app
            init_path = child / "__init__.py"
            if init_path.exists():
                init_changed = self._replace_in_file(
                    init_path,
                    _RE_VERSION_ASSIGN,
                    f'__version__ = "{ver}"',
                )
                if init_changed:
                    results[f"{app_name}/__init__"] = True

        return results

    def sync_all(self) -> dict[str, bool]:
        """Sync VERSION.txt to all tracked project files.

        Returns:
            Dict of file/section -> changed (True/False)
        """
        results: dict[str, bool] = {}
        results["pyproject.toml"] = self.sync_pyproject()
        results["frontend/package.json"] = self.sync_frontend()
        results["core/__init__.py"] = self.sync_core_init()
        manifest_results = self.sync_app_manifests()
        for k, v in manifest_results.items():
            results[f"app/{k}"] = v
        return results

    # ── changelog ────────────────────────────────────────────────────────

    def append_changelog(self, message: str, author: str = "Hermes Agent") -> None:
        """Append an entry to CHANGELOG.md under the current version header.

        If the version header doesn't exist, creates it.
        """
        ver = str(self.get_version())
        today = date.today().isoformat()
        header = f"## [{ver}] - {today}"

        if not CHANGELOG_FILE.exists():
            CHANGELOG_FILE.write_text(
                f"# Changelog\n\n{header}\n\n- {message} — {author}\n",
                encoding="utf-8",
            )
            return

        content = CHANGELOG_FILE.read_text(encoding="utf-8")

        # If this version header already exists, append under it
        version_header_pattern = re.compile(
            rf"^## \[{re.escape(ver)}\] - \d{{4}}-\d{{2}}-\d{{2}}$",
            re.MULTILINE,
        )
        match = version_header_pattern.search(content)
        if match:
            # Insert after the header line
            header_end = match.end()
            insert_pos = content.index("\n", header_end) + 1
            # Check if next line is already a list item or another header
            rest = content[insert_pos:].lstrip()
            insertion = f"- {message} — {author}\n"
            if rest.startswith("##"):
                # No entries yet under this header
                insertion = "\n" + insertion
            content = content[:insert_pos] + insertion + content[insert_pos:]
        else:
            # Insert new header at the top (after the first line if it's a title)
            if content.startswith("# "):
                first_newline = content.index("\n")
                content = (
                    content[: first_newline + 1]
                    + f"\n{header}\n\n- {message} — {author}\n\n"
                    + content[first_newline + 1 :]
                )
            else:
                content = f"{header}\n\n- {message} — {author}\n\n{content}"

        CHANGELOG_FILE.write_text(content, encoding="utf-8")

    # ── git tag ──────────────────────────────────────────────────────────

    def git_tag(self, message: str | None = None) -> str:
        """Create a git tag for the current version and return the tag name.

        Requires git to be available and the project to be a git repo.
        """
        ver = str(self.get_version())
        tag = f"v{ver}"
        msg = message or f"Release {tag}"
        try:
            subprocess.run(
                ["git", "tag", "-a", tag, "-m", msg],
                cwd=self.root,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else ""
            if "already exists" in stderr:
                raise VersionError(f"Tag {tag} already exists. Bump version first.") from e
            raise VersionError(f"Git tag failed: {stderr}") from e
        except FileNotFoundError as e:
            raise VersionError("Git not found. Cannot create tag.") from e
        return tag

    # ── info ─────────────────────────────────────────────────────────────

    def info(self) -> dict[str, object]:
        """Return a dict with version info for the API endpoint."""
        ver = self.get_version()
        raw = self.read_raw()
        return {
            "version": str(ver),
            "raw": raw,
            "major": ver.major,
            "minor": ver.minor,
            "patch": ver.patch,
            "pre_release": ver.pre,
            "semver": str(ver),
            "pyproject": self._read_pyproject_version(),
            "frontend": self._read_frontend_version(),
        }

    def _read_pyproject_version(self) -> str | None:
        try:
            text = PYPROJECT_TOML.read_text(encoding="utf-8")
            m = _RE_PYPROJECT_VERSION.search(text)
            return m.group(1) if m else None
        except Exception:
            return None

    def _read_frontend_version(self) -> str | None:
        try:
            text = FRONTEND_PACKAGE_JSON.read_text(encoding="utf-8")
            m = _RE_PKG_VERSION.search(text)
            return m.group(1) if m else None
        except Exception:
            return None


# ── standalone CLI ─────────────────────────────────────────────────────────


def cli() -> None:
    """Entry point for 'ownex-version' CLI script."""
    import argparse

    parser = argparse.ArgumentParser(
        description="OWNEX Version Engine — manage platform version from VERSION.txt",
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="get",
        choices=["get", "bump", "sync", "tag", "info"],
        help="Action to perform (default: get)",
    )
    parser.add_argument(
        "--part",
        default="patch",
        choices=["major", "minor", "patch"],
        help="Version part to bump (default: patch)",
    )
    parser.add_argument(
        "--pre",
        default=None,
        help="Pre-release suffix (e.g. 'dev', 'alpha.1')",
    )
    parser.add_argument(
        "--message",
        "-m",
        default=None,
        help="Tag / changelog message",
    )
    parser.add_argument(
        "--changelog",
        "-c",
        action="store_true",
        help="Append changelog entry (requires --message)",
    )
    parser.add_argument(
        "--auto-sync",
        action="store_true",
        help="Sync all files after bump",
    )

    args = parser.parse_args()
    ve = VersionEngine()

    try:
        if args.action == "get":
            ver = ve.get_version()
            print(ver)
            if args.message == "v":
                print(f"  major={ver.major} minor={ver.minor} patch={ver.patch}{' pre=' + ver.pre if ver.pre else ''}")

        elif args.action == "bump":
            new_ver = ve.bump(args.part, pre=args.pre, auto_sync=args.auto_sync)
            print(f"Bumped to {new_ver}" + (" (synced)" if args.auto_sync else ""))
            if args.changelog and args.message:
                ve.append_changelog(args.message)
                print("Changelog entry added.")

        elif args.action == "sync":
            results = ve.sync_all()
            changed = [k for k, v in results.items() if v]
            if changed:
                print(f"Synced {len(changed)} file(s): {', '.join(changed)}")
            else:
                print("All files already in sync.")

        elif args.action == "tag":
            tag = ve.git_tag(message=args.message)
            print(f"Created git tag: {tag}")

        elif args.action == "info":
            info = ve.info()
            print(f"  Version:    {info['version']}")
            print(f"  Semver:     {info['semver']}")
            print(f"  Major:      {info['major']}")
            print(f"  Minor:      {info['minor']}")
            print(f"  Patch:      {info['patch']}")
            print(f"  Pre:        {info['pre_release'] or '(none)'}")
            print(f"  pyproject:  {info['pyproject']}")
            print(f"  frontend:   {info['frontend']}")

    except VersionError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli()
