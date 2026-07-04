#!/usr/bin/env python3
"""CATEYE AutoRelease — deterministic, safe, professional GitHub Releases automation.

Usage:
    python scripts/autorelease.py                              # Auto-release from artifacts
    python scripts/autorelease.py --dir <path>                  # Custom artifact directory
    python scripts/autorelease.py --dry-run                     # Preview only
    python scripts/autorelease.py --force                       # Override safety checks
    python scripts/autorelease.py --version X.Y.Z               # Override version

Flow:
    1. Validate all artifacts exist (sizes + SHA256)
    2. Read version (VERSION file > build_info.json)
    3. Validate git tag (auto-fix if mispointed)
    4. Create or update GitHub release
    5. Upload artifacts (skip already-uploaded unless --force)
    6. Ensure Latest + not prerelease
    7. Final integrity verification (re-download + SHA256 check)

Exit codes:
    0 = SUCCESS
    1 = VALIDATION FAILURE
    2 = RELEASE ALREADY EXISTS (use --force to override)
    3 = UPLOAD FAILURE
    4 = VERIFICATION FAILURE
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
VERSION_FILE = PROJECT_ROOT / "VERSION"

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
ARTIFACT_NAMES = [
    "CATEYEInstaller.exe",
    "CATEYE-1.6.0.zip",
    "build_info.json",
    "RELEASE_REPORT.md",
]
REQUIRED_ARTIFACTS = ["CATEYEInstaller.exe", "CATEYE-1.6.0.zip"]
GITHUB_REPO = "AdriDob/CATEYEhunteralpha"

PASS = True
FAILURES: list[str] = []
version: str = ""


def log(step: str, msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    icon = {"OK": "✅", "FAIL": "❌", "WARN": "⚠️", "INFO": "ℹ️", "SKIP": "⏭️"}.get(step, "•")
    print(f"{icon} [{ts}] [{step:>8}] {msg}", flush=True)


def fail(msg: str) -> None:
    global PASS
    PASS = False
    FAILURES.append(msg)
    log("FAIL", msg)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def gh(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return run(["gh"] + args + ["--repo", GITHUB_REPO], timeout=timeout)


# ── Phase 1: Artifact Validation ────────────────────────────────────────────


def validate_artifacts(artifact_dir: Path, build_info: dict | None) -> bool:
    log("INFO", f"Validating artifacts in: {artifact_dir}")
    ok = True
    missing: list[str] = []

    for name in ARTIFACT_NAMES:
        path = artifact_dir / name
        if not path.exists():
            missing.append(name)
            ok = False
            log("FAIL", f"Missing: {name}")
            continue
        size = path.stat().st_size
        log("OK", f"{name}: {size / 1024 / 1024:.1f} MB ({size:,} bytes)")

    for name in REQUIRED_ARTIFACTS:
        if name in missing:
            fail(f"Required artifact missing: {name}")

    if not ok:
        return False

    if build_info:
        stored = build_info.get("sha256", {})
        for name in ("CATEYE.exe", "CATEYEInstaller.exe", "CATEYE-1.6.0.zip"):
            path = artifact_dir / name
            if not path.exists():
                continue
            actual = sha256(path)
            expected = stored.get(name)
            if expected and actual != expected:
                fail(f"SHA256 mismatch for {name}")
                log("FAIL", f"  Expected: {expected}")
                log("FAIL", f"  Actual:   {actual}")
                ok = False
            elif expected:
                log("OK", f"SHA256 {name}: {actual[:16]}... (matches build_info)")
            else:
                log("WARN", f"SHA256 {name}: {actual[:16]}... (no reference in build_info)")

    return ok


# ── Phase 2: Version & Tag Management ───────────────────────────────────────


def read_version(artifact_dir: Path, build_info: dict | None, override: str | None) -> str:
    if override:
        if not SEMVER_RE.match(override):
            fail(f"Version override '{override}' is not valid semver")
            sys.exit(1)
        log(" INFO", f"Version from --override: {override}")
        return override

    if VERSION_FILE.exists():
        v = VERSION_FILE.read_text().strip()
        log("INFO", f"Version from VERSION file: {v}")
        return v

    if build_info and build_info.get("version"):
        v = build_info["version"]
        log("INFO", f"Version from build_info.json: {v}")
        return v

    fail("Cannot determine version (no VERSION file, no --version, no build_info.json)")
    sys.exit(1)


def validate_tag(version: str, dry_run: bool, force: bool) -> str:
    tag = f"v{version}"
    log("INFO", f"Checking git tag: {tag}")

    r = run(["git", "rev-parse", "--short", "HEAD"])
    head = r.stdout.strip()

    r = run(["git", "rev-parse", "--short", "--verify", f"refs/tags/{tag}"])
    if r.returncode == 0:
        existing_commit = r.stdout.strip()
        if existing_commit == head:
            log("OK", f"Tag {tag} already points to HEAD ({head})")
        else:
            log("WARN", f"Tag {tag} points to {existing_commit}, HEAD is {head}")
            if force and not dry_run:
                run(["git", "tag", "-f", tag, "HEAD"])
                run(["git", "push", "origin", tag, "--force"])
                log("OK", f"Tag {tag} force-moved to HEAD and pushed")
            elif dry_run:
                log("SKIP", f"[dry-run] Would force-move tag {tag} to HEAD")
            else:
                fail(f"Tag {tag} mispointed. Use --force to move it.")
                return ""
    else:
        log("INFO", f"Tag {tag} does not exist locally")
        if not dry_run:
            run(["git", "tag", tag, "HEAD"])
            run(["git", "push", "origin", tag])
            log("OK", f"Tag {tag} created at HEAD and pushed")
        else:
            log("SKIP", f"[dry-run] Would create tag {tag} at HEAD and push")

    return tag


# ── Phase 3: GitHub Release ─────────────────────────────────────────────────


def get_existing_release(tag: str) -> dict | None:
    r = gh(["release", "view", tag, "--json", "tagName,isDraft,isPrerelease,isLatest,name,url,assets"])
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def get_uploaded_assets(tag: str) -> set[str]:
    rel = get_existing_release(tag)
    if not rel:
        return set()
    return {a["name"] for a in rel.get("assets", [])}


def create_or_update_release(tag: str, artifact_dir: Path, dry_run: bool, force: bool) -> str | None:
    existing = get_existing_release(tag)
    notes_path = artifact_dir / "RELEASE_REPORT.md"

    if existing:
        is_draft = existing.get("isDraft", False)
        is_prerelease = existing.get("isPrerelease", False)
        is_latest = existing.get("isLatest", False)
        url = existing.get("url", "")
        log("INFO", f"Release already exists: {url}")
        log("INFO", f"  Draft: {is_draft}, Prerelease: {is_prerelease}, Latest: {is_latest}")

        if not force and not is_draft:
            log("WARN", "Release exists and is published. Use --force to update.")
            return url

        if dry_run:
            log("SKIP", f"[dry-run] Would update release {tag}")
            return url

        r = gh(["release", "edit", tag,
                "--draft=false",
                "--prerelease=false",
                "--latest",
                f"--notes-file={notes_path}"])
        if r.returncode == 0:
            log("OK", f"Release {tag} updated (draft=false, prerelease=false, latest=true)")
        else:
            fail(f"Failed to update release: {r.stderr.strip()}")
            return None
        return url

    notes_arg = []
    if notes_path.exists():
        notes_arg = [f"--notes-file={notes_path}"]
    else:
        notes_arg = ["--notes", f"CATEYE v{version} — Stable Release (automated)"]

    if dry_run:
        log("SKIP", "[dry-run] Would create release:")
        log("SKIP", f"  gh release create {tag} --title 'CATEYE v{version} — Stable Release'")
        return "https://github.com/AdriDob/CATEYEhunteralpha/releases/tag/" + tag

    r = gh(["release", "create", tag,
            "--title", f"CATEYE v{version} — Stable Release",
            "--draft=false",
            "--prerelease=false",
            "--latest"] + notes_arg)
    if r.returncode == 0:
        url = r.stdout.strip()
        log("OK", f"Release created: {url}")
        return url
    else:
        fail(f"Failed to create release: {r.stderr.strip()}")
        return None


# ── Phase 4: Artifact Upload ──────────────────────────────────────────────────


def upload_artifacts(tag: str, artifact_dir: Path, dry_run: bool, force: bool) -> bool:
    uploaded = get_uploaded_assets(tag)
    ok = True

    for name in ARTIFACT_NAMES:
        path = artifact_dir / name
        if not path.exists():
            continue

        if name in uploaded and not force:
            log("SKIP", f"{name} already uploaded (use --force to re-upload)")
            continue

        if dry_run:
            log("SKIP", f"[dry-run] Would upload: {name} ({path.stat().st_size / 1024 / 1024:.1f} MB)")
            continue

        log("INFO", f"Uploading {name} ({path.stat().st_size / 1024 / 1024:.1f} MB)...")
        r = gh(["release", "upload", tag, str(path), "--clobber"], timeout=300)

        if r.returncode == 0:
            log("OK", f"Uploaded: {name}")
        else:
            fail(f"Upload failed for {name}: {r.stderr.strip()}")
            ok = False

    return ok


# ── Phase 5: Final Verification ──────────────────────────────────────────────


def verify_release(tag: str, artifact_dir: Path, dry_run: bool) -> bool:
    if dry_run:
        log("SKIP", "[dry-run] Skipping final verification")
        return True

    log("INFO", "Running final integrity verification...")
    rel = get_existing_release(tag)
    if not rel:
        fail("Cannot verify — release not found after creation")
        return False

    if rel.get("isDraft", True):
        fail("Release is still in draft state")
        return False
    log("OK", "Release is published (not draft)")

    if rel.get("isPrerelease", True):
        fail("Release is marked as prerelease")
        return False
    log("OK", "Release is not prerelease")

    log("OK", f"Is latest: {rel.get('isLatest', False)}")

    uploaded_names = {a["name"] for a in rel.get("assets", [])}
    for name in ARTIFACT_NAMES:
        if name in uploaded_names:
            log("OK", f"Asset present: {name}")
        else:
            fail(f"Asset missing from release: {name}")

    exe_asset = next((a for a in rel.get("assets", []) if a["name"] == "CATEYEInstaller.exe"), None)
    if exe_asset:
        log("INFO", "Downloading CATEYEInstaller.exe from GitHub to verify SHA256...")
        tmp = Path(tempfile.mkstemp(suffix=".exe")[1])
        try:
            r = gh(["release", "download", tag, "--pattern", "CATEYEInstaller.exe",
                    "--output", str(tmp)], timeout=120)
            if r.returncode == 0:
                local_hash = sha256(artifact_dir / "CATEYEInstaller.exe")
                remote_hash = sha256(tmp)
                if local_hash == remote_hash:
                    log("OK", f"SHA256 match: {local_hash[:16]}... (upload integrity verified)")
                else:
                    fail("SHA256 mismatch after upload!")
                    log("FAIL", f"  Local:  {local_hash}")
                    log("FAIL", f"  Remote: {remote_hash}")
                    return False
            else:
                log("WARN", f"Could not download for verification: {r.stderr.strip()}")
        finally:
            tmp.unlink()

    url = rel.get("url", "")
    log("OK", f"Release URL: {url}")
    return True


# ── Main ─────────────────────────────────────────────────────────────────────


def build_confidence_score() -> int:
    if not PASS:
        return 0
    return 100


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CATEYE AutoRelease — deterministic GitHub Releases automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--dir", type=Path,
                        default=Path(os.environ.get("HOME", "/tmp")) / "CATEYE" if sys.platform != "win32"
                        else Path(os.environ.get("USERPROFILE", "C:/")) / "OneDrive" / "Desktop" / "Yo" / "privado" / "CATEYE",
                        help="Artifact directory (default: CATEYE final output)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no changes")
    parser.add_argument("--force", action="store_true", help="Override safety checks")
    parser.add_argument("--version", default=None, help="Override version (semver)")
    args = parser.parse_args()

    artifact_dir = args.dir.resolve()
    dry_run = args.dry_run
    force = args.force

    print("=" * 64)
    print("  CATEYE AutoRelease v1.0")
    print(f"  {datetime.now(timezone.utc).isoformat()}")
    print("=" * 64)
    print(f"  Artifact dir: {artifact_dir}")
    print(f"  Dry run:      {dry_run}")
    print(f"  Force:        {force}")
    print("=" * 64)
    print()

    # ── Phase 0: Pre-flight ──────────────────────────────────────────────
    if not artifact_dir.exists():
        fail(f"Artifact directory not found: {artifact_dir}")
        print()
        log("INFO", "Tip: Use --dir <path> to point to your artifacts folder")
        sys.exit(1)

    r = run(["gh", "auth", "status"])
    if r.returncode != 0:
        fail("gh CLI not authenticated. Run 'gh auth login' first.")
        sys.exit(1)
    log("OK", "gh CLI authenticated")

    # ── Phase 1: Validation ──────────────────────────────────────────────
    print()
    print("─" * 64)
    print("  PHASE 1: Artifact Validation")
    print("─" * 64)

    build_info = None
    bi_path = artifact_dir / "build_info.json"
    if bi_path.exists():
        try:
            build_info = json.loads(bi_path.read_text())
            log("OK", "build_info.json loaded")
        except json.JSONDecodeError:
            log("WARN", "build_info.json is invalid JSON")
    else:
        log("WARN", "build_info.json not found — skipping SHA256 reference check")

    if not validate_artifacts(artifact_dir, build_info):
        print()
        log("FAIL", "Artifact validation failed — aborting")
        sys.exit(1)

    # ── Phase 2: Version & Tag ───────────────────────────────────────────
    print()
    print("─" * 64)
    print("  PHASE 2: Version & Tag Management")
    print("─" * 64)

    global version
    version = read_version(artifact_dir, build_info, args.version)
    log("INFO", f"Release version: {version}")

    tag = validate_tag(version, dry_run, force)
    if not tag:
        sys.exit(1)

    # ── Phase 3: GitHub Release ──────────────────────────────────────────
    print()
    print("─" * 64)
    print("  PHASE 3: GitHub Release")
    print("─" * 64)

    url = create_or_update_release(tag, artifact_dir, dry_run, force)
    if not url:
        sys.exit(3)

    # ── Phase 4: Upload ─────────────────────────────────────────────────
    print()
    print("─" * 64)
    print("  PHASE 4: Artifact Upload")
    print("─" * 64)

    if not upload_artifacts(tag, artifact_dir, dry_run, force):
        sys.exit(3)

    # ── Phase 5: Verification ───────────────────────────────────────────
    print()
    print("─" * 64)
    print("  PHASE 5: Final Verification")
    print("─" * 64)

    if not verify_release(tag, artifact_dir, dry_run):
        sys.exit(4)

    # ── Summary ─────────────────────────────────────────────────────────
    print()
    print("=" * 64)
    confidence = build_confidence_score()

    if PASS:
        print(f"  ✅ RELEASE v{version} — SUCCESS")
    else:
        print(f"  ❌ RELEASE v{version} — FAILED")
    print(f"  Tag:          {tag}")
    print(f"  GitHub URL:   {url}")
    print(f"  Artifacts:    {len(ARTIFACT_NAMES)} files (~{sum((artifact_dir / n).stat().st_size for n in ARTIFACT_NAMES if (artifact_dir / n).exists()) / 1024 / 1024:.0f} MB)")
    print(f"  Confidence:   {confidence}/100")
    if FAILURES:
        print(f"  Failures:     {len(FAILURES)}")
        for f in FAILURES:
            print(f"    - {f}")
    print("=" * 64)

    sys.exit(0 if PASS else 1)


if __name__ == "__main__":
    main()
