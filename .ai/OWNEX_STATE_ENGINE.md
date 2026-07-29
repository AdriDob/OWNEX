# State Engine — State Machine Concreta

> FASE 6 del plan OWNEX v6
> Fecha: 2026-07-29

---

## 1. Estado Completos y Transiciones

```
                ┌──────────────┐
                │  DISCOVERED  │  Observación cruda recibida
                └──────┬───────┘
                       │ normalize()
                ┌──────▼───────┐
                │  NORMALIZED  │  Campos unificados
                └──────┬───────┘
                       │ resolve()
                ┌──────▼───────┐
                │  IDENTIFIED  │  Entity resolvida
                └──────┬───────┘
                       │ classify()
                ┌──────▼───────┐
                │  CLASSIFIED  │  Es oportunidad o ruido
                └──────┬───────┘
                       │ score()
                ┌──────▼───────┐
                │    SCORED    │  EV, difficulty, personal_fit
                └──────┬───────┘
                       │
           ┌───────────┼───────────┐
           │           │           │
    ┌──────▼─────┐ ┌──▼────┐ ┌───▼──────┐
    │ QUEUED     │ │ACTIVE │ │ SKIPPED  │
    │ (waiting)  │ │(doing)│ │(not now) │
    └──────┬─────┘ └──┬────┘ └──────────┘
           │          │
           └─────┬────┘
                 │
          ┌──────▼───────┐     pending review, error, etc.
          │  BLOCKED     │─────────────────┐
          └──────┬───────┘                 │
                 │ resume()                │
          ┌──────▼───────┐                 │
          │ IN_PROGRESS  │                 │
          └──────┬───────┘                 │
                 │ complete()              │
          ┌──────▼───────┐                 │
          │  SUBMITTED   │                 │
          └──────┬───────┘                 │
                 │                         │
          ┌──────▼───────┐     ┌───────────▼──────┐
          │  VALIDATING  │────►│ NEEDS_REVISION   │
          └──────┬───────┘     └───────────┬──────┘
                 │ (valid)                 │ (revise)
          ┌──────▼───────┐                 │
          │   ACCEPTED   │◄────────────────┘
          └──────┬───────┘
                 │
     ┌───────────┼───────────┐
     │           │           │
┌────▼────┐ ┌───▼───┐ ┌────▼──────┐
│  PAID   │ │CLOSED │ │ REJECTED  │
│ (goal)  │ │(w/out │ │ (platform)│
└────┬────┘ │ pay)  │ └────┬──────┘
     │      └───┬───┘      │
     └──────┬───┘──────────┘
            │
     ┌──────▼───────┐
     │   LEARNED    │  Patrón extraído
     └──────┬───────┘
            │
     ┌──────▼───────┐
     │   EVOLVED    │  Sistema mejorado
     └──────────────┘

States de ciclo de vida corto:
  NOISE         → no es oportunidad (no persiste)
  DUPLICATE     → ya existe como otra observación
  STALE         → oportunidad expiró
  WITHDRAWN     → usuario canceló
  ARCHIVED      → referencia histórica
```

---

## 2. Interfaz Concreta

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any


class OpportunityState(str, Enum):
    """All possible states in the opportunity lifecycle."""
    
    # Discovery pipeline
    DISCOVERED = "discovered"
    NORMALIZED = "normalized"
    IDENTIFIED = "identified"
    CLASSIFIED = "classified"
    SCORED = "scored"
    
    # Active pipeline
    QUEUED = "queued"
    ACTIVE = "active"
    BLOCKED = "blocked"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    VALIDATING = "validating"
    NEEDS_REVISION = "needs_revision"
    
    # Terminal states
    ACCEPTED = "accepted"
    PAID = "paid"
    REJECTED = "rejected"
    CLOSED = "closed"
    
    # Learning
    LEARNED = "learned"
    EVOLVED = "evolved"
    
    # Discard states
    SKIPPED = "skipped"
    NOISE = "noise"
    DUPLICATE = "duplicate"
    STALE = "stale"
    WITHDRAWN = "withdrawn"
    ARCHIVED = "archived"


# ── Transition rules ─────────────────────────────────────────────────────

