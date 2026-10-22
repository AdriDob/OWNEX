# AUDITORÍA COMPLETA DE CREDENCIALES — Hallazgos y Plan de Acción

## Resumen Ejecutivo

| Categoría | Total | Estado |
|-----------|-------|--------|
| Credenciales en Settings UI | **41** | ✅ **COMPLETA (FASE 1 hecha)** |
| Credenciales en sync.py (KEY_MAPPING) | 41 | ✅ Completo para sync |
| Credenciales referenciadas por capabilities | 19 | ⚠️ Gap crítico (FASE 2 pendiente) |
| Credenciales en vault.py (API keys) | 31 | ⚠️ Muchas no expuestas (FASE 4 opcional) |
| Credenciales documentadas (KEY_SOURCES) | 17 | ⚠️ Incompleto (FASE 3 pendiente) |
| URLs en vault.py | 26 | ❌ No expuestas (FASE 4 opcional) |

---

## 🔴 GAPS CRÍTICOS (Requieren acción inmediata)

### 1. **25 credenciales en sync.py pero NO en Settings UI**
Estas se sincronizan correctamente de DB → .env → os.environ, pero **el usuario no puede configurarlas desde la UI**.

| UI Key | Env Variable | Sección sugerida |
|--------|--------------|------------------|
| `algora` | ALGORA_API_KEY | Bug Bounty / Forge |
| `cantina` | CANTINA_API_KEY | Bug Bounty |
| `ccxt` | CCXT_API_KEY | Trading / Inversión |
| `code4rena` | CODE4RENA_API_KEY | Bug Bounty / Atlas |
| `codehawks` | CODEHAWKS_API_KEY | Bug Bounty / Atlas |
| `dataannotation` | DATAANNOTATION_API_KEY | Pulse / AI Work |
| `freelancer` | FREELANCER_API_KEY | Forge |
| `freelancer_micro` | FREELANCER_MICRO_API_KEY | Pulse |
| `immunefi` | IMMUNEFI_API_KEY | Bug Bounty |
| `issuehunt` | ISSUEHUNT_API_KEY | Forge |
| `linkedin_client_id` | LINKEDIN_CLIENT_ID | OSINT / Social |
| `linkedin_client_secret` | LINKEDIN_CLIENT_SECRET | OSINT / Social |
| `linkedin_redirect_uri` | LINKEDIN_REDIRECT_URI | OSINT / Social |
| `mindrift` | MINDRIFT_API_KEY | Pulse / AI Work |
| `nim` | NIM_API_KEY | IA |
| `nvidia` | NVIDIA_API_KEY | IA |
| `omniroute` | OMNIROUTE_API_KEY | IA / OAR |
| `opencollective` | OPENCOLLECTIVE_API_KEY | Forge |
| `opire` | OPIRE_API_KEY | Forge |
| `opyre_micro` | OPYRE_MICRO_API_KEY | Pulse |
| `outlier` | OUTLIER_API_KEY | Pulse / AI Work |
| `polymarket` | POLYMARKET_API_KEY | Trading / Inversión |
| `remotasks` | REMOTASKS_API_KEY | Pulse |
| `sherlock` | SHERLOCK_API_KEY | Bug Bounty / Atlas |
| `superteam` | SUPERTEAM_API_KEY | Forge |

### 2. **19 credenciales referenciadas por capabilities pero NO en sync.py**
Estas **no se sincronizan** de DB → .env aunque el usuario las configure en la UI (si las agregamos).

| Env Variable | Capability | Comentario |
|--------------|------------|------------|
| ANTHROPIC_API_KEY | ai_free_cloud | Ya en sync como `anthropic` |
| BUGCROWD_API_KEY | bugbounty_submission | Ya en sync como `bugcrowd` |
| BUILTWITH_API_KEY | osint_deep | Falta en sync |
| CEREBRAS_API_KEY | ai_free_cloud | Falta en sync |
| DEEPINFRA_API_KEY | ai_free_cloud | Falta en sync |
| GITHUB_TOKEN | bounty_target_discovery, dev_bounty_pr | Ya en sync como `github` |
| GROQ_API_KEY | ai_free_cloud, trading_radar | Falta en sync |
| HACKERONE_API_KEY | bugbounty_submission | Ya en sync como `hackerone` |
| HIBP_API_KEY | osint_deep | Falta en sync |
| HTTP_PROXY | bugbounty_scan | Falta en sync |
| HUNTER_API_KEY | osint_deep | Falta en sync |
| NVIDIA_API_KEY | ai_free_cloud | Ya en sync como `nvidia` |
| OLLAMA_CLOUD_API_KEY | ai_free_cloud | Falta en sync |
| OWNEX_APPROVAL_KEY | trading_live | Falta en sync |
| OWNEX_MAX_PER_SOURCE | dev_bounty_pr | Falta en sync |
| SECURITYTRAILS_API_KEY | osint_deep | Ya en sync como `securitytrails` |
| SOLANA_PRIVATE_KEY | trading_live | Falta en sync |
| TOGETHER_API_KEY | ai_free_cloud | Falta en sync |
| TRADING_MODE | trading_live | Falta en sync |

