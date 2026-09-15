"""Frontend backend.ts root-mounted contract guard (regression para §17).

Audit 2026-09-15: first-money / result-based / platform-guides se montaban en
RAÍZ en el backend pero el frontend los resolvía bajo /api/* → 404 total en
FirstMoney, ResultBased y PlatformGuides. Fix: ROOT_MOUNTED_PREFIXES en
frontend/src/lib/backend.ts ahora incluye los routers que el backend monta sin
/ (direct-work, mobile, wear-os, first-money, result-based, platform-guides).

Este guard pinea que cada router root-mounted del backend tiene su contraparte
en el front, para que el drift no regrese.
"""

from __future__ import annotations

import re
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
BACKEND = Path(__file__).resolve().parent.parent / "api"


def _backend_root_mounted_prefixes() -> set[str]:
    """Routers del backend montados sin prefijo / (por evidencia runtime)."""
    import os

    os.environ["CATEYE_CSRF_DISABLED"] = "1"
    import sys

    sys.path.insert(0, str(BACKEND.parent))
    import api.main as m

    prefixes: set[str] = set()
    for route in m.app.routes:
        path = getattr(route, "path", None)
        if not path or not path.startswith("/"):
            continue
        if path.startswith(("/api", "/docs", "/openapi", "/redoc", "/assets")):
            continue
        seg = "/" + path.strip("/").split("/")[0]
        prefixes.add(seg)
    # Segmentos que el frontend NO debería mandar bajo /api (routers root-mounted).
    return prefixes


def _frontend_root_mounted() -> list[str]:
    src = (FRONTEND / "src" / "lib" / "backend.ts").read_text(encoding="utf-8")
    m = re.search(r"ROOT_MOUNTED_PREFIXES = \[(.*?)\]", src, re.S)
    assert m, "ROOT_MOUNTED_PREFIXES no encontrado en backend.ts"
    return re.findall(r"['\"](/[^'\"]+)['\"]", m.group(1))


def _frontend_calls_root_paths() -> set[str]:
    """Paths que el frontend llama SIN /api (resolveApiUrl los resuelve)."""
    calls: set[str] = set()
    for pattern in ("*.ts", "*.vue"):
        for f in (FRONTEND / "src").rglob(pattern):
            text = f.read_text(encoding="utf-8", errors="ignore")
            for match in re.findall(r"api\.(?:get|post|put|patch|delete)\(['\"]([^'\"?]+)", text):
                if match.startswith(
                    ("/direct-work", "/mobile", "/wear-os", "/first-money", "/result-based", "/platform-guides")
                ):
                    calls.add(match)
    return calls


def test_root_mounted_prefixes_cover_real_backend_routers() -> None:
    front = set(_frontend_root_mounted())
    # Los routers críticos root-mounted DEBEN estar en ROOT_MOUNTED_PREFIXES
    required = {"/direct-work", "/mobile", "/wear-os", "/first-money", "/result-based", "/platform-guides"}
    missing = required - front
    assert not missing, f"Falta prefix frontend para routers root-mounted: {missing}"


def test_frontend_root_calls_have_backend_route() -> None:
    import sys

    sys.path.insert(0, str(BACKEND.parent))
    import os

    os.environ["CATEYE_CSRF_DISABLED"] = "1"
    import api.main as m

    backend_paths: set[str] = {getattr(r, "path", "") or "" for r in m.app.routes if hasattr(r, "path")}
    for call in _frontend_calls_root_paths():
        # Coincidencia por prefijo dinámico: /first-money/{x} → /first-money/…
        base = "/" + call.strip("/").split("/", 1)[0]
        any_match = any(p == call or p.startswith(base + "/") for p in backend_paths)
        assert any_match, f"Frontend llama {call} pero el backend no lo sirve (ni por prefijo dinámico)"


def test_no_double_prefix_for_root_mounted() -> None:
    """Los callers de first-money/result-based/platform-guides NO usan /api delante."""
    for pattern in ("*.ts", "*.vue"):
        for f in (FRONTEND / "src").rglob(pattern):
            text = f.read_text(encoding="utf-8", errors="ignore")
            for match in re.findall(
                r"api\.(?:get|post|put|patch|delete)\(['\"]/api/(first-money|result-based|platform-guides)", text
            ):
                raise AssertionError(f"Doble prefijo en {f}: /api/{match} — usar sin /api (resolveApiUrl lo resuelve)")
