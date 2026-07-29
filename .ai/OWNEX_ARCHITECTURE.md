# OWNEX Architecture v6 — Autonomous Work Operating System

> Architecture canonical document.
> All engines, interfaces, and data flows described here are the single source of truth for OWNEX.

---

## Core Philosophy

OWNEX is not a bug bounty tool. OWNEX is an **Autonomous Work Operating System**:

- **Sensors observe** the digital world without interpretation
- **Engines classify, plan, decide, execute, validate, and learn**
- **Everything is an Observation** until proven otherwise
- **Context is built before any AI call** — never a naked prompt
- **Strategy decides what to do** — engines execute the decision

---

## Architecture Overview

```
                    ┌─────────────────────────────────────┐
                    │        UNIVERSAL SENSOR NETWORK       │
                    │  (30+ sensors observing the world)    │
                    └──────────────────┬──────────────────┘
                                       │ list[Observation]
                                       ▼
                    ┌─────────────────────────────────────┐
                    │          OBSERVATION ENGINE           │
                    │  (Orchestrate sensors, collect obs)   │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │        NORMALIZATION ENGINE           │
                    │  (Unify formats: reward → payout →   │
                    │   hourly_rate → maximum_payout → EV)  │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │         IDENTITY ENGINE               │
                    │  (Resolution: obs A + obs B + obs C  │
                    │   → same target. NOT dedup — it's    │
                    │   entity resolution)                  │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │       CLASSIFICATION ENGINE           │
                    │  (Observation → Opportunity | Noise  │
                    │   | Needs Review. Assigns cycle,      │
                    │   source_type, tags, confidence)      │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │         OPPORTUNITY ENGINE            │
                    │  (Scoring, ranking, EV calculation,   │
                    │   personal_fit, competition analysis) │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │          STATE ENGINE                 │
                    │  (State machine: DISCOVERED → ... →  │
                    │   PAID | REJECTED | LEARNED)          │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │     ┌───────────────────────┐       │
                    │     │    STRATEGY ENGINE    │       │
                    │     │  Decide what to work  │       │
                    │     │  on RIGHT NOW based   │       │
                    │     │  on EV, time, skills, │       │
                    │     │  competition, energy  │       │
                    │     └───────────┬───────────┘       │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │         CONTEXT ENGINE                │
                    │  (Build enriched context: docs,      │
                    │   history, rules, memory, credentials,│
                    │   platform rules, past findings)      │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │         CAPABILITY ENGINE             │
                    │  (What can OWNEX do? Map opportunity │
                    │   requirements → available tools,    │
                    │   models, adapters, scripts)          │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │         PLANNING ENGINE               │
                    │  (Break opportunity into stages,     │
                    │   assign capabilities, set timeline) │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │        PREPARATION ENGINE             │
                    │  (Setup: clone repo, install deps,   │
                    │   configure tools, gather intel)     │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │         EXECUTION ENGINE              │
                    │  (Run agents, validate output,       │
                    │   auto-submit)                        │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │        VALIDATION ENGINE              │
                    │  (Verify results, check quality,     │
                    │   detect false positives, validate   │
                    │   against platform criteria)          │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │         LEARNING ENGINE               │
                    │  (Extract patterns, success rates,   │
                    │   failure modes, platform behavior,  │
                    │   personal performance data)          │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │         EVOLUTION ENGINE              │
                    │  (Evolve OWNEX itself: auto-healing, │
                    │   sensor tuning, strategy adjustment,│
                    │   pipeline optimization)              │
                    └─────────────────────────────────────┘
```

---

## Data Flow & Contracts

### 1. Observation — The Universal Data Unit

