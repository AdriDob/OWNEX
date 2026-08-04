# 🏢 Trabajos Extra: Plataformas de Trabajo Directo en Software (Sin Portfolio / Sin Entrevista / Sin Experiencia)

> **Objetivo**: Documentar plataformas donde puedes trabajar directamente en desarrollo de software sin barreras tradicionales (portfolio obligatorio, entrevistas técnicas extensas, años de experiencia requeridos).
> Integrado en el ciclo **FORGE** (Dev Bounty) y **PULSE** (AI Work) de OWNEX.

---

## 📋 Resumen de Plataformas

| Plataforma | Categoría | Barrera de Entrada | Tipo de Trabajo | API / Integración |
|------------|-----------|-------------------|-----------------|-------------------|
| **Freelancer.com** | Freelance general | Baja (microtareas, fixed-price) | Proyectos, concursos, microtareas | ✅ REST API (OAuth) |
| **Open Collective** | Funding OSS / Bounties | Muy baja (contribuciones) | Bounties, funding, sponsorship | ✅ GraphQL API v2 |
| **Algora.xyz** | OSS Bounties (GitHub) | Baja (issues etiquetados) | Bounties en issues GitHub | ✅ REST API |
| **Opire / Opyre** | OSS Bounties | Baja | Bounties en issues GitHub | ✅ REST API |
| **IssueHunt / IssueHand** | OSS Bounties | Baja | Bounties en issues GitHub | ⚠️ API limitada / Scraping |
| **LinkedIn Jobs** | Empleo directo/contrato | Media (filtros: entry-level, contract) | Contratos, freelance, junior | ⚠️ API restringida (partner) |
| **DataAnnotation.tech** | AI Data Work | Muy baja (test de calificación) | Etiquetado, evaluación, training AI | ⚠️ Login + API no oficial |
| **Outlier.ai** | AI Training/Eval | Baja (test de habilidades) | Entrenamiento y evaluación de modelos | ⚠️ API no pública |
| **Mindrift** | AI Training | Baja | Tareas de entrenamiento IA | ⚠️ API no pública |
| **Remotasks** | AI Data Tasks | Muy baja | Data entry, annotation, categorización | ⚠️ API no pública |

---

## 🔵 CICLO FORGE — Dev Bounty / Freelance Directo

### 1. **Freelancer.com** (`core/opportunity/adapters/freelancer.py`)
- **Ubicación**: Sídney, Australia (ASX: FLN, fundada por Matt Barrie)
- **Modelo**: Marketplace global, fixed-price y hourly
- **Barrera baja**: Filtro por "entry level", "junior", "no portfolio", "microtask", "bug fix", "small task"
- **Adapter**: `FreelancerAdapter` (proyectos) + `FreelancerMicrotaskAdapter` (microtareas/concursos)
- **Config**: `api_key` (OAuth token), `user_id`
- **Ciclo**: `forge` (proyectos) / `pulse` (microtareas)
- **Filtros aplicados**: Categoría software development, job_type=fixed, budget 10-5000, keywords de baja barrera

### 2. **Open Collective** (`core/opportunity/adapters/opencollective.py`)
- **Ubicación**: Matriz en París, Francia; Fundación 501(c)(3) en Wyoming, US
- **Modelo**: Fiscal hosting para proyectos OSS; tiers de contribución/backer
- **Barrera muy baja**: Cualquiera puede contribuir a proyectos que aceptan funding
- **Adapters**: 
  - `OpenCollectiveAdapter` — tiers de funding (backer/contributor)
  - `OpenCollectiveProjectsAdapter` — busca colectivos activos por tech stack
- **Config**: `collectives` (lista de slugs), `search_terms` (tech stack)
- **Ciclo**: `forge` (dev_bounty / contribution)
- **GraphQL**: `https://api.opencollective.com/graphql/v2`

