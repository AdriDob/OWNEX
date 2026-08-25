#!/usr/bin/env python3
"""OWNEX — Next Best Action desde la terminal.

Consume GET /api/applications/income-plan y muestra la acción 🎯AHORA con
los campos económicos reales (sin probabilidades inventadas). Útil hasta que
la card visual llegue en v1.0.1-alpha.

Uso:
    python scripts/next_action.py                 # escanea puertos 8000-8099
    python scripts/next_action.py --port 8123     # puerto conocido
    python scripts/next_action.py --json          # payload crudo
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any

HOST = "127.0.0.1"
PORT_RANGE = range(8000, 8100)


def _get(url: str, token: str | None = None, timeout: float = 30) -> Any:
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def find_backend(explicit_port: int | None) -> int | None:
    if explicit_port:
        return explicit_port
    for port in PORT_RANGE:
        try:
            with urllib.request.urlopen(f"http://{HOST}:{port}/api/health", timeout=0.6) as r:
                if r.status == 200:
                    return port
        except Exception:
            continue
    return None


def login(base: str) -> str:
    req = urllib.request.Request(
        f"{base}/api/auth/login",
        method="POST",
        data=json.dumps({"device_id": "cli-next-action"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    return (data.get("data") or {}).get("token", "")


def fmt_hours(h: Any) -> str:
    return f"{float(h):g}h" if h is not None else "—"


def main() -> int:
    ap = argparse.ArgumentParser(description="NEXT BEST ACTION de OWNEX")
    ap.add_argument("--port", type=int, default=None, help="puerto del backend (default: scan 8000-8099)")
    ap.add_argument("--json", action="store_true", help="imprimir el plan completo en JSON")
    args = ap.parse_args()

    port = find_backend(args.port)
    if not port:
        print("❌ Backend OWNEX no encontrado en puertos 8000-8099. ¿Está corriendo?", file=sys.stderr)
        return 1
    base = f"http://{HOST}:{port}"

    token = login(base)
    try:
        plan = _get(f"{base}/api/applications/income-plan", token=token)
    except urllib.error.HTTPError as e:
        print(f"❌ income-plan HTTP {e.code}: {e.reason}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    cc = plan.get("income_command_center") or {}
    today = cc.get("today") or {}

    print()
    print("════════════════════════════════════════════")
    print(" 🎯 AHORA — NEXT BEST ACTION")
    print("════════════════════════════════════════════")

    na = plan.get("next_action") or {}
    if not na:
        print(" Sin acción disponible ahora. Corré un ciclo del Work Bank.")
        print("════════════════════════════════════════════")
        return 0

    title = na.get("title") or na.get("detail") or "(sin título)"
    print(f" {title}")
    if na.get("source"):
        src = str(na["source"]).replace("_", " ").upper()
        print(f" Fuente:    {src}")
    url = na.get("url")
    if url:
        print(f" URL:       {url}")
    hours = na.get("human_hours")
    evh = na.get("ev_per_human_hour_usd")
    payoff = na.get("payoff_range")
    cash = na.get("cash_speed_days")

    def fmt_payoff(p: Any) -> str:
        if isinstance(p, dict):
            lo, hi = p.get("low"), p.get("high")

            def f(v: Any) -> str:
                return f"${float(v):,.0f}" if v is not None else "?"

            return f"{f(lo)} – {f(hi)}" if hi != lo else f(lo)
        return str(p)

    if hours is not None or evh is not None:
        print(f" Tiempo:    {fmt_hours(hours)}   EV/h: {'$' + format(evh, '.0f') if evh is not None else '—'}")
    if payoff:
        print(f" Pago:      {fmt_payoff(payoff)}")
    if cash is not None:
        print(f" Cobro:     ~{cash} días")
    ze = na.get("zero_experience")
    ass = na.get("assessment_required")
    if ze is not None:
        print(f" Experiencia previa: {'NO requerida' if ze else 'requerida'}")
    if ass is not None:
        print(f" Assessment: {'sí' if ass else 'no'} ({'costo amortizado' if ass else 'entrada directa'})")
    prob = na.get("access_probability")
    if prob:
        print(f" Acceso:    {prob}")
    item_url = na.get("url")
    print()
    print(" Tu acción:", "abrí la URL y ejecutá." if item_url else "seguí el detalle del plan.")
    print("════════════════════════════════════════════")

    if today.get("low") or today.get("high"):
        lo, hi = today.get("low"), today.get("high")

        def fmt(v: Any) -> str:
            return f"${float(v):,.0f}" if v is not None else "—"

        print(f" Hoy (rango): {fmt(lo)} – {fmt(hi)}")

    tracks = plan.get("tracks") or []
    if tracks:
        print(f" Tracks activos: {len(tracks)}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