```python
@dataclass
class Observation:
    id: str                        # hash: sensor + external_id
    sensor_id: str                 # "hackerone", "github_issues", "rss"
    source_type: str               # "bug_bounty", "dev_task", "freelance", "ai_work"
    observed_at: datetime          # when the sensor detected it
    title: str
    description: str
    url: str | None
    tags: list[str]
    confidence: float = 0.8       # how sure the sensor is about the data
    external_id: str = ""          # original platform ID

    # Raw economic data (normalization engine converts these)
    estimated_reward_min: float = 0.0
    estimated_reward_max: float = 0.0
    estimated_effort_hours: float = 0.0
    reward_currency: str = "USD"
    reward_raw: str = ""           # original string like "$500 - $10,000"

    # State
    status: str = "new"            # new | normalized | identified | classified
    checksum: str = ""             # for identity resolution + dedup

    # Raw payload
    raw_data: dict = field(default_factory=dict)
    raw_format: str = ""           # "json", "html", "rss", "email", "file"

    # Cycle hint (set by ClassificationEngine)
    cycle: str | None = None       # "security", "forge", "pulse", "vault", "atlas"
```

**Key insight**: Observation is atomic. It carries no interpretation. It's a raw observation.

### 2. Sensor — Interface

```python
class Sensor(ABC):
    """A sensor observes ONE domain and returns Observations.
    
    Sensors have NO intelligence. They do NOT classify, score,
    or decide. They simply observe and report.
    
    Each sensor is easy to test independently:
    - Mock the external source
    - Verify the Observation list
    """
    
    id: str                        # unique sensor ID
    name: str                      # human name
    description: str = ""
    version: str = "1.0.0"
    
    # Configuration
    enabled: bool = True
    cadence_seconds: int = 3600   # default 1 hour
    max_observations_per_run: int = 100
    timeout_seconds: int = 30
    
    # Credentials required (names in the vault)
    required_credentials: list[str] = field(default_factory=list)
    
    @abstractmethod
    async def observe(self) -> list[Observation]:
        """Poll the external source and return observations.
        
        Implementations:
        - BugBountySensor: calls BountyScraper.scrape_all() then wraps in Observation
        - GitHubSensor: queries GitHub API for issues/PRs with bounties
        - RSSSensor: parses RSS feeds
        - EmailSensor: reads IMAP inbox
        """
        pass
    
    async def pre_filter(self, observation: Observation) -> Observation | None:
        """Optional: filter or enrich before releasing. Return None to discard."""
        return observation

    async def post_process(self, observations: list[Observation]) -> list[Observation]:
        """Optional: deduplicate within this sensor's batch."""
        return observations
```

### 3. ObservationEngine — Orchestrator

```python
class ObservationEngine:
    """Orchestrates all sensors.
    
    - Maintains sensor registry
    - Manages execution cadence
    - Handles failures gracefully (per-sensor error isolation)
    - Emits events on the EventBus
    
    Each sensor runs independently. A crash in one sensor
    NEVER affects others.
    """
    
    def register(self, sensor: Sensor): ...
    def unregister(self, sensor_id: str): ...
    
    async def poll_all(self) -> list[Observation]:
        """Run all enabled sensors, collect observations."""
        ...
    
    async def poll_one(self, sensor_id: str) -> list[Observation]:
        """Run a specific sensor."""
        ...
    
    def get_status(self) -> dict[str, dict]:
        """Returns sensor statuses: last_run, count, errors."""
        ...
```

### 4. NormalizationEngine

```python
class NormalizationEngine:
    """Normalizes observations into a universal format.
    
    Each platform expresses the same concept differently:
    - GitHub: "reward"
    - Algora: "bounty"
    - Bugcrowd: "maximum_payout"
    - DataAnnotation: "hourly_rate"
    - HackerOne: "offers_bounties: bool"
    
    This engine extracts the canonical fields:
    - estimated_reward_min, estimated_reward_max, reward_currency
    - effort_hours (from "estimated_time" / "time_estimate" / "hours")
    - tags (from "skills" / "categories" / "topics")
    - confidence (from data quality heuristics)
    """
    
    normalizers: dict[str, Normalizer]  # keyed by sensor_id
    
    def register_normalizer(self, sensor_id: str, normalizer: Normalizer): ...
    
    async def normalize(self, observation: Observation) -> Observation:
        """Returns the same observation with normalized fields."""
        ...
```

