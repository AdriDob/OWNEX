"""Firma de transacciones Solana — el orden de argumentos no es intuitivo.

Por qué existe (auditoría 2026-10-05, verificado empíricamente con
solders 0.29.0):

La auditoría afirmó que `memecoin_adapter._live_swap` tenía "los argumentos
invertidos". **Era al revés.** Probado con una MessageV0 real:

| Forma | solders 0.29.0 |
|---|---|
| `VersionedTransaction(message, [keypair])` | **OK** |
| `VersionedTransaction([signature], message)` | `TypeError: failed to extract enum VersionedMessage` |
| `VersionedTransaction(message, [signature])` | `TypeError: failed to extract enum Signer` |

El bug real estaba en `solana_wallet.sign_and_serialize`, que usaba
`([sig], message)` — inválido — y además `sign_message()`, que firma bytes
arbitrarios en vez de la transacción. Es el path que usa el copy trading y
`RealExecutor`, o sea el que mueve fondos.

Este test fija el contrato con una transacción real, no con un mock: si
solders cambia el orden en una actualización, el test cae.
"""

from __future__ import annotations

import base64

import pytest

solders = pytest.importorskip("solders")

from solders.hash import Hash  # noqa: E402
from solders.instruction import Instruction  # noqa: E402
from solders.keypair import Keypair  # noqa: E402
from solders.message import MessageV0  # noqa: E402
from solders.pubkey import Pubkey  # noqa: E402
from solders.transaction import VersionedTransaction  # noqa: E402


@pytest.fixture
def signer() -> Keypair:
    """La keypair que firma. Debe ser la MISMA que armó la transacción."""
    return Keypair()


@pytest.fixture
def unsigned_tx_b64(signer: Keypair) -> str:
    """Una transacción Versioned real sin firmar, en base64 (como Jupiter).

    El fee payer es `signer`, así que `sign_and_serialize` tiene que firmar
    con esa misma key: solders rechaza `keypair-pubkey mismatch` si no.
    """
    ix = Instruction(program_id=Pubkey.default(), accounts=[], data=bytes([0, 0, 0, 0]))
    msg = MessageV0.try_compile(signer.pubkey(), [ix], [], Hash.default())
    return base64.b64encode(bytes(VersionedTransaction(msg, [signer]))).decode()


def test_orden_correcto_del_constructor_de_versionedtransaction() -> None:
    """Guard del hallazgo: (message, [keypair]) es el ORDEN VÁLIDO.

    Si solders lo cambia, este test cae y hay que revisar ambos call sites.
    """
    kp = Keypair()
    ix = Instruction(program_id=Pubkey.default(), accounts=[], data=bytes([0, 0, 0, 0]))
    vmsg = MessageV0.try_compile(kp.pubkey(), [ix], [], Hash.default())

    # Válido: message primero, keypairs después.
    VersionedTransaction(vmsg, [kp])

    # Inválido: una lista de Signature NO es un Message.
    sig = kp.sign_message(bytes(vmsg))
    with pytest.raises(TypeError):
        VersionedTransaction([sig], vmsg)  # type: ignore[arg-type]

    # Inválido: un Signature no es un Keypair.
    with pytest.raises(TypeError):
        VersionedTransaction(vmsg, [sig])  # type: ignore[list-item]


class TestSignAndSerialize:
    def test_firma_una_transaccion_real(self, unsigned_tx_b64: str, signer: Keypair) -> None:
        """El path que mueve fondos tiene que firmar de verdad."""
        from cores.trading.dex.solana_wallet import SolanaWallet

        w = SolanaWallet()
        w._keypair = signer

        out = w.sign_and_serialize(unsigned_tx_b64)
        assert out is not None, "firmar no puede fallar con una tx válida"

        # El resultado debe deserializar como VersionedTransaction y tener
        # la misma cantidad de firmantes que antes.
        signed = VersionedTransaction.from_bytes(base64.b64decode(out))
        assert len(signed.signatures) == 1

    def test_rechaza_keypair_que_no_es_el_fee_payer(self, unsigned_tx_b64: str) -> None:
        """Guard de seguridad: no firma una tx de otra cuenta.

        solders lanza `keypair-pubkey mismatch`. Devolvemos None (no
        propagamos la excepción), pero lo importante es que NO firma.
        """
        from cores.trading.dex.solana_wallet import SolanaWallet

        w = SolanaWallet()
        w._keypair = Keypair()  # keypair distinta a la que armó la tx

        assert w.sign_and_serialize(unsigned_tx_b64) is None

    def test_sin_keypair_devuelve_none_no_revienta(self, unsigned_tx_b64: str) -> None:
        from cores.trading.dex.solana_wallet import SolanaWallet

        w = SolanaWallet()
        w._keypair = None
        assert w.sign_and_serialize(unsigned_tx_b64) is None

    def test_basura_devuelve_none_no_revienta(self) -> None:
        """Una entrada inválida degrada a None; no propaga la excepción."""
        from cores.trading.dex.solana_wallet import SolanaWallet

        w = SolanaWallet()
        w._keypair = Keypair()
        assert w.sign_and_serialize("no-es-una-transaccion") is None