**Nota:** ANTHROPIC, BUGCROWD, GITHUB, HACKERONE, NVIDIA, SECURITYTRAILS ya están en sync con nombres diferentes (lowercase). El problema son las 13 que faltan completamente.

### 3. **gitlab en UI pero NO en sync.py**
Simple: agregar `gitlab -> GITLAB_API_KEY` a KEY_MAPPING.

### 4. **14 credenciales en vault.py SIN documentación ni sync**
Estas existen en el modelo Pydantic pero no están documentadas ni sincronizadas:

| Env Variable | Comentario |
|--------------|------------|
| ALGORA_API_KEY | Sync OK, falta UI |
| CANTINA_API_KEY | Sync OK, falta UI |
| CODE4RENA_API_KEY | Sync OK, falta UI |
| CODEHAWKS_API_KEY | Sync OK, falta UI |
| DATAANNOTATION_API_KEY | Sync OK, falta UI |
| FREELANCER_API_KEY | Sync OK, falta UI |
| FREELANCER_MICRO_API_KEY | Sync OK, falta UI |
| IMMUNEFI_API_KEY | Sync OK, falta UI |
| INTIGRITI_API_KEY | Sync OK, falta UI |
| ISSUEHUNT_API_KEY | Sync OK, falta UI |
| MINDRIFT_API_KEY | Sync OK, falta UI |
| NIM_API_KEY | Sync OK, falta UI |
| OMNIROUTE_API_KEY | Sync OK, falta UI |
| OPENAI_API_KEY | Sync OK, falta UI |
| OPENCOLLECTIVE_API_KEY | Sync OK, falta UI |
| OPIRE_API_KEY | Sync OK, falta UI |
| OPYRE_MICRO_API_KEY | Sync OK, falta UI |
| OUTLIER_API_KEY | Sync OK, falta UI |
| REMOTASKS_API_KEY | Sync OK, falta UI |
| SHERLOCK_API_KEY | Sync OK, falta UI |
| SUPERTEAM_API_KEY | Sync OK, falta UI |
| SYNACK_API_KEY | Sync OK, falta UI |
| YESWEHACK_API_KEY | Sync OK, falta UI |
| ISSUEHAND_API_KEY | Ni en sync ni en caps (¿dead?) |
| FCC_BASE_URL | Config, no credencial |
| OLLAMA_BASE_URL | Config, no credencial |

### 5. **26 URLs en vault.py NO expuestas en ningún lado**
Todas las `*_API_URL` y `FCC_BASE_URL`, `OLLAMA_BASE_URL`. Son configuración, no credenciales, pero podrían necesitarse para endpoints custom.

---

## 🟡 GAPS SECUNDARIOS

### 6. **KEY_SOURCES incompleto** (17 documentadas vs 41 en sync)
Faltan instrucciones para conseguir: ALGORA, CANTINA, CCXT, CODE4RENA, CODEHAWKS, DATAANNOTATION, FREELANCER, IMMUNEFI, INTIGRITI, ISSUEHUNT, LINKEDIN, MINDRIFT, NIM, NVIDIA, OMNIROUTE, OPENCOLLECTIVE, OPIRE, OPYRE_MICRO, OUTLIER, POLYMARKET, REMOTASKS, SHERLOCK, SUPERTEAM, SYNACK, YESWEHACK, etc.

### 7. **Naming inconsistency**
- Capabilities usan: `UPPER_SNAKE_CASE` (ej: `HACKERONE_API_KEY`)
- Sync/UI usan: `lowercase` (ej: `hackerone`)
- Vault usa: `UPPER_SNAKE_CASE` con alias (ej: `HACKERONE_API_KEY` → `hackerone_api_key`)