STATE_TRANSITIONS: dict[OpportunityState, list[OpportunityState]] = {
    OpportunityState.DISCOVERED: [OpportunityState.NORMALIZED, OpportunityState.NOISE, OpportunityState.DUPLICATE],
    OpportunityState.NORMALIZED: [OpportunityState.IDENTIFIED, OpportunityState.NOISE],
    OpportunityState.IDENTIFIED: [OpportunityState.CLASSIFIED, OpportunityState.NOISE],
    OpportunityState.CLASSIFIED: [OpportunityState.SCORED, OpportunityState.NOISE],
    OpportunityState.SCORED: [OpportunityState.QUEUED, OpportunityState.SKIPPED, OpportunityState.ACTIVE],
    OpportunityState.QUEUED: [OpportunityState.ACTIVE, OpportunityState.SKIPPED, OpportunityState.STALE],
    OpportunityState.ACTIVE: [OpportunityState.IN_PROGRESS, OpportunityState.BLOCKED, OpportunityState.WITHDRAWN],
    OpportunityState.BLOCKED: [OpportunityState.IN_PROGRESS, OpportunityState.SKIPPED],
    OpportunityState.IN_PROGRESS: [OpportunityState.SUBMITTED, OpportunityState.BLOCKED, OpportunityState.WITHDRAWN],
    OpportunityState.SUBMITTED: [OpportunityState.VALIDATING, OpportunityState.REJECTED],
    OpportunityState.VALIDATING: [OpportunityState.ACCEPTED, OpportunityState.NEEDS_REVISION, OpportunityState.REJECTED],
    OpportunityState.NEEDS_REVISION: [OpportunityState.IN_PROGRESS, OpportunityState.WITHDRAWN],
    OpportunityState.ACCEPTED: [OpportunityState.PAID, OpportunityState.CLOSED],
    OpportunityState.PAID: [OpportunityState.LEARNED],
    OpportunityState.REJECTED: [OpportunityState.LEARNED, OpportunityState.ARCHIVED],
    OpportunityState.CLOSED: [OpportunityState.LEARNED, OpportunityState.ARCHIVED],
    OpportunityState.LEARNED: [OpportunityState.EVOLVED, OpportunityState.ARCHIVED],
    OpportunityState.EVOLVED: [OpportunityState.ARCHIVED],
    # Terminal states can only go to archival
    OpportunityState.SKIPPED: [OpportunityState.ACTIVE, OpportunityState.ARCHIVED],
    OpportunityState.NOISE: [OpportunityState.ARCHIVED],
    OpportunityState.DUPLICATE: [OpportunityState.ARCHIVED],
    OpportunityState.STALE: [OpportunityState.ARCHIVED],
    OpportunityState.WITHDRAWN: [OpportunityState.ARCHIVED],
    OpportunityState.ARCHIVED: [],  # Final state
}


# ── State record ─────────────────────────────────────────────────────────


@dataclass
class StateRecord:
    """A single state transition record."""
    from_state: OpportunityState | None
    to_state: OpportunityState
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    actor: str = "system"  # "system", "user", "scheduler", "engine"


@dataclass
class StateMachine:
    """State machine for a single opportunity."""
    
    opportunity_id: str
    current_state: OpportunityState = OpportunityState.DISCOVERED
    history: list[StateRecord] = field(default_factory=list)
    in_state_since: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    transitions_count: int = 0
    
    def can_transition(self, new_state: OpportunityState) -> bool:
        """Check if transition is valid."""
        if new_state == self.current_state:
            return False
        valid = STATE_TRANSITIONS.get(self.current_state, [])
        return new_state in valid
    
    def transition(
        self,
        new_state: OpportunityState,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
        actor: str = "system",
    ) -> bool:
        """Attempt a state transition. Returns True if successful."""
        if not self.can_transition(new_state):
            logger.warning(
                f"Cannot transition {self.opportunity_id}: "
                f"{self.current_state.value} → {new_state.value}"
            )
            return False
        
        record = StateRecord(
            from_state=self.current_state,
            to_state=new_state,
            reason=reason,
            metadata=metadata or {},
            actor=actor,
        )
        
        self.history.append(record)
        self.current_state = new_state
        self.in_state_since = record.timestamp
        self.transitions_count += 1
        
        # Emit event
        asyncio.ensure_future(
            event_bus.emit("opportunity:state_changed", {
                "opportunity_id": self.opportunity_id,
                "from": record.from_state.value if record.from_state else None,
                "to": record.to_state.value,
                "reason": reason,
                "actor": actor,
            })
        )
        
        return True
    
    def is_terminal(self) -> bool:
        """Check if in a terminal state."""
        return self.current_state in TERMINAL_STATES
    
    def is_active(self) -> bool:
        """Check if in an active (non-terminal, non-waiting) state."""
        return self.current_state in ACTIVE_STATES
    
    def time_in_state(self) -> float:
        """Seconds in current state."""
        return (datetime.now(timezone.utc) - self.in_state_since).total_seconds()
    
    def summary(self) -> dict[str, Any]:
        """Summary for display."""
        return {
            "opportunity_id": self.opportunity_id,
            "current_state": self.current_state.value,
            "in_state_since": self.in_state_since.isoformat(),
            "time_in_state_hours": round(self.time_in_state() / 3600, 1),
            "transitions_count": self.transitions_count,
            "is_terminal": self.is_terminal(),
        }


