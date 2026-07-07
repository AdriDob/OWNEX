# Testing Policy — Política de Testing

## Comandos

```bash
# Ejecutar todos los tests (excepto test_security.py que tiene fallo preexistente)
.venv/bin/python -m pytest --timeout=60 --ignore=tests/test_security.py

# Tests específicos
.venv/bin/python -m pytest tests/test_desktop_release.py -k "license" -v

# Con cobertura
.venv/bin/python -m pytest --cov=cores --cov=api --cov-report=term

# Lint
.venv/bin/python -m ruff check .
```

## Cobertura Actual

- **Tests**: 355 tests, 2 xfailed
- **Fallo conocido**: `test_login_rate_limit` en `test_security.py` — fallo preexistente por timing
- **Framework**: pytest con pytest-timeout, pytest-cov

## Requisitos Mínimos

1. **Código nuevo DEBE tener tests**: Toda función/clase nueva debe incluir tests.
2. **No romper tests existentes**: Cualquier cambio debe mantener la suite verde.
3. **Tests de integración para cambios en API**: Los endpoints modificados deben tener tests que verifiquen:
   - Respuesta exitosa (200)
   - Respuesta de error esperada (400, 401, 403, 404)
   - Casos límite
4. **Tests de seguridad para cambios sensibles**: Auth, tokens, licencias, cifrado.

## Estructura de Tests

- `tests/test_*.py` — Tests organizados por módulo
- `tests/conftest.py` — Fixtures compartidos
- Los tests usan `fastapi.testclient.TestClient` para tests de API
- Los tests de units evitan dependencias externas (mock cuando sea necesario)

## Lo que NO se Testea Actualmente

- CSRF middleware (nuevo, sin tests específicos)
- Scheduler adaptativo (nuevo, sin tests específicos)
- Rate limit middleware mejorado (sin tests específicos)
- Frontend (sin tests automatizados)
