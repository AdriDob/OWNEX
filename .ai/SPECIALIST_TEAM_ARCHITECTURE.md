# OWNEX Specialist Team Architecture

## Overview

OWNEX is designed as a team of 11 specialized agents, each with clear objectives, limits, tools, and responsibilities. The Commander coordinates all specialists but never executes tasks directly.

## Team Structure

### Leadership Layer

#### 1. Commander (Priority: 1)
- **Role**: Team coordination and orchestration
- **Primary Objective**: Coordinate OWNEX specialists to achieve system objectives
- **Secondary Objectives**: 
  - Optimize team cooperation and performance
  - Handle task failures and retries
  - Monitor system health and status
  - Report system state to users
- **Limits**: 
  - NEVER executes tasks directly
  - Max 50 concurrent delegations
  - Max 120s per coordination cycle
- **Tools**: Task assignment, agent monitoring, workflow orchestration, health dashboard
- **Memory**: 10,000 items (system-wide state)
- **Communication**: All specialists, system alerts, user interface
- **Handoffs**: Delegates to all specialists, never receives handoffs

### Planning Layer

#### 2. Planner (Priority: 2)
- **Role**: Task planning and decomposition
- **Primary Objective**: Create detailed plans for complex objectives
- **Secondary Objectives**: 
  - Estimate required resources
  - Resolve task dependencies
  - Optimize execution order
- **Limits**: Max 5 concurrent plans, 300s per plan
- **Tools**: Task decomposition, resource estimation, dependency resolution
- **Handoffs**: 
  - Receives from: Commander
  - Hands off to: Research, Coder, Browser, Security

### Technical Specialists

#### 3. Research (Priority: 3)
- **Role**: Intelligence gathering and analysis
- **Primary Objective**: Gather and analyze intelligence about targets
- **Secondary Objectives**: 
  - Discover vulnerabilities and attack surface
  - Analyze competitive landscape
  - Map technology stacks
- **Limits**: Max 10 concurrent research tasks, 600s per operation
- **Tools**: Shodan, Censys, Wayback, subdomain enumeration, endpoint discovery
- **Handoffs**: 
  - Receives from: Commander, Planner
  - Hands off to: Security, Coder, Learning

#### 4. Coder (Priority: 3)
- **Role**: Code generation and implementation
- **Primary Objective**: Generate, refactor, and implement code
- **Secondary Objectives**: 
  - Create pull requests
  - Apply bug fixes
  - Optimize code performance
- **Limits**: Max 5 concurrent coding tasks, 900s per operation
- **Tools**: Code generation (Devin, OpenCode), refactoring, PR creation, testing
- **Handoffs**: 
  - Receives from: Commander, Planner, Research
  - Hands off to: Reviewer, Documentation

#### 5. Reviewer (Priority: 4)
- **Role**: Code review and quality assurance
- **Primary Objective**: Review code and changes for quality
- **Secondary Objectives**: 
  - Grant or deny approvals
  - Ensure coding standards compliance
  - Security review of changes
- **Limits**: Max 8 concurrent reviews, 300s per review
- **Tools**: Code analysis, quality check, security review, approval system
- **Handoffs**: 
  - Receives from: Coder, Security
  - Hands off to: Commander (approval), Documentation

#### 6. Browser (Priority: 3)
- **Role**: Web automation and interaction
- **Primary Objective**: Automate web interactions and scraping
- **Secondary Objectives**: 
  - Form submission and validation
  - Element interaction and clicking
  - Navigation and page handling
- **Limits**: Max 5 concurrent browser sessions, 600s per operation
- **Tools**: Playwright automation, form submission, element interaction, web scraping
- **Handoffs**: 
  - Receives from: Commander, Planner
  - Hands off to: Research, Documentation

#### 7. Security (Priority: 2)
- **Role**: Vulnerability detection and security testing
- **Primary Objective**: Detect vulnerabilities and perform security testing
- **Secondary Objectives**: 
  - Collect evidence for findings
  - Confirm exploit viability
  - Validate security hypotheses
- **Limits**: Max 3 concurrent security scans, 1200s per operation
- **Tools**: Nuclei scanner, Nmap scanner, exploit testing, evidence collection
- **Handoffs**: 
  - Receives from: Commander, Research
  - Hands off to: Reviewer, Documentation, Learning

### Knowledge & Documentation Layer

#### 8. Documentation (Priority: 5)
- **Role**: Documentation generation and maintenance
- **Primary Objective**: Generate and maintain system documentation
- **Secondary Objectives**: 
  - Create user guides and tutorials
  - Update API documentation
  - Document procedures and workflows
