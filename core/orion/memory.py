"""ORION CORE — Working memory layer over the existing Knowledge Graph.

Builds on ``core.knowledge.models`` (KGNode, KGEdge) to provide
a living-memory interface: observations, decisions, patterns, and facts
that ORION persists across OODA cycles and uses to make better decisions.

The underlying KG already has nodes and edges — this module provides
the ``remember`` / ``recall`` / ``forget`` API that ORION calls mid-cycle.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.orion.models import MemoryRecord

logger = logging.getLogger("ownex.orion.memory")

# ── TTL defaults (hours) ───────────────────────────────────────
TTL_OBSERVATION = 24 * 7  # 1 week
TTL_DECISION = 24 * 30  # 30 days
TTL_PATTERN = 24 * 90  # 90 days
TTL_FACT = 0  # permanent

_CATEGORY_TTL = {
    "observation": TTL_OBSERVATION,
    "decision": TTL_DECISION,
    "pattern": TTL_PATTERN,
    "fact": TTL_FACT,
}


def remember(
    session: Session,
    key: str,
    value: Any = None,
    category: str = "observation",
    source: str = "",
    tags: list[str] | None = None,
    ttl_hours: int = 0,
) -> MemoryRecord:
    """Store a memory in the Knowledge Graph.

    Creates/updates a node of type ``orion_<category>`` with the given
    key-value pair. If the node already exists, updates its properties
    and timestamp.
    """
    if ttl_hours <= 0:
        ttl_hours = _CATEGORY_TTL.get(category, TTL_OBSERVATION)

    from core.knowledge.models import KGNode

    node_id = f"orion:{category}:{key}"

    # Upsert: find existing or create
    existing = session.execute(select(KGNode).where(KGNode.id == node_id)).scalar_one_or_none()

    if existing:
        existing.properties = json.dumps(
            {
                "value": _serialize(value),
                "tags": tags or [],
                "category": category,
                "source": source,
                "ttl_hours": ttl_hours,
            }
        )
        existing.updated_at = datetime.now(UTC)
    else:
        node = KGNode(
            id=node_id,
            node_type=f"orion_{category}",
            name=key,
            display_label=str(value)[:128] if value else key,
            properties=json.dumps(
                {
                    "value": _serialize(value),
                    "tags": tags or [],
                    "category": category,
                    "source": source,
                    "ttl_hours": ttl_hours,
                }
            ),
            source=source,
        )
        session.add(node)

    session.commit()

    return MemoryRecord(
        key=key,
        value=value,
        category=category,
        source=source,
        ttl_hours=ttl_hours,
        tags=tags or [],
    )


def recall(
    session: Session,
    key: str | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
    limit: int = 20,
) -> list[MemoryRecord]:
    """Retrieve memories from the Knowledge Graph.

    Filters by key, category, and/or tags. Returns up to ``limit``
    entries, sorted by most recent first.
    """
    from core.knowledge.models import KGNode

    stmt = select(KGNode).where(KGNode.id.like("orion:%"))

    if key:
        stmt = stmt.where(KGNode.name == key)
    if category:
        stmt = stmt.where(KGNode.node_type == f"orion_{category}")

    stmt = stmt.order_by(KGNode.updated_at.desc()).limit(limit)

    results: list[MemoryRecord] = []
    for node in session.execute(stmt).scalars():
        props = _load_props(node.properties)
        mem = MemoryRecord(
            key=node.name,
            value=props.get("value"),
            category=props.get("category", "observation"),
            source=props.get("source", node.source or ""),
            ttl_hours=props.get("ttl_hours", 0),
            tags=props.get("tags", []),
        )
        if not mem.is_expired():
            if tags:
                if any(t in mem.tags for t in tags):
                    results.append(mem)
            else:
                results.append(mem)

    return results


def forget(
    session: Session,
    key: str | None = None,
    category: str | None = None,
    older_than_hours: int = 0,
) -> int:
    """Delete memories from the Knowledge Graph.

    Removes nodes matching key/category/age criteria. Returns count
    of deleted nodes.
    """
    from core.knowledge.models import KGNode

    stmt = select(KGNode).where(KGNode.id.like("orion:%"))

    if key:
        stmt = stmt.where(KGNode.name == key)
    if category:
        stmt = stmt.where(KGNode.node_type == f"orion_{category}")
    if older_than_hours > 0:
        cutoff = datetime.now(UTC).timestamp() - older_than_hours * 3600
        from sqlalchemy import func as sa_func

        stmt = stmt.where(sa_func.strftime("%s", KGNode.created_at) < str(int(cutoff)))

    nodes = list(session.execute(stmt).scalars())
    count = len(nodes)
    for node in nodes:
        session.delete(node)
    if count > 0:
        session.commit()
        logger.info("Forgot %d memories (key=%s, category=%s)", count, key, category)
    return count


def connect(
    session: Session,
    source_key: str,
    target_key: str,
    edge_type: str = "related_to",
    weight: float = 1.0,
) -> None:
    """Create a directed edge between two memories.

    Example: ``connect("shopify:/api/users", "403_no_auth", "returns")``
    creates a graph edge: ``/api/users --[returns]--> 403_no_auth``
    """
    from core.knowledge.models import KGEdge, KGNode

    source = session.execute(
        select(KGNode).where(KGNode.name == source_key, KGNode.id.like("orion:%"))
    ).scalar_one_or_none()
    target = session.execute(
        select(KGNode).where(KGNode.name == target_key, KGNode.id.like("orion:%"))
    ).scalar_one_or_none()

    if not source or not target:
        logger.warning("Cannot connect: source=%s target=%s (missing nodes)", source_key, target_key)
        return

    edge = KGEdge(
        source_id=source.id,
        target_id=target.id,
        edge_type=edge_type,
        weight=weight,
    )
    session.add(edge)
    session.commit()
    logger.info("Connected %s --[%s]--> %s", source_key, edge_type, target_key)


def _serialize(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        return str(value)
    except Exception:
        return repr(value)


def _load_props(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}
