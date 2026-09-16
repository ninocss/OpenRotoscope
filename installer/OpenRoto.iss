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

[Dirs]
; Resolve Free can render into this fixed directory without Lua filesystem APIs.
; Keep user sessions on uninstall so unfinished mattes and safety snapshots survive.
Name: "{localappdata}\OpenRoto\FreeExchange"; Flags: uninsneveruninstall
Name: "{localappdata}\OpenRoto\Sessions"; Flags: uninsneveruninstall

[Files]
Source: "..\dist\OpenRoto\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Resolve installations in the wild can enumerate either per-user script root.
Source: "..\resolve\OpenRoto.lua"; DestDir: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"; Flags: ignoreversion
Source: "..\resolve\OpenRoto.lua"; DestDir: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility"; Flags: ignoreversion
; Studio keeps the Python bridge for the one-click automatic round trip.
Source: "..\resolve\OpenRotoEntry.py"; DestDir: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\OpenRoto"; DestName: "OpenRoto.py3"; Flags: ignoreversion
Source: "..\resolve\OpenRoto.py"; DestDir: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\OpenRoto"; DestName: "OpenRotoBridge.py"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
; Resolve Studio/Fusion uses OpenRoto's private CPython runtime for the in-app bridge.
Root: HKCU; Subkey: "Environment"; ValueType: string; ValueName: "FUSION_Python3_Home"; ValueData: "{app}\python-runtime"; Flags: preservestringtype
; Resolve Free cannot launch external processes from Lua, so keep one lightweight
; OpenRoto agent running after user login. It shows no window until frames arrive.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "OpenRoto Free Agent"; ValueData: """{app}\{#MyAppExeName}"" --free-agent"; Flags: uninsdeletevalue

[InstallDelete]
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\OpenRoto Apply.lua"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility\OpenRoto Apply.lua"
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
Filename: "{app}\{#MyAppExeName}"; Parameters: "--free-agent"; Flags: nowait runhidden skipifsilent
Filename: "{app}\{#MyAppExeName}"; Description: "Show OpenRoto launch instructions"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\OpenRoto.lua"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\OpenRoto Apply.lua"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\OpenRoto.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\OpenRoto.py3"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\OpenRoto\OpenRoto.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\OpenRoto\OpenRoto.py3"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\OpenRoto\OpenRotoBridge.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility\OpenRoto.lua"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility\OpenRoto Apply.lua"
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
    MsgBox('DaVinci Resolve 21.1 or newer was not found. OpenRoto can still be installed, but its Resolve scripts cannot be used until Resolve is installed.', mbInformation, MB_OK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    BackupFusionPythonHome();

  if CurStep = ssPostInstall then
    MsgBox('OpenRoto is installed for DaVinci Resolve Free and Studio.' + #13#10 + #13#10 +
      'Fully quit and restart DaVinci Resolve so Workspace > Scripts is refreshed.' + #13#10 + #13#10 +
      'Start a session with Workspace > Scripts > OpenRoto.' + #13#10 +
      'Select and track the subject, then use Render & Apply in the OpenRoto window.' + #13#10 +
      'On both Resolve Free and Studio the matte is applied automatically and OpenRoto closes when finished.', mbInformation, MB_OK);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    RestoreFusionPythonHome();
end;
