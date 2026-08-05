# OWNEX Architecture Diagrams

This directory contains Mermaid source files for all architecture diagrams.
Rendered versions are included in documentation and README.

## Diagram Index

| File | Description | Used In |
|------|-------------|---------|
| `system-overview.mmd` | Complete system architecture | README.md, docs/ARCHITECTURE.md |
| `layer-breakdown.mmd` | Detailed layer responsibilities | docs/ARCHITECTURE.md |
| `data-flow.mmd` | Data flow through cycles | docs/DATA_FLOW.md |
| `event-bus.mmd` | Event Bus topology | docs/EVENT_BUS.md |
| `agent-departments.mmd` | Agent department structure | docs/AGENTS.md |
| `work-cycles.mmd` | Six work cycles pipeline | docs/WORK_CYCLES.md |
| `merlin-architecture.mmd` | MERLIN assistant internals | docs/OWNEX_MERLIN_SYSTEM.md |
| `evolution-engine.mmd` | Self-evolution pipeline | docs/EVOLUTION_ENGINE.md |
| `recovery-engine.mmd` | Auto-recovery flow | docs/RECOVERY_ENGINE.md |
| `mobile-architecture.mmd` | Android + Wear OS integration | docs/MOBILE.md |
| `security-cycle.mmd` | Security cycle pipeline | docs/SECURITY_CYCLE.md |
| `forge-cycle.mmd` | FORGE cycle pipeline | docs/FORGE_CYCLE.md |
| `pulse-cycle.mmd` | PULSE cycle pipeline | docs/PULSE_CYCLE.md |
| `vault-cycle.mmd` | VAULT cycle pipeline | docs/VAULT_CYCLE.md |
| `atlas-cycle.mmd` | ATLAS cycle pipeline | docs/ATLAS_CYCLE.md |
| `odyssey-cycle.mmd` | ODYSSEY cycle pipeline | docs/ODYSSEY_CYCLE.md |
| `deployment.mmd` | Deployment architecture | docs/DEPLOYMENT.md |
| `development.mmd` | Development environment | docs/DEVELOPMENT.md |

## Rendering

```bash
# Install mermaid-cli
npm install -g @mermaid-js/mermaid-cli

# Render all diagrams
for f in *.mmd; do mmdc -i "$f" -o "${f%.mmd}.svg" -b transparent; done

# Or use the generation script
python scripts/brand/generate_diagrams.py
```

## Style Guidelines

All diagrams follow OWNEX brand identity:

- **Background:** Cosmos (#08090A) or transparent
- **Primary nodes:** Surface (#111113) with Accent (#5E6AD2) borders
- **Secondary nodes:** Surface-alt (#1F2023) with subtle borders
- **Text:** Primary (#F6F8FB) on dark, Cosmos (#08090A) on light
- **Accent connections:** #5E6AD2
- **Success paths:** #00E39A
- **Warning paths:** #FFB020
- **Error paths:** #FF5252
- **Font:** Inter for labels, JetBrains Mono for technical text