### 5. IdentityEngine

```python
class IdentityEngine:
    """Entity resolution for observations.
    
    Multiple sensors can observe the same target:
    - GitHub Issues API sees a new issue
    - RSS feed announces the same issue
    - Email notification about the same issue
    
    The IdentityEngine resolves:
    - fingerprint(obs) → same entity
    - Groups observations into identity clusters
    - Reports duplicates (same target, different sensor)
    
    NOT simple deduplication — it's entity resolution
    across disparate data sources.
    """
    
    def resolve(self, observation: Observation) -> str:
        """Returns the canonical entity_id for this observation.
        Creates a new entity if never seen before."""
        pass
    
    def get_entity_observations(self, entity_id: str) -> list[Observation]:
        """All observations for this entity."""
        pass
```

### 6. ClassificationEngine

```python
class ClassificationEngine:
    """Classifies observations into opportunities or discards.
    
    Decision tree:
    1. Is this a real opportunity? (has reward, has actionable scope)
    2. Which cycle? (security, forge, pulse, vault, atlas)
    3. What source_type? (bug_bounty, dev_bounty, ai_work, freelance)
    4. Confidence score (how reliable is this classification?)
    5. Tags + skills required
    
    The Classifier can use:
    - Rule-based classification (fast, for known patterns)
    - ML-based classification (for ambiguous observations)
    - LLM-based classification (for complex cases, expensive)
    
    Typical flow:
    1. Try rules first (90% of cases, <1ms)
    2. If confidence < threshold, escalate to ML/LLM
    """
    
    classifiers: dict[str, ClassifierRule]
    
    def add_rule(self, rule: ClassifierRule): ...
    
    async def classify(self, observation: Observation, depth: str = "fast") -> ScoredOpportunity | None:
        """Returns a ScoredOpportunity or None (noise)."""
        ...
```

### 7. StateEngine — Full State Machine

```
                    ┌──────────────┐
                    │  DISCOVERED  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  NORMALIZED  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ IDENTIFIED   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ CLASSIFIED   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ SCORED       │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼─────┐ ┌───▼────┐ ┌───▼──────┐
       │ STRATEGIC  │ │ QUEUED │ │ SKIPPED  │
       │ SELECTION  │ │        │ │ (reasons)│
       └──────┬─────┘ └───┬────┘ └──────────┘
              │            │
              └─────┬──────┘
                    │
             ┌──────▼───────┐
             │  PLANNING    │
             └──────┬───────┘
                    │
             ┌──────▼───────┐
             │ PREPARATION  │
             └──────┬───────┘
                    │
             ┌──────▼───────┐
             │  EXECUTION   │
             └──────┬───────┘
                    │
             ┌──────▼───────┐          ┌──────────┐
             │ VALIDATION   │─────────►│ REJECTED │
             └──────┬───────┘          └──────────┘
                    │ (accepted)
             ┌──────▼───────┐
             │  SUBMITTED   │
             └──────┬───────┘
                    │
             ┌──────▼───────┐
             │  ACCEPTED    │
             │  / PENDING   │
             │  / PAID      │
             └──────┬───────┘
                    │
             ┌──────▼───────┐
             │   LEARNED    │
             └──────┬───────┘
                    │
             ┌──────▼───────┐
             │   EVOLVED    │  (system improves from this)
             └──────────────┘

States:
- DISCOVERED → raw observation arrived
- NORMALIZED → fields unified
- IDENTIFIED → entity resolved
- CLASSIFIED → classified as opportunity or noise
- SCORED → EV, difficulty, personal_fit calculated
- STRATEGIC_SELECTION → StrategyEngine picked this
- QUEUED → waiting in pipeline
- PLANNING → plan being generated
- PREPARATION → setup in progress
- EXECUTION → active work
- VALIDATION → results being validated
- SUBMITTED → delivered to platform
- ACCEPTED / PENDING / PAID / REJECTED → outcome states
- LEARNED → pattern extracted
- EVOLVED → system adapted
- SKIPPED → strategically deprioritized
- NOISE → not an opportunity
```

