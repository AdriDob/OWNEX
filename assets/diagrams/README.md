# OWNEX Architecture Diagrams

Mermaid source files for the OWNEX system architecture. Rendered versions are
included in the README and referenced documentation.

## Diagram Index

| File | Description |
|------|-------------|
| `system-overview.mmd` | Complete system architecture — human, core, intelligence, agent departments, execution and learning layers |
| `layer-breakdown.mmd` | Detailed layer responsibilities across the stack |
| `data-flow.mmd` | Data flow through the observe → decide → execute → learn → evolve loop |
| `event-bus.mmd` | Event Bus topology and event-driven communication |
| `agent-departments.mmd` | Agent department structure and capabilities |

## Rendering

Mermaid diagrams render natively on GitHub in `.md` files. To render locally:

```bash
# CLI rendering (requires Node.js)
npx @mermaid-js/mermaid-cli -i system-overview.mmd -o system-overview.png
```

## Style

All diagrams use the OWNEX dark theme: background `#111113`, text `#F6F8FB`,
accent `#00D4AA` (teal), secondary `#5E6AD2` (indigo), warning `#FF6B35`
(orange). Diagrams are plain text — edit the `.mmd` source, never generated PNGs.
