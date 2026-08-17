"""OWNEX Migration — full PC-to-PC export/import of all persistent data.

One command to move every byte of OWNEX to a new machine:

    python run.py --migrate-export            # creates OWNEX_MIGRATE_<ts>.zip
    python run.py --migrate <file.zip>        # on the new PC: verify + restore

Sections captured (each with its own destination on import):

    orion/              → ~/.orion            (identity_vault.key, license.json,
                                               config.sh, database/, events, targets/)
    ownex/              → ~/.ownex            (knowledge.db, observability, config, ...)
    config_ownex/       → ~/.config/ownex     (trading.json, payment_network.json, ...)
    repo_database/      → <repo>/database     (*.db only)
    repo_data/          → <repo>/data         (workbank, knowledge index, voice, ...)
    env/.env            → <repo>/.env

Excluded by design (regenerable or transient): backups/, logs/, vision_cache/,
caches, __pycache__, node_modules, *.pid/*.lock/*.log, sqlite -wal/-shm
(after WAL checkpoint), and legacy *.tar.gz/*.zip archives.

License note: license.json carries the HWID of the source machine. On the new
PC validation requires CATEYE_PORTABLE=1 (migration mode) or re-activation —
the import prints the exact guidance.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import sqlite3
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from core import OWNEX_DIR
from core.version import OWNEX_VERSION

logger = logging.getLogger("ownex.core.backup.migrate")

MIGRATE_PREFIX = "OWNEX_MIGRATE"
MANIFEST_NAME = "manifest.json"
README_NAME = "README_MIGRATION.txt"

_COMMON_EXCLUDED_DIRS = {"__pycache__", "node_modules", ".git", ".venv", "venv", "backups"}
_COMMON_EXCLUDED_SUFFIXES = (".pyc", "-wal", "-shm", ".pid", ".lock", ".log", ".tar.gz", ".zip")


def _data_dir() -> Path:
    """Persistent data dir (mirror of cores/platform/system.get_data_dir)."""
    env_dir = os.environ.get("CATEYE_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", "")
        return Path(base) / "CATEYE" if base else Path.home() / ".orion"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "CATEYE"
    return Path.home() / ".orion"


def _project_root() -> Path:
    """Repo root (dev mode). In frozen mode migration is not applicable."""
    return Path(__file__).resolve().parent.parent.parent


def _get_hw_id() -> str:
    """Lazy hardware id (license guidance only — cores import avoided at module level)."""
    try:
        from cores.license.hardware import get_hardware_id

        return get_hardware_id()
    except Exception:
        return platform.node()


def _checkpoint_dbs(paths: list[Path]) -> None:
    """WAL checkpoint every known sqlite database for consistent export."""
    for db in paths:
        if not db.exists() or not db.is_file():
            continue
        try:
            conn = sqlite3.connect(str(db))
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.close()
            logger.debug("WAL checkpoint: %s", db.name)
        except Exception as exc:
            logger.warning("WAL checkpoint failed for %s: %s", db, exc)


def _scan_dir(base: Path, prefix: str, excludes: set[str] | None = None) -> list[dict]:
    """Recursively scan base, returning manifest entries with relative paths."""
    entries: list[dict] = []
    excludes = excludes or set()
    if not base.exists():
        return entries
    for root, dirs, files in os.walk(str(base)):
        rel_root = Path(root).relative_to(base)
        keep_dirs: list[str] = []
        for d in sorted(dirs):
            if d in _COMMON_EXCLUDED_DIRS or d in excludes or d.startswith("."):
                continue
            keep_dirs.append(d)
        dirs[:] = keep_dirs
        for name in sorted(files):
            rel = str(rel_root / name) if str(rel_root) != "." else name
            if name in _COMMON_EXCLUDED_DIRS or name in excludes:
                continue
            if name.startswith(".") or name.endswith(_COMMON_EXCLUDED_SUFFIXES):
                continue
            full = Path(root) / name
            try:
                stat = full.stat()
                entries.append(
                    {
                        "path": f"{prefix}/{rel}",
                        "size": stat.st_size,
                        "sha256": _sha256_file(full),
                    }
                )
            except Exception:
                logger.warning("Cannot read %s, skipping", full)
    return entries


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _readme_text(manifest: dict) -> str:
    return f"""OWNEX FULL MIGRATION
=====================
Exportado: {manifest.get("created_at")}
Versión:   {manifest.get("version")}
Máquina:   {manifest.get("source_hostname")}

CONTENIDO
---------
{json.dumps(manifest.get("sections", {}), indent=2)}

RESTAURAR EN LA PC NUEVA
------------------------
1) Instalá OWNEX (git clone + .venv + pip install -r requirements.txt)
2) python run.py --migrate {Path(manifest.get("archive_name", "OWNEX_MIGRATE.zip")).name}
3) Licencia: como la licencia viene ligada al hardware de la PC vieja,
   arrancá con CATEYE_PORTABLE=1 (modo migración) o reactivá la licencia.
