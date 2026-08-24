; ---------------------------------------------------------------
; OWNEX Desktop - Instalador Windows
; Generated for OWNEX Desktop v7.0.0
; ---------------------------------------------------------------

[Setup]
; ---------------------------------------------------------------
; Basic installer information
; ---------------------------------------------------------------
AppName=OWNEX Desktop
AppVersion=7.0.0
AppPublisher=OWNEX
AppURL=https://ownex.desktop
; UseUTF8=icons
; -------------------------------------------------------------
; Default installation path
; -------------------------------------------------------------
DefaultDirName={commonpf32}\OWNEX
; -------------------------------------------------------------
; Default group name
; -------------------------------------------------------------
DefaultGroupName=OWNEX
; -------------------------------------------------------------
; Uninstall display name
; -------------------------------------------------------------
UninstallDisplayName=OWNEX Desktop
; -------------------------------------------------------------
; Setup icons
; -------------------------------------------------------------
; Install directory icon
SetupIconFile=app:ownex-icon-alpha.ico
; -------------------------------------------------------------
; File definitions
; -------------------------------------------------------------
; Source files
SourceDir={app}\

; -------------------------------------------------------------
; Sections
; -------------------------------------------------------------
[Files]
; Copy the main executable
Source: "{app}\OWNEX-Desktop-Alpha.exe"; DestDir:{app}
; Copy the icon
Source: "assets\logos\ownex-icon-alpha.ico"; DestDir:{app}
; Copy additional resources and data
Source: "data\*.*"; DestDir:{app}\data
; Copy desktop services
Source: "desktop\native\*.*"; DestDir:{app}\desktop\native
; Copy API routers
Source: "api\routers\*.py"; DestDir:{app}\api\routers
; Copy core modules
Source: "cores\*.py"; DestDir:{app}\cores
; Copy scripts
Source: "scripts\*.py"; DestDir:{app}\scripts

; -------------------------------------------------------------
; Post-installation tasks
; -------------------------------------------------------------
[Tasks]
name:"Default tasks"; description:"Install Default tasks"; value:auto

[Icons]
; Create Desktop shortcut
Name: "{commondesktopmenu}\OWNEX Desktop"; Filename: "{app}\OWNEX-Desktop-Alpha.exe"
; Create Start Menu shortcut
Name: "{group}\OWNEX Desktop"; Filename: "{app}\OWNEX-Desktop-Alpha.exe"
; Pin to taskbar (optional)
; Name: "{cmddlg}ownex"; Filename: "{app}\OWNEX-Desktop-Alpha.exe"

; -------------------------------------------------------------
; Uninstallation
; -------------------------------------------------------------
[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Uninstall]
Name: "OWNEX Desktop"; Description: "Desinstalar OWNEX Desktop"; DefaultGroup: OwnExGroup

; Register uninstall in Add/Remove programs
[Registry]
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\OWNEX"; 
  ValueType: string; ValueName: "DisplayName"; ValueData: "OWNEX Desktop"
  ValueType: string; ValueName: "UninstallString"; ValueData: "{uninstallexe}"
  ValueType: string; ValueName: "DisplayIcon"; ValueData: "{app}\ownex-icon-alpha.ico"
  ValueType: string; ValueName: "DisplayVersion"; ValueData: "7.0.0"
  ValueType: string; ValueName: "QuietUninstallString"; ValueData: "{uninstallexe} /silent"

; -------------------------------------------------------------
; Post-installation configuration
; -------------------------------------------------------------
[Code]
; -------------------------------------------------------------
; Function to set up paths after installation
; -------------------------------------------------------------
function InitializeSetup(): Boolean;
var
  appdataDir: string;
  ownexDataDir: string;
begin
  ; Ensure data directory exists in APPDATA
  appdataDir := ExpandConstant('{appdata}');
  ownexDataDir := BuildPath(appdataDir, 'OWNEX');
  
  ; Create the directory if it doesn't exist
  if not DirExists(ownexDataDir) then
    CreateDir(ownexDataDir);
  
  ; Write initialization file if needed
  ; This ensures the user data directory is ready
  Result := True;
end;

; -------------------------------------------------------------
; InitializeSetup event
; -------------------------------------------------------------
procedure CurStepChanged(Step: Integer);
var
  appdataDir: string;
  ownexDataDir: string;
begin
  if Step = ssPostInstall then
  begin
    ; Ensure data directory exists
    appdataDir := ExpandConstant('{appdata}');
    ownexDataDir := BuildPath(appdataDir, 'OWNEX');
    
    ; Create directory
    if not DirExists(ownexDataDir) then
      CreateDir(ownexDataDir);
    
    ; Write a success marker
    ; The application will read this on first launch
    ; In a real implementation, you might write a config file here
  end;
end;