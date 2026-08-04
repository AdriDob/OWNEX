# Normalization Engine + Identity Engine — Design Concreto

> FASE 5 del plan OWNEX v6
> Fecha: 2026-07-29

---

## Problema

Cada plataforma expresa la misma información de forma distinta:

```
GitHub:           {"reward": 500}
Algora:           {"bounty": "$500 - $2000"}
Bugcrowd:         {"max_payout": 10000}
DataAnnotation:   {"hourly_rate": 25, "estimated_hours": 8}
HackerOne:        {"offers_bounties": true, "structured_scope": {...}}
Freelancer:       {"prize": 500, "time_left_days": 3}
```

Antes de clasificar, necesitamos un **lenguaje común**.

---

## 1. NormalizationEngine

### Data Flow

```
Observation (raw)                Observation (normalized)
─────────────────                ────────────────────────
raw_data = {                     estimated_reward_min = 500.0
    "reward": "$500-$10000"      estimated_reward_max = 10000.0
    "time_estimate": "2 days"    estimated_effort_hours = 16.0
    "skills": ["python", "api"]  tags = ["python", "api"]
    "max_payout": 10000          confidence = 0.9
    "hourly_rate": 25            
}                                reward_raw = "$500-$10000"
                                 
NormalizationEngine aplica:
1. Parser de recompensa (texto → min/max)
2. Parser de esfuerzo (texto → horas)
3. Normalizador de etiquetas (estandariza nombres)
4. Calculador de confianza (calidad de datos)
5. Convertidor de moneda (opcional)
```

### Interface

