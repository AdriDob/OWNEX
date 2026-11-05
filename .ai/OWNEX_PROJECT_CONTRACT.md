# OWNEX — Product, Architecture, Functional & Completion Contract

## 1. PRODUCT IDENTITY (NON-NEGOTIABLE)

**OWNEX** is a:
- **Personal Work, Income & Capital Operating System**
- Cross-platform desktop-first software platform
- Coordinates work opportunities, external work sources, task execution, AI-assisted operations, security research, data work, blockchain/crypto activities, investments, financial tracking and general system management through one unified environment

**Purpose**: Help one person discover legitimate opportunities, qualify for them, prepare and execute work, verify outcomes, deliver results, receive payments, manage capital and continuously improve operations.

**Must not become**: A collection of disconnected dashboards, mock modules, duplicated engines or independent agents. Must behave as **one coherent operating system**.

## 2. PRODUCT SCOPE (EXPLICIT)

### 2.1 Work Source Extensibility
OWNEX supports an extensible registry of external work source categories:
- Software development and programming (GitHub, funded issues, grants)
- QA, testing and automation
- Cybersecurity, authorized pentesting and bug bounty
- AI training, evaluation, annotation and data collection
- Data processing, labeling and analysis
- AI agent tasks and AI-assisted services
- Freelance and professional service marketplaces
- Crypto and Web3 bounties
- Blockchain development and smart contract work
- Research, competitions, grants and technical challenges
- New categories discovered in the future

**Each integration must declare actual capabilities**: Discovery, Read, Search, Authentication, Submission, Execution, Payment tracking, Account status, Monitoring.

**Must not claim** a capability exists when it is not implemented and verified.

### 2.2 Opportunity & Work Orchestration
Required capabilities:
- Discover opportunities, normalize to common model, detect duplicates
- Evaluate eligibility, identify missing requirements
- Estimate effort and realistic reward, assess probability and uncertainty
- Calculate expected value and risk, prioritize best next action
- Track lifecycle and deadlines, prepare workspaces and execution plans
- Track submissions, reviews and payments, learn from historical results

**Prioritization must account for**: Actual user constraints, regional eligibility, payment accessibility, experience requirements, interviews, portfolios, examinations, time, costs, risk and probability of payment.

**Estimated earnings must never** be presented as verified earnings.

### 2.3 Unified Execution Environment
Provides a central workspace to prepare and execute work:
- Project and repository management, code workspace, terminal integration
- Git operations, AI-assisted programming, documentation generation
- Testing and debugging, data processing, security analysis
- Evidence collection, task execution, deliverable preparation
- Submission preparation, execution history

**Reuse existing implementations** when they satisfy the contract.

### 2.4 Security & Bug Bounty
Support authorized security workflows:
- Scope ingestion, asset inventory, reconnaissance
- Evidence-backed findings, vulnerability validation
- Deduplication, severity assessment, report preparation
- Submission tracking, remediation tracking

**Every finding must have an evidence trail**. AI-generated hypotheses are not verified vulnerabilities.

### 2.5 AI & Intelligence
Provides contextual AI assistance across the whole platform:
- Contextual assistant, natural-language interaction, task planning
- Research, tool orchestration, code assistance, analysis
- Summarization, monitoring, anomaly detection
- Recommendation generation, workflow optimization

**AI must operate through explicit capabilities, permissions, evidence and policies**. Do not create unnecessary agents or independent orchestration systems.

### 2.6 Investments & Capital
Target capabilities:
- Portfolio tracking, asset tracking, traditional markets
- Cryptocurrencies, exchange and broker integrations
- Market data, technical and fundamental analysis
- Alerts, strategy management, backtesting
- Paper trading, risk management, exposure and allocation tracking
- Trade history, fees, profit and loss
- Copy-trading integrations when supported
- Controlled automated execution when explicitly authorized

**Separate clearly**: Simulation, Historical backtesting, Market observation, Proposed operation, Authorized real operation, Confirmed execution.

**Financial actions must use strict authorization policies, limits, audit records and secure credentials**. Never imply that simulated or estimated returns are actual profits.

