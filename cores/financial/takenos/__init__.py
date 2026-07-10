"""Takenos connector — virtual USD wallet for LATAM freelancers.

Takenos es una billetera virtual que permite recibir pagos internacionales
(ACH, wire, crypto) y retirar a bancos argentinos vía CBU.

API pública: No disponible actualmente.
Este connector soporta:
  - Balance manual (ingreso manual)
  - CSV import de extractos Takenos
  - Seguimiento on-chain de USDC en Solana (si se vincula wallet)
"""

from cores.financial.takenos.connector import TakenosConnector

__all__ = ["TakenosConnector"]