### 8. ContextEngine

```python
class ContextEngine:
    """Builds enriched context for AI calls.
    
    Before ANY provider call, ContextEngine assembles:
    - Platform documentation (scope, rules, API)
    - Repository/Project context (README, issues, commits)
    - User history on this platform (past submissions, acceptance rate)
    - Similar past opportunities (from LearningEngine)
    - Platform-specific rules (what's in/out of scope)
    - Credentials and account info (from Vault)
    - Deadline / urgency
    - User preferences and strategy
    - Current state of the opportunity
    
    This turns a single prompt into a complete dossier.
    """
    
    context_sources: dict[str, ContextSource]
    
    def add_source(self, source: ContextSource): ...
    
    async def build_context(self, opportunity: ScoredOpportunity, depth: str = "standard") -> AgentContext:
        """Returns structured context ready for AI consumption."""
        ...
    
    async def build_system_prompt(self, context: AgentContext) -> str:
        """Converts context into system prompt for the model."""
        ...
```

### 9. CapabilityEngine

```python
class CapabilityEngine:
    """Maps opportunity requirements to OWNEX capabilities.
    
    OWNEX has capabilities, not tools:
    - web_scraping (urllib, httpx, playwright)
    - code_execution (python, node, docker)
    - git_operations (clone, commit, PR)
    - browser_automation (playwright)
    - android_automation (adb)
    - windows_automation (powershell)
    - document_parsing (pdf, docx, markdown)
    - llm_reasoning (provider router)
    - ocr (tesseract)
    - network_scanning (nmap, nuclei)
    - api_interaction (http client)
    
    The Planner asks: "What capabilities does this opportunity need?"
    CapabilityEngine answers: "These 3 capabilities, available via these tools/agents"
    """
    
    capabilities: dict[str, Capability]
    
    def register_capability(self, cap: Capability): ...
    
    def match_opportunity(self, opportunity: ScoredOpportunity) -> list[Capability]:
        """Returns capabilities required for this opportunity."""
        ...
    
    def can_execute(self, requirements: list[str]) -> bool:
        """Check if OWNEX has all required capabilities."""
        ...
```

### 10. StrategyEngine

```python
class StrategyEngine:
    """Decides what to work on RIGHT NOW.
    
    Not planning — DECIDING.
    
    Given N opportunities, StrategyEngine asks:
    - Which maximizes expected income RIGHT NOW?
    - Which has lowest competition?
    - Which fits current time block? (30min vs 4h)
    - Which plays to the user's strengths?
    - Is there a deadline approaching?
    - What's the opportunity cost of NOT doing X?
    
    Strategy is NOT static. It evolves with:
    - Market conditions (more/less competition)
    - User performance data (acceptance rate by type)
    - Time of day / day of week
    - Energy level (hard vs easy tasks)
    - Financial goals (this week/month/quarter)
    """
    
    strategies: list[Strategy]
    
    def add_strategy(self, strategy: Strategy): ...
    
    async def decide(self, opportunities: list[ScoredOpportunity], context: WorkContext) -> list[PrioritizedOpportunity]:
        """Returns opportunities in execution order."""
        ...
    
    async def should_continue(self, current: ScoredOpportunity, paused: bool = False) -> bool:
        """Check if we should keep working on current or switch."""
        ...
```

---

## Sensor Catalog — What Exists Today

### Sensors already implementable from current code:

