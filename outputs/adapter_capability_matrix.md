# Adapter Capability Matrix (OWNEX v8.0)

*Generated: 2026-10-31 | Per Integration Bundle P5 & §8*

## Adapter Architecture Philosophy

**Do not build 85 bespoke engines.** Design adapter boundaries around stable protocols and capabilities, with thin provider-specific implementations where justified.

**Shared connector families** (adapters map into these):
- Official REST/HTTP API connector
- GraphQL connector
- MCP client connector
- CLI/process adapter
- GitHub issues/PR/releases adapter
- Webhook/event adapter
- In-app browser adapter for permitted web workflows
- On-chain read/indexer adapter
- Wallet signing interface (external key custody; never store seed phrases/private keys in OWNEX)
- Payout-status/import adapter

**Capability states** (each source chooses ONE):
- **MANUAL_ONLY**: Display official link and instructions, no automation.
- **DISCOVERY_READ_ONLY**: Obtain public listings or permitted data.
- **PREPARE_ASSISTED**: Prepare drafts, code workspaces, checklists, evidence without submission.
- **EXECUTE_HUMAN_APPROVAL**: A human approves claim, bid, PR, report, application, upload, or transaction.
- **AUTO_REVERSIBLE**: Only low-risk reversible actions explicitly permitted by the provider and OWNEX policy.

No adapter may claim to support a provider action that has not been tested. Respect APIs, rate limits, robots/terms, account restrictions, and provider anti-automation rules. For website navigation, use OWNEX's in-app browser requirement; document platforms that block or do not support embedded browsers rather than silently launching an external browser.

---

## Source Adapter Mappings

### taskbounty: TaskBounty (task-bounty.ai)

- **Category**: dev_bounties
- **Evidence Grade**: B
- **Capability State**: `MANUAL_ONLY`
- **Permitted Capabilities**: task list polling, evidence drafting, human approval for submission
- **Connector Family**: `MCP client connector / REST API`
- **Argentina Availability**: conditional
- **Beginner Access**: medium
- **Payout Currency**: USDC/ETH
- **Blockers**: AI policy: no auto-submit
- **First Seen**: 2026-10-31
- **Last Verified**: 2026-10-31

---
### github_bounties: GitHub bounties

- **Category**: dev_bounties
- **Evidence Grade**: C
- **Capability State**: `MANUAL_ONLY`
- **Permitted Capabilities**: issue listing, PR monitoring
- **Connector Family**: `GitHub issues/PR/releases adapter`
- **Argentina Availability**: denied
- **Beginner Access**: low
- **Payout Currency**: unknown
- **Blockers**: no primary evidence, not recommended for OWNEX
- **First Seen**: 2026-10-31
- **Last Verified**: 2026-10-31

---
### agenthansa: AgentHansa

- **Category**: dev_bounties
- **Evidence Grade**: C
- **Capability State**: `MANUAL_ONLY`
- **Permitted Capabilities**: documentation reference only
- **Connector Family**: `MANUAL_ONLY (platform flagged as fake)`
- **Argentina Availability**: denied
- **Beginner Access**: low
- **Payout Currency**: unknown
- **Blockers**: no primary evidence, fake (SPA shell)
- **First Seen**: 2026-10-31
- **Last Verified**: 2026-10-31

---
### opire: Opire

- **Category**: dev_bounties
- **Evidence Grade**: C
- **Capability State**: `MANUAL_ONLY`
- **Permitted Capabilities**: bounty listing retrieval, evidence collection, work preparation
- **Connector Family**: `REST API connector (no auth)`
- **Argentina Availability**: conditional
- **Beginner Access**: medium
- **Payout Currency**: USDC/SOL
- **Blockers**: no primary evidence, research mixed on receipts
- **First Seen**: 2026-10-31
- **Last Verified**: 2026-10-31

---
### bugbounty: Bug Bounties (security)

- **Category**: security_bounty
- **Evidence Grade**: B
- **Capability State**: `MANUAL_ONLY`
- **Permitted Capabilities**: bounty status checking, draft report preparation, human verification gate
- **Connector Family**: `Official REST/HTTP API adapter`
- **Argentina Availability**: conditional
- **Beginner Access**: medium
- **Payout Currency**: USD/USDC-ETH
- **Blockers**: requires security skill, human verification gate, intermittent work
- **First Seen**: 2026-10-31
- **Last Verified**: 2026-10-31

---
