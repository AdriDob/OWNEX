# Knowledge Graph — Diseño del Grafo de Relaciones

> FASE 11 del plan OWNEX v6
> Fecha: 2026-07-29

---

## ¿Por Qué un Knowledge Graph?

Cada engine produce datos aislados. El Knowledge Graph los conecta:

```
Platform ──── Program ──── Finding ──── Payout
   │                          │
   │                    Tag ──┘
   │
   └─── Sensor ──── Observation ──── Entity ──── Opportunity ──── Outcome
```

Sin el grafo, cada respuesta del sistema es un lookup aislado. Con el grafo, el sistema **razona sobre relaciones**:

- "Este programa de HackerOne tiene findings similares a otro que pagó bien"
- "Este tag 'xss' tiene 70% de acceptance rate en Bugcrowd vs 40% en H1"
- "Esta plataforma paga mejor en Q4 que en Q1"

---

## 1. Esquema del Grafo

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ── Node Types ───────────────────────────────────────────────────────────


@dataclass
class KnowledgeNode:
    """A node in the knowledge graph."""
    id: str
    type: str                    # "platform", "program", "entity", "opportunity", "tag", "skill"
    name: str
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = 1.0      # how sure we are about this node


@dataclass
class KnowledgeEdge:
    """A relationship between two nodes."""
    source_id: str
    target_id: str
    relationship: str            # "belongs_to", "similar_to", "leads_to", "requires", "produces"
    strength: float = 1.0        # 0.0 to 1.0
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = 1.0


# ── Predefined node types ────────────────────────────────────────────────


NODE_TYPES = {
    "platform": {
        "description": "A work platform (HackerOne, GitHub, Upwork, etc.)",
        "properties": ["url", "type", "fee_percent", "payout_method"],
    },
    "program": {
        "description": "A specific program on a platform (Google VRP, etc.)",
        "properties": ["url", "scope", "out_of_scope", "reward_min", "reward_max", "status"],
    },
    "entity": {
        "description": "A resolved entity (from IdentityEngine)",
        "properties": ["name", "type", "canonical_url", "observation_count"],
    },
    "opportunity": {
        "description": "A scored opportunity ready for execution",
        "properties": ["cycle", "source_type", "reward", "effort_hours", "status"],
    },
    "tag": {
        "description": "A tag/skill/technology node",
        "properties": ["category", "aliases"],
    },
    "finding": {
        "description": "A bug bounty finding or work submission",
        "properties": ["severity", "type", "reward", "accepted", "cve"],
    },
    "user": {
        "description": "The user (you)",
        "properties": ["name", "role", "preferences"],
    },
    "sensor": {
        "description": "A sensor in the Universal Sensor Network",
        "properties": ["type", "cadence", "version", "status"],
    },
    "capability": {
        "description": "A capability OWNEX possesses",
        "properties": ["category", "providers", "available"],
    },
}

# ── Predefined edge types ────────────────────────────────────────────────


