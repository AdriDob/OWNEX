"""OWNEX Full Migration — export/import PC-a-PC en un solo comando.

Empaqueta los 6 orígenes de datos de OWNEX en un zip con manifest.json
(sha256 por archivo), con WAL checkpoint antes de leer cada *.db.

Secciones:
- orion/          → ~/.orion            (config, vault, license, DB)
- ownex/          → ~/.ownex            (estado, backups de datos)
- config_ownex/   → ~/.config/ownex     (trading.json, payment_network.json)
- repo_database/  → <repo>/database     (catseye.db)
- repo_data/      → <repo>/data         (workbank, learning, knowledge)
- env/            → <repo>/.env         (variables, sin secretos en git)

Seguridad:
- La clave de IdentityVault existente se preserva como
  `identity_vault.key.bak` ANTES de escribir (nunca se pierde).
- Destino no vacío sin force=True → error (guard anti-sobrescritura).
- Tests con destinos inyectables: JAMÁS tocan el home real.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import socket
import sqlite3
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from cores.version import OWNEX_VERSION

logger = logging.getLogger("ownex.cores.backup.migrate")

MANIFEST_NAME = "manifest.json"
README_NAME = "README_MIGRATION.txt"

# Sufijos/transients que nunca entran al zip.
_COMMON_EXCLUDED_SUFFIXES = (".pyc", "-wal", "-shm", ".pid", ".lock", ".log", ".tar.gz", ".zip")
_COMMON_EXCLUDED_NAMES = {
    "__pycache__",
    "node_modules",
    ".git",
    ".venv",
    "venv",
    "backups",
    "logs",
    "vision_cache",
}


def _data_dir() -> Path:
    """Directorio de datos del repo (respeta OWNEX_DATA_DIR)."""
    base = os.environ.get("OWNEX_DATA_DIR")
    if base:
        return Path(base)
    return Path.cwd() / "data"


def _project_root() -> Path:
    """Raíz del repo (donde vive run.py)."""
    return Path.cwd()


def _get_hw_id() -> str:
    """Hardware ID para la guía de licencia (best-effort, nunca raisea)."""
    try:
        from cores.license.hardware import get_hardware_id

        return get_hardware_id()
    except Exception:
        return "unknown"


def _checkpoint_dbs(paths: list[Path]) -> None:
    """WAL checkpoint (TRUNCATE) en cada *.db para lectura consistente."""
    for db_path in paths:
        if not db_path.exists() or db_path.suffix != ".db":
            continue
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.close()
        except Exception as exc:
            logger.warning("WAL checkpoint failed for %s: %s", db_path, exc)


def _scan_dir(base: Path, prefix: str, excludes: set[str] | None = None) -> list[dict]:
    """Escanea un directorio recursivo. Retorna [{path, size, sha256}]."""
    entries: list[dict] = []
    if not base.exists() or not base.is_dir():
        return entries
    excludes = excludes or set()
    dbs: list[Path] = []
    for root, dirs, files in os.walk(str(base)):
        rel_root = Path(root).relative_to(base)
        # Podar directorios excluidos.
        dirs[:] = [d for d in dirs if d not in _COMMON_EXCLUDED_NAMES and d not in excludes]
        for name in sorted(files):
            if name in _COMMON_EXCLUDED_NAMES or name.startswith("."):
                continue
            if name.endswith(_COMMON_EXCLUDED_SUFFIXES):
                continue
            full = Path(root) / name
            rel = str(rel_root / name) if str(rel_root) != "." else name
            try:
                entries.append(
                    {
                        "path": f"{prefix}/{rel}",
                        "size": full.stat().st_size,
                        "sha256": _sha256_file(full),
                        "_full": str(full),
                    }
                )
                if full.suffix == ".db":
                    dbs.append(full)
            except Exception as exc:
                logger.warning("Cannot read %s, skipping: %s", full, exc)
    # Checkpoint de DBs encontradas (consistencia).
    _checkpoint_dbs(dbs)
    return entries


def _sha256_file(path: Path) -> str:
    """SHA256 de un archivo."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _readme_text(manifest: dict) -> str:
    """README humano dentro del zip de migración."""
    return (
        "OWNEX MIGRATION ARCHIVE\n"
        "=======================\n"
        f"Version: {manifest.get('version')}\n"
        f"Created: {manifest.get('created_at')}\n"
        f"Source host: {manifest.get('source_hostname')}\n"
        f"Source HWID: {manifest.get('source_hwid')}\n"
        f"Files: {manifest.get('total_files')} ({manifest.get('total_size_mb')} MB)\n"
        "\n"
        "RESTORE:\n"
        "  python run.py --migrate <este-archivo.zip>\n"
        "  python run.py --migrate <archivo.zip> --force   (sobrescribir)\n"
        "\n"
        "LICENSE: la licencia está ligada al HWID de origen.\n"
        "En la PC nueva: CATEYE_PORTABLE=1 python run.py --daemon\n"
        "o reactivá la licencia en Settings con tu key.\n"
        "\n"
        "VAULT: identity_vault.key viaja en el zip; si la PC destino ya tiene\n"
        "una clave, se preserva como identity_vault.key.bak antes de escribir.\n"
    )


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
    """Exporta TODO OWNEX a un zip de migración.

    Destinos inyectables (tests usan tmp, jamás el home real).
    Retorna {status, archive_path, total_files, total_size_mb, size_mb, sections}.
    """
    home = Path.home()
    orion_dir = orion_dir or (home / ".orion")
    ownex_dir = ownex_dir or (home / ".ownex")
    config_dir = config_dir or (home / ".config" / "ownex")
    repo_root = _project_root()
    repo_database_dir = repo_database_dir or (repo_root / "database")
    repo_data_dir = repo_data_dir or (repo_root / "data")
    env_file = env_file or (repo_root / ".env")

    # Excluir targets/ (4.1G de recon) si se pide.
    orion_excludes = set() if include_targets else {"targets"}

    sections: dict[str, list[dict]] = {
        "orion": _scan_dir(orion_dir, "orion", orion_excludes),
        "ownex": _scan_dir(ownex_dir, "ownex"),
        "config_ownex": _scan_dir(config_dir, "config_ownex"),
        "repo_database": _scan_dir(repo_database_dir, "repo_database"),
        "repo_data": _scan_dir(repo_data_dir, "repo_data"),
        "env": [],
    }
    # .env como archivo suelto (sección env/).
    if env_file.exists() and env_file.is_file():
        try:
            sections["env"].append(
                {
                    "path": "env/.env",
                    "size": env_file.stat().st_size,
                    "sha256": _sha256_file(env_file),
                    "_full": str(env_file),
                }
            )
        except Exception as exc:
            logger.warning("Cannot read .env, skipping: %s", exc)

    all_files = [f for files in sections.values() for f in files]
    total_size = sum(f["size"] for f in all_files)
    manifest = {
        "tool": "ownex-migrate",
        "version": OWNEX_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "source_hostname": socket.gethostname(),
        "source_hwid": _get_hw_id(),
        "sections": {
            name: {
                "files": len(files),
                "size": sum(f["size"] for f in files),
            }
            for name, files in sections.items()
        },
        "total_files": len(all_files),
        "total_size": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "files": [{k: v for k, v in f.items() if k != "_full"} for f in all_files],
    }

    if dest is None:
        default_dir = ownex_dir / "backups"
        default_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        dest = default_dir / f"OWNEX_MIGRATE_{ts}.zip"
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(MANIFEST_NAME, json.dumps(manifest, indent=2))
            zf.writestr(README_NAME, _readme_text(manifest))
            for f in all_files:
                zf.write(f["_full"], arcname=f["path"])
        size_mb = round(dest.stat().st_size / (1024 * 1024), 2)
        logger.info("Migration exported: %s (%d files)", dest, len(all_files))
        return {
            "status": "ok",
            "archive_path": str(dest),
            "total_files": len(all_files),
            "total_size_mb": manifest["total_size_mb"],
            "size_mb": size_mb,
            "sections": manifest["sections"],
        }
    except Exception as exc:
        logger.exception("Migration export failed")
        return {"status": "error", "reason": str(exc)}