| Sensor ID | Source | Code Location | Status |
|-----------|--------|---------------|--------|
| `bug_bounty` | HackerOne, Bugcrowd, Intigriti, YesWeHack, Immunefi, HackenProof, OpenBugBounty, GitHub, WebSearch | `cores/bounty_scraper/scraper.py` (995 líneas) | ✅ EXISTENTE — refactorizar como Sensor |
| `algora` | Algora API | `core/opportunity/adapters/forge/algora.py` | ✅ EXISTENTE |
| `issuehunt` | IssueHunt API | `core/opportunity/adapters/forge/issuehunt.py` | ✅ EXISTENTE |
| `opencollective` | OpenCollective API | `core/opportunity/adapters/forge/opencollective.py` | ✅ EXISTENTE |
| `superteam` | Superteam API | `core/opportunity/adapters/forge/superteam.py` | ✅ EXISTENTE |
| `freelancer_forge` | Freelancer for dev bounties | `core/opportunity/adapters/forge/freelancer.py` | ✅ EXISTENTE |
| `opire` | Opire API | `core/opportunity/adapters/forge/opire.py` | ✅ EXISTENTE |
| `github_sponsors` | GitHub Sponsors API | `core/opportunity/adapters/forge/github_sponsors.py` | ✅ EXISTENTE |
| `opencollective_projects` | OpenCollective Projects | `core/opportunity/adapters/forge/opencollective_projects.py` | ✅ EXISTENTE |
| `outlier` | Outlier.ai | `core/opportunity/adapters/pulse/__init__.py` | ✅ EXISTENTE |
| `dataannotation` | DataAnnotation.tech | `core/opportunity/adapters/pulse/__init__.py` | ✅ EXISTENTE |
| `mindrift` | Mindrift | `core/opportunity/adapters/pulse/__init__.py` | ✅ EXISTENTE |
| `remotasks` | Remotasks | `core/opportunity/adapters/pulse/__init__.py` | ✅ EXISTENTE |
| `freelancer_microtask` | Freelancer micro-tasks | `core/opportunity/adapters/pulse/__init__.py` | ✅ EXISTENTE |
| `linkedin_easyapply` | LinkedIn Easy Apply | `core/opportunity/adapters/pulse/__init__.py` | ✅ EXISTENTE (stub) |
| `opyre_microtask` | Opyre micro-tasks | `core/opportunity/adapters/pulse/__init__.py` | ✅ EXISTENTE (stub) |

**Total sensores implementables inmediatamente: 16+**

### Sensors to build new:

| Sensor ID | Source | Priority | Notes |
|-----------|--------|----------|-------|
| `github_issues` | GitHub Issues search (bounty labels) | Alta | API exists, wrapper needed |
| `rss` | RSS/Atom feeds (blogs, changelogs, CVE feeds) | Alta | feedparser |
| `email` | IMAP inbox (platform notifications) | Alta | imaplib |
| `discord` | Discord bot (community alerts) | Media | discord.py |
| `slack` | Slack webhooks | Media | SDK |
| `webhook` | Custom webhook receiver (API) | Media | FastAPI endpoint |
| `api_poller` | Generic REST API poller (configurable) | Alta | Generic crawler |
| `playwright` | Browser automation for JS-heavy sites | Alta | playwright |
| `security_txt` | security.txt parser (direct) | Media | URL pattern |
| `robots_txt` | robots.txt / sitemap discovery | Media | XML parser |
| `calendar` | Google Calendar events | Media | google API |
| `filesystem` | Local file watcher | Baja | watchdog |
| `bank` | Bank account/transaction monitor | Baja | Plaid API |
| `windows` | Windows event/notification watcher | Baja | PowerShell |
| `android` | Android notification watcher | Baja | ADB |

---

## Existing Patterns to Extract from BB Scraper (995 lines)

The `cores/bounty_scraper/scraper.py` contains battle-tested patterns for:

