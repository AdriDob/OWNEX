#!/usr/bin/env python3
"""OWNEX — verificación real del circuito operativo.

DISCOVER → EVALUATE → PRIORITIZE → PREPARE → HUMAN GATE → EXECUTE
         → VERIFY → EARN → CAPITAL → LEARN

No inventa resultados: por cada etapa reporta el código HTTP real, un
resumen de lo devuelto y el veredicto (OK / VACÍO / BLOQUEADO).

Auth: usa el flujo real de la API (registro opcional + login) y mantiene la
cookie de CSRF en un jar. El token puede pasarse con --token para no crear
usuarios.

Uso:
    python scripts/verify_circuit.py                       # login con usuario de prueba
    python scripts/verify_circuit.py --token <bearer>      # token ya emitido
    python scripts/verify_circuit.py --base http://127.0.0.1:8000

Exit: 0 si el circuito responde en todas las etapas, 1 si hay bloqueos.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

CSRF_COOKIE = "csrf-token"
CSRF_HEADER = "X-CSRF-Token"

# (etapa, método, ruta, resumen)
STAGES: list[tuple[str, str, str, Callable[[Any], str]]] = [
    (
        "DISCOVER",
        "GET",
        "/api/discovery/stats",
        lambda d: "sources=" + str(_count(d, ("sources", "total_sources", "total"))),
    ),
    (
        "DISCOVER",
        "GET",
        "/api/discovery/programs",
        lambda d: "programs=" + str(_count(d, ("programs", "items", "data"))),
    ),
    (
        "PRIORITIZE",
        "GET",
        "/api/discovery/programs/ranked",
        lambda d: "ranked=" + str(_count(d, ("ranked", "items", "programs", "data"))),
    ),
    (
        "PREPARE",
        "GET",
        "/api/direct-work/workbank",
        lambda d: "workbank=" + str(_count(d, ("items", "packages", "workbank", "data"))),
    ),
    ("HUMAN GATE", "GET", "/api/execution-queue", lambda d: "queue=" + str(_count(d, ("items", "queue", "data")))),
    (
        "HUMAN GATE",
        "GET",
        "/api/execution-queue/states/transitions?current=queued",
        lambda d: "transitions=" + str(_count(d, ("transitions", "states", "data"))),
    ),
    (
        "EXECUTE",
        "GET",
        "/api/canonical/execution",
        lambda d: "canonical=" + str(_count(d, ("items", "executions", "data"))),
    ),
    ("VERIFY", "GET", "/api/verdicts", lambda d: "verdicts=" + str(_count(d, ("verdicts", "items", "data")))),
    ("EARN", "GET", "/api/economic/monthly-revenue", lambda d: "months=" + str(_count(d, ("months", "items", "data")))),
    ("CAPITAL", "GET", "/api/capital/dashboard", lambda d: "keys=" + str(len(d) if isinstance(d, dict) else 0)),
    ("LEARN", "GET", "/api/core/learning/stats", lambda d: "keys=" + str(len(d) if isinstance(d, dict) else 0)),
    (
        "SCHEDULER",
        "GET",
        "/api/autonomous-scheduler/stats",
        lambda d: "stats=" + str(_count(d, ("stats", "items", "data"))),
    ),
    ("AGENDA", "GET", "/api/agenda/next-actions", lambda d: "actions=" + str(_count(d, ("items", "actions", "data")))),
    ("AGENDA", "GET", "/api/agenda/completed-today", lambda d: "done=" + str(_count(d, ("items", "data")))),
    ("AGENDA", "GET", "/api/agenda/by-source", lambda d: "sources=" + str(_count(d, ("by_source", "sources", "data")))),
    ("AGENDA", "GET", "/api/agenda/items", lambda d: "items=" + str(_count(d, ("items", "data")))),
    (
        "SETUP",
        "GET",
        "/api/setup/checklist/status",
        lambda d: "pending=" + str(_count(d, ("pending", "items", "data"))),
    ),
    ("AI CHAT", "GET", "/api/assistant/status", lambda d: "keys=" + str(len(d) if isinstance(d, dict) else 0)),
    ("VOICE", "GET", "/voice/status", lambda d: "tts=" + str((d or {}).get("tts_provider", "?"))),
]


def _count(data: Any, keys: tuple[str, ...]) -> int:
    """Primer contenedor/ escalar que exista en la respuesta."""
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for k in keys:
            v = data.get(k)
            if isinstance(v, list):
                return len(v)
            if isinstance(v, dict):
                return len(v)
            if isinstance(v, int):
                return v
    return 0


class Client:
    """Cliente HTTP con cookie jar (CSRF double-submit) y Bearer opcional."""

    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.token: str | None = None

    def _headers(self) -> dict[str, str]:
        h = {"Accept": "application/json"}
        csrf = next((c.value for c in self.jar if c.name == CSRF_COOKIE), None)
        if csrf:
            h[CSRF_HEADER] = csrf
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def call(self, method: str, path: str, payload: Any = None) -> tuple[int, Any, str]:
        url = self.base + path
        data = None
        headers = self._headers()
        if payload is not None:
            data = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self.opener.open(req, timeout=30) as resp:  # noqa: S310
                body = resp.read().decode("utf-8", "replace")
                try:
                    return resp.status, json.loads(body), ""
                except json.JSONDecodeError:
                    return resp.status, None, body[:160]
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            try:
                return e.code, json.loads(body), ""
            except json.JSONDecodeError:
                return e.code, None, body[:160]
        except Exception as e:  # noqa: BLE001
            return 0, None, str(e)[:160]

    def prime_csrf(self) -> None:
        """Deja la cookie csrf-token en el jar.

        NO puede ser /api/health: esa ruta está en EXEMPT_PATHS del middleware
        CSRF, así que sale sin cookie. /api/version es pública para auth pero
        no exenta de CSRF → es la que emite el token del double-submit.
        """
        self.call("GET", "/api/version")

    def register(self, username: str, email: str, password: str) -> tuple[int, Any, str]:
        self.prime_csrf()
        return self.call(
            "POST",
            "/api/auth/users/register",
            {"username": username, "email": email, "password": password},
        )

    def login(self, username: str, password: str) -> tuple[int, Any, str]:
        self.prime_csrf()
        return self.call("POST", "/api/auth/users/login", {"username": username, "password": password})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--token", default=os.environ.get("OWNEX_TOKEN", ""))
    ap.add_argument("--username", default="circuit_probe")
    ap.add_argument("--password", default="Circuit-Probe-Pass-123!")
    args = ap.parse_args()

    print("=" * 78)
    print("OWNEX — VERIFICACIÓN DEL CIRCUITO OPERATIVO (endpoints reales)")
    print("=" * 78)
    print(f"Base: {args.base}\n")

    c = Client(args.base)

    status, _, _ = c.call("GET", "/api/health")
    if status != 200:
        print(f"BLOQUEO: /api/health devolvió {status} — backend no operativo.\n")
        return 1
    print("[OK] /api/health responde 200")

    # ── Sesión ──────────────────────────────────────────────────────────
    # El registro emite token directamente. El login es la vía normal, pero
    # exige email verificado cuando hay SMTP configurado (mail_configured());
    # en una instalación local sin SMTP el login funciona directo.
    if args.token:
        c.token = args.token
        print("[OK] token provisto por --token/OWNEX_TOKEN")
    else:
        reg_status, reg_body, reg_raw = c.register(args.username, f"{args.username}@example.invalid", args.password)
        if reg_status in (200, 201) and isinstance(reg_body, dict) and reg_body.get("access_token"):
            c.token = reg_body["access_token"]
            print(f"[OK] registro {reg_status} — token emitido (email_verified={reg_body.get('email_verified')})")
        else:
            print(f"[..] registro devolvió {reg_status} ({str(reg_body)[:120]}) — se intenta login")

        login_status, login_body, login_raw = c.login(args.username, args.password)
        if login_status == 200 and isinstance(login_body, dict):
            c.token = login_body.get("access_token") or login_body.get("token")
            print(f"[OK] login OK — token emitido ({len(c.token or '')} chars)")
        elif not c.token:
            print(f"[BLOQUEO] login devolvió {login_status}: {str(login_body)[:160]}")
            print("         (registro sin token y login rechazado)")
            return 1
        else:
            print(f"[..] login devolvió {login_status} — se sigue con el token del registro")

    print()
    rows: list[str] = []
    blocked: list[str] = []
    empty: list[str] = []

    for stage, method, path, summariser in STAGES:
        status, data, raw = c.call(method, path)
        if status == 200:
            summary = summariser(data) if data is not None else "sin cuerpo"
            rows.append(f"  [OK]        {stage:<11} {path:<44} {summary}")
            if summary.endswith("=0"):
                empty.append(f"{stage:<11} {path} ({summary})")
        elif status in (401, 403):
            blocked.append(f"{stage:<11} {path} → HTTP {status} (sesión rechazada)")
            rows.append(f"  [AUTH]      {stage:<11} {path:<44} HTTP {status}")
        elif status == 404:
            # 404 con `detail` = el endpoint existe pero no hay datos todavía
            # (p.ej. "ExecutionPlanArtifact not available. Run a pipeline first.").
            # 404 sin detalle = ruta realmente ausente → bloqueo.
            detail = ""
            if isinstance(data, dict):
                detail = str(data.get("detail") or "")
            if detail:
                rows.append(f"  [VACÍO]     {stage:<11} {path:<44} {detail[:60]}")
                empty.append(f"{stage:<11} {path} ({detail[:60]})")
            else:
                blocked.append(f"{stage:<11} {path} → 404 (ruta no montada)")
                rows.append(f"  [404]       {stage:<11} {path:<44} ruta ausente")
        else:
            blocked.append(f"{stage:<11} {path} → HTTP {status} {raw[:80]}")
            rows.append(f"  [ERR {status}]   {stage:<11} {path:<44} {raw[:60]}")

    print("\n".join(rows))

    print("\n" + "-" * 78)
    ok = len(rows) - len(blocked)
    print(f"RESULTADO: {ok} etapas operativas | {len(empty)} vacías | {len(blocked)} bloqueadas")
    if empty:
        print("\nEtapas sin datos (no es un fallo: la base está limpia):")
        for e in empty:
            print(f"  - {e}")
    if blocked:
        print("\nBLOQUEOS REALES:")
        for b in blocked:
            print(f"  ! {b}")
    print("-" * 78)
    return 1 if blocked else 0


if __name__ == "__main__":
    sys.exit(main())
