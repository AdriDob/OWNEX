Title: Validación instalador Windows — Tauri

Relación: PR #37 — `feat/phase0-foundation`

Descripción:
Sigue esta guía para validar el instalador Tauri en Windows y recoger evidencia requerida antes de promover a RC.

Pasos para el validador:
1. Descargar el artefacto instalador desde la última build (o usar el `dist` generado localmente).
2. Verificar checksum SHA256 del instalador.
3. Instalar en Windows como usuario estándar y como admin (si procede).
4. Verificar que la app arranca y que la API está disponible en `http://127.0.0.1:8000/api/health`.
5. Comprobar que la base de datos local existe en `%LOCALAPPDATA%\OWNEX\database\catseye.db` y tiene las tablas esperadas.
6. Ejecutar las siguientes comprobaciones rápidas contra la API:
   - `GET /api/targets` → 200
   - `POST /api/targets` con payload de prueba → 201 (y revisar DB)
   - `GET /api/system/status` → 200 (o endpoint equivalente según build)
7. Ejecutar el cliente desktop y revisar logs en `%LOCALAPPDATA%\OWNEX\logs`.
8. Adjuntar los logs y capturas de pantalla en este issue o en el PR #37.

Checklist de evidencia a adjuntar:
- Captura del checksum verificado
- Captura de la instalación exitosa
- `curl` outputs de los endpoints de health y targets
- Archivo `catseye.db` (opcional) o volcado `sqlite3 .dump`
- Logs del directorio `%LOCALAPPDATA%\OWNEX\logs`

Notas de seguridad:
- Si ocurre un error de migración DB, no sobrescribir el archivo `catseye.db` de producción.

Asignar a: @qa-team, @AdriDob
