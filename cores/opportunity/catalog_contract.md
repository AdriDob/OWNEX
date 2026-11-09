# Catálogo de Fuentes de Trabajo Propio — Contrato de Separación y Adaptador

## 1. Propósito

Este documento describe el contrato de separación entre el catálogo propio de fuentes de trabajo (OWNEX) y el motor de discovery (DWE). El catálogo propio se construye fuera del árbol bloqueado (`core/`, `cores/`, `core/cores/`, `core/manage/`, `core/opportunity/adapters/*`, `core/mcp_rastro.py`, `core/targets_sync.py`) para no interferir con la migración del otro proceso.

## 2. Alcance del Catálogo Propio

El catálogo propio incluye:
- 18 fuentes base en `cores/opportunity/own_work_sources.py`
- 5 fuentes segunda ola en `cores/opportunity/own_work_sources_extensions.py` (build_second_wave_extension)
- 5 fuentes tercera ola en `cores/opportunity/own_work_sources_extensions.py` (build_third_wave_extension)
- 7 fuentes cuarta ola en `cores/opportunity/own_work_sources_extensions.py` (build_fourth_wave_bounty_extension + build_fourth_wave_dev_extension)
- 7 fuentes quinta ola en `cores/opportunity/own_work_sources_extensions.py` (build_fifth_wave_dev_extension)
- 2 fuentes sexta ola en `cores/opportunity/own_work_sources_extensions.py` (build_sixth_wave_security_extension + build_sixth_wave_dev_extension)
- Total: 44 fuentes propias

## 3. Separación Discovery vs Motor

### Regla de Oro

No conectar fuentes al motor de discovery (DWE) hasta que:
1. El contrato del adaptador esté verificado completamente.
2. La separación entre discovery y motor esté validada.
3. El motor acepte extensiones externas verificadas.

### Estado Actual

- **OwnWorkCatalogAdapter** (api/adapters/own_work_catalog_adapter.py): prototipo, NO registrado en producción.
- **HermesDirectWorkAdapter** (api/adapters/direct_work_hermes.py): prototipo, NO registrado en producción; hereda `BaseDiscoveryAdapter` y reutiliza los helpers de mapeo del adaptador de catálogo.
- El motor DWE sigue siendo un mono-opositorio estricto: no acepta extensiones externas verificadas.
- Decision pendiente: registrar adaptadores en `_ensure_default_adapters` (api/routers/direct_work.py) después de verificación completa.

## 4. Mapeo de Plataformas

Las fuentes del catálogo propio tienen campos de plataforma que requieren mapeo a las plataformas del motor de discovery. El mapeo se realiza mediante `SOURCE_PLATFORM_MAP` en `cores/opportunity/own_work_sources.py`.

Los campos se mapean con helpers en `api/adapters/own_work_catalog_adapter.py`; el detalle normativo está en "Reglas de Mapeo" debajo. `employment_type` se corrige post-creación porque `_create_opportunity` no lo expone como parámetro.

## 4. Reglas de Mapeo

### Mapeo de Plataforma

- SourceDefinition no tiene campo platform.
- SOURCE_PLATFORM_MAP resuelve plataforma desde nombre de fuente para fuentes con plataforma conocida del motor.
- Solo se mapea cuando source.name coincide con una clave en SOURCE_PLATFORM_MAP.
- Fuentes sin mapear quedan solo en catálogo; NO inyectadas en motor.

### Mapeo de Campos

Todos los mapeos usan helpers de adaptador en `api/adapters/own_work_catalog_adapter.py`:

#### platform
- Resuelto de SOURCE_PLATFORM_MAP por source.name o `source.platform` cuando existe.
- Si no hay mapeo, `_create_opportunity` mantiene `DiscoverySource.platform` (no se fuerza `OTHER`).

#### category
- Mapeado de source.category a OpportunityCategory aceptado por el motor.
- Fallback a DEV_BOUNTY para categorías desconocidas.

#### payment_method
- Mapeado de source.payment_methods usando métodos de pago documentados de source_payment_docs.py.
- Fallback a PLATFORM_CREDIT para fuentes no documentadas.

#### employment_type
- Mapeado de source.employment_type.
- Fallback a BOUNTY para tipos de empleo desconocidos.

#### entry_mechanism
- Mapeado de source.apply_method.
- Fallback a DIRECT para métodos de aplicación desconocidos.