# ── Convenience sets ─────────────────────────────────────────────────────


TERMINAL_STATES = {
    OpportunityState.PAID,
    OpportunityState.ARCHIVED,
}

ACTIVE_STATES = {
    OpportunityState.IN_PROGRESS,
    OpportunityState.ACTIVE,
    OpportunityState.SUBMITTED,
    OpportunityState.VALIDATING,
    OpportunityState.NEEDS_REVISION,
}

# Goals — the actual end states we care about for revenue analysis
GOAL_STATES = {
    OpportunityState.PAID,
    OpportunityState.ACCEPTED,
}


# ── State Engine ─────────────────────────────────────────────────────────


class StateEngine:
    """Manages state machines for all opportunities.
    
    This is the backbone of the opportunity lifecycle.
    Every opportunity has exactly one state machine.
    The state engine persists transitions and provides querying.
    """
    
    def __init__(self, db_path: str = "~/.orion/state.db"):
        self.db_path = str(db_path)
        self._machines: dict[str, StateMachine] = {}
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite storage for state transitions."""
        import sqlite3
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS state_machines (
                opportunity_id TEXT PRIMARY KEY,
                current_state TEXT NOT NULL,
                in_state_since TEXT NOT NULL,
                transitions_count INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS state_transitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opportunity_id TEXT NOT NULL,
                from_state TEXT,
                to_state TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                reason TEXT DEFAULT '',
                actor TEXT DEFAULT 'system',
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (opportunity_id) REFERENCES state_machines(opportunity_id)
            )
        """)
        conn.commit()
        conn.close()
    
    def get_or_create(self, opportunity_id: str) -> StateMachine:
        """Get existing machine or create new."""
        if opportunity_id not in self._machines:
            self._machines[opportunity_id] = StateMachine(
                opportunity_id=opportunity_id
            )
        return self._machines[opportunity_id]
    
    def transition(
        self,
        opportunity_id: str,
        to_state: OpportunityState,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
        actor: str = "system",
    ) -> bool:
        """Transition and persist."""
        machine = self.get_or_create(opportunity_id)
        result = machine.transition(to_state, reason, metadata, actor)
        if result:
            self._persist_transition(machine, machine.history[-1])
        return result
    
    def _persist_transition(self, machine: StateMachine, record: StateRecord):
        """Write transition to DB."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT OR REPLACE INTO state_machines (opportunity_id, current_state, in_state_since, transitions_count) "
            "VALUES (?, ?, ?, ?)",
            (machine.opportunity_id, record.to_state.value, record.timestamp.isoformat(), machine.transitions_count),
        )
        conn.execute(
            "INSERT INTO state_transitions (opportunity_id, from_state, to_state, timestamp, reason, actor, metadata) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                machine.opportunity_id,
                record.from_state.value if record.from_state else None,
                record.to_state.value,
                record.timestamp.isoformat(),
                record.reason,
                record.actor,
                json.dumps(record.metadata),
            ),
        )
        conn.commit()
        conn.close()
    
    def get_history(self, opportunity_id: str) -> list[StateRecord]:
        """Get full transition history."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT from_state, to_state, timestamp, reason, actor, metadata "
            "FROM state_transitions WHERE opportunity_id = ? ORDER BY id",
            (opportunity_id,),
        )
        records = []
        for row in cursor:
            records.append(StateRecord(
                from_state=OpportunityState(row[0]) if row[0] else None,
                to_state=OpportunityState(row[1]),
                timestamp=datetime.fromisoformat(row[2]),
                reason=row[3],
                actor=row[4],
                metadata=json.loads(row[5]),
            ))
        conn.close()
        return records
    
    def get_state_summary(self) -> dict[str, int]:
        """Count opportunities by state."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT current_state, COUNT(*) FROM state_machines GROUP BY current_state"
        )
        summary = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return summary
    
    def get_opportunities_by_state(self, state: OpportunityState) -> list[str]:
        """Get all opportunity IDs in a given state."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT opportunity_id FROM state_machines WHERE current_state = ?",
            (state.value,),
        )
        ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        return ids
    
    def get_statistics(self) -> dict[str, Any]:
        """Get state engine statistics."""
        summary = self.get_state_summary()
        return {
            "total_opportunities": sum(summary.values()),
            "by_state": summary,
            "total_terminal": sum(summary.get(s.value, 0) for s in TERMINAL_STATES),
            "total_active": sum(summary.get(s.value, 0) for s in ACTIVE_STATES),
            "total_paid": summary.get(OpportunityState.PAID.value, 0),
        }
