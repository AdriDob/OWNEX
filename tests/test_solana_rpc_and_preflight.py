"""El RPC con key y el preflight: dos decisiones que cuestan dinero.

Por qué existe (auditoría 2026-10-05). En `jupiter.py`:

1. `helius_api_key` se recibía y se guardaba en `self._helius_api_key`, y
   **nunca se leía**. El RPC quedaba siempre en
   `api.mainnet-beta.solana.com`, que limita por IP y puede devolver 429
   justo en un swap. Una key configurada que no cambia nada es
   configuración muerta que además promete un rendimiento que no llega.

2. `send_transaction(..., skip_preflight: bool = True)` tenía el preflight
   **hardcodeado en True**. Con el preflight apagado, el RPC no simula la tx:
   una tx inválida (slippage vencido, cuenta sin lamports, mint inválido) se
   incluye igual, **cobra la fee de la red** y se descarta. El owner paga
   fees por transacciones que nunca pudieron ejecutarse.

Regla: *un default que quema dinero no puede quedar hardcodeado. Y una key
recibida que no se lee es una promise que el sistema no cumple.*
"""

from __future__ import annotations

import base64

import pytest

from cores.trading.dex.jupiter import JupiterClient

PUB = "https://api.mainnet-beta.solana.com"


class TestRpcResolution:
    def test_sin_key_se_usa_el_publico(self) -> None:
        c = JupiterClient(PUB)
        assert c.rpc_url == PUB
        assert c.using_paid_rpc is False

    def test_con_key_se_usa_helius(self) -> None:
        """La key tiene que cambiar algo, si no está muerta."""
        c = JupiterClient(PUB, helius_api_key="test-key")
        assert c.using_paid_rpc is True
        assert "helius-rpc.com" in c.rpc_url
        assert "api-key=test-key" in c.rpc_url

    def test_un_rpc_dedicado_no_se_pisa(self) -> None:
        """Si el operador eligió un nodo propio, Helius no debe pisarlo."""
        propio = "https://mi-nodo.example.com"
        c = JupiterClient(propio, helius_api_key="test-key")
        assert c.rpc_url == propio
        assert c.using_paid_rpc is False

    @pytest.mark.parametrize(
        "publico",
        [
            "https://api.mainnet-beta.solana.com",
            "https://rpc.ankr.com/solana",
            "http://localhost:8899",
        ],
    )
    def test_todo_rpc_publico_se_puede_sustituir(self, publico: str) -> None:
        c = JupiterClient(publico, helius_api_key="k")
        assert "helius-rpc.com" in c.rpc_url, f"{publico} deberia caerse con key"


class TestPreflight:
    def test_preflight_on_por_default(self) -> None:
        """Apagar el preflight quema fees en transacciones inválidas."""
        assert JupiterClient()._skip_preflight is False

    def test_se_puede_activar_por_instancia(self) -> None:
        assert JupiterClient(skip_preflight=True)._skip_preflight is True

    def test_el_payload_lleva_skip_preflight_false(self) -> None:
        """El valor por defecto debe viajar al RPC, no quedar implícito."""
        sent: dict = {}

        class _Resp:
            status_code = 200
            text = ""

            def json(self):
                return {"jsonrpc": "2.0", "id": 1, "result": "5x7yFakeSignature111"}

            def raise_for_status(self):
                return None

        class _Http:
            def post(self, url, json=None):
                sent["payload"] = json
                return _Resp()

        c = JupiterClient()
        c._http = _Http()

        tx_b64 = base64.b64encode(b"fake-signed-tx-bytes").decode()
        sig = c.send_transaction(tx_b64)

        assert sig == "5x7yFakeSignature111"
        opts = sent["payload"]["params"][1]
        assert opts["skipPreflight"] is False, "el preflight debe ir ON por defecto"

    def test_override_por_llamada(self) -> None:
        sent: dict = {}

        class _Resp:
            status_code = 200
            text = ""

            def json(self):
                return {"jsonrpc": "2.0", "id": 1, "result": "sig"}

            def raise_for_status(self):
                return None

        class _Http:
            def post(self, url, json=None):
                sent["payload"] = json
                return _Resp()

        c = JupiterClient(skip_preflight=False)
        c._http = _Http()

        c.send_transaction(base64.b64encode(b"x").decode(), skip_preflight=True)
        assert sent["payload"]["params"][1]["skipPreflight"] is True

    def test_la_key_tambien_llega_al_rpc_del_post(self) -> None:
        """El RPC elegido debe ser el que realmente recibe el sendTransaction."""
        posted: list[str] = []

        class _Resp:
            status_code = 200
            text = ""

            def json(self):
                return {"jsonrpc": "2.0", "id": 1, "result": "sig"}

            def raise_for_status(self):
                return None

        class _Http:
            def post(self, url, json=None):
                posted.append(url)
                return _Resp()

        c = JupiterClient(PUB, helius_api_key="k-real")
        c._http = _Http()
        c.send_transaction(base64.b64encode(b"x").decode())

        assert posted and "helius-rpc.com" in posted[0], f"el post fue a {posted}, no al RPC con key"
