#!/usr/bin/env python3
# sync_version.py — Sincroniza la versión desde .VERSION.txt a todos los archivos del proyecto.
# One Source of Truth: .VERSION.txt es la única autoridad.
# Ejecutar después de cualquier cambio de versión manual o CI.

import re

with open(".VERSION.txt", encoding="utf-8") as f:
    VERSION = f.read().strip()
changed = False


def sync(filepath, pattern, replacement):
    """Busca un patrón de versión en el archivo y lo reemplaza si es distinto."""
    global changed
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    new_content = re.sub(pattern, replacement, content)
    if new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        changed = True
        print(f"  actualizado: {filepath}")


# 1. pyproject.toml  —  version = "7.0.0"
sync(
    "pyproject.toml",
    r'version = ["\']\d+\.\d+\.\d+["\']',
    f'version = "{VERSION}"',
)

# 2. package.json  —  "version": "7.0.0"
sync(
    "package.json",
    r'"version": "\d+\.\d+\.\d+"',
    f'"version": "{VERSION}"',
)

# 3. core/__init__.py  —  __version__ = "7.0.0"
sync(
    "core/__init__.py",
    r'__version__ = ["\']\d+\.\d+\.\d+["\']',
    f'__version__ = "{VERSION}"',
)

# 4. .ai/SESSION_CHECKPOINT.md  —  actualizar el número de versión (sin truncar el resto de la línea)
sync(
    ".ai/SESSION_CHECKPOINT.md",
    r"v\d+\.\d+\.\d+",
    f"v{VERSION}",
)

# 5. VERSION (raíz) — leído por api/main.py para /api/version y el bundle
sync(
    "VERSION",
    r"\d+\.\d+\.\d+",
    VERSION,
)

# 5b. VERSION.txt — duplicate SSOT file kept in sync
sync(
    "VERSION.txt",
    r"\d+\.\d+\.\d+",
    VERSION,
)

# 5c. core/version.py — legacy core twin re-export
sync(
    "core/version.py",
    r'__version__ = ["\']\d+\.\d+\.\d+["\']',
    f'__version__ = "{VERSION}"',
)

# 6. frontend/package.json — workspace del frontend
sync(
    "frontend/package.json",
    r'"version": "\d+\.\d+\.\d+"',
    f'"version": "{VERSION}"',
)

# 7. src-tauri/tauri.conf.json — versión del bundle MSI/NSIS
sync(
    "src-tauri/tauri.conf.json",
    r'"version": "\d+\.\d+\.\d+"',
    f'"version": "{VERSION}"',
)

# 8. src-tauri/Cargo.toml — versión del crate
# NOTA: el patrón está anclado a inicio de línea y el archivo NO empieza con
# "version", así que requiere el flag re.MULTILINE — sin él el sync nunca
# matcheaba y Cargo.toml quedaba desincronizado (bug silencioso).
sync(
    "src-tauri/Cargo.toml",
    r'(?m)^version = ["\']\d+\.\d+\.\d+["\']',
    f'version = "{VERSION}"',
)

# 9. cores/version.py — OWNEX_VERSION (consumido por /api/stability/status)
sync(
    "cores/version.py",
    r'OWNEX_VERSION = ["\']\d+\.\d+\.\d+["\']',
    f'OWNEX_VERSION = "{VERSION}"',
)

# 10. apps/*/manifest.py — version="7.x" de cada app (IAppPlugin)
for _app in ("aegis", "atlas", "cateye", "forge", "hermes", "odyssey", "pulse", "vault"):
    sync(
        f"apps/{_app}/manifest.py",
        r'version=["\']\d+\.\d+\.\d+["\']',
        f'version="{VERSION}"',
    )

# 11. installer/OWNEX-Desktop-Alpha.nsi — instalador legacy Gen2
# El NSI usa tres defines (MAJOR/MINOR/BUILD); se sincronizan por partes.
_nsi_major, _nsi_minor, _nsi_build = VERSION.split(".")
sync(
    "installer/OWNEX-Desktop-Alpha.nsi",
    r"!define VERSIONMAJOR \d+",
    f"!define VERSIONMAJOR {_nsi_major}",
)
sync(
    "installer/OWNEX-Desktop-Alpha.nsi",
    r"!define VERSIONMINOR \d+",
    f"!define VERSIONMINOR {_nsi_minor}",
)
sync(
    "installer/OWNEX-Desktop-Alpha.nsi",
    r"!define VERSIONBUILD \d+",
    f"!define VERSIONBUILD {_nsi_build}",
)

if changed:
    print(f"✅ Version {VERSION} sincronizada en los archivos del proyecto.")
else:
    print(f"⚠️ No se detectaron diferencias — todos los archivos ya tienen version {VERSION}.")

# Verificación final: asegurar que .VERSION.txt tenga el contenido correcto
with open(".VERSION.txt", encoding="utf-8") as f:
    assert f.read().strip() == VERSION, "ERROR: .VERSION.txt desactualizada"
print(f"✅ .VERSION.txt confirmada como {VERSION}")
