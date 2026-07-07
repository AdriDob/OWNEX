# Security Policy — Política de Seguridad

## Vulnerabilidades Conocidas y Resueltas

### CVE-1: HMAC hardcode en license validator (RESUELTO)
- **Archivo**: `cores/license/validator.py`
- **Riesgo**: Cualquier persona con acceso al código fuente podía forjar licencias
- **Solución**: Reemplazado por Ed25519 asimétrico. Clave pública embebida (segura), clave privada en servidor de licencias.
- **Verificación**: Todos los tests de licencia pasan. No hay secretos HMAC en el código.

### CVE-2: Clave AES derivada de /etc/machine-id (RESUELTO)
- **Archivo**: `cores/identity_vault.py`
- **Riesgo**: Cualquier usuario local podía leer /etc/machine-id y descifrar la bóveda
- **Solución**: Clave AES-256 aleatoria generada con `secrets.token_bytes(32)`, almacenada en `~/.orion/identity_vault.key` (chmod 600). Migración automática desde vaults existentes.
- **Verificación**: Tests pasan. No hay referencias a machine-id en la derivación de clave.

### CVE-3: Tokens y sesiones en JSON plano (RESUELTO)
- **Archivos**: `cores/auth/token_service.py`, `cores/auth/session.py`
- **Riesgo**: Cualquier usuario local podía leer tokens de acceso
- **Solución**: Archivos cifrados con AES-256-GCM via `cores/vault_crypto.py`
- **Verificación**: Tests pasan. Archivos en disco son binarios cifrados.

### CVE-4: Sin protección CSRF (RESUELTO)
- **Archivo**: `api/middleware/csrf_middleware.py`
- **Riesgo**: Un atacante podía ejecutar acciones en nombre de un usuario autenticado
- **Solución**: Middleware CSRF con patrón double-submit cookie. Token en cookie + header X-CSRF-Token.
- **Verificación**: Middleware activo en producción. Deshabilitado en dev (CATEYE_DESKTOP no configurado).

### CVE-5: OAuth2 Gmail sin state (RESUELTO)
- **Archivo**: `cores/authhub/gmail.py`
- **Riesgo**: CSRF en callback OAuth2
- **Solución**: Generación de state token criptográficamente aleatorio en authorize_url(), verificación en exchange_code().
- **Verificación**: Tests pasan. El parámetro state es obligatorio.

### CVE-6: Fuga de excepciones (RESUELTO)
- **Archivo**: `api/middleware/error_handling.py`
- **Riesgo**: Mensajes de excepción internos expuestos en HTTP response
- **Solución**: Mensaje genérico "An unexpected error occurred". Excepción completa en log server-side.
- **Verificación**: Tests pasan. No hay referencias a `{e}` en la respuesta.

### CVE-7: CORS allow_credentials + wildcard (RESUELTO)
- **Archivo**: `api/main.py`
- **Riesgo**: Configuración inválida según Fetch spec, potencial fuga de cookies
- **Solución**: `allow_credentials=True` solo cuando `allow_origins` es específica. En dev mode, `allow_credentials=False`.
- **Verificación**: Tests pasan. Configuración separada por modo.

### CVE-8: Sin auditoría de seguridad (RESUELTO)
- **Archivo**: `cores/audit_log.py`
- **Riesgo**: Sin registro de eventos de autenticación, imposible forensica
- **Solución**: Audit log persistente en `~/.orion/audit.jsonl` (JSONL, append-only, chmod 600). Eventos registrados: login, logout, token_stored.
- **Verificación**: Tests pasan. Log contiene eventos de autenticación.

## Políticas de Seguridad para Desarrollo

1. **No hardcodear secretos**: Usar variables de entorno o IdentityVault.
2. **Cifrar datos sensibles en disco**: AES-256-GCM con clave aleatoria.
3. **CSRF en todas las rutas mutantes**: Middleware global con excepciones mínimas.
4. **OAuth2 state en todas las integraciones**: Verificar state en callback.
5. **No exponer detalles internos**: Errores genéricos al cliente, log completo al server.
6. **CORS restrictivo**: Orígenes específicos en producción.
7. **Auditar eventos de seguridad**: login, logout, token management.
8. **Rate limiting por identity**: No solo por IP.

## Vulnerabilidades No Verificadas

Las siguientes áreas NO han sido auditadas para seguridad:
- Frontend (XSS, CSP headers) — solo se revisó localStorage
- Mobile y Android
- Instaladores (Windows NSIS, Linux)
- Dependencias third-party (npm, pip)
