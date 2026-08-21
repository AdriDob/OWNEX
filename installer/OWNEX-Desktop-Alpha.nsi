; OWNEX Desktop Alpha - NSIS Installer Script
; Requires NSIS 3.0+ to build
; Run with: makensis OWNEX-Desktop-Alpha.nsi
; Compile from the repo root: makensis resolves relative paths (File/OutFile)
; against the script directory, so step up to the checkout root.
!cd ..

!include "x64.nsh"

!define APPNAME "OWNEX Desktop Alpha"
!define COMPANYNAME "CATEYE"
!define DESCRIPTION "Native bug bounty intelligence platform"
!define VERSIONMAJOR 7
!define VERSIONMINOR 0
!define VERSIONBUILD 0
!define HELPURL "https://github.com/AdriDob/OWNEX"
!define UPDATEURL "https://github.com/AdriDob/OWNEX"
!define ABOUTURL "https://github.com/AdriDob/OWNEX"
!define INSTALLSIZE 250000

; VC++ Redistributable download URL (Microsoft Visual C++ 2015-2022 Redist x64)
!define VCPP_URL "https://aka.ms/vs/17/release/vc_redist.x64.exe"
!define VCPP_INSTALLER "$TEMP\vc_redist.x64.exe"

; Use admin-level installation for Program Files
RequestExecutionLevel admin

InstallDir "$PROGRAMFILES\OWNEX"

; ── VC++ Runtime Detection ─────────────────────────────────────────────
Var VCPP_Installed

Function .onInit
    ; Check for Visual C++ 2015-2022 Runtime (x64)
    ; Qt/PySide6 requires VC++ Runtime to load DLLs
    ReadRegDWORD $1 HKLM "SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" "Installed"
    ${If} $1 == 1
        StrCpy $VCPP_Installed "1"
        Goto vcpp_done
    ${EndIf}
    ; Also check WOW6432Node for 32-bit systems running 64-bit apps
    ReadRegDWORD $1 HKLM "SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" "Installed"
    ${If} $1 == 1
        StrCpy $VCPP_Installed "1"
        Goto vcpp_done
    ${EndIf}
    ; Not found — prompt user
    StrCpy $VCPP_Installed "0"
    MessageBox MB_YESNO|MB_ICONQUESTION "Visual C++ Runtime (2015-2022) is required but was not detected on your system.$\n$\nOWNEX uses PySide6/Qt which depends on VC++ Runtime.$\n$\nWould you like to download and install it now?$\n(Requires internet connection, ~25 MB)" IDYES download_vcpp IDNO vcpp_done

    download_vcpp:
        NSISdl::download /URL "${VCPP_URL}" /TIMEOUT 60000 "${VCPP_INSTALLER}"
        Pop $0
        ${If} $0 == "success"
            DetailPrint "Installing Visual C++ Runtime..."
            ExecWait '"${VCPP_INSTALLER}" /install /quiet /norestart' $1
            ${If} $1 == 0
                DetailPrint "VC++ Runtime installed successfully."
                StrCpy $VCPP_Installed "1"
            ${Else}
                MessageBox MB_OK|MB_ICONEXCLAMATION "VC++ Runtime installation failed (exit code: $1).$\n$\nOWNEX may not start correctly without it.$\nYou can install it manually from: https://aka.ms/vs/17/release/vc_redist.x64.exe"
            ${EndIf}
            ; Cleanup installer
            Delete "${VCPP_INSTALLER}"
        ${Else}
            MessageBox MB_OK|MB_ICONEXCLAMATION "Could not download VC++ Runtime ($0).$\n$\nPlease install it manually from:$\nhttps://aka.ms/vs/17/release/vc_redist.x64.exe"
        ${EndIf}

    vcpp_done:
FunctionEnd

Page directory
Page instfiles

UninstPage uninstConfirm
UninstPage instfiles

Section "install"
    SetOutPath $INSTDIR
    File /r "dist\OWNEX-Desktop-Alpha\*"
    
    WriteUninstaller "$INSTDIR\uninstall.exe"
    
    CreateShortCut "$SMPROGRAMS\${APPNAME}.lnk" "$INSTDIR\OWNEX-Desktop-Alpha.exe" "" "$INSTDIR\OWNEX-Desktop-Alpha.exe" 0
    CreateShortCut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\OWNEX-Desktop-Alpha.exe" "" "$INSTDIR\OWNEX-Desktop-Alpha.exe" 0
    
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayName" "${APPNAME}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "QuietUninstallString" "$INSTDIR\uninstall.exe /S"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayIcon" "$INSTDIR\OWNEX-Desktop-Alpha.exe"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "Publisher" "${COMPANYNAME}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "HelpLink" "${HELPURL}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "URLUpdateInfo" "${UPDATEURL}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "URLInfoAbout" "${ABOUTURL}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "DisplayVersion" "${VERSIONMAJOR}.${VERSIONMINOR}.${VERSIONBUILD}"
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "VersionMajor" ${VERSIONMAJOR}
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "VersionMinor" ${VERSIONMINOR}
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "VersionBuild" ${VERSIONBUILD}
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}" "EstimatedSize" ${INSTALLSIZE}
SectionEnd

Section "uninstall"
    Delete "$SMPROGRAMS\${APPNAME}.lnk"
    Delete "$DESKTOP\${APPNAME}.lnk"
    
    RMDir /r "$INSTDIR"
    
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APPNAME}"
SectionEnd

; Final output name
OutFile "OWNEX-Desktop-Alpha-Setup.exe"