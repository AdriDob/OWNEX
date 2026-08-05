# OWNEX Architecture Diagrams

Mermaid source files for the OWNEX system architecture. Each diagram ships as
`.mmd` source plus a rendered `1920px` transparent PNG (TESLA palette).

## Diagram Index

| File | Description |
|------|-------------|
| `system-overview.mmd` / `.png` | Complete system architecture — human, core, intelligence, agent departments, execution and learning layers |
| `layer-breakdown.mmd` / `.png` | Detailed layer responsibilities across the stack |
| `data-flow.mmd` / `.png` | Data flow through the observe → decide → execute → learn → evolve loop |
| `event-bus.mmd` / `.png` | Event Bus topology and event-driven communication |
| `agent-departments.mmd` / `.png` | Agent department structure and capabilities |

## Rendering

Mermaid diagrams render natively on GitHub inside `.md` fenced blocks. To
re-render the PNGs locally (requires Node.js + a Chrome for Puppeteer):

```bash
mmdc -p scripts/brand/puppeteer-config.json \
     -i assets/diagrams/system-overview.mmd \
     -o assets/diagrams/system-overview.png -b transparent -w 1920
```

After editing a `.mmd` source, re-render its PNG before committing.

## Style

TESLA palette (mirror of `frontend/src/design/tokens.css`): black background
`#000000`, surfaces `#0a0a0a`/`#141414`, borders `#1f1f1f`/`#2e2e2e`, text
`#f5f5f5`, desaturated status colors (`#16a34a` success, `#d97706` warning) and
Tesla red `#e82127` as the only saturated accent. No glows, no gradients.
Diagrams are plain text — edit the `.mmd` source, never generated PNGs.
