[Setup]
AppName=StudyMate
AppVersion=1.1.0
DefaultDirName={autopf}\StudyMate
DefaultGroupName=StudyMate
UninstallDisplayIcon={app}\StudyMate.exe
Compression=lzma2
SolidCompression=yes
OutputDir=.\InnoSetup
OutputBaseFilename=StudyMate_Installer

[Files]
Source: "dist\StudyMate\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\StudyMate"; Filename: "{app}\StudyMate.exe"
Name: "{autodesktop}\StudyMate"; Filename: "{app}\StudyMate.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"
