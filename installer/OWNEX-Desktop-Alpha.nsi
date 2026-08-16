; OWNEX Desktop Alpha - NSIS Installer Script
; Requires NSIS 3.0+ to build
; Run with: makensis OWNEX-Desktop-Alpha.nsi
; Compile from the repo root: makensis resolves relative paths (File/OutFile)
; against the script directory, so step up to the checkout root.
!cd ..

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

; Use user-level installation to avoid admin requirement
RequestExecutionLevel user

InstallDir "$LOCALAPPDATA\Programs\${APPNAME}"

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