@echo off
rem ============================================================================
rem  OWNEX — daily launcher (manual start; no autostart is registered)
rem
rem  Starts the installed app and waits for the internal backend to answer.
rem  Works with both bundle layouts:
rem    - Tauri v2 NSIS, currentUser  -> %LOCALAPPDATA%\<productName>\
rem    - Tauri v2 NSIS, perMachine   -> %PROGRAMFILES%\<productName>\
rem    - legacy WiX/MSI               -> %LOCALAPPDATA%\Programs\OWNEX\
rem  If no desktop app is found, it falls back to the backend-only build,
rem  which serves the same UI at http://127.0.0.1:8000.
rem ============================================================================
setlocal

set "APP_NAME=OWNEX Alpha"
set "EXE_NAME=%APP_NAME%.exe"

rem --- candidate locations, most specific first -------------------------------
set "CANDIDATES="
set "CANDIDATES=%CANDIDATES%;%LOCALAPPDATA%\%APP_NAME%\%EXE_NAME%"
set "CANDIDATES=%CANDIDATES%;%LOCALAPPDATA%\Programs\%APP_NAME%\%EXE_NAME%"
set "CANDIDATES=%CANDIDATES%;%PROGRAMFILES%\%APP_NAME%\%EXE_NAME%"
set "CANDIDATES=%CANDIDATES%;%LOCALAPPDATA%\Programs\OWNEX\OWNEX Alpha.exe"
set "CANDIDATES=%CANDIDATES%;%LOCALAPPDATA%\Programs\OWNEX\OWNEX-Desktop-Alpha.exe"

set "FOUND="
for %%C in ("%CANDIDATES:;=" "%") do (
    if exist %%C if not defined FOUND set "FOUND=%%~C"
)

if defined FOUND (
    echo OWNEX: launching "%FOUND%"
    start "" "%FOUND%"
) else (
    rem Fall back to the backend-only portable build, if present.
    if exist "%~dp0ownex-backend.exe" (
        echo OWNEX: desktop app not found - starting backend only.
        start "" "%~dp0ownex-backend.exe" --port 8000 --host 127.0.0.1
    ) else (
        echo OWNEX: no installation found.
        echo   Expected one of:
        echo     %LOCALAPPDATA%\%APP_NAME%\%EXE_NAME%
        echo     %PROGRAMFILES%\%APP_NAME%\%EXE_NAME%
        echo   Re-run the installer: OWNEX Alpha-Setup.exe
        pause
        exit /b 1
    )
)

echo.
echo Waiting for the backend (up to 90 s)...
powershell -NoProfile -Command ^
  "for ($i=0; $i -lt 18; $i++) { try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { Write-Host 'Backend online (health 200).' -ForegroundColor Green; exit 0 } } catch {}; Start-Sleep -Seconds 5 }"

echo.
echo If the window did not open, browse to http://127.0.0.1:8000
endlocal
