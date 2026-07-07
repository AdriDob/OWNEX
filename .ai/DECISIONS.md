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

## 2026-07-06: API keys del frontend separadas a sessionStorage

- **Problema**: API keys (openai, gemini, wallet, bank) almacenadas en localStorage, exfiltrables via XSS.
- **Alternativas consideradas**:
  1. **sessionStorage (elegido)** — Se limpia al cerrar pestaña. Mitigación parcial.
  2. Backend IdentityVault — La solución correcta pero requiere cambios de API
  3. No cambiar — Riesgo continuo
- **Decisión**: Mover API keys a sessionStorage como mitigación temporal. La solución permanente es almacenarlas en el backend via IdentityVault.
- **Impacto**: Las keys sobreviven refrescos de página pero no a nuevas pestañas.
- **Condiciones para reabrir**: Inmediatamente — esta es una solución temporal. La solución definitiva requiere endpoints de API para gestionar keys.
