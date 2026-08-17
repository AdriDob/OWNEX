@echo off
rem OWNEX Desktop Alpha - One-click Windows 11 installer
rem Doubles-click: installs OWNEX, launches it and verifies the backend is alive.
setlocal

set "SCRIPT_DIR=%~dp0"
set "SETUP=%SCRIPT_DIR%OWNEX-Desktop-Alpha-Setup.exe"
set "INSTALL_DIR=%LOCALAPPDATA%\Programs\OWNEX"
set "APP_EXE=%INSTALL_DIR%\OWNEX-Desktop-Alpha.exe"
set "CHECKSUM_FILE=%SCRIPT_DIR%checksums\SHA256SUMS.txt"

echo ============================================
echo  OWNEX Desktop Alpha - Instalador One-Click
echo ============================================
echo.

if not exist "%SETUP%" (
    echo [ERROR] No se encontro el instalador: %SETUP%
    echo         Copia OWNEX-Desktop-Alpha-Setup.exe junto a este script.
    pause
    exit /b 1
)

rem --- 1. Verify checksum (optional) -----------------------------------
if exist "%CHECKSUM_FILE%" (
    echo [1/4] Verificando integridad del instalador...
    for /f "tokens=1" %%h in ('powershell -NoProfile -Command "(Get-FileHash '%SETUP%' -Algorithm SHA256).Hash"') do set "HASH=%%h"
    for /f "tokens=1" %%e in ('findstr /i "OWNEX-Desktop-Alpha-Setup.exe" "%CHECKSUM_FILE%"') do set "EXPECTED=%%e"
    if defined EXPECTED (
        if /i not "%HASH%"=="%EXPECTED%" (
            echo [WARN] El hash no coincide con el esperado.
            echo        Real:     %HASH%
            echo        Esperado: %EXPECTED%
            echo        Continua? Presiona una tecla para continuar o Ctrl+C para abortar.
            pause >nul
        ) else (
            echo        SHA256 OK
        )
    )
) else (
    echo [1/4] Archivo de checksums no encontrado, se salta la verificacion.
)

rem --- 2. Install silently --------------------------------------------
echo [2/4] Instalando OWNEX (silencioso)...
"%SETUP%" /S
if errorlevel 1 (
    echo [ERROR] El instalador fallo (code %errorlevel%).
    echo         Reintenta haciendo doble clic en el instalador y siguiendo el asistente.
    pause
    exit /b 1
)
if not exist "%APP_EXE%" (
    echo [WARN] La app no aparece en %INSTALL_DIR%
    echo        Busca OWNEX Desktop en el menu Inicio.
) else (
    echo        Instalado en %INSTALL_DIR%
)

rem --- 3. Launch --------------------------------------------------------
echo [3/4] Lanzando OWNEX Desktop...
if exist "%APP_EXE%" (
    start "" "%APP_EXE%"
) else (
    start "" "OWNEX Desktop"
)

rem --- 4. Verify backend (waits up to ~90 s) ---------------------------
echo [4/4] Verificando el backend interno (127.0.0.1:8000)...
set /a tries=0
:waitloop
set /a tries+=1
if %tries% gtr 18 (
    echo        El backend tarda mas de lo esperado. La vista MISSION se
    echo        actualiza sola: deberia pasar a "Source: api" en 1-2 minutos.
    goto done
)
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    timeout /t 5 /nobreak >nul
    goto waitloop
)
echo        Backend online (health 200). Todo listo.

:done
echo.
echo ============================================
echo  Instalacion completada. OWNEX Desktop
echo  muestra datos reales en MISSION Control.
echo ============================================
pause