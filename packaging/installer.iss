#define AppVersion "2.1.2"
[Setup]
SourceDir=..
AppId={{35954A3A-2729-4C3F-9309-EA4673ED9AF9}
AppName=SR Inqly
AppVersion={#AppVersion}
AppPublisher=Sachin Rathnayaka
AppPublisherURL=https://github.com/SachinRathnayaka
DefaultDirName={localappdata}\Programs\SR Inqly
DefaultGroupName=SR Inqly
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=dist
OutputBaseFilename=SR Inqly Setup {#AppVersion}
SetupIconFile=assets\sr-inqly.ico
UninstallDisplayIcon={app}\SR Inqly.exe
LicenseFile=LICENSE
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "dist\SR Inqly\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SR Inqly"; Filename: "{app}\SR Inqly.exe"; IconFilename: "{app}\_internal\assets\sr-inqly.ico"
Name: "{autodesktop}\SR Inqly"; Filename: "{app}\SR Inqly.exe"; IconFilename: "{app}\_internal\assets\sr-inqly.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\SR Inqly.exe"; Description: "Launch SR Inqly"; Flags: nowait postinstall skipifsilent
