"""System Memory — evidence-based memory with Assumed/Observed/Verified/Historical states.

This module implements the memory system that separates knowledge by evidence level:
- Assumed: Hypotheses, predictions, unconfirmed beliefs
- Observed: Direct observations from sensors, raw data
- Verified: Confirmed facts, validated through multiple sources
- Historical: Archived decisions, outcomes, learnings
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from core.events.event_bus import get_core_event_bus

logger = logging.getLogger("ownex.memory")


class EvidenceLevel(Enum):
    """Evidence levels for memory entries."""

    ASSUMED = 0  # Hypothesis, prediction, unconfirmed
    OBSERVED = 1  # Direct observation, sensor data
    VERIFIED = 2  # Cross-validated, confirmed fact
    HISTORICAL = 3  # Archived decision/outcome/learning


class MemoryType(Enum):
    """Types of memory entries."""

    FACT = "fact"  # Discrete fact about world
    OBSERVATION = "observation"  # Raw sensor/agent observation
    DECISION = "decision"  # Decision made and why
    OUTCOME = "outcome"  # Result of an action
    LEARNING = "learning"  # Pattern discovered
    PREFERENCE = "preference"  # User preference
    GOAL = "goal"  # Active goal
    HYPOTHESIS = "hypothesis"  # Testable prediction
    SKILL = "skill"  # Learned capability
    CONTEXT = "context"  # Situational context


@dataclass
class MemoryEntry:
    """A single memory entry with evidence tracking."""

    id: str
    type: MemoryType
    level: EvidenceLevel
    content: dict[str, Any]
    source: str  # Who/what created this
    created_at: datetime
    updated_at: datetime

    # Evidence tracking
    confidence: float = 0.5  # 0.0 - 1.0
    evidence_refs: list[str] = field(default_factory=list)  # IDs of supporting evidence
    contradicted_by: list[str] = field(default_factory=list)  # IDs of contradicting evidence

    # Verification
    verified_at: datetime | None = None
    verified_by: str | None = None
    verification_method: str | None = None

    # Lifecycle
    expires_at: datetime | None = None
    superseded_by: str | None = None
    access_count: int = 0
    last_accessed: datetime | None = None

    # Metadata
    tags: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)

    def promote(self, new_level: EvidenceLevel, verified_by: str, method: str) -> bool:
        """Promote to higher evidence level."""
        if new_level.value <= self.level.value:
            return False

        self.level = new_level
        self.verified_at = datetime.now(UTC)
        self.verified_by = verified_by
        self.verification_method = method
        self.updated_at = datetime.now(UTC)
        self.confidence = min(1.0, self.confidence + 0.2)
        return True

    def contradict(self, other_id: str) -> None:
        """Mark as contradicted by another entry."""
        if other_id not in self.contradicted_by:
            self.contradicted_by.append(other_id)
            self.confidence = max(0.0, self.confidence - 0.1)
            self.updated_at = datetime.now(UTC)

    def support(self, other_id: str) -> None:
        """Add supporting evidence."""
        if other_id not in self.evidence_refs:
            self.evidence_refs.append(other_id)
            self.confidence = min(1.0, self.confidence + 0.05)
            self.updated_at = datetime.now(UTC)

    def access(self) -> None:
        """Record access."""
        self.access_count += 1
        self.last_accessed = datetime.now(UTC)

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    def is_superseded(self) -> bool:
        """Check if entry is superseded."""
        return self.superseded_by is not None


@dataclass
class MemoryQuery:
    """Query for memory retrieval."""

    types: set[MemoryType] | None = None
    levels: set[EvidenceLevel] | None = None
    min_confidence: float = 0.0
    max_confidence: float = 1.0
    tags: set[str] | None = None
    source: str | None = None
    since: datetime | None = None
    until: datetime | None = None
    content_filter: Callable[[dict], bool] | None = None
    limit: int = 100
    include_expired: bool = False
    include_superseded: bool = False


class MemoryStore(ABC):
    """Abstract memory storage backend."""

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize storage."""
        pass

    @abstractmethod
    async def store(self, entry: MemoryEntry) -> bool:
        """Store a memory entry."""
        pass

    @abstractmethod
    async def retrieve(self, entry_id: str) -> MemoryEntry | None:
        """Retrieve a memory entry by ID."""
        pass

    @abstractmethod
    async def query(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Query memory entries."""
        pass

    @abstractmethod
    async def update(self, entry: MemoryEntry) -> bool:
        """Update an existing entry."""
        pass

    @abstractmethod
    async def delete(self, entry_id: str) -> bool:
        """Delete an entry."""
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Health check."""
        pass


class InMemoryStore(MemoryStore):
    """In-memory memory store for development/testing."""

    def __init__(self):
        self._entries: dict[str, MemoryEntry] = {}
        self._indices: dict[str, dict[str, set[str]]] = {
            "type": {},
            "level": {},
            "source": {},
            "tags": {},
        }

    async def initialize(self) -> bool:
        return True

    def _index_entry(self, entry: MemoryEntry) -> None:
        """Update indices for an entry."""
        # Type index
        t = entry.type.value
        if t not in self._indices["type"]:
            self._indices["type"][t] = set()
        self._indices["type"][t].add(entry.id)

        # Level index
        level_name = entry.level.name
        if level_name not in self._indices["level"]:
            self._indices["level"][level_name] = set()
        self._indices["level"][level_name].add(entry.id)

        # Source index
        src = entry.source
        if src not in self._indices["source"]:
            self._indices["source"][src] = set()
        self._indices["source"][src].add(entry.id)

        # Tags index
        for tag in entry.tags:
            if tag not in self._indices["tags"]:
                self._indices["tags"][tag] = set()
            self._indices["tags"][tag].add(entry.id)

    def _unindex_entry(self, entry: MemoryEntry) -> None:
        """Remove entry from indices."""
        for _idx_name, idx in self._indices.items():
            for _key, ids in idx.items():
                ids.discard(entry.id)

    async def store(self, entry: MemoryEntry) -> bool:
        self._entries[entry.id] = entry
        self._index_entry(entry)
        return True

    async def retrieve(self, entry_id: str) -> MemoryEntry | None:
        entry = self._entries.get(entry_id)
        if entry and not entry.is_expired() and not entry.is_superseded():
            entry.access()
            return entry
        return None

    async def query(self, query: MemoryQuery) -> list[MemoryEntry]:
        # Start with all entries
        candidate_ids = set(self._entries.keys())

        # Filter by type
        if query.types:
            type_ids = set()
            for t in query.types:
                type_ids.update(self._indices["type"].get(t.value, set()))
            candidate_ids &= type_ids

        # Filter by level
        if query.levels:
            level_ids = set()
            for level in query.levels:
                level_ids.update(self._indices["level"].get(level.name, set()))
            candidate_ids &= level_ids

        # Filter by source
        if query.source:
            candidate_ids &= self._indices["source"].get(query.source, set())

        # Filter by tags
        if query.tags:
            tag_ids = None
            for tag in query.tags:
                ids = self._indices["tags"].get(tag, set())
                if tag_ids is None:
                    tag_ids = ids.copy()
                else:
                    tag_ids &= ids
            if tag_ids is not None:
                candidate_ids &= tag_ids

        # Apply content filters
        results = []
        for entry_id in candidate_ids:
            entry = self._entries[entry_id]

            if not query.include_expired and entry.is_expired():
                continue
            if not query.include_superseded and entry.is_superseded():
                continue

            if entry.confidence < query.min_confidence or entry.confidence > query.max_confidence:
                continue

            if query.since and entry.created_at < query.since:
                continue
            if query.until and entry.created_at > query.until:
                continue

            if query.content_filter and not query.content_filter(entry.content):
                continue

            results.append(entry)

        # Sort by confidence desc, then recency
        results.sort(key=lambda e: (-e.confidence, -e.created_at.timestamp()))

        return results[: query.limit]

    async def update(self, entry: MemoryEntry) -> bool:
        if entry.id in self._entries:
            self._unindex_entry(self._entries[entry.id])
            self._entries[entry.id] = entry
            self._index_entry(entry)
            return True
        return False

    async def delete(self, entry_id: str) -> bool:
        if entry_id in self._entries:
            self._unindex_entry(self._entries[entry_id])
            del self._entries[entry_id]
            return True
        return False

    async def health_check(self) -> dict[str, Any]:
        return {
            "healthy": True,
            "entries": len(self._entries),
            "type_indices": {k: len(v) for k, v in self._indices["type"].items()},
            "level_indices": {k: len(v) for k, v in self._indices["level"].items()},
        }


class MemorySystem:
    """
    Central memory system for OWNEX.

    Manages memory entries across evidence levels, handles promotion/
    contradiction, and provides querying capabilities.
    """

    def __init__(
        self,
        store: MemoryStore | None = None,
        auto_promote_threshold: float = 0.8,
        max_entries: int = 100000,
    ):
        self.store = store or InMemoryStore()
        self.auto_promote_threshold = auto_promote_threshold
        self.max_entries = max_entries

        # Callbacks
        self._promotion_callbacks: list[Callable[[MemoryEntry, EvidenceLevel], None]] = []
        self._contradiction_callbacks: list[Callable[[MemoryEntry, MemoryEntry], None]] = []

        # Stats
        self._stats = {
            "stored": 0,
            "retrieved": 0,
            "promoted": 0,
            "contradictions": 0,
            "expired": 0,
        }

        self.event_bus = get_core_event_bus()
        logger.info("MemorySystem initialized")

    async def initialize(self) -> bool:
        return await self.store.initialize()

    # ──────────────────────────────────────────────────────────────────────
    # CORE OPERATIONS
    # ──────────────────────────────────────────────────────────────────────

    def create_entry(
        self,
        type: MemoryType,
        level: EvidenceLevel,
        content: dict[str, Any],
        source: str,
        confidence: float = 0.5,
        tags: set[str] | None = None,
        expires_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Create a new memory entry."""
        now = datetime.now(UTC)
        entry = MemoryEntry(
            id=f"mem_{uuid.uuid4().hex[:12]}",
            type=type,
            level=level,
            content=content,
            source=source,
            created_at=now,
            updated_at=now,
            confidence=confidence,
            tags=tags or set(),
            expires_at=expires_at,
            metadata=metadata or {},
        )
        return entry

    async def remember(self, entry: MemoryEntry) -> str:
        """Store a memory entry."""
        # Check for contradictions
        await self._check_contradictions(entry)

        # Store
        await self.store.store(entry)
        self._stats["stored"] += 1

        # Check for auto-promotion
        if entry.level == EvidenceLevel.ASSUMED and entry.confidence >= self.auto_promote_threshold:
            await self.promote(entry.id, EvidenceLevel.OBSERVED, "system", "auto_promote")

        self.event_bus.publish(
            "memory:stored",
            id=entry.id,
            type=entry.type.value,
            level=entry.level.name,
            confidence=entry.confidence,
        )

        return entry.id

    async def recall(self, entry_id: str) -> MemoryEntry | None:
        """Retrieve a memory entry."""
        entry = await self.store.retrieve(entry_id)
        if entry:
            self._stats["retrieved"] += 1
        return entry

    async def search(self, query: MemoryQuery) -> list[MemoryEntry]:
        """Search memory."""
        return await self.store.query(query)

    async def update_entry(self, entry: MemoryEntry) -> bool:
        """Update an existing entry."""
        return await self.store.update(entry)

    async def forget(self, entry_id: str) -> bool:
        """Delete a memory entry."""
        return await self.store.delete(entry_id)

    # ──────────────────────────────────────────────────────────────────────
    # EVIDENCE MANAGEMENT
    # ──────────────────────────────────────────────────────────────────────

    async def promote(
        self,
        entry_id: str,
        new_level: EvidenceLevel,
        verified_by: str,
        method: str,
    ) -> bool:
        """Promote entry to higher evidence level."""
        entry = await self.store.retrieve(entry_id)
        if not entry:
            return False

        if entry.promote(new_level, verified_by, method):
            await self.store.update(entry)
            self._stats["promoted"] += 1

            self.event_bus.publish(
                "memory:promoted",
                id=entry.id,
                old_level=entry.level.name,
                new_level=new_level.name,
                verified_by=verified_by,
            )

            for cb in self._promotion_callbacks:
                try:
                    cb(entry, new_level)
                except Exception as e:
                    logger.error("Promotion callback failed: %s", e)

            return True
        return False

    async def add_evidence(self, entry_id: str, evidence_id: str) -> bool:
        """Add supporting evidence to an entry."""
        entry = await self.store.retrieve(entry_id)
        if not entry:
            return False

        entry.support(evidence_id)
        await self.store.update(entry)

        # Check for auto-promotion
        if entry.level == EvidenceLevel.ASSUMED and entry.confidence >= self.auto_promote_threshold:
            await self.promote(entry_id, EvidenceLevel.OBSERVED, "system", "evidence_accumulation")

        return True

    async def contradict(self, entry_id: str, contradiction_id: str) -> bool:
        """Mark an entry as contradicted by another."""
        entry = await self.store.retrieve(entry_id)
        if not entry:
            return False

        entry.contradict(contradiction_id)
        await self.store.update(entry)
        self._stats["contradictions"] += 1

        self.event_bus.publish(
            "memory:contradicted",
            entry_id=entry_id,
            contradiction_id=contradiction_id,
            new_confidence=entry.confidence,
        )

        for cb in self._contradiction_callbacks:
            try:
                contradiction = await self.store.retrieve(contradiction_id)
                if contradiction:
                    cb(entry, contradiction)
            except Exception as e:
                logger.error("Contradiction callback failed: %s", e)

        return True

    async def _check_contradictions(self, new_entry: MemoryEntry) -> None:
        """Check if new entry contradicts existing memories."""
        # Search for potentially contradictory entries
        query = MemoryQuery(
            types={new_entry.type},
            levels={EvidenceLevel.OBSERVED, EvidenceLevel.VERIFIED, EvidenceLevel.HISTORICAL},
            limit=50,
        )

        existing = await self.store.query(query)

        for existing_entry in existing:
            # Simple contradiction detection (could be enhanced with NLP)
            if self._are_contradictory(new_entry.content, existing_entry.content):
                await self.contradict(new_entry.id, existing_entry.id)
                await self.contradict(existing_entry.id, new_entry.id)

    def _are_contradictory(self, content1: dict, content2: dict) -> bool:
        """Check if two content dicts are contradictory."""
        # Simple heuristic: same keys with conflicting values
        common_keys = set(content1.keys()) & set(content2.keys())
        for key in common_keys:
            v1, v2 = content1[key], content2[key]
            if isinstance(v1, (str, int, float, bool)) and isinstance(v2, (str, int, float, bool)) and v1 != v2:
                # Check if they're semantic opposites
                if isinstance(v1, bool) and isinstance(v2, bool) and v1 != v2:
                    return True
                if (
                    isinstance(v1, (int, float))
                    and isinstance(v2, (int, float))
                    and abs(v1 - v2) / max(abs(v1), abs(v2), 1) > 0.5
                ):
                    return True
        return False

    # ──────────────────────────────────────────────────────────────────────
    # CONVENIENCE METHODS
    # ──────────────────────────────────────────────────────────────────────

    async def remember_fact(
        self,
        fact: dict[str, Any],
        source: str,
        confidence: float = 0.7,
        level: EvidenceLevel = EvidenceLevel.OBSERVED,
        tags: set[str] | None = None,
    ) -> str:
        """Remember a fact."""
        entry = self.create_entry(
            type=MemoryType.FACT,
            level=level,
            content=fact,
            source=source,
            confidence=confidence,
            tags=tags,
        )
        return await self.remember(entry)

    async def remember_observation(
        self,
        observation: dict[str, Any],
        source: str,
        confidence: float = 0.9,
        tags: set[str] | None = None,
    ) -> str:
        """Remember a direct observation."""
        entry = self.create_entry(
            type=MemoryType.OBSERVATION,
            level=EvidenceLevel.OBSERVED,
            content=observation,
            source=source,
            confidence=confidence,
            tags=tags,
        )
        return await self.remember(entry)

    async def remember_decision(
        self,
        decision: dict[str, Any],
        source: str,
        tags: set[str] | None = None,
    ) -> str:
        """Remember a decision and its rationale."""
        entry = self.create_entry(
            type=MemoryType.DECISION,
            level=EvidenceLevel.VERIFIED,
            content=decision,
            source=source,
            confidence=0.95,
            tags=tags,
        )
        return await self.remember(entry)

    async def remember_outcome(
        self,
        outcome: dict[str, Any],
        source: str,
        tags: set[str] | None = None,
    ) -> str:
        """Remember an action outcome."""
        entry = self.create_entry(
            type=MemoryType.OUTCOME,
            level=EvidenceLevel.HISTORICAL,
            content=outcome,
            source=source,
            confidence=1.0,
            tags=tags,
        )
        return await self.remember(entry)

    async def remember_learning(
        self,
        learning: dict[str, Any],
        source: str,
        confidence: float = 0.8,
        tags: set[str] | None = None,
    ) -> str:
        """Remember a learned pattern/insight."""
        entry = self.create_entry(
            type=MemoryType.LEARNING,
            level=EvidenceLevel.VERIFIED,
            content=learning,
            source=source,
            confidence=confidence,
            tags=tags,
        )
        return await self.remember(entry)

    async def remember_preference(
        self,
        preference: dict[str, Any],
        source: str = "user",
        tags: set[str] | None = None,
    ) -> str:
        """Remember a user preference."""
        entry = self.create_entry(
            type=MemoryType.PREFERENCE,
            level=EvidenceLevel.VERIFIED,
            content=preference,
            source=source,
            confidence=0.95,
            tags=tags,
        )
        return await self.remember(entry)

    async def remember_goal(
        self,
        goal: dict[str, Any],
        source: str,
        expires_at: datetime | None = None,
        tags: set[str] | None = None,
    ) -> str:
        """Remember an active goal."""
        entry = self.create_entry(
            type=MemoryType.GOAL,
            level=EvidenceLevel.VERIFIED,
            content=goal,
            source=source,
            confidence=1.0,
            expires_at=expires_at,
            tags=tags,
        )
        return await self.remember(entry)

    async def remember_hypothesis(
        self,
        hypothesis: dict[str, Any],
        source: str,
        confidence: float = 0.3,
        tags: set[str] | None = None,
    ) -> str:
        """Remember a testable hypothesis."""
        entry = self.create_entry(
            type=MemoryType.HYPOTHESIS,
            level=EvidenceLevel.ASSUMED,
            content=hypothesis,
            source=source,
            confidence=confidence,
            tags=tags,
        )
        return await self.remember(entry)

    # ──────────────────────────────────────────────────────────────────────
    # QUERY HELPERS
    # ──────────────────────────────────────────────────────────────────────

    async def get_facts(self, min_confidence: float = 0.5, tags: set[str] | None = None) -> list[MemoryEntry]:
        """Get verified facts."""
        query = MemoryQuery(
            types={MemoryType.FACT},
            levels={EvidenceLevel.VERIFIED, EvidenceLevel.HISTORICAL},
            min_confidence=min_confidence,
            tags=tags,
        )
        return await self.search(query)

    async def get_observations(self, source: str | None = None, since: datetime | None = None) -> list[MemoryEntry]:
        """Get raw observations."""
        query = MemoryQuery(
            types={MemoryType.OBSERVATION},
            levels={EvidenceLevel.OBSERVED},
            source=source,
            since=since,
        )
        return await self.search(query)

    async def get_decisions(self, since: datetime | None = None) -> list[MemoryEntry]:
        """Get past decisions."""
        query = MemoryQuery(
            types={MemoryType.DECISION},
            since=since,
        )
        return await self.search(query)

    async def get_outcomes(self, since: datetime | None = None) -> list[MemoryEntry]:
        """Get action outcomes."""
        query = MemoryQuery(
            types={MemoryType.OUTCOME},
            since=since,
        )
        return await self.search(query)

    async def get_learnings(self, tags: set[str] | None = None) -> list[MemoryEntry]:
        """Get learned patterns."""
        query = MemoryQuery(
            types={MemoryType.LEARNING},
            levels={EvidenceLevel.VERIFIED, EvidenceLevel.HISTORICAL},
            tags=tags,
        )
        return await self.search(query)

    async def get_preferences(self) -> list[MemoryEntry]:
        """Get user preferences."""
        query = MemoryQuery(
            types={MemoryType.PREFERENCE},
            levels={EvidenceLevel.VERIFIED, EvidenceLevel.HISTORICAL},
        )
        return await self.search(query)

    async def get_active_goals(self) -> list[MemoryEntry]:
        """Get active (non-expired) goals."""
        query = MemoryQuery(
            types={MemoryType.GOAL},
            include_expired=False,
        )
        return await self.search(query)

    async def get_hypotheses(self, min_confidence: float = 0.0) -> list[MemoryEntry]:
        """Get untested hypotheses."""
        query = MemoryQuery(
            types={MemoryType.HYPOTHESIS},
            levels={EvidenceLevel.ASSUMED},
            min_confidence=min_confidence,
        )
        return await self.search(query)

    # ──────────────────────────────────────────────────────────────────────
    # LIFECYCLE
    # ──────────────────────────────────────────────────────────────────────

    async def cleanup_expired(self) -> int:
        """Remove expired entries."""
        # This would need a full scan in a real implementation
        # For in-memory store, we check on access
        return 0

    async def archive_historical(self, older_than_days: int = 90) -> int:
        """Archive old verified facts as historical."""
        cutoff = datetime.now(UTC).replace(day=datetime.now(UTC).day - older_than_days)

        query = MemoryQuery(
            levels={EvidenceLevel.VERIFIED},
            until=cutoff,
            limit=self.max_entries,
        )

        entries = await self.search(query)
        count = 0

        for entry in entries:
            entry.level = EvidenceLevel.HISTORICAL
            await self.store.update(entry)
            count += 1

        return count

    # ──────────────────────────────────────────────────────────────────────
    # CALLBACKS
    # ──────────────────────────────────────────────────────────────────────

    def on_promotion(self, callback: Callable[[MemoryEntry, EvidenceLevel], None]) -> None:
        """Register promotion callback."""
        self._promotion_callbacks.append(callback)

    def on_contradiction(self, callback: Callable[[MemoryEntry, MemoryEntry], None]) -> None:
        """Register contradiction callback."""
        self._contradiction_callbacks.append(callback)

    # ──────────────────────────────────────────────────────────────────────
    # STATUS
    # ──────────────────────────────────────────────────────────────────────

    def get_stats(self) -> dict[str, Any]:
        """Get memory system stats."""
        return {
            **self._stats,
            "store_health": asyncio.create_task(self.store.health_check()),
        }

    async def health_check(self) -> dict[str, Any]:
        """Health check."""
        store_health = await self.store.health_check()
        return {
            "healthy": store_health.get("healthy", False),
            "store": store_health,
            "stats": self._stats,
        }


# ──────────────────────────────────────────────────────────────────────────
# SINGLETON
# ──────────────────────────────────────────────────────────────────────────

_memory_system: MemorySystem | None = None


def get_memory_system() -> MemorySystem:
    """Get or create the global memory system."""
    global _memory_system
    if _memory_system is None:
        _memory_system = MemorySystem()
    return _memory_system


async def initialize_memory(store: MemoryStore | None = None) -> MemorySystem:
    """Initialize the memory system."""
    global _memory_system
    _memory_system = MemorySystem(store=store)
    await _memory_system.initialize()
    logger.info("Memory system initialized")
    return _memory_system
