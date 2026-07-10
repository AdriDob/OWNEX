# Senior Copilot Architecture

> The Copilot is a **consumer of Core Services**, not a direct-access module.
> It never knows how CATEYE, ATLAS, or ODYSSEY work internally.

---

## 1. Responsibilities

- Analyze findings and hypotheses automatically
- Generate investigation plans per vulnerability type
- Audit system health, configuration, security, and architecture
- Pre-report quality review (simulates senior hunter checklist)
- Recommend next steps based on context
- Explain every decision with evidence and alternatives
- Enforce safety policies per authority level
- Detect inconsistencies across the system

## 2. Boundaries (what it does NOT do)

- Does NOT access apps (CATEYE/ATLAS/ODYSSEY) directly
- Does NOT execute actions — only recommends (unless authority permits)
- Does NOT store state in apps — only Decision Journal + Memory
- Does NOT publish events that it subscribes to (no loops)
- Does NOT replace the existing validation pipeline — complements it

## 3. Architecture

```
CopilotAgent
  │
  ├── CopilotContext        ← Context Builder (aggregates state before analysis)
  ├── FindingAnalyzer       ← Analyzes findings, evidence, confidence
  ├── Planner               ← Multi-step investigation plans per vuln type
  ├── Recommender           ← Next-step recommendations
  ├── CopilotReview         ← Pre-report quality checklist
  ├── ExplanationEngine     ← Human-readable explanations of decisions
  ├── PolicyEngine          ← Safety rules (centralized)
  └── IAuditor[]            ← Pluggable auditors (health, config, security, arch.)
```

### Module Map

| Module | File | Dependencies |
|---|---|---|
| CopilotAgent | `core/copilot/agent.py` | All sub-modules |
| CopilotConfig | `core/copilot/config.py` | os.environ |
| CopilotContext | `core/copilot/context.py` | permissions, config |
| AuthorityLevel | `core/copilot/permissions.py` | enum |
| DecisionConfidence | `core/copilot/permissions.py` | — |
| PolicyEngine | `core/copilot/permissions.py` | — |
| ExplanationEngine | `core/copilot/explain.py` | — |
| Planner | `core/copilot/planner.py` | CopilotContext |
| FindingAnalyzer | `core/copilot/analyzer.py` | CopilotContext, ExplanationEngine |
| Recommender | `core/copilot/recommender.py` | CopilotContext |
| CopilotReview | `core/copilot/review.py` | — |
| IAuditor | `core/copilot/auditor.py` | ABC |
| HealthAuditor | `core/copilot/auditor.py` | IAuditor |
| ConfigurationAuditor | `core/copilot/auditor.py` | IAuditor |
| SecurityAuditor | `core/copilot/auditor.py` | IAuditor |
| ArchitectureAuditor | `core/copilot/auditor.py` | IAuditor |

---

## 4. Authority Levels

| Level | Tag | Can do |
|---|---|---|
| Observer | `observer` | Only observe, never act |
| Assistant | `assistant` | Suggest actions, never execute |
| Operator | `operator` | Execute safe tasks (backup, health) |
| Senior Hunter | `senior_hunter` | Validate findings, decide workflow |
| Administrator | `admin` | Full system configuration |

Each level inherits all abilities of lower levels.

## 5. Decision Confidence Bands

| Band | Threshold | Behavior |
|---|---|---|
| No action | < 0.40 | Do not act, recommend human review |
| Request approval | 0.40–0.70 | Suggest but require human approval |
| Safe execute | 0.70–0.90 | Execute safe tasks autonomously |
| Auto close | > 0.90 | Can close the full workflow autonomously |

Authority + Confidence are checked together:
- Senior Hunter at 0.85 confidence → can execute safe tasks
- Senior Hunter at 0.50 confidence → must request approval
- Administrator bypasses all confidence gates

## 6. Policies (safety rules)

Built-in rules (configurable via `PolicyEngine`):

| Rule | Min Level | Description |
|---|---|---|
| `auto_report_min_confidence` | Senior Hunter | Never auto-report if confidence < 92% |
| `never_delete_data` | Administrator | Never permanently delete data |
| `never_touch_credentials` | Administrator | Never touch stored credentials |
| `config_read_only` | Administrator | Never modify config without admin |
| `safe_mode_only` | Operator | Never execute outside safe mode |
| `evidence_required` | Assistant | Every report needs reproducible evidence |

