"""OWNEX MCP Server — read-only tools for external agents (Perch Desktop/CLI).

Exposes ONLY allowlisted, read-scoped OWNEX data over the MCP stdio
transport. No write, trade, withdraw, or credential access — ever.

Run:  python -m core.mcp_ownex_server
Config for Perch (~/.perch/mcp.json or .perch/mcp.json):
  {"mcpServers": {"ownex": {"command": "python", "args": ["-m", "core.mcp_ownex_server"],
   "cwd": "/path/to/Rastro"}}}

Privacy: financial data stays local unless the user explicitly points an
agent at this server. No secrets are ever returned — the vault never
decrypts into tool payloads.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from cores.connections import mcp_consent

logger = logging.getLogger("ownex.mcp_server")

server = Server("ownex")

# ── Tool catalog (read-only allowlist) ─────────────────────────────────

TOOLS: list[Tool] = [
    Tool(
        name="get_ownex_status",
        description="Estado general de OWNEX: providers en catálogo, conectados, con datos normalizados.",
        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    Tool(
        name="list_connected_providers",
        description="Lista providers del catálogo con su estado de conexión real (sin secretos).",
        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    Tool(
        name="get_connection_status",
        description="Estado detallado de un provider: dominio, método, último sync, errores.",
        inputSchema={
            "type": "object",
            "properties": {"provider": {"type": "string"}},
            "required": ["provider"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_portfolio_snapshot",
        description="Cartera consolidada normalizada: saldos por moneda y providers con datos (sin conversión FX).",
        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
    Tool(
        name="get_portfolio_positions",
        description="Posiciones normalizadas de un provider (ticker, cantidad, precio, valor, moneda).",
        inputSchema={
            "type": "object",
            "properties": {"provider": {"type": "string"}},
            "required": ["provider"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_cash_balances",
        description="Saldos por moneda de un provider o consolidado si provider='all'.",
        inputSchema={
            "type": "object",
            "properties": {"provider": {"type": "string", "default": "all"}},
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_transaction_history",
        description="Movimientos/operaciones normalizados de un provider (máx 200).",
        inputSchema={
            "type": "object",
            "properties": {"provider": {"type": "string"}},
            "required": ["provider"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_last_sync_results",
        description="Historial de sincronizaciones/importaciones de un provider.",
        inputSchema={
            "type": "object",
            "properties": {"provider": {"type": "string"}},
            "required": ["provider"],
            "additionalProperties": False,
        },
    ),
    Tool(
        name="get_data_quality_report",
        description="Errores parciales y cobertura de datos normalizados por provider.",
        inputSchema={"type": "object", "properties": {}, "additionalProperties": False},
    ),
]


# ── Data accessors (read-only, lazy imports keep startup cheap) ────────


def _catalog_meta() -> dict[str, dict[str, Any]]:
    from cores.connections.catalog import AI_TOOLS, INFRA, INVESTMENT_AR

    merged = {**INVESTMENT_AR, **AI_TOOLS, **INFRA}
    return {k: v.as_dict() for k, v in merged.items()}


def _provider_state(provider: str) -> dict[str, Any] | None:
    from cores.identity_vault import get_identity_vault

    vault = get_identity_vault()
    account = vault.get_account(provider)
    if not account:
        return None
    return {
        "provider": provider,
        "state": account.get("session_state") or account.get("health_status") or "unknown",
        "has_credentials": account.get("has_credentials", False),
        "last_sync_at": account.get("last_sync_at"),
        "last_sync_meta": account.get("last_sync_meta"),
        "email": account.get("email"),
    }


def _normalized(provider: str) -> dict[str, Any] | None:
    from cores.connections import financial_normalizer

    return financial_normalizer.load_normalized(provider)


# ── Tool handlers ──────────────────────────────────────────────────────


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a read-only tool. Returns a JSON-serializable payload."""
    if name == "get_ownex_status":
        from cores.connections import financial_normalizer

        catalog = _catalog_meta()
        normalized_dir = financial_normalizer._norm_dir()
        with_data = [p.stem for p in normalized_dir.glob("*.json")] if normalized_dir.exists() else []
        return {
            "catalog_providers": len(catalog),
            "domains": sorted({m.get("domain") for m in catalog.values()}),
            "providers_with_normalized_data": with_data,
        }

    if name == "list_connected_providers":
        catalog = _catalog_meta()
        out = []
        for provider, meta in catalog.items():
            state = _provider_state(provider) or {}
            out.append(
                {
                    "provider": provider,
                    "domain": meta.get("domain"),
                    "integration_method": meta.get("integration_method"),
                    "sync_mode": meta.get("sync_mode"),
                    "connected": bool(state.get("has_credentials")),
                    "state": state.get("state", "NOT_CONNECTED"),
                    "last_sync_at": state.get("last_sync_at"),
                }
            )
        return {"providers": out}

    if name == "get_connection_status":
        provider = str(arguments.get("provider", ""))
        meta = _catalog_meta().get(provider)
        if not meta:
            return {"error": f"provider desconocido: {provider}"}
        return {"provider": provider, "setup": meta, "state": _provider_state(provider)}

    if name == "get_portfolio_snapshot":
        from cores.connections import financial_normalizer

        return financial_normalizer.consolidated_portfolio()

    if name == "get_portfolio_positions":
        data = _normalized(str(arguments.get("provider", "")))
        if data is None:
            return {"error": "sin datos normalizados para ese provider"}
        return {"provider": data["provider"], "positions": data.get("positions", []), "normalized_at": data.get("normalized_at")}

    if name == "get_cash_balances":
        provider = str(arguments.get("provider", "all"))
        if provider == "all":
            from cores.connections import financial_normalizer

            return financial_normalizer.consolidated_portfolio()
        data = _normalized(provider)
        if data is None:
            return {"error": "sin datos normalizados para ese provider"}
        return {"provider": provider, "cash_by_currency": data.get("cash_by_currency", {}), "normalized_at": data.get("normalized_at")}

    if name == "get_transaction_history":
        data = _normalized(str(arguments.get("provider", "")))
        if data is None:
            return {"error": "sin datos normalizados para ese provider"}
        txs = data.get("transactions", [])[-200:]
        return {"provider": data["provider"], "count": len(txs), "transactions": txs}

    if name == "get_last_sync_results":
        provider = str(arguments.get("provider", ""))
        from cores.connections.snapshots import load_snapshot
        from cores.connections.sync_history import get_history

        return {
            "provider": provider,
            "history": get_history(provider, 50),
            "has_snapshot": load_snapshot(provider) is not None,
        }

    if name == "get_data_quality_report":
        from cores.connections import financial_normalizer
        from cores.connections.snapshots import load_snapshot

        norm_dir = financial_normalizer._norm_dir()
        report = {}
        if norm_dir.exists():
            for path in sorted(norm_dir.glob("*.json")):
                try:
                    data = json.loads(path.read_text())
                except (json.JSONDecodeError, OSError):
                    continue
                provider = data.get("provider") or path.stem
                snap = load_snapshot(provider) or {}
                report[provider] = {
                    "position_count": data.get("position_count", 0),
                    "transaction_count": data.get("transaction_count", 0),
                    "partial_errors": snap.get("data", {}).get("partial_errors") if isinstance(snap, dict) else None,
                    "normalized_at": data.get("normalized_at"),
                }
        return {"providers": report}

    return {"error": f"tool desconocida o no permitida: {name}"}


