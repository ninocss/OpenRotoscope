#define MyAppName "OpenRoto"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "OpenRoto contributors"
#define MyAppExeName "OpenRoto.exe"

[Setup]
AppId={{0E36C9B9-1E8E-4B31-BA0E-6DA5243AEF77}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\OpenRoto
DefaultGroupName=OpenRoto
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=OpenRotoSetup-{#MyAppVersion}-x64
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
LicenseFile=..\LICENSE
SetupLogging=yes
CloseApplications=yes
RestartApplications=no
ChangesEnvironment=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\OpenRoto\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Resolve installations in the wild can enumerate either of these per-user
; script roots. Ship the same sandbox-safe Lua launcher to both so Workspace >
; Scripts continues to discover OpenRoto across Resolve versions/configurations.
Source: "..\resolve\OpenRoto.lua"; DestDir: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"; Flags: ignoreversion
Source: "..\resolve\OpenRoto.lua"; DestDir: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility"; Flags: ignoreversion
Source: "..\resolve\OpenRotoEntry.py"; DestDir: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\OpenRoto"; DestName: "OpenRoto.py3"; Flags: ignoreversion
Source: "..\resolve\OpenRoto.py"; DestDir: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\OpenRoto"; DestName: "OpenRotoBridge.py"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
; Resolve/Fusion does not ship an embedded Python interpreter on Windows. Point
; its Python 3 host at OpenRoto's private CPython runtime. The previous value is
; backed up/restored by the code section below.
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "FUSION_Python3_Home"; ValueData: "{app}\python-runtime"; Flags: preservestringtype

[InstallDelete]
; Remove bridge/menu files left by older preview and development installs.
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\OpenRoto.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\OpenRoto.py3"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\OpenRoto\OpenRoto.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\OpenRoto\OpenRotoBridge.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility\OpenRoto.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility\OpenRoto.py3"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\OpenRoto\OpenRoto.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\OpenRoto\OpenRoto.py3"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\OpenRoto\OpenRotoBridge.py"

[Icons]
Name: "{group}\OpenRoto"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall OpenRoto"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Show OpenRoto launch instructions"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\OpenRoto.lua"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\OpenRoto.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\OpenRoto.py3"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\OpenRoto\OpenRoto.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\OpenRoto\OpenRoto.py3"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\OpenRoto\OpenRotoBridge.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility\OpenRoto.lua"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility\OpenRoto.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility\OpenRoto.py3"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\OpenRoto\OpenRoto.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\OpenRoto\OpenRoto.py3"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\OpenRoto\OpenRotoBridge.py"

[Code]
const
  EnvKey = 'Environment';
  BackupKey = 'Software\OpenRoto';
  FusionPythonValue = 'FUSION_Python3_Home';
  BackupValue = 'PreviousFusionPython3Home';
  BackupPresentValue = 'PreviousFusionPython3HomePresent';

procedure BackupFusionPythonHome();
var
  ExistingValue: String;
begin
  if RegQueryStringValue(HKCU, EnvKey, FusionPythonValue, ExistingValue) then
  begin
    RegWriteStringValue(HKCU, BackupKey, BackupValue, ExistingValue);
    RegWriteDWordValue(HKCU, BackupKey, BackupPresentValue, 1);
  end
  else
  begin
    RegDeleteValue(HKCU, BackupKey, BackupValue);
    RegWriteDWordValue(HKCU, BackupKey, BackupPresentValue, 0);
  end;
end;

procedure RestoreFusionPythonHome();
var
  CurrentValue: String;
  PreviousValue: String;
  HadPrevious: Cardinal;
  InstalledValue: String;
begin
  InstalledValue := ExpandConstant('{app}\python-runtime');
  if not RegQueryStringValue(HKCU, EnvKey, FusionPythonValue, CurrentValue) then
    exit;
  if CompareText(CurrentValue, InstalledValue) <> 0 then
    exit;

  if RegQueryDWordValue(HKCU, BackupKey, BackupPresentValue, HadPrevious) and (HadPrevious = 1) and
     RegQueryStringValue(HKCU, BackupKey, BackupValue, PreviousValue) then
    RegWriteStringValue(HKCU, EnvKey, FusionPythonValue, PreviousValue)
  else
    RegDeleteValue(HKCU, EnvKey, FusionPythonValue);

  RegDeleteKeyIncludingSubkeys(HKCU, BackupKey);
end;

function InitializeSetup(): Boolean;
var
  ResolveExe: String;
begin
  ResolveExe := ExpandConstant('{pf}\Blackmagic Design\DaVinci Resolve\Resolve.exe');
  Result := True;
  if not FileExists(ResolveExe) then
    MsgBox('DaVinci Resolve 21.1 or newer was not found. OpenRoto can still be installed, but its Resolve script cannot be used until Resolve is installed.', mbInformation, MB_OK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    BackupFusionPythonHome();

  if CurStep = ssPostInstall then
    MsgBox('OpenRoto is installed.' + #13#10 + #13#10 +
      'IMPORTANT: Fully quit and restart DaVinci Resolve so it refreshes Workspace > Scripts and loads the bundled Python runtime.' + #13#10 + #13#10 +
      'Then place the playhead over a clip and choose:' + #13#10 +
      'Workspace > Scripts > OpenRoto', mbInformation, MB_OK);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    RestoreFusionPythonHome();
end;