def verify_migration(archive: str | Path) -> dict:
    """Valida schema + checksums de un zip de migración.

    Retorna {status: ok|error|corrupted, manifest, total_files, checksum_errors}.
    Rechaza formatos legacy (mensaje --restore).
    """
    archive = Path(archive)
    if not archive.exists():
        return {"status": "error", "reason": f"Archive not found: {archive}"}
    try:
        with zipfile.ZipFile(archive, "r") as zf:
            names = zf.namelist()
            if MANIFEST_NAME not in names:
                # Formato legacy (backup viejo sin manifest de migración).
                return {
                    "status": "error",
                    "reason": "Not a migration archive (no manifest.json). "
                    "Si es un backup legacy, usá --restore en vez de --migrate.",
                }
            manifest = json.loads(zf.read(MANIFEST_NAME))
            if manifest.get("tool") != "ownex-migrate":
                return {"status": "error", "reason": "Unknown archive tool, refusing."}
            errors: list[str] = []
            for f in manifest.get("files", []):
                arc = f["path"]
                if arc not in names:
                    errors.append(f"missing: {arc}")
                    continue
                data = zf.read(arc)
                if hashlib.sha256(data).hexdigest() != f["sha256"]:
                    errors.append(f"checksum: {arc}")
            if errors:
                return {
                    "status": "corrupted",
                    "manifest": manifest,
                    "total_files": manifest.get("total_files", 0),
                    "checksum_errors": errors,
                }
            return {
                "status": "ok",
                "manifest": manifest,
                "total_files": manifest.get("total_files", 0),
                "checksum_errors": [],
            }
    except zipfile.BadZipFile:
        return {"status": "error", "reason": "Not a valid zip archive."}
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}


