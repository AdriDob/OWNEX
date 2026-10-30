# Credential Vault Security Audit — OWNEX

## Fecha: 2026-10-20

## Arquitectura actual

### Archivos involucrados
- `cores/vault_crypto.py` — AES-256-GCM encryption, key file management
- `cores/identity_vault.py` — Credential storage (encrypted at rest)

### Directorios
- **Linux/WSL**: `~/.ownex/vault/` (key + data)
- **Windows**: `%LOCALAPPDATA%\OWNEX\vault\` (key + data)

### Archivos
- `identity_vault.key` — 32 bytes (AES-256 key), raw binary
- `identity_vault.json` — Encrypted credentials, JSON format

### Algoritmo
- AES-256-GCM (authenticated encryption)
- Nonce: 12 bytes (os.urandom)
- Tag: 16 bytes (GCM authentication tag)
- Key: 32 bytes (secrets.token_bytes(32))

## Hallazgos de seguridad

### 1. Clave y datos en el mismo directorio
**Riesgo**: Si un atacante obtiene acceso al directorio, obtiene tanto la clave como los datos cifrados.
**Impacto**: Compromiso total de las credenciales.
**Mitigación actual**: chmod 600 (Linux only, no-op en Windows).

### 2. Sin protección OS-level en Windows
**Riesgo**: Windows no usa chmod. Los archivos son accesibles por cualquier usuario con acceso al directorio.
**Impacto**: Cualquier proceso o usuario en la máquina puede leer la clave y descifrar los datos.
**Mitigación actual**: Ninguna en Windows.

### 3. Sin DPAPI ni almacén seguro
**Riesgo**: La clave se almacena en texto plano en disco.
**Impacto**: Si el disco se compromete (robo, backup, etc.), las credenciales son accesibles.
**Mitigación actual**: Ninguna.

### 4. Key regeneration risk
**Riesgo**: Si `identity_vault.key` se pierde o corrompe, `get_vault_key()` genera una nueva clave, haciendo ilegibles todos los datos existentes.
**Impacto**: Pérdida permanente de credenciales.
**Mitigación actual**: Ninguna (no hay backup de la clave).

### 5. Sin rotación de claves
**Riesgo**: La clave nunca se rota.
**Impacto**: Si la clave se compromete, todas las credenciales históricas están comprometidas.
**Mitigación actual**: Ninguna.

## Recomendaciones

### Prioridad 1 (antes de distribuir en Windows)
1. **Implementar DPAPI en Windows** para proteger la clave AES-256 en reposo.
   - Usar `CryptProtectData` / `CryptUnprotectData` de Windows API
   - Fallback: si DPAPI no está disponible, usar la clave de archivo actual
   - Mantener compatibilidad con datos existentes (migración transparente)

2. **Separar clave y datos** en directorios diferentes (defensa en profundidad).
   - Clave: `%LOCALAPPDATA%\OWNEX\vault\key\identity_vault.key`
   - Datos: `%LOCALAPPDATA%\OWNEX\vault\data\identity_vault.json`

3. **Agregar backup de clave** (encriptado con DPAPI o contraseña del usuario).

### Prioridad 2 (mejora de seguridad)
4. **Rotación de claves** con re-encriptación de datos existentes.
5. **Auditoría de acceso** (log de cuándo se accede a credenciales).
6. **Timeout de sesión** (limpiar clave de memoria después de N minutos).

### Prioridad 3 (nice-to-have)
7. **Integración con Windows Credential Manager** como alternativa a archivo.
8. **Soporte para hardware security keys** (YubiKey, etc.).

## Plan de implementación (NO implementado aún)

1. **Fase A**: Implementar DPAPI wrapper en `cores/vault_crypto.py`
   - Función `protect_key(key: bytes) -> bytes` usando CryptProtectData
   - Función `unprotect_key(protected: bytes) -> bytes` usando CryptUnprotectData
   - Fallback a clave de archivo si DPAPI no disponible

2. **Fase B**: Migración transparente
   - Al leer la clave, intentar DPAPI primero
   - Si falla, intentar clave de archivo
   - Si ninguna funciona, generar nueva clave
   - Re-encriptar datos con nueva clave si hubo migración

3. **Fase C**: Tests de seguridad
   - Verificar que la clave no es legible por otros usuarios
   - Verificar que DPAPI protege correctamente
   - Verificar compatibilidad con datos existentes
   - Verificar recuperación ante pérdida de clave

## Estado actual: NO IMPLEMENTADO

El vault actual almacena la clave AES-256 en texto plano en disco. En Windows, sin DPAPI ni ACLs, cualquier usuario o proceso puede leer la clave y descifrar los datos.

**Riesgo**: ALTO en Windows (sin protección OS-level)
**Riesgo**: MEDIO en Linux (chmod 600 protege contra otros usuarios, pero no contra root o acceso físico)

## Recomendación

Implementar DPAPI en Windows antes de distribuir OWNEX. No es un cambio trivial y requiere:
- ctypes o pywin32 para CryptProtectData/CryptUnprotectData
- Tests de compatibilidad con datos existentes
- Plan de migración y recuperación
- Documentación para el usuario

**No implementar sin pruebas exhaustivas.**