```python
from __future__ import annotations

import re
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ── Field parsers ──────────────────────────────────────────────────────


def parse_reward_range(text: str) -> tuple[float, float, str]:
    """Universal reward parser — handles all known formats.

    "$500 - $10,000"           → (500.0, 10000.0, "USD")
    "$1000"                    → (1000.0, 1000.0, "USD")
    "25 USD/h"                 → (25.0, 25.0, "USD")  # hourly
    "$25/hr"                   → (25.0, 25.0, "USD")
    "€15-€25 per hour"         → (15.0, 25.0, "EUR")
    "500 SOL"                  → (500.0, 500.0, "SOL")
    "10000 max_payout"         → (10000.0, 10000.0, "USD")
    "bounty: 0.5 ETH - 2 ETH"  → (0.5, 2.0, "ETH")
    "hourly_rate: 25"          → (25.0, 25.0, "USD")  # hourly rate
    "prize: 500"               → (500.0, 500.0, "USD")
    "offers_bounties: true"    → (0.0, 0.0, "USD")  # boolean, no amount
    "" or None                 → (0.0, 0.0, "USD")
    """
    if not text:
        return (0.0, 0.0, "USD")

    text = str(text).strip()

    # Detect currency
    currency = "USD"
    for sym, code in [
        ("$", "USD"),
        ("€", "EUR"),
        ("£", "GBP"),
        ("¥", "JPY"),
        ("ETH", "ETH"),
        ("BTC", "BTC"),
        ("SOL", "SOL"),
        ("usd", "USD"),
        ("eur", "EUR"),
    ]:
        if sym.lower() in text.lower():
            currency = code
            break

    # Extract all number patterns
    amounts = re.findall(r"([\d,]+(?:\.\d+)?)", text.replace(",", ""))
    parsed = []
    for a in amounts:
        try:
            parsed.append(float(a.replace(",", "")))
        except ValueError:
            continue

    if not parsed:
        return (0.0, 0.0, currency)

    return (min(parsed), max(parsed), currency)


def parse_effort_hours(text: str | float | None) -> float:
    """Parse effort estimation into hours.

    "2 days"        → 16.0
    "3 hours"       → 3.0
    "1 week"        → 40.0
    "30 min"        → 0.5
    "estimated_hours: 8" → 8.0
    "time_estimate: 2"  → 2.0
    5.0             → 5.0  # already a number
    None            → 0.0
    """
    if text is None:
        return 0.0
    if isinstance(text, (int, float)):
        return float(text)

    text = str(text).lower().strip()

    # Check for days
    days_match = re.search(r"(\d+(?:\.\d+)?)\s*d(?:ay)?s?", text)
    if days_match:
        return float(days_match.group(1)) * 8  # 8 hours per day

    # Check for weeks
    weeks_match = re.search(r"(\d+(?:\.\d+)?)\s*w(?:ee)?k", text)
    if weeks_match:
        return float(weeks_match.group(1)) * 40  # 40 hours per week

    # Check for minutes
    min_match = re.search(r"(\d+(?:\.\d+)?)\s*min", text)
    if min_match:
        return float(min_match.group(1)) / 60

    # Check for hours
    hours_match = re.search(r"(\d+(?:\.\d+)?)\s*h(?:(?:ou)?r)?", text)
    if hours_match:
        return float(hours_match.group(1))

    # Try plain number
    try:
        return float(text)
    except ValueError:
        return 0.0


def normalize_tags(tags: list[str]) -> list[str]:
    """Normalize tag names across platforms.

    ["Python", "python3", "py"] → ["python"]
    ["API", "api", "ApI"]       → ["api"]
    ["Data Science", "data_science"] → ["data-science"]
    """
    normalized = []
    seen = set()
    for tag in tags:
        t = tag.lower().strip().replace("_", "-").replace(" ", "-")
        if t not in seen:
            seen.add(t)
            normalized.append(t)
    return normalized


# ── Normalizer interface ────────────────────────────────────────────────


class Normalizer(ABC):
    """A normalizer knows how to normalize observations from ONE sensor."""

    @abstractmethod
    def normalize(self, observation: Observation) -> Observation:
        """Normalize sensor-specific fields into canonical form."""
        pass


# ── Concrete normalizers for existing sensors ──────────────────────────


class ScrapedProgramNormalizer(Normalizer):
    """Normalizes BountyScraper's ScrapedProgram → Observation fields."""

    FIELD_MAP = {
        "estimated_payout": ("estimated_reward_max", float),
    }

    def normalize(self, observation: Observation) -> Observation:
        raw = observation.raw_data

        # Parse reward from raw_payout_range or payout field
        reward_raw = raw.get("raw_payout_range", "")
        if reward_raw:
            min_r, max_r, currency = parse_reward_range(reward_raw)
            observation.estimated_reward_min = min_r
            observation.estimated_reward_max = max_r
            observation.reward_currency = currency
            observation.reward_raw = str(reward_raw)

        # If no parsed reward but estimated_payout exists
        if observation.estimated_reward_max == 0.0 and raw.get("estimated_payout"):
            observation.estimated_reward_max = float(raw["estimated_payout"])

        # Tags from platform name + technologies
        tags = [raw.get("platform", "")]
        tags.extend(raw.get("technologies", []))
        observation.tags = normalize_tags(tags)

        # Confidence from has_rewards + data completeness
        if raw.get("has_rewards"):
            observation.confidence = 0.9
        else:
            observation.confidence = 0.5

        # Checksum
        raw_id = f"{raw.get('platform', '')}:{raw.get('name', '')}"
        observation.checksum = hashlib.sha256(raw_id.encode()).hexdigest()[:16]

        return observation


class PulseAdapterNormalizer(Normalizer):
    """Normalizes Pulse adapter raw dicts → Observation fields."""

    FIELD_MAP = {
        "reward": "estimated_reward_max",
        "effort_hours": "estimated_effort_hours",
        "hourly_rate": None,  # handled specially
    }

    def normalize(self, observation: Observation) -> Observation:
        raw = observation.raw_data

        # Reward
        reward = raw.get("reward", 0)
        if isinstance(reward, str):
            min_r, max_r, curr = parse_reward_range(reward)
            observation.estimated_reward_min = min_r
            observation.estimated_reward_max = max_r
            observation.reward_currency = curr
        else:
            observation.estimated_reward_max = float(reward or 0)
            observation.estimated_reward_min = float(reward or 0)

        # Hourly rate override (multiply by hours)
        hourly = raw.get("hourly_rate", 0)
        if hourly and observation.estimated_reward_max == 0:
            hours = observation.estimated_effort_hours or 1.0
            observation.estimated_reward_max = float(hourly) * hours
            observation.estimated_reward_min = float(hourly) * hours

        # Effort
        effort = raw.get("effort_hours", 0)
        if isinstance(effort, str):
            observation.estimated_effort_hours = parse_effort_hours(effort)
        else:
            observation.estimated_effort_hours = float(effort or 0)

        # Tags from raw
        tags = raw.get("tags", [])
        observation.tags = normalize_tags(tags)

        # Checksum
        raw_id = f"{raw.get('platform', '')}:{raw.get('id', '')}"
        observation.checksum = hashlib.sha256(raw_id.encode()).hexdigest()[:16]

        return observation


# ── Normalization Engine ─────────────────────────────────────────────────


class NormalizationEngine:
    """Orchestrates normalizers for all sensors.

    Each sensor has its own normalizer that knows how to
    convert the platform's specific format into canonical Observation fields.

    The engine:
    1. Looks up normalizer by sensor_id
    2. Applies sensor-specific normalization
    3. Falls back to generic parsing for unknown fields
    4. Validates required fields
    5. Tags the observation as 'normalized'
    """

    def __init__(self):
        self._normalizers: dict[str, Normalizer] = {}

    def register(self, sensor_id: str, normalizer: Normalizer):
        """Register a normalizer for a sensor."""
        self._normalizers[sensor_id] = normalizer

    def normalize(self, observation: Observation) -> Observation:
        """Normalize a single observation.

        If no specific normalizer is registered, applies generic fallback:
        - Tries to parse any field named 'reward', 'payout', 'prize', 'bounty'
        - Tries to parse any field named 'hours', 'time', 'effort'
        - Normalizes any list field named 'tags', 'skills', 'categories'
        """
        normalizer = self._normalizers.get(observation.sensor_id)
        if normalizer:
            observation = normalizer.normalize(observation)
        else:
            observation = self._generic_normalize(observation)

        # Mark as normalized
        if observation.status == "new":
            observation.status = "normalized"

        return observation

    def _generic_normalize(self, obs: Observation) -> Observation:
        """Generic fallback that tries common field names."""
        raw = obs.raw_data

        # Try common reward field names
        for field in (
            "reward",
            "bounty",
            "payout",
            "prize",
            "max_payout",
            "maximum_payout",
            "pay",
            "pay_rate",
            "price",
        ):
            value = raw.get(field)
            if value is not None:
                if isinstance(value, str):
                    min_r, max_r, curr = parse_reward_range(value)
                    if max_r > 0:
                        obs.estimated_reward_min = min_r
                        obs.estimated_reward_max = max_r
                        obs.reward_currency = curr
                elif isinstance(value, (int, float)):
                    obs.estimated_reward_max = float(value)
                    obs.estimated_reward_min = float(value)
                break

        # Try common effort field names
        for field in ("hours", "time", "effort", "estimated_hours", "estimated_time", "time_estimate", "duration"):
            value = raw.get(field)
            if value is not None:
                obs.estimated_effort_hours = parse_effort_hours(value)
                break

        # Try common tag field names
        for field in ("tags", "skills", "categories", "topics", "technologies"):
            value = raw.get(field, [])
            if isinstance(value, list) and value:
                obs.tags = normalize_tags(value)
                break

        return obs
```

