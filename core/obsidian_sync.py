"""Obsidian Sync — sincronización bidireccional con vault de Obsidian.

Obsidian guarda notas como archivos .md en una carpeta (vault).
OWNEX lee y escribe directamente en esa carpeta — NO duplica archivos.
Sincronización bidireccional en tiempo real.

Características:
- Lee notas existentes de Obsidian
- Crea nuevas notas desde OWNEX
- Actualiza notas existentes
- Bidireccional: cambios en Obsidian se reflejan en OWNEX y viceversa
- 100% gratis — no requiere servicios pagos de Obsidian
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.obsidian_sync")


class ObsidianSync:
    """Sincronización bidireccional con vault de Obsidian."""

    def __init__(self, vault_path: str = "") -> None:
        self._vault_path = Path(vault_path) if vault_path else self._detect_vault()
        self._notes_cache: dict[str, dict[str, Any]] = {}
        self._last_sync: datetime | None = None

    def _detect_vault(self) -> Path:
        """Detectar automáticamente el vault de Obsidian."""
        # Common vault locations
        possible_paths = [
            Path.home() / "Documents" / "Obsidian",
            Path.home() / "Obsidian",
            Path.home() / "notes",
            Path.home() / "Documents" / "notes",
            Path.home() / "vault",
        ]

        # Check for .obsidian config folder (indicates vault root)
        for path in possible_paths:
            if (path / ".obsidian").exists():
                return path

        # Default to Documents/Obsidian if not found
        default = Path.home() / "Documents" / "Obsidian"
        default.mkdir(parents=True, exist_ok=True)
        return default

    @property
    def vault_path(self) -> Path:
        return self._vault_path

    @property
    def is_connected(self) -> bool:
        return self._vault_path.exists() and self._vault_path.is_dir()

    # ── Lectura ──────────────────────────────────────────────────

    def list_notes(self, folder: str = "") -> list[dict[str, Any]]:
        """Listar todas las notas del vault."""
        notes = []
        search_path = self._vault_path / folder if folder else self._vault_path

        if not search_path.exists():
            return []

        for md_file in search_path.rglob("*.md"):
            try:
                note = self._parse_note(md_file)
                if note:
                    notes.append(note)
            except Exception as e:
                logger.debug("Error leyendo %s: %s", md_file, e)

        return sorted(notes, key=lambda n: n.get("modified", ""), reverse=True)

    def _parse_note(self, file_path: Path) -> dict[str, Any] | None:
        """Parsear un archivo Markdown y extraer metadata."""
        try:
            content = file_path.read_text(encoding="utf-8")

            # Extraer frontmatter YAML si existe
            frontmatter = {}
            if content.startswith("---"):
                end = content.find("---", 3)
                if end != -1:
                    fm_text = content[3:end].strip()
                    for line in fm_text.split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            frontmatter[key.strip()] = value.strip()

            # Calcular stats
            words = len(content.split())
            lines = len(content.split("\n"))

            # Ruta relativa al vault
            rel_path = file_path.relative_to(self._vault_path)

            return {
                "filename": file_path.name,
                "path": str(rel_path),
                "full_path": str(file_path),
                "folder": str(rel_path.parent) if rel_path.parent != Path(".") else "",
                "title": frontmatter.get("title", file_path.stem),
                "tags": frontmatter.get("tags", "").split(",") if "tags" in frontmatter else [],
                "created": frontmatter.get("created", datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()),
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                "words": words,
                "lines": lines,
                "size_kb": round(file_path.stat().st_size / 1024, 1),
                "frontmatter": frontmatter,
                "preview": content[:200].replace("\n", " ") + "...",
            }
        except Exception:
            return None

    def read_note(self, path: str) -> dict[str, Any] | None:
        """Leer el contenido completo de una nota."""
        file_path = self._vault_path / path
        if not file_path.exists() or file_path.suffix != ".md":
            return None

        content = file_path.read_text(encoding="utf-8")
        return {
            "path": path,
            "filename": file_path.name,
            "content": content,
            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
        }

    # ── Escritura ─────────────────────────────────────────────────

    def create_note(
        self,
        title: str,
        content: str,
        folder: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Crear una nueva nota en el vault."""
        # Sanitizar nombre de archivo
        safe_title = re.sub(r'[<>:"/\\|?*]', "_", title)
        folder_path = self._vault_path / folder if folder else self._vault_path
        folder_path.mkdir(parents=True, exist_ok=True)

        file_path = folder_path / f"{safe_title}.md"

        # Construir frontmatter
        frontmatter = {
            "title": title,
            "created": datetime.now(UTC).strftime("%Y-%m-%d %H:%M"),
            "tags": ", ".join(tags) if tags else "",
        }

        # Construir contenido
        fm_lines = ["---"]
        for key, value in frontmatter.items():
            if value:
                fm_lines.append(f"{key}: {value}")
        fm_lines.append("---")
        fm_lines.append("")
        fm_lines.append(content)

        full_content = "\n".join(fm_lines)

        file_path.write_text(full_content, encoding="utf-8")

        return {
            "created": True,
            "path": str(file_path.relative_to(self._vault_path)),
            "full_path": str(file_path),
            "title": title,
        }

    def update_note(self, path: str, content: str) -> dict[str, Any] | None:
        """Actualizar el contenido de una nota existente."""
        file_path = self._vault_path / path
        if not file_path.exists():
            return None

        # Preservar frontmatter si existe
        existing = file_path.read_text(encoding="utf-8")
        if existing.startswith("---"):
            end = existing.find("---", 3)
            if end != -1:
                frontmatter = existing[: end + 3]
                new_content = f"{frontmatter}\n\n{content}"
            else:
                new_content = content
        else:
            new_content = content

        file_path.write_text(new_content, encoding="utf-8")

        return {
            "updated": True,
            "path": path,
            "modified": datetime.now(UTC).isoformat(),
        }

    def delete_note(self, path: str) -> bool:
        """Eliminar una nota."""
        file_path = self._vault_path / path
        if file_path.exists() and file_path.suffix == ".md":
            file_path.unlink()
            return True
        return False

    def search_notes(self, query: str) -> list[dict[str, Any]]:
        """Buscar notas por contenido o título."""
        results = []
        for note in self.list_notes():
            if query.lower() in note.get("title", "").lower() or query.lower() in note.get("preview", "").lower():
                results.append(note)
        return results

    def get_folders(self) -> list[str]:
        """Obtener lista de carpetas del vault."""
        folders = set()
        for item in self._vault_path.iterdir():
            if item.is_dir() and not item.name.startswith(".") and item.name != ".obsidian":
                folders.add(item.name)
        return sorted(folders)

    def get_stats(self) -> dict[str, Any]:
        """Obtener estadísticas del vault."""
        notes = self.list_notes()
        total_words = sum(n.get("words", 0) for n in notes)
        total_size = sum(n.get("size_kb", 0) for n in notes)

        return {
            "vault_path": str(self._vault_path),
            "total_notes": len(notes),
            "total_words": total_words,
            "total_size_kb": round(total_size, 1),
            "folders": len(self.get_folders()),
            "connected": self.is_connected,
        }


# ── Singleton ─────────────────────────────────────────────────────

_obsidian: ObsidianSync | None = None


def get_obsidian_sync(vault_path: str = "") -> ObsidianSync:
    """Get singleton ObsidianSync."""
    global _obsidian
    if _obsidian is None:
        _obsidian = ObsidianSync(vault_path)
    return _obsidian
