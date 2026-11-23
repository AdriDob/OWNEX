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

# El neto solo se declara COMPLETE cuando el slippage se MIDIÓ contra el libro
# real de ambos exchanges. Si el libro no está disponible o su profundidad no
# absorbe el tamaño, la ronda queda PARTIAL: sin slippage observado no hay neto
# definitivo.
COMPLETE = "COMPLETE"
PARTIAL = "PARTIAL"
# Distinto de PARTIAL: la pata de compra tiene precio de fill y la de venta no
# tiene dónde llenar. La posición queda abierta y sin resultado realizado, así
# que no hay PnL que registrar ni siquiera de forma provisional.
LEG_UNHEDGED = "LEG_UNHEDGED"


def _quote_currency(symbol: str) -> str:
    """Quote asset de un par estilo CCXT (``BTC/USDT`` -> ``USDT``).

    Devuelve "" si el símbolo no expone el quote: mejor un trade sin atribuir que
    una moneda inventada.
    """
    base, sep, quote = symbol.partition("/")
    return quote.upper() if sep and base and quote else ""


def _simulate(opp: dict, capital: float, execution: dict | None = None) -> dict:
    """Simula el trade sobre una oportunidad real, devuelve resultado con PnL.

    ``execution`` es la medición de ``measure_slippage`` sobre los libros reales.
    Si está medida, el bruto es el spread REMANENTE al segundo fill
    (``residual_spread_pct``): el spread del scan es solo la promesa del momento
    de detección, y la diferencia entre ambos es el costo de ejecución
    (profundidad de los libros + deriva de la segunda pata mientras la primera
    llenaba). Si no hay medición, se usa el spread del scan y ``costs_complete``
    queda False: el neto es provisional, no definitivo.

    Si la pata de venta no pudo llenarse (``leg_unhedged``), no hay simulación de
    cierre posible: se devuelve el resultado con ``leg_unhedged=True`` y sin
    ninguna cifra realizada (``realized_spread_pct``/``net_pct``/``gross_pnl`` en
    None). Cualquier número ahí sería inventado: la posición sigue abierta y su
    resultado depende de un precio de salida que todavía no existe.
    """
    scan_spread = opp["spread_pct"]
    deploy = min(capital, 500.0)
    # redondear SIEMPRE hacia abajo: deploy ≤ capital/available real, evita el
    # rechazo por float (manager compara available_usd crudo vs monto redondeado)
    deploy = math.floor(deploy * 100) / 100
    if execution and execution.get("leg_unhedged"):
        # Pata 1 con fill, pata 2 sin profundidad: exposición abierta, no trade.
        fill_price = float(execution.get("buy_fill_price") or opp["buy_price"])
        return {
            "symbol": opp["symbol"],
            "buy_on": opp["buy_on"],
            "sell_on": opp["sell_on"],
            "buy_price": opp["buy_price"],
            "sell_price": opp["sell_price"],
            "spread_pct": scan_spread,
            "realized_spread_pct": None,
            "net_pct": None,
            "deployed": round(deploy, 2),
            "qty": deploy / fill_price,
            "fill_price": fill_price,
            "pnl": 0.0,
            "pnl_pct": 0.0,
            "gross_pnl": None,
            "fee_pct": FEE_PCT,
            "fee_usd": 0.0,
            "slippage_pct": 0.0,
            "slippage_usd": 0.0,
            "depth_slippage_pct": 0.0,
            "drift_pct": 0.0,
            "execution_gap_s": float(execution.get("leg_gap_seconds") or 0.0),
            "unhedged_value_usd": round(float(execution.get("unhedged_value_usd") or deploy), 2),
            "unhedged_reason": str(execution.get("reason") or ""),
            "costs_complete": False,
            "leg_unhedged": True,
        }

    exec_metrics: dict = execution or {}
    measured = bool(exec_metrics.get("measured"))
    if measured:
        realized_spread = float(exec_metrics["residual_spread_pct"])
        execution_cost_pct = scan_spread - realized_spread
        fill_price = float(exec_metrics["buy_fill_price"])
    else:
        realized_spread = scan_spread
        execution_cost_pct = 0.0
        fill_price = opp["buy_price"]

    net_pct = realized_spread - FEE_PCT
    qty = deploy / fill_price
    # el bruto se declara contra el spread del scan: así el costo de ejecución
    # queda como componente propio y gross - fee - ejecución concilia con el neto
    gross_pnl = deploy * scan_spread / 100.0
    fee_usd = deploy * FEE_PCT / 100.0
    execution_cost_usd = deploy * execution_cost_pct / 100.0
    net_pnl = gross_pnl - fee_usd - execution_cost_usd
    metrics = exec_metrics
    return {
        "symbol": opp["symbol"],
        "buy_on": opp["buy_on"],
        "sell_on": opp["sell_on"],
        "buy_price": opp["buy_price"],
        "sell_price": opp["sell_price"],
        "spread_pct": scan_spread,
        "realized_spread_pct": round(realized_spread, 4),
        "net_pct": round(net_pct, 3),
        "deployed": round(deploy, 2),
        "qty": qty,
        "pnl": round(net_pnl, 4),
        "pnl_pct": round(net_pct, 3),
        "gross_pnl": round(gross_pnl, 4),
        "fee_pct": FEE_PCT,
        "fee_usd": round(fee_usd, 4),
        "slippage_pct": round(execution_cost_pct, 4),
        "slippage_usd": round(execution_cost_usd, 4),
        "depth_slippage_pct": round(float(metrics.get("depth_slippage_pct") or 0.0), 4),
        "drift_pct": round(float(metrics.get("drift_pct") or 0.0), 4),
        "execution_gap_s": float(metrics.get("leg_gap_seconds") or 0.0),
        "costs_complete": measured,
        "leg_unhedged": False,
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
    total_unhedged = 0.0
    wins = 0
    losses = 0
    unhedged = 0

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
        # costo de ejecución medido sobre el libro real de ambas puntas, en orden
        # de fill; si no se puede medir, la ronda queda PARTIAL (sin neto definitivo)
        execution = await adapter.measure_slippage(opp, deploy_amt)
        if execution.get("leg_unhedged"):
            print(f"  run {i}: LEG_UNHEDGED ({execution.get('reason')}) -> sin PnL realizado")
        elif not execution.get("measured"):
            print(f"  run {i}: ejecución NO medible ({execution.get('reason')}) -> neto parcial")
        res = _simulate(opp, deploy_amt, execution=execution)
        deploy_ok = manager.deploy(STRATEGY, res["deployed"])
        if not deploy_ok.get("success"):
            print(f"  run {i}: deploy rechazado ({deploy_ok.get('error')})")
            continue

        if res["leg_unhedged"]:
            # La ronda quedó abierta: se registra el HECHO (posición sin cubrir)
            # sin resultado realizado. pnl 0.0 es un marcador, no una medición;
            # LEG_UNHEDGED lo mantiene fuera de todo agregado realizado.
            manager.record_trade_result(
                strategy_id=STRATEGY,
                symbol=res["symbol"],
                side="arb",
                entry_price=res["fill_price"],
                exit_price=None,  # no hubo salida: no se inventa un precio
                quantity=res["qty"],
                pnl=0.0,
                pnl_pct=0.0,
                fee=0.0,
                duration_hours=0.0,
                metadata={
                    "type": "paper",
                    "buy_on": res["buy_on"],
                    "sell_on": res["sell_on"],
                    "leg_unhedged": True,
                    "unhedged_reason": res["unhedged_reason"],
                    "unhedged_value_usd": res["unhedged_value_usd"],
                    "buy_fill_price": res["fill_price"],
                    "execution_gap_s": res["execution_gap_s"],
                    "exchange": res["buy_on"],
                    "asset": res["symbol"].partition("/")[0].upper(),
                },
                currency=_quote_currency(res["symbol"]),
                net_pnl_completeness=LEG_UNHEDGED,
            )
            unhedged += 1
            total_unhedged += res["unhedged_value_usd"]
            print(
                f"  run {i}: {res['symbol']} {res['buy_on']}→{res['sell_on']}"
                f" spread {res['spread_pct']:.2f}% sin cubrir ${res['unhedged_value_usd']:.2f}"
                f" ({res['unhedged_reason']})"
            )
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
            # pnl es NETO de fee y slippage; los componentes viajan en metadata
            # para que la atribución pueda conciliar gross - fee - slippage
            fee=res["fee_usd"],
            duration_hours=0.1,
            metadata={
                "type": "paper",
                "buy_on": res["buy_on"],
                "sell_on": res["sell_on"],
                # gross_pnl es el spread del scan; slippage absorbe el costo de
                # ejecución (profundidad + deriva de la 2da pata) para que
                # gross - fee - slippage == pnl
                "gross_pnl": res["gross_pnl"],
                "slippage": res["slippage_usd"],
                "slippage_pct": res["slippage_pct"],
                "depth_slippage_pct": res["depth_slippage_pct"],
                "drift_pct": res["drift_pct"],
                "realized_spread_pct": res["realized_spread_pct"],
                "execution_gap_s": res["execution_gap_s"],
                "costs_complete": res["costs_complete"],
                "exchange": res["buy_on"],
                "asset": res["symbol"].partition("/")[0].upper(),
                **({"slippage_source": "measured_sequenced_order_book"} if res["costs_complete"] else {}),
            },
            currency=_quote_currency(res["symbol"]),
            net_pnl_completeness=COMPLETE if res["costs_complete"] else PARTIAL,
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
            f" spread {res['spread_pct']:.2f}% real {res['realized_spread_pct']:.2f}%"
            f" net {res['net_pct']:+.2f}% deployed ${res['deployed']:.2f} pnl ${res['pnl']:.2f}"
        )

    print("\n=== RESULTADO PAPER ===")
    print(f"Trades simulados: {wins + losses} | Wins: {wins} | Losses: {losses}")
    if unhedged:
        print(f"Rondas LEG_UNHEDGED: {unhedged} | Exposición abierta: ${total_unhedged:.2f} (sin resultado realizado)")
    if total_deployed:
        print(f"Capital desplegado: ${total_deployed:.2f}")
        print(f"PnL total (paper): ${total_pnl:.2f}")
        print(f"Retorno sobre desplegado: {total_pnl / total_deployed * 100:.2f}%")
        comp = paper_balance - capital
        print(f"Balance virtual final: ${paper_balance:.2f} (retorno compuesto: {comp / capital * 100:+.2f}%)")
        if comp > 0:
            print("→ EDGE detectado: retorno compuesto positivo sobre capital virtual.")
    elif unhedged:
        print("Sin rondas cerradas: solo hubo exposición abierta (LEG_UNHEDGED).")
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
    p.add_argument(
        "--min-quote-volume",
        type=float,
        default=500000.0,
        dest="min_qv",
        help="Liquidez mínima 24h (suma ambas puntas) en USD para declarar ejecutable",
    )
    p.add_argument(
        "--exchanges",
        type=str,
        default="binance,okx,kraken,coinbase,bybit,bitget,mexc,gateio",
        help="Exchanges separados por coma a escanear",
    )
    args = p.parse_args()
    exchanges = [e.strip() for e in args.exchanges.split(",") if e.strip()]
    return asyncio.run(run_paper(args.runs, args.capital, args.min_spread, exchanges, args.min_qv))


if __name__ == "__main__":
    sys.exit(main())
