#!/usr/bin/env python3
"""
OWNEX — Pre-flight check para trabajo diario.

Ejecuta este script antes de empezar a trabajar para verificar que todo el
sistema está operativo. No modifica nada, solo lee estado.

Uso:
    python scripts/daily_check.py
"""

from __future__ import annotations

import json
import sys
import urllib.request
from typing import Any

BASE = "http://127.0.0.1:8000"


def _get(path: str) -> tuple[int, Any, str]:
    try:
        with urllib.request.urlopen(BASE + path, timeout=10) as resp:  # noqa: S310
            body = resp.read().decode("utf-8", "replace")
            try:
                return resp.status, json.loads(body), ""
            except json.JSONDecodeError:
                return resp.status, None, body[:120]
    except Exception as exc:  # noqa: BLE001
        return 0, None, str(exc)[:120]


def main() -> int:
    print("=" * 60)
    print("OWNEX — PRE-FLIGHT CHECK (trabajo diario)")
    print("=" * 60)

    checks: list[tuple[str, bool, str]] = []

    # ── 1. Backend vivo ──
    status, data, err = _get("/api/health")
    ok = status == 200 and data and data.get("status") == "ok"
    checks.append(("Backend API responde", ok, err or (data or {}).get("status", "")))

    # ── 2. Salud global ──
    status, data, err = _get("/api/system/health")
    ok = status == 200
    msg = ""
    if data:
        score = data.get("score", "N/A")
        sstatus = data.get("status", "N/A")
        msg = f"score={score}, estado={sstatus}"
    checks.append(("Salud del sistema", ok, err or msg))

    # ── 3. Sesiones (autoguardado) ──
    status, data, err = _get("/api/session/status")
    ok = status == 200 and data and data.get("success") is not None
    has_session = data.get("has_active_session") if data else False
    checks.append(
        (
            "Sistema de sesiones (autoguardado)",
            ok,
            err or (f"sesión activa: {'sí' if has_session else 'no'}" if data else ""),
        )
    )

    # ── 4. Métricas del sistema ──
    status, data, err = _get("/api/system/health/metrics")
    ok = status == 200
    mem = ""
    if data and "memory" in data:
        mem = f"RAM {data['memory'].get('percent', '?')}%"
    checks.append(("Métricas del sistema", ok, err or mem))

    # ── 5. Recovery engine ──
    status, data, err = _get("/api/system/health/recovery")
    ok = status == 200
    rec_status = data.get("status", "N/A") if data else ""
    checks.append(("Motor de recuperación", ok, err or rec_status))

    # ── Resultados ──
    print()
    all_ok = True
    for name, ok, detail in checks:
        mark = "✅" if ok else "❌"
        print(f"{mark} {name}")
        if detail:
            print(f"      {detail}")
        if not ok:
            all_ok = False

    print()
    if all_ok:
        print("✅ TODO LISTO — Puedes empezar a trabajar.")
        print("   Tu última sesión se restauró automáticamente si existía una.")
        return 0
    else:
        print("⚠️  ALGUNOS COMPONENTES NO RESPONDEN — Revisa antes de trabajar.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
