@echo off
setlocal enabledelayedexpansion
set "CATEYE_DIR=%~dp0"

echo === CATEYE Portable Setup ===
echo.

REM ── Create directory structure (idempotent) ──
for %%d in (data\database data\uploads data\evidence config logs backups tools docs) do (
    if not exist "%CATEYE_DIR%%%d" (
        mkdir "%CATEYE_DIR%%%d" >nul 2>&1
    )
)

REM ── Verify ──
set "ALL_OK=1"

echo.
echo Verifying installation...
echo.

REM 1. CATEYE.exe exists
if exist "%CATEYE_DIR%CATEYE.exe" (
    echo [OK] CATEYE.exe
) else (
    echo [MISSING] CATEYE.exe — binary not found
    set ALL_OK=0
)

REM 2. Write permissions (data/)
echo. >"%CATEYE_DIR%data\.write_test" 2>&1
if exist "%CATEYE_DIR%data\.write_test" (
    del "%CATEYE_DIR%data\.write_test" >nul 2>&1
    echo [OK] Write permissions — data/
) else (
    echo [FAIL] No write permission in data/
    set ALL_OK=0
)

REM 3. Write permissions (logs/)
echo. >"%CATEYE_DIR%logs\.write_test" 2>&1
if exist "%CATEYE_DIR%logs\.write_test" (
    del "%CATEYE_DIR%logs\.write_test" >nul 2>&1
    echo [OK] Write permissions — logs/
) else (
    echo [FAIL] No write permission in logs/
    set ALL_OK=0
)

REM 4. Frontend assets
if exist "%CATEYE_DIR%_internal\frontend_dist\index.html" (
    echo [OK] Frontend assets
) else (
    echo [WARN] Frontend assets not found at _internal\frontend_dist\
    echo        Some features may not work in browser mode.
)

REM 5. Brief backend test
echo.
echo Testing backend launch...
set "BACKEND_OK=0"
set "TIMEOUT_COUNT=0"

start "" /B "%CATEYE_DIR%CATEYE.exe" --check >"%CATEYE_DIR%logs\health_check.log" 2>&1
if !ERRORLEVEL! EQU 0 (
    echo [OK] Backend responds
    set BACKEND_OK=1
) else (
    echo [WARN] Backend check returned code !ERRORLEVEL!
    type "%CATEYE_DIR%logs\health_check.log" 2>nul
)

echo.
if "!ALL_OK!"=="1" (
    echo ========================================
    echo   CATEYE quedo configurado correctamente.
    echo   El sistema esta listo para uso diario.
    echo ========================================
    echo.
    echo   Para iniciar: ejecute run.bat
    echo.
) else (
    echo ========================================
    echo   ERROR: La configuracion no se completo.
    echo ========================================
    echo.
    if not exist "%CATEYE_DIR%CATEYE.exe" (
        echo   CATEYE.exe no encontrado.
        echo   Asegurese de que el binario esta en la misma carpeta.
    )
    echo   Revise logs/backend.log si el backend fallo.
    echo.
    pause
    exit /b 1
)

pause
