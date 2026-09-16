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

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\dist\OpenRoto\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\resolve\OpenRoto.lua"; DestDir: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility"; Flags: ignoreversion
Source: "..\resolve\OpenRoto.py"; DestDir: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\OpenRoto"; DestName: "OpenRoto.py3"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[InstallDelete]
; Remove bridge/menu files left by older preview and development installs. The
; supported launcher is Lua and the bridge filename is OpenRoto.py3.
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\OpenRoto.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts\Utility\OpenRoto.py3"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Support\OpenRoto\OpenRoto.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility\OpenRoto.lua"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility\OpenRoto.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility\OpenRoto.py3"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\OpenRoto\OpenRoto.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\OpenRoto\OpenRoto.py3"

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
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility\OpenRoto.lua"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility\OpenRoto.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility\OpenRoto.py3"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\OpenRoto\OpenRoto.py"
Type: files; Name: "{userappdata}\Blackmagic Design\DaVinci Resolve\Fusion\OpenRoto\OpenRoto.py3"

[Code]
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
  if CurStep = ssPostInstall then
    MsgBox('OpenRoto is installed.' + #13#10 + #13#10 +
      'Restart DaVinci Resolve, place the playhead over a clip, then choose:' + #13#10 +
      'Workspace > Scripts > OpenRoto', mbInformation, MB_OK);
end;
