[Setup]
AppName=Solizer
AppVersion=1.0
DefaultDirName={autopf}\Solizer
DefaultGroupName=Solizer
OutputDir=C:\Users\Akalanka\Desktop\SOFTWARE\Solizer_Release\Output2
OutputBaseFilename=Solizer_Setup
Compression=lzma
SolidCompression=yes
SetupIconFile=C:\Users\Akalanka\Desktop\SOFTWARE\Solizer_Release\setup_icon.ico
UninstallDisplayIcon={app}\setup_icon.ico


[Files]
Source: "C:\Users\Akalanka\Desktop\SOFTWARE\Solizer_Release\backend\dist\solizer-backend.exe"; DestDir: "{app}"; DestName: "Solizer.exe"; Flags: ignoreversion
Source: "C:\Users\Akalanka\Desktop\SOFTWARE\Solizer_Release\solizer.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Solizer"; Filename: "{app}\Solizer.exe"; IconFilename: "{app}\solizer.ico"
Name: "{group}\Uninstall Solizer"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Solizer"; Filename: "{app}\Solizer.exe"; IconFilename: "{app}\solizer.ico"; Tasks: desktopicon


[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"

[Run]
Filename: "{app}\Solizer.exe"; Description: "Launch Solizer"; Flags: nowait postinstall skipifsilent
