"""File Manager — visualiza archivos de la PC sin duplicar.

Navega, busca y visualiza archivos directamente del sistema.
No copia ni duplica — solo presenta lo que ya existe.
"""

from __future__ import annotations

import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.file_manager")


class FileManager:
    """Gestor de archivos — visualiza sin duplicar."""

    def __init__(self, root_path: str = "") -> None:
        self._root = Path(root_path) if root_path else Path.home()

    def list_directory(self, path: str = "") -> dict[str, Any]:
        """Listar contenido de un directorio."""
        target = self._root / path if path else self._root

        if not target.exists():
            return {"error": "Path not found", "path": str(target)}

        items = []
        try:
            for item in sorted(target.iterdir()):
                stat = item.stat()
                items.append(
                    {
                        "name": item.name,
                        "path": str(item.relative_to(self._root)),
                        "is_dir": item.is_dir(),
                        "size": stat.st_size if item.is_file() else 0,
                        "size_human": self._human_size(stat.st_size) if item.is_file() else "",
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "type": mimetypes.guess_type(str(item))[0] or "directory" if item.is_dir() else "file",
                    }
                )
        except PermissionError:
            return {"error": "Permission denied", "path": str(target)}

        return {
            "path": str(target.relative_to(self._root)) if target != self._root else "",
            "full_path": str(target),
            "items": items,
            "total_files": sum(1 for i in items if not i["is_dir"]),
            "total_dirs": sum(1 for i in items if i["is_dir"]),
        }

    def _human_size(self, size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def search_files(self, query: str, path: str = "") -> list[dict[str, Any]]:
        """Buscar archivos por nombre."""
        target = self._root / path if path else self._root
        results = []

        try:
            for item in target.rglob("*"):
                if query.lower() in item.name.lower():
                    stat = item.stat()
                    results.append(
                        {
                            "name": item.name,
                            "path": str(item.relative_to(self._root)),
                            "is_dir": item.is_dir(),
                            "size": stat.st_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        }
                    )
        except Exception:
            pass

        return results[:100]

    def read_file(self, path: str) -> dict[str, Any] | None:
        """Leer contenido de archivo de texto."""
        target = self._root / path
        if not target.exists() or target.is_dir():
            return None

        try:
            content = target.read_text(encoding="utf-8")
            return {
                "path": path,
                "content": content,
                "size": target.stat().st_size,
                "modified": datetime.fromtimestamp(target.stat().st_mtime).isoformat(),
            }
        except Exception:
            return None

    def get_file_info(self, path: str) -> dict[str, Any] | None:
        """Obtener metadata de un archivo."""
        target = self._root / path
        if not target.exists():
            return None

        stat = target.stat()
        return {
            "name": target.name,
            "path": str(target.relative_to(self._root)),
            "full_path": str(target),
            "is_dir": target.is_dir(),
            "size": stat.st_size,
            "size_human": self._human_size(stat.st_size),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "type": mimetypes.guess_type(str(target))[0] or "unknown",
        }


_file_manager: FileManager | None = None


def get_file_manager(root_path: str = "") -> FileManager:
    global _file_manager
    if _file_manager is None:
        _file_manager = FileManager(root_path)
    return _file_manager
