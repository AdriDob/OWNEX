# Contributing to OWNEX

> OWNEX is a private project. This document serves as a reference for the development workflow.

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- pnpm or npm

### Quick Start

```bash
# Clone the repository
git clone <repo-url>
cd Rastro

# Backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Frontend
cd frontend && pnpm install && cd ..

# Start development
python run.py
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design.

### Key Directories

| Directory | Purpose |
|-----------|---------|
| `api/` | FastAPI application + routers |
| `cores/` | Core business logic (200+ modules) |
| `core/` | Legacy core (near-duplicate of `cores/`) |
| `database/` | SQLAlchemy models + SQLite/PostgreSQL |
| `frontend/` | Vue 3 + TypeScript + Tailwind CSS v4 |
| `android/` | Wear OS companion app (Kotlin) |
| `src-tauri/` | Desktop app (Tauri v2 + Rust) |
| `tests/` | 4500+ tests (pytest) |
| `.ai/` | Strategy, decisions, roadmap |

## Development Workflow

### 1. Plan First

Always read `.ai/AGENT_CHARTER.md` and `.ai/PRODUCTION_RULES.md` before making changes.

### 2. Small Changes

Each commit should be a single logical unit. Prefer 3 small commits over 1 large one.

### 3. Verify

```bash
# Lint
python scripts/dev fmt

# Type check
python scripts/dev typecheck-fast

# Tests
python scripts/dev test-fast

# Full check
python scripts/dev check
```

### 4. Commit

Use conventional commits:
- `feat:` — new feature
- `fix:` — bug fix
- `refactor:` — code restructuring
- `test:` — adding tests
- `docs:` — documentation
- `chore:` — maintenance

## Code Standards

### Python
- Ruff for linting + formatting
- mypy strict mode
- Type hints on all public functions
- Docstrings on all public classes/methods

### TypeScript/Vue
- Biome for linting + formatting
- vue-tsc for type checking
- Composition API with `<script setup>`
- Tailwind CSS v4 utility classes

### Design System
- All colors use CSS custom properties (`--ownex-*` tokens)
- No hardcoded hex colors in Vue/TS files
- Tesla-inspired: pure black bg, white primary, minimal accent

## Testing

```bash
# Run specific test
pytest tests/test_my_feature.py -v

# Run fast suite (scoring + opportunity + scheduler)
python scripts/dev test-fast

# Run all tests
python scripts/dev test
```

## Security

- Never commit secrets, API keys, or credentials
- Use `IdentityVault` for credential management
- All external actions require approval in ASSISTED mode
- See [SECURITY.md](SECURITY.md) for details

## Documentation

- Update `.ai/CURRENT_STATE.md` when completing a feature
- Update `ARCHITECTURE.md` for structural changes
- Update `README.md` for user-facing changes
- Keep `.ai/` files as the single source of truth

---

*Last updated: September 2026*