EDGE_TYPES = {
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
```

---

## 2. Knowledge Engine

```python
import json
import sqlite3
from pathlib import Path
import hashlib


class KnowledgeGraph:
    """The knowledge graph — relationships between everything.
    
    No more bucket-based thinking:
    - Not "a program in a DB row"
    - Not "a tag in a JSON field"
    - EVERYTHING is a node, and EVERY relationship is an edge.
    
    Powered by SQLite JSON (simple, no external deps needed).
    For large scale, this can be swapped to Neo4j or DGraph.
    """
    
    def __init__(self, db_path: str = "~/.orion/knowledge.db"):
        self.db_path = str(Path(db_path).expanduser())
        self._init_db()
    
    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
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
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_edges_relationship ON edges(relationship)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type)
        """)
        conn.commit()
        conn.close()
    
    # ── Node operations ─────────────────────────────────────────────────
    
    def add_node(self, node: KnowledgeNode) -> KnowledgeNode:
        """Add or update a node."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT OR REPLACE INTO nodes 
               (id, type, name, properties, created_at, last_updated, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                node.id, node.type, node.name,
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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT id, type, name, properties, created_at, last_updated, confidence "
            "FROM nodes WHERE id = ?",
            (node_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return KnowledgeNode(
                id=row[0], type=row[1], name=row[2],
                properties=json.loads(row[3]),
                created_at=datetime.fromisoformat(row[4]),
                last_updated=datetime.fromisoformat(row[5]),
                confidence=row[6],
            )
        return None
    
    def find_nodes(self, type: str, limit: int = 100) -> list[KnowledgeNode]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT id, type, name, properties, created_at, last_updated, confidence "
            "FROM nodes WHERE type = ? ORDER BY last_updated DESC LIMIT ?",
            (type, limit),
        )
        nodes = []
        for row in cursor:
            nodes.append(KnowledgeNode(
                id=row[0], type=row[1], name=row[2],
                properties=json.loads(row[3]),
                created_at=datetime.fromisoformat(row[4]),
                last_updated=datetime.fromisoformat(row[5]),
                confidence=row[6],
            ))
        conn.close()
        return nodes
    
    def search_nodes(self, query: str, type: str | None = None, limit: int = 20) -> list[KnowledgeNode]:
        """Search nodes by name."""
        conn = sqlite3.connect(self.db_path)
        if type:
            cursor = conn.execute(
                "SELECT id, type, name, properties, created_at, last_updated, confidence "
                "FROM nodes WHERE type = ? AND (name LIKE ? OR id LIKE ?) LIMIT ?",
                (type, f"%{query}%", f"%{query}%", limit),
            )
        else:
            cursor = conn.execute(
                "SELECT id, type, name, properties, created_at, last_updated, confidence "
                "FROM nodes WHERE name LIKE ? OR id LIKE ? LIMIT ?",
                (f"%{query}%", f"%{query}%", limit),
            )
        nodes = []
        for row in cursor:
            nodes.append(KnowledgeNode(
                id=row[0], type=row[1], name=row[2],
                properties=json.loads(row[3]),
                created_at=datetime.fromisoformat(row[4]),
                last_updated=datetime.fromisoformat(row[5]),
                confidence=row[6],
            ))
        conn.close()
        return nodes
    
    # ── Edge operations ─────────────────────────────────────────────────
    
    def add_edge(self, edge: KnowledgeEdge) -> KnowledgeEdge:
        """Add or update an edge."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT OR REPLACE INTO edges
               (source_id, target_id, relationship, strength, properties, created_at, last_updated, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                edge.source_id, edge.target_id, edge.relationship,
                edge.strength, json.dumps(edge.properties),
                edge.created_at.isoformat(),
                edge.last_updated.isoformat(),
                edge.confidence,
            ),
        )
        conn.commit()
        conn.close()
        return edge
    
    def relate(
        self, 
        source_id: str, target_id: str, 
        relationship: str, 
        strength: float = 1.0,
        properties: dict | None = None,
    ) -> KnowledgeEdge:
        """Shorthand to connect two nodes."""
        now = datetime.now(timezone.utc)
        edge = KnowledgeEdge(
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            strength=strength,
            properties=properties or {},
            created_at=now,
            last_updated=now,
        )
        return self.add_edge(edge)
    
    def get_neighbors(
        self, node_id: str, 
        relationship: str | None = None,
        max_depth: int = 1,
    ) -> list[tuple[KnowledgeNode, KnowledgeEdge]]:
        """Get all neighbors of a node, optionally filtered by relationship."""
        conn = sqlite3.connect(self.db_path)
        
        if relationship:
            cursor = conn.execute(
                """SELECT n.id, n.type, n.name, n.properties, n.created_at, n.last_updated, n.confidence,
                          e.relationship, e.strength, e.properties, e.created_at, e.last_updated, e.confidence
                   FROM edges e
                   JOIN nodes n ON (n.id = e.target_id OR n.id = e.source_id)
                   WHERE (e.source_id = ? OR e.target_id = ?)
                     AND e.relationship = ?
                     AND n.id != ?
                   ORDER BY e.strength DESC""",
                (node_id, node_id, relationship, node_id),
            )
        else:
            cursor = conn.execute(
                """SELECT n.id, n.type, n.name, n.properties, n.created_at, n.last_updated, n.confidence,
                          e.relationship, e.strength, e.properties, e.created_at, e.last_updated, e.confidence
                   FROM edges e
                   JOIN nodes n ON (n.id = e.target_id OR n.id = e.source_id)
                   WHERE (e.source_id = ? OR e.target_id = ?)
                     AND n.id != ?
                   ORDER BY e.strength DESC""",
                (node_id, node_id, node_id),
            )
        
        results = []
        for row in cursor:
            node = KnowledgeNode(
                id=row[0], type=row[1], name=row[2],
                properties=json.loads(row[3]),
                created_at=datetime.fromisoformat(row[4]),
                last_updated=datetime.fromisoformat(row[5]),
                confidence=row[6],
            )
            edge = KnowledgeEdge(
                source_id=node_id,
                target_id=node.id,
                relationship=row[7],
                strength=row[8],
                properties=json.loads(row[9]),
                created_at=datetime.fromisoformat(row[10]),
                last_updated=datetime.fromisoformat(row[11]),
                confidence=row[12],
            )
            results.append((node, edge))
        
        conn.close()
        return results
    
    def traverse(
        self,
        start_id: str,
        relationship: str,
        target_type: str | None = None,
        max_depth: int = 3,
    ) -> list[list[tuple[KnowledgeNode, KnowledgeEdge]]]:
        """Traverse the graph following edges of a specific type.
        
        Returns all paths found.
        """
        # BFS traversal
        results = []
        visited = set()
        queue: list[tuple[str, list[tuple[KnowledgeNode, KnowledgeEdge]]]] = [
            (start_id, [])
        ]
        
        while queue and max_depth > 0:
            depth_size = len(queue)
            for _ in range(depth_size):
                current_id, path = queue.pop(0)
                
                if current_id in visited:
                    continue
                visited.add(current_id)
                
                neighbors = self.get_neighbors(current_id, relationship)
                for node, edge in neighbors:
                    new_path = path + [(node, edge)]
                    
                    if target_type and node.type == target_type:
                        results.append(new_path)
                    
                    if len(new_path) < max_depth:
                        queue.append((node.id, new_path))
            
            max_depth -= 1
        
        return results
    
    # ── Query helpers ───────────────────────────────────────────────────
    
    def get_subgraph(self, center_id: str, radius: int = 2) -> dict[str, Any]:
        """Get the subgraph centered on a node.
        
        Returns serializable dict with nodes and edges.
        """
        nodes = {}
        edges = []
        visited = set()
        queue = [(center_id, 0)]
        
        while queue:
            node_id, depth = queue.pop(0)
            if node_id in visited or depth > radius:
                continue
            visited.add(node_id)
            
            node = self.get_node(node_id)
            if node:
                nodes[node_id] = {
                    "id": node.id,
                    "type": node.type,
                    "name": node.name,
                    "properties": node.properties,
                }
            
            neighbors = self.get_neighbors(node_id)
            for neighbor, edge in neighbors:
                edges.append({
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "relationship": edge.relationship,
                    "strength": edge.strength,
                })
                if neighbor.id not in visited:
                    queue.append((neighbor.id, depth + 1))
        
        return {"nodes": list(nodes.values()), "edges": edges}
    
    def get_statistics(self) -> dict[str, Any]:
        """Get graph statistics."""
        conn = sqlite3.connect(self.db_path)
        
        cursor = conn.execute("SELECT type, COUNT(*) FROM nodes GROUP BY type")
        node_counts = dict(cursor.fetchall())
        
        cursor = conn.execute("SELECT relationship, COUNT(*) FROM edges GROUP BY relationship")
        edge_counts = dict(cursor.fetchall())
        
        cursor = conn.execute("SELECT COUNT(*) FROM nodes")
        total_nodes = cursor.fetchone()[0]
        
        cursor = conn.execute("SELECT COUNT(*) FROM edges")
        total_edges = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "nodes_by_type": node_counts,
            "edges_by_relationship": edge_counts,
        }
    
    def reset(self):
        """Clear all data."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM nodes")
        conn.execute("DELETE FROM edges")
        conn.commit()
        conn.close()
