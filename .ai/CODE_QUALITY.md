# Code Quality — Estándares de Calidad

## Estándares Obligatorios

### Python
- **Versión objetivo**: Python 3.10+
- **Formatter**: Ruff (line-length 120, indent 4)
- **Type hints**: Obligatorios en todas las funciones públicas
- **`from __future__ import annotations`**: En todos los archivos
- **Logging**: `logger = logging.getLogger("catseye.<modulo>")`
- **Sin comentarios innecesarios**: El código debe ser auto-documentado. Comentar solo lo que no es obvio.
- **Nombres descriptivos**: Variables, funciones, clases con nombres que indiquen propósito

### Frontend (Vue 3 + TypeScript)
- **TypeScript estricto**: Tipos para todas las interfaces y props
- **Componentes**: Composition API con `<script setup lang="ts">`
- **Estado**: Pinia stores
- **API**: Módulo `@/lib/api` centralizado

### General
- **Sin archivos no utilizados**: No commitear código muerto
- **Sin imports no utilizados**: Ruff los detecta y debe eliminarlos
- **Tests**: pytest con naming `test_<funcionalidad>`
- **Commits**: Un cambio por commit, mensaje descriptivo

## Configuración de Herramientas

Ver `pyproject.toml` para:
- Ruff: E, F, W, I, N, UP, B, SIM
- MyPy: python_version 3.10, strict mode parcial
- Pytest: testpaths = tests, -v --tb=short

## Lo que NO Está Configurado

- **pre-commit hooks**: No hay configuración
- **coverage mínimo**: No hay umbral obligatorio
- **bandit/safety**: No hay análisis de seguridad automatizado
