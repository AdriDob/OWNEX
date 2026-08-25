"""Guardián anti-filtración: ningún archivo TRACKED contiene JWTs reales.

Incidente 2026-08-25 (0b64ae8b): backups/orion.log entró al índice con 3
session-JWTs (expiraban en 24h, scope localhost). Removido del árbol, pero
este test convierte la higiene en contrato permanente.

Alcance: solo archivos trackeados por git (los locales/untracked no son
superficie de filtración vía repo). Excluye tests y fixtures donde un JWT
de ejemplo es legítimo.
"""

from __future__ import annotations

import re
import subprocess

# Triple segmento base64url = JWT real (header.payload.signature).
JWT_PATTERN = re.compile(rb"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")

EXCLUDED_PREFIXES = (
    "tests/",
    "docs/archived/",
    # Binarios/artefactos: los eyJ embebidos son JSON genérico, no tokens.
    # (verificado en release audit: 0 JWTs triple-segmento en MSI/NSIS)
)


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [f for f in out.splitlines() if f and not f.startswith(EXCLUDED_PREFIXES)]


def test_no_tracked_file_contains_real_jwt() -> None:
    """Ningún archivo commiteado debe contener un JWT triple-segmento."""
    offenders: list[str] = []
    for path in _tracked_files():
        try:
            data = open(path, "rb").read()
        except OSError:
            continue
        if JWT_PATTERN.search(data):
            offenders.append(path)
    assert not offenders, (
        f"JWT(s) real(es) commiteado(s) en: {offenders}. "
        "Rotá/invalidá las sesiones, remové el archivo (git rm --cached + "
        ".gitignore) y considerá purga de historial si el token sigue vigente."
    )


def test_backups_dir_is_ignored() -> None:
    """backups/ (logs runtime con sesiones) debe seguir fuera del árbol."""
    gitignore = open(".gitignore", encoding="utf-8").read()
    assert re.search(r"^backups/?$", gitignore, re.MULTILINE), (
        ".gitignore perdió la regla de backups/ — los logs runtime contienen sesiones y no deben volver al árbol."
    )