- **Limits**: Max 10 concurrent documentation tasks, 300s per operation
- **Tools**: Guide generation, API documentation, procedure documentation
- **Handoffs**: 
  - Receives from: All specialists
  - Hands off to: Commander (completion)

#### 9. Learning (Priority: 4)
- **Role**: Knowledge capture and pattern learning
- **Primary Objective**: Capture knowledge and learn from system operations
- **Secondary Objectives**: 
  - Analyze patterns in data
  - Process feedback from operations
  - Improve decision-making through learning
- **Limits**: Max 15 concurrent learning tasks, 240s per operation
- **Tools**: Knowledge storage, pattern recognition, error analysis, feedback processing
- **Handoffs**: 
  - Receives from: All specialists
  - Hands off to: Evolution (improvement suggestions)

### Business & Strategy Layer

#### 10. Finance (Priority: 4)
- **Role**: Financial tracking and revenue optimization
- **Primary Objective**: Track financial performance and optimize revenue
- **Secondary Objectives**: 
  - Calculate operational costs
  - Manage payouts and payments
  - Track profitability by project
- **Limits**: Max 5 concurrent financial tasks, 180s per operation
- **Tools**: Revenue calculation, cost tracking, payout management, profitability analysis
- **Handoffs**: 
  - Receives from: Commander, Security (payouts)
  - Hands off to: Evolution (optimization suggestions)

#### 11. Evolution (Priority: 5)
- **Role**: System improvement and self-evolution
- **Primary Objective**: Improve system through continuous analysis and optimization
- **Secondary Objectives**: 
  - Audit system infrastructure
  - Suggest improvements based on learning
  - Watch technology trends for upgrades
- **Limits**: Max 3 concurrent evolution tasks, 600s per operation
- **Tools**: System audit, improvement suggestion, self-testing, technology watching
- **Handoffs**: 
  - Receives from: Finance, Learning
  - Hands off to: Commander (implementation approval)

## Handoff Matrix

| From → To       | Commander | Planner | Research | Coder | Reviewer | Browser | Security | Docs | Learning | Finance | Evolution |
|----------------|-----------|---------|----------|-------|----------|---------|---------|------|----------|---------|-----------|
| **Commander**  | -         | ✓       | ✓        | ✓     | -        | ✓       | ✓       | -    | -        | -       | -         |
| **Planner**    | -         | -       | ✓        | ✓     | -        | ✓       | ✓       | -    | -        | -       | -         |
| **Research**   | -         | -       | -        | ✓     | -        | -       | ✓       | -    | ✓        | -       | -         |
| **Coder**      | -         | -       | -        | -     | ✓        | -       | -       | ✓    | -        | -       | -         |
| **Reviewer**   | ✓         | -       | -        | -     | -        | -       | -       | ✓    | -        | -       | -         |
| **Browser**    | -         | -       | ✓        | -     | -        | -       | -       | ✓    | -        | -       | -         |
| **Security**   | -         | -       | -        | -     | ✓        | -       | -       | ✓    | ✓        | ✓       | -         |
| **Docs**       | ✓         | -       | -        | -     | -        | -       | -       | -    | -        | -       | -         |
| **Learning**   | -         | -       | -        | -     | -        | -       | -       | -    | -        | -       | ✓         |
| **Finance**     | -         | -       | -        | -     | -        | -       | -       | -    | -        | -       | ✓         |
| **Evolution**   | ✓         | -       | -        | -     | -        | -       | -       | -    | -        | -       | -         |

## Handoff Conditions

### Research → Security
- **Condition**: `vulnerability_found`
- **Trigger**: Research discovers potential vulnerability
- **Payload**: Target, vulnerability type, preliminary evidence

### Research → Coder
- **Condition**: `requires_coding`
- **Trigger**: Research identifies need for custom tool/script
- **Payload**: Requirements, specifications

### Research → Learning
- **Condition**: `pattern_discovered`
- **Trigger**: Research finds recurring pattern
- **Payload**: Pattern description, context

### Coder → Reviewer
- **Condition**: `code_review_needed`
- **Trigger**: Code generated/modified
- **Payload**: Code changes, affected files

### Coder → Documentation
- **Condition**: `documentation_needed`
- **Trigger**: New feature or API created
- **Payload**: Feature details, API specification

### Security → Reviewer
- **Condition**: `evidence_collected`
- **Trigger**: Security findings ready for review
- **Payload**: Evidence, vulnerability details

### Security → Documentation
- **Condition**: `report_needed`
- **Trigger**: Security finding confirmed
- **Payload**: Finding details, report template

### Security → Learning
- **Condition**: `pattern_learned`
- **Trigger**: Security discovers attack pattern
- **Payload**: Pattern description, mitigations

