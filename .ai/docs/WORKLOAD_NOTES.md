# Workload Notes: Rastro Core + ORION Ecosystem (Sprint 2.1)

## Progressmente registrada por fases

### FASE 1: Core No-Code & Automation
✓ Completed:
  - Framework ORION listo con Work Cycles (MISIÓN, PULSE, etc.)
  - Componentes frontend básicos (Dashboard, Programs, Vault, Atlas, Connections)

✗ FASE 2: Frontend Application
  ⚡ Continuando: Pulse.vue + Connections Vue completo con refinamientos

✖ FASE 3: Opportunity Engine
  ⚡ Continuando: Registration de adaptadores + Integration con vault de credenciales

### Tareas activas (pila)

1. ✅ Adaptador Forge (4 platforms: Superteam, Opire, Algora, OpireMicrotask)
   - Integrado con vault/credentials
   - Registrado en app registry para FORGE cycle

2. ⚡ Adaptador Pulse (7 platforms: Outlier, DataAnnotation, Mindrift, Remotasks, FreelancerMicrotask, LinkedInEasyApply, OpyreMicrotask)
   - **PRIORIDAD ALTA** — Refinado con credenciales completas

3. ⚡ Adaptadores Vault & Atlas (12 platforms total)
   - Por integrar con vault/credentials

### Estado de la pila de trabajo (última actualización)

#### ✅ ADAPTADORES PULSE actualizados con credentials
File: /home/adrie/projects/Rastro/core/opportunity/adapters/pulse.py
- 7 adaptadores Pulse usando load_credentials() de claves vault
- Cada adapter ahora fusiona configuración con credenciales del vault automáticamente
- Cada adaptador se inicializa con carga automática de API keys/cookie/credentials

#### ✅ ADAPTADORES FORGE actualizados con credentials
File: /home/adrie/projects/Rastro/core/opportunity/adapters/forge.py
- 4 adaptadores Forge integrados con load_credentials()
- Cada adaptador usa get_api_key() / get_auth_headers() para auth

#### ✅ Credential helpers creado
File: /home/adrie/projects/Rastro/core/credentials/adapter_helpers.py
- load_credentials(), get_api_key(), get_oauth_credentials(), get_auth_headers()
- Funciona con todos los adaptadores a través del pattern token/api_key/cookie

#### ✅ Vault clima lista
File: /home/adrie/.config/ownex/opportunity.env
- 30+ credenciales de plataformas + variables de entorno ORION (FCC_PROXY, OPENAI_API_KEY, etc.)

#### ✅ App Registry se auto-depende
- Forge, Pulse, Vault, Atlas ahora aportan todos los jobs al scheduler (se registran automáticamente)

### Próximas tareas

1. **Adaptadores restantes** (Vault + Atlas) - Integrar credenciales en los 10 adaptadores restantes
2. **Database models** - Crear tablas SQLAlchemy para cada apps/forge, .pulse, .vault, .atlas
3. **Routers API** - Implementar routers REST para cada app, conectar a frontend
4. **Jobs de planificación** - Implementar sync_cycle_scores y discovery jobs por ciclo
5. **Tests de unitarios** - Agregar coverage test para todos los adaptadores
6. **E2E/uHealth** - Verificar secuencias completas de preparación, sync, endpoints API

### Iniciador del pipeline

```bash
# 1. Ejecutar linting
.venv/bin/python -m ruff check .

# 2. Ejecutar base de tests (core)
.venv/bin/python -m pytest tests/ -x -q --ignore=tests/test_security.py

# 3. Verificar rutas del adaptador (Registrador del agente)
hermes run "Agente de oportunidad --ofertas"

# 4. Iniciar servidor + agente en background
.venv/bin/python run.py &  # frontend + backend + scheduler
```