"""Trading on-chain: la API de Jupiter cambió y nadie se enteró.

Por qué existe (2026-10-05, KNOWN_DEBT #61). Al revisar por qué el owner
decía "nada de pago" en lugar de Helius, se probó el path real de trading y
**estaba muerto**:

1. `quote-api.jup.ag` **no resuelve DNS**. Todas las llamadas de quote y swap
   caían en un `except httpx.HTTPError` que devolvía `None`. El sistema
   reportaba "sin liquidity found" o "no route" — indistinguible de "no hay
   oportunidades". La API migró de `/v6/{quote,swap}` a `/swap/v1/{quote,swap}`.

2. `api.jup.ag/price/v2` devuelve **404** (migró a `/price/v3`).

3. `/price/v3` cambió la forma de la respuesta **dos veces**:
   - v2: `{"data": {"<mint>": {...}}}`   v3: `{"<mint>": {...}}` (en la raíz)
   - campos: `price`/`change24h`  →  `usdPrice`/`priceChange24h`

   El parser viejo leía `data["data"]` y `info["price"]`: con v3 devolvía
   **0.0 sin error**. El peor modo de fallo posible — un número plausible
   que en realidad es "no lo sé".

Nada de esto daba excepción: cada capa absorbía el fallo y devolvía un
valor por defecto. Un pipeline que devuelve 0 en cada paso parece
"funcionando" y no做出的 nada.

Este test fija las URLs y el parser contra la **forma real** de la API.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest

from cores.trading.dex import jupiter as jup_mod
from cores.trading.dex.jupiter import JupiterClient

SOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# Respuesta REAL de /price/v3 (capturada 2026-10-05)
PRICE_V3_REAL = {
    USDC: {
        "createdAt": "2024-06-05T08:55:25.527Z",
        "liquidity": 472363379.68282896,
        "usdPrice": 0.9999639367606884,
        "blockId": 453655173,
        "decimals": 6,
        "priceChange24h": 0.0032166507765790083,
    }
}


class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.text = json.dumps(payload)
        self.request = None
        self.headers = {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError(f"{self.status_code}", request=None, response=self)  # type: ignore[arg-type]


class _Http:
    def __init__(self, payload):
        self._payload = payload
        self.posts: list[str] = []

    def get(self, url, params=None, **kw):
        return _Resp(self._payload)

    def post(self, url, json=None, **kw):
        self.posts.append(url)
        return _Resp({"jsonrpc": "2.0", "id": 1, "result": "5xFakeSignature111"})


class TestUrlsAreCurrent:
    """Si Jupiter vuelve a migrar, esto falla antes que el trading."""

    def test_quote_no_usa_la_url_muerta(self) -> None:
        """`quote-api.jup.ag` no resuelve DNS: mataba todo el trading."""

        for name in ("JUPITER_QUOTE_URL", "JUPITER_SWAP_URL"):
            url = getattr(jup_mod, name)
            assert "quote-api.jup.ag" not in url, (
                f"{name} apunta a quote-api.jup.ag, que no resuelve DNS. "
                "El fallo se tragaba en un except y devolvía None."
            )

    def test_price_usa_v3(self) -> None:

        assert jup_mod.JUPITER_PRICE_URL.endswith("/price/v3"), "price/v2 devuelve 404"

    def test_el_default_del_cliente_no_es_la_url_muerta(self) -> None:
        import inspect

        src = inspect.signature(JupiterClient.__init__)
        default = src.parameters["jupiter_api_url"].default
        assert "quote-api.jup.ag" not in default

    def test_todo_el_trading_es_keyless(self) -> None:
        """Regla del owner: nada de pago. Ninguna URL con key."""

        for name in ("JUPITER_QUOTE_URL", "JUPITER_SWAP_URL", "JUPITER_PRICE_URL"):
            url = getattr(jup_mod, name)
            assert "api-key" not in url and "apikey" not in url.lower()


class TestPriceParserV3:
    """El parser leía claves de v2 sobre una respuesta de v3 → 0.0 sin error."""

    def test_parsea_la_forma_real(self) -> None:
        c = JupiterClient()
        c._http = _Http(PRICE_V3_REAL)

        prices = c.get_token_prices([USDC])

        assert USDC in prices, "no parseó la entrada"
        assert prices[USDC].price_usd == Decimal(str(PRICE_V3_REAL[USDC]["usdPrice"]))
        assert prices[USDC].price_change_24h == pytest.approx(0.0032166, rel=1e-3)

    def test_el_precio_no_es_cero_si_la_api_responde(self) -> None:
        """El bug viejo devolvía 0.0 sin error: un número plausible y falso."""
        c = JupiterClient()
        c._http = _Http(PRICE_V3_REAL)

        precios = list(c.get_token_prices([USDC]).values())

        assert precios[0].price_usd > 0, "precio 0 con respuesta válida = parser roto"

    def test_tolera_la_forma_v2_por_compatibilidad(self) -> None:
        """Si alguien pega un mock viejo, no debe romperse."""
        v2 = {"data": PRICE_V3_REAL}
        c = JupiterClient()
        c._http = _Http(v2)

        assert USDC in c.get_token_prices([USDC])

    def test_entradas_no_dict_se_ignoran(self) -> None:
        c = JupiterClient()
        c._http = _Http({USDC: "no soy un dict", SOL: {"usdPrice": "1.5"}})

        precios = c.get_token_prices([USDC, SOL])

        assert SOL in precios
        assert USDC not in precios


class TestFreeRpcResilience:
    """Cero pago: laInstead de un provider, retry + rotación de gratuitos."""

    def test_hay_al_menos_un_rpc_gratuito(self) -> None:
        c = JupiterClient()
        cands = c._rpc_candidates()
        assert len(cands) >= 2, "sin fallback: un 429 pierde la operación"

    def test_el_fallback_es_gratuito(self) -> None:
        """Regla del owner: nada de pago."""

        for url in jup_mod._FREE_FALLBACK_RPCS:
            assert "api-key" not in url.lower() and "helius" not in url.lower()

    def test_todas_las_llamadas_rpc_pasan_por_el_helper(self) -> None:
        """Guard estructural: una llamada directa al RPC no tiene retry."""
        import inspect

        src = inspect.getsource(jup_mod)
        # Debe existir el helper y no debe quedar ningun post directo al rpc
        assert "_rpc_post" in src
        assert "self._http.post(self._rpc_url" not in src, "quedó una llamada RPC sin retry/rotación"

    def test_reintenta_ante_429_y_rota(self) -> None:
        """Ante un 429 debe probar el siguiente endpoint, no rendirse."""
        import httpx

        c = JupiterClient(rpc_retries=1, rpc_backoff_base=0.01, rpc_backoff_max=0.02)
        urls: list[str] = []

        class _RateLimited:
            def post(self, url, json=None, **kw):
                urls.append(url)
                raise httpx.HTTPStatusError("429", request=None, response=None)  # type: ignore[arg-type]

            def get(self, url, params=None, **kw):
                return _Resp({})

        c._http = _RateLimited()  # type: ignore[assignment]

        resultado = c._rpc_post({"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": []})

        assert resultado is None
        assert len(urls) >= 2, f"debería haber rotado de endpoint; intentó {len(urls)}"

    def test_exito_no_rota(self) -> None:
        """Con un endpoint sano no debe gastar intentos en los demás."""
        c = JupiterClient(rpc_retries=2)
        posts: list[str] = []

        class _Ok:
            def post(self, url, json=None, **kw):
                posts.append(url)
                return _Resp({"jsonrpc": "2.0", "id": 1, "result": "sig"})

            def get(self, url, params=None, **kw):
                return _Resp({})

        c._http = _Ok()  # type: ignore[assignment]

        assert c._rpc_post({"jsonrpc": "2.0", "id": 1}) is not None
        assert len(posts) == 1, f"no debía rotar con éxito en el primero; hizo {len(posts)}"
