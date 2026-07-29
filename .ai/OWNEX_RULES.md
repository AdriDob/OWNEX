# OWNEX Development Rules

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
- Mix OWNEX with Hermes Desktop responsibilities

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
--ownex-bg-primary: #050508;
--ownex-blue-core: #3B82F6;
--ownex-gold-accent: #F59E0B;
--ownex-green-accent: #10B981;
--ownex-glow: 0 0 20px rgba(59, 130, 246, 0.3);
--ownex-border: 1px solid rgba(59, 130, 246, 0.2);
```

Define tokens in `frontend/src/style.css` or Tailwind config before creating components.

## Vision System Rule

Vision capabilities belong to the OpenCode environment.
They must not modify OWNEX codebase or architecture.
Use CapabilityRegistry (`vision:analyze`) for integration.
