"""Obsidian Sync Manager — gestiona sincronización entre dispositivos.

Opciones soportadas:
- Syncthing (recomendado, gratis, P2P)
- Git (gratis, técnico)
- Cloud storage (Google Drive, Dropbox, etc.)
- Remotely Save (plugin de Obsidian)
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger("orion.obsidian_sync_manager")


class ObsidianSyncManager:
    """Gestiona la sincronización de Obsidian entre dispositivos."""

    SYNC_METHODS = {
        "syncthing": {
            "name": "Syncthing",
            "description": "Sincronización P2P directa entre dispositivos. Sin nube, sin límite.",
            "cost": "Gratis",
            "difficulty": "Fácil",
            "speed": "Muy rápida (WiFi local)",
            "setup_url": "https://syncthing.net",
            "android_app": "Syncthing (F-Droid/Play Store)",
            "ios_app": "Móbil (pago único)",
        },
        "git": {
            "name": "Git",
            "description": "Sincronización vía repositorio Git. Manual (commit/push/pull).",
            "cost": "Gratis",
            "difficulty": "Media",
            "speed": "Manual",
            "setup_url": "https://git-scm.com",
        },
        "google_drive": {
            "name": "Google Drive",
            "description": "Sincronización vía carpeta de Google Drive.",
            "cost": "Gratis 15GB",
            "difficulty": "Fácil",
            "speed": "Nube",
            "setup_url": "https://drive.google.com",
        },
        "remotely_save": {
            "name": "Remotely Save",
            "description": "Plugin de Obsidian para sync con S3, Dropbox, OneDrive, etc.",
            "cost": "Gratis",
            "difficulty": "Fácil",
            "speed": "Nube",
            "setup_url": "https://github.com/remotely-save/remotely-save",
        },
    }

    def __init__(self, vault_path: str = "") -> None:
        self._vault_path = Path(vault_path) if vault_path else self._detect_vault()

    def _detect_vault(self) -> Path:
        """Detectar vault de Obsidian."""
        possible = [
            Path.home() / "Documents" / "Obsidian",
            Path.home() / "Obsidian",
            Path.home() / "notes",
        ]
        for p in possible:
            if (p / ".obsidian").exists():
                return p
        return Path.home() / "Documents" / "Obsidian"

    def get_setup_guide(self, method: str) -> dict[str, Any]:
        """Obtener guía de setup para un método de sync."""
        method = method.lower()
        if method not in self.SYNC_METHODS:
            return {"error": f"Método no soportado: {method}"}

        info = self.SYNC_METHODS[method]
        vault = str(self._vault_path)

        guides = {
            "syncthing": {
                **info,
                "steps_pc": [
                    "1. Descargar Syncthing de https://syncthing.net",
                    "2. Instalar y abrir Syncthing",
                    "3. Click 'Agregar carpeta'",
                    f"   - Ruta: {vault}",
                    "   - Etiqueta: Obsidian Vault",
                    "4. Copiar el Device ID (está en la esquina superior derecha)",
                    "5. Dejar Syncthing corriendo en background",
                ],
                "steps_android": [
                    "1. Instalar 'Syncthing' de F-Droid (recomendado) o Play Store",
                    "2. Abrir Syncthing en el celular",
                    "3. Click '+' → 'Agregar dispositivo'",
                    "   - Pegar el Device ID de la PC",
                    "4. Click '+' → 'Agregar carpeta'",
                    "   - Ruta: /storage/emulated/0/Obsidian (o donde tengas el vault)",
                    "5. Aceptar la solicitud de conexión en la PC",
                    "6. ¡Listo! Los cambios se sincronizan automáticamente",
                ],
                "tips": [
                    "Ambos dispositivos deben estar en la misma red WiFi para sync inicial",
                    "Después puede sync por internet si configuran relay",
                    "Syncthing corre en background — no necesitas abrirlo cada vez",
                    "Los cambios se detectan en segundos",
                ],
            },
            "git": {
                **info,
                "steps_pc": [
                    f"1. cd {vault}",
                    "2. git init",
                    "3. git add .",
                    "4. git commit -m 'Initial commit'",
                    "5. Crear repo en GitHub/GitLab (privado)",
                    "6. git remote add origin <url>",
                    "7. git push -u origin main",
                    "",
                    "Para sync: git pull && git add . && git commit -m 'sync' && git push",
                ],
                "steps_android": [
                    "1. Instalar 'Termux' de F-Droid",
                    "2. pkg install git",
                    "3. git clone <url-del-repo>",
                    "4. Para sync: cd vault && git pull",
                    "5. Después de editar: git add . && git commit && git push",
                ],
                "tips": [
                    "Más técnico pero muy confiable",
                    "Podés usar scripts para automatizar commit/push/pull",
                    "Ideal si ya usás Git",
                ],
            },
            "google_drive": {
                **info,
                "steps_pc": [
                    "1. Instalar Google Drive para desktop",
                    f"2. Mover vault a: {Path.home() / 'Google Drive' / 'Obsidian'}",
                    "3. Google Drive sincroniza automáticamente",
                ],
                "steps_android": [
                    "1. Instalar Obsidian de Play Store",
                    "2. Abrir Obsidian → Crear nuevo vault",
                    "3. Elegir 'Google Drive' como ubicación",
                    "4. Seleccionar la misma carpeta que en PC",
                ],
                "tips": [
                    "15GB gratis (compartido con Gmail y Fotos)",
                    "Sincronización vía nube — necesita internet",
                    "Simple pero depende de Google",
                ],
            },
            "remotely_save": {
                **info,
                "steps_pc": [
                    "1. Abrir Obsidian → Settings → Community plugins",
                    "2. Buscar 'Remotely Save' e instalar",
                    "3. Configurar: elegir servicio (S3, Dropbox, OneDrive, WebDAV)",
                    "4. Configurar credenciales del servicio",
                    "5. Configurar auto-sync cada X minutos",
                ],
                "steps_android": [
                    "1. Mismo proceso en Obsidian mobile",
                    "2. Instalar 'Remotely Save'",
                    "3. Misma configuración que en PC",
                ],
                "tips": [
                    "Más flexible — funciona con muchos servicios",
                    "Auto-sync configurable",
                    "Requiere configurar un servicio de nube",
                ],
            },
        }

        return guides.get(method, {"error": "Guía no disponible"})

    def check_syncthing_installed(self) -> dict[str, Any]:
        """Verificar si Syncthing está instalado."""
        try:
            result = subprocess.run(
                ["syncthing", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return {
                    "installed": True,
                    "version": result.stdout.strip(),
                    "message": "Syncthing está instalado",
                }
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return {
            "installed": False,
            "message": "Syncthing no está instalado",
            "install_url": "https://syncthing.net/downloads/",
        }

    def get_all_methods(self) -> dict[str, Any]:
        """Obtener todos los métodos de sync disponibles."""
        return {
            "methods": self.SYNC_METHODS,
            "recommended": "syncthing",
            "vault_path": str(self._vault_path),
        }

    def generate_sync_script(self, method: str) -> str:
        """Generar script de sync para el método elegido."""
        if method == "git":
            return f"""#!/bin/bash
# Obsidian Git Sync Script
cd "{self._vault_path}"
git pull
git add .
git commit -m "sync: $(date '+%Y-%m-%d %H:%M')"
git push
echo "✅ Sync completado"
"""
        elif method == "syncthing":
            return "# Syncthing no necesita script — sincronización automática P2P"
        return "# Script no disponible para este método"


_manager: ObsidianSyncManager | None = None


def get_sync_manager(vault_path: str = "") -> ObsidianSyncManager:
    """Get singleton ObsidianSyncManager."""
    global _manager
    if _manager is None:
        _manager = ObsidianSyncManager(vault_path)
    return _manager
