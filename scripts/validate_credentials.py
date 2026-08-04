"""validate_credentials.py — Saca en claro qué credenciales de plataforma faltan.

Lee core/credentials/vault.py (definición) y ~/.config/ownex/opportunity.env (valores).
No imprime valores, solo estado configurado/vacío por plataforma.

Uso: python scripts/validate_credentials.py
"""

from __future__ import annotations

import re
from pathlib import Path

vault = Path("core/credentials/vault.py").read_text()
aliases = re.findall(r'alias="([A-Z0-9_]+)"', vault)

# Solo claves sensibles (no URLs)
keys = [a for a in aliases if a.endswith(("_KEY", "_TOKEN", "_SECRET", "_ID"))]

env_path = Path.home() / ".config" / "ownex" / "opportunity.env"
configured: set[str] = set()
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k = line.split("=")[0].strip()
            v = line.split("=", 1)[1].strip().strip('"').strip("'")
            if k in keys and v and not v.startswith("your_"):
                configured.add(k)

print(f"Vault define {len(keys)} claves de plataforma")
print(f"Archivo credenciales: {env_path}")
print(f"Configuradas ahora: {len(configured)}\n")

missing = [k for k in keys if k not in configured]
print("=== FALTAN (configurar) ===")
for k in sorted(missing):
    print(f"  {k}")
print(f"\nTotal faltantes: {len(missing)} de {len(keys)}")