| Pattern | Lines | Generic Version | Extract To |
|---------|-------|-----------------|------------|
| Rate limiting | 50-52 | `BaseSensor._rate_limit()` | core/sensors/base.py |
| HTTP fetching with urllib | 54-91 | `BaseSensor._fetch_json()` / `_fetch_text()` | core/sensors/http.py |
| Pagination loop | 158-165 | `BaseSensor._paginate_url()` | core/sensors/http.py |
| Reward parsing | 94-107 | `NormalizationEngine.parse_reward()` | core/normalization/parsers.py |
| Dedup in scrape_all | 809-857 | `IdentityEngine.resolve()` | core/identity/engine.py |
| Error isolation per source | 824-835 | `ObservationEngine.poll_all()` | core/observation/engine.py |
| Change tracking | changes.py (184 lines) | `IdentityEngine` with snapshot | core/identity/snapshot.py |
| Timing/ISO formatting | 110-112 | `utils.time` | core/utils/time.py |
| HTML parsing patterns | scattered | `ContentParser` | core/normalization/parsers.py |
| Confidence scoring | 134 | `Observation.confidence` | native in dataclass |
| Batch size limits | scraper methods | `Sensor.max_observations_per_run` | native in Sensor |

**Nothing is lost. Everything is extracted, generalized, and reused.**

---

## OWNEX v5 vs v6 Code Map

