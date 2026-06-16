; Inno Setup script for SynthPop Desktop
; https://jrsoftware.org/isinfo.php
;
; Prerequisites:
;   1. Run PyInstaller first: build.bat  (produces dist\SynthPop Desktop\)
;   2. Install Inno Setup 6: https://jrsoftware.org/isdl.php
;   3. Compile this script: ISCC packaging\installer.iss
;      (or open it in the Inno Setup GUI and press Compile)
;
; Output: dist\installer\SynthPop_Desktop_Setup_1.0.0.exe

#define AppName      "SynthPop Desktop"
#define AppVersion   "1.0.0"
#define AppPublisher "Your Organisation"
#define AppExeName   "SynthPop Desktop.exe"
#define BuildDir     "..\dist\SynthPop Desktop"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/tc245/synthpop-windows
AppSupportURL=https://github.com/tc245/synthpop-windows/issues
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; Output installer to dist\installer\
OutputDir=..\dist\installer
OutputBaseFilename=SynthPop_Desktop_Setup_{#AppVersion}
SetupIconFile=..\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; 64-bit Windows only (matches PyInstaller win_amd64 build)
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Require admin rights to install to Program Files
PrivilegesRequired=admin
; Minimum Windows 10
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; \
  Description: "{cm:CreateDesktopIcon}"; \
  GroupDescription: "{cm:AdditionalIcons}"; \
  Flags: unchecked

[Files]
; Include the entire PyInstaller onedir output
Source: "{#BuildDir}\*"; \
  DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{group}\{#AppName}"; \
  Filename: "{app}\{#AppExeName}"; \
  IconFilename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; \
  Filename: "{uninstallexe}"
; Optional desktop shortcut
Name: "{autodesktop}\{#AppName}"; \
  Filename: "{app}\{#AppExeName}"; \
  IconFilename: "{app}\{#AppExeName}"; \
  Tasks: desktopicon

[Run]
; Offer to launch the app after installation
Filename: "{app}\{#AppExeName}"; \
  Description: "{cm:LaunchProgram,{#AppName}}"; \
  Flags: nowait postinstall skipifsilent
