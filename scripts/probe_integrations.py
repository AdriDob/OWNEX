#!/usr/bin/env python3
"""Sondeo de integraciones externas — ¿viven o las mataron en silencio?

Por qué existe (2026-10-05). Dos integraciones estaban **muertas y nadie lo
sabía**:

  - `quote-api.jup.ag` (Jupiter): no resuelve DNS. Todo el trading on-chain
    devolvía None dentro de un `except`, y el sistema reportaba "sin route" —
    indistinguible de "no hay oportunidades".
  - `spoocheck.io` (SpoofCheck): no resuelve DNS. Marcado como *keyless* desde
    siempre; nunca funcionó ni una vez.

Las dos fallaron del mismo modo: **una dependencia que cambia de forma no
lanza excepción, devuelve su valor por defecto.** Un `None` o un `0.0` se
confunden con "no hay datos".

Este script las encuentra en segundos. No reemplaza los tests: los tests usan
fakes para ser deterministas, y este script es el que verifica que la **API
real** siga contestando.

Uso:
    python scripts/probe_integrations.py          # todas
    python scripts/probe_integrations.py --json   # salida parseable
    python scripts/probe_integrations.py --only dexscreener,polymarket

Códigos:
    VIVO        2xx — responde
    pide-key    401/402/403 — la ruta existe, falta credencial
    throttle    429 — la ruta existe, nos están limitando
    MUERTO      404, DNS fail o connection error — la integración NO funciona
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from typing import Any

try:
    import httpx
except ImportError:  # pragma: no cover
    print("Falta httpx: pip install httpx", file=sys.stderr)
    raise SystemExit(2) from None


# ── Veredicto ────────────────────────────────────────────────────

VIVO = "VIVO"
PIDE_KEY = "pide-key"
THROTTLE = "throttle"
MUERTO = "MUERTO"


@dataclass(slots=True)
class Probe:
    name: str
    url: str
    method: str = "get"
    #: Clave de env requerida. None = keyless.
    env_key: str | None = None
    #: Se espera 401 sin key; un 404 igual significa ruta muerta.
    expects_key: bool = False
    body: dict[str, Any] | None = None
    timeout: float = 12.0
    #: El servicio external murio, pero el codigo YA no lo usa. Es un
    #: canario: si alguien lo reintroduce, el probe lo sigue marcando, pero
    #: no es una integracion rota del sistema.
    retired: bool = False
    note: str = ""
    status: str = field(default="", init=False)
    code: int | None = field(default=None, init=False)
    ms: int = field(default=0, init=False)
    detail: str = field(default="", init=False)

    def run(self) -> None:
        t0 = time.monotonic()
        try:
            if self.method == "post":
                r = httpx.post(
                    self.url,
                    json=self.body or {},
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"},
                    follow_redirects=True,
                )
            else:
                r = httpx.get(self.url, timeout=self.timeout, follow_redirects=True)
        except httpx.ConnectError as e:
            self.status, self.detail = MUERTO, f"DNS/connect: {type(e).__name__}"
            self.ms = int((time.monotonic() - t0) * 1000)
            return
        except Exception as e:
            self.status, self.detail = MUERTO, f"{type(e).__name__}: {str(e)[:60]}"
            self.ms = int((time.monotonic() - t0) * 1000)
            return

        self.ms = int((time.monotonic() - t0) * 1000)
        self.code = r.status_code
        if 200 <= r.status_code < 300:
            self.status = VIVO
        elif r.status_code in (401, 402, 403):
            # La ruta existe (si estuviera muerta daría 404). Falta credencial.
            self.status = PIDE_KEY
            self.detail = f"falta {self.env_key}" if self.env_key else "pide auth"
        elif r.status_code == 429:
            self.status = THROTTLE
            self.detail = "rate limited (existe)"
        elif r.status_code == 404:
            self.status = MUERTO
            self.detail = "404 — ruta o host inexistente"
        else:
            self.status = f"HTTP {r.status_code}"
            self.detail = r.text[:80].replace("\n", " ")


# ── Las integraciones ───────────────────────────────────────────
#
# Sólo endpoints que el código llama EN RUNTIME. Los 404 son integraciones
# rotas; los "pide-key" son integraciones sanas con la key puesta.

SOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

PROBES: tuple[Probe, ...] = (
    # ── Trading / Solana (keyless) ──────────────────────────────
    Probe("jupiter-price", f"https://lite-api.jup.ag/price/v3?ids={SOL}"),
    Probe(
        "jupiter-quote",
        f"https://lite-api.jup.ag/swap/v1/quote?inputMint={SOL}&outputMint={USDC}&amount=1000000&slippageBps=100",
    ),
    Probe(
        "solana-rpc-oficial",
        "https://api.mainnet-beta.solana.com",
        "post",
        body={"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": ["11111111111111111111111111111111"]},
    ),
    Probe(
        "solana-rpc-publicnode",
        "https://solana-rpc.publicnode.com",
        "post",
        body={"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": ["11111111111111111111111111111111"]},
    ),
    Probe("dexscreener", "https://api.dexscreener.com/latest/dex/search?q=solana"),
    Probe("rugcheck", f"https://api.rugcheck.xyz/v1/tokens/{SOL}/report"),
    Probe("binance", "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT"),
    Probe(
        "polymarket-leaderboard", "https://data-api.polymarket.com/v1/leaderboard?limit=2&orderBy=PNL&timePeriod=MONTH"
    ),
    # ── Bounty discovery (keyless) ───────────────────────────────
    Probe(
        "bounty-targets-data",
        "https://raw.githubusercontent.com/arkadiyt/bounty-targets-data/main/data/hackerone_data.json",
    ),
    Probe("nvd-cve", "https://services.nvd.nist.gov/rest/json/cves/2.0?resultsPerPage=1"),
    Probe("osv-api", "https://api.osv.dev/v1/query", "post", body={"version": "0.0.0"}),
    Probe("open-meteo", "https://api.open-meteo.com/v1/forecast?latitude=0&longitude=0&current=temperature_2m"),
    # ── OSINT keyless ───────────────────────────────────────────
    Probe("otx-alienvault", "https://otx.alienvault.com/api/v1/indicators/domain/google.com/general"),
    Probe("urlscan", "https://urlscan.io/api/v1/search/?q=example.com&size=1"),
    Probe("pulsedive", "https://pulsedive.com/api/info.php?indicator=8.8.8.8"),
    Probe("shodan", "https://api.shodan.io/shodan/host/8.8.8.8?key=invalid", expects_key=True),
    # ── OSINT con key ───────────────────────────────────────────
    Probe("censys", "https://search.censys.io/api/v2/hosts/8.8.8.8", env_key="CENSYS_API_KEY", expects_key=True),
    Probe(
        "virustotal",
        "https://www.virustotal.com/api/v3/domains/google.com",
        env_key="VIRUSTOTAL_API_KEY",
        expects_key=True,
    ),
    Probe(
        "hunter", "https://api.hunter.io/v2/domain-search?domain=google.com", env_key="HUNTER_API_KEY", expects_key=True
    ),
    Probe(
        "hibp",
        "https://haveibeenpwned.com/api/v3/breachedaccount/probe@example.invalid",
        env_key="HIBP_API_KEY",
        expects_key=True,
    ),
    Probe(
        "greynoise", "https://api.greynoise.io/v2/noise/context/8.8.8.8", env_key="GREYNOISE_API_KEY", expects_key=True
    ),
    Probe("intelx", "https://2.intelx.io/intelligent/search?term=probe", env_key="INTELX_API_KEY", expects_key=True),
    # SpoofCheck: declarado keyless en osint_api.py pero el host NO resuelve.
    # NOTA: spoofcheck.io NO resuelve DNS (el servicio fue cerrado). El codigo
    # ya NO lo usa: lee DNS directo con dnspython (ver osint_api.py).
    # Se mantiene aca como canario: si alguien lo reintroduce, esto lo marca.
    Probe("spoofcheck", "https://spoofcheck.io/api/domain/google.com", retired=True),
    Probe(
        "securitytrails",
        "https://api.securitytrails.com/v1/domain/google.com/subdomains",
        env_key="SECURITYTRAILS_API_KEY",
        expects_key=True,
    ),
    Probe("threatfox", "https://threatfox-api.abuse.ch/api/v1/recent/", env_key="THREATFOX_API_KEY"),
    Probe(
        "builtwith", "https://api.builtwith.com/v21/api.json?KEY=invalid", env_key="BUILTWITH_API_KEY", expects_key=True
    ),
    Probe("ipinfo", "https://ipinfo.io/8.8.8.8", env_key="IPINFO_API_KEY", timeout=8.0),
)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="salida JSON")
    ap.add_argument("--only", default="", help="comma-separated de nombres a sondear")
    args = ap.parse_args()

    selected = [p for p in PROBES if not args.only or p.name in args.only.split(",")]

    for p in selected:
        p.run()

    muertos = [p for p in selected if p.status == MUERTO and not p.retired]
    retirados = [p for p in selected if p.status == MUERTO and p.retired]

    if args.json:
        print(
            json.dumps(
                [
                    {
                        "name": p.name,
                        "url": p.url,
                        "status": p.status,
                        "code": p.code,
                        "ms": p.ms,
                        "detail": p.detail,
                    }
                    for p in selected
                ],
                indent=2,
            )
        )
        return 1 if muertos else 0

    print(f"{'estado':10} {'code':>5} {'ms':>6}  servicio")
    print("-" * 62)
    for p in selected:
        code = str(p.code) if p.code is not None else "---"
        flag = "  <-- MUERTO" if p.status == MUERTO and not p.retired else ""
        flag = "  (servicio retirado, no en uso)" if p.status == MUERTO and p.retired else flag
        print(f"{p.status:10} {code:>5} {p.ms:>6}  {p.name}{flag}")
        if p.status == MUERTO and p.detail:
            print(f"{'':10} {'':>5} {'':>6}  └─ {p.detail}")

    print()
    vivas = [p for p in selected if p.status in (VIVO, PIDE_KEY, THROTTLE) and not p.retired]
    print(f"{len(vivas)} / {len(vivas) + len(muertos)} integraciones vivas")
    if retirados:
        print()
        print("SERVICIOS RETIRADOS (el código ya no los usa; canarios contra regresión):")
        for p in retirados:
            print(f"  · {p.name}: {p.detail}")

    if muertos:
        print()
        print("INTEGRACIONES MUERTAS — el sistema las llama y recibe None/0 sin error:")
        for p in muertos:
            print(f"  · {p.name}: {p.detail}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
