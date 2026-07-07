# Do Not Touch — Componentes Estables

> **ADVERTENCIA**: Antes de modificar cualquiera de estos componentes, debes tener una justificación técnica clara documentada en DECISIONS.md.
>
> Cada entrada incluye evidencia de por qué es estable y el riesgo de modificarlo.

## Licencia: Validator + Store

- **Archivos**: `cores/license/validator.py`, `cores/license/store.py`
- **Estado**: Production Ready
- **Evidencia**: 
  - 355 tests pasan
  - Cifrado Ed25519 implementado y verificado
  - Formato de 25 caracteres preservado
  - HW binding implementado
- **Motivo**: Sistema de licencias crítico para el modelo de negocio. Cualquier error puede dejar el producto inaccesible.
- **Riesgo de modificar**: Alto — puede romper licencias existentes.

## IdentityVault

- **Archivos**: `cores/identity_vault.py`, `cores/vault_crypto.py`
- **Estado**: Stable
- **Evidencia**:
  - 355 tests pasan
  - Cifrado AES-256-GCM implementado y verificado
  - Migración automática desde machine-id
  - Clave aleatoria con chmod 600
  - Usado por auth, crypto, financial modules
- **Motivo**: Bóveda de credenciales central. Cualquier error expone secrets.
- **Riesgo de modificar**: Alto — puede exponer credenciales o perder acceso a cuentas.

## Auth: TokenService + SessionStore

- **Archivos**: `cores/auth/token_service.py`, `cores/auth/session.py`
- **Estado**: Stable
- **Evidencia**:
  - 355 tests pasan
  - Cifrado AES-256-GCM en disco
  - Sesiones con device binding
- **Motivo**: Gestión de sesiones crítica para autenticación.
- **Riesgo de modificar**: Alto — puede dejar a usuarios sin acceso.

## CSRF Middleware

- **Archivos**: `api/middleware/csrf_middleware.py`
- **Estado**: Production Ready
- **Evidencia**:
  - Middleware activo en producción
  - Double-submit cookie implementado
  - Excepciones mínimas para endpoints públicos
- **Motivo**: Protección CSRF esencial para seguridad API.
- **Riesgo de modificar**: Medio — puede introducir falsos positivos (403) o bypass de seguridad.

## Error Handling Middleware

- **Archivos**: `api/middleware/error_handling.py`
- **Estado**: Production Ready
- **Evidencia**:
  - Sin fuga de excepciones
  - Logging server-side completo
- **Motivo**: Seguridad de información.
- **Riesgo de modificar**: Bajo — cambios controlados.

## Audit Log

- **Archivos**: `cores/audit_log.py`
- **Estado**: Stable
- **Evidencia**:
  - JSONL persistente con chmod 600
  - Eventos: login, logout, token_stored
- **Motivo**: Trazabilidad de seguridad.
- **Riesgo de modificar**: Bajo.

## Nota sobre componentes no listados

Los componentes NO listados aquí no han sido verificados como estables. Pueden contener bugs, deuda técnica, o vulnerabilidades. Revisar antes de modificar.
