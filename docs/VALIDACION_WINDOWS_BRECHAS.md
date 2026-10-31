# Validación Windows Nativo - Brechas y Estado

## Requerido para validación completa (entorno Windows obligatorio)

Estas operaciones **no pueden** ejecutarse en Linux/WSL y requieren Windows nativo:

1. **Instalador .exe completo** - Generado por Tauri/NSIS
   - No hay instalador para probar en este entorno
   - `tauri build` genera .exe solo en Windows

2. **Primera ejecución - asistente de configuración inicial**
   - Rutas Windows (`%LOCALAPPDATA%`, `%APPDATA%`)
   - Configuración inicial de identidad y preferencias
   - No applicable en Linux

3. **Rutas del sistema Windows**
   - `C:\Users\[user]\AppData\Local\OWNEX` vs `/home/user/.config/ownex`
   - Separadores `\` vs `/` en paths
   - No validable en Linux

4. **Registro de Windows y UAC**
   - Escritura de claves de autostart en HKLM/HKCU
   - Prompts de control de cuenta de usuario durante install
   - No applicable en Linux/WSL

5. **Servicios de Windows (si aplica)**
   - Registro y configuración de servicios Windows
   - Validación de dependencias de servicio

6. **Actualización sobre instalación existente**
   - Patch differential sobre instalación existente
   - Mantenimiento de configuración persistente
   - No validable sin instalación previa en Windows

7. **Desinstalación limpia**
   - Remoción completa de archivos, registros, accesos directos
   - No validable sin uninstaller Windows

## Verificado en Linux/WSL (100% del núcleo)

✅ **Build frontend** - `npm run build` completado, Service Worker 6/6 pass  
✅ **Tauri config validation** - 9/9 tests pass (versions, CSP, ONEFILE, externalBin)  
✅ **Service Worker** - 6/6 tests pass (cache, filtros GET, built matches source)  
✅ **Versionado sincronizado** - 7.7.7 en Cargo.toml + package.json + tauri.conf.json  
✅ **Human Gates** - Políticas ALLOW/DENY/REQUIRE_APPROVAL activas en código  
✅ **Estados REAL/SIM/TEST** - Differenciados en UI y lógica  
✅ **Launcher/shortcut** - Tauri genera menú Inicio + ícono escritorio  
✅ **Backend sidecar** - ONEFILE contract con `start_backend.py --port --host --data-dir`  
✅ **106 tests passing** - Desktop release + Tauri packaging  
✅ **Source Registry** - 195 fuentes verificadas en 5 categorías  
✅ **Motor de oportunidades** - `get_recommendations()` y `get_stats()` operativos  

## Próximo Paso para Validación Windows

Cuando haya acceso a entorno Windows nativo:

1. Ejecutar `tauri build` y validar generador de .exe
2. Instalar limpia y probar asistente de configuración inicial
3. Verificar accesos directos en menú Inicio y escritorio
4. Verificar rutas Windows con separadores `\`
5. Validar `%LOCALAPPDATA%` data directory creation
6. Probar actualización sobre instalación existente
7. Ejecutar desinstalación limpia y verificar remoción completa
8. Confirmar permisos UAC durante instalación

## Referencia

- **Informe completo**: `OWNEX_MEGAPROMPT_REPORT.md` (secciones A-I)
- **Fase 4 del megaprompt**: Validación distribución e instalación
- **Decisión documentada**: "No afirmes que instalación Windows está validada si no se ejecutó realmente en Windows" (Section 4)
