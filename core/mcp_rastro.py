#!/usr/bin/env python3
"""Rastro (bug bounty) tools for the OWNEX MCP bridge.

Exposes the Rastro data layer to MCP clients so an agent can inspect and operate
the bug bounty system: targets, findings, validation verdicts and reports.

Every tool is a thin adapter over the canonical service layer; no query is
re-implemented here:

  - api.services.data_service      → targets, findings, verdicts, writes
  - cores.pipeline.report_service  → reports
  - database.db / database.models  → aggregate status counters only

The bridge discovers these tools through build_rastro_tools() and dispatches
handlers through resolve_rastro_handler(), so this module can grow without
touching the bridge's own tool definitions.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

logger = logging.getLogger("ownex.mcp_bridge.rastro")


def _data_service():
    """Import the Rastro data service lazily.

    Kept lazy so importing the bridge stays cheap and the MCP server does not
    pull the whole API service graph at startup.
    """
    from api.services import data_service

    return data_service


def _open_session():
    """Open a Rastro DB session using the canonical database module."""
    from database import db

    db.init_db()
    return db.SessionLocal()


def _bucket(session, column) -> dict[str, int]:
    """Group rows by a column and return ``{value: count}``."""
    from sqlalchemy import func

    rows = session.query(column, func.count()).group_by(column).all()
    buckets: dict[str, int] = {}
    for value, count in rows:
        key = "unknown" if value is None else str(value).lower() if isinstance(value, bool) else str(value)
        buckets[key] = buckets.get(key, 0) + int(count)
    return buckets


# ── Tool definitions ────────────────────────────────────────────────


def build_rastro_tools() -> dict[str, Any]:
    """Build the Rastro tool definitions for the MCP bridge.

    Returns:
        Mapping of tool name to McpToolDefinition.
    """
    from core.mcp_bridge import McpToolCategory, McpToolDefinition

    category = McpToolCategory.BUG_BOUNTY
    tools: dict[str, McpToolDefinition] = {}

    tools["list_targets"] = McpToolDefinition(
        name="list_targets",
        description="List Rastro bug bounty targets with endpoint/finding counts, estimated payout, ROI and risk score",
        category=category,
        parameters={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum targets to return (default 50)"},
                "search": {"type": "string", "description": "Filter by target name or domain"},
            },
            "required": [],
        },
        returns={
            "type": "object",
            "properties": {
                "targets": {"type": "array", "items": {"type": "object"}},
                "total": {"type": "integer"},
                "data_source": {"type": "string"},
            },
            "required": ["targets", "total"],
        },
        handler="list_targets_tool",
    )

    tools["get_target"] = McpToolDefinition(
        name="get_target",
        description="Get one Rastro target in detail: endpoints, findings, confirmed count, attack surfaces and vectors",
        category=category,
        parameters={
            "type": "object",
            "properties": {"target_id": {"type": "integer", "description": "Target ID"}},
            "required": ["target_id"],
        },
        returns={
            "type": "object",
            "properties": {"target": {"type": "object"}, "found": {"type": "boolean"}},
            "required": ["target", "found"],
        },
        handler="get_target_tool",
    )

    tools["list_findings"] = McpToolDefinition(
        name="list_findings",
        description="List Rastro findings with severity, target, endpoint and estimated payout",
        category=category,
        parameters={
            "type": "object",
            "properties": {
                "target_id": {"type": "integer", "description": "Filter by target ID"},
                "search": {"type": "string", "description": "Filter by title or severity"},
                "limit": {"type": "integer", "description": "Maximum findings to return (default 50)"},
            },
            "required": [],
        },
        returns={
            "type": "object",
            "properties": {
                "findings": {"type": "array", "items": {"type": "object"}},
                "total": {"type": "integer"},
            },
            "required": ["findings", "total"],
        },
        handler="list_findings_tool",
    )

    tools["list_verdicts"] = McpToolDefinition(
        name="list_verdicts",
        description="List validation verdicts (confirmed/rejected/inconclusive) with confidence scores",
        category=category,
        parameters={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["confirmed", "rejected", "inconclusive", "pending"],
                    "description": "Filter by verdict status",
                },
                "target_id": {"type": "integer", "description": "Filter by target ID"},
                "confidence_min": {"type": "number", "description": "Minimum confidence score (0-1)"},
                "limit": {"type": "integer", "description": "Maximum verdicts to return (default 50)"},
            },
            "required": [],
        },
        returns={
            "type": "object",
            "properties": {"verdicts": {"type": "array", "items": {"type": "object"}}, "total": {"type": "integer"}},
            "required": ["verdicts", "total"],
        },
        handler="list_verdicts_tool",
    )

    tools["list_reports"] = McpToolDefinition(
        name="list_reports",
        description="List generated reports with status, severity, estimated and confirmed rewards",
        category=category,
        parameters={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by report status (draft, ready, submitted, triaged, paid, duplicate, ...)",
                },
                "search": {"type": "string", "description": "Filter by program, target or vulnerability"},
                "limit": {"type": "integer", "description": "Maximum reports to return (default 20)"},
            },
            "required": [],
        },
        returns={
            "type": "object",
            "properties": {"reports": {"type": "array", "items": {"type": "object"}}, "total": {"type": "integer"}},
            "required": ["reports", "total"],
        },
        handler="list_reports_tool",
    )

    tools["get_bounty_status"] = McpToolDefinition(
        name="get_bounty_status",
        description="Aggregate Rastro hive status: active targets, findings by severity, verdicts by status, reports by status and rewards",
        category=category,
        parameters={"type": "object", "properties": {}, "required": []},
        returns={
            "type": "object",
            "properties": {
                "targets": {"type": "object"},
                "findings": {"type": "object"},
                "verdicts": {"type": "object"},
                "reports": {"type": "object"},
                "data_source": {"type": "string"},
            },
            "required": ["targets", "findings", "verdicts", "reports"],
        },
        handler="get_bounty_status_tool",
    )

    tools["create_target"] = McpToolDefinition(
        name="create_target",
        description="Create a Rastro target (mutates the database; returns the existing row if the name already exists)",
        category=category,
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Target name"},
                "domain": {"type": "string", "description": "Target domain"},
            },
            "required": ["name"],
        },
        returns={
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "domain": {"type": "string"},
                "duplicate": {"type": "boolean"},
            },
            "required": ["id", "name"],
        },
        handler="create_target_tool",
    )

    tools["create_finding"] = McpToolDefinition(
        name="create_finding",
        description="Record a Rastro finding on a target (mutates the database)",
        category=category,
        parameters={
            "type": "object",
            "properties": {
                "target_id": {"type": "integer", "description": "Existing target ID"},
                "title": {"type": "string", "description": "Finding title"},
                "severity": {
                    "type": "string",
                    "enum": ["critical", "high", "medium", "low", "info"],
                    "description": "Severity (default medium)",
                },
                "description": {"type": "string", "description": "Technical description and impact"},
                "endpoint_id": {"type": "integer", "description": "Existing endpoint ID, if known"},
            },
            "required": ["target_id", "title"],
        },
        returns={
            "type": "object",
            "properties": {"id": {"type": "integer"}, "title": {"type": "string"}, "severity": {"type": "string"}},
            "required": ["id", "title"],
        },
        handler="create_finding_tool",
    )

    return tools


# ── Handlers ────────────────────────────────────────────────────────


def list_targets_tool(limit: int = 50, search: str = "") -> dict[str, Any]:
    """Handle the list_targets MCP tool."""
    targets, total = _data_service().list_targets(limit=limit, search=search)

    # The service does not report the active flag; fetch it for the returned page.
    if targets:
        from database import models

        session = _open_session()
        try:
            ids = [t["id"] for t in targets]
            active_map = {row[0]: bool(row[1]) for row in session.query(models.Target.id, models.Target.active).filter(models.Target.id.in_(ids)).all()}
        finally:
            session.close()
        for target in targets:
            target["active"] = active_map.get(target["id"], False)

    return {"targets": targets, "total": total, "data_source": "rastro_database"}


def get_target_tool(target_id: int) -> dict[str, Any]:
    """Handle the get_target MCP tool."""
    target = _data_service().get_target(target_id)
    if target is None:
        return {"found": False, "target": {}, "error": f"Target {target_id} not found"}
    return {"found": True, "target": target}


def list_findings_tool(target_id: int | None = None, search: str = "", limit: int = 50) -> dict[str, Any]:
    """Handle the list_findings MCP tool."""
    findings, total = _data_service().list_findings(target_id=target_id, search=search, limit=limit)
    return {"findings": findings, "total": total, "data_source": "rastro_database"}


def list_verdicts_tool(
    status: str | None = None,
    target_id: int | None = None,
    confidence_min: float = 0.0,
    limit: int = 50,
) -> dict[str, Any]:
    """Handle the list_verdicts MCP tool."""
    verdicts = _data_service().list_verdicts(
        status=status,
        confidence_min=confidence_min,
        target_id=target_id,
        limit=limit,
    )
    return {"verdicts": verdicts, "total": len(verdicts), "data_source": "rastro_database"}


def list_reports_tool(status: str | None = None, search: str | None = None, limit: int = 20) -> dict[str, Any]:
    """Handle the list_reports MCP tool."""
    from cores.pipeline.report_service import list_reports

    session = _open_session()
    try:
        reports, total = list_reports(session, limit=limit, status_filter=status, search=search)
    finally:
        session.close()
    return {"reports": reports, "total": total, "data_source": "rastro_database"}


def get_bounty_status_tool() -> dict[str, Any]:
    """Handle the get_bounty_status MCP tool."""
    from sqlalchemy import func

    from database import models

    session = _open_session()
    try:
        active_counts = _bucket(session, models.Target.active)
        findings_by_severity = _bucket(session, models.Finding.severity)
        verdicts_by_status = _bucket(session, models.Verdict.status)
        reports_by_status = _bucket(session, models.Report.status)

        return {
            "targets": {
                "total": sum(active_counts.values()),
                "active": active_counts.get("true", 0),
            },
            "findings": {
                "total": sum(findings_by_severity.values()),
                "by_severity": findings_by_severity,
            },
            "verdicts": {
                "total": sum(verdicts_by_status.values()),
                "by_status": verdicts_by_status,
                "confirmed": verdicts_by_status.get("confirmed", 0),
                "pending": verdicts_by_status.get("pending", 0),
            },
            "reports": {
                "total": sum(reports_by_status.values()),
                "by_status": reports_by_status,
                "estimated_reward": float(session.query(func.sum(models.Report.estimated_reward)).scalar() or 0.0),
                "confirmed_reward": float(session.query(func.sum(models.Report.confirmed_reward)).scalar() or 0.0),
            },
            "data_source": "rastro_database",
        }
    finally:
        session.close()


def create_target_tool(name: str, domain: str | None = None) -> dict[str, Any]:
    """Handle the create_target MCP tool."""
    result = _data_service().create_target(name=name, domain=domain)
    result.setdefault("duplicate", False)
    return result


def create_finding_tool(
    target_id: int,
    title: str,
    severity: str = "medium",
    description: str | None = None,
    endpoint_id: int | None = None,
) -> dict[str, Any]:
    """Handle the create_finding MCP tool."""
    return _data_service().create_finding(
        target_id=target_id,
        title=title,
        severity=severity,
        description=description,
        endpoint_id=endpoint_id,
    )


_HANDLERS: dict[str, Callable[..., dict[str, Any]]] = {
    "list_targets_tool": list_targets_tool,
    "get_target_tool": get_target_tool,
    "list_findings_tool": list_findings_tool,
    "list_verdicts_tool": list_verdicts_tool,
    "list_reports_tool": list_reports_tool,
    "get_bounty_status_tool": get_bounty_status_tool,
    "create_target_tool": create_target_tool,
    "create_finding_tool": create_finding_tool,
}


def resolve_rastro_handler(name: str) -> Callable[..., dict[str, Any]] | None:
    """Resolve a Rastro tool handler by its declared name.

    Args:
        name: Handler name as declared in the tool definition.

    Returns:
        The handler callable, or None if this module does not provide it.
    """
    return _HANDLERS.get(name)