---

## ✅ PLAN DE ACCIÓN PRIORIZADO

### ✅ FASE 1: Completar Settings UI (Alta prioridad) — **COMPLETADA 2026-10-20**
**Archivo:** `frontend/src/pages/Settings.vue` → `apiSections` — **HECHO**

Se agregaron **6 nuevas secciones con 25 credenciales** (total 41 en UI):

| Sección | Icono | Credenciales agregadas |
|---------|-------|------------------------|
| **Bug Bounty Extended** | Crosshair | cantina, code4rena, codehawks, immunefi, sherlock, synack, yeswehack |
| **IA Extended** | Sparkles | nvidia, nim, omniroute |
| **Forge / Dev Platforms** | Wrench | algora, freelancer, opire, issuehunt, opencollective, superteam |
| **Pulse / AI Work** | Sparkles | outlier, mindrift, dataannotation, remotasks, freelancer_micro, opyre_micro |
| **Trading / Inversión** | DollarSign | ccxt, polymarket |
| **Social / OSINT** | Globe | linkedin_client_id, linkedin_client_secret, linkedin_redirect_uri |

**Verificación:**
- ✅ Frontend build exitoso (`npm run build` — 14.47s)
- ✅ `make test-fast` — 105 passed
- ✅ `make work` — Startup protocol complete
- ✅ Settings UI → pestaña "API Keys" muestra todas las secciones
- ✅ `GET /api/credentials/missing` reporta 41 credenciales agrupadas por sección correcta

---

### FASE 2: Completar KEY_MAPPING en sync.py

### FASE 2: Completar KEY_MAPPING en sync.py
**Archivo:** `cores/credentials/sync.py`

Agregar las 13 claves faltantes de capabilities:
```python
KEY_MAPPING = {
    # ... existentes ...
    
    # Capabilities envs faltantes
    "cerebras": "CEREBRAS_API_KEY",
    "deepinfra": "DEEPINFRA_API_KEY",
    "groq": "GROQ_API_KEY",
    "ollama_cloud": "OLLAMA_CLOUD_API_KEY",
    "own_ex_approval": "OWNEX_APPROVAL_KEY",
    "own_ex_max_per_source": "OWNEX_MAX_PER_SOURCE",
    "solana_private_key": "SOLANA_PRIVATE_KEY",
    "trading_mode": "TRADING_MODE",
    "builtwith": "BUILTWITH_API_KEY",
    "hibp": "HIBP_API_KEY",
    "hunter": "HUNTER_API_KEY",
    "http_proxy": "HTTP_PROXY",
    "together": "TOGETHER_API_KEY",
    
    # GitLab (en UI pero no en sync)
    "gitlab": "GITLAB_API_KEY",
}
```

### FASE 3: Completar KEY_SOURCES en capability_config.py
**Archivo:** `cores/setup/capability_config.py`

Agregar documentación para todas las claves faltantes (ver sección 6).

### FASE 4: Exponer URLs de vault (opcional)
**Archivo:** `frontend/src/pages/Settings.vue` → nueva sección "Endpoints / URLs"

O simplemente documentar que usan defaults y solo se cambian en casos edge.

---

## 📋 CHECKLIST DE VERIFICACIÓN POST-FIX

Después de implementar, verificar:

- [ ] `make test-fast` pasa (105 tests)
- [ ] `make work` → Startup protocol completo sin warnings de credenciales
- [ ] Settings UI → pestaña API Keys muestra **todas** las secciones arriba
- [ ] POST `/api/credentials/sync` sincroniza todas las claves
- [ ] GET `/api/credentials/missing` reporta 0 faltantes después de configurar
- [ ] `PendingConfig` component muestra estado honesto (bloqueada/degradada/ninguno)
- [ ] Capability snapshot (`/api/system/capabilities`) refleja presencia real
- [ ] Security Cycle corre end-to-end con API keys configuradas

---

## 🎯 CRITERIO DE ÉXITO

> **Toda credencial que el sistema lea de `os.environ` o `OpportunityCredentials` debe poder configurarse desde Settings UI, sincronizarse via `/api/credentials/sync`, y aparecer en `PendingConfig` con su impacto real (bloqueada/degradada/ninguno).**