```

---

## 3. Graph Population

Cómo se construye el grafo a partir de cada engine:

```python
# ── Automatic graph population ───────────────────────────────────────────


class GraphPopulator:
    """Listens to EventBus events and populates the knowledge graph."""
    
    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg
        self.event_bus = None
    
    async def start(self):
        """Subscribe to EventBus events."""
        if self.event_bus:
            self.event_bus.subscribe("observation:new", self._on_new_observation)
            self.event_bus.subscribe("opportunity:created", self._on_opportunity_created)
            self.event_bus.subscribe("opportunity:state_changed", self._on_state_change)
            self.event_bus.subscribe("execution:completed", self._on_execution_completed)
            self.event_bus.subscribe("learning:pattern_extracted", self._on_pattern_extracted)
            self.event_bus.subscribe("sensor:status", self._on_sensor_status)
    
    async def _on_new_observation(self, data: dict):
        """Observation arrived → create observation + sensor + entity nodes."""
        obs = data  # dict with observation data
        
        # Sensor node
        sensor_node = KnowledgeNode(
            id=f"sensor:{obs['sensor_id']}",
            type="sensor",
            name=obs['sensor_id'],
            properties={"type": obs.get('source_type', '')},
        )
        self.kg.add_node(sensor_node)
        
        # Observation node
        obs_node = KnowledgeNode(
            id=f"obs:{obs['id']}",
            type="observation",
            name=obs.get('title', f"Observation {obs['id']}")[:100],
            properties={
                "sensor_id": obs['sensor_id'],
                "source_type": obs.get('source_type', ''),
                "reward": obs.get('estimated_reward_max', 0),
            },
        )
        self.kg.add_node(obs_node)
        
        # Edge: sensor → observed_by → observation
        self.kg.relate(sensor_node.id, obs_node.id, "observes", properties={
            "timestamp": obs.get('observed_at', ''),
        })
    
    async def _on_opportunity_created(self, data: dict):
        """Opportunity created → connect to entity + platform."""
        opp_id = data['opportunity_id']
        
        opp_node = KnowledgeNode(
            id=f"opp:{opp_id}",
            type="opportunity",
            name=opp_id,
            properties={
                "cycle": data.get('cycle', ''),
                "source_type": data.get('source_type', ''),
            },
        )
        self.kg.add_node(opp_node)
        
        # Connect observation → classified_as → opportunity
        self.kg.relate(f"obs:{opp_id}", opp_node.id, "classified_as")
    
    async def _on_state_change(self, data: dict):
        """State changes → update opportunity node properties."""
        opp_id = data['opportunity_id']
        node = self.kg.get_node(f"opp:{opp_id}")
        if node:
            node.properties["current_state"] = data.get('to', '')
            node.last_updated = datetime.now(timezone.utc)
            self.kg.add_node(node)
    
    async def _on_execution_completed(self, data: dict):
        """Execution completed → connect opportunity to outcome."""
        opp_id = data.get('opportunity_id', '')
        success = data.get('success', False)
        
        outcome_node = KnowledgeNode(
            id=f"outcome:{opp_id}",
            type="outcome",
            name=f"Outcome for {opp_id}",
            properties={
                "success": success,
                "reward": data.get('reward', 0),
                "effort_hours": data.get('effort', 0),
            },
        )
        self.kg.add_node(outcome_node)
        self.kg.relate(f"opp:{opp_id}", outcome_node.id, "produces")
    
    async def _on_pattern_extracted(self, data: dict):
        """Learning pattern → create pattern node + connect to source."""
        pattern_id = data.get('id', '')
        pattern_text = data.get('pattern', '')
        
        pattern_node = KnowledgeNode(
            id=f"pattern:{pattern_id}",
            type="pattern",
            name=pattern_text[:100],
            properties={
                "pattern": pattern_text,
                "confidence": data.get('confidence', 0.5),
                "success_rate": data.get('success_rate', 0.5),
            },
        )
        self.kg.add_node(pattern_node)
    
    async def _on_sensor_status(self, data: dict):
        """Sensor status update → update sensor node."""
        sensor_id = data.get('sensor_id', '')
        node = self.kg.get_node(f"sensor:{sensor_id}")
        if node:
            node.properties.update({
                "status": data.get('status', 'unknown'),
                "last_run": data.get('last_run', ''),
                "observations_count": data.get('count', 0),
            })
            node.last_updated = datetime.now(timezone.utc)
            self.kg.add_node(node)