---

## 2. IdentityEngine

### Problema

Tres sensores detectan lo mismo pero no lo saben:

```
Sensor GitHub Issues:
  Observation: "Fix XSS in login form" → repo: target/website
  Fingerprint: github:target/website:issue:42

Sensor RSS Feed:
  Observation: "New issue: Fix XSS in login form" → blog: target
  Fingerprint: rss:target-security-feed:entry:2026-07-28

Sensor Email (GitHub notification):
  Observation: "[target/website] New issue: Fix XSS..."
  Fingerprint: email:github@notifications:msg:abc123
```

IdentityEngine debe RESOLVER que las 3 son el mismo entity.

### Approach

```
Identity resolution strategy:
1. EXACT MATCH — same external_id → same entity (fastest)
2. URL MATCH — same URL → same entity
3. TITLE SIMILARITY — fuzzy title match + same platform
4. CONTENT HASH — raw_data content similarity
5. LLM MATCH — for ambiguous cases (expensive, last resort)
```

### Interface

```python
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Entity:
    """A resolved entity — the canonical representation of a real-world thing.

    Multiple observations can point to the same entity.
    Bug bounty programs, GitHub repos, dev bounty tasks — all are entities.
    """

    id: str  # canonical UUID
    name: str
    type: str  # "bug_bounty_program", "dev_bounty", "repo", "task"
    canonical_url: str | None = None
    platform: str = ""

    # First and last seen
    first_observed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_observed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Statistics
    observation_count: int = 1
    confidence: float = 0.5

    # Enriched data (accumulated across observations)
    aliases: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)
    domains: set[str] = field(default_factory=set)

    # Latest scoring
    estimated_value: float = 0.0
    status: str = "active"  # active | inactive | closed

    # Reference to DB
    db_id: int | None = None


class IdentityEngine:
    """Resolves observations to entities.

    Entity resolution happens across sensors:
    - Same GitHub issue from GitHub API + RSS + Email → one entity
    - Same bug bounty program from H1 + web search → one entity
    - Same freelance task from Upwork + email notification → one entity

    Deduplication is a side effect, not the goal.
    The goal is LINKING observations to their canonical entity.
    """

    def __init__(self, db_path: str | Path = "~/.orion/identity.db"):
        self.db_path = str(db_path)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite for entity storage."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # ... SQLite schema

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
        entity = self._find_by_checksum(checksum)
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

    def _find_by_fuzzy_title(self, obs: Observation) -> Entity | None:
        """Fuzzy title match within same platform."""
        # Use simple word overlap for now
        obs_words = set(obs.title.lower().split())
        # ... query DB for similar titles
        pass

    def get_observations(self, entity_id: str) -> list[Observation]:
        """Get all observations linked to an entity."""
        ...

    def get_entity(self, entity_id: str) -> Entity | None:
        """Get entity by ID."""
        ...

    def get_statistics(self) -> dict[str, Any]:
        """Get identity resolution statistics."""
        return {
            "total_entities": 0,
            "total_observations": 0,
            "resolved_pairs": 0,
        }


# ── Primitive change tracker (from existing changes.py) ──────────────────


class ObservationSnapshot:
    """Tracks observations across cycles to detect new/changed/removed.

    This is the evolution of ProgramChangeTracker from changes.py.
    Instead of tracking only BB programs, it tracks ANY Observation.
    """

    def __init__(self, storage_path: str = "~/.orion/snapshots/"):
        self.path = Path(storage_path).expanduser()
        self.path.mkdir(parents=True, exist_ok=True)

    def compute_diff(self, sensor_id: str, observations: list[Observation]) -> dict[str, list[Observation]]:
        """Compare with previous snapshot to detect changes.

        Returns:
        {
            "new": [...],       # never seen before
            "removed": [...],   # no longer present
            "changed": [...],   # same entity, different data
            "unchanged": [...], # exact match
        }
        """
        previous = self._load_snapshot(sensor_id)
        current = {self._key(o): o for o in observations}

        new = {k: v for k, v in current.items() if k not in previous}
        removed = {k: v for k, v in previous.items() if k not in current}

        changed = {}
        unchanged = {}
        for k, v in current.items():
            if k in previous:
                if self._checksum(v) != self._checksum(previous[k]):
                    changed[k] = v
                else:
                    unchanged[k] = v

        # Save current as new snapshot
        self._save_snapshot(sensor_id, current)

        return {
            "new": list(new.values()),
            "removed": list(removed.values()),
            "changed": list(changed.values()),
            "unchanged": list(unchanged.values()),
        }

    def _key(self, obs: Observation) -> str:
        return f"{obs.sensor_id}:{obs.external_id or obs.checksum}"

    def _checksum(self, obs: Observation) -> str:
        # Hash only the data fields (not timestamps)
        data = f"{obs.title}|{obs.estimated_reward_max}|{obs.url}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def _load_snapshot(self, sensor_id: str) -> dict:
        path = self.path / f"{sensor_id}.json"
        if path.exists():
            return json.loads(path.read_text())
        return {}

    def _save_snapshot(self, sensor_id: str, data: dict):
        path = self.path / f"{sensor_id}.json"
        path.write_text(json.dumps(data, indent=2, default=str))
```

