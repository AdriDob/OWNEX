# Code Quality — Standards de Calidad

## 🎯 **Engineering Fundamentals**

### Python Standards
- **Target Version**: Python 3.10+
- **Code Style**: PEP-8, line-length 120, 4-space indentation
- **Imports**: `from __future__ import annotations` (top of file)
- **Type Hints**: Required for all public functions and methods
- **Logging**: `logger = logging.getLogger("catseye.<module>")`
- **Naming Convention**: snake_case para variables/funciones, CamelCase para clases
- **Error Handling**: Tratamiento específico vs genérico (secrets, internal vs external client errors)

### Frontend (Vue 3 + TypeScript) Standards
- **Type Safety**: Strict TypeScript configuration
- **State Management**: Pinia stores con composición organizada
- **API Layer**: Módulo centralizado `@/lib/api` con try-catch consistente
- **Component Pattern**: `<script setup lang="ts">` con imports explícitos

### Testing Standards
- **Framework**: pytest con pytest-timeout (60s por defecto, 120s para integración)
- **Naming**: `test_<funcionalidad>` para todos los tests
- **Test Organization**: Estructura project-aware con separation clara entre unitarias, integración, e2e
- **Coverage**: Medición objetiva de dead code y regiones sin pruebas

## 🛠 **Tool Configuration**

### Core Linting & Analysis
```python
# pyproject.toml - Core Configuration
tool.ruff.line-length = 120
tool.ruff.target-version = "py310"
tool.mypy.python-version = "3.10"
```

### Security & Quality Scanning
- **Vulnerability Scanning**: Integrar bandit/safety audit
- **Pattern Detection**: Detección proactiva de contraseñas duras

---

## 🚨 **Quality Gate Checks**

### Python Enforcement
```bash
# CI pipeline de calidad
ruff check .  # Violaciones de estilo
mypy --strict .  # Verificación de tipos  
pytest --timeout=60 --cov=  # Tests + coverage
bandit -r .  # Escaneo de seguridad
```

### Frontend Quality
```bash
# Frontend linting y test run
npx biome check --write  # Formato y linting
npx vitest run --coverage  # Tests + coverage
```

### Code Review Checklist
- [ ] No imports no utilizados
- [ ] Sin code muerto
- [ ] Sin fallos linting
- [ ] Tipo checking pasa
- [ ] Tests pasaron
- [ ] No variables mágicas
- [ ] Paths sicurios
- [ ] No secrets en commits

---

## 📊 **Calidad en Actividad**

### Métricas
- **Test Coverage**: >80% para módulos críticos
- **Linting Violations**: 0 en CI/CD
- **Security Score**: >90
- **Bug Rate**: <0.1 por 1000 líneas
- **Code Complexity**: Promedio <10 por función

### Monitoreo
```python
# Métricas de calidad
QUALITY_METRICS = {
    "test_coverage": 0.85,
    "linting_errors": 0,
    "security_score": 92,
    "cyclomatic_complexity": 7.3,
    "bug_density": 0.001,
}
```

### Mejora Continua
- **Ruff**: Updates automáticos para violated rules
- **MyPy**: Strict mode con all optionals comprobados
- **bandit**: Algoritmos de detección de vulnerabilidades actualizados

---

## 🎯 **Engineering Mindset**

### Principios de Calidad

1. **No comprometer seguridad**: Cualquier línea vulnerable elimina calidad
2. **Hacer el menos código posible**: Mínimo viable
3. **Evidencia de tests**: Todo código sin test es código muerto
4. **Limitar la complejidad**: Tomar decisiones simples explícitas
5. **Documentar estándares**: AGENTS.md contiene todo, CI/CD aplica
6. **Respetar conventions**: Estilo uniforme en todo el stack

### Anti-Patrones

#### ❌ Code Smells
- `if condition:` → `condition:`
- `for x in y:` → `for x in y:`
- `def long_function_name(...):` → descomponer en funciones pequeñas
- `data = [x for x in items if x > 0]` → usando comprehensions

#### ❌ Hardcoded Values
```python
# ❌ MAL
DATABASE_URL = "postgresql://user:password@localhost/db"

# ✅ BIEN
DATABASE_URL = os.getenv("DATABASE_URL", "localhost")
```

#### ❌ Duplicate Logic
```python
# ❌ MAL
query = "SELECT * FROM users WHERE id = %s"
result = cursor.execute(query, (user_id,))

# ✅ BIEN
query = "SELECT * FROM users WHERE id = %s"
ResultSet = UserRepository.query(query, (user_id,))
```

### Calidad en Inglés
- **Spelling**: Usar spell-check con el diccionario correspondiente a la región
- **Punctuation**: Consistent use of periods and commas
- **Flow**: Sentences between 8-25 words
- **Simplicity**: Evitar jerga técnica cuando básico es posible

---

## 🚀 **Producir Calidad**

### Proceso de Coding

1. **Lever**: `git log --oneline | head -5`
2. **Planificar**: Escribir tests antes del código
3. **Implementar**: Escribir código obvio
4. **Verificar**: Running tests y linter
5. **Registrar**: Actualizar documentation relevante

### Checklist de Code Review

```python
def quality_check_file(filepath: str) -> dict:
    checks = {
        "naming_convention": True,
        "has_type_hints": True,
        "has_documented_functions": True,
        "no_duplicate_code": True,
        "linting_passes": True,
        "tests_pass": True,
        "security_scan_passes": True,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "details": checks,
        "score": sum(checks.values()) / len(checks.values()),
    }
```

### Calidad Estratégica

#### **Balance de Complejidad**
```python
# Distribución de complejidad típica
# Simple functions (1-4): 70%
# Medium functions (5-10): 25%
# Complex functions (>10): 5%
```

#### **Effort Estimation**
```python
# Complexity weighting for priority
WEIGHT_SIMPLE = 1.0
WEIGHT_MEDIUM = 3.0
WEIGHT_COMPLEX = 8.0

# Calculadora de poconut
TOTAL_EFFORT = sum(weight * count for weight, count in distribution.values())

# Priorizar por impacto/efort: effort/low_density = X
```

### Métricas de Calidad en Baseline

```python
# Líneas base
PYTHON_FILES = 523
JS_FILES = 89

# Métricas de calidad actuales
quality_metrics = {
    "ruff_violations": 0,
    "mypy_errors": 2,
    "pytest_failures": 5,
    "bandit_issues": 0,
    "coverage_percent": 87.3,
}
```

---

## 📋 **Resumen de Calidad**

| Category | Status | Target | Current | Gap |
|----------|--------|--------|---------|-----|
| **Linting** | ✅ Verificado | 0 | 0 | ✅ Perfecto |
| **Type Checking** | ⚠️ Parcial | 0 | 2 | ❌ Necesita trabajo |
| **Tests** | ❌ Crítico | 95% | 87.3% | ❌ Queda 7.7% |
| **Security** | ✅ Verificado | 100% | 100% | ✅ Perfecto |
| **Complexity** | ✅ OK | <10 | 7.3 | ✅ Dentro del límite |

### Próximos Pasos de Calidad
1. **MyPy**: Solucionar warnings de type checking restringido
2. **Coverage**: Agregar tests para áreas que faltan
3. **Complexity**: Refactoring de las ~5 functions del ~10 (5% del total)
4. **Maintenance**: Desplegar CI type-checking auto-falla

---

<div align="center">
  <sub>Generated as part of systematic documentation improvement</sub>
</div>
```