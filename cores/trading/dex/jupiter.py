from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx

logger = logging.getLogger("orion.trading.jupiter")

JUPITER_QUOTE_URL = "https://lite-api.jup.ag/swap/v1/quote"
JUPITER_SWAP_URL = "https://lite-api.jup.ag/swap/v1/swap"
JUPITER_PRICE_URL = "https://lite-api.jup.ag/price/v3"

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


@dataclass
class JupiterQuote:
    input_mint: str
    output_mint: str
    in_amount: int
    out_amount: int
    other_amount_threshold: int
    price_impact_pct: float
    route_plan: list[dict[str, Any]]
    slippage_bps: int
    swap_mode: str = "ExactIn"
    platform_fee: dict[str, Any] | None = None


@dataclass
class SwapResult:
    tx_id: str
    input_amount: int
    output_amount: int
    fee: int
    price_impact_pct: float


@dataclass
class TokenPrice:
    mint: str
    price_usd: Decimal
    price_change_24h: float = 0.0


# RPCs publicos de Solana: si el caller dejo uno de estos Y hay key de Helius,
# preferimos Helius (el publico limita por IP y puede dar 429 en un swap).
_PUBLIC_RPC_URLS: frozenset[str] = frozenset(
    {
        "https://api.mainnet-beta.solana.com",
        "https://solana-mainnet.g.alchemy.com/v2/demo",
        "https://rpc.ankr.com/solana",
        "https://solana-rpc.publicnode.com",
        "http://localhost:8899",
    }
)


# IMPORTANTE (verificado 2026-10-05, KNOWN_DEBT #61): la API de Jupiter
# movió el trading de /v6/{quote,swap} a /swap/v1/{quote,swap}. La URL vieja
# `quote-api.jup.ag` ya NO RESUELVE DNS, así que TODO el trading on-chain
# estaba muerto con un ConnectError silencioso dentro de un try/except que
# devolvía None. Medido contra la API real antes de cambiar la constante.

# RPCs alternativos keyless y gratuitos, medidos 2026-10-05.
# publicnode respondió 354 ms vs 1002 ms del oficial: mismo tier free, 3x más rápido.
_FREE_FALLBACK_RPCS: tuple[str, ...] = ("https://solana-rpc.publicnode.com",)


