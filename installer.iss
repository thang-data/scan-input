; Inno Setup Script for Scan Input - Vietnamese OCR Tool
; Download Inno Setup from: https://jrsoftware.org/isdl.php

[Setup]
AppName=Scan Input - OCR Tiếng Việt
AppVersion=1.0.0
AppPublisher=Scan Input
DefaultDirName={autopf}\ScanInput
DefaultGroupName=Scan Input
OutputDir=dist
OutputBaseFilename=ScanInput_Setup_v1.0.0
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=resources\icon.ico
UninstallDisplayIcon={app}\ScanInput.exe
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "vietnamese"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Tạo shortcut trên Desktop"; GroupDescription: "Biểu tượng:"; Flags: unchecked

[Files]
; Main application
Source: "dist\ScanInput\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Scan Input"; Filename: "{app}\ScanInput.exe"
Name: "{group}\Gỡ cài đặt Scan Input"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Scan Input"; Filename: "{app}\ScanInput.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ScanInput.exe"; Description: "Mở Scan Input ngay"; Flags: nowait postinstall skipifsilent
