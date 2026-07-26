# Lessons — Lecciones Aprendidas del Desarrollo

> Registro de lecciones duras, anti-patrones descubiertos, y cosas que costaron caro aprender. No repetir errores.

## Arquitectura

### 1. `nohup` no es suficiente para procesos hijos longevos

El FCC Proxy se moría espontáneamente. Tras horas de debugging, la causa era simple: OpenCode lanza Bash tools con timeout. Al expirar el timeout, el shell recibe SIGTERM. `nohup` bloquea SIGHUP pero no SIGTERM. uvicorn tiene un handler de SIGTERM que hace shutdown clean.

**Solución**: `setsid -w` crea un nuevo process group que no recibe señales del padre. Es inmune a SIGTERM del timeout de la tool.

**Archivos tocados**: `~/start_proxy.sh`

---

### 2. Los bugs de integración vienen en racimos de 3

La integración Hermes + FCC Proxy falló con HTTP 404. Causa raíz: tres errores independientes y simultáneos:

1. `provider: github-copilot` → Hermes usaba formato OpenAI, FCC sirve Anthropic Messages API
2. `base_url: http://localhost:8082/v1` → El SDK Anthropic añade `/v1/messages`, resultando en `.../v1/v1/messages`
3. `model: gpt-5.4` → No existe en ningún catálogo

**Lección**: Cuando un sistema no funciona y el error es genérico (404), sospechar que hay **múltiples causas simultáneas**. Arreglar una sola no resuelve el síntoma.

---

### 3. La seguridad por derivación (machine-id) es peor que la aleatoriedad

IdentityVault original derivaba la clave AES de `/etc/machine-id`. Archivo world-readable. Cualquier usuario local podía descifrar la bóveda.

**Solución**: `secrets.token_bytes(32)` + archivo con chmod 600. Simple, correcto, auditable.

**Lección**: No usar "identificadores del sistema" como secretos criptográficos.

---

### 4. Siempre verificar que el sentinel y el guard están en el mismo proceso

El proxy lock (`~/.orion/proxy_mode`) existía como archivo de señal para bash scripts. Pero Hermes no lo leía. Cada vez que el usuario cambiaba de modelo, Hermes resolvía el nombre contra OpenRouter, cambiaba provider silenciosamente, y perdía el proxy.

**Solución**: Agregar `_is_proxy_locked()` en el código de Hermes que lee el mismo archivo. El guard debe estar en el proceso que ejecuta la acción, no en un script externo.

**Patrón**: Sentinel file + in-process guard. El sentinel es compartido, el guard está donde se ejecuta la decisión.

---

### 5. sessionStorage > localStorage, pero ambos son mitigaciones temporales

Mover API keys de localStorage a sessionStorage evita exfiltración vía XSS persistentes. Pero sigue siendo almacenamiento del lado del cliente.

**Solución permanente**: IdentityVault en backend con endpoints de API para gestionar keys. Las keys nunca llegan al frontend.

---

## Desarrollo

### 6. La memoria sin un consumidor es un cementerio de datos

UnifiedMemoryStore tiene columna `embedding` desde el día 1. Nadie la usa. Agregar búsqueda semántica ahora requeriría ~50 líneas de numpy + Ollama embeddings API, pero **no hay ningún agente preguntando semánticamente**.

**Lección**: No construir infraestructura de memoria hasta que haya un consumidor real. El schema-ready está bien. La implementación completa, no.

**Corolario**: `.ai/*.md` documental es más útil hoy que 1000 entradas en una vector DB que nadie consulta.

---

### 7. El router crece en proporción inversa a la disciplina

El frontend pasó de ~50 rutas planas en un solo archivo de 483 líneas a 8 secciones jerárquicas. El router plano era insostenible: agregar una página nueva requería escanear 483 líneas para encontrar dónde ponerla.

**Solución**: Router anidado por sección + 79 redirecciones de legacy. Cualquier ruta nueva es un child en la sección correspondiente.

**Lección**: La navegación es arquitectura, no cosmética. Invertir temprano.

---

### 8. 80% del valor está en los últimos 20% de conexión

El Hypothesis Challenger estaba ~80% implementado: generaba explicaciones alternativas, diseñaba tests de contradicción, calculaba incertidumbre. Pero los contradiction_tests nunca se ejecutaban. El sistema explicitaba dudas sin resolverlas.

**Lección**: Una feature al 80% que no está conectada al flujo principal no produce valor. Preferir 3 features 100% conectadas sobre 10 al 80%.

---

### 9. El cooldown previene más bugs que cualquier validación

El scheduler ejecutaba scans a intervalos fijos sin memoria de lo escaneado. Targets de alto ROI se escaneaban 10 veces por hora; targets nuevos morían de hambre.

**Solución**: Cooldown de 1h por target + priorización por RewardLearner.

**Lección**: La contención (rate limiting, cooldown, backpressure) es más importante que la optimización. Un sistema sin contención es un sistema que se autodestruye.

---

### 10. Siempre migrar, nunca romper

La decisión de migrar licencias de HMAC-SHA256 a Ed25519 fue correcta, pero las licencias HMAC antiguas no eran compatibles.

**Lección menor**: Quemar puentes criptográficos tiene costo real. La migración automática (clave machine-id → random, sin pérdida de vaults existentes) es el patrón correcto.

---

### 11. Los 404 casi nunca significan "no encontrado"

En sistemas con proxies, routers y múltiples providers, un 404 suele significar:
- El endpoint no existe (ruta mal configurada)
- El provider espera otro formato de API
- La URL se duplicó (v1/v1/messages)
- El modelo no existe
- La autenticación falló silenciosamente

**Lección**: DEBUGGEAR POR CAPAS. 1) ¿El servicio responde? 2) ¿El formato es correcto? 3) ¿La ruta? 4) ¿El modelo? 5) ¿La auth? En ese orden.

---

### 12. Consolidación > Expansión

El mayor salto de calidad del frontend no fue agregar una feature. Fue reducir 5 páginas de revenue a 1 con tabs. Menos código, menos estados inconsistentes, menos bugs.

**Lección**: Si una mejora requiere eliminar código en lugar de agregarlo, probablemente es la mejora correcta.
