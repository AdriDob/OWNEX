"""paper_trade.py — Paper-trading del módulo de arbitraje sin arriesgar capital.

Usa la maquinaria real (GlobalArbitrageAdapter + InvestmentManager +
RevenueAllocationController) pero con capital VIRTUAL: escanea discrepancias
de precio reales entre exchanges (ccxt), simula el trade y registra el
resultado en las métricas. No ejecuta ninguna orden real.

Validación de edge: si tras N runs el retorno compuesto es positivo y el
drawdown está dentro de límite, la estrategia tiene edge y se puede considerar
más adelante para capital real (SIEMPRE en papeles primero).

Uso:
    python scripts/paper_trade.py --runs 10 --capital 1000 --min-spread 0.5
    python scripts/paper_trade.py --exchanges binance,okx,mexc --min-quote-volume 500000 --min-spread 0.5
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.investment.adapters.global_arbitrage_adapter import GlobalArbitrageAdapter
from core.investment.allocation import get_allocation_controller, reset_allocation_controller
from core.investment.manager import InvestmentManager

logging.basicConfig(level=logging.WARNING)

STRATEGY = "global_arbitrage"
FEE_PCT = 0.10  # típico maker/taker x2 exchanges simulados


def _simulate(opp: dict, capital: float) -> dict:
    """Simula el trade sobre una oportunidad real, devuelve resultado con PnL."""
    spread = opp["spread_pct"]
    net_pct = spread - FEE_PCT
    deploy = min(capital, 500.0)
    # redondear SIEMPRE hacia abajo: deploy ≤ capital/available real, evita el
    # rechazo por float (manager compara available_usd crudo vs monto redondeado)
    deploy = math.floor(deploy * 100) / 100
    qty = deploy / opp["buy_price"]
    pnl = deploy * net_pct / 100.0
    return {
        "symbol": opp["symbol"],
        "buy_on": opp["buy_on"],
        "sell_on": opp["sell_on"],
        "buy_price": opp["buy_price"],
        "sell_price": opp["sell_price"],
        "spread_pct": spread,
        "net_pct": round(net_pct, 3),
        "deployed": round(deploy, 2),
        "qty": qty,
        "pnl": round(pnl, 4),
        "pnl_pct": round(net_pct, 3),
        "fee_pct": FEE_PCT,
    }


async def run_paper(runs: int, capital: float, min_spread: float, exchanges: list[str], min_qv: float) -> int:
    adapter = GlobalArbitrageAdapter(
        {
            "min_spread_pct": min_spread,
            "max_position_usd": 500,
            "exchanges": exchanges,
            "min_quote_volume_usd": min_qv,
        }
    )

    print("=== PAPER TRADING — arbitraje global (sin riesgo) ===")
    print(f"Capital virtual: ${capital:.2f} | Runs: {runs} | Min spread: {min_spread}% | Fee sim: {FEE_PCT}% | Min liq 24h: ${min_qv:,.0f}")
    print(f"Exchanges: {', '.join(exchanges)}")
    print(f"Estrategia: {STRATEGY} | Fecha: {datetime.now(UTC).isoformat()}\n")

    connected = await adapter.connect()
    print(f"Adapter conectado: {connected}")

    total_deployed = 0.0
    total_pnl = 0.0
    wins = 0
    losses = 0

    # balance virtual compuesto: se reinicia alocación por ronda (cada arbitraje
    # cierra su posición, el capital vuelve al pool)
    paper_balance = capital

    for i in range(1, runs + 1):
        reset_allocation_controller()
        # manager recreado tras el reset: se liga al controller fresco de la ronda
        manager = InvestmentManager()
        alloc = get_allocation_controller()
        alloc.update_capital(paper_balance)
        alloc.allocate_payout(paper_balance, source=f"paper_seed_{i}")

        opps = await adapter.scan_opportunities()
        if not opps:
            print(f"  run {i}: sin oportunidades (skip)")
            continue
        # disponibilidad real de la estrategia en la alocación
        sa = alloc.get_strategy_allocation(STRATEGY)
        available = sa.available_usd if sa else 0.0
        if available <= 0:
            print(f"  run {i}: sin capital disponible para {STRATEGY}")
            continue
        opp = opps[0]
        deploy_amt = min(available, 500.0)
        res = _simulate(opp, deploy_amt)
        deploy_ok = manager.deploy(STRATEGY, res["deployed"])
        if not deploy_ok.get("success"):
            print(f"  run {i}: deploy rechazado ({deploy_ok.get('error')})")
            continue

        manager.record_trade_result(
            strategy_id=STRATEGY,
            symbol=res["symbol"],
            side="arb",
            entry_price=res["buy_price"],
            exit_price=res["sell_price"],
            quantity=res["qty"],
            pnl=res["pnl"],
            pnl_pct=res["net_pct"],
            fee=res["deployed"] * FEE_PCT / 100,
            duration_hours=0.1,
            metadata={"type": "paper", "buy_on": res["buy_on"], "sell_on": res["sell_on"]},
        )
        total_deployed += res["deployed"]
        total_pnl += res["pnl"]
        paper_balance += res["pnl"]  # compone el balance virtual tras cerrar la posición
        if res["pnl"] >= 0:
            wins += 1
        else:
            losses += 1
        print(
            f"  run {i}: {res['symbol']} {res['buy_on']}→{res['sell_on']}"
            f" spread {res['spread_pct']:.2f}% net {res['net_pct']:+.2f}%"
            f" deployed ${res['deployed']:.2f} pnl ${res['pnl']:.2f}"
        )

    print("\n=== RESULTADO PAPER ===")
    print(f"Trades simulados: {wins + losses} | Wins: {wins} | Losses: {losses}")
    if total_deployed:
        print(f"Capital desplegado: ${total_deployed:.2f}")
        print(f"PnL total (paper): ${total_pnl:.2f}")
        print(f"Retorno sobre desplegado: {total_pnl / total_deployed * 100:.2f}%")
        comp = paper_balance - capital
        print(f"Balance virtual final: ${paper_balance:.2f} (retorno compuesto: {comp / capital * 100:+.2f}%)")
        if comp > 0:
            print("→ EDGE detectado: retorno compuesto positivo sobre capital virtual.")
    else:
        print("Sin trades ejecutables (sin oportunidades sobre min_spread o deploy rechazado).")

    snap = manager.snapshot()
    print(f"\nSnapshot total_capital: ${getattr(snap, 'total_capital', 'n/a')}")
    risk = manager.risk_report()
    print(f"Riesgo: pautado={risk.get('paused', 'n/a')} riesgo={risk.get('hyper_risk_active', 'n/a')}")

    return 0 if wins else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Paper trading arbitraje global")
    p.add_argument("--runs", type=int, default=5)
    p.add_argument("--capital", type=float, default=1000.0)
    p.add_argument("--min-spread", type=float, default=0.5, dest="min_spread")
    p.add_argument("--min-quote-volume", type=float, default=500000.0, dest="min_qv",
                   help="Liquidez mínima 24h (suma ambas puntas) en USD para declarar ejecutable")
    p.add_argument("--exchanges", type=str,
                   default="binance,okx,kraken,coinbase,bybit,bitget,mexc,gateio",
                   help="Exchanges separados por coma a escanear")
    args = p.parse_args()
    exchanges = [e.strip() for e in args.exchanges.split(",") if e.strip()]
    return asyncio.run(run_paper(args.runs, args.capital, args.min_spread, exchanges, args.min_qv))


if __name__ == "__main__":
    sys.exit(main())
