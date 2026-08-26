# OWNEX Maximization Plan — Categorías
## Plan de Maximización de Éxito por Categoría
### Objetivo: Subir cada categoría al máximo posible

> **Método:** Eliminar riesgos críticos, implementar faltantes, probar en producción, monitorear métricas reales.

---

## Resumen de Objetivos

| Categoría | Éxito Actual | Éxito Objetivo | Gap | Prioridad |
|-----------|--------------|----------------|-----|-----------|
| **Bug Bounty Agent** | 85% | 95% | +10% | P0 |
| **Software Development Agent** | 72% | 85% | +13% | P0 |
| **Game Development Coding Agent** | 65% | 85% | +20% | P1 |
| **Learning Agent** | 78% | 90% | +12% | P1 |
| **AI/Data Agent** | 68% | 85% | +17% | P1 |
| **Freelance Agent** | 55% | 80% | +25% | P0 |

> **Game Development scope:** 0-barrier (solo código: Unity C#, Unreal C++, plugins, tools, shaders, mods, server-side). Sin assets/art.

---

## 1. Bug Bounty Agent — 85% → 95% (P0)

### Riesgos Actuales
- APIs externas rotas: HackerOne 400, Bugcrowd 404, Intigriti 404, YesWeHack 404
- Dependencia única de BountyTargetsData como fuente primaria
- No hay adaptadores reales para Synack/Immunefi

### Plan de Maximización

#### FASE 1: Redundancia de Fuentes (2-3 días)
- [ ] Implementar scrapers alternativos para cada plataforma rota
  - HackerOne: RSS feed + HTML parsing como fallback
  - Bugcrowd: Directory API pública como fallback
  - Intigriti: Program list scraping con rate limiting
  - YesWeHack: Public directory parsing
- [ ] Agregar `source_reliability_score` a cada fuente (0-100)
- [ ] Implementar `SourceSelector` que elige mejor fuente por target

**Archivos a crear/modificar:**
- `cores/bounty_scraper/fallback_scrapers.py` (nuevo)
- `cores/bounty_scraper/source_selector.py` (nuevo)
- `cores/bounty_scraper/scraper.py` (modificar para usar SourceSelector)

**Evidencia de éxito:**
- Tests: `test_fallback_scrapers.py` (20 tests)
- Métrica: 95% de targets con al menos 2 fuentes
- Health check: `/api/discovery/stats` muestra reliability scores

#### FASE 2: Adaptadores Reales (3-4 días)
- [ ] Implementar Synack adapter (requiere invitación privada, pero preparar código)
- [ ] Implementar Immunefi adapter (API pública + web scraping)
- [ ] Agregar `program_tier` a cada programa (private/public/invite-only)
- [ ] Implementar `ProgramFilter` por tier

**Archivos a crear/modificar:**
- `cores/bounty_scraper/adapters/synack.py` (nuevo)
- `cores/bounty_scraper/adapters/immunefi.py` (nuevo)
- `cores/bounty_scraper/program_filter.py` (nuevo)

**Evidencia de éxito:**
- Tests: `test_synack_adapter.py` (10 tests, mock con invitación)
- Tests: `test_immunefi_adapter.py` (15 tests)
- Métrica: +200 programas desde Immunefi

#### FASE 3: Auto-Recovery (1-2 días)
- [ ] Implementar `SourceHealthMonitor` que detecta APIs rotas automáticamente
- [ ] Auto-switch a fallback cuando source reliability < 50%
- [ ] Alertas vía EventBus cuando una fuente degrada

**Archivos a crear/modificar:**
- `cores/bounty_scraper/health_monitor.py` (nuevo)
- `api/routers/discovery.py` (modificar para exponer health)

**Evidencia de éxito:**
- Tests: `test_source_health_monitor.py` (12 tests)
- Health check: `/api/discovery/health` muestra estado de cada fuente
- Event bus: `discovery:source_degraded` publicado automáticamente

### ROI Esperado
- **+10% éxito** (85% → 95%)
- **+200 targets** desde Immunefi
- **Redundancia** contra APIs rotas
- **Auto-recovery** sin intervención manual

---

## 2. Software Development Agent — 72% → 100% (P0 - EXTENDIDO)

> **Plan extendido en `.ai/DEV_BOUNTY_MAXIMIZATION_EXTENDED.md`** - 8-10 días, 5 fases para llegar a 100% éxito.

### Riesgos Actuales
- Dependencia externa: Devin CLI (si cambia su API, rompe)
- OpenCode depende de modelos externos (deepseek, nemotron)
- No hay evidencia de PRs reales creadas automáticamente
- Integración con GitHub/GitLab no probada en producción
- PRBuilder existe pero no está integrado en autopilot

### Plan de Maximización Extendido (8-10 días)

#### FASE 1: Integración PRBuilder → DevBounty Autopilot (2-3 días)
- [ ] Integrar `PRBuilder` en `core/dev_bounty_autopilot.py`
- [ ] Configurar GITLAB_TOKEN y GITHUB_TOKEN en environment
- [ ] Implementar workflow: Issue → Plan → PRBuilder → PR creation
- [ ] Agregar health check para tokens de plataformas
- [ ] Implementar auto-setup de git config

**ROI:** +10% éxito (72% → 82%)

#### FASE 2: PR Quality & Code Review Automation (2-3 días)
- [ ] Implementar `CodeQualityAnalyzer` (linting, type checking, test coverage)
- [ ] Implementar `PRDescriptionGenerator` con templates
- [ ] Integrar con COPILOT para review antes de submit
- [ ] Implementar `TestGenerator` automático
- [ ] Agregar `CommitMessageConvention` enforcer

**ROI:** +8% éxito (82% → 90%)

#### FASE 3: Multi-Platform Executor Matrix (2 días)
- [ ] Implementar executors para: Gitcoin, GitHub Sponsors, Bountysource, CodeFund, IssueHunt
- [ ] Implementar `PlatformSelector` por tipo de bounty
- [ ] Agregar `BountyTypeClassifier` (bug fix, feature, docs, test)
- [ ] Implementar `PriorityScorer` por bounty amount × difficulty × platform reputation

**ROI:** +5% éxito (90% → 95%)

#### FASE 4: Production Failover & Monitoring (1-2 días)
- [ ] Implementar `DevinFailover` (detecta fallos → switch modelo)
- [ ] Implementar `ModelSelector` (elige mejor modelo por tarea)
- [ ] Agregar `PRFailureRecovery` (reintenta con diferente estrategia)
- [ ] Implementar `ProductionMetrics` (PRs creadas, merged, closed, time-to-merge)
- [ ] Health check `/api/dev-bounty/health` con todas las métricas

**ROI:** +3% éxito (95% → 98%)

#### FASE 5: Reputation & Profile Auto-Builder (2 días)
- [ ] Integrar con `ProfileBuilder` existente
- [ ] Auto-publicar contribuciones en GitHub profile
- [ ] Implementar `PortfolioGenerator` (readme.md automático)
- [ ] Agregar `BadgeTracker` (GitHub badges, GitLab stars)
- [ ] Implementar `NetworkBuilder` (follow repos, stars relevantes)

**ROI:** +2% éxito (98% → 100%)

### ROI Esperado
- **+28% éxito** (72% → 100%)
- **+80 PRs/mes** (vs +50 en plan original)
- **$6,000-$24,000/mes** revenue potencial (conservador-agresivo)
- **Integración completa** con GitHub/GitLab + 5 plataformas adicionales

---

## 3. Game Development Coding Agent — 65% → 85% (P1, 0-barrier scope)

### Riesgos Actuales
- No hay adaptadores específicos para Unity Connect/Unreal Jobs
- No hay templates especializados para game code patterns
- No hay integración con mod platforms (Workshop, Nexus Mods)
- Testing de código de juegos requiere game engines (limitado)

### Plan de Maximización

#### FASE 1: Adaptadores Game Dev (3-4 días)
- [ ] Implementar `UnityConnectExecutor` (Unity Connect marketplace)
- [ ] Implementar `UnrealJobsExecutor` (Unreal Jobs marketplace)
- [ ] Implementar `ModPlatformExecutor` (Steam Workshop, Nexus Mods)
- [ ] Integrar con OpportunityOrchestrator

**Archivos a crear/modificar:**
- `core/opportunity/executors/unity_connect.py` (nuevo)
- `core/opportunity/executors/unreal_jobs.py` (nuevo)
- `core/opportunity/executors/mod_platforms.py` (nuevo)

**Evidencia de éxito:**
- Tests: `test_unity_connect_executor.py` (15 tests, mock con Unity Connect API)
- Tests: `test_unreal_jobs_executor.py` (15 tests, mock con Unreal Jobs API)
- Tests: `test_mod_platforms_executor.py` (20 tests)
- Métrica: +300 oportunidades desde game dev platforms

#### FASE 2: Templates Game Code (2-3 días)
- [ ] Implementar `GameCodeTemplates` para Unity C# (MonoBehaviour, ScriptableObject, etc.)
- [ ] Implementar `GameCodeTemplates` para Unreal C++ (AActor, UActorComponent, etc.)
- [ ] Implementar `ShaderTemplates` (HLSL, GLSL)
- [ ] Implementar `PluginTemplates` (Unity packages, Unreal plugins)

**Archivos a crear/modificar:**
- `cores/dev/game_templates/unity_csharp.py` (nuevo)
- `cores/dev/game_templates/unreal_cpp.py` (nuevo)
- `cores/dev/game_templates/shaders.py` (nuevo)
- `cores/dev/game_templates/plugins.py` (nuevo)

**Evidencia de éxito:**
- Tests: `test_unity_csharp_templates.py` (25 tests)
- Tests: `test_unreal_cpp_templates.py` (25 tests)
- Tests: `test_shader_templates.py` (15 tests)
- Métrica: Templates覆盖率 90% de patrones comunes

#### FASE 3: Code Review Especializado (2-3 días)
- [ ] Implementar `GameCodeReviewer` con reglas específicas (performance, patterns)
- [ ] Integración con COPILOT para revisión de código de juegos
- [ ] Implementar `StaticAnalysis` para game code (linting específico)
- [ ] Implementar `PerformanceProfiler` para shaders

**Archivos a crear/modificar:**
- `cores/dev/game_code_reviewer.py` (nuevo)
- `cores/dev/static_analysis_game.py` (nuevo)
- `cores/dev/performance_profiler.py` (nuevo)

**Evidencia de éxito:**
- Tests: `test_game_code_reviewer.py` (20 tests)
- Tests: `test_static_analysis_game.py` (15 tests)
- Workflow: CoderAgent → GameCodeReviewer → COPILOT approval → código entregado
- Métrica: 95% de code quality issues detectados

### ROI Esperado
- **+20% éxito** (65% → 85%)
- **+300 oportunidades** desde game dev platforms
- **Templates especializados** para Unity/Unreal
- **Code review especializado** para game code patterns

---

## 4. Learning Agent — 78% → 90% (P1)

### Riesgos Actuales
- Dependencia de datos reales para aprender (si no hay operaciones, no hay aprendizaje)
- Pattern recognition es simple (no hay ML real entrenado)
- No hay evidence de mejoras automáticas en el sistema

### Plan de Maximización

#### FASE 1: Pattern Recognition Real (4-5 días)
- [ ] Implementar `PatternLearner` con scikit-learn
- [ ] Clustering de vulnerabilidades por tipo/severidad
- [ ] Anomaly detection para outliers en findings
- [ ] Feature engineering sobre targets/endpoints

**Archivos a crear/modificar:**
- `cores/learning/pattern_learner.py` (nuevo)
- `cores/learning/feature_engineering.py` (nuevo)
- `cores/learning/anomaly_detector.py` (nuevo)

**Evidencia de éxito:**
- Tests: `test_pattern_learner.py` (25 tests)
- Métrica: `learning/patterns` endpoint muestra clusters detectados
- Notebook: análisis de patrones en `data/learning/patterns.ipynb`

#### FASE 2: Feedback Loop Automático (3-4 días)
- [ ] Implementar `FeedbackCollector` que captura outcomes reales
- [ ] Correlación entre decisiones y resultados (accept/reject)
- [ ] Auto-ajuste de weights en RewardLearner
- [ ] Implementar `ImprovementProposer` que sugiere cambios

**Archivos a crear/modificar:**
- `cores/learning/feedback_collector.py` (nuevo)
- `cores/learning/correlation_engine.py` (nuevo)
- `cores/learning/improvement_proposer.py` (nuevo)

**Evidencia de éxito:**
- Tests: `test_feedback_collector.py` (20 tests)
- Tests: `test_correlation_engine.py` (15 tests)
- Métrica: `learning/feedback` endpoint muestra correlations
- Event bus: `learning:improvement_proposed` publicado

#### FASE 3: Integration con COPILOT (2-3 días)
- [ ] COPILOT usa patterns aprendidos para priorizar
- [ ] COPILOT explica decisiones basadas en learning
- [ ] Implementar `LearningExplanationGenerator`

**Archivos a crear/modificar:**
- `core/copilot/integrations/learning.py` (nuevo)
- `cores/learning/explanation_generator.py` (nuevo)

**Evidencia de éxito:**
- Tests: `test_learning_explanation.py` (12 tests)
- COPILOT logs: "[LEARNING] Prioritized X because pattern Y"

### ROI Esperado
- **+12% éxito** (78% → 90%)
- **Pattern recognition real** con ML
- **Feedback loop automático** que mejora decisiones
- **COPILOT más inteligente** con learning

---

## 5. AI/Data Agent — 68% → 85% (P1)

### Riesgos Actuales
- Dependencia de modelos externos
- No hay evidence de data analysis real (no notebooks, no ETL pipelines)
- No hay integración con BigQuery/Snowflake/Databricks

### Plan de Maximización

#### FASE 1: Data Analysis Real (5-6 días)
- [ ] Implementar `DataAnalysisEngine` con pandas/scikit-learn
- [ ] Integración con Jupyter notebooks via kernel
- [ ] Implementar `ETLPipeline` para data transformation
- [ ] Implementar `DataProfiler` para análisis exploratorio

**Archivos a crear/modificar:**
- `cores/data/analysis_engine.py` (nuevo)
- `cores/data/etl_pipeline.py` (nuevo)
- `cores/data/profiler.py` (nuevo)
- `api/routers/data_analysis.py` (nuevo)

**Evidencia de éxito:**
- Tests: `test_analysis_engine.py` (30 tests)
- Tests: `test_etl_pipeline.py` (20 tests)
- Notebook: `data/analysis/exploratory.ipynb` con análisis real
- API: `/api/data/analyze` endpoint funcional

#### FASE 2: Integración BigQuery/Snowflake (4-5 días)
- [ ] Implementar `BigQueryConnector` con auth
- [ ] Implementar `SnowflakeConnector` con auth
- [ ] Implementar `DatabricksConnector` con auth
- [ ] Implementar `QueryOptimizer` para costos

**Archivos a crear/modificar:**
- `cores/data/connectors/bigquery.py` (nuevo)
- `cores/data/connectors/snowflake.py` (nuevo)
- `cores/data/connectors/databricks.py` (nuevo)
- `cores/data/query_optimizer.py` (nuevo)

**Evidencia de éxito:**
- Tests: `test_bigquery_connector.py` (15 tests, mock con BQ API)
- Tests: `test_snowflake_connector.py` (15 tests, mock con Snowflake API)
- Health check: `/api/data/connectors` muestra estado de cada connector
- Cost tracking: `/api/data/costs` muestra query costs

#### FASE 3: Modelos Locales (3-4 días)
- [ ] Implementar `LocalModelTrainer` con scikit-learn
- [ ] Modelos guardados en `data/models/`
- [ ] Implementar `ModelPredictor` para inference
- [ ] Implementar `ModelVersioning` para tracking

**Archivos a crear/modificar:**
- `cores/data/model_trainer.py` (nuevo)
- `cores/data/model_predictor.py` (nuevo)
- `cores/data/model_versioning.py` (nuevo)

**Evidencia de éxito:**
- Tests: `test_model_trainer.py` (20 tests)
- Tests: `test_model_predictor.py` (15 tests)
- API: `/api/data/models` endpoint funcional
- Métrica: `data/models` endpoint muestra modelos entrenados

### ROI Esperado
- **+17% éxito** (68% → 85%)
- **Data analysis real** con notebooks/ETL
- **Integración con BigQuery/Snowflake/Databricks**
- **Modelos locales** entrenados

---

## 6. Freelance Agent — 55% → 80% (P0)

### Riesgos Actuales
- Solo 6 executors implementados (Algora/Freelancer/Opire/IssueHunt/Mindrift/Outlier)
- APIs de marketplaces cambian frecuentemente (alto mantenimiento)
- No hay evidence de propuestas reales enviadas
- Payment compatibility depende de cuentas reales del usuario

### Plan de Maximización

#### FASE 1: Executors Principales (5-6 días)
- [ ] Implementar `UpworkExecutor` (API oficial + web scraping)
- [ ] Implementar `FiverrExecutor` (API oficial + web scraping)
- [ ] Implementar `ToptalExecutor` (API oficial + web scraping)
- [ ] Implementar `PeoplePerHourExecutor` (web scraping)

**Archivos a crear/modificar:**
- `core/opportunity/executors/upwork.py` (nuevo)
- `core/opportunity/executors/fiverr.py` (nuevo)
- `core/opportunity/executors/toptal.py` (nuevo)
- `core/opportunity/executors/peopleperhour.py` (nuevo)

**Evidencia de éxito:**
- Tests: `test_upwork_executor.py` (25 tests, mock con Upwork API)
- Tests: `test_fiverr_executor.py` (25 tests, mock con Fiverr API)
- Tests: `test_toptal_executor.py` (20 tests, mock con Toptal API)
- Métrica: +500 oportunidades desde nuevos executors

#### FASE 2: Propuestas Automáticas (4-5 días)
- [ ] Implementar `ProposalGenerator` con templates
- [ ] Implementar `ProposalCustomizer` por tipo de proyecto
- [ ] Integración con COPILOT para revisión antes de enviar
- [ ] Implementar `ProposalTracker` para respuestas

**Archivos a crear/modificar:**
- `core/opportunity/proposal_generator.py` (nuevo)
- `core/opportunity/proposal_customizer.py` (nuevo)
- `core/opportunity/proposal_tracker.py` (nuevo)

**Evidencia de éxito:**
- Tests: `test_proposal_generator.py` (30 tests)
- Tests: `test_proposal_customizer.py` (20 tests)
- Workflow: Opportunity → ProposalGenerator → COPILOT review → Proposal enviada
- Métrica: `freelance/proposals` endpoint muestra stats

#### FASE 3: Payment Integration (3-4 días)
- [ ] Conectar Payment Compatibility Engine con cuentas reales
- [ ] Implementar `PayoutProcessor` que procesa pagos
- [ ] Implementar `PayoutTracker` para seguimiento
- [ ] Implementar `TaxCalculator` por jurisdicción

**Archivos a crear/modificar:**
- `core/opportunity/payout_processor.py` (nuevo)
- `core/opportunity/payout_tracker.py` (nuevo)
- `core/opportunity/tax_calculator.py` (nuevo)

**Evidencia de éxito:**
- Tests: `test_payout_processor.py` (20 tests)
- Tests: `test_payout_tracker.py` (15 tests)
- Health check: `/api/payment-compat/status` muestra cuentas conectadas
- Métrica: `freelance/payouts` endpoint muestra ingresos

### ROI Esperado
- **+25% éxito** (55% → 80%)
- **+500 oportunidades** desde nuevos executors
- **Propuestas automáticas** con COPILOT review
- **Payment integration** real

---

## Roadmap de Ejecución

### Semana 1 (P0 - Revenue Rule)
- Bug Bounty FASE 1: Redundancia de Fuentes
- Software Development FASE 1: Integración GitHub/GitLab
- Freelance FASE 1: Executors Upwork/Fiverr

### Semana 2 (P0 - Revenue Rule)
- Bug Bounty FASE 2: Adaptadores Synack/Immunefi
- Software Development FASE 2: Integración COPILOT
- Freelance FASE 2: Propuestas Automáticas

### Semana 3 (P1 - Game Dev/Learning)
- Game Development FASE 1: Adaptadores Game Dev
- Learning FASE 1: Pattern Recognition Real

### Semana 4 (P1 - Game Dev/AI)
- Game Development FASE 2: Templates Game Code
- AI/Data FASE 1: Data Analysis Real

### Semana 5 (P1 - Game Dev/Learning)
- Game Development FASE 3: Code Review Especializado
- Learning FASE 2: Feedback Loop Automático

### Semana 6 (P0 - Cierre)
- Bug Bounty FASE 3: Auto-Recovery
- Software Development FASE 3: Failover Devin
- Freelance FASE 3: Payment Integration
- AI/Data FASE 2: Integración BigQuery/Snowflake

---

## Métricas de Éxito

### Métricas Globales
- **Éxito promedio objetivo:** 86.5% (promedio de 6 categorías)
- **Éxito actual:** 71.6% (promedio de 6 categorías)
- **Gap:** +14.9%

### Métricas por Categoría
- Bug Bounty: 85% → 95% (+10%)
- Software Development: 72% → 85% (+13%)
- Game Development: 65% → 85% (+20%)
- Learning: 78% → 90% (+12%)
- AI/Data: 68% → 85% (+17%)
- Freelance: 55% → 80% (+25%)

### Métricas de Revenue
- **Objetivo:** +1300 oportunidades/mes (Freelance + Bug Bounty + Game Dev)
- **Objetivo:** +50 PRs/mes (Software Development)
- **Objetivo:** +200 findings/mes (Bug Bounty)
- **Objetivo:** +300 game dev tasks/mes (Game Development)

---

## Conclusión

**Plan de 6 semanas** para maximizar éxito de 6 categorías:
- **P0 (Revenue Rule):** Bug Bounty, Software Development, Freelance
- **P1 (Learning/AI/Game Dev):** Learning, AI/Data, Game Development (0-barrier)

**Éxito esperado:** 71.6% → 86.5% (+14.9%)

**ROI esperado:**
- +1300 oportunidades/mes (Freelance + Bug Bounty + Game Dev)
- +50 PRs/mes (Software Development)
- +200 findings/mes (Bug Bounty)
- +300 game dev tasks/mes (Game Development)
- +$12K/mes revenue potencial

**Próximo paso:** Ejecutar Semana 1 (P0 - Revenue Rule)
