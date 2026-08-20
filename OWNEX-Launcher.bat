@echo off
REM ============================================================================
REM OWNEX Windows Launcher (Batch version)
REM Starts OWNEX in WSL2 and opens dashboard in browser app mode
REM Runs entirely from WSL - no project files copied to Windows
REM ============================================================================

setlocal enabledelayedexpansion

set WSL_DISTRO=Ubuntu
set PROJECT_PATH=/home/adriel/projects/Rastro
set PYTHON_PATH=/home/adriel/projects/Rastro/.venv/bin/python
set BACKEND_PORT=8000
set HEALTH_ENDPOINT=http://127.0.0.1:%BACKEND_PORT%/api/health
set STARTUP_TIMEOUT=120
set HEALTH_CHECK_INTERVAL=2

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║                    OWNEX Windows Launcher                      ║
echo  ║              Autonomous Intelligence Platform                   ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

REM 1. Check WSL
echo [INFO] Checking WSL2 availability...
wsl.exe --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] WSL not available or not installed
    echo Please install WSL2: wsl --install -d Ubuntu
    pause
    exit /b 1
)

wsl.exe -l -v 2>&1 | find "%WSL_DISTRO%" >nul
if %errorlevel% neq 0 (
    echo [ERROR] WSL distro '%WSL_DISTRO%' not found
    wsl.exe -l -v
    pause
    exit /b 1
)
echo [OK] WSL2 with %WSL_DISTRO% available

REM 2. Ensure logs directory
wsl.exe -d %WSL_DISTRO% -- mkdir -p "%PROJECT_PATH%/logs" >nul 2>&1

REM 3. Check if backend already running
echo [INFO] Checking if backend is running on port %BACKEND_PORT%...
powershell -Command "$listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, %BACKEND_PORT%); try { $listener.Start(); $listener.Stop(); exit 0 } catch { exit 1 }"
if %errorlevel% equ 0 (
    echo [WARN] Port %BACKEND_PORT% is free
    set BACKEND_RUNNING=0
) else (
    echo [INFO] Port %BACKEND_PORT% in use - verifying health...
    powershell -Command "try { $r = Invoke-RestMethod -Uri '%HEALTH_ENDPOINT%' -TimeoutSec 5; if ($r.status -eq 'ok') { exit 0 } else { exit 1 } } catch { exit 1 }"
    if %errorlevel% equ 0 (
        echo [OK] Backend already running and healthy
        set BACKEND_RUNNING=1
    ) else (
        echo [WARN] Port in use but not OWNEX backend
        set BACKEND_RUNNING=0
    )
)

REM 4. Start backend if needed
if %BACKEND_RUNNING% equ 0 (
    echo [INFO] Stopping any stale backend processes...
    wsl.exe -d %WSL_DISTRO% -- pkill -f "uvicorn.*api.main:app.*--port %BACKEND_PORT%" 2>nul
    timeout /t 1 /nobreak >nul
    
    echo [INFO] Starting OWNEX backend in WSL...
    
    REM Create startup script and run it
    wsl.exe -d %WSL_DISTRO% -- bash -c "cat > '%PROJECT_PATH%/start_backend.sh' << 'EOF'
#!/bin/bash
cd '%PROJECT_PATH%'
export PYTHONPATH='%PROJECT_PATH%:$PYTHONPATH'
nohup '%PYTHON_PATH%' -m uvicorn api.main:app --host 127.0.0.1 --port %BACKEND_PORT% --log-level warning ^
    > '%PROJECT_PATH%/logs/backend.log' 2>&1 &
echo \$! > '%PROJECT_PATH%/logs/backend.pid'
EOF
chmod +x '%PROJECT_PATH%/start_backend.sh'
'%PROJECT_PATH%/start_backend.sh'
"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to start backend in WSL
        pause
        exit /b 1
    )
    echo [OK] Backend startup script executed in WSL
    
    REM Wait for health check
    echo [INFO] Waiting for backend health check...
    set /a ELAPSED=0
    :HEALTH_LOOP
    if %ELAPSED% geq %STARTUP_TIMEOUT% (
        echo.
        echo [ERROR] Health check TIMEOUT after %STARTUP_TIMEOUT%s
        echo Check logs at: %PROJECT_PATH%/logs/backend.log
        echo You can view logs with: wsl -d Ubuntu -- cat %PROJECT_PATH%/logs/backend.log
        pause
        exit /b 1
    )
    
    powershell -Command "try { $r = Invoke-RestMethod -Uri '%HEALTH_ENDPOINT%' -TimeoutSec 5; if ($r.status -eq 'ok') { exit 0 } else { exit 1 } } catch { exit 1 }"
    if %errorlevel% equ 0 (
        echo.
        echo [OK] Backend health check PASSED
    ) else (
        echo.>nul
        set /a ELAPSED+=2
        timeout /t 2 /nobreak >nul
        goto HEALTH_LOOP
    )
) else (
    echo [OK] Reusing existing backend instance
)

REM 5. Open dashboard in browser (app mode)
echo [INFO] Opening dashboard in browser...

REM Try Edge first, then Chrome
for %%B in (msedge.exe chrome.exe) do (
    where %%B >nul 2>&1
    if %errorlevel% equ 0 (
        set BROWSER=%%B
        goto BROWSER_FOUND
    )
)

REM Fallback to default browser
echo [WARN] Edge/Chrome not found, using default browser
start "" "http://127.0.0.1:%BACKEND_PORT%"
goto LAUNCH_DONE

:BROWSER_FOUND
echo [OK] Using browser: %BROWSER%
start "" "%BROWSER%" --app=http://127.0.0.1:%BACKEND_PORT% --new-window

:LAUNCH_DONE
echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║  OWNEX is running!                                             ║
echo  ║  Dashboard: http://127.0.0.1:%BACKEND_PORT%                            ║
echo  ║  Backend logs: %PROJECT_PATH%/logs/backend.log                  ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.
echo Close this window to keep OWNEX running in background.
echo To stop OWNEX, close the browser window or run: wsl -d Ubuntu -- pkill -f "uvicorn.*api.main:app.*--port %BACKEND_PORT%"
echo.
timeout /t 3 >nul