### 2.7 Income & Financial Truth
Tracks the complete economic lifecycle: DISCOVERED → ESTIMATED → PENDING → VERIFIED → AVAILABLE → WITHDRAWN.

**These states must have explicit definitions and evidence requirements**. Track: Expected compensation, Pending payments, Confirmed payments, Available balances, Withdrawals, Fees, Currency conversions, Payment methods, Reconciliation, Historical income, Realized profits and losses.

**Do not count** hypothetical rewards, estimated balances or unconfirmed platform data as collected income.

### 2.7 System Management & Autonomy
Monitor and manage own operational state:
- Health checks, process monitoring, scheduler monitoring
- Background task management, integration health, queue management
- Resource monitoring, error detection, recovery where safe
- Configuration management, backup and restoration, updates
- Logs, audit trails, notifications, permission management

## 3. CENTRAL ORCHESTRATION MODEL

**ONE coherent Core Loop**: DISCOVER → EVALUATE → PREPARE → EXECUTE → VERIFY → DELIVER → EARN → LEARN

All domains and modules must participate in this common lifecycle where applicable.

**Central orchestration system must**:
1. Discover available work and system events
2. Evaluate priorities and constraints
3. Generate the best next actions
4. Prepare execution contexts
5. Execute permitted operations
6. Verify actual outcomes
7. Request human authorization when necessary
8. Register evidence and results
9. Update financial and operational state
10. Improve future decisions from verified history

**Do not create parallel Core Loops**. Do not allow independent agents to contradict central policies.

## 4. HUMAN INTERVENTION MODEL

**Objective**: Maximum safe semi-autonomy with minimum unnecessary interruptions.

**Classify operations into**:
- MANUAL. ASSISTED. AUTO_REVERSIBLE. HUMAN_APPROVAL.

**Fully automatic where safe**:
- Discovery, Synchronization, Classification, Analysis
- Preparation, Reversible internal operations
- Monitoring, Verification, Reporting
- Non-destructive maintenance

**Human approval or participation required**:
- Financial transfers and withdrawals
- Irreversible operations
- External commitments
- Contract acceptance
- Sensitive permission changes
- Identity verification
- MFA/CAPTCHA
- Submissions with legal or financial consequences
- Actions outside previously approved policies

**Implement or consolidate a central PolicyEngine with**: ALLOW, DENY, REQUIRE_APPROVAL.

Every sensitive action must have an auditable authorization path.

## 5. DESKTOP-FIRST CROSS-PLATFORM EXPERIENCE

**Main user experience**: Unified OWNEX desktop application.

**Current known stack**:
- Tauri 2 + Rust desktop shell
- Vue 3 + TypeScript frontend
- Vite
- Python + FastAPI backend
- SQLite/local persistence where appropriate
- Shared typed contracts
- Background services and adapters

**Target platforms**: Windows native, Linux native, macOS where technically feasible, Mobile companion application sharing domain services and contracts.

**Do not claim** a platform is supported until its native build, installation, startup, persistence, update and recovery paths are verified.

**Desktop interface must provide a unified experience**, including:
- Home/Dashboard, Work/Opportunities, Sources/Integrations
- Unified Workspace, Development, Security, AI Work
- Data Work, Crypto/Blockchain, Investments/Capital
- Automation, Monitoring, Human Approval Center
- Activity/Audit, Settings

**Every visible feature must be classified as**:
- IMPLEMENTED_AND_CONNECTED, IMPLEMENTED_BUT_DISCONNECTED
- PARTIALLY_IMPLEMENTED, SIMULATION_ONLY, PLACEHOLDER
- NOT_IMPLEMENTED, BLOCKED_BY_EXTERNAL_DEPENDENCY

**No fake functionality, mock success, invented balances or decorative controls** presented as working features.

## 6. ARCHITECTURE

### 6.1 Current Architecture (.ai/ARCHITECTURE_CURRENT.md)
Describes exclusively that which exists, is connected and was verified.

