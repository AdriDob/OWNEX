# Twin Tree Adjudication Report

**Generated**: 2026-11-10

## Summary

| Metric | Count |
|--------|-------|
| Total twins (same path in core/ and cores/) | 198 |
| Identical twins (byte-for-byte) | 196 |
| Divergent twins (intentional) | 2 |
| Files only in core/ | 490 |
| Files only in cores/ | 710 |
| Orphaned twins deleted | 122 |
| Divergent twins synced to core/ | 11 |

## Architecture Decision

**core/** = Canonical, active development (what's currently running)
**cores/** = Legacy, maintained for backward compatibility

For divergent twins, we need to determine which version is authoritative:

### Divergence Analysis

#### 1. `autonomy/coder_agent.py`
- **core/**: Newer version with updated agent logic
- **cores/**: Legacy version
- **Decision**: core/ is authoritative

#### 2. `credentials/vault.py`
- **core/**: Updated security implementation
- **cores/**: Legacy implementation  
- **Decision**: core/ is authoritative

#### 3. `cycles/knowledge_capture.py`
- **core/**: New knowledge capture logic
- **cores/**: Legacy version
- **Decision**: core/ is authoritative

#### 4. `events/event_bus.py`
- **core/**: Updated event bus
- **cores/**: Legacy event bus
- **Decision**: core/ is authoritative

#### 5. `evidence/composer.py`
- **core/**: New evidence composition
- **cores/**: Legacy version
- **Decision**: core/ is authoritative

#### 6. `health/engine.py`
- **core/**: New health monitoring
- **cores/**: Legacy version
- **Decision**: core/ is authoritative

#### 7. `memory/__init__.py`
- **core/**: New memory package init
- **cores/**: Restored from core/ (needed for imports)
- **Decision**: Keep cores/ sync with core/

#### 8. `opportunity/engine.py` ⚠️ CRITICAL
- **core/**: NEW - has `OpportunityType`, discovery integration, scoring
- **cores/**: OLD - has `OpportunityCategory`, `SEED_OPPORTUNITIES`, legacy structure
- **Import analysis**:
  - `core/cycles/metrics.py` imports `SEED_OPPORTUNITIES` from `cores.opportunity.engine`
  - `core/opportunity/discovery_to_workbank.py` imports from `core.opportunity.engine`
  - Various `cores/` files import from `cores.opportunity.engine`
- **Decision**: **BOTH NEED TO COEXIST** - different use cases
  - `core/opportunity/engine.py` = New discovery pipeline
  - `cores/opportunity/engine.py` = Legacy engine with seed data

#### 9. `opportunity/models.py`
- **core/**: New models
- **cores/**: Legacy models
- **Decision**: core/ is authoritative for new code

#### 10. `opportunity/scoring.py`
- **core/**: New scoring logic (used by `make check`)
- **cores/**: Legacy scoring
- **Decision**: core/ is authoritative

#### 11. `opportunity/source_payment_docs.py`
- **core/**: New payment doc handling
- **cores/**: Legacy version
- **Decision**: core/ is authoritative

#### 12. `validation/confidence.py`
- **core/**: New validation logic
- **cores/**: Legacy version
- **Decision**: core/ is authoritative

## Action Items

### Completed
- [x] Deleted 122 orphaned twins from cores/ (no importers)
- [x] Restored `cores/memory/__init__.py` (needed for package imports)
- [x] Investigated `core/cycles/metrics.py` dependency on `SEED_OPPORTUNITIES` → legacy engine must stay
- [x] Sync 11 divergent twins to core/ versions (copiado desde core/ a cores/)

### Intentional Divergences (by design)
- `memory/__init__.py`: versión ligeramente diferente (cores/ más simple, suficiente para imports)
- `opportunity/engine.py`: legacy (`cores/`) tiene `SEED_OPPORTUNITIES` + `OpportunitySource`; nuevo (`core/`) tiene `OpportunityType` + discovery pipeline. Coexisten por propósitos distintos.

## Makefile Verification

```bash
make check  # ✅ PASSES - 100 passed, 1 skipped
```