#### international_payment
- `source.international_payment` explícito gana cuando existe (bool o string booleano).
- Si no hay campo explícito: True cuando `source.region` no es específico de Argentina; None cuando `source.region` es `ar`/`argentina`/vacío.

#### experience_requirement
- Mapeado de source.requires_experience (True/False/"preferred"/"optional"/"required"/"none").
- Fallback a NONE para valores desconocidos.

#### rate_source
- Siempre "catalog" para oportunidades del catálogo propio.

#### technology_tags
- `_technology_tags_for_source` lee `source.technology_tags` primero y `source.tags` después, deduplicando strings no vacíos.

#### employment_type
- Corrección post-creación: _create_opportunity no pasa **kwargs al constructor de Opportunity, por lo que employment_type se establece después de la creación.

---

## 5. Adaptadores

### OwnWorkCatalogAdapter (api/adapters/own_work_catalog_adapter.py)

- Adaptador prototipo que puentea fuentes de trabajo propias de OWNEX al DWE.
- Hereda BaseDiscoveryAdapter, recibe DiscoverySource en __init__.
- Implementa async def validate_connection() -> bool y async def fetch_opportunities() -> list[Opportunity].
- Usa _create_opportunity con corrección post-creación de employment_type.
- Mapea plataforma desde SOURCE_PLATFORM_MAP cuando no hay platform explícito.
- Mapea entry_mechanism, international_payment, experience_requirement, rate_source, technology_tags.
- Fuentes mapeadas (13): GitHub Sponsors→github, IssueHunt→issuehunt, Algora→algora, Superteam Earn→superteam, Opire→opire, Opyre→opire, Immunefi→immunefi, HackerOne→hackerone, Bugcrowd→bugcrowd, Intigriti→intigriti, YesWeHack→yeswehack, Open Collective→opencollective, GitHub Bounty Labels→github.
- Fuentes sin mapear (31): quedan en catálogo, no inyectadas en motor.
- Tests: 22 pasaron (test_own_work_catalog_adapter_contract.py).

### HermesDirectWorkAdapter (api/adapters/direct_work_hermes.py)

- Adaptador prototipo que puentea fuentes de trabajo de Hermes al DWE.
- Hereda `BaseDiscoveryAdapter` y reutiliza los helpers de `own_work_catalog_adapter` (platform, category, payment_method, employment_type, entry_mechanism, international_payment, experience_requirement, rate_source, technology_tags).
- Los campos específicos de Hermes (`heuristics_analyzed`, `analysis_complete`, `cached_analysis`, `analysis_revision`, `analysis_started_at`) NO se inyectan en `Opportunity`: el modelo usa `__slots__` y los tests verifican `not hasattr(opp, ...)`. Permanecen en la fuente de catálogo.
- NO afirma verificación de pago, compatibilidad Argentina, o FULLY_ELIGIBLE.
- Tests: 19 pasaron (test_direct_work_hermes.py).

### Estado de Registro

- OwnWorkCatalogAdapter: NO registrado en producción. Solo prototipo.
- HermesDirectWorkAdapter: NO registrado en producción. Solo prototipo.
- Decision pendiente: si registrar adaptadores en _ensure_default_adapters (api/routers/direct_work.py) después de verificación completa del contrato.

---

## 6. Catálogo de Fuentes

### Fuentes OwnWork (18 base + 5 segunda ola + 5 tercera ola + 7 cuarta ola + 7 quinta ola + 2 sexta ola = 44 total)

#### Base (18 fuentes en own_work_sources.py)

| Fuente | Plataforma | Categoría | Métodos de Pago |
|--------|------------|-----------|-----------------|
| WordPress Plugin Bounties | (sin mapeo) | dev_bounty | not_published |
| GitHub Sponsors | github | dev_bounty | varies |
| IssueHunt | issuehunt | dev_bounty | varies |
| Bountysource | (sin mapeo) | dev_bounty | varies |
| SeaPay Bounties | (sin mapeo) | dev_bounty | varies |
| Superteam Earn | superteam | dev_bounty | varies |
| Algora | algora | dev_bounty | crypto/stablecoin |
| Opire | opire | dev_bounty | varies |
| Opyre | opire | dev_bounty | varies |
| BountyHub | (sin mapeo) | dev_bounty | varies |
| TaskBounty | (sin mapeo) | dev_bounty | varies |
| FreelanceMap | (sin mapeo) | dev_bounty | varies |
| Stack Overflow Jobs | (sin mapeo) | dev_bounty | varies |
| Immunefi | immunefi | bug_bounty | varies |
| Hats Finance | (sin mapeo) | bug_bounty | varies |
| Secure3 | (sin mapeo) | bug_bounty | varies |
| BugRap | (sin mapeo) | bug_bounty | varies |
| ChainLove | (sin mapeo) | bug_bounty | varies |

