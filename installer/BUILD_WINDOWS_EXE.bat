@echo off
REM OWNEX Windows Installer Build Script
REM Run this on Windows with NSIS installed

echo ========================================
echo OWNEX Windows Installer Build
echo ========================================
echo.

REM Check if makensis is available
where makensis >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: makensis not found in PATH
    echo Please install NSIS from https://nsis.sourceforge.io/
    pause
    exit /b 1
)

echo 1. Checking PyInstaller bundle...
if not exist "dist\OWNEX-Desktop-Alpha\OWNEX-Desktop-Alpha.exe" (
    echo ERROR: PyInstaller bundle not found
    echo Please build it first: .venv\Scripts\python -m PyInstaller OWNEX-Desktop-Alpha.spec
    pause
    exit /b 1
)

echo    Bundle found at dist\OWNEX-Desktop-Alpha\
echo.

echo 2. Building NSIS installer...
makensis installer\OWNEX-Desktop-Alpha.nsi
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: NSIS build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS: Installer created
echo ========================================
echo Output: OWNEX-Desktop-Alpha-Setup.exe
echo.
echo To verify:
echo   1. Run OWNEX-Desktop-Alpha-Setup.exe
echo   2. Verify installation in %%LOCALAPPDATA%%\Programs\OWNEX\
echo   3. Test shortcuts and application launch
echo.
pause