4) Frontend: cd frontend && npm install && npm run build
5) Verificá: python run.py --verify

El archivo identity_vault.key se restaura automáticamente: sin él, las
credenciales cifradas (API keys, sesiones) no podrían descifrarse.
"""


def export_migration(
    dest: str | Path | None = None,
    *,
    orion_dir: Path | None = None,
    ownex_dir: Path | None = None,
    config_dir: Path | None = None,
    repo_database_dir: Path | None = None,
    repo_data_dir: Path | None = None,
    env_file: Path | None = None,
    include_targets: bool = True,
) -> dict:
    """Export all OWNEX persistent data into a single migration zip."""
    root = _project_root()
    orion = orion_dir or _data_dir()
    ownex = ownex_dir or OWNEX_DIR
    config = config_dir or Path.home() / ".config" / "ownex"
    repo_db = repo_database_dir or root / "database"
    repo_data = repo_data_dir or root / "data"
    env = env_file or root / ".env"

    # Deterministic default destination: ~/.ownex/backups/ (excluded from scans)
    if dest is None:
        ownex_backups = ownex / "backups"
        ownex_backups.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")
        dest = ownex_backups / f"{MIGRATE_PREFIX}_{ts}.zip"
    dest = Path(dest)

    # 1. Consistent databases: WAL checkpoint before reading
    db_candidates = [
        orion / "database",
        ownex / "database",
        repo_db,
        repo_data,
    ]
    for d in db_candidates:
        if d.exists():
            _checkpoint_dbs(sorted(d.glob("*.db")))

    # 2. Scan every section
    orion_excludes = {"logs", "vision_cache", "targets"} if not include_targets else {"logs", "vision_cache"}
    sections: list[tuple[str, Path, set[str] | None]] = [
        ("orion", orion, orion_excludes),
        ("ownex", ownex, None),
        ("config_ownex", config, None),
        ("repo_database", repo_db, None),
        ("repo_data", repo_data, None),
    ]
    files: list[dict] = []
    section_meta: dict[str, dict] = {}
    for prefix, base, excludes in sections:
        entries = _scan_dir(base, prefix, excludes)
        section_meta[prefix] = {"files": len(entries), "size": sum(e["size"] for e in entries)}
        files.extend(entries)

    env_entries: list[dict] = []
    if env.exists():
        env_entries = [{"path": "env/.env", "size": env.stat().st_size, "sha256": _sha256_file(env)}]
        section_meta["env"] = {"files": 1, "size": env.stat().st_size}

    total_size = sum(e["size"] for e in files) + sum(e["size"] for e in env_entries)
    manifest = {
        "tool": "ownex-migrate",
        "version": OWNEX_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "source_hostname": platform.node(),
        "source_hwid": _get_hw_id(),
        "archive_name": dest.name,
        "sections": section_meta,
        "total_files": len(files) + len(env_entries),
        "total_size": total_size,
        "files": files + env_entries,
    }

    # 3. Write the archive (manifest first, then files)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2))
            zf.writestr(README_NAME, _readme_text(manifest))
            for entry in files:
                section = entry["path"].split("/", 1)[0]
                base = next(b for p, b, _ in sections if p == section)
                try:
                    zf.write(base / entry["path"].split("/", 1)[1], arcname=entry["path"])
                except Exception as exc:
                    logger.warning("Failed to add %s to migration: %s", entry["path"], exc)
            if env_entries:
                zf.write(env, arcname="env/.env")
        size = dest.stat().st_size
        return {
            "status": "ok",
            "archive_path": str(dest),
            "size": size,
            "size_mb": round(size / (1024 * 1024), 2),
            "total_files": manifest["total_files"],
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "sections": section_meta,
        }
    except Exception as exc:
        logger.exception("Migration export failed")
        return {"status": "error", "reason": str(exc)}


def verify_migration(archive: str | Path) -> dict:
    """Verify migration archive: manifest schema + per-file sha256."""
    path = Path(archive)
    if not path.exists():
        return {"status": "error", "reason": f"Archive not found: {path}"}
    try:
        with zipfile.ZipFile(path, "r") as zf:
            if MANIFEST_NAME not in zf.namelist():
                return {"status": "error", "reason": "Missing manifest.json — not an OWNEX migration archive"}
            try:
                manifest = json.loads(zf.read(MANIFEST_NAME))
            except json.JSONDecodeError as exc:
                return {"status": "error", "reason": f"Corrupt manifest.json: {exc}"}
            if manifest.get("tool") != "ownex-migrate":
                return {
                    "status": "error",
                    "reason": "Legacy backup format — use `python run.py --restore <file>` instead of --migrate",
                }

            expected = {e["path"]: e for e in manifest.get("files", [])}
            checksum_errors: list[str] = []
            for entry in manifest.get("files", []):
                rel = entry["path"]
                try:
                    content = zf.read(rel)
                    actual = hashlib.sha256(content).hexdigest()
                    if actual != entry.get("sha256"):
                        checksum_errors.append(rel)
                except KeyError:
                    checksum_errors.append(f"{rel} (missing in archive)")
                except Exception as exc:
                    checksum_errors.append(f"{rel} ({exc})")

            extra = [n for n in zf.namelist() if n not in expected and n not in (MANIFEST_NAME, README_NAME)]
            status = "ok" if not checksum_errors else "corrupted"
            return {
                "status": status,
                "checksum_errors": checksum_errors[:20],
                "total_files": len(expected),
                "manifest": {
                    "tool": manifest.get("tool"),
                    "version": manifest.get("version"),
                    "created_at": manifest.get("created_at"),
                    "source_hostname": manifest.get("source_hostname"),
                    "sections": manifest.get("sections"),
                    "total_size_mb": round(manifest.get("total_size", 0) / (1024 * 1024), 2),
                },
                "extra_files": extra,
            }
    except zipfile.BadZipFile as exc:
        return {"status": "error", "reason": f"Not a valid zip: {exc}"}
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}


def _section_dest(
    prefix: str,
    repo_root: Path,
    data_dir: Path | None = None,
    ownex_dir: Path | None = None,
    config_dir: Path | None = None,
) -> Path | None:
    """Map archive section prefix → destination directory."""
    if prefix == "orion":
        return data_dir or _data_dir()
    if prefix == "ownex":
        return ownex_dir or OWNEX_DIR
    if prefix == "config_ownex":
        return config_dir or Path.home() / ".config" / "ownex"
    if prefix == "repo_database":
        return repo_root / "database"
    if prefix == "repo_data":
        return repo_root / "data"
    if prefix == "env":
        return repo_root
    return None


def import_migration(
    archive: str | Path,
    repo_root: Path | None = None,
    *,
    data_dir: Path | None = None,
    ownex_dir: Path | None = None,
    config_dir: Path | None = None,
    force: bool = False,
) -> dict:
    """Restore a full migration archive on the target machine.

    Destinations are injectable (data_dir/ownex_dir/config_dir) so callers
    (tests, sandboxes) can isolate imports from the real home. A guard refuses
    to overwrite non-empty home sections unless force=True.
    """
    path = Path(archive)
    verification = verify_migration(path)
    if verification.get("status") == "error":
        return {"status": "error", "reason": verification.get("reason", "Invalid archive")}
    if verification.get("status") == "corrupted":
        return {
            "status": "error",
            "reason": "Checksum errors — archive is corrupted",
            "checksum_errors": verification.get("checksum_errors", []),
        }

    root = repo_root or _project_root()
    sections = (
        ("orion", _section_dest("orion", root, data_dir, ownex_dir, config_dir)),
        ("ownex", _section_dest("ownex", root, data_dir, ownex_dir, config_dir)),
        ("config_ownex", _section_dest("config_ownex", root, data_dir, ownex_dir, config_dir)),
    )
    for _name, dest in sections:
        if dest is not None and dest.exists() and any(dest.iterdir()) and not force:
            return {
                "status": "error",
                "reason": (
                    f"Target directory {dest} already has data — refusing to overwrite. "
                    "Run with force=True (python run.py --migrate <file> --force) to overwrite."
                ),
            }

    # 3. Safety: never silently replace an existing vault key — keep a .bak
    key = (data_dir or _data_dir()) / "identity_vault.key"
    if key.exists() and not key.with_suffix(".key.bak").exists():
        try:
            key.rename(key.with_suffix(".key.bak"))
            logger.info("Existing vault key preserved as identity_vault.key.bak")
        except Exception as exc:
            logger.warning("Could not preserve existing vault key: %s", exc)

    try:
        with zipfile.ZipFile(path, "r") as zf:
            manifest = json.loads(zf.read(MANIFEST_NAME))
            restored = 0
            skipped: list[str] = []
            for entry in manifest.get("files", []):
                rel = entry["path"]
                prefix, _, sub = rel.partition("/")
                dest_dir = _section_dest(prefix, root, data_dir, ownex_dir, config_dir)
                if dest_dir is None:
                    skipped.append(rel)
                    continue
                target = dest_dir / sub if prefix != "env" else dest_dir / ".env"
                target.parent.mkdir(parents=True, exist_ok=True)
                try:
                    target.write_bytes(zf.read(rel))
                    restored += 1
                except Exception as exc:
                    logger.warning("Failed to restore %s: %s", rel, exc)
                    skipped.append(rel)
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}

    return {
        "status": "ok",
        "restored_files": restored,
        "skipped_files": skipped,
        "targets": {
            "orion": str(_section_dest("orion", root, data_dir, ownex_dir, config_dir)),
            "ownex": str(_section_dest("ownex", root, data_dir, ownex_dir, config_dir)),
            "config_ownex": str(_section_dest("config_ownex", root, data_dir, ownex_dir, config_dir)),
            "repo_database": str(root / "database"),
            "repo_data": str(root / "data"),
            "env": str(root / ".env"),
        },
    }
