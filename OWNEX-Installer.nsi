; ============================================================================
; OWNEX Windows Installer (NSIS)
; 
; IMPORTANT: OWNEX runs entirely from WSL2. This installer ONLY places the
; launcher scripts and icon on the Windows side. No project source is copied.
; The backend, Python venv, and all code remain in WSL. The launcher
; automatically detects the WSL project path at runtime.
; Compile on Windows with: makensis OWNEX-Installer.nsi
; ============================================================================

!define APP_NAME "OWNEX"
!define APP_VERSION "7.0.0"
!define APP_PUBLISHER "OWNEX Project"
!define APP_WEBSITE "https://github.com/AdriDob/Rastro"
!define APP_EXE "OWNEX-Launcher.ps1"
!define APP_ICON "ownex-icon-alpha.ico"
; Launcher runs from WSL2 - project path is detected dynamically at runtime

; Include modern UI
!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"
!include "WinCore.nsh"
!include "x64.nsh"

; Installer settings
Name "${APP_NAME} ${APP_VERSION}"
OutFile "OWNEX-Setup-${APP_VERSION}.exe"
InstallDir "$PROGRAMFILES\${APP_NAME}"
InstallDirRegKey HKCU "Software\${APP_NAME}" "InstallDir"
; Program Files + HKLM require elevation
RequestExecutionLevel admin
Icon "${APP_ICON}"

; Modern UI pages
!define MUI_ABORTWARNING
!define MUI_ICON "${APP_ICON}"
!define MUI_UNICON "${APP_ICON}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

; Variables
Var PreviousInstallDir
Var StartMenuFolder

Section "MainSection" SEC_MAIN
    SectionIn RO
    
    ; Set output path
    SetOutPath "$INSTDIR"
    
    ; Copy desktop exe when built (CI PyInstaller output), else launcher scripts
    !if exists "dist\OWNEX-Desktop-Alpha\OWNEX-Desktop-Alpha.exe"
        File /r "dist\OWNEX-Desktop-Alpha\*"
        WriteRegStr HKCU "Software\${APP_NAME}" "ExePath" "$INSTDIR\OWNEX-Desktop-Alpha.exe"
    !else
        ; Copy launcher scripts (only Windows-side files)
        File "OWNEX-Launcher.ps1"
        File "OWNEX-Launcher.bat"
        File "Create-Shortcut.ps1"
    !endif

    ; Copy icon (for shortcut) - from assets/logos/
    File "assets\logos\ownex-icon-alpha.ico"
    
; Note: OWNEX runs entirely from WSL2. The launcher accesses files via
; WSL automatic detection. No project source is copied to Windows.
    
    ; Create logs directory
    CreateDirectory "$INSTDIR\logs"
    
    ; Write uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    ; Registry entries
    WriteRegStr HKCU "Software\${APP_NAME}" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "Software\${APP_NAME}" "Version" "${APP_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME} ${APP_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "URLInfoAbout" "${APP_WEBSITE}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoModify" "1"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoRepair" "1"
    
    ; Create Start Menu shortcuts (desktop exe when built, else launcher)
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    ${If} ${FileExists} "$INSTDIR\OWNEX-Desktop-Alpha.exe"
        CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\OWNEX-Desktop-Alpha.exe" "" "$INSTDIR\ownex-icon-alpha.ico" 0
    ${Else}
        CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "powershell.exe" "-ExecutionPolicy Bypass -File `"$INSTDIR\OWNEX-Launcher.ps1`"" "$INSTDIR\ownex-icon-alpha.ico" 0
    ${EndIf}
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe" "" "" 0

    ; Create Desktop shortcut (required for zero-config one-click launch)
    ${If} ${FileExists} "$INSTDIR\OWNEX-Desktop-Alpha.exe"
        CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\OWNEX-Desktop-Alpha.exe" "" "$INSTDIR\ownex-icon-alpha.ico" 0
    ${Else}
        CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "powershell.exe" "-ExecutionPolicy Bypass -File `"$INSTDIR\OWNEX-Launcher.ps1`"" "$INSTDIR\ownex-icon-alpha.ico" 0
    ${EndIf}
    
SectionEnd

Section "StartMenuShortcut" SEC_STARTMENU
    ; Already created in main section
SectionEnd

; ============================================================================
; Uninstaller
; ============================================================================
Section "Uninstall"
    ; Remove Start Menu shortcuts
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    
    ; Remove Desktop shortcut (if exists)
    Delete "$DESKTOP\${APP_NAME}.lnk"
    
    ; Remove installed files (only launcher scripts + icon, no project source)
    Delete "$INSTDIR\OWNEX-Launcher.ps1"
    Delete "$INSTDIR\OWNEX-Launcher.bat"
    Delete "$INSTDIR\Create-Shortcut.ps1"
    Delete "$INSTDIR\ownex-icon-alpha.ico"
    Delete "$INSTDIR\Uninstall.exe"
    
    ; Remove directories (only logs, no project dirs copied to Windows)
    RMDir /r "$INSTDIR\logs"
    
    ; Remove registry entries
    DeleteRegKey HKCU "Software\${APP_NAME}"
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
    
    ; Remove install directory
    RMDir "$INSTDIR"
    
    ; Note: We do NOT remove WSL data. User data is preserved in WSL.
SectionEnd

; ============================================================================
; Functions
; ============================================================================
Function .onInit
    ; Check if running on 64-bit Windows
    ${IfNot} ${RunningX64}
        MessageBox MB_ICONSTOP "This installer requires 64-bit Windows."
        Abort
    ${EndIf}
    
    ; Check for WSL
    ExecWait 'wsl.exe --version 2>NUL'
    ${If} $0 != 0
        MessageBox MB_ICONWARNING "WSL2 not detected. OWNEX requires WSL2 with Ubuntu.${n}${n}Continue anyway?" IDYES IDNO
        ${If} $0 == IDNO
            Abort
        ${EndIf}
    ${EndIf}
FunctionEnd

Function .onInstSuccess
    ; Show finish message with instructions
    MessageBox MB_ICONINFORMATION "OWNEX installed successfully!${n}${n}OWNEX is now ready to use.${n}${n}• Double-click the OWNEX icon on your Desktop${n}• Or find OWNEX in the Start Menu${n}${n}The launcher starts the OWNEX backend in WSL and opens the dashboard in browser app mode."
FunctionEnd

; ============================================================================
; Custom Pages (optional)
; ============================================================================
; Uncomment to add a custom page for WSL path configuration
; !define MUI_CUSTOMFUNCTION_GUIINIT MyGuiInit
; Function MyGuiInit
;     ; Custom initialization
; FunctionEnd