### 6.2 Target Architecture (.ai/ARCHITECTURE_TARGET.md)
Incorporates the approved architectural direction:
`PRODUCT → DOMAIN → APPLICATION → INFRASTRUCTURE → EXTERNAL WORLD`

**Canonical responsibilities**:
- ValidationService
- EvidenceBundle
- PolicyEngine
- ExecutionService + adapters
- Unitary Core Loop

### 6.3 Architecture Contract (.ai/ARCHITECTURE_CONTRACT.md)
API and synchronization contracts between layers.

### 6.4 Executable Contracts
- `cores/contracts/api.py`: DTOs and API backend contracts
- `packages/ownex-contracts/`: Typescript shared types
- `cores/direct_work_engine/models.py`: Domain model and taxonomy
- `cores/work_taxonomy.py`: Normalization between taxonomies

**No fourth system of contracts**. Define compatibility verification between existing definitions.

## 5. HUMAN INTERVENTION MODEL (DETAILED)

**Classify operations into**:
- MANUAL. ASSISTED. AUTO_REVERSIBLE. HUMAN_APPROVAL.

**Fully automatic where safe**:
- Discovery, Synchronization, Classification, Analysis
- Preparation, Reversible internal operations
- Monitoring, Verification, Reporting
- Non-destructive maintenance

**Human approval or participation required**:
- Financial transfers and withdrawals
- Irreversible operations
- External commitments
- Contract acceptance
- Sensitive permission changes
- Identity verification
- MFA/CAPTCHA
- Submissions with legal or financial consequences
- Actions outside previously approved policies

**Implement or consolidate a central PolicyEngine with**: ALLOW, DENY, REQUIRE_APPROVAL.

Every sensitive action must have an auditable authorization path.

## 6. DEFINITIVE CONTENT REQUIREMENTS

Create/update `.ai/OWNEX_PROJECT_CONTRACT.md`. It must contain:

1. **Product identity** - What OWNEX is and for whom it works
2. **Product purpose** - Core purpose and value proposition
3. **Target users and usage model** - Who uses it and how
4. **Explicit product scope** - Capability domains and boundaries
5. **Domain and module definitions** - How modules map to domains
6. **Work source extensibility model** - How new sources are integrated
7. **Integration capability contract** - What each integration must declare
8. **Opportunity lifecycle** - From discovery to payment
9. **Unified execution model** - Central workspace and workflow
10. **Core Loop** - DISCOVER → EVALUATE → PREPARE → EXECUTE → VERIFY → DELIVER → EARN → LEARN
11. **AI responsibilities and limitations** - What AI can/cannot do
12. **Investment and capital scope** - Tracking, analysis, execution
13. **Financial truth model** - State lifecycle: DISCOVERED → ... → WITHDRAWN
14. **Autonomy levels** - MANUAL/ASSISTED/AUTO_REVERSIBLE/HUMAN_APPROVAL
15. **Human Gates** - When human intervention is required
16. **Security and privacy requirements** - Credentials, sessions, devices, isolation
17. **Desktop-first cross-platform requirements** - Windows, Linux, macOS, mobile
18. **Frontend functional requirements** - Vue 3, Tailwind v4, Vite, connected features
19. **Persistence and data integrity requirements** - SQLite, backups, recovery
20. **Observability and recovery** - Health checks, logs, audit trails
21. **API and shared contracts** - Executable DTOs and type definitions
22. **Testing and verification requirements** - Unit, integration, E2E, acceptance
23. **Performance and resource principles** - Resource usage, stability guidelines
24. **Documentation governance** - .ai/ as single source of truth
25. **Definition of Done** - Measurable completion criteria (see below)
26. **Explicit non-goals and prohibited architectural patterns**
27. **Rules for future extensions and integrations**

## 7. DEFINITION OF DONE (MEASURABLE COMPLETION CRITERIA)

OWNEX is not complete merely because its frontend builds or its tests pass.

**Measurable completion criteria**:

| Category | Criterion |
|---|---|
| **Product coherence** | Single purpose and scope inequívocos |
| **Architecture consistency** | Single coherent architecture, no redundant motors |
| **Source integration framework** | At least one genuinely functional end-to-end source integration per supported category |
| **Opportunity discovery and normalization** | Real external opportunities verified and normalized |
| **Eligibility and prioritization** | Correct regional eligibility and EV ranking |
| **Execution lifecycle** | DISCOVER→EVALUATE→PREPARE→EXECUTE→VERIFY→DELIVER→EARN→LEARN operational |
| **Evidence collection** | Every finding has an evidence trail |
| **Human approval workflows** | Financial transfers, irreversible ops require explicit approval |
| **AI orchestration** | AI assistance through explicit capabilities only |
| **Financial truth** | Estimated/pending/verified/available/distinguished correctly |
| **Investment functionality** | Real module with simulation and controlled execution |
| **Frontend-to-backend connectivity** | All frontend domains connected to real backend endpoints |
| **Desktop startup and shutdown** | Clean install, start, persistence, update verified |
| **Installation and update** | Fresh install works on declared platforms |
| **Persistent state** | Data survives restarts, failures, updates |
| **Backup and recovery** | Backups restorable, data not lost |
| **Native platform builds** | Tauri Android APK builds verified |
| **Security** | Permissions, isolation, secrets, Human Gates |
| **Automated tests** | Test suite passes (226 frontend + backend tests) |
| **Documentation** | .ai/ contract matches code reality |
| **Resource usage and stability** | No memory leaks, reasonable resource consumption |

**Differentiate** mandatory product capabilities from optional future integrations.

**Every acceptance criterion must specify**:
- What is expected
- Where it is implemented
- How it is tested
- What evidence proves it
- Current status

## 8. VERSION & SYNCHRONIZATION

- **Product version**: 9.0.0 (pyproject.toml, frontend/package.json, API /api/version)
- **Contract version**: 1.0.0-alpha (packages/ownex-contracts)
- **Single source of truth**: `.ai/` directory
- **Document hierarchy**: .ai/OWNEX_PROJECT_CONTRACT.md > AGENT_CHARTER.md > OWNEX_ARCHITECTURE.md > ARCHITECTURE_CONTRACT.md > packages/ownex-contracts/ > CURRENT_STATE.md > ROADMAP.md > TASK_QUEUE.md

**No commits, no pushes, no destructive operations** during contract establishment.

## 9. CHANGE CONTROL

**Strict rules**:
- Do not run destructive Git commands
- Do not reset, checkout, clean, rebase, force-push or revert
- Do not commit or push
- Do not modify credentials, API keys, tokens or secrets
- Do not modify production databases or delete user data
- Do not perform destructive migrations
- Do not remove working modules without dependency analysis
- Do not replace the current stack without compelling evidence
- Do not invent successful integrations or test results
- Do not silently change public API contracts
- Do not create fake mock functionality

**Documentation changes permitted**: Small corrective changes to documentation references.

**If structural code change appears necessary**: Document as finding and proposed action rather than implementing in this phase.

## 10. SAFETY AND CHANGE CONTROL ( reiterated )

Same strict rules as section 9. Documentation changes permitted within this mission. Small corrective changes to documentation references allowed.

If structural code change appears necessary, document it as a finding and proposed action rather than implementing it in this phase.

---

**Final directive**: The goal is not to create more OWNEX. The goal is to define, consolidate and finish the OWNEX that already exists. Build the specification around the complete vision: **One cross-platform desktop-first operating environment. An extensible universe of work sources. One central orchestration system. Maximum safe automation. Minimal human intervention. Real execution. Verifiable income. Investment and capital management. Complete monitoring and system management.**

Preserve the project's history. Reuse its working foundations. Eliminate architectural ambiguity. Establish one authoritative contract and a measurable path to a genuinely functional product.

**Start with Phase A. Continue through all phases that can be safely completed in this session.** Do not stop merely to ask questions when repository evidence can resolve the uncertainty.

If the session limit is reached, leave a precise progress report and the exact next actions for a new OpenCode session.

**No commits. No pushes. No destructive operations. No broad implementation. Documentation and specification consolidation only.**