### 3. **Algora.xyz** (`core/opportunity/adapters/forge.py` → `AlgoraAdapter`)
- **Ubicación**: San Francisco, US (YC W22)
- **Modelo**: Bounties directamente en issues de GitHub
- **Barrera baja**: Issues etiquetados con bounty, sin entrevista
- **Adapter**: `AlgoraAdapter` en `forge.py`
- **Config**: `token` (GitHub PAT con scope repo)
- **API**: `https://api.algora.xyz/v1/bounties`
- **Ciclo**: `forge` (dev_bounty)

### 4. **Opire / Opyre** (`core/opportunity/adapters/opire.py`)
- **Opire**: Platform principal — `OpireAdapter`
- **Opyre**: Alias/mirror — `OpyreAdapter`
- **Ubicación**: España / EU
- **Modelo**: Bounties en issues GitHub (similar a Algora)
- **Barrera baja**: Claim issue → PR → pago automático
- **API**: `https://api.opire.com/v1/bounties`
- **Config**: `token` (auth token)
- **Ciclo**: `forge` (dev_bounty)

### 5. **IssueHunt / IssueHand** (`core/opportunity/adapters/issuehunt.py`)
- **IssueHunt**: Platforma coreana OSS bounties (issuehunt.io)
- **IssueHand**: Posible variante/typos o fork
- **Modelo**: Bounties en GitHub issues
- **Barrera baja**: Similar a Algora/Opire
- **Adapters creados**:
  - `IssueHuntAdapter` — API `https://api.issuehunt.io/v1/bounties`
  - `IssueHandAdapter` — fallback si es plataforma distinta
- **Config**: `api_key`
- **Ciclo**: `forge` (dev_bounty)

### 6. **LinkedIn Jobs** (`core/opportunity/adapters/linkedin.py`)
- **Ubicación**: Sunnyvale, California, US (Microsoft desde 2016)
- **Modelo**: Job board + networking; filtros para contract/freelance/entry-level
- **Barrera media**: Requiere perfil LinkedIn, pero filtros "entry level", "contract", "freelance", "no experience" reducen barrera
- **Adapter**: `LinkedInAdapter` con fallback curado
- **Config**: `api_key` (partner API), `urn` (organization URN)
- **API**: `https://api.linkedin.com/v2/jobSearch` (requiere partnership)
- **Fallback**: URLs de búsqueda pre-filtradas para trabajo directo sin portfolio
- **Ciclo**: `forge` (direct_employment)

---

## 🟢 CICLO PULSE — AI Work / Data Annotation

### 7. **DataAnnotation.tech** (`core/opportunity/adapters/pulse.py` → `DataAnnotationAdapter`)
- **Ubicación**: US (operación global remota)
- **Modelo**: Data labeling, RLHF, evaluation para empresas AI
- **Barrera muy baja**: Test de calificación (15-30 min) → acceso inmediato a tareas
- **Pago**: Por tarea completada ($20-50/hr típico)
- **Adapter**: Login email/password → token → fetch projects
- **API**: `https://api.dataannotation.tech` (no oficial)
- **Ciclo**: `pulse` (ai_work)

### 8. **Outlier.ai** (`core/opportunity/adapters/pulse.py` → `OutlierAdapter`)
- **Ubicación**: US (Scale AI subsidiary)
- **Modelo**: AI training, evaluation, coding tasks
- **Barrera baja**: Assessment de habilidades → tareas disponibles
- **Pago**: $15-50/hr según tarea
- **API**: `https://api.outlier.ai/v1/projects/available`
- **Config**: `api_key`
- **Ciclo**: `pulse` (ai_work)

### 9. **Mindrift** (`core/opportunity/adapters/pulse.py` → `MindriftAdapter`)
- **Ubicación**: Global (remoto)
- **Modelo**: AI training tasks, writing, coding evaluation
- **Barrera baja**: Registro → test → tareas
- **API**: `https://api.mindrift.com/v1/tasks/available`
- **Config**: `api_key`
- **Ciclo**: `pulse` (ai_work)

### 10. **Remotasks** (`core/opportunity/adapters/pulse.py` → `RemotasksAdapter`)
- **Ubicación**: Scale AI (US), operación global
- **Modelo**: Data entry, annotation, categorization, lidar, etc.
- **Barrera muy baja**: Training modules → certificación → tareas
- **Pago**: Por tarea, variable ($5-20/hr typical)
- **API**: `https://api.remotasks.com/v1/tasks`
- **Config**: `api_key`
- **Ciclo**: `pulse` (ai_work)