```

---

## 3. Integración con el Pipeline

La StateEngine se conecta al pipeline en cada etapa:

```python
# Cada engine notifica a StateEngine cuando cambia el estado:

class ObservationEngine:
    async def poll_all(self) -> list[Observation]:
        observations = []
        for sensor in self.sensors:
            obs = await sensor.observe()
            observations.extend(obs)
        
        # State: DISCOVERED
        for obs in observations:
            state_engine.transition(
                obs.id, 
                OpportunityState.DISCOVERED,
                reason=f"Sensor {obs.sensor_id}: {len(observations)} observations",
                actor="observation_engine",
            )
        return observations

class ClassificationEngine:
    async def classify(self, obs) -> ScoredOpportunity | None:
        result = await self._classify(obs)
        if result:
            # State: CLASSIFIED
            state_engine.transition(
                obs.id,
                OpportunityState.CLASSIFIED,
                reason=f"Classified as {result.cycle}/{result.source_type}",
                actor="classification_engine",
            )
        else:
            # State: NOISE
            state_engine.transition(
                obs.id,
                OpportunityState.NOISE,
                reason="Classification: noise (no reward, no scope)",
                actor="classification_engine",
            )
        return result
```

---

## 4. Automatizaciones por Estado

El StateEngine permite acciones automáticas en transiciones:

```python
# En la inicialización del sistema:
STATE_ACTIONS: dict[OpportunityState, Callable] = {
    OpportunityState.DISCOVERED: normalize_opportunity,
    OpportunityState.NORMALIZED: resolve_identity,
    OpportunityState.IDENTIFIED: classify_opportunity,
    OpportunityState.CLASSIFIED: score_opportunity,
    OpportunityState.SCORED: decide_strategy,
    OpportunityState.QUEUED: execute_when_slot_available,
    OpportunityState.SUBMITTED: wait_for_validation,
    OpportunityState.VALIDATING: check_platform_response,
    OpportunityState.NEEDS_REVISION: notify_user_or_revise,
    OpportunityState.PAID: extract_learning,
    OpportunityState.REJECTED: extract_rejection_pattern,
}
```

---

## 5. Consultas Útiles

```sql
-- Oportunidades activas hoy
SELECT * FROM state_machines 
WHERE current_state IN ('queued', 'active', 'in_progress', 'submitted', 'validating')
  AND in_state_since > datetime('now', '-7 days');

-- Oportunidades pagadas este mes
SELECT o.*, t.reason, t.timestamp 
FROM state_transitions t 
JOIN opportunities o ON t.opportunity_id = o.id 
WHERE t.to_state = 'paid' 
  AND t.timestamp > datetime('now', 'start of month');

-- Oportunidades bloqueadas más de 48h
SELECT * FROM state_machines 
WHERE current_state = 'blocked' 
  AND in_state_since < datetime('now', '-48 hours');

-- Pipeline funnel
SELECT current_state, COUNT(*) 
FROM state_machines 
WHERE current_state IN ('discovered', 'classified', 'scored', 'in_progress', 'submitted', 'paid', 'rejected')
GROUP BY current_state;
```
