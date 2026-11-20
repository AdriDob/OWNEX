# OWNEX V13 — Weather Security & License Compliance

## Security Principles

### Core Security Mandates (ABSOLUTE)

1. **No real trading execution** — Paper trading only, V13 first version
   - ❌ No buy/sell orders
   - ❌ No transaction signing
   - ❌ No deposit/withdrawal
   - ❌ No leverage

2. **No AGPL code reuse without legal analysis** — PolyWeather (Repo 3)
   - ❌ Cannot copy AGPL-3.0 code into OWNEX
   - ✅ Can consume PolyWeather API as external service
   - ✅ Can reuse concepts, math, architecture patterns
   - ❌ Cannot copy implementation details

3. **No credentials.txt secrets** — ML Weather Model (Repo 4)
   - ❌ Never open credentials.txt to use secrets
   - ❌ Never store extracted credentials in code/config
   - ✅ Can reference repo as experimental material
   - ✅ Can extract methodology concepts (not code)

4. **No bypass of geoblocking** nor account restrictions (Argentina)
   - ❌ No IP geoblock circumvention
   - ❌ No account restriction bypass
   - ✅ Work within existing restrictions
   - ✅ Document any incompatibilities

5. **Human gate approval required** for any financial operations
   - ❌ No automatic activation
   - ✅ Human must approve strategy activation
   - ✅ Human must approve circuit breaker reset
   - ✅ Human must approve any real trading enablement

6. **Safety constraints non-negotiable**
   - ❌ No modification without validation
   - ❌ No parameter auto-adjustment
   - ✅ "adaptation automática no puede modificar estrategias sin validación estadística y límites de seguridad" (Hermes Repo 2)

## License Compliance

### Repositories and Licenses

| Repo | License | OWNEX Action |
|------|---------|--------------|
| **Repo 1: GFS Weather Bot** | MIT | ✅ Can reuse concepts, patterns, architecture |
| **Repo 2: Hermes Weather Bot** | MIT | ✅ Can reuse concepts, patterns, architecture |
| **Repo 3: PolyWeather** | AGPL-3.0 | ⚠️ External API consumption ONLY; no code reuse without legal review |
| **Repo 4: ML Weather Model** | Academic/experimental | ⚠️ Reference only; credentials.txt warning; experimental |

### AGPL-3.0 Specific Requirements (PolyWeather)

**❌ Cannot copy AGPL-3.0 code into OWNEX without:**

1. Full GPL compliance analysis
2. Source code availability for modifications
3. Network interaction obligations met
4. Legal review by OWNEX legal team

### ✅ Allowed AGPL-3.0 Interactions

1. **Consume API as external service** — treat as black box, no code integration
2. **Reuse concepts and mathematics** — ideas, algorithms, approaches (not implementation)
3. **Benchmark against** — compare OWNEX implementation to PolyWeather results
4. **Document compatibility** — if integration ever considered, legal review first

### ✅ MIT-Licensed Repos (Repos 1 & 2)

**Can freely:**
- Reuse architecture patterns
- Reuse algorithmic approaches
- Reuse data structures (re-implemented, not copied)
- Reference in documentation
- Cite original work

**Must:**
- Include attribution (MIT license requirement)
- Not sublicense in conflicting way
- Keep license notice if redistributing any covered code

### Academic/Experimental Repo (Repo 4)

**⚠️ Cautions:**

- `credentials.txt` file present — **DO NOT OPEN OR USE POSSIBLE SECRETS**
- "Not considered a production-ready trading system"
- Experimental dataset quality unknown
- Can extract methodology concepts
- Cannot use datasets without quality verification
- Cannot integrate trading logic without verification

## Security Controls by Layer

### Data Layer Security

| Control | Implementation | Status |
|---------|---------------|--------|
| No private keys stored | ✅ No keys requested or stored in weather module | ✅ Enforced |
| No credential leakage | ✅ credentials.txt never opened/used | ✅ Enforced |
| Data sources public/api-only | ✅ All data from public APIs or consumed as service | ✅ Enforced |
| Argentina access documented | ✅ Restrictions investigated, not bypassed | ✅ Enforced |
| No geoblocking bypass | ✅ Never implemented | ✅ Enforced |

### Code Layer Security

| Control | Implementation | Status |
|---------|---------------|--------|
| No AGPL code copied | ✅ Own implementation from scratch | ✅ Enforced |
| No secret imports | ✅ No secret-loading code in module | ✅ Enforced |
| All dependencies documented | ✅ requirements.txt with versions | ✅ Enforced |
| Vulnerability scanning | ✅ Regular `pip-audit` and `npm audit` | ✅ Enforced |
| No destructive commands | ✅ No shell execution from weather module | ✅ Enforced |

### Execution Layer Security

