#define MyAppName "Age of Duck"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "BubbleDuckz"
#define MyAppExeName "AgeOfDuck.exe"

[Setup]
AppId={{8B9A41A8-897B-48DA-967F-D6E4A1F6BB47}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Age of Duck
DefaultGroupName=Age of Duck
DisableProgramGroupPage=yes
OutputDir=..\installer-output
OutputBaseFilename=AgeOfDuck-Setup-v2.0.0
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=..\duck.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=admin
VersionInfoVersion=2.0.0.0
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "..\dist\AgeOfDuck\*"; DestDir: "{app}"; Excludes: "tc-live-status.json,*.log"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Age of Duck"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Age of Duck"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Age of Duck"; Flags: nowait postinstall skipifsilent
