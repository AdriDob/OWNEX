@echo off
rem OWNEX Desktop Alpha - daily launcher
rem Starts the installed app and waits for the internal backend.
setlocal

set "APP_EXE=%LOCALAPPDATA%\Programs\OWNEX\OWNEX-Desktop-Alpha.exe"

if exist "%APP_EXE%" (
    start "" "%APP_EXE%"
) else (
    start "" "OWNEX Desktop"
)

echo OWNEX Desktop iniciado.
echo El backend interno arranca solo (~30-60 s); MISSION pasa a "Source: api".
powershell -NoProfile -Command "for ($i=0; $i -lt 18; $i++) { try { $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/health' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { Write-Host 'Backend online (health 200).' -ForegroundColor Green; exit 0 } } catch {}; Start-Sleep -Seconds 5 }"