---

## 🔧 Configuración en OWNEX (core/cycles/models.py)

```python
# FORGE cycle - Dev Bounty & Direct Freelance
(
    {
        "name": "Forge",
        "slug": "forge",
        "description": "Dev bounty, open source development, freelance software work",
        "category": "FORGE",
        "status": "INACTIVE",
        "enabled": True,
        "priority": 80,
        "config": json.dumps(
            {
                "platforms": [
                    "superteam",
                    "opire",
                    "algora",
                    "opencollective",
                    "freelancer",
                    "linkedin",
                    "issuehunt",
                    "opyre",
                    "issuehand",
                ]
            }
        ),
    },
)

# PULSE cycle - AI Work & Data Annotation
(
    {
        "name": "Pulse",
        "slug": "pulse",
        "description": "AI work, microtasks, data annotation, direct software work",
        "category": "PULSE",
        "status": "INACTIVE",
        "enabled": True,
        "priority": 70,
        "config": json.dumps({"platforms": ["outlier", "mindrift", "dataannotation", "datannotation", "remotasks"]}),
    },
)
```

---

## 📦 Adapter Registry (core/opportunity/adapters/__init__.py)

```python
def _seed_defaults(registry: AdapterRegistry) -> None:
    # ... existing ...
    try:
        from core.opportunity.adapters.forge import ForgeAdapter, SuperteamAdapter, OpireAdapter, AlgoraAdapter

        registry.register("superteam", SuperteamAdapter)
        registry.register("opire", OpireAdapter)
        registry.register("algora", AlgoraAdapter)
        registry.register("forge", ForgeAdapter)  # base
    except ImportError:
        pass

    try:
        from core.opportunity.adapters.opire import OpireAdapter, OpyreAdapter

        registry.register("opire", OpireAdapter)
        registry.register("opyre", OpyreAdapter)
    except ImportError:
        pass

    try:
        from core.opportunity.adapters.issuehunt import IssueHuntAdapter, IssueHandAdapter

        registry.register("issuehunt", IssueHuntAdapter)
        registry.register("issuehand", IssueHandAdapter)
    except ImportError:
        pass

    try:
        from core.opportunity.adapters.linkedin import LinkedInAdapter

        registry.register("linkedin", LinkedInAdapter)
    except ImportError:
        pass

    try:
        from core.opportunity.adapters.freelancer import FreelancerAdapter, FreelancerMicrotaskAdapter

        registry.register("freelancer", FreelancerAdapter)
        registry.register("freelancer_microtask", FreelancerMicrotaskAdapter)
    except ImportError:
        pass

    try:
        from core.opportunity.adapters.opencollective import OpenCollectiveAdapter, OpenCollectiveProjectsAdapter

        registry.register("opencollective", OpenCollectiveAdapter)
        registry.register("opencollective_projects", OpenCollectiveProjectsAdapter)
    except ImportError:
        pass

    try:
        from core.opportunity.adapters.pulse import (
            OutlierAdapter,
            DataAnnotationAdapter,
            MindriftAdapter,
            RemotasksAdapter,
        )

        registry.register("outlier", OutlierAdapter)
        registry.register("dataannotation", DataAnnotationAdapter)
        registry.register("mindrift", MindriftAdapter)
        registry.register("remotasks", RemotasksAdapter)
    except ImportError:
        pass
```

---

## 🔑 Variables de Configuración Necesarias