Policies can be added, removed, or cleared at runtime:
```python
copilot.policies.add(Policy("my_rule", "Description", level=AuthorityLevel.ADMINISTRATOR))
copilot.policies.remove("my_rule")
```

## 7. Decision Journal

Every Copilot decision is logged in-memory with:
- decision_id, agent_id, action, reason
- data snapshot (analysis result, plan, review)
- confidence, authority level
- timestamp

The journal is queryable:
```python
copilot.get_decision_journal(limit=10, action="analyze_finding")
copilot.explain("copilot-abc123-def456")
```

## 8. Lifecycle

### 8.1 Finding Created
```
finding:created (EventBus)
       │
       ▼
CopilotAgent.analyze_finding()
       │
       ├── CopilotContext (aggregates finding + evidence)
       ├── FindingAnalyzer (evaluates evidence, confidence, alternatives)
       ├── log_decision("analyze_finding", result)
       └── if needs_human → log "needs human review"
```

### 8.2 Pre-Report Review
```
CopilotAgent.pre_report_review(finding, verdict)
       │
       ├── CopilotReview.review() → 9-item checklist
       ├── log_decision("pre_report_review", report)
       └── returns ReviewReport (passed/failed + items)
```

### 8.3 System Audit
```
CopilotAgent.audit_system(system_state)
       │
       ├── HealthAuditor.audit()
       ├── ConfigurationAuditor.audit()
       ├── SecurityAuditor.audit()
       ├── ArchitectureAuditor.audit()
       ├── log_decision("audit_system", combined)
       └── returns AuditReport (all findings)
```

## 9. Events Consumed

| Event | Handler | Action |
|---|---|---|
| `finding:created` | `_copilot_finding_handler` | Analyze finding |
| `finding:status_changed` | `_copilot_finding_handler` | Re-analyze on status change |
| (future) `report:generated` | TBD | Pre-report review |

The Copilot does NOT publish events to avoid feedback loops.

## 10. Integration Points

| Core Service | Interface | Used by |
|---|---|---|
| EventBus | `subscribe()` | Analyze findings on events |
| Decision Journal | `log_decision()` (future) | Persistent decision storage |
| Unified Memory | `store()` (future) | Store analysis context |
| Evidence Graph | `query()` (future) | Retrieve evidence for/against |
| System State | `get_summary()` (future) | Audit context |

## 11. Configuration

All via environment variables (see `CONFIGURATION_GUIDE.md`):

| Variable | Default | Purpose |
|---|---|---|
| `COPILOT_AUTHORITY` | `observer` | Authority level |
| `COPILOT_MIN_CONFIDENCE_AUTO` | `0.70` | Auto-execution threshold |
| `COPILOT_MIN_CONFIDENCE_REPORT` | `0.92` | Auto-report threshold |
| `COPILOT_ENABLE_AUTO_AUDIT` | `true` | Periodic audit flag |
| `COPILOT_HUNTER_MODE` | `standard` | Hunter behavior mode |

## 12. Integrations

### Evidence Graph (Sprint 2 — ✅ Implemented)

The Copilot queries the Evidence Graph during analysis:

```
CopilotAgent.analyze_finding()
    │
    ├── EvidenceGraph.get_evidence(finding_id)  ← existing evidence for/against
    ├── EvidenceGraph.get_balance(finding_id)     ← net score
    ├── FindingAnalyzer.analyze()                ← uses evidence in context
    └── EvidenceGraph.record_from_copilot()      ← stores analysis result
```

Exposed via:
- `copilot.evidence_balance(hypothesis_id)` → net score, counts
- `copilot.evidence_for(hypothesis_id)` → list of pro evidence
- `copilot.evidence_against(hypothesis_id)` → list of con evidence

### Unified Memory (Sprint 3 — ✅ Implemented)

The Copilot stores and queries Unified Memory during analysis:

```
CopilotAgent.analyze_finding()
    │
    ├── remember_analysis()  → stores in memory/copilot namespace
    │
CopilotAgent.remember(namespace, key, content, tags, priority)
CopilotAgent.recall(namespace, search, tags, limit)
```

Every analysis result is auto-stored in the `copilot` namespace with:
- status, confidence, inconsistencies
- tags for filtering
- priority based on confidence

### Future Integrations

- **Decision Journal persistence**: Move from in-memory to SQLite
- **Copilot API endpoints**: Expose analysis, review, audit via REST
- **Copilot webhook**: Notify on findings needing human review