# ── MCP protocol handlers ──────────────────────────────────────────────


async def _list_tools_handler(_request: types.ListToolsRequest, _ctx: Any) -> types.ListToolsResult:
    return types.ListToolsResult(tools=TOOLS)


async def _call_tool_handler(request: types.CallToolRequest, _ctx: Any) -> types.CallToolResult:
    name = request.params.name
    arguments = dict(request.params.arguments or {})
    provider = str(arguments.get("provider", ""))
    allowed, reason = mcp_consent.check_tool_allowed(name)
    if not allowed:
        mcp_consent.record_call(name, provider, "denied")
        result = {"error": reason, "denied": True}
        return types.CallToolResult(
            content=[TextContent(type="text", text=json.dumps(result))],
            structuredContent=result,
            isError=True,
        )
    try:
        result = call_tool(name, arguments)
        is_error = "error" in result
    except Exception as exc:
        logger.warning("MCP tool %s failed: %s", name, exc)
        result = {"error": f"falló la consulta: {exc}"}
        is_error = True
    mcp_consent.record_call(name, provider, "error" if is_error else "ok")
    return types.CallToolResult(
        content=[TextContent(type="text", text=json.dumps(result, default=str))],
        structuredContent=result,
        isError=is_error,
    )


server.add_request_handler("tools/list", types.ListToolsRequest, _list_tools_handler)
server.add_request_handler("tools/call", types.CallToolRequest, _call_tool_handler)


async def _amain() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
