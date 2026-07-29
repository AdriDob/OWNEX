"""Knowledge Graph — relationships between everything in OWNEX.

Every entity is a node, every relationship is an edge.
No more bucket-based: programs, tags, findings, sensors, opportunities,
capabilities — all live in the same graph.

Powered by SQLite JSON (simple, no external deps).
Scalable to Neo4j/DGraph later.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.engine.base import Engine

logger = logging.getLogger("ownex.knowledge")

# ── Shared SQLite connection helper ────────────────────────────────


def _connect(db_path: str) -> sqlite3.Connection:
    """Connect to SQLite, handling :memory: with shared cache."""
    if db_path == ":memory:":
        return sqlite3.connect("file::memory:?cache=shared", uri=True)
    return sqlite3.connect(db_path)


# ── Node and edge types ────────────────────────────────────────────


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph."""

    id: str
    type: str  # program, opportunity, tag, finding, user, sensor, capability
    name: str
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = 1.0


@dataclass
class KnowledgeEdge:
    """A directed relationship between two nodes."""

    source_id: str
    target_id: str
    relationship: str  # belongs_to, similar_to, requires, produces, ...
    strength: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = 1.0


# ── Predefined types ───────────────────────────────────────────────


NODE_TYPES = {
    "program": {
        "description": "A bug bounty or work program",
        "properties": ["name", "type", "canonical_url", "observation_count"],
    },
    "opportunity": {
        "description": "A scored opportunity for execution",
        "properties": ["cycle", "source_type", "reward", "effort_hours", "status"],
    },
    "tag": {"description": "A tag/skill/technology node", "properties": ["category", "aliases"]},
    "finding": {
        "description": "A bug bounty finding or work submission",
        "properties": ["severity", "type", "reward", "accepted", "cve"],
    },
    "user": {"description": "The user", "properties": ["name", "role", "preferences"]},
    "sensor": {
        "description": "A sensor in the Universal Sensor Network",
        "properties": ["type", "cadence", "version", "status"],
    },
    "capability": {"description": "A capability OWNEX possesses", "properties": ["category", "providers", "available"]},
}

EDGE_TYPES: dict[str, dict[str, str]] = {
    "belongs_to": {"inverse": "contains"},
    "similar_to": {"inverse": "similar_to"},
    "leads_to": {"inverse": "leads_from"},
    "requires": {"inverse": "required_by"},
    "produces": {"inverse": "produced_by"},
    "observed_by": {"inverse": "observes"},
    "resolved_to": {"inverse": "resolves"},
    "classified_as": {"inverse": "classifies"},
    "scored_with": {"inverse": "scores"},
    "executed_by": {"inverse": "executes"},
    "paid_by": {"inverse": "pays"},
    "tagged_with": {"inverse": "tags"},
    "related_to": {"inverse": "related_to"},
    "depends_on": {"inverse": "depended_by"},
    "improves": {"inverse": "improved_by"},
}


# ── Knowledge Graph Engine ─────────────────────────────────────────