```

---

## 4. Queries Útiles

```python
class GraphQueries:
    """Common knowledge graph queries."""
    
    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg
    
    def similar_programs(self, program_name: str, limit: int = 5) -> list[dict]:
        """Find similar programs to one that paid well."""
        nodes = self.kg.search_nodes(program_name, type="program")
        if not nodes:
            return []
        
        # Get all neighbors of the program with similar_to edges
        neighbors = self.kg.get_neighbors(nodes[0].id, "similar_to")
        return [
            {"id": n.id, "name": n.name, "type": n.type, "strength": e.strength}
            for n, e in neighbors[:limit]
        ]
    
    def best_platform_for_tag(self, tag: str) -> list[dict]:
        """Which platform pays most for a given skill/tag."""
        tag_nodes = self.kg.search_nodes(tag, type="tag")
        if not tag_nodes:
            return []
        
        # Traverse: tag → tagged_with → opportunities → paid_by → platform
        paths = self.kg.traverse(
            tag_nodes[0].id,
            relationship="tagged_with|belongs_to|paid_by",
            target_type="platform",
        )
        
        # Aggregate by platform
        platform_rewards = {}
        for path in paths:
            for node, edge in path:
                if node.type == "platform":
                    name = node.name
                    reward = node.properties.get("total_rewards", 0)
                    platform_rewards[name] = platform_rewards.get(name, 0) + reward
        
        return sorted(
            [{"platform": p, "total_rewards": r} for p, r in platform_rewards.items()],
            key=lambda x: x["total_rewards"],
            reverse=True,
        )
    
    def opportunity_path_to_payment(self, opportunity_id: str) -> list[dict]:
        """Trace the full path from opportunity to payment."""
        node_id = f"opp:{opportunity_id}"
        path = self.kg.traverse(
            node_id,
            relationship="produces|leads_to|paid_by",
            max_depth=5,
        )
        
        result = []
        for step in path:
            for node, edge in step:
                result.append({
                    "node": node.name,
                    "type": node.type,
                    "relationship": edge.relationship,
                    "strength": edge.strength,
                })
        return result
    
    def what_has_high_acceptance_rate(self, min_samples: int = 5) -> list[dict]:
        """What patterns have high acceptance rates?"""
        patterns = self.kg.find_nodes(type="pattern")
        good = []
        for p in patterns:
            success_rate = p.properties.get("success_rate", 0)
            total = p.properties.get("total_count", 0)
            if success_rate > 0.6 and total >= min_samples:
                good.append({
                    "pattern": p.properties.get("pattern", p.name),
                    "success_rate": success_rate,
                    "samples": total,
                })
        return sorted(good, key=lambda x: x["success_rate"], reverse=True)
    
    def full_system_status(self) -> dict[str, Any]:
        """Full system status from the graph."""
        sensors = self.kg.find_nodes(type="sensor")
        platforms = self.kg.find_nodes(type="platform")
        opportunities = self.kg.find_nodes(type="opportunity")
        outcomes = self.kg.find_nodes(type="outcome")
        patterns = self.kg.find_nodes(type="pattern")
        
        return {
            "sensors": [{"name": s.name, **s.properties} for s in sensors],
            "platforms": len(platforms),
            "active_opportunities": [
                {"name": o.name, **o.properties}
                for o in opportunities
                if o.properties.get("current_state") not in ("paid", "rejected", "learned")
            ],
            "total_outcomes": len(outcomes),
            "total_patterns": len(patterns),
            "successful_outcomes": sum(
                1 for o in outcomes if o.properties.get("success")
            ),
            "total_rewards": sum(
                o.properties.get("reward", 0) for o in outcomes
            ),
        }
