# ORION Development Rules

## Stability First

Never prioritize appearance over stability.

Before changes:
- Understand current implementation
- Identify impacted files
- Estimate risk

After changes (always run):
```bash
npm run build       # Frontend
pytest              # Backend
ruff check .        # Lint
```

If failure occurs:
1. STOP.
2. `git diff --name-only` — verify only expected files changed.
3. Revert accidental modifications.
4. Fix before continuing.

## Architecture

Do NOT:
- Create duplicate systems
- Replace existing capabilities unnecessarily
- Migrate frameworks without evidence
- Modify unrelated modules
- Mix ORION with Hermes Desktop responsibilities

Prefer:
- Incremental changes
- Reusable components
- Existing architecture patterns
- Backward compatibility

## Validation

After every phase:
- `npm run build` must pass
- `pytest --timeout=60 --ignore=tests/test_security.py` must pass
- `ruff check .` must be clean

If any fails → resolve before next phase.

## Design Tokens Rule

All visual modifications must consume centralized CSS variables (design tokens).

Do NOT:
- Hardcode colors, spacing, or typography values
- Use inline styles for brand-related properties
- Scatter color values across components

Do:
```css
--orion-bg-primary: #050508;
--orion-purple-core: #6D28D9;
--orion-gold-accent: #F5A623;
--orion-green-accent: #00FF41;
--orion-glow: 0 0 20px rgba(109, 40, 217, 0.3);
--orion-border: 1px solid rgba(109, 40, 217, 0.2);
```

Define tokens in `frontend/src/style.css` or Tailwind config before creating components.

## Vision System Rule

Vision capabilities belong to the OpenCode environment.
They must not modify ORION codebase or architecture.
Use CapabilityRegistry (`vision:analyze`) for integration.