class JupiterClient:
    def __init__(
        self,
        rpc_url: str = "https://api.mainnet-beta.solana.com",
        jupiter_api_url: str = "https://lite-api.jup.ag/swap/v1",
        helius_api_key: str = "",
        skip_preflight: bool = False,
        rpc_retries: int = 2,
        rpc_backoff_base: float = 0.25,
        rpc_backoff_max: float = 2.0,
    ) -> None:
        # Preflight ON por defecto: simular la tx es local y gratis, evitarla
        # cuesta fees reales. Ver `send_transaction`.
        self._skip_preflight = skip_preflight
        # Retry con backoff por endpoint: el tier free aguanta secuencial pero
        # castiga concurrencia (medido: 10 hilos x 20 -> 160/200 con 429).
        # La rotación entre endpoints gratuitos evita pagar un RPC.
        self._rpc_retries = rpc_retries
        self._rpc_backoff_base = rpc_backoff_base
        self._rpc_backoff_max = rpc_backoff_max
        self._jupiter_url = jupiter_api_url.rstrip("/")
        self._helius_api_key = helius_api_key
        # `helius_api_key` se recibía y se guardaba pero NUNCA se usaba: el RPC
        # quedaba siempre en `api.mainnet-beta.solana.com`, que rate-limita
        # fuerte y puede rechazar `sendTransaction`. Con la key de Helius
        # configurada, el RPC con y sin key prioriza el endpoint de Helius.
        self._rpc_url = self._resolve_rpc_url(rpc_url, helius_api_key)
        self._http = httpx.Client(timeout=30)

    @staticmethod
    def _resolve_rpc_url(rpc_url: str, helius_api_key: str) -> str:
        """Endpoint RPC efectivo.

        Prioriza Helius si hay key: `api.mainnet-beta.solana.com` limita por
        IP y en un flujo de swaps puede devolver 429 justo cuando más se
        necesita (construir, firmar y enviar la tx). Con Helius se levanta el
        límite y además da más throughput.

        Regla: una key que se recibe y se guarda pero no se usa es
        configuración muerta que además promete un rendimiento que no llega.
        """
        configured = (rpc_url or "").strip().lower()
        # Si el caller YA pasó un RPC dedicado (no el público), respetarlo:
        # Helius no debe pisar una preferencia explícita del operador.
        if configured and configured not in _PUBLIC_RPC_URLS:
            return rpc_url
        if helius_api_key:
            return f"https://mainnet.helius-rpc.com/?api-key={helius_api_key}"
        return rpc_url

    @property
    def rpc_url(self) -> str:
        """RPC efectivo (expuesto para diagnóstico)."""
        return self._rpc_url

    @property
    def using_paid_rpc(self) -> bool:
        """True si estamos usando Helius en vez del RPC público."""
        return "helius" in self._rpc_url

    def _rpc_candidates(self) -> list[str]:
        """Endpoints RPC a intentar, en orden.

        Todos **gratuitos y keyless** salvo que el operador haya puesto uno
        propio o una key de Helius. Medido 2026-10-05 (ver KNOWN_DEBT #60):

            api.mainnet-beta.solana.com  -> 1002 ms, tier free, 30/30 seq OK
            solana-rpc.publicnode.com    ->  354 ms, keyless, más rápido

        El oficial aguanta 30 requests secuenciales sin un solo 429; el
        límite de 250 RPS es nominal pero con concurrencia el efectivo cae a
        ~10-20 RPS. Por eso la rotación: si uno está saturado, el otro
        probablemente no lo esté.
        """
        cands = [self._rpc_url]
        for alt in _FREE_FALLBACK_RPCS:
            if alt not in cands:
                cands.append(alt)
        return cands

    def _rpc_post(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """POST JSON-RPC con reintento exponencial y rotación de endpoint.

        Antes cada llamada RPC era UN intento contra UN endpoint: un 429 o un
        timeout perdía la operación sin reintentar nada. Con el tier free
        eso es esperable bajo concurrencia (medido: 10 hilos × 20 → 160/200
        con 429), no una excepción.

        Reintenta sólo errores transitorios (429, 5xx, timeout, conexión).
        Un error de JSON-RPC de negocio (cuenta sin lamports, slippage
        vencido) NO se reintenta: son deterministas y retry sólo quema
        tiempo.
        """
        import time as _time

        last_exc: Exception | None = None
        candidates = self._rpc_candidates()

        for attempt in range(self._rpc_retries * len(candidates)):
            url = candidates[attempt % len(candidates)]
            try:
                resp = self._http.post(url, json=payload)
                if resp.status_code == 429 or resp.status_code >= 500:
                    last_exc = httpx.HTTPStatusError(f"RPC {resp.status_code}", request=resp.request, response=resp)
                else:
                    resp.raise_for_status()
                    return resp.json()
            except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
                last_exc = e

            if attempt < self._rpc_retries * len(candidates) - 1:
                backoff = min(self._rpc_backoff_base * (2**attempt), self._rpc_backoff_max)
                logger.warning(
                    "RPC %s falló (%s); reintento %d/%d en %.2fs",
                    url,
                    type(last_exc).__name__,
                    attempt + 1,
                    self._rpc_retries * len(candidates) - 1,
                    backoff,
                )
                _time.sleep(backoff)

        logger.error(
            "RPC falló tras %d intentos en %d endpoints: %s",
            self._rpc_retries * len(candidates),
            len(candidates),
            last_exc,
        )
        return None

    def quote(
        self,
        input_mint: str,
        output_mint: str,
        amount: int,
        slippage_bps: int = 100,
        swap_mode: str = "ExactIn",
        only_direct_routes: bool = False,
    ) -> JupiterQuote | None:
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": str(slippage_bps),
            "swapMode": swap_mode,
        }
        if only_direct_routes:
            params["onlyDirectRoutes"] = "true"

        try:
            resp = self._http.get(f"{self._jupiter_url}/quote", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.error("Jupiter quote failed: %s", e)
            return None

        error = data.get("error")
        if error:
            logger.warning("Jupiter quote error: %s", error)
            return None

        return JupiterQuote(
            input_mint=data.get("inputMint", input_mint),
            output_mint=data.get("outputMint", output_mint),
            in_amount=int(data.get("inAmount", 0)),
            out_amount=int(data.get("outAmount", 0)),
            other_amount_threshold=int(data.get("otherAmountThreshold", 0)),
            price_impact_pct=float(data.get("priceImpactPct", 0)),
            route_plan=data.get("routePlan", []),
            slippage_bps=slippage_bps,
            swap_mode=data.get("swapMode", "ExactIn"),
            platform_fee=data.get("platformFee"),
        )

    def build_swap_tx(
        self,
        quote: JupiterQuote,
        wallet_address: str,
        user_public_key: str | None = None,
        wrap_and_unwrap_sol: bool = True,
        dynamic_compute_unit_limit: bool = True,
        prioritization_fee_lamports: int | None = None,
    ) -> str | None:
        payload: dict[str, Any] = {
            "quoteResponse": {
                "inputMint": quote.input_mint,
                "outputMint": quote.output_mint,
                "inAmount": str(quote.in_amount),
                "outAmount": str(quote.out_amount),
                "otherAmountThreshold": str(quote.other_amount_threshold),
                "priceImpactPct": str(quote.price_impact_pct),
                "routePlan": quote.route_plan,
                "slippageBps": quote.slippage_bps,
                "swapMode": quote.swap_mode,
            },
            "userPublicKey": wallet_address,
            "wrapAndUnwrapSol": wrap_and_unwrap_sol,
            "dynamicComputeUnitLimit": dynamic_compute_unit_limit,
        }
        if user_public_key:
            payload["userPublicKey"] = user_public_key
        if prioritization_fee_lamports is not None:
            payload["prioritizationFeeLamports"] = prioritization_fee_lamports
        if quote.platform_fee:
            payload["quoteResponse"]["platformFee"] = quote.platform_fee

        try:
            resp = self._http.post(f"{self._jupiter_url}/swap", json=payload)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.error("Jupiter swap tx build failed: %s", e)
            return None

        tx = data.get("swapTransaction")
        if not tx:
            logger.error("Jupiter response missing swapTransaction")
            return None

        return tx

    def send_transaction(self, signed_tx_b64: str, skip_preflight: bool | None = None) -> str | None:
        """Envía la tx firmada por JSON-RPC `sendTransaction`.

        `skip_preflight` decide si el RPC **simula** la transacción antes de
        aceptarla. Venía hardcodeado en `True`, y eso es una pérdida de dinero
        silenciosa: con el preflight apagado, una tx inválida (slippage vencido,
        cuenta sin lamports, mint inválido) se incluye igual, cobra la fee de
        la red y se descarta. El owner paga fees por transacciones que nunca
        pudieron ejecutarse.

        Por defecto ahora es `False` (preflight ON). El preflight es una
        simulación local que no cuesta fees y evita quemarlas.

        `None` = usar el default del cliente (configurable por instancia).
        `True`/`False` = override explícito para esa llamada.
        """
        if skip_preflight is None:
            skip_preflight = self._skip_preflight
        tx_bytes = base64.b64decode(signed_tx_b64)
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "sendTransaction",
            "params": [
                base64.b64encode(tx_bytes).decode(),
                {
                    "encoding": "base64",
                    "skipPreflight": skip_preflight,
                    "preflightCommitment": "processed",
                },
            ],
        }
        result = self._rpc_post(payload)
        if result is None:
            logger.error("sendTransaction: no se pudo obtener respuesta RPC tras reintentos")
            return None

        err = result.get("error")
        if err:
            logger.error("sendTransaction RPC error: %s", err)
            return None

        sig = result.get("result")
        if sig:
            logger.info("Transaction sent: %s", sig)
        return sig

    def get_token_prices(self, mints: list[str]) -> dict[str, TokenPrice]:
        if not mints:
            return {}
        try:
            resp = self._http.get(
                JUPITER_PRICE_URL,
                params={"ids": ",".join(mints)},
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.error("Jupiter price fetch failed: %s", e)
            return {}

        # /price/v3 devuelve `{ "<mint>": {...} }` en la RAÍZ.
        # /price/v2 (la URL vieja) devolvía `{ "data": { "<mint>": {...} } }`.
        # El parser viejo leía `data["data"]` y con v3 devolvía `{}` siempre.
        entries = data.get("data") if isinstance(data.get("data"), dict) else data

        prices: dict[str, TokenPrice] = {}
        for mint, info in (entries or {}).items():
            if not isinstance(info, dict):
                continue
            # v3 renombró los campos: `usdPrice` (antes `price`) y
            # `priceChange24h` (antes `change24h`). Leídos con los nombres
            # viejos devolvían 0.0 sin error: el peor modo de fallo.
            prices[mint] = TokenPrice(
                mint=mint,
                price_usd=Decimal(str(info.get("usdPrice", info.get("price", "0")))),
                price_change_24h=float(info.get("priceChange24h", info.get("change24h", 0)) or 0),
            )
        return prices

    def get_token_balance(self, wallet_address: str, mint: str) -> int:
        if mint == SOL_MINT:
            return self._get_sol_balance(wallet_address)
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTokenAccountsByOwner",
            "params": [
                wallet_address,
                {"mint": mint},
                {"encoding": "jsonParsed"},
            ],
        }
        data = self._rpc_post(payload)
        if data is None:
            logger.error("getTokenAccountsByOwner: RPC sin respuesta tras reintentos")
            return 0

        accounts = data.get("result", {}).get("value", [])
        if not accounts:
            return 0
        return int(
            accounts[0]
            .get("account", {})
            .get("data", {})
            .get("parsed", {})
            .get("info", {})
            .get("tokenAmount", {})
            .get("amount", 0)
        )

    def _get_sol_balance(self, wallet_address: str) -> int:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [wallet_address],
        }
        data = self._rpc_post(payload)
        if data is None:
            logger.error("getBalance: RPC sin respuesta tras reintentos")
            return 0
        return data.get("result", {}).get("value", 0)

    def close(self) -> None:
        self._http.close()