### Browser → Research
- **Condition**: `data_collected`
- **Trigger**: Browser scraping completes
- **Payload**: Scraped data, metadata

### Browser → Documentation
- **Condition**: `guide_needed`
- **Trigger**: Browser identifies UI workflow
- **Payload**: Workflow steps, screenshots

### Reviewer → Commander
- **Condition**: `approval_granted` or `approval_denied`
- **Trigger**: Review decision made
- **Payload**: Decision, reasons, recommendations

### Documentation → Commander
- **Condition**: `documentation_completed`
- **Trigger**: Documentation generated
- **Payload**: Documentation location, type

### Learning → Evolution
- **Condition**: `improvement_opportunity`
- **Trigger**: Learning identifies improvement potential
- **Payload**: Opportunity description, impact analysis

### Finance → Evolution
- **Condition**: `optimization_needed`
- **Trigger**: Finance identifies cost/revenue optimization
- **Payload**: Optimization suggestion, expected impact

### Evolution → Commander
- **Condition**: `improvement_ready`
- **Trigger**: Evolution prepares improvement plan
- **Payload**: Improvement plan, implementation steps

## Cooperation Optimization

The Commander continuously optimizes cooperation between specialists by:

1. **Analyzing Handoff Patterns**
   - High handoff frequency → Consider direct integration
   - Failed handoffs → Adjust conditions or targets
   - Slow handoffs → Optimize communication channels

2. **Monitoring Performance Metrics**
   - Success rate < 80% → Review task vs specialist fit
   - High execution time → Suggest task decomposition
   - Resource bottlenecks → Adjust concurrency limits

3. **Dynamic Priority Adjustment**
   - System load → Adjust specialist priorities
   - Urgent tasks → Temporarily raise priority
   - Resource constraints → Throttle non-critical tasks

4. **Learning from Failures**
   - Pattern in failures → Adjust specialist capabilities
   - Tool limitations → Request new tools or permissions
   - Dependencies → Replan handoff conditions

## Example Workflow

### Bug Bounty Discovery Workflow

1. **Commander** receives objective: "Find vulnerabilities in target X"
2. **Commander** delegates to **Planner** for task planning
3. **Planner** creates plan:
   - Research: Discover attack surface
   - Security: Scan for vulnerabilities
   - Security: Test exploit viability
   - Reviewer: Validate findings
   - Documentation: Generate report
4. **Planner** hands off to **Research**
5. **Research** discovers endpoints → hands off to **Security**
6. **Security** finds vulnerability → hands off to **Security** (exploit test)
7. **Security** confirms exploit → hands off to **Reviewer**
8. **Reviewer** validates → hands off to **Documentation**
9. **Documentation** generates report → hands off to **Commander**
10. **Commander** marks workflow complete

## Communication Protocols

### Event Format
All specialists communicate via typed events with:
- `event_type`: Specific to the operation
- `source`: Sending specialist
- `target`: Receiving specialist (if applicable)
- `payload`: Operation-specific data
- `correlation_id`: Links related events
- `priority`: 1 (highest) → 10 (lowest)

### Response Timeout
- Commander: 30s (urgent coordination)
- Security: 60s (critical operations)
- Research: 90s (intensive operations)
- Other specialists: 60s (standard)

### Error Handling
- Failed tasks → Automatic retry (max 2 attempts)
- Specialist unavailable → Handoff to alternative
- Critical failure → Commander escalation
- System error → All specialists notified

## Resource Allocation

### Concurrency Limits
- Commander: 50 (coordination)
- Research: 10 (parallel discovery)
- Documentation: 10 (multiple docs)
- Learning: 15 (continuous learning)
- Others: 3-8 (specialized work)

### Memory Allocation
- Commander: 10,000 items (system state)
- Security: 5,000 items (evidence)
- Research: 3,000 items (intelligence)
- Learning: 8,000 items (patterns)
- Others: 1,000 items (specialized)

### Tool Permissions
- Commander: Coordination tools only (no execution)
- Security: Security testing tools only
- Coder: Code generation tools only
- Browser: Web automation tools only
- Others: Specialist-specific tools

## Performance Monitoring

Each specialist tracks:
- Tasks completed/failed
- Average execution time
- Handoffs completed
- Resource usage
- Success rate

Commander aggregates:
- Overall system health
- Specialist performance comparison
- Bottleneck identification
- Cooperation efficiency metrics

## Continuous Improvement

The Evolution specialist monitors:
- System performance trends
- Technology changes
- Learning pattern opportunities
- Financial optimization potential

Improvements are suggested to Commander for:
- Specialist capability expansion
- Handoff condition optimization
- Tool permission adjustments
- Resource limit rebalancing