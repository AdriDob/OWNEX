"""API Router for Obsidian Sync."""

from typing import Any

from fastapi import APIRouter

from core.obsidian_sync import (
    _delete_file,
    _list_all_files,
    _load_state,
    sync_full,
    sync_markdown_to_json,
)

router = APIRouter(prefix="/api/obsidian", tags=["obsidian"])


@router.get("/files")
def list_obsidian_files():
    """List all files in the Obsidian sync vault."""
    return {"files": _list_all_files()}


@router.post("/sync")
def sync_obsidian_file(req: dict[str, Any]):
    """Sincronizar un archivo markdown → JSON."""
    path = req.get("path") or req.get("f_id")
    if not path:
        return {"success": False, "error": "Se requiere 'path' (id del archivo)"}
    return {
        "success": True,
        "result": sync_markdown_to_json(path, req.get("content", ""), req.get("title", "File"), req.get("tags")),
    }


@router.post("/sync/all")
def sync_all_obsidian():
    """Sincronizar todo el vault."""
    return sync_full()


@router.post("/delete/{file_id}")
def delete_obsidian_file(file_id: str):
    """Eliminar archivo."""
    return {"deleted": _delete_file(file_id)}


@router.get("/state")
def obsidian_state():
    """Devolver estado de sync."""
    return _load_state()


@router.post("/sync/force")
def sync_obsidian_force():
    """Forzar sincronización completa."""
    return sync_full()
