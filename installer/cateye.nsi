; CATEYE — Professional Windows 11 Installer
; Build: makensis installer\cateye.nsi
;        makensis /DPRODUCT_VERSION=X.Y.Z installer\cateye.nsi
; Output: dist\CATEYEInstaller.exe
;
; FEATURES:
;   - Dark-themed MUI2 wizard
;   - Gold accent branding (#D4AF37)
;   - Installs to C:\Program Files\CATEYE\
;   - Desktop + Start Menu shortcuts
;   - Add/Remove Programs entry
;   - NO Python execution — pure file copy + registry

Unicode True
CRCCheck On
ManifestDPIAware True
SetCompressor /SOLID lzma
SetCompressorDictSize 32

!define PRODUCT_NAME "CATEYE"
!ifndef PRODUCT_VERSION
!define PRODUCT_VERSION "3.0.0"
!endif
!define PRODUCT_PUBLISHER "CATEYE Labs"
!define PRODUCT_WEB_SITE "https://cateye.security"
!define PRODUCT_DIR "$PROGRAMFILES64\${PRODUCT_NAME}"
!define PRODUCT_DATA_DIR "$APPDATA\${PRODUCT_NAME}"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"

RequestExecutionLevel admin

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "..\dist\CATEYEInstaller.exe"
InstallDir "${PRODUCT_DIR}"
ShowInstDetails hide
ShowUnInstDetails hide

; ── MUI2 Configuration ─────────────────────────────────────────────
!define MUI_ICON "icons\cateye.ico"
!define MUI_UNICON "icons\cateye.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT
!define MUI_ABORTWARNING
!define MUI_COMPONENTSPAGE_SMALLDESC
!define MUI_FINISHPAGE_RUN "$INSTDIR\CATEYE.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Launch CATEYE now"
!define MUI_FINISHPAGE_RUN_PARAMETERS "--tray"
!define MUI_FINISHPAGE_LINK "Learn more at cateye.security"
!define MUI_FINISHPAGE_LINK_LOCATION "${PRODUCT_WEB_SITE}"

!include "MUI2.nsh"

; ── Pages ──────────────────────────────────────────────────────────
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; ── Language ───────────────────────────────────────────────────────
!insertmacro MUI_LANGUAGE "English"

; ══════════════════════════════════════════════════════════════════
; SECTION — Install
; ══════════════════════════════════════════════════════════════════
Section "CATEYE Application" SEC_APP
  SectionIn RO

  SetOutPath "$INSTDIR"

  ; Copy all built artifacts — NO Python execution
  ; Source: dist\CATEYE\* (PyInstaller output)
  File /r "..\dist\CATEYE\*.*"

  ; Copy supporting files
  File "..\LICENSE"

  ; Create user data directories
  CreateDirectory "${PRODUCT_DATA_DIR}"
  CreateDirectory "${PRODUCT_DATA_DIR}\logs"
  CreateDirectory "${PRODUCT_DATA_DIR}\database"
  CreateDirectory "${PRODUCT_DATA_DIR}\uploads"
  CreateDirectory "${PRODUCT_DATA_DIR}\evidence"
  CreateDirectory "${PRODUCT_DATA_DIR}\config"
  CreateDirectory "${PRODUCT_DATA_DIR}\backups"
  CreateDirectory "${PRODUCT_DATA_DIR}\tools"

  ; ── Start Menu ────────────────────────────────────────────────
  CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\CATEYE.lnk" \
    "$INSTDIR\CATEYE.exe" "--tray" "$INSTDIR\CATEYE.exe" 0
  WriteIniStr "$SMPROGRAMS\${PRODUCT_NAME}\Dashboard.url" \
    "InternetShortcut" "URL" "http://127.0.0.1:8000"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Logs.lnk" \
    "$WINDIR\explorer.exe" "${PRODUCT_DATA_DIR}\logs"
  CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\Uninstall CATEYE.lnk" \
    "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0

  ; ── Desktop Shortcut ──────────────────────────────────────────
  CreateShortCut "$DESKTOP\CATEYE.lnk" \
    "$INSTDIR\CATEYE.exe" "--tray" "$INSTDIR\CATEYE.exe" 0

  ; ── Registry (Add/Remove Programs) ─────────────────────────────
  WriteUninstaller "$INSTDIR\uninstall.exe"

  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "UninstallString" \
    '"$INSTDIR\uninstall.exe"'
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "QuietUninstallString" \
    '"$INSTDIR\uninstall.exe" /S'
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayVersion" \
    "${PRODUCT_VERSION}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "Publisher" \
    "${PRODUCT_PUBLISHER}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "URLInfoAbout" \
    "${PRODUCT_WEB_SITE}"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayIcon" \
    "$INSTDIR\CATEYE.exe,0"
  WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "InstallLocation" \
    "$INSTDIR"
  WriteRegDWORD HKLM "${PRODUCT_UNINST_KEY}" "NoModify" 1
  WriteRegDWORD HKLM "${PRODUCT_UNINST_KEY}" "NoRepair" 1
  WriteRegDWORD HKLM "${PRODUCT_UNINST_KEY}" "EstimatedSize" 350000

  ; ── Firewall Rule (backend port 8000) ──────────────────────────
  ; Runs silently, best-effort
  ExecWait 'netsh advfirewall firewall add rule name="CATEYE Backend" \
    dir=in action=allow program="$INSTDIR\CATEYE.exe" enable=yes \
    profile=private'
SectionEnd

; ── Optional: Start with Windows ────────────────────────────────
Section "Start CATEYE with Windows" SEC_AUTOSTART
  WriteRegStr HKCU \
    "Software\Microsoft\Windows\CurrentVersion\Run" \
    "CATEYE" '"$INSTDIR\CATEYE.exe" --tray'
SectionEnd

; ── Section descriptions ─────────────────────────────────────────
LangString DESC_SEC_APP ${LANG_ENGLISH} \
  "Install CATEYE application and all required components."
LangString DESC_SEC_AUTOSTART ${LANG_ENGLISH} \
  "Automatically launch CATEYE in the system tray when you log in."

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_APP} $(DESC_SEC_APP)
  !insertmacro MUI_DESCRIPTION_TEXT ${SEC_AUTOSTART} $(DESC_SEC_AUTOSTART)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; ══════════════════════════════════════════════════════════════════
; SECTION — Uninstall
; ══════════════════════════════════════════════════════════════════
Section "Uninstall"
  ; Stop running instance gracefully
  ExecWait 'taskkill /f /im CATEYE.exe'
  Sleep 500

  ; Remove Start Menu
  RMDir /r "$SMPROGRAMS\${PRODUCT_NAME}"

  ; Remove Desktop shortcut
  Delete "$DESKTOP\CATEYE.lnk"

  ; Remove application files
  RMDir /r "$INSTDIR"

  ; Remove autostart
  DeleteRegValue HKCU \
    "Software\Microsoft\Windows\CurrentVersion\Run" \
    "CATEYE"

  ; Remove firewall rule
  ExecWait 'netsh advfirewall firewall delete rule name="CATEYE Backend"'

  ; Remove uninstall key
  DeleteRegKey HKLM "${PRODUCT_UNINST_KEY}"

  ; User data kept by default — uncomment to remove:
  ; RMDir /r "${PRODUCT_DATA_DIR}"
SectionEnd
