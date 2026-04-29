[Setup]
AppName=InnoTech VideoTutor
AppVersion=1.0.0
AppPublisher=InnoTech Solutions
AppPublisherURL=https://www.innotech.com
DefaultDirName={autopf}\InnoTech\VideoTutor
DefaultGroupName=InnoTech VideoTutor
OutputDir=dist\installer
OutputBaseFilename=InnoTech_VideoTutor_Setup_v1.0.0
SetupIconFile=resources\icons\app_logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\InnoTech VideoTutor.exe

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
; Aplicación principal (salida de PyInstaller)
Source: "dist\InnoTech VideoTutor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

; Visual C++ Redistributable
Source: "installer\prereqs\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Run]
; Instalar VC++ Redist silenciosamente si no está presente
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/quiet /norestart"; \
  StatusMsg: "Instalando componentes de Visual C++..."; \
  Flags: runhidden; Check: VCRedistNeedsInstall

; Lanzar la aplicación al finalizar
Filename: "{app}\InnoTech VideoTutor.exe"; Description: "Iniciar InnoTech VideoTutor"; \
  Flags: nowait postinstall skipifsilent

[Icons]
Name: "{group}\InnoTech VideoTutor"; Filename: "{app}\InnoTech VideoTutor.exe"
Name: "{commondesktop}\InnoTech VideoTutor"; Filename: "{app}\InnoTech VideoTutor.exe"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function VCRedistNeedsInstall: Boolean;
var
  Installed: Cardinal;
begin
  Result := not RegQueryDWordValue(HKLM,
    'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
    'Installed', Installed) or (Installed = 0);
end;
