"""Audita las fuentes registradas contra la realidad de la red.

Por qué existe. `global_sources.py` declara ~195 `SourceDefinition` (o 178 tras
el gate). Esa cifra mide Registration, no Capability: un endpoint puedereturns 200
con HTML donde se esperaba JSON, o 404, y el conector sigue "registrado".

La auditoría pasada usa `monkeypatch(httpx)`, así que nunca tocó la red: todos los
tests pasan aunque los tres adapters de discovery apunten a endpoints muertos
(medido 2026-10-05: IssueHunt 404, Opire 404, Algora devuelve HTML).

Este script mide. Es read-only: GET público, sin credenciales, sin escribir nada.

Uso:
    python scripts/audit_source_liveness.py            # todas
    python scripts/audit_source_liveness.py --limit 20
    python scripts/audit_source_liveness.py --json auditoria.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cores.opportunity.global_sources import get_sources  # noqa: E402

# Endpoints reales que los adapters de discovery llaman. Se miden aparte del
# SourceDefinition.url, que es la URL pública del sitio humano: que devuelva
# HTML es lo esperado, no un fallo. Lo que decide si un conector sirve es si el
# endpoint que el adapter consume devuelve el formato que el adapter parsea.
# Endpoints REALES, verificados contra la red el 2026-10-05. El valor es lo
# que el adapter llama hoy; la nota explica qué es realmente ese endpoint.
#
# `kind` separa dos cosas que el script v1 confundía:
#   api      — existe un endpoint de API consumible
#   frontend — NO hay API pública: es la SPA del producto y devuelve HTML
# Un "html-not-json" sobre un frontend no es un bug que arreglar, es un hecho
# que documentar: para esa plataforma la integración no es un GET.
ADAPTER_ENDPOINTS: dict[str, tuple[str, str, str]] = {
    # (endpoint que llama el adapter, kind, nota)
    "atlas": (
        "https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=1",
        "api",
        "API pública del NIST. Correcta.",
    ),
    "security_bounty": (
        "https://api.hackerone.com/v1/hackers/programs",
        "api",
        "Devuelve 401 JSON: pide credencial. Gate correcto.",
    ),
    "forge_legacy": (
        "https://superteam.fun/api/listings?type=bounty",
        "api",
        "Reparado: earn.superteam.fun responde 308 aquí. 20 listings.",
    ),
    "opencollective": (
        "https://api.opencollective.com/graphql/v2",
        "api",
        "GraphQL: 400 en GET es correcto, necesita POST con query.",
    ),
    "opire": (
        "https://api.opire.com/v1/bounties",
        "api",
        "El dominio NO resuelve por DNS. Fuente caída o URL inventada.",
    ),
    "opyre": (
        "https://api.opyre.com/v1/bounties",
        "api",
        "El dominio NO resuelve por DNS. Sin verificar si existe otro.",
    ),
    "issuehunt": (
        "https://api.issuehunt.io/v1/bounties",
        "api",
        "El host responde pero la ruta da 404. API no pública aquí.",
    ),
    "ai_tasks": ("https://outlier.ai", "frontend", "Sin API pública; el producto es una SPA."),
    "ar_jobs": ("https://www.zonajobs.com.ar", "frontend", "Bolsa de empleo sin API pública."),
    "high_payout": ("https://immunefi.com/bug-bounty/", "frontend", "El listado es la SPA; el backend es privado."),
    "microtask": (
        "https://app.prolific.com/api/v1/tasks",
        "frontend",
        "La ruta devuelve 404 JSON: la API exige credencial y otro path.",
    ),
}


# Un 401/403 con content-type JSON significa "existe y pide credencial": la
# respuesta correcta de un Human Gate, no un endpoint muerto.
AUTH_REQUIRED = (401, 403)

PROBE_CONCURRENCY = 8
TIMEOUT_SECONDS = 12
USER_AGENT = "OWNEX-source-audit/1.0 (read-only liveness probe)"


@dataclass
class Finding:
    name: str
    url: str
    status: int | None
    verdict: str  # live | dead | html-not-json | error | skip
    detail: str
    latency_ms: int


async def probe(client: httpx.AsyncClient, name: str, url: str, kind: str = "api") -> Finding:
    try:
        r = await client.get(url)
    except Exception as exc:  # noqa: BLE001
        return Finding(name, url, None, "error", f"{type(exc).__name__}: {exc}"[:120], 0)

    ctype = (r.headers.get("content-type") or "").lower()
    latency = int(r.elapsed.total_seconds() * 1000)

    if "json" in ctype:
        if r.status_code in AUTH_REQUIRED:
            return Finding(name, url, r.status_code, "needs-credential", f"HTTP {r.status_code} json", latency)
        if r.status_code >= 400:
            return Finding(name, url, r.status_code, "dead", f"HTTP {r.status_code} json", latency)
        return Finding(name, url, r.status_code, "live", "json", latency)
    if r.status_code >= 400:
        return Finding(name, url, r.status_code, "dead", f"HTTP {r.status_code}", latency)
    if kind == "frontend":
        return Finding(name, url, r.status_code, "sin-api-publica", "SPA: no hay API que consumir", latency)
    snippet = " ".join(r.text[:110].split())
    return Finding(name, url, r.status_code, "html-not-json", snippet, latency)


async def run(limit: int | None, adapters_only: bool) -> list[Finding]:
    if adapters_only:
        items = [(n, v[0], v[1]) for n, v in ADAPTER_ENDPOINTS.items()]
        if limit:
            items = items[:limit]
        sem = asyncio.Semaphore(PROBE_CONCURRENCY)
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT}
        ) as client:

            async def one(item):
                async with sem:
                    return await probe(client, item[0], item[1])

            return await asyncio.gather(*(one(i) for i in items))

    sources = get_sources()
    if limit:
        sources = sources[:limit]

    sem = asyncio.Semaphore(PROBE_CONCURRENCY)

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=TIMEOUT_SECONDS,
        headers={"User-Agent": USER_AGENT},
    ) as client:

        async def one(src: object) -> Finding:
            name = str(getattr(src, "name", "?"))
            url = str(getattr(src, "url", "") or "")
            if not url.startswith("http"):
                return Finding(name, url, None, "skip", "sin url http(s)", 0)
            async with sem:
                return await probe(client, name, url)

        return await asyncio.gather(*(one(s) for s in sources))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--adapters", action="store_true", help="sólo los endpoints de API de los adapters")
    args = ap.parse_args()

    findings = asyncio.run(run(args.limit, args.adapters))

    counts: dict[str, int] = {}
    for f in findings:
        counts[f.verdict] = counts.get(f.verdict, 0) + 1

    total = len(findings)
    print(f"\n  {total} fuentes auditadas")
    for verdict, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        pct = 100 * n / total if total else 0
        print(f"    {verdict:16} {n:>4}  ({pct:5.1f}%)")

    usable_verdicts = {"live", "needs-credential", "skip"} if args.adapters else {"live", "skip"}
    broken = [f for f in findings if f.verdict not in usable_verdicts]
    if broken:
        sin_api = [f for f in findings if f.verdict == "sin-api-publica"]
    if sin_api:
        print(f"\n  {len(sin_api)} SIN API PÚBLICA (no es un bug: no hay endpoint que consumir):")
        for f in sin_api:
            print(f"    {f.name[:26]:28} {f.detail[:48]}")
    sin_api = [f for f in findings if f.verdict == "sin-api-publica"]
    if sin_api:
        print(f"\n  {len(sin_api)} SIN API PUBLICA (no es un bug: no hay endpoint que consumir):")
        for f in sin_api:
            print(f"    {f.name[:26]:28} {f.detail[:48]}")

    print(f"\n  {len(broken)} con problemas (las que un conector no puede usar tal cual):")
    for f in broken[:25]:
        print(f"    {f.verdict:14} {f.name[:26]:28} {f.detail[:44]}")
    if len(broken) > 25:
        print(f"    ... y {len(broken) - 25} mas")

    usable = sum(counts.get(v, 0) for v in usable_verdicts)
    print(f"\n  conectores usables tal cual: {usable}/{total}  ({100 * usable / total:.1f}%)")

    if args.json:
        args.json.write_text(
            json.dumps([asdict(f) for f in findings], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"  detalle escrito en {args.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