class KnowledgeGraph(Engine):
    """The knowledge graph — relationships between everything.

    Every entity is a node, every relationship is an edge.
    Supports SQLite-backed persistence with JSON properties.
    """

    name = "knowledge_graph"

    def __init__(self, db_path: str = "~/.orion/knowledge.db") -> None:
        super().__init__()
        self.db_path = os.path.expanduser(db_path)

    def _init_db(self) -> None:
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = _connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                properties TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                confidence REAL DEFAULT 1.0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relationship TEXT NOT NULL,
                strength REAL DEFAULT 1.0,
                properties TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                UNIQUE(source_id, target_id, relationship)
            )
        """)
        for col in ("source_id", "target_id", "relationship"):
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_edges_{col} ON edges({col})")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type)")
        conn.commit()
        conn.close()

    # ── Node operations ─────────────────────────────────────────────

    def add_node(self, node: KnowledgeNode) -> KnowledgeNode:
        node.last_updated = datetime.now(timezone.utc)
        conn = _connect(self.db_path)
        conn.execute(
            """INSERT OR REPLACE INTO nodes
               (id, type, name, properties, created_at, last_updated, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                node.id,
                node.type,
                node.name,
                json.dumps(node.properties),
                node.created_at.isoformat(),
                node.last_updated.isoformat(),
                node.confidence,
            ),
        )
        conn.commit()
        conn.close()
        return node

    def get_node(self, node_id: str) -> KnowledgeNode | None:
        conn = _connect(self.db_path)
        cursor = conn.execute(
            "SELECT id, type, name, properties, created_at, last_updated, confidence FROM nodes WHERE id = ?",
            (node_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return self._row_to_node(row)
        return None

    def find_nodes(
        self,
        type: str | None = None,
        limit: int = 100,
    ) -> list[KnowledgeNode]:
        conn = _connect(self.db_path)
        if type:
            cursor = conn.execute(
                "SELECT id, type, name, properties, created_at, last_updated, confidence "
                "FROM nodes WHERE type = ? ORDER BY last_updated DESC LIMIT ?",
                (type, limit),
            )
        else:
            cursor = conn.execute(
                "SELECT id, type, name, properties, created_at, last_updated, confidence "
                "FROM nodes ORDER BY last_updated DESC LIMIT ?",
                (limit,),
            )
        nodes = [self._row_to_node(row) for row in cursor]
        conn.close()
        return nodes

    def search_nodes(
        self,
        query: str,
        type: str | None = None,
        limit: int = 20,
    ) -> list[KnowledgeNode]:
        conn = _connect(self.db_path)
        like = f"%{query}%"
        if type:
            cursor = conn.execute(
                "SELECT id, type, name, properties, created_at, last_updated, confidence "
                "FROM nodes WHERE type = ? AND (name LIKE ? OR id LIKE ?) LIMIT ?",
                (type, like, like, limit),
            )
        else:
            cursor = conn.execute(
                "SELECT id, type, name, properties, created_at, last_updated, confidence "
                "FROM nodes WHERE name LIKE ? OR id LIKE ? LIMIT ?",
                (like, like, limit),
            )
        nodes = [self._row_to_node(row) for row in cursor]
        conn.close()
        return nodes

    def upsert_node(
        self,
        type: str,
        name: str,
        properties: dict[str, Any] | None = None,
        node_id: str | None = None,
    ) -> KnowledgeNode:
        """Create or update a node. Generates ID from type+name if not given."""
        if not node_id:
            raw = f"{type}:{name}"
            node_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
        existing = self.get_node(node_id)
        now = datetime.now(timezone.utc)
        if existing:
            existing.name = name
            existing.last_updated = now
            if properties:
                existing.properties.update(properties)
            return self.add_node(existing)
        return self.add_node(
            KnowledgeNode(
                id=node_id,
                type=type,
                name=name,
                properties=properties or {},
                created_at=now,
                last_updated=now,
            )
        )

    def delete_node(self, node_id: str) -> bool:
        conn = _connect(self.db_path)
        conn.execute("DELETE FROM edges WHERE source_id = ? OR target_id = ?", (node_id, node_id))
        cursor = conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    # ── Edge operations ─────────────────────────────────────────────

    def add_edge(self, edge: KnowledgeEdge) -> KnowledgeEdge:
        edge.last_updated = datetime.now(timezone.utc)
        conn = _connect(self.db_path)
        conn.execute(
            """INSERT OR REPLACE INTO edges
               (source_id, target_id, relationship, strength, properties,
                created_at, last_updated, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                edge.source_id,
                edge.target_id,
                edge.relationship,
                edge.strength,
                json.dumps(edge.properties),
                edge.created_at.isoformat(),
                edge.last_updated.isoformat(),
                edge.confidence,
            ),
        )
        conn.commit()
        conn.close()
        return edge

    def connect(
        self,
        source_id: str,
        target_id: str,
        relationship: str,
        strength: float = 1.0,
    ) -> KnowledgeEdge:
        """Create an edge between two nodes."""
        return self.add_edge(
            KnowledgeEdge(
                source_id=source_id,
                target_id=target_id,
                relationship=relationship,
                strength=strength,
            )
        )

    def get_edges(
        self,
        node_id: str,
        direction: str = "both",
        relationship: str | None = None,
        limit: int = 100,
    ) -> list[KnowledgeEdge]:
        conn = _connect(self.db_path)
        if direction == "outgoing":
            q = "SELECT * FROM edges WHERE source_id = ?"
            params: list[Any] = [node_id]
        elif direction == "incoming":
            q = "SELECT * FROM edges WHERE target_id = ?"
            params = [node_id]
        else:
            q = "SELECT * FROM edges WHERE source_id = ? OR target_id = ?"
            params = [node_id, node_id]

        if relationship:
            q += " AND relationship = ?"
            params.append(relationship)

        q += " ORDER BY strength DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(q, params)
        edges = [self._row_to_edge(row) for row in cursor]
        conn.close()
        return edges

    def traverse(
        self,
        node_id: str,
        relationship: str | None = None,
        max_depth: int = 2,
    ) -> list[dict[str, Any]]:
        """BFS traversal from a node. Returns paths."""
        visited: set[str] = set()
        results: list[dict[str, Any]] = []
        queue: list[tuple[str, int, list[str]]] = [(node_id, 0, [])]

        while queue:
            current, depth, path = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)

            edges = self.get_edges(current, relationship=relationship, limit=50)
            for edge in edges:
                neighbor = edge.target_id if edge.source_id == current else edge.source_id
                rel = edge.relationship
                new_path = path + [f"--[{rel}]-->{neighbor}"]
                results.append({"from": current, "to": neighbor, "rel": rel, "depth": depth + 1, "path": new_path})
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1, new_path))

        return results

    # ── Queries ─────────────────────────────────────────────────────

    def get_statistics(self) -> dict[str, Any]:
        conn = _connect(self.db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM nodes")
        total_nodes = cursor.fetchone()[0]
        cursor = conn.execute("SELECT COUNT(*) FROM edges")
        total_edges = cursor.fetchone()[0]
        cursor = conn.execute("SELECT type, COUNT(*) as cnt FROM nodes GROUP BY type ORDER BY cnt DESC")
        by_type = dict(cursor.fetchall())
        cursor = conn.execute("SELECT relationship, COUNT(*) as cnt FROM edges GROUP BY relationship ORDER BY cnt DESC")
        by_rel = dict(cursor.fetchall())
        conn.close()
        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "nodes_by_type": by_type,
            "edges_by_relationship": by_rel,
        }

    # ── Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _row_to_node(row: sqlite3.Row | tuple) -> KnowledgeNode:
        return KnowledgeNode(
            id=row[0],
            type=row[1],
            name=row[2],
            properties=json.loads(row[3]),
            created_at=datetime.fromisoformat(row[4]),
            last_updated=datetime.fromisoformat(row[5]),
            confidence=row[6],
        )

    @staticmethod
    def _row_to_edge(row: sqlite3.Row | tuple) -> KnowledgeEdge:
        return KnowledgeEdge(
            source_id=row[1],
            target_id=row[2],
            relationship=row[3],
            strength=row[4],
            properties=json.loads(row[5]),
            created_at=datetime.fromisoformat(row[6]),
            last_updated=datetime.fromisoformat(row[7]),
            confidence=row[8],
        )

    # ── Engine lifecycle ────────────────────────────────────────────

    async def initialize(self) -> None:
        self._init_db()
        self._initialized = True

    async def health(self) -> dict[str, Any]:
        stats = self.get_statistics()
        return {
            "status": "ok",
            "name": self.name,
            "db_path": self.db_path,
            **stats,
        }