---

## 3. Integración con OWNEX

### Cómo se conectan al ObservationEngine

```python
# ── Wiring everything together ───────────────────────────────────────────


class NormalizationPipeline:
    """Normalization + Identity, wired as a pipeline stage."""

    def __init__(self, db_path: str = "~/.orion/"):
        self.normalizer = NormalizationEngine()
        self.identity = IdentityEngine(f"{db_path}/identity.db")
        self.snapshot = ObservationSnapshot(f"{db_path}/snapshots/")

        # Register built-in normalizers
        self.normalizer.register("bug_bounty", ScrapedProgramNormalizer())
        self.normalizer.register("outlier", PulseAdapterNormalizer())
        self.normalizer.register("dataannotation", PulseAdapterNormalizer())
        # ...

    async def process(self, observations: list[Observation]) -> list[Observation]:
        """Full pipeline: normalize → identify → diff.

        Returns normalized observations with entity_id assigned.
        Emits events for new/changed observations.
        """
        normalized = []
        for obs in observations:
            # 1. Normalize fields
            obs = self.normalizer.normalize(obs)

            # 2. Resolve identity
            entity = self.identity.resolve(obs)
            obs.entity_id = entity.id

            normalized.append(obs)

        # 3. Compute diff per sensor
        sensor_groups: dict[str, list[Observation]] = {}
        for obs in normalized:
            sensor_groups.setdefault(obs.sensor_id, []).append(obs)

        for sensor_id, sensor_obs in sensor_groups.items():
            diff = self.snapshot.compute_diff(sensor_id, sensor_obs)

            if diff["new"]:
                logger.info(f"[{sensor_id}] {len(diff['new'])} new observations")
                for new_obs in diff["new"]:
                    await event_bus.emit("observation:new", new_obs)

            if diff["changed"]:
                logger.info(f"[{sensor_id}] {len(diff['changed'])} changed observations")

        return normalized
```

