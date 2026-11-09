"""Financial normalizer — provider snapshots/imports -> canonical models.

Reuses ``core.normalizer.base`` types (NormalizedPortfolio/Position/Transaction)
as the single canonical shape. Persisted per provider under
``OWNEX_DATA_DIR/connections/normalized/{provider}.json`` with provenance.

RULE: never sum nominal amounts across currencies. Values stay grouped by
currency; no invented FX rates.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cores.env.config import get_config

logger = logging.getLogger("ownex.connections.financial_normalizer")

try:
    from core.normalizer.base import NormalizedPortfolio, NormalizedPosition, NormalizedTransaction
except ImportError:  # pragma: no cover
    NormalizedPortfolio = NormalizedPosition = NormalizedTransaction = dict  # type: ignore[assignment]


def _norm_dir() -> Path:
    return get_config().data_dir / "connections" / "normalized"


def _num(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _currency_totals(records: list[dict[str, Any]], amount_key: str = "amount") -> dict[str, float]:
    totals: dict[str, float] = {}
    for r in records:
        cur = str(r.get("currency") or "UNKNOWN").upper()
        totals[cur] = totals.get(cur, 0.0) + _num(r.get(amount_key))
    return {k: round(v, 8) for k, v in totals.items() if v != 0}


# ── Provider snapshot -> normalized ─────────────────────────────────────


def normalize_iol(snapshot: dict[str, Any]) -> dict[str, Any]:
    # Real IOL shapes: positions -> {account, currency, positions:[{instrument, availability, cost_basis, market_value}]}
    # balances -> {ars: {available, totals, available_for_withdrawal}, usd: {...}}
    raw_positions = snapshot.get("positions") or {}
    if isinstance(raw_positions, dict):
        raw_positions = raw_positions.get("positions") or []
    positions: list[NormalizedPosition] = []
    for p in raw_positions or []:
        if not isinstance(p, dict):
            continue
        inst = p.get("instrument") or {}
        avail = p.get("availability") or {}
        cost = p.get("cost_basis") or {}
        mkt = p.get("market_value") or {}
        qty = _num(avail.get("quantity_available") or avail.get("quantity") or p.get("quantity") or p.get("amount"))
        positions.append(
            NormalizedPosition(
                symbol=str(inst.get("symbol") or p.get("ticker") or p.get("instrument") or ""),
                name=str(inst.get("name") or p.get("name") or p.get("description") or ""),
                asset_type=str(inst.get("asset_class") or inst.get("type") or p.get("type") or ""),
                quantity=qty,
                avg_price=_num(cost.get("average_entry_price") or p.get("average_price") or p.get("avg_price")),
                current_price=_num(mkt.get("current_price") or p.get("price") or p.get("current_price")),
                value=_num(mkt.get("value") or mkt.get("total") or p.get("value") or p.get("market_value")),
                currency=str(inst.get("currency") or p.get("currency") or "ARS"),
                exchange="iol",
                extra={
                    "total_cost": cost.get("total_cost"),
                    "price_change_percent": mkt.get("price_change_percent"),
                },
            )
        )
    cash_by_currency = _iol_cash(snapshot.get("balances"))
    quotes = snapshot.get("quotes") or {}
    for pos in positions:
        q = quotes.get(pos.symbol) or {}
        if isinstance(q, dict):
            price = _num(q.get("price") or q.get("last") or (q.get("data") or {}).get("price"))
            if price:
                if not pos.current_price:
                    pos.current_price = price
                if not pos.value and pos.quantity:
                    pos.value = round(pos.quantity * price, 8)
                pos.extra["quote_ts"] = q.get("timestamp") or q.get("fetched_at")
    return _envelope("iol", positions, cash_by_currency, snapshot.get("movements") or [])


def _iol_cash(balances: Any) -> dict[str, float]:
    """IOL balances: {ARS: {available:{t0..}, available_for_withdrawal}, USD: {...}}."""
    cash: dict[str, float] = {}
    if not isinstance(balances, dict):
        return cash
    for cur, block in balances.items():
        if not isinstance(block, dict):
            continue
        available = block.get("available") or {}
        amount = sum(_num(v) for v in available.values()) if isinstance(available, dict) else _num(available)
        if block.get("available_for_withdrawal") is not None:
            amount = _num(block["available_for_withdrawal"])
        cur_key = str(cur).upper()
        cash[cur_key] = cash.get(cur_key, 0.0) + amount
    return {k: round(v, 8) for k, v in cash.items() if v != 0}


def normalize_ppi(snapshot: dict[str, Any]) -> dict[str, Any]:
    positions: list[NormalizedPosition] = []
    cash: dict[str, float] = {}
    for acc in snapshot.get("account_details") or []:
        bp = acc.get("balances_and_positions") or {}
        grouped = bp.get("groupedInstruments") if isinstance(bp, dict) else None
        for group in grouped or []:
            for ins in group.get("instruments") or []:
                if not isinstance(ins, dict):
                    continue
                positions.append(
                    NormalizedPosition(
                        symbol=str(ins.get("ticker") or ""),
                        name=str(ins.get("name") or group.get("name") or ""),
                        asset_type=str(group.get("name") or ""),
                        quantity=_num(ins.get("amount")),
                        avg_price=_num(ins.get("averagePrice") or ins.get("avgPrice")),
                        current_price=_num(ins.get("price")),
                        value=_num(ins.get("value")),
                        currency=str(ins.get("currency") or "ARS"),
                        exchange="ppi",
                    )
                )
        for avail in (bp.get("groupedAvailability") if isinstance(bp, dict) else []) or []:
            for c in avail.get("availability") or []:
                cur = str(c.get("name") or c.get("currency") or "ARS").upper()
                cash[cur] = cash.get(cur, 0.0) + _num(c.get("amount"))
        for b in acc.get("available_balance") or []:
            if not isinstance(b, dict):
                continue
            cur = str(b.get("name") or b.get("currency") or "ARS").upper()
            cash.setdefault(cur, 0.0)
            cash[cur] += _num(b.get("amount"))
    transactions = _ppi_movements(snapshot)
    out = _envelope("ppi", positions, {k: round(v, 8) for k, v in cash.items() if v}, [])
    out["transactions"] = [t.__dict__ for t in transactions]
    out["transaction_count"] = len(transactions)
    return out


def _ppi_movements(snapshot: dict[str, Any]) -> list[NormalizedTransaction]:
    txs: list[NormalizedTransaction] = []
    for acc in snapshot.get("account_details") or []:
        for m in acc.get("movements") or []:
            if not isinstance(m, dict):
                continue
            txs.append(
                NormalizedTransaction(
                    tx_id=str(m.get("id") or ""),
                    symbol=str(m.get("ticker") or ""),
                    tx_type=str(m.get("type") or m.get("operation") or "movement"),
                    quantity=_num(m.get("quantity")),
                    price=_num(m.get("price")),
                    total=_num(m.get("amount")),
                    currency=str(m.get("currency") or "ARS"),
                    executed_at=str(m.get("settlementDate") or m.get("agreementDate") or ""),
                    platform="ppi",
                    extra={"description": m.get("description")},
                )
            )
    return txs


def normalize_binance(snapshot: dict[str, Any]) -> dict[str, Any]:
    positions: list[NormalizedPosition] = []
    balances = snapshot.get("balances") or {}
    total = balances.get("total") or {}
    free = balances.get("free") or {}
    quotes = snapshot.get("quotes") or {}
    for asset, qty in total.items():
        if not isinstance(qty, (int, float)) or qty == 0:
            continue
        quote = quotes.get(str(asset)) or {}
        price = _num(quote.get("last"))
        is_fiat = str(asset) in ("USDT", "USDC", "FDUSD", "BUSD")
        positions.append(
            NormalizedPosition(
                symbol=str(asset),
                asset_type="crypto",
                quantity=float(qty),
                current_price=price if price else (1.0 if is_fiat else 0.0),
                value=round(float(qty) * price, 8) if price else (float(qty) if is_fiat else 0.0),
                currency="USDT" if price or is_fiat else str(asset),
                exchange="binance",
                extra={"free": free.get(asset, 0.0), "quote_ts": quote.get("timestamp")},
            )
        )
    cash = {str(k): float(v) for k, v in total.items() if isinstance(v, (int, float)) and v != 0 and str(k) in ("USDT", "USDC", "FDUSD", "BUSD")}
    return _envelope("binance", positions, cash, [])


# ── Import records -> normalized transactions ───────────────────────────


def normalize_import_records(provider: str, records: list[dict[str, Any]]) -> list[NormalizedTransaction]:
    txs: list[NormalizedTransaction] = []
    for r in records:
        txs.append(
            NormalizedTransaction(
                tx_id=str(r.get("external_id") or r.get("_hash") or ""),
                symbol=str(r.get("ticker") or ""),
                tx_type=str(r.get("type") or "movement"),
                quantity=_num(r.get("amount") or r.get("quantity")),
                price=_num(r.get("price")),
                total=_num(r.get("amount")),
                currency=str(r.get("currency") or "ARS"),
                executed_at=str(r.get("date") or ""),
                platform=provider,
                extra={"description": r.get("description"), "batch_id": r.get("batch_id")},
            )
        )
    return txs


# ── Envelope / persistence ───────────────────────────────────────────────


def _envelope(
    provider: str,
    positions: list[NormalizedPosition],
    cash_by_currency: dict[str, float],
    raw_movements: list[Any],
) -> dict[str, Any]:
    transactions: list[NormalizedTransaction] = []
    for m in raw_movements or []:
        if isinstance(m, dict):
            transactions.append(
                NormalizedTransaction(
                    symbol=str(m.get("ticker") or m.get("instrument") or ""),
                    tx_type=str(m.get("type") or m.get("operation") or "movement"),
                    quantity=_num(m.get("quantity") or m.get("amount")),
                    price=_num(m.get("price")),
                    total=_num(m.get("amount") or m.get("value")),
                    currency=str(m.get("currency") or "ARS"),
                    executed_at=str(m.get("date") or m.get("settlementDate") or m.get("agreementDate") or ""),
                    platform=provider,
                    extra={"description": m.get("description")},
                )
            )
    return {
        "provider": provider,
        "normalized_at": datetime.now(UTC).isoformat(),
        "positions": [p.__dict__ if hasattr(p, "__dict__") else p for p in positions],
        "transactions": [t.__dict__ if hasattr(t, "__dict__") else t for t in transactions],
        "cash_by_currency": cash_by_currency,
        "position_count": len(positions),
        "transaction_count": len(transactions),
    }


def normalize_provider(provider: str, snapshot_data: dict[str, Any]) -> dict[str, Any]:
    """Dispatch on provider sync_mode/source to the right normalizer."""
    if provider == "iol":
        out = normalize_iol(snapshot_data)
    elif provider == "ppi":
        out = normalize_ppi(snapshot_data)
    elif provider == "binance":
        out = normalize_binance(snapshot_data)
    else:
        # manual/import providers: snapshot may contain positions list or records
        positions = snapshot_data.get("positions") or snapshot_data.get("holdings") or []
        norm_positions = [
            NormalizedPosition(
                symbol=str(p.get("ticker") or p.get("symbol") or ""),
                name=str(p.get("name") or p.get("description") or ""),
                quantity=_num(p.get("quantity") or p.get("amount")),
                avg_price=_num(p.get("avg_price") or p.get("average_price")),
                current_price=_num(p.get("price") or p.get("current_price")),
                value=_num(p.get("value") or p.get("market_value")),
                currency=str(p.get("currency") or "ARS"),
                exchange=provider,
            ).__dict__
            for p in positions
            if isinstance(p, dict)
        ]
        txs = normalize_import_records(provider, snapshot_data.get("records") or snapshot_data.get("movements") or [])
        out = {
            "provider": provider,
            "normalized_at": datetime.now(UTC).isoformat(),
            "positions": norm_positions,
            "transactions": [t.__dict__ for t in txs],
            "cash_by_currency": _currency_totals(snapshot_data.get("balances") or []),
            "position_count": len(norm_positions),
            "transaction_count": len(txs),
        }
    save_normalized(provider, out)
    return out


def save_normalized(provider: str, payload: dict[str, Any]) -> None:
    path = _norm_dir() / f"{provider}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str))


def load_normalized(provider: str) -> dict[str, Any] | None:
    path = _norm_dir() / f"{provider}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def consolidated_portfolio() -> dict[str, Any]:
    """Merge normalized data across providers — per-currency, no FX mixing."""
    norm_dir = _norm_dir()
    providers: dict[str, Any] = {}
    if norm_dir.exists():
        for path in sorted(norm_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                continue
            providers[data.get("provider") or path.stem] = {
                "position_count": data.get("position_count", 0),
                "transaction_count": data.get("transaction_count", 0),
                "cash_by_currency": data.get("cash_by_currency", {}),
                "normalized_at": data.get("normalized_at"),
            }
    cash_totals: dict[str, float] = {}
    for pdata in providers.values():
        for cur, amt in (pdata.get("cash_by_currency") or {}).items():
            cash_totals[cur] = cash_totals.get(cur, 0.0) + _num(amt)
    return {
        "providers": providers,
        "cash_by_currency": {k: round(v, 8) for k, v in cash_totals.items()},
        "provider_count": len(providers),
        "generated_at": datetime.now(UTC).isoformat(),
    }