```
OWNEX v5 (current)                          OWNEX v6 (target)
─────────────────                          ─────────────────
OWNEX/                                      OWNEX/
├── main.py                                 ├── main.py
├── pyproject.toml                          ├── pyproject.toml
├── config/                                 ├── config/
│   └── engine.yaml                         │   └── engine.yaml
├── core/                                   ├── core/
│   ├── pipeline/                           │   ├── pipeline/           ← unchanged
│   │   └── engine.py                       │   │   └── engine.py
│   ├── scheduler/                          │   ├── scheduler/          ← unchanged
│   │   └── scheduler.py                    │   │   └── scheduler.py
│   ├── eventbus/                           │   ├── eventbus/           ← unchanged
│   │   └── bus.py                          │   │   └── bus.py
│   ├── healing/                            │   ├── healing/            ← unchanged
│   │   ├── orchestrator.py                 │   │   ├── orchestrator.py
│   │   ├── monitor.py                      │   │   ├── monitor.py
│   │   ├── fixer.py                        │   │   ├── fixer.py
│   │   └── version.py                      │   │   └── version.py
│   ├── adapters/                           │   ├── adapters/           ← unchanged
│   │   ├── registry.py                     │   │   ├── registry.py
│   │   └── rastro.py                       │   │   └── rastro.py
│   ├── agents/                             │   ├── agents/             ← unchanged
│   │   ├── registry.py                     │   │   ├── registry.py
│   │   └── prompts/                        │   │   └── prompts/
│   └── learning/                           │   ├── learning/          ← unchanged
│       └── system.py                       │   │   └── system.py
│                                           │   ├── sensors/           🆕
│                                           │   │   ├── __init__.py
│                                           │   │   ├── base.py         (Sensor ABC)
│                                           │   │   ├── http.py         (HTTP mixins)
│                                           │   │   ├── bug_bounty.py   (extracted from scraper.py)
│                                           │   │   ├── rss.py
│                                           │   │   └── registry.py
│                                           │   ├── observation/      🆕
│                                           │   │   ├── __init__.py
│                                           │   │   ├── engine.py      (ObservationEngine)
│                                           │   │   └── models.py      (Observation dataclass)
│                                           │   ├── normalization/    🆕
│                                           │   │   ├── __init__.py
│                                           │   │   ├── engine.py
│                                           │   │   └── parsers.py
│                                           │   ├── identity/         🆕
│                                           │   │   ├── __init__.py
│                                           │   │   ├── engine.py
│                                           │   │   └── snapshot.py
│                                           │   ├── classification/  🆕
│                                           │   │   ├── __init__.py
│                                           │   │   ├── engine.py
│                                           │   │   └── rules.py
│                                           │   ├── opportunity/      ← expanded
│                                           │   │   ├── __init__.py
│                                           │   │   ├── engine.py
│                                           │   │   ├── scorer.py
│                                           │   │   └── models.py
│                                           │   ├── state/            🆕
│                                           │   │   ├── __init__.py
│                                           │   │   ├── engine.py
│                                           │   │   └── machine.py    (state machine)
│                                           │   ├── context/          🆕
│                                           │   │   ├── __init__.py
│                                           │   │   ├── engine.py
│                                           │   │   └── sources/
│                                           │   ├── strategy/         🆕
│                                           │   │   ├── __init__.py
│                                           │   │   ├── engine.py
│                                           │   │   └── strategies/
│                                           │   ├── capability/       🆕
│                                           │   │   ├── __init__.py
│                                           │   │   ├── engine.py
│                                           │   │   └── registry.py
│                                           │   ├── knowledge/        ← expanded
│                                           │   │   ├── __init__.py
│                                           │   │   ├── graph.py
│                                           │   │   └── queries.py
│                                           │   ├── loop/             ← unchanged
│                                           │   │   ├── engine.py
│                                           │   │   ├── registry.py
│                                           │   │   └── startup.py
│                                           │   ├── execution/        ← unchanged
│                                           │   │   └── runtime/
│                                           │   └── auto_submit/      ← unchanged
│                                           │       └── pipeline.py
Rastro/ (apps)                              Rastro/ (apps)
├── core/                                   ├── core/
│   ├── discovery/                          │   ├── discovery/         ← mark deprecated
│   │   ├── importer.py                     │   │   └── importer.py
│   │   └── scrape.py                       │   │
│   ├── memory/                             │   ├── memory/            ← unchanged
│   │   └── store.py                        │   │   └── store.py
│   ├── knowledge/                          │   ├── knowledge/         ← unused, remove or fold
│   │   └── graph.py                        │   │
│   ├── events/                             │   ├── events/            ← unchanged
│   │   ├── event_bus.py                    │   │   ├── event_bus.py
│   │   └── types.py                        │   │   └── types.py
│   └── loop/                               │   └── loop/             ← unchanged
├── cores/                                  ├── cores/
│   └── bounty_scraper/                     │   └── bounty_scraper/   ← keep as implementation
│       ├── scraper.py                      │       ├── scraper.py     detail of BB sensor
│       └── changes.py                      │       └── changes.py
├── apps/                                   ├── apps/
│   ├── cateye/                             │   ├── cateye/            ← unchanged
│   ├── forge/                              │   ├── forge/             ← unchanged
│   └── pulse/                              │   └── pulse/             ← unchanged
├── core/opportunity/                       ├── core/opportunity/    ← moves to OWNEX, Rastro
│   └── adapters/                           │   └── adapters/         imports from OWNEX
│       ├── forge/                          │       ├── forge/
│       ├── pulse/                          │       ├── pulse/
│       └── base.py                         │       └── base.py
└── database/                               └── database/
    ├── models.py                                ├── models.py
    └── models_economic.py                       └── models_economic.py
```

---

## Key Design Principles

### 1. Acoplamiento Intencional

No perseguimos "cero acoplamiento". Perseguimos:
- **Acoplamiento pequeño** — cada módulo conoce interfaces, no implementaciones
- **Acoplamiento bien delimitado** — contratos claros (Observation, Opportunity, Context)
- **Acoplamiento intencional** — sabemos exactamente por qué existe cada dependencia

### 2. Cada Engine es Independiente

- Cada engine tiene su propio test suite
- Cada engine puede ejecutarse sin los demás (para testing)
- Cada engine publica eventos en el EventBus
- Engine A no importa Engine B — se comunican por eventos y datos

### 3. Extraer, No Reemplazar

NUNCA reemplazar código existente que funciona. Siempre:
1. Identificar el patrón común
2. Extraerlo a un módulo base
3. Hacer que el código existente herede/use el módulo base
4. El código original sigue funcionando durante la transición