```bash
# ~/.config/ownex/opportunity.env (o equivalent)

# Freelancer.com
FREELANCER_API_KEY="oauth_token_here"
FREELANCER_USER_ID="user_id_here"

# Open Collective
OPENCOLLECTIVE_COLLECTIVES="webpack,babel,eslint,vuejs,react,nodejs,rust-lang,python,django,rails,laravel,opensource,maintainers,contributors"

# Algora
ALGORA_TOKEN="github_pat_with_repo_scope"

# Opire / Opyre
OPIRE_TOKEN="opire_auth_token"

# IssueHunt
ISSUEHUNT_API_KEY="issuehunt_api_key"

# LinkedIn (requiere partnership)
LINKEDIN_API_KEY="linkedin_partner_api_key"
LINKEDIN_URN="urn:li:organization:xxxxx"

# Outlier.ai
OUTLIER_API_KEY="outlier_api_key"

# DataAnnotation.tech
DATAANNOTATION_EMAIL="email@domain.com"
DATAANNOTATION_PASSWORD="password"

# Mindrift
MINDRIFT_API_KEY="mindrift_api_key"

# Remotasks
REMOTASKS_API_KEY="remotasks_api_key"
```

---

## 🚀 Automatización 24/7 — Próximos Pasos

### 1. Scheduler Jobs (core/scheduler/scheduler.py)
```python
# Jobs para ciclos FORGE y PULSE
JOBS = [
    JobDefinition(
        job_id="forge_fetch_opportunities",
        app_id="opportunity",
        seconds=3600,  # cada hora
        handler=fetch_forge_opportunities,
    ),
    JobDefinition(
        job_id="pulse_fetch_opportunities",
        app_id="opportunity",
        seconds=1800,  # cada 30 min (AI work rota rápido)
        handler=fetch_pulse_opportunities,
    ),
    JobDefinition(
        job_id="score_and_rank_opportunities",
        app_id="opportunity",
        seconds=900,  # cada 15 min
        handler=score_all_opportunities,
    ),
]
```

### 2. Auto-apply / Auto-claim (Future)
- **Algora/Opire/IssueHunt**: Auto-claim issues matching skills → create PR → submit
- **Freelancer**: Auto-bid on microtasks matching profile
- **DataAnnotation/Outlier**: Auto-accept qualified tasks
- **LinkedIn**: Auto-apply to "Easy Apply" contract roles matching filters

### 3. Learning Loop
- Track: applications sent → responses → interviews → contracts → payouts
- Feed back into `PersonalHistory` for better scoring
- `VerdictLearner` (core/learning/) aprende qué plataformas/tipos convierten mejor

---

## 📊 Métricas de Éxito (Revenue Rule)

| Métrica | Target | Plataforma Principal |
|---------|--------|---------------------|
| **Aplicaciones/semana** | 50+ | Freelancer, LinkedIn, Algora |
| **Respuestas/semana** | 10+ | Opire, IssueHunt, Open Collective |
| **Contratos cerrados/mes** | 5+ | Freelancer, LinkedIn, Algora |
| **Ingresos mensuales** | $2,000+ | Mix todas las plataformas |
| **Tasa conversión application→contract** | >10% | Optimizar scoring |

---

## ⚠️ Riesgos y Mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| API rate limits | Backoff exponencial, cache, múltiples API keys |
| Scraping detection (LinkedIn, DataAnnotation) | Usar APIs oficiales, rotar User-Agent, proxies |
| Pago no garantizado (freelance) | Escrow (Freelancer), milestones, reputación |
| Tareas de baja calidad (AI work) | Filter por pay_rate/hr > threshold |
| Cambios en plataformas | Adapter pattern = aislamiento, tests de integración |

---

## 📚 Referencias y URLs

- **Freelancer API**: https://developers.freelancer.com/
- **Open Collective GraphQL**: https://api.opencollective.com/graphql/v2
- **Algora API**: https://api.algora.xyz/v1/bounties
- **Opire API**: https://api.opire.com/v1/bounties
- **IssueHunt**: https://issuehunt.io/ (API docs limitadas)
- **LinkedIn Jobs API**: https://learn.microsoft.com/en-us/linkedin/shared/references/jobs-api (partner only)
- **Outlier.ai**: https://outlier.ai/
- **DataAnnotation.tech**: https://dataannotation.tech/
- **Mindrift**: https://mindrift.com/
- **Remotasks**: https://remotasks.com/

---

*Documento vivo — actualizar al añadir nuevas plataformas o cambiar APIs.*