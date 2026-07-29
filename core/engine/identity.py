"""Identity Engine — resolves observations to canonical entities.

Multiple observations from different sensors may refer to the same real-world
entity (bug bounty program, GitHub repo, freelance task, etc.). This engine
resolves identities across sensors using strategies from exact match → fuzzy match.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.engine.base import Engine
from core.sensors.observation import Observation

logger = logging.getLogger("ownex.identity")


@dataclass
class Entity:
    """A resolved entity — the canonical representation of a real-world thing.

    Multiple observations can point to the same entity.
    Bug bounty programs, GitHub repos, dev bounty tasks — all are entities.
    """

    id: str  # canonical UUID
    name: str
    entity_type: str  # "bug_bounty_program", "dev_bounty", "repo", "task"

    canonical_url: str | None = None
    platform: str = ""

    # First and last seen
    first_observed: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_observed: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # Statistics
    observation_count: int = 1
    confidence: float = 0.5

    # Enriched data (accumulated across observations)
    aliases: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)
    domains: set[str] = field(default_factory=set)

    # Latest scoring
    estimated_value: float = 0.0
    entity_status: str = "active"  # active | inactive | closed

    # Reference to DB
    db_id: int | None = None


class IdentityEngine(Engine):
    """Resolves observations to entities.

    Entity resolution happens across sensors:
    - Same GitHub issue from GitHub API + RSS + Email → one entity
    - Same bug bounty program from H1 + web search → one entity
    - Same freelance task from Upwork + email notification → one entity

    Deduplication is a side effect, not the goal.
    The goal is LINKING observations to their canonical entity.
    """

    name = "identity_engine"

    def __init__(self, db_path: str = "~/.orion/identity.db") -> None:
        super().__init__()
        self.db_path = os.path.expanduser(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize SQLite for entity storage."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                canonical_url TEXT,
                platform TEXT DEFAULT '',
                first_observed TEXT NOT NULL,
                last_observed TEXT NOT NULL,
                observation_count INTEGER DEFAULT 1,
                confidence REAL DEFAULT 0.5,
                aliases TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                domains TEXT DEFAULT '[]',
                estimated_value REAL DEFAULT 0.0,
                entity_status TEXT DEFAULT 'active'
            );

            CREATE TABLE IF NOT EXISTS entity_observations (
                entity_id TEXT NOT NULL,
                observation_id TEXT NOT NULL,
                sensor_id TEXT NOT NULL,
                external_id TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                PRIMARY KEY (entity_id, observation_id),
                FOREIGN KEY (entity_id) REFERENCES entities(id)
            );

            CREATE INDEX IF NOT EXISTS idx_entity_obs_sensor
                ON entity_observations(sensor_id, external_id);
            CREATE INDEX IF NOT EXISTS idx_entity_obs_fingerprint
                ON entity_observations(fingerprint);
        """)
        self._conn.commit()

    async def initialize(self) -> None:
        self._initialized = True
        logger.info("IdentityEngine: db=%s", self.db_path)

    async def health(self) -> dict[str, Any]:
        stats = self.get_statistics()
        return {
            "status": "ok",
            "name": self.name,
            "db_path": self.db_path,
            **stats,
        }

    # ── Resolution ──────────────────────────────────────────────────

    def resolve(self, observation: Observation) -> Entity:
        """Resolve an observation to its canonical entity.

        Returns existing entity or creates new one.
        """
        # Strategy 1: exact external_id match
        if observation.external_id:
            entity = self._find_by_external_id(observation.external_id)
            if entity:
                self._update_entity(entity, observation)
                return entity

        # Strategy 2: URL match
        if observation.url:
            entity = self._find_by_url(observation.url)
            if entity:
                self._update_entity(entity, observation)
                return entity

        # Strategy 3: checksum / fingerprint match
        checksum = self._compute_fingerprint(observation)
        entity = self._find_by_fingerprint(checksum)
        if entity:
            self._update_entity(entity, observation)
            return entity

        # Strategy 4: fuzzy title match (same platform, similar name)
        entity = self._find_by_fuzzy_title(observation)
        if entity:
            self._update_entity(entity, observation)
            return entity

        # No match → create new entity
        return self._create_entity(observation)

    # ── Lookup ──────────────────────────────────────────────────────

    def _find_by_external_id(self, external_id: str) -> Entity | None:
        """Find entity linked to a specific external_id."""
        cursor = self._conn.execute(
            """SELECT entity_id FROM entity_observations
               WHERE external_id = ? LIMIT 1""",
            (external_id,),
        )
        row = cursor.fetchone()
        if row:
            return self.get_entity(row["entity_id"])
        return None

    def _find_by_url(self, url: str) -> Entity | None:
        """Find entity with matching URL."""
        cursor = self._conn.execute(
            "SELECT * FROM entities WHERE canonical_url = ? LIMIT 1",
            (url,),
        )
        row = cursor.fetchone()
        return self._row_to_entity(row) if row else None

    def _find_by_fingerprint(self, fingerprint: str) -> Entity | None:
        """Find entity by observation fingerprint."""
        cursor = self._conn.execute(
            """SELECT entity_id FROM entity_observations
               WHERE fingerprint = ? LIMIT 1""",
            (fingerprint,),
        )
        row = cursor.fetchone()
        if row:
            return self.get_entity(row["entity_id"])
        return None

    def _find_by_fuzzy_title(self, obs: Observation) -> Entity | None:
        """Fuzzy title match within same platform."""
        # Simple word overlap: count shared words
        obs_words = set(obs.title.lower().split())
        if len(obs_words) < 2:
            return None

        # Find entities on same platform with similar name
        cursor = self._conn.execute(
            "SELECT * FROM entities WHERE platform = ?",
            (obs.source_name,),
        )
        best_match: Entity | None = None
        best_score = 0.0

        for row in cursor.fetchall():
            entity = self._row_to_entity(row)
            if not entity:
                continue
            name_words = set(entity.name.lower().split())
            shared = len(obs_words & name_words)
            total = len(obs_words | name_words)
            if total == 0:
                continue
            score = shared / total
            if score > 0.6 and score > best_score:  # 60% word overlap threshold
                best_score = score
                best_match = entity

        return best_match

    # ── Entity CRUD ─────────────────────────────────────────────────

    def _create_entity(self, observation: Observation) -> Entity:
        """Create a new entity from an observation."""
        entity_id = hashlib.sha256(
            f"{observation.sensor_id}:{observation.external_id}:{observation.observed_at}".encode()
        ).hexdigest()[:16]

        fingerprint = self._compute_fingerprint(observation)
        now = datetime.now(timezone.utc).isoformat()

        entity = Entity(
            id=entity_id,
            name=observation.title,
            entity_type=observation.source_type,
            canonical_url=observation.url,
            platform=observation.source_name,
            first_observed=now,
            last_observed=now,
            observation_count=1,
            confidence=observation.confidence,
            aliases={observation.external_id},
            tags=set(observation.tags),
            estimated_value=max(observation.estimated_reward_min, observation.estimated_reward_max),
        )

        # Persist
        self._conn.execute(
            """INSERT INTO entities
               (id, name, entity_type, canonical_url, platform,
                first_observed, last_observed, observation_count, confidence,
                aliases, tags, estimated_value, entity_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                entity.id, entity.name, entity.entity_type, entity.canonical_url,
                entity.platform, entity.first_observed, entity.last_observed,
                entity.observation_count, entity.confidence,
                json.dumps(list(entity.aliases)),
                json.dumps(list(entity.tags)),
                entity.estimated_value, entity.entity_status,
            ),
        )

        # Link observation
        self._conn.execute(
            """INSERT INTO entity_observations
               (entity_id, observation_id, sensor_id, external_id, fingerprint, observed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                entity.id, observation.id, observation.sensor_id,
                observation.external_id, fingerprint, observation.observed_at,
            ),
        )
        self._conn.commit()

        return entity

    def _update_entity(self, entity: Entity, observation: Observation) -> Entity:
        """Update an existing entity with new observation data."""
        entity.last_observed = datetime.now(timezone.utc).isoformat()
        entity.observation_count += 1

        # Merge tags
        for tag in observation.tags:
            entity.tags.add(tag)

        # Merge aliases
        entity.aliases.add(observation.external_id)

        # Update value if higher
        obs_value = max(observation.estimated_reward_min, observation.estimated_reward_max)
        if obs_value > entity.estimated_value:
            entity.estimated_value = obs_value

        # Persist
        fingerprint = self._compute_fingerprint(observation)
        self._conn.execute(
            """UPDATE entities SET
               last_observed = ?, observation_count = ?, confidence = ?,
               tags = ?, aliases = ?, estimated_value = ?, entity_status = ?
               WHERE id = ?""",
            (
                entity.last_observed, entity.observation_count,
                min(1.0, entity.confidence + 0.05),  # confidence increases with more observations
                json.dumps(list(entity.tags)),
                json.dumps(list(entity.aliases)),
                entity.estimated_value, entity.entity_status,
                entity.id,
            ),
        )

        # Link observation
        self._conn.execute(
            """INSERT OR IGNORE INTO entity_observations
               (entity_id, observation_id, sensor_id, external_id, fingerprint, observed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                entity.id, observation.id, observation.sensor_id,
                observation.external_id, fingerprint, observation.observed_at,
            ),
        )
        self._conn.commit()

        return entity

    # ── Helpers ─────────────────────────────────────────────────────

    def _compute_fingerprint(self, obs: Observation) -> str:
        """Compute a stable fingerprint for identity resolution.

        Combines: sensor_id + platform + external_id + url + content hash
        """
        components = [
            obs.sensor_id,
            obs.raw_data.get("platform", ""),
            obs.external_id,
            obs.url or "",
        ]
        raw = ":".join(str(c) for c in components if c)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _row_to_entity(self, row: sqlite3.Row | None) -> Entity | None:
        """Convert a DB row to an Entity dataclass."""
        if row is None:
            return None
        return Entity(
            id=row["id"],
            name=row["name"],
            entity_type=row["entity_type"],
            canonical_url=row["canonical_url"],
            platform=row["platform"],
            first_observed=row["first_observed"],
            last_observed=row["last_observed"],
            observation_count=row["observation_count"],
            confidence=row["confidence"],
            aliases=set(json.loads(row["aliases"])),
            tags=set(json.loads(row["tags"])),
            domains=set(json.loads(row["domains"])),
            estimated_value=row["estimated_value"],
            entity_status=row["entity_status"],
            db_id=row["id"],
        )

    # ── Public API ──────────────────────────────────────────────────

    def get_entity(self, entity_id: str) -> Entity | None:
        """Get entity by ID."""
        cursor = self._conn.execute(
            "SELECT * FROM entities WHERE id = ?", (entity_id,)
        )
        return self._row_to_entity(cursor.fetchone())

    def get_observations(self, entity_id: str) -> list[Observation]:
        """Get all observations linked to an entity."""
        cursor = self._conn.execute(
            "SELECT * FROM entity_observations WHERE entity_id = ?",
            (entity_id,),
        )
        observations: list[Observation] = []
        for row in cursor.fetchall():
            observations.append(
                Observation(
                    id=row["observation_id"],
                    sensor_id=row["sensor_id"],
                    external_id=row["external_id"],
                    title="",
                    description="",
                    raw_data={},
                    source_type="",
                    source_name="",
                    observed_at=row["observed_at"],
                )
            )
        return observations

    def get_statistics(self) -> dict[str, Any]:
        """Get identity resolution statistics."""
        total_entities = self._conn.execute(
            "SELECT COUNT(*) FROM entities"
        ).fetchone()[0]
        total_observations = self._conn.execute(
            "SELECT COUNT(*) FROM entity_observations"
        ).fetchone()[0]

        # Entities with more than 1 observation (resolved pairs)
        resolved = self._conn.execute(
            """SELECT COUNT(*) FROM (
                SELECT entity_id FROM entity_observations
                GROUP BY entity_id HAVING COUNT(*) > 1
            )"""
        ).fetchone()[0]

        return {
            "total_entities": total_entities,
            "total_observations": total_observations,
            "resolved_pairs": resolved,
        }
