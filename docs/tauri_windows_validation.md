# Tauri Windows Installer Validation Checklist

Este documento describe los pasos para validar manualmente el instalador Tauri/OWNEX en una máquina Windows.

## Requisitos previos
- Windows 10/11 con sesión de usuario (NO usar WSL para la validación GUI).
- Permisos de instalación (Run as Administrator cuando sea necesario).
- Herramientas recomendadas: PowerShell (Admin), `Get-FileHash` o `sha256sum`.

## Pasos de validación

1. Descargar el instalador (MSI o EXE) generado por CI y verificar su checksum:

```powershell
Get-FileHash .\OWNEX-Installer.msi -Algorithm SHA256
```

2. Ejecutar el instalador en modo interactivo (elevado si es necesario):

```powershell
Start-Process -FilePath .\OWNEX-Installer.msi -Wait -Verb RunAs
```

3. Abrir la app (OWNEX Desktop) desde el menú Inicio o acceso directo creado.

4. Verificar que la GUI arranca y no muestra errores fatales al iniciar.

5. Verificar que el sidecar/backend se inicia (por defecto en `http://127.0.0.1:8000`) y responde al endpoint de health:

```powershell
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/health -UseBasicParsing
```

6. Verificar que el directorio de datos del usuario fue creado y contiene la base de datos:

- Ruta típica: `%LOCALAPPDATA%\OWNEX\database\catseye.db`

7. Ejecutar un check básico de API: crear y listar un `target`:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/targets -Body (@{name='test'; domain='example.com'} | ConvertTo-Json) -ContentType 'application/json'
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/targets
```

8. Revisar logs del sidecar en `%LOCALAPPDATA%\OWNEX\logs` y confirmar que no hay tracebacks fatales ni errores de DB.

9. Cerrar la app y reiniciarla; confirmar que la base de datos persiste y que la app reanuda sin recrear esquemas.

10. (Opcional) Ejecutar el runner E2E incluido (si aplica) o lanzar `python scripts/debug_worker_e2e.py` dentro de un entorno Python con las dependencias necesarias para generar checkpoints/audit.

## Resultados esperados mínimos
- `GET /api/health` → HTTP 200 JSON.
- App GUI abre sin crash.
- `catseye.db` creado en carpeta de datos del usuario.
- API POST/GET funcional para `targets`.
- Logs sin tracebacks fatales.

## Anexos
- Si se detecta un fallo crítico (crash del backend, DB no creada, tracebacks), recopilar:
  - `%LOCALAPPDATA%\OWNEX\logs\*.log`
  - Screenshot de la ventana y del error
  - Output de `Get-FileHash` del instalador

Guardar la evidencia en un zip y subirla al PR como artifact.
