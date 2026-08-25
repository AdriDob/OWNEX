# OWNEX Documentation

Comprehensive technical documentation for the OWNEX Autonomous Operating System.

## Quick Navigation

- [Getting Started](#getting-started)
- [Architecture](#architecture)
- [Development](#development)
- [Operations](#operations)
- [Security](#security)
- [Integrations](#integrations)
- [Reference](#reference)

---

## Getting Started

### Essential Guides
- [README](README.md) — Project overview and quick start
- [API Setup Guide](API_SETUP_GUIDE.md) — Initial API configuration
- [Known Limitations](KNOWN_LIMITATIONS.md) — Current system constraints

### Installation & Setup
- [Integration Guide](INTEGRATION_GUIDE.md) — Platform integration setup
- [Real Data Connection Runbook](REAL_DATA_CONNECTION_RUNBOOK.md) — Production data setup

---

## Architecture

### Core Architecture
- [Architecture Review](ARCHITECTURE_REVIEW.md) — System architecture analysis
- [EventBus Documentation](EVENTBUS.md) — Internal event system
- [OWNEX Design System](OWNEX_DESIGN_SYSTEM.md) — UI/UX design principles

### System Components
- [ORION Operation Manual](ORION_OPERATION_MANUAL.md) — ORION system guide
- [OWNEX MERLIN System](OWNEX_MERLIN_SYSTEM.md) — AI assistant system
- [Attack Pipeline](ATTACK_PIPELINE.md) — Security attack workflows

### Architecture Diagrams
See [Architecture Diagrams](../assets/diagrams/) for visual system architecture:
- [Architecture Overview](../assets/diagrams/architecture-overview.md)
- [Security Cycle Pipeline](../assets/diagrams/security-cycle-pipeline.md)
- [Execution Layer](../assets/diagrams/execution-layer.md)
- [Intelligence System](../assets/diagrams/intelligence-system.md)
- [Work Cycles](../assets/diagrams/work-cycles.md)
- [Deployment Architecture](../assets/diagrams/deployment-architecture.md)

---

## Development

### Development Guides
- [Development](development/) — Development workflows and practices
- [Plugin SDK](PLUGIN_SDK.md) — Extension development
- [Project](project/) — Project-specific documentation
- [Apuntes de Programación](APUNTES_PROGRAMACION.md) — Errores con causa raíz, gotchas por stack, patrones y comandos aprendidos desarrollando OWNEX

### API Reference
- [API Reference](API_REFERENCE.md) — Complete REST API documentation
- [Direct Software Work Platforms](DIRECT_SOFTWARE_WORK_PLATFORMS.md) — Platform adapters

### Tools & Utilities
- [Hermes Guide](HERMES_GUIDE.md) — Hermes CLI usage
- [Hermes/OpenCode Setup](HERMES_OPENCODE_ZEN_SETUP.md) — ORION tooling setup

---

## Operations

### Operational Guides
- [Operations](operations/) — Operational procedures
- [Backup and Recovery](BACKUP_AND_RECOVERY.md) — Data backup procedures
- [Production Audit](PRODUCTION_AUDIT.md) — Production readiness checklist

### Monitoring & Maintenance
- [Security Baseline](SECURITY_BASELINE.md) — Security standards
- [Audit](audit/) — Audit procedures and results
  - [Internal System Audit](audit/INTERNAL_AUDIT.md) — Classification of every system (EXISTENTE/IMPLEMENTADO/PARCIAL/EXPERIMENTAL/DESCARTADO), with evidence
  - [GitHub Presentation Report](audit/GITHUB_PRESENTATION_REPORT.md) — Presentation deliverables, verification, honest gaps, regenerate instructions

---

## Security

### Security Documentation
- [Security Model](SECURITY_MODEL.md) — Comprehensive security architecture
- [Security Policy](../SECURITY.md) — Vulnerability reporting

### Security Best Practices
- See [Security Model](SECURITY_MODEL.md) for authentication, authorization, and data protection guidelines.

---

## Integrations

### Platform Integration
- [Integration Guide](INTEGRATION_GUIDE.md) — General integration procedures
- [Providers](providers/) — Third-party service providers

### Data Connections
- [Real Data Connection Runbook](REAL_DATA_CONNECTION_RUNBOOK.md) — Production data setup
- [opportunity.env.example](opportunity.env.example) — Environment configuration

### Knowledge Bridge (Obsidian vault)
- [Knowledge Architecture](knowledge/KNOWLEDGE_ARCHITECTURE.md) — Bridge architecture and components
- [Obsidian Integration](knowledge/OBSIDIAN_INTEGRATION.md) — Connect your vault to OWNEX
- [Obsidian Migration](knowledge/OBSIDIAN_MIGRATION.md) — Moving knowledge into the vault
- [Knowledge Backup & Recovery](knowledge/BACKUP_AND_RECOVERY.md) — Snapshots and restore
- [Knowledge Security](knowledge/SECURITY.md) — Authorization and secret scanning

---

## Reference

### System Reference
- [API Reference](API_REFERENCE.md) — Complete API endpoint documentation
- [EventBus Documentation](EVENTBUS.md) — Event system reference
- [Plugin SDK](PLUGIN_SDK.md) — Extension API reference

### Planning & Strategy
- [Personal Intelligence Roadmap](PERSONAL_INTELLIGENCE_ROADMAP.md) — AI development roadmap
- [Architecture](architecture/) — Detailed architecture documents

### Archives
- [Archived](archived/) — Historical documentation
- [Audits](audits/) — Past audit results

---

## Documentation Structure

```
docs/
├── README.md                    # This file
├── API_REFERENCE.md             # Complete API documentation
├── API_SETUP_GUIDE.md           # API configuration
├── ARCHITECTURE_REVIEW.md       # Architecture analysis
├── ATTACK_PIPELINE.md           # Security workflows
├── BACKUP_AND_RECOVERY.md       # Backup procedures
├── DIRECT_SOFTWARE_WORK_PLATFORMS.md  # Platform adapters
├── EVENTBUS.md                  # Event system
├── HERMES_GUIDE.md              # Hermes CLI
├── INTEGRATION_GUIDE.md         # Integration setup
├── KNOWN_LIMITATIONS.md         # System constraints
├── ORION_OPERATION_MANUAL.md    # ORION system
├── OWNEX_DESIGN_SYSTEM.md       # UI/UX design
├── OWNEX_MERLIN_SYSTEM.md       # AI assistant
├── PLUGIN_SDK.md                # Extension development
├── PRODUCTION_AUDIT.md          # Production checklist
├── REAL_DATA_CONNECTION_RUNBOOK.md  # Data setup
├── SECURITY_BASELINE.md         # Security standards
├── SECURITY_MODEL.md            # Security architecture
├── opportunity.env.example      # Environment config
├── architecture/                # Architecture details
├── archived/                    # Historical docs
├── audit/                       # Audit procedures
├── assets/                      # Documentation assets
├── audits/                      # Audit results
├── brand-preview/               # Brand previews
├── development/                 # Development guides
├── images/                      # Documentation images
├── knowledge/                   # Knowledge Bridge (Obsidian vault) docs
├── operations/                  # Operational procedures
├── project/                     # Project-specific docs
└── providers/                   # Third-party providers
```

---

## Contributing to Documentation

When adding new documentation:

1. **Place in appropriate directory** — Use existing structure
2. **Follow naming convention** — UPPERCASE_WITH_UNDERSCORES.md
3. **Update this README** — Add entry to relevant section
4. **Link from parent** — Ensure discoverability
5. **Maintain consistency** — Follow existing format and style

---

## Documentation Standards

- **Markdown format** — All docs in GitHub Flavored Markdown
- **Code blocks** — Specify language for syntax highlighting
- **Diagrams** — Use Mermaid for technical diagrams
- **Version info** — Include applicable OWNEX version
- **Date stamps** — Update modification dates
- **Cross-references** — Link to related documentation

---

## Need Help?

- **General Issues**: [GitHub Issues](https://github.com/AdriDob/OWNEX/issues)
- **Security**: [security@ownex.ai](mailto:security@ownex.ai)
- **Documentation Issues**: Create a documentation issue with the `documentation` label

---

*Documentation for OWNEX v7.0.0*
*Last updated: 2026-08-25*

## Release Audits
- [OWNEX 1.0 Alpha — Release Audit & Plan](release/OWNEX_1.0_ALPHA_AUDIT.md) — diagnóstico release-ready (2026-08-25): causa raíz del fondo rojo, estados por página, branding, artefactos obsoletos (~9GB), plan Prompt 2.