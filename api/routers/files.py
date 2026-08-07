"""API Router para Obsidian Sync, Sync Manager y File Manager."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger("api.files")

router = APIRouter(prefix="/api/files", tags=["files"])


# ── Obsidian Sync Manager (cross-device) ─────────────────────────


@router.get("/sync/methods")
async def sync_methods() -> dict[str, Any]:
    """Obtener métodos de sync disponibles."""
    try:
        from core.obsidian_sync_manager import get_sync_manager

        return get_sync_manager().get_all_methods()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/sync/guide/{method}")
async def sync_guide(method: str) -> dict[str, Any]:
    """Obtener guía de setup para un método de sync."""
    try:
        from core.obsidian_sync_manager import get_sync_manager

        return get_sync_manager().get_setup_guide(method)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/sync/syncthing-status")
async def syncthing_status() -> dict[str, Any]:
    """Verificar si Syncthing está instalado."""
    try:
        from core.obsidian_sync_manager import get_sync_manager

        return get_sync_manager().check_syncthing_installed()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/sync/script/{method}")
async def sync_script(method: str) -> dict[str, Any]:
    """Generar script de sync."""
    try:
        from core.obsidian_sync_manager import get_sync_manager

        manager = get_sync_manager()
        script = manager.generate_sync_script(method)
        return {"method": method, "script": script}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── Obsidian ──────────────────────────────────────────────────────


@router.get("/obsidian/status")
async def obsidian_status() -> dict[str, Any]:
    try:
        from core.obsidian_sync import get_obsidian_sync

        sync = get_obsidian_sync()
        return sync.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/obsidian/notes")
async def obsidian_notes(folder: str = "") -> dict[str, Any]:
    try:
        from core.obsidian_sync import get_obsidian_sync

        sync = get_obsidian_sync()
        notes = sync.list_notes(folder)
        return {"notes": notes, "total": len(notes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/obsidian/note/{note_path:path}")
async def obsidian_read(note_path: str) -> dict[str, Any]:
    try:
        from core.obsidian_sync import get_obsidian_sync

        sync = get_obsidian_sync()
        note = sync.read_note(note_path)
        if note:
            return note
        raise HTTPException(status_code=404, detail="Note not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/obsidian/note")
async def obsidian_create(note: dict[str, Any]) -> dict[str, Any]:
    try:
        from core.obsidian_sync import get_obsidian_sync

        sync = get_obsidian_sync()
        return sync.create_note(
            title=note.get("title", "Untitled"),
            content=note.get("content", ""),
            folder=note.get("folder", ""),
            tags=note.get("tags"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.put("/obsidian/note/{note_path:path}")
async def obsidian_update(note_path: str, note: dict[str, Any]) -> dict[str, Any]:
    try:
        from core.obsidian_sync import get_obsidian_sync

        sync = get_obsidian_sync()
        result = sync.update_note(note_path, note.get("content", ""))
        if result:
            return result
        raise HTTPException(status_code=404, detail="Note not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.delete("/obsidian/note/{note_path:path}")
async def obsidian_delete(note_path: str) -> dict[str, Any]:
    try:
        from core.obsidian_sync import get_obsidian_sync

        sync = get_obsidian_sync()
        deleted = sync.delete_note(note_path)
        return {"deleted": deleted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/obsidian/search")
async def obsidian_search(query: str) -> dict[str, Any]:
    try:
        from core.obsidian_sync import get_obsidian_sync

        sync = get_obsidian_sync()
        results = sync.search_notes(query)
        return {"results": results, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/obsidian/folders")
async def obsidian_folders() -> dict[str, Any]:
    try:
        from core.obsidian_sync import get_obsidian_sync

        sync = get_obsidian_sync()
        return {"folders": sync.get_folders()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


# ── File Manager ──────────────────────────────────────────────────


@router.get("/browse")
async def browse(path: str = "") -> dict[str, Any]:
    try:
        from core.file_manager import get_file_manager

        fm = get_file_manager()
        return fm.list_directory(path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/search")
async def file_search(query: str, path: str = "") -> dict[str, Any]:
    try:
        from core.file_manager import get_file_manager

        fm = get_file_manager()
        results = fm.search_files(query, path)
        return {"results": results, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/info/{file_path:path}")
async def file_info(file_path: str) -> dict[str, Any]:
    try:
        from core.file_manager import get_file_manager

        fm = get_file_manager()
        info = fm.get_file_info(file_path)
        if info:
            return info
        raise HTTPException(status_code=404, detail="File not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/read/{file_path:path}")
async def file_read(file_path: str) -> dict[str, Any]:
    try:
        from core.file_manager import get_file_manager

        fm = get_file_manager()
        content = fm.read_file(file_path)
        if content:
            return content
        raise HTTPException(status_code=404, detail="File not found or not readable")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