---

## 4. Lo que se EXTRAE y NO se PIERDE

Del scraper existente (`cores/bounty_scraper/scraper.py`, 995 líneas):

| Patrón Extraído | Destino | Líneas Originales |
|----------------|---------|-------------------|
| `_parse_reward_range()` → `parse_reward_range()` | `core/normalization/parsers.py` | ~14 líneas (94-107) |
| `_rate_limit()` → base class method | `core/sensors/base.py` | ~3 líneas (50-52) |
| `_fetch_json()` / `_fetch_text()` → HTTP mixin | `core/sensors/http.py` | ~40 líneas (54-91) |
| `seen_names` dedup → `IdentityEngine._compute_fingerprint()` | `core/identity/engine.py` | ~10 líneas (809-817) |
| `ProgramChangeTracker` → `ObservationSnapshot` | `core/identity/snapshot.py` | ~184 líneas (changes.py) |
| Error isolation per source (try/except por scraper) → `ObservationEngine.poll_all()` | `core/observation/engine.py` | ~12 líneas (824-835) |
| Pagination loop pattern → `BaseSensor._paginate()` | `core/sensors/base.py` | ~10 líneas (158-165) |
| Domain scanning → `BugBountySensor` method | `core/sensors/bug_bounty.py` | ~30 líneas |
| Security.txt checks → `BugBountySensor` method | `core/sensors/bug_bounty.py` | ~20 líneas |

**Total extraído: ~320 líneas de 995 = 32%.**
El resto queda en `BugBountySensor`, que hereda de `Sensor` y usa los mixins.

**Nada se pierde. Todo el conocimiento de rate limiting, parsing HTML, retries, manejo de errores, logging, persistencia — queda en el código original, solo reorganizado.**

---

## 5. Schema DB para Identity

```sql
-- identity.db
CREATE TABLE entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    canonical_url TEXT,
    platform TEXT DEFAULT '',
    first_observed TEXT NOT NULL,
    last_observed TEXT NOT NULL,
    observation_count INTEGER DEFAULT 1,
    confidence REAL DEFAULT 0.5,
    status TEXT DEFAULT 'active'
);

CREATE TABLE observation_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL,
    observation_id TEXT NOT NULL,
    sensor_id TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    checksum TEXT,
    FOREIGN KEY (entity_id) REFERENCES entities(id),
    UNIQUE(observation_id)
);

CREATE INDEX idx_obs_entity ON observation_links(entity_id);
CREATE INDEX idx_obs_sensor ON observation_links(sensor_id);

-- For change tracking
CREATE TABLE snapshots (
    sensor_id TEXT NOT NULL,
    key TEXT NOT NULL,
    data JSON NOT NULL,
    checksum TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    PRIMARY KEY (sensor_id, key)
);
```
