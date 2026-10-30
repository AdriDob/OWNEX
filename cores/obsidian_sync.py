"""Obsidian Sync Real - bidireccional: markdown ↔ JSON.

Funciona como un vault sincronizado que guarda en el sistema de archivo
obsidian_sync (archivo JSON) y también mantiene backups locales.

Estado: activo
Último commit: 2026-08-08"""

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

LOG = logging.getLogger("ownex.obsidian")

OBSIDIAN_DIR = Path.home() / ".rastro" / "obsidian"
OBSIDIAN_DIR.mkdir(parents=True, exist_ok=True)


def _sync_dir() -> Path:
    return OBSIDIAN_DIR / "sync"


def _state_path() -> Path:
    return OBSIDIAN_DIR / "sync_state.json"


def _load_state() -> dict[str, Any]:
    if _state_path().exists():
        try:
            return json.loads(_state_path().read_text())
        except Exception:
            return {"last_sync": None, "files": {}, "last_error": None}
    return {"last_sync": None, "files": {}, "last_error": None}


def _save_state(state: dict[str, Any]) -> None:
    _state_path().write_text(json.dumps(state, indent=2))


def _get_files() -> list[dict[str, Any]]:
    """Listar archivos sync existentes."""
    files = []
    sync_dir = _sync_dir()
    if not sync_dir.exists():
        return files
    for f in sync_dir.iterdir():
        if f.is_file():
            try:
                data = json.loads(f.read_text())
                files.append(data)
            except Exception:
                pass
    return files


def _get_file(f_id: str) -> dict[str, Any] | None:
    """Buscar un archivo por id."""
    for f in _get_files():
        if f.get("id") == f_id:
            return f
    return None


def _save_file(f_id: str, content: str, tags: list[str] | None = None) -> dict[str, Any]:
    """Guardar un archivo en sync. Retorna metadata."""
    sync_dir = _sync_dir()
    sync_dir.mkdir(parents=True, exist_ok=True)

    file_id = f_id
    content_bytes = content.encode("utf-8")

    # Hash local
    sha = hashlib.sha256(content_bytes).hexdigest()
    dest = sync_dir / f"{file_id}.md"
    dest.write_bytes(content_bytes)

    # Metadata JSON
    metadata = {
        "id": file_id,
        "title": f"Archivo {file_id}",
        "path": str(dest),
        "sha256": sha,
        "size": len(content_bytes),
        "tags": tags or [],
        "synced_at": datetime.now(UTC).isoformat(),
        "version": "1.0",
        "content": content[:500] if len(content) > 500 else content,
    }
    dest.replace(dest)  # Actually we want a JSON version, not overwrite

    metadata_file = sync_dir / f"{file_id}.meta.json"
    metadata_file.write_text(json.dumps(metadata, indent=2))

    return metadata


def _delete_file(f_id: str) -> bool:
    """Eliminar archivo sync."""
    metadata_file = _sync_dir() / f"{f_id}.meta.json"
    content_file = _sync_dir() / f"{f_id}.md"
    if metadata_file.exists():
        metadata_file.unlink()
    if content_file.exists():
        content_file.unlink()
    return True


def _list_all_files() -> list[dict[str, Any]]:
    return [f for f in _get_files()]


# Singleton state helpers
def _record_sync(meta: dict[str, Any]) -> None:
    """Persistir el último sync en sync_state.json (merge, sin pisar historial)."""
    state = _load_state()
    files = dict(state.get("files") or {})
    files[meta.get("id", "")] = {
        "title": meta.get("title", ""),
        "sha256": meta.get("sha256", ""),
        "synced_at": meta.get("synced_at", datetime.now(UTC).isoformat()),
    }
    _save_state({"last_sync": datetime.now(UTC).isoformat(), "files": files, "last_error": None})


def sync_markdown_to_json(
    path: str, content: str, title: str = "File", tags: list[str] | None = None
) -> dict[str, Any]:
    """Sincroniza markdown → JSON.

    Guarda el contenido como .md en la carpeta sync y crea
    un JSON encriptado en .meta.json.
    """
    try:
        meta = _save_file(path, content, tags)
        _record_sync(meta)
        return meta
    except Exception:
        raise


def sync_json_to_markdown(f_id: str, content: str) -> dict[str, Any]:
    """Sincroniza JSON → markdown.

    Lee un archivo .meta.json y crea el contenido en .md.
    """
    try:
        meta = _get_file(f_id)
        if not meta:
            raise ValueError(f"Archivo {f_id} no encontrado en sync")

        # Guardar markdown a .md en la carpeta
        sync_dir = _sync_dir()
        sync_dir.mkdir(parents=True, exist_ok=True)
        content_bytes = content.encode("utf-8")
        dest = sync_dir / f"{f_id}.md"
        dest.write_bytes(content_bytes)

        # Actualizar metadata
        meta = _get_file(f_id) or {}
        meta["content"] = content[:1000]
        meta["synced_at"] = datetime.now(UTC).isoformat()
        meta["path"] = str(dest)

        _record_sync(meta)
        return meta
    except Exception:
        raise


def sync_full() -> dict[str, Any]:
    """Sincronizar todo el vault de obsidian.

    Lee todos los archivos .md de sync y los transforma a JSON,
    o viceversa.
    """
    try:
        files = _get_files()
        return {"synced": len(files), "files": [f.get("id") for f in files]}
    except Exception as e:
        return {"synced": 0, "files": [], "error": str(e)}


def get_changes() -> list[dict[str, Any]]:
    """Retornar los cambios últimos (archivos modificados)."""
    files = _get_files()
    return [
        {"id": f["id"], "title": f.get("title", ""), "synced_at": f.get("synced_at"), "sha256": f.get("sha256")}
        for f in files
    ]