def _section_dest(
    prefix: str,
    repo_root: Path,
    data_dir: Path | None = None,
    ownex_dir: Path | None = None,
    config_dir: Path | None = None,
) -> Path | None:
    """Destino de restauración por sección (inyectable para tests)."""
    home = Path.home()
    if prefix == "orion":
        return data_dir or (home / ".orion")
    if prefix == "ownex":
        return ownex_dir or (home / ".ownex")
    if prefix == "config_ownex":
        return config_dir or (home / ".config" / "ownex")
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
    """Restaura un zip de migración.

    Guard de seguridad: destino no vacío sin force → error, nada se toca.
    La clave de IdentityVault existente se preserva como .key.bak.
    Retorna {status, restored_files, targets, skipped_files, checksum_errors}.
    """
    verification = verify_migration(archive)
    if verification.get("status") == "error":
        return {"status": "error", "reason": verification.get("reason")}
    manifest = verification.get("manifest", {})

    repo_root = Path(repo_root) if repo_root else _project_root()

    # Agrupar archivos por sección → destino.
    by_dest: dict[str, list[dict]] = {}
    for f in manifest.get("files", []):
        arc = f["path"]
        prefix = arc.split("/")[0] if "/" in arc else ""
        dest_base = _section_dest(prefix, repo_root, data_dir, ownex_dir, config_dir)
        if dest_base is None:
            continue
        rel = arc[len(prefix) + 1 :] if prefix else arc
        by_dest.setdefault(str(dest_base), []).append({**f, "_rel": rel})

    # Guard: ningún destino no vacío sin force.
    for dest_str in by_dest:
        dest_base = Path(dest_str)
        if dest_base.exists() and any(dest_base.iterdir()) and not force:
            return {
                "status": "error",
                "reason": f"Destination not empty (use --force): {dest_base}",
            }

    restored = 0
    skipped: list[str] = []
    targets: dict[str, str] = {}
    checksum_errors: list[str] = list(verification.get("checksum_errors", []))
    if checksum_errors and not force:
        return {
            "status": "error",
            "reason": "Archive has checksum errors, refusing without --force.",
            "checksum_errors": checksum_errors,
        }

    try:
        with zipfile.ZipFile(archive, "r") as zf:
            for dest_str, files in by_dest.items():
                dest_base = Path(dest_str)
                dest_base.mkdir(parents=True, exist_ok=True)
                label = dest_base.name or dest_str
                targets[label] = dest_str
                for f in files:
                    arc = f["path"]
                    if arc in checksum_errors and not force:
                        skipped.append(arc)
                        continue
                    out = dest_base / f["_rel"]
                    # Preservar clave de vault existente.
                    if out.name == "identity_vault.key" and out.exists():
                        bak = out.with_name("identity_vault.key.bak")
                        shutil.copy2(out, bak)
                    out.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(arc) as src, open(out, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                    restored += 1
        # Permisos de la clave restaurada.
        import contextlib

        for dest_str in by_dest:
            key_path = Path(dest_str) / "identity_vault.key"
            if key_path.exists():
                with contextlib.suppress(OSError):
                    os.chmod(key_path, 0o600)
        logger.info("Migration imported: %d files", restored)
        return {
            "status": "ok",
            "restored_files": restored,
            "targets": targets,
            "skipped_files": skipped,
            "checksum_errors": checksum_errors,
        }
    except Exception as exc:
        logger.exception("Migration import failed")
        return {"status": "error", "reason": str(exc)}