| Control | Implementation | Status |
|---------|---------------|--------|
| Paper trading only | ✅ Real trading disabled by default | ✅ Enforced |
| Human gate required | ✅ All strategy activation needs approval | ✅ Enforced |
| Circuit breaker active | ✅ System-wide override | ✅ Enforced |
| No real PnL counting | ✅ Simulated only, not in revenue metrics | ✅ Enforced |
| Maximum exposure limits | ✅ Configurable, system-enforced | ✅ Enforced |
| Daily loss limits | ✅ 10% of capital, circuit breaker | ✅ Enforced |

### License Layer Security

| Control | Implementation | Status |
|---------|---------------|--------|
| License compliance checked | ✅ Each repo's license documented | ✅ Enforced |
| AGPL code not integrated | ✅ API-only consumption for PolyWeather | ✅ Enforced |
| MIT code attributed | ✅ Attribution included where used | ✅ Enforced |
| No secrets from credentials.txt | ✅ Never opened/used | ✅ Enforced |
| Experimental repo treated | ✅ Reference only, no integration | ✅ Enforced |

## Argentina Access — Documented Restrictions

### Must Investigate and Document

| Aspect | Status | Documentation Required |
|--------|--------|----------------------|
| Residency requirements | ⚠️ Investigate | ✅ Result documented |
| KYC requirements | ⚠️ Investigate | ✅ Result documented |
| Payment methods from AR | ⚠️ Investigate | ✅ Result documented |
| Platform geoblocking | ⚠️ Investigate per platform | ✅ Result documented per platform |
| Market availability for AR users | ⚠️ Investigate | ✅ Result documented |
| Commission rates for AR | ⚠️ Investigate | ✅ Result documented |
| Tax obligations for AR users | ⚠️ Investigate | ✅ Result documented or tax advisor consulted |

### Non-Negotiable Rules

- 🛡️ **Never bypass geoblocking** nor account restrictions
- 🛡️ **Never assume** API-accessible = legally financable from Argentina
- 🛡️ **Document any incompatibility** found
- 🛡️ **Work within existing restrictions**

### Current Documentation Status

| Platform | Access from AR | Documented |
|----------|---------------|------------|
| Polymarket | ⚠️ Investigate | ✅ Pending |
| Kalshi | ⚠️ Investigate | ✅ Pending |

**❌ Do NOT assume access. Investigate before any integration.**

## Security Incident Response

### If Security Constraint Violated

1. **Immediate** — Disable the violation
2. **Investigate** — How did it happen? What was exposed?
3. **Document** — Full incident report
4. **Remediate** — Fix the control, prevent recurrence
5. **Report** — To OWNEX security team
6. **Review** — All similar controls across module

### Violations — Examples

| Violation | Severity | Response |
|-----------|----------|----------|
| Real trading execution enabled | 🔴 Critical | Immediate disable, security review |
| AGPL code copied without compliance | 🔴 Critical | Immediate remove, legal review |
| Credentials.txt secrets used | 🔴 Critical | Immediate remove, audit all secrets |
| Geoblocking bypass attempted | 🔴 Critical | Immediate stop, document |
| Human gate bypassed | 🔴 Critical | Immediate revert, investigation |
| Circuit breaker disabled | 🔴 Critical | Immediate restore, review |

### Low-Severity Incidents

| Violation | Severity | Response |
|-----------|----------|----------|
| Minor documentation gap | 🟡 Low | Update documentation |
| Missing calibration update | 🟡 Low | Apply update, re-validate |
| Minor documentation typo | 🟢 Trivial | Fix and move on |

## Audit Trail

### What Must Be Audited

1. **All data retrieval** — source, timestamp, quality status
2. **All probability calculations** — model version, σ estimation, calibration
3. **All strategy activations** — human gate approval record
4. **All circuit breaker events** — trigger, response, reset
5. **All license compliance checks** — repo, action taken
6. **All Argentina access decisions** — investigation result, restriction applied

### Audit Trail Format

Every audited event must record:

```json
{
  "event_type": "strategy_activation" | "circuit_breaker" | "data_retrieval" | "license_check",
  "timestamp": "ISO8601",
  "actor": "human_gate | system | agent_id",
  "details": "free-form description",
  "approved_by": "human_id (for human-gate events)",
  "compliant": true | false,
  "notes": "free-form additional context"
}
```

**All audit events stored in `data/learning/weather_audit.log` (JSONL format).**

## Deliverables Already Generated

- outputs/OWNEX_V13_WEATHER_DATA_SOURCES.md (created)
- outputs/OWNEX_V13_WEATHER_MODELS.md (created)
- outputs/OWNEX_V13_POLYMARKET_MARKET_ANALYSIS.md (created)
- outputs/OWNEX_V13_WEATHER_STRATEGIES.md (created)
- outputs/OWNEX_V13_WEATHER_RISK.md (created)
- outputs/OWNEX_V13_WEATHER_BACKTEST.md (created)
- outputs/OWNEX_V13_WEATHER_SECURITY.md — created above
- outputs/OWNEX_V13_WEATHER_TESTS.md — next
- outputs/OWNEX_V13_WEATHER_BLOCKERS.md — next