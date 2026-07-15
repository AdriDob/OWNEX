# Decisions — Registro de Decisiones Arquitectónicas

## 2026-07-06: Ed25519 para licencias

- **Problema**: El sistema de licencias usaba HMAC-SHA256 con una clave hardcodeada en el código fuente. Cualquier persona con acceso al binario podía forjar licencias.
- **Alternativas consideradas**:
  1. RSA-2048 — Claves grandes (512 bytes), dependencia de openssl CLI
  2. ECDSA P-256 — Buen tamaño pero más complejo de implementar
  3. **Ed25519 (elegido)** — Claves pequeñas (32 bytes públicas), verificación rápida, sin dependencias externas
- **Decisión**: Ed25519. Clave pública embebida en el binario, clave privada en servidor de licencias.
- **Impacto**: 
  - Formato de licencia: 25 caracteres (sin cambios en UX)
  - Firma completa almacenada en license.json (64 bytes base64)
  - Migración: licencias HMAC antiguas no son compatibles (deben re-generarse)
- **Condiciones para reabrir**: Si se demuestra que Ed25519 tiene una vulnerabilidad criptográfica.

## 2026-07-06: Clave AES aleatoria en archivo para IdentityVault

- **Problema**: La clave AES se derivaba de `/etc/machine-id`, que es world-readable. Cualquier usuario local podía descifrar la bóveda.
- **Alternativas consideradas**:
  1. **Clave aleatoria en archivo (elegido)** — Generada con `secrets.token_bytes(32)`, chmod 600
  2. Master password + Argon2id — Más seguro pero requiere UX para pedir contraseña
  3. TPM/secure enclave — No portable entre plataformas
- **Decisión**: Clave aleatoria en archivo. El archivo se crea con permisos 600. Migración automática desde vaults existentes.
- **Impacto**: 
  - Bóvedas existentes se migran automáticamente en el primer acceso
  - La clave sobrevive reinicios (persistente en disco)
  - Master password no implementado (pendiente para futura versión)
- **Condiciones para reabrir**: Si se requiere proteger contra acceso root.

## 2026-07-06: Doble-submit cookie para CSRF

- **Problema**: No existía protección CSRF en la API.
- **Alternativas consideradas**:
  1. **Doble-submit cookie (elegido)** — Token en cookie + header. Sin estado en servidor.
  2. CSRF token con sesión — Requiere store server-side
  3. SameSite=Strict — Insuficiente para cross-origin legítimos
- **Decisión**: Doble-submit cookie. Token criptográficamente aleatorio en cookie httponly, mismo token en header X-CSRF-Token.
- **Impacto**:
  - Middleware global con excepciones para endpoints públicos
  - Deshabilitado en dev mode (CATEYE_DESKTOP no configurado)
  - GET requests setean la cookie automáticamente
- **Condiciones para reabrir**: Si se encuentra un bypass del patrón double-submit.

## 2026-07-06: Scheduler adaptativo con cooldown

- **Problema**: El scheduler ejecutaba scans a intervalos fijos sin considerar si un target ya fue escaneado recientemente o si tiene baja prioridad.
- **Alternativas consideradas**:
  1. **Cooldown por target + priorización (elegido)** — Saltar targets escaneados hace < 1 hora, ordenar por prioridad RewardLearner
  2. Intervalos fijos (original) — Simple pero ineficiente
  3. Cola de prioridad con backpressure — Más complejo, mejor para escala
- **Decisión**: Cooldown de 1 hora por target + ordenamiento por prioridad (ajustes de RewardLearner).
- **Impacto**:
  - Targets de alto ROI se escanean primero
  - Targets recién escaneados no se repiten
  - Compatible hacia atrás: misma API
- **Condiciones para reabrir**: Si el número de targets supera ~1000 y se necesita backpressure.

## 2026-07-06: .ai/ como fuente de verdad única

- **Problema**: La documentación del proyecto estaba dispersa en 16 archivos .md en la raíz, sin estructura ni consistencia.
- **Alternativas consideradas**:
  1. **Directorio .ai/ dedicado (elegido)** — Un solo lugar para toda la documentación operativa
  2. Wiki externa — Requiere conexión, fuera del repo
  3. Mantener documentación dispersa — Status quo insostenible
- **Decisión**: .ai/ contiene toda la documentación operativa. Los archivos existentes se consolidan progresivamente.
- **Impacto**:
  - Cualquier agente (OpenCode, Cline, Copilot) tiene un solo lugar que leer
  - Documentación versionada con el código
  - OpenCode configurado via `instructions` + `references`
  - Cline configurado via `.cline/rules/` que referencia .ai/
- **Condiciones para reabrir**: Si las herramientas de IA soportan un mecanismo mejor que archivos locales.

## 2026-07-06: opencode.json estabilizado a formato mínimo válido

- **Problema**: opencode.json.save contenía formato corrupto (2 JSONs concatenados) con campos no soportados (`references`, `instructions` como objetos). OpenCode rechazaba el schema.
- **Alternativas consideradas**:
  1. **Formato mínimo válido (elegido)** — Solo `instructions` array de strings. Sin `$schema` si no es verificado.
  2. Mantener `references` — No soportado por OpenCode, causa errores de schema.
  3. Migrar toda la config a Cline — Perdería integración con OpenCode.
- **Decisión**: opencode.json contiene solo `instructions` array con paths a `.ai/`. No hay lógica duplicada. `.ai/` es la única fuente de verdad.
- **Impacto**:
  - opencode.json.save eliminado
  - OpenCode referencia exclusivamente `.ai/` + skill
  - Sin campos inválidos ni estructuras no soportadas
  - Sistema listo para evolución incremental sin corrupción de config
- **Condiciones para reabrir**: Si OpenCode agrega soporte nativo para `references` o estructura de objetos en `instructions`.

## 2026-07-09: Auditoría de validación — documentar, no implementar antes del release

- **Problema**: El motor de validación no refuta hipótesis, no evalúa explicaciones alternativas, no aprende de falsos positivos.
- **Alternativas consideradas**:
  1. **Documentar limitaciones y posponer (elegido)** — Crear KNOWN_LIMITATIONS.md, agregar deuda a KNOWN_DEBT.md, mover mejoras a v3.1
  2. Implementar detección de recursos públicos + campo uncertainties — Mejora parcial pero aumenta alcance del release
  3. Reescritura del pipeline de validación — Violaría DO-NOT-TOUCH, aumenta complejidad
- **Decisión**: Cerrar v3.0.0 con el pipeline actual. Las mejoras de razonamiento son para v3.1 (ORION Reasoning Layer).
- **Impacto**:
  - Los findings automatizados requieren revisión humana (ya documentado)
  - El pipeline actual es honesto sobre sus limitaciones
  - Los falsos positivos siguen siendo responsabilidad del humano
- **Condiciones para reabrir**: Cuando se inicie v3.1.

## 2026-07-06: API keys del frontend separadas a sessionStorage

- **Problema**: API keys (openai, gemini, wallet, bank) almacenadas en localStorage, exfiltrables via XSS.
- **Alternativas consideradas**:
  1. **sessionStorage (elegido)** — Se limpia al cerrar pestaña. Mitigación parcial.
  2. Backend IdentityVault — La solución correcta pero requiere cambios de API
  3. No cambiar — Riesgo continuo
- **Decisión**: Mover API keys a sessionStorage como mitigación temporal. La solución permanente es almacenarlas en el backend via IdentityVault.
- **Impacto**: Las keys sobreviven refrescos de página pero no a nuevas pestañas.
- **Condiciones para reabrir**: Inmediatamente — esta es una solución temporal. La solución definitiva requiere endpoints de API para gestionar keys.

## 2026-07-09: ORION Hypothesis Challenger — razonamiento previo a validación

- **Problema**: El pipeline de validación ejecutaba hipótesis sin cuestionarlas. No consideraba explicaciones alternativas, no diseñaba contrapruebas, no explicitaba qué no se verificó. El sistema razonaba linealmente (hipótesis → validar → decidir) en vez de cíclicamente (hipótesis → cuestionar → diseñar contraprueba → validar → reinterpretar).
- **Alternativas consideradas**:
  1. **HypothesisChallenger como capa insertada (elegido)** — ~250 líneas nuevas, 0 regresiones, 393 tests pasan. Se inserta entre HypothesisEngine y ValidationLoopEngine. No modifica replayer, rules, ni hypothesis generators.
  2. Refactor del pipeline completo — Violaría DO_NOT_TOUCH (replayer/rules estables). Riesgo alto.
  3. Solo documentar — Deuda existente en KNOWN_DEBT.md, pero la implementación era directa y bajo riesgo.
- **Decisión**: Insertar HypothesisChallenger en loop_engine.evaluate(). El challenger genera alternative_explanations, contradiction_tests con info_gain, missing_verifications, y uncertainty_level antes de la validación. El uncertainty_level se traduce a uncertainty_penalty (0.0–0.12) que descuenta del confidence score.
- **Impacto**:
  - Los reportes ahora incluyen "falta verificar X, considerar Y como explicación alternativa"
  - El confidence score refleja incertidumbre no resuelta (penalización)
  - El humano ve qué no se verificó, no solo el score final
  - 0 regresiones: el parámetro vulnerability_type tiene default "unknown" que da genéricos
- **Condiciones para reabrir**: Si se necesita que el Challenger ejecute los contradiction_tests automáticamente (hoy solo los diseña y recomienda). Eso requiere integrar con replayer como mutaciones adicionales.

## 2026-07-11: RC1 — De construir a operar

- **Problema**: ORION había acumulado 12+ dominios funcionales (Core, CATEYE, ATLAS, ODYSSEY, HERMES, AEGIS, Copilot, Companion, Workflows, Unified Memory, Health Center, Mission Control). El instinto natural era seguir agregando módulos. Sin embargo, el sistema ya cubre todo el flujo diario del usuario.
- **Alternativas consideradas**:
  1. **Congelar desarrollo, operar durante semanas reales (elegido)** — El mayor valor no viene de nuevas features sino de confiar en el sistema durante uso real continuo. Medir por indicadores operativos (días sin incidentes, tiempo hasta revisar MC < 1 minuto, clics reducidos).
  2. Seguir agregando módulos — Aumenta complejidad sin cerrar loops funcionales. Infla el proyecto sin validar lo existente.
  3. Time Machine / Sandbox / Observatorio — Ideas valiosas para RC2/RC3, no para RC1. Implementar ahora distrae de la validación operativa.
- **Decisión**: RC1 congelado. No se escribe una línea de código nuevo que no sea corrección de bug, seguridad o rendimiento. El proyecto entra en fase operativa mínima 2-4 semanas. Después se evalúa qué mejoras (solo Time Machine, Sandbox, Observatorio) justifican RC2.
- **Impacto**:
  - El usuario pasa de "operador manual" a "estratega" — solo decide, prioriza, aprueba, descarta
  - El sistema se evalúa por resultados observables (dinero generado, tiempo ahorrado, automatizaciones ejecutadas), no por cantidad de código
  - ORION se convierte en un "sistema operativo de trabajo" que envejece bien
- **Filosofía registrada**: ORION no crece por expansión. Crece por consolidación. Cada clic innecesario que desaparece vale más que veinte features nuevas. Dentro de 5 años ORION funciona no por sus miles de líneas sino porque tiene configuración portable, backups, export/import, plugins, mantenimiento, rollback, auditoría, Health Center, Update Manager y Mission Control.