```

---

## 5. Integración con el Pipeline

```python
# Wiring: GraphPopulator escucha EventBus y construye el grafo automáticamente.

async def init_knowledge_graph():
    kg = KnowledgeGraph()
    populator = GraphPopulator(kg)
    populator.event_bus = event_bus
    await populator.start()
    return kg


# Uso en ContextEngine:
class KnowledgeGraphSource(ContextSource):
    """Knowledge graph as a context source."""
    
    def __init__(self, kg: KnowledgeGraph):
        self.kg = kg
    
    async def fetch(self, opportunity: ScoredOpportunity, depth: str = "standard") -> ContextFragment | None:
        """Get relevant graph context for an opportunity."""
        
        # Find similar past opportunities
        similar = self.kg.get_neighbors(f"opp:{opportunity.id}", "similar_to")
        
        if not similar:
            # Try by tags
            tag_contexts = []
            for tag in opportunity.tags[:3]:
                platforms = queries.best_platform_for_tag(tag)
                if platforms:
                    tag_contexts.append(f"Tag '{tag}': best platforms: {[p['platform'] for p in platforms[:3]]}")
            
            if tag_contexts:
                text = "\n".join(tag_contexts)
                return ContextFragment(
                    source="knowledge_graph",
                    content=text,
                    relevance=0.6,
                    token_estimate=len(text) // 4,
                )
        
        # Build context from similar opportunities
        if similar:
            text_lines = ["Similar past opportunities:"]
            for node, edge in similar[:5]:
                text_lines.append(f"- {node.name} ({node.properties.get('cycle', '')}, EV: ${node.properties.get('reward', 0):.2f})")
            text = "\n".join(text_lines)
            
            return ContextFragment(
                source="knowledge_graph",
                content=text,
                relevance=0.7,
                token_estimate=len(text) // 4,
            )
        
        return None
```

---

## Visualización del Grafo (Idea)

```
                             Tag:"xss"
                                │
                                │ tagged_with
                                │
Platform:"HackerOne" ──── Program:"Google VRP" ──── Finding:"XSS in login"
      │                        │                              │
      │ belongs_to             │ has                          │ leads_to
      │                        ▼                              ▼
      └─── Entity:"Google" ──── Opportunity:"Google XSS" ──── Outcome:"PAID"
                                   │                             │
                                   │ classified_as               │ $5,000
                                   ▼                             ▼
                              Cycle:"security"             Wallet:+$5,000
                              Source:"bug_bounty"
                                   │
                                   │ executed_by
                                   ▼
                              Sensor:"hackerone"
```

El grafo produce respuestas como:

- "Llevas $12,000 en earnings de HackerOne este mes"
- "Los findings XSS pagan 30% más en Bugcrowd que en H1"
- "Hay 3 oportunidades similares a esta que aceptaron rápido"
- "Tu mejor plataforma para 'api' es Intigriti con 80% acceptance"