### 4. Capas de Velocidad

Cada engine tiene 3 modos:
- **fast** — reglas, <1ms, 90% de casos
- **standard** — heurísticas, <100ms, 9% de casos
- **deep** — LLM/ML, >1s, 1% de casos

Esto evita llamadas de IA innecesarias.

---

## Event Flow (Complete)

```
1. BugBountySensor.observe()
       │
       ├─→ EventBus.emit("observation:raw", [Observation])
       │
2. ObservationEngine.poll_all()
       │
       ├─→ EventBus.emit("observation:collected", count)
       │
3. NormalizationEngine.normalize(obs)
       │
       ├─→ EventBus.emit("observation:normalized", obs_id)
       │
4. IdentityEngine.resolve(obs)
       │
       ├─→ EventBus.emit("observation:identified", entity_id)
       │
5. ClassificationEngine.classify(obs)
       │
       ├─→ EventBus.emit("opportunity:created", opportunity_id)
       │   (if classified as opportunity)
       │
       ├─→ EventBus.emit("observation:discarded", obs_id)
       │   (if classified as noise)
       │
6. OpportunityEngine.score(opportunity)
       │
       ├─→ EventBus.emit("opportunity:scored", opportunity_id, score)
       │
7. StateEngine.transition(opportunity, new_state)
       │
       ├─→ EventBus.emit("opportunity:state_changed", from, to)
       │
8. StrategyEngine.decide(opportunities)
       │
       ├─→ EventBus.emit("strategy:selected", opportunity_id)
       │
9. ContextEngine.build_context(opportunity)
       │
       ├─→ EventBus.emit("context:built", opportunity_id)
       │
10. CapabilityEngine.match_opportunity(opportunity)
        │
        ├─→ EventBus.emit("capability:matched", requirements)
        │
11. PlanningEngine.plan(opportunity, context, capabilities)
        │
        ├─→ EventBus.emit("plan:created", plan_id)
        │
12. PreparationEngine.prepare(plan)
        │
        ├─→ EventBus.emit("preparation:done", plan_id)
        │
13. ExecutionEngine.execute(plan)
        │
        ├─→ EventBus.emit("execution:started", plan_id)
        ├─→ EventBus.emit("execution:completed", result)
        │
14. ValidationEngine.validate(result)
        │
        ├─→ EventBus.emit("validation:passed", submission)
        ├─→ EventBus.emit("validation:failed", errors)
        │
15. LearningEngine.learn(outcome)
        │
        ├─→ EventBus.emit("learning:pattern_extracted")
        │
16. EvolutionEngine.evolve()
        │
        ├─→ EventBus.emit("evolution:adapted", changes)
```

---

## DB Model Evolution

### Current (v5) → Target (v6)

```python
# Current v5 — BB coupled
class Program:       # bug bounty specific
class BountyTier:    # bug bounty specific
class BountyEvent:   # bug bounty specific
class Finding:       # bug bounty scoped

# Target v6 — Universal
class Observation:    # universal, raw sensor data
class Entity:         # resolved identity (universal)
class Opportunity:    # classified opportunity (universal)
class WorkState:      # state machine record (universal)
class WorkOutcome:    # execution result (universal)
class UserCapability: # user skills / preferences (universal)

# Keep existing BB models as specializations
class Program(Entity):       # BB-specific entity
class BountyFinding(Opportunity):  # BB-specific opportunity
```

---

## Documents de Referencia

- `.ai/AGENT_CHARTER.md` — reglas de operación
- `.ai/PRODUCTION_RULES.md` — reglas de producción
- `.ai/ROADMAP.md` — roadmap general
- `.ai/DECISIONS.md` — decisiones arquitectónicas

---

*Documento canónico — v1.0 — 2026-07-29*
*Próximo paso: Implementar FASE 4 (Sensores concretos) a FASE 14 (OWNEX v6 completo)*
