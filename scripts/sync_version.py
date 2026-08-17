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
    r'\$1"7\.0\.0",',
    '"7.0.0",',
)

# 3. core/__init__.py  —  __version__ = "7.0.0"
sync(
    "core/__init__.py",
    r'__version__ = ["\']\d+\.\d+\.\d+["\']',
    f'__version__ = "{VERSION}"',
)

# 4. .ai/SESSION_CHECKPOINT.md  —  actualizar la línea de version
sync(
    ".ai/SESSION_CHECKPOINT.md",
    r"(v\d+\.\d+\.\d+)[^\n]*",
    f"v{VERSION} STABLE",
)

if changed:
    print(f"✅ Version {VERSION} sincronizada en 5 archivos del proyecto.")
else:
    print(f"⚠️ No se detectaron diferencias — todos los archivos ya tienen version {VERSION}.")

# Verificación final: asegurar que .VERSION.txt tenga el contenido correcto
with open(".VERSION.txt", encoding="utf-8") as f:
    assert f.read().strip() == VERSION, "ERROR: .VERSION.txt desactualizada"
print(f"✅ .VERSION.txt confirmada como {VERSION}")