#### Segunda Ola (5 fuentes en own_work_sources_extensions.py)

| Fuente | Plataforma | Categoría | Métodos de Pago |
|--------|------------|-----------|-----------------|
| Wordscape Bounties | (sin mapeo) | dev_bounty | not_published |
| BountySource Forge | (sin mapeo) | dev_bounty | crypto/stablecoin |
| CryptoDev Bounties | (sin mapeo) | bug_bounty | crypto/stablecoin |
| Solana Guild Tasks | (sin mapeo) | dev_bounty | crypto/stablecoin |
| Web3 Bug Bounties Hub | (sin mapeo) | bug_bounty | crypto/stablecoin |

#### Tercera Ola (5 fuentes en own_work_sources_extensions.py)

| Fuente | Plataforma | Categoría | Métodos de Pago |
|--------|------------|-----------|-----------------|
| Gitcoin Bounties | (sin mapeo) | bug_bounty | crypto/stablecoin |
| Bounties Network | (sin mapeo) | dev_bounty | crypto/stablecoin |
| ETHGlobal Bounties | (sin mapeo) | dev_bounty | crypto/stablecoin |
| CodeTriage Bounties | (sin mapeo) | dev_bounty | not_published |
| Polywork Bounties | (sin mapeo) | dev_bounty | crypto/stablecoin |

#### Cuarta Ola — Bug Bounty (4 fuentes en own_work_sources_extensions.py)

| Fuente | Plataforma | Categoría | Métodos de Pago |
|--------|------------|-----------|-----------------|
| HackerOne | hackerone | bug_bounty | paypal/bank_transfer |
| Bugcrowd | bugcrowd | bug_bounty | paypal/bank_transfer |
| Intigriti | intigriti | bug_bounty | bank_transfer/paypal |
| YesWeHack | yeswehack | bug_bounty | paypal/bank_transfer |

#### Cuarta Ola — Dev/OSS Funding (3 fuentes en own_work_sources_extensions.py)

| Fuente | Plataforma | Categoría | Métodos de Pago |
|--------|------------|-----------|-----------------|
| Open Collective | opencollective | dev_bounty | paypal/bank_transfer |
| OnlyDust | (sin mapeo) | dev_bounty | crypto/stablecoin |
| Polar | (sin mapeo) | dev_bounty | not_published |

#### Quinta Ola — Dev/OSS Funding (7 fuentes en own_work_sources_extensions.py)

| Fuente | Plataforma | Categoría | Métodos de Pago |
|--------|------------|-----------|-----------------|
| GitHub Bounty Labels | github | dev_bounty | not_published |
| OpenQ | (sin mapeo) | dev_bounty | crypto/stablecoin |
| Codefund | (sin mapeo) | dev_bounty | crypto/stablecoin |
| HackerLink | (sin mapeo) | dev_bounty | crypto/stablecoin |
| Dework | (sin mapeo) | dev_bounty | crypto/stablecoin |
| Guild.xyz | (sin mapeo) | dev_bounty | crypto/stablecoin |
| Buidlbox | (sin mapeo) | dev_bounty | crypto/stablecoin |

#### Sexta Ola — Prioridad (2 fuentes en own_work_sources_extensions.py)

| Fuente | Plataforma | Categoría | Métodos de Pago |
|--------|------------|-----------|-----------------|
| Patchstack | (sin mapeo) | bug_bounty | paypal/crypto |
| Bountycaster | (sin mapeo) | dev_bounty | crypto/stablecoin |

### Resumen de Mapeo de Plataformas

- Mapeadas (13): GitHub Sponsors→github, IssueHunt→issuehunt, Algora→algora, Superteam Earn→superteam, Opire→opire, Opyre→opire, Immunefi→immunefi, HackerOne→hackerone, Bugcrowd→bugcrowd, Intigriti→intigriti, YesWeHack→yeswehack, Open Collective→opencollective, GitHub Bounty Labels→github.
- Sin mapear (31): quedan en catálogo, no inyectadas en motor.

### Documentación de Pago

- source_payment_docs.py: KNOWN_PAYMENT_METHODS con 35 entradas (19 base + 7 cuarta ola + 7 quinta ola + 2 sexta ola).
- own_work_sources_extensions.py: build_payment_doc_second_wave(), build_payment_doc_third_wave(), build_payment_doc_fourth_wave(), build_payment_doc_fifth_wave() y build_payment_doc_sixth_wave() con documentación de pago para fuentes de segunda, tercera, cuarta, quinta y sexta ola.

---

## 7. Resultados de Verificación

### Pruebas del Contrato del Adaptador

- test_own_work_catalog_adapter_contract.py: 22 pasaron
  - imports/construct/load/validate/fetch fixture
  - entry_mechanism / international_payment / experience_requirement mappings
  - payment docs reales (Algora→crypto, GitHub Sponsors→platform_credit, HackerOne→paypal, OnlyDust→crypto, GitHub Bounty Labels→platform_credit, OpenQ→crypto, Patchstack→paypal, Bountycaster→crypto), payment_methods desconocidos, technology_tags con no-strings y serialización `_opportunity_to_dict`

### Pruebas de Fuentes

- test_own_work_sources.py: 58 pasaron
- test_own_work_sources_extensions.py: 36 pasaron (base + segunda ola + tercera ola + cuarta ola + quinta ola + sexta ola)

### Pruebas del Adaptador Hermes

- test_direct_work_hermes.py: 19 pasaron
  - imports/constructs/loads catalog source
  - base fields + Hermes fields permanecen fuera de Opportunity
  - entry_mechanism / international_payment / experience_requirement / rate_source / technology_tags
  - empty catalog source, unknown employment_type y smoke de construcción
  - edge cases: payment_methods desconocidos, platform/category desconocidos, international_payment explícito, serialización `_opportunity_to_dict` y build determinista de 100 fuentes

### Verificación scoped adicional

- test_direct_work_engine.py: 39 pasaron (regresión del helper `_create_opportunity`).

### Total de Pruebas scoped: 58 + 36 + 22 + 19 + 39 = 174 pasaron

---

## 8. Decisiones

### Decisión: NO Registrar en Producción (documentada)

- Adaptadores NO registrados en _ensure_default_adapters (api/routers/direct_work.py).
- Razón: verificación del contrato incompleta, separación discovery/motor no fully verificada.
- Estado: documentado, sin registro prematuro.
- Próximo paso: completar verificación del contrato antes de reconsiderar registro.

### Decisión: Mapeo de Plataforma via SOURCE_PLATFORM_MAP

- Plataforma resuelta desde source.name via SOURCE_PLATFORM_MAP.
- Fuentes sin mapear quedan solo en catálogo.
- No inyección en motor sin mapeo de plataforma verificado.

### Decisión: Adaptador Hermes como Prototipo

- HermesDirectWorkAdapter hereda `BaseDiscoveryAdapter` y reutiliza los helpers de `own_work_catalog_adapter`.
- Los campos Hermes-specific NO se inyectan en `Opportunity` (slots); permanecen en la fuente de catálogo.
- NO afirma verificación de pago, compatibilidad Argentina, o FULLY_ELIGIBLE.
- No registrado en producción.

---

## 9. Próximos Pasos

### Verificación del Contrato del Adaptador (pendiente)

1. Completar verificación del contrato del adaptador Hermes:
   - Campos restantes: payment_method, payment, currency, registration_required, accepts_beginner, accepts_individuals, asynchronous, company, title, description, url, external_id.
   - Casos edge adicionales: fuente con payment_methods con valores desconocidos, fuente con tags con valores no-string, fuente con platform desconocido que no está en SOURCE_PLATFORM_MAP, fuente con category desconocido que no está en el mapping del adaptador.
   - Rendimiento: tiempo de construcción y fetch para múltiples fuentes, memoria por oportunidad.
   - Serialización: verificar que _opportunity_to_dict maneja los campos Hermes extras (heuristics_analyzed, analysis_complete, cached_analysis, analysis_revision, analysis_started_at) correctamente.
2. Completar verificación del contrato del adaptador OwnWorkCatalogAdapter:
   - Campos restantes: payment_method (con valores desconocidos), payment (con valores cero y no-cero), currency (con valores diferentes a USD), registration_required (con valores diferentes a bool), accepts_beginner (con valores diferentes a bool), accepts_individuals (con valores diferentes a bool), asynchronous (con valores diferentes a bool).
   - Casos edge adicionales: fuente con payment_methods con métodos no documentados, fuente con tags con valores no-string, fuente con platform desconocido que no está en SOURCE_PLATFORM_MAP, fuente con category desconocido que no está en el mapping del adaptador.
   - Rendimiento: tiempo de construcción y fetch para múltiples fuentes, memoria por oportunidad.
   - Serialización: verificar que _opportunity_to_dict maneja los campos del catálogo extras correctamente.
3. Verificar separación discovery/motor:
   - Confirmar que el motor DWE no acepta extensiones externas verificadas.
   - Confirmar que el catálogo propio no inyecta fuentes en el motor sin verificación completa.
   - Documentar la separación en este archivo.
4. RESUELTO — Pregunta pendiente: cómo los campos reales de Opportunity pierden información del catálogo propio (argentina_compatible, withdrawal_verified, payout_verified, etc.)

**Respuesta corta:** los campos del catálogo propio NO se pierden porque NO se inyectan en Opportunity en primer lugar. El modelo Opportunity bloquea la inyección de campos que no existen en el modelo (usa `__slots__`), por lo que no hay pérdida posible.

**Evidencia:** Intentar inyectar campos del catálogo propio (argentina_compatible, withdrawal_verified, payout_verified, min_payment_usd, max_payment_usd, payment_crypto, payment_bank_transfer, payment_paypal) en una Opportunity existente falla con:

```
AttributeError: 'Opportunity' object has no attribute 'argentina_compatible' and no __dict__ for setting new attributes
```

**Consecuencia:** El catálogo propio mantiene su información en su propio espacio (OwnWorkSourceDefinition, OwnWorkExtensionCatalog) y NO la pierde. El motor DWE no recibe campos del catálogo propio porque no existen en Opportunity. Si un adaptador intenta inyectar campos del catálogo propio en Opportunity, la operación fallará con AttributeError.

**Campos que SÍ se inyectan correctamente (existen en Opportunity):**

- `platform` (WorkPlatform enum) — override opcional vía `_create_opportunity(platform=...)` solo cuando `_platform_for_source` mapea; si no hay mapeo, queda `DiscoverySource.platform`.
- `category` (OpportunityCategory enum) — inyectado via `_category_for_source`.
- `payment_method` (PaymentMethod enum) — inyectado via `_payment_method_for_source`.
- `employment_type` (EmploymentType enum) — corrección post-creación porque `_create_opportunity` no lo expone como parámetro.
- `entry_mechanism` (EntryMechanism enum) — inyectado via `_entry_mechanism_for_source`.
- `international_payment` (bool | None) — inyectado via `_international_payment_for_source` (explicit catalog field wins; si no, heurística de `region`).
- `experience_requirement` (ExperienceRequirement enum) — inyectado via `_experience_requirement_for_source`.
- `rate_source` (str: "catalog") — inyectado directamente en `_build_opportunity`.
- `technology_tags` (list[str]) — inyectado via `_technology_tags_for_source` (`technology_tags` primero, luego `tags`).

Los campos Hermes extras (`heuristics_analyzed`, `analysis_complete`, `cached_analysis`, `analysis_revision`, `analysis_started_at`) NO existen en `Opportunity` y NO se inyectan; los tests del adaptador Hermes verifican `not hasattr(opp, ...)`. Permanecen en la fuente de catálogo.

**Campos que NO se inyectan porque NO existen en Opportunity (permanecen en catálogo):**

- `payment_verified` (bool)
- `payout_verified` (bool)
- `argentina_compatible` (bool)
- `withdrawal_verified` (bool)
- `min_payment_usd` (float)
- `max_payment_usd` (float)
- `payment_crypto` (str)
- `payment_bank_transfer` (str)
- `payment_paypal` (str)

Estos campos se mantienen en el catálogo propio (OwnWorkSourceDefinition, OwnWorkExtensionCatalog) y NO se pierden porque NO se inyectan en Opportunity.

5. Considerar fuentes de extensión segunda ola para mapeo de plataforma (si las plataformas become available en WorkPlatform).
6. Documentar decisión de registro en este archivo.
