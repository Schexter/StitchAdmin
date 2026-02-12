; ============================================================================
; StitchAdmin 2.0 - Erweiterter Inno Setup Installer
; Professioneller Windows-Installer mit Konfigurationsassistent
; 
; Erstellt von Hans Hahn - Alle Rechte vorbehalten
; ============================================================================

#define MyAppName "StitchAdmin 2.0"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "Hans Hahn"
#define MyAppURL "https://stitchadmin.de"
#define MyAppExeName "StitchAdmin.exe"
#define MyAppDescription "ERP-System für Stickerei & Textilveredelung"

[Setup]
; === App-Informationen ===
AppId={{A1B2C3D4-E5F6-4A5B-9C8D-7E6F5A4B3C2D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/support
AppUpdatesURL={#MyAppURL}/updates
AppComments={#MyAppDescription}
AppCopyright=© 2025 {#MyAppPublisher} - Alle Rechte vorbehalten

; === Installationspfade ===
DefaultDirName={autopf}\StitchAdmin
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

; === Dateien ===
LicenseFile=LICENSE
InfoBeforeFile=INSTALL_INFO.txt
OutputDir=installer_output
OutputBaseFilename=StitchAdmin_2.0_Setup
SetupIconFile=src\static\img\logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; === Kompression ===
Compression=lzma2/ultra64
SolidCompression=yes
LZMANumBlockThreads=4

; === Darstellung ===
WizardStyle=modern
WizardSizePercent=120,120
; WizardImageFile=src\static\img\installer_wizard.bmp
; WizardSmallImageFile=src\static\img\installer_small.bmp
; Hinweis: Wizard-Bilder sind optional. Erstellen Sie 164x314 (links) und 55x55 (oben) BMP-Dateien

; === Berechtigungen ===
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; === Versionsinfo ===
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppDescription}
VersionInfoCopyright=© 2025 {#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
; Deutsche Texte
german.WelcomeLabel1=Willkommen bei StitchAdmin 2.0
german.WelcomeLabel2=Das ERP-System für Stickerei und Textilveredelung.%n%nDieser Assistent führt Sie durch die Installation und Erstkonfiguration.
german.DataFoldersTitle=Datenverzeichnisse
german.DataFoldersDesc=Wo sollen Ihre Geschäftsdaten gespeichert werden?
german.DataFoldersInfo=Diese Ordner enthalten Ihre Kundendaten, Designs und Backups. Sie können auch Netzlaufwerke verwenden.
german.CompanyTitle=Firmendaten
german.CompanyDesc=Ihre Firmeninformationen für Dokumente
german.CompanyInfo=Diese Daten erscheinen auf Rechnungen, Lieferscheinen, Angeboten und E-Mails.
german.AdminTitle=Administrator-Konto
german.AdminDesc=Erstellen Sie Ihren ersten Benutzer
german.AdminInfo=Mit diesem Konto melden Sie sich bei StitchAdmin an. Weitere Benutzer können später hinzugefügt werden.
german.DatabaseTitle=Datenbank wird eingerichtet
german.DatabaseDesc=Bitte warten Sie, während die Datenbank initialisiert wird...
german.FinishedLabel=StitchAdmin wurde erfolgreich installiert!
german.LaunchProgram=StitchAdmin jetzt starten

; Englische Texte
english.WelcomeLabel1=Welcome to StitchAdmin 2.0
english.WelcomeLabel2=The ERP system for embroidery and textile finishing.%n%nThis wizard will guide you through installation and initial configuration.
english.DataFoldersTitle=Data Directories
english.DataFoldersDesc=Where should your business data be stored?
english.DataFoldersInfo=These folders contain your customer data, designs and backups. You can also use network drives.
english.CompanyTitle=Company Information
english.CompanyDesc=Your company details for documents
english.CompanyInfo=This information appears on invoices, delivery notes, quotes and emails.
english.AdminTitle=Administrator Account
english.AdminDesc=Create your first user
english.AdminInfo=Use this account to log in to StitchAdmin. Additional users can be added later.
english.DatabaseTitle=Setting up Database
english.DatabaseDesc=Please wait while the database is being initialized...
english.FinishedLabel=StitchAdmin has been successfully installed!
english.LaunchProgram=Launch StitchAdmin now

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1
Name: "autostart"; Description: "StitchAdmin beim Windows-Start ausführen"; GroupDescription: "Systemintegration:"; Flags: unchecked
Name: "firewall"; Description: "Windows-Firewall für lokalen Zugriff konfigurieren"; GroupDescription: "Systemintegration:"; Flags: unchecked

[Files]
; === Hauptanwendung ===
Source: "dist\StitchAdmin\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; === Konfigurationsvorlagen ===
Source: "config\*"; DestDir: "{app}\config"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist

; === Dokumentation ===
Source: "README.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "CHANGELOG.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "QUICKSTART.md"; DestDir: "{app}\docs"; Flags: ignoreversion

; === Vorlagen für Dokumente ===
Source: "templates\documents\*"; DestDir: "{app}\templates\documents"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist

[Dirs]
; === Erstelle wichtige Verzeichnisse mit Berechtigungen ===
Name: "{app}\instance"; Permissions: users-full
Name: "{app}\instance\uploads"; Permissions: users-full
Name: "{app}\instance\uploads\photos"; Permissions: users-full
Name: "{app}\instance\uploads\thumbnails"; Permissions: users-full
Name: "{app}\instance\uploads\designs"; Permissions: users-full
Name: "{app}\instance\uploads\documents"; Permissions: users-full
Name: "{app}\instance\backups"; Permissions: users-full
Name: "{app}\logs"; Permissions: users-full
Name: "{app}\config"; Permissions: users-full

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "{#MyAppDescription}"
Name: "{group}\StitchAdmin Dokumentation"; Filename: "{app}\docs\README.md"
Name: "{group}\Datenverzeichnis öffnen"; Filename: "{code:GetCustomerFolder}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "{#MyAppDescription}"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Registry]
; === Autostart (optional) ===
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "StitchAdmin"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

; === App-Registrierung ===
Root: HKLM; Subkey: "Software\StitchAdmin"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\StitchAdmin"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"
Root: HKLM; Subkey: "Software\StitchAdmin"; ValueType: string; ValueName: "DataPath"; ValueData: "{code:GetCustomerFolder}"

[Run]
; === Nach Installation ausführen ===
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; === Vor Deinstallation ===
Filename: "{app}\cleanup.exe"; Parameters: "--uninstall"; Flags: runhidden skipifdoesntexist

[Code]
var
  // === Custom Pages ===
  DataFolderPage: TInputDirWizardPage;
  CompanyPage: TInputQueryWizardPage;
  CompanyPage2: TInputQueryWizardPage;
  AdminPage: TInputQueryWizardPage;
  ProgressPage: TOutputProgressWizardPage;
  
  // === Gespeicherte Werte ===
  CustomerFolderValue: String;
  DesignFolderValue: String;
  BackupFolderValue: String;

// ============================================================================
// HILFSFUNKTIONEN
// ============================================================================

function GetRandomString(Length: Integer): String;
const
  Chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*';
var
  I: Integer;
begin
  Result := '';
  for I := 1 to Length do
    Result := Result + Chars[Random(Length(Chars)) + 1];
end;

function BoolToStr(Value: Boolean): String;
begin
  if Value then
    Result := 'true'
  else
    Result := 'false';
end;

function GetCustomerFolder(Param: String): String;
begin
  Result := CustomerFolderValue;
end;

function GetDesignFolder(Param: String): String;
begin
  Result := DesignFolderValue;
end;

function GetBackupFolder(Param: String): String;
begin
  Result := BackupFolderValue;
end;

// ============================================================================
// WIZARD INITIALISIERUNG
// ============================================================================

procedure InitializeWizard;
var
  DefaultDataPath: String;
begin
  // Standard-Datenpfad
  DefaultDataPath := ExpandConstant('{userdocs}\StitchAdmin');

  // ========================================
  // SEITE 1: Datenverzeichnisse
  // ========================================
  DataFolderPage := CreateInputDirPage(
    wpSelectDir,
    ExpandConstant('{cm:DataFoldersTitle}'),
    ExpandConstant('{cm:DataFoldersDesc}'),
    ExpandConstant('{cm:DataFoldersInfo}') + #13#10#13#10 +
    'Tipp: Für Backups empfehlen wir ein separates Laufwerk oder einen Netzwerkpfad.',
    False, '');
  
  DataFolderPage.Add('Kundenordner (Kundendateien, Logos, Aufträge):');
  DataFolderPage.Add('Design-Archiv (Stickdateien, Druckvorlagen):');
  DataFolderPage.Add('Backup-Ordner (Automatische Sicherungen):');
  
  // Standardwerte setzen
  DataFolderPage.Values[0] := DefaultDataPath + '\Kunden';
  DataFolderPage.Values[1] := DefaultDataPath + '\Designs';
  DataFolderPage.Values[2] := DefaultDataPath + '\Backups';

  // ========================================
  // SEITE 2: Firmendaten (Teil 1)
  // ========================================
  CompanyPage := CreateInputQueryPage(
    DataFolderPage.ID,
    ExpandConstant('{cm:CompanyTitle}'),
    ExpandConstant('{cm:CompanyDesc}'),
    ExpandConstant('{cm:CompanyInfo}'));
  
  CompanyPage.Add('Firmenname:', False);
  CompanyPage.Add('Inhaber / Geschäftsführer:', False);
  CompanyPage.Add('Straße + Hausnummer:', False);
  CompanyPage.Add('PLZ:', False);
  CompanyPage.Add('Ort:', False);
  CompanyPage.Add('Land:', False);
  
  // Standardwerte
  CompanyPage.Values[5] := 'Deutschland';

  // ========================================
  // SEITE 3: Firmendaten (Teil 2 - Kontakt & Steuern)
  // ========================================
  CompanyPage2 := CreateInputQueryPage(
    CompanyPage.ID,
    ExpandConstant('{cm:CompanyTitle}') + ' (Fortsetzung)',
    'Kontaktdaten und Steuerinformationen',
    'Diese Angaben sind für Rechnungen und behördliche Dokumente erforderlich.');
  
  CompanyPage2.Add('Telefon:', False);
  CompanyPage2.Add('Mobil (optional):', False);
  CompanyPage2.Add('E-Mail:', False);
  CompanyPage2.Add('Website (optional):', False);
  CompanyPage2.Add('Steuernummer:', False);
  CompanyPage2.Add('USt-IdNr. (optional):', False);
  
  // Standardwerte
  CompanyPage2.Values[3] := 'https://';

  // ========================================
  // SEITE 4: Administrator-Konto
  // ========================================
  AdminPage := CreateInputQueryPage(
    CompanyPage2.ID,
    ExpandConstant('{cm:AdminTitle}'),
    ExpandConstant('{cm:AdminDesc}'),
    ExpandConstant('{cm:AdminInfo}') + #13#10#13#10 +
    'Hinweis: Merken Sie sich diese Zugangsdaten! Sie können sie später in den Einstellungen ändern.');
  
  AdminPage.Add('Benutzername:', False);
  AdminPage.Add('E-Mail-Adresse:', False);
  AdminPage.Add('Passwort:', True);
  AdminPage.Add('Passwort wiederholen:', True);
  
  // Standardwerte
  AdminPage.Values[0] := 'admin';

  // ========================================
  // Fortschritts-Seite für Datenbankinitialisierung
  // ========================================
  ProgressPage := CreateOutputProgressPage(
    ExpandConstant('{cm:DatabaseTitle}'),
    ExpandConstant('{cm:DatabaseDesc}'));
end;

// ============================================================================
// VALIDIERUNG
// ============================================================================

function ValidateEmail(Email: String): Boolean;
var
  AtPos, DotPos: Integer;
begin
  Result := False;
  AtPos := Pos('@', Email);
  if AtPos > 1 then
  begin
    DotPos := Pos('.', Copy(Email, AtPos + 1, Length(Email)));
    Result := (DotPos > 1) and (DotPos < Length(Email) - AtPos);
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  I: Integer;
begin
  Result := True;
  
  // === Validierung Datenverzeichnisse ===
  if CurPageID = DataFolderPage.ID then
  begin
    for I := 0 to 2 do
    begin
      if DataFolderPage.Values[I] = '' then
      begin
        MsgBox('Bitte füllen Sie alle Verzeichnispfade aus!', mbError, MB_OK);
        Result := False;
        Exit;
      end;
    end;
    
    // Speichere Werte für später
    CustomerFolderValue := DataFolderPage.Values[0];
    DesignFolderValue := DataFolderPage.Values[1];
    BackupFolderValue := DataFolderPage.Values[2];
  end;
  
  // === Validierung Firmendaten (Teil 1) ===
  if CurPageID = CompanyPage.ID then
  begin
    if CompanyPage.Values[0] = '' then
    begin
      MsgBox('Bitte geben Sie einen Firmennamen ein!', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    
    if (CompanyPage.Values[3] = '') or (CompanyPage.Values[4] = '') then
    begin
      MsgBox('Bitte geben Sie PLZ und Ort ein!', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
  
  // === Validierung Firmendaten (Teil 2) ===
  if CurPageID = CompanyPage2.ID then
  begin
    if CompanyPage2.Values[2] = '' then
    begin
      MsgBox('Bitte geben Sie eine E-Mail-Adresse ein!', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    
    if not ValidateEmail(CompanyPage2.Values[2]) then
    begin
      MsgBox('Bitte geben Sie eine gültige E-Mail-Adresse ein!', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
  
  // === Validierung Administrator ===
  if CurPageID = AdminPage.ID then
  begin
    // Benutzername prüfen
    if AdminPage.Values[0] = '' then
    begin
      MsgBox('Bitte geben Sie einen Benutzernamen ein!', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    
    if Length(AdminPage.Values[0]) < 3 then
    begin
      MsgBox('Der Benutzername muss mindestens 3 Zeichen lang sein!', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    
    // E-Mail prüfen
    if AdminPage.Values[1] = '' then
    begin
      MsgBox('Bitte geben Sie eine E-Mail-Adresse ein!', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    
    if not ValidateEmail(AdminPage.Values[1]) then
    begin
      MsgBox('Bitte geben Sie eine gültige E-Mail-Adresse ein!', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    
    // Passwort prüfen
    if AdminPage.Values[2] = '' then
    begin
      MsgBox('Bitte geben Sie ein Passwort ein!', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    
    if Length(AdminPage.Values[2]) < 6 then
    begin
      MsgBox('Das Passwort muss mindestens 6 Zeichen lang sein!', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    
    // Passwörter vergleichen
    if AdminPage.Values[2] <> AdminPage.Values[3] then
    begin
      MsgBox('Die Passwörter stimmen nicht überein!', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
end;

// ============================================================================
// POST-INSTALLATION
// ============================================================================

procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvFile: String;
  ConfigFile: String;
  InitialSetupFile: String;
  EnvContent: String;
  ConfigContent: String;
  InitialSetupContent: String;
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    ProgressPage.Show;
    
    try
      // ========================================
      // Schritt 1: Verzeichnisse erstellen
      // ========================================
      ProgressPage.SetText('Erstelle Datenverzeichnisse...', '');
      ProgressPage.SetProgress(10, 100);
      
      ForceDirectories(DataFolderPage.Values[0]);  // Kundenordner
      ForceDirectories(DataFolderPage.Values[1]);  // Design-Archiv
      ForceDirectories(DataFolderPage.Values[2]);  // Backup-Ordner
      
      // Unterordner im Kundenordner
      ForceDirectories(DataFolderPage.Values[0] + '\Logos');
      ForceDirectories(DataFolderPage.Values[0] + '\Dokumente');
      
      // Unterordner im Design-Archiv
      ForceDirectories(DataFolderPage.Values[1] + '\Stickdateien');
      ForceDirectories(DataFolderPage.Values[1] + '\Druckvorlagen');
      ForceDirectories(DataFolderPage.Values[1] + '\Vorlagen');
      
      // ========================================
      // Schritt 2: .env Datei erstellen
      // ========================================
      ProgressPage.SetText('Erstelle Konfigurationsdateien...', '');
      ProgressPage.SetProgress(30, 100);
      
      EnvFile := ExpandConstant('{app}\.env');
      
      EnvContent := 
        '# ============================================' + #13#10 +
        '# StitchAdmin 2.0 - Konfiguration' + #13#10 +
        '# Erstellt während der Installation' + #13#10 +
        '# ============================================' + #13#10 +
        #13#10 +
        '# === Flask Einstellungen ===' + #13#10 +
        'FLASK_APP=app.py' + #13#10 +
        'FLASK_ENV=production' + #13#10 +
        'SECRET_KEY=' + GetRandomString(64) + #13#10 +
        #13#10 +
        '# === Datenbank ===' + #13#10 +
        'DATABASE_URL=sqlite:///instance/stitchadmin.db' + #13#10 +
        #13#10 +
        '# === Datenverzeichnisse ===' + #13#10 +
        'CUSTOMER_FOLDER=' + DataFolderPage.Values[0] + #13#10 +
        'DESIGN_FOLDER=' + DataFolderPage.Values[1] + #13#10 +
        'BACKUP_FOLDER=' + DataFolderPage.Values[2] + #13#10 +
        'UPLOAD_FOLDER=instance/uploads' + #13#10 +
        #13#10 +
        '# === Logging ===' + #13#10 +
        'LOG_LEVEL=INFO' + #13#10 +
        'LOG_FILE=logs/stitchadmin.log' + #13#10;
      
      SaveStringToFile(EnvFile, EnvContent, False);
      
      // ========================================
      // Schritt 3: Firmen-Konfiguration erstellen
      // ========================================
      ProgressPage.SetText('Speichere Firmendaten...', '');
      ProgressPage.SetProgress(50, 100);
      
      ConfigFile := ExpandConstant('{app}\config\company.json');
      
      ConfigContent := 
        '{' + #13#10 +
        '  "company": {' + #13#10 +
        '    "name": "' + CompanyPage.Values[0] + '",' + #13#10 +
        '    "owner": "' + CompanyPage.Values[1] + '",' + #13#10 +
        '    "street": "' + CompanyPage.Values[2] + '",' + #13#10 +
        '    "zip": "' + CompanyPage.Values[3] + '",' + #13#10 +
        '    "city": "' + CompanyPage.Values[4] + '",' + #13#10 +
        '    "country": "' + CompanyPage.Values[5] + '",' + #13#10 +
        '    "phone": "' + CompanyPage2.Values[0] + '",' + #13#10 +
        '    "mobile": "' + CompanyPage2.Values[1] + '",' + #13#10 +
        '    "email": "' + CompanyPage2.Values[2] + '",' + #13#10 +
        '    "website": "' + CompanyPage2.Values[3] + '",' + #13#10 +
        '    "tax_id": "' + CompanyPage2.Values[4] + '",' + #13#10 +
        '    "vat_id": "' + CompanyPage2.Values[5] + '"' + #13#10 +
        '  },' + #13#10 +
        '  "settings": {' + #13#10 +
        '    "currency": "EUR",' + #13#10 +
        '    "tax_rate": 19.0,' + #13#10 +
        '    "language": "de",' + #13#10 +
        '    "date_format": "DD.MM.YYYY",' + #13#10 +
        '    "time_format": "HH:mm"' + #13#10 +
        '  },' + #13#10 +
        '  "paths": {' + #13#10 +
        '    "customers": "' + StringChange(DataFolderPage.Values[0], '\', '\\') + '",' + #13#10 +
        '    "designs": "' + StringChange(DataFolderPage.Values[1], '\', '\\') + '",' + #13#10 +
        '    "backups": "' + StringChange(DataFolderPage.Values[2], '\', '\\') + '"' + #13#10 +
        '  }' + #13#10 +
        '}';
      
      SaveStringToFile(ConfigFile, ConfigContent, False);
      
      // ========================================
      // Schritt 4: Initial Setup Datei für ersten Start
      // ========================================
      ProgressPage.SetText('Bereite Ersteinrichtung vor...', '');
      ProgressPage.SetProgress(70, 100);
      
      InitialSetupFile := ExpandConstant('{app}\config\initial_setup.json');
      
      InitialSetupContent := 
        '{' + #13#10 +
        '  "setup_required": true,' + #13#10 +
        '  "admin_user": {' + #13#10 +
        '    "username": "' + AdminPage.Values[0] + '",' + #13#10 +
        '    "email": "' + AdminPage.Values[1] + '",' + #13#10 +
        '    "password": "' + AdminPage.Values[2] + '"' + #13#10 +
        '  },' + #13#10 +
        '  "installed_at": "' + GetDateTimeString('yyyy-mm-dd hh:nn:ss', '-', ':') + '",' + #13#10 +
        '  "installer_version": "' + '{#MyAppVersion}' + '"' + #13#10 +
        '}';
      
      SaveStringToFile(InitialSetupFile, InitialSetupContent, False);
      
      // ========================================
      // Schritt 5: Datenbank initialisieren
      // ========================================
      ProgressPage.SetText('Initialisiere Datenbank...', '');
      ProgressPage.SetProgress(85, 100);
      
      // Führe init_database.exe aus wenn vorhanden
      if FileExists(ExpandConstant('{app}\init_database.exe')) then
      begin
        Exec(ExpandConstant('{app}\init_database.exe'), 
             '--config "' + ExpandConstant('{app}\config') + '"',
             ExpandConstant('{app}'),
             SW_HIDE, ewWaitUntilTerminated, ResultCode);
      end;
      
      // ========================================
      // Schritt 6: Firewall-Regel (optional)
      // ========================================
      if IsTaskSelected('firewall') then
      begin
        ProgressPage.SetText('Konfiguriere Windows-Firewall...', '');
        ProgressPage.SetProgress(95, 100);
        
        Exec('netsh', 'advfirewall firewall add rule name="StitchAdmin" dir=in action=allow program="' + 
             ExpandConstant('{app}\{#MyAppExeName}') + '" enable=yes',
             '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      end;
      
      ProgressPage.SetProgress(100, 100);
      
    finally
      ProgressPage.Hide;
    end;
  end;
end;

// ============================================================================
// DEINSTALLATION
// ============================================================================

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Response: Integer;
  DataPath: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    Response := MsgBox(
      'Möchten Sie auch alle Daten löschen?' + #13#10 + #13#10 +
      '• Datenbank (Kunden, Aufträge, Rechnungen)' + #13#10 +
      '• Uploads (Fotos, Dokumente)' + #13#10 +
      '• Konfiguration' + #13#10 + #13#10 +
      'ACHTUNG: Dies kann nicht rückgängig gemacht werden!' + #13#10 + #13#10 +
      'Ihre Datenverzeichnisse (Kunden, Designs, Backups) werden NICHT gelöscht.',
      mbConfirmation, MB_YESNO);
      
    if Response = IDYES then
    begin
      // Lösche Anwendungsdaten
      DelTree(ExpandConstant('{app}\instance'), True, True, True);
      DelTree(ExpandConstant('{app}\logs'), True, True, True);
      DelTree(ExpandConstant('{app}\config'), True, True, True);
    end;
    
    // Firewall-Regel entfernen
    Exec('netsh', 'advfirewall firewall delete rule name="StitchAdmin"',
         '', SW_HIDE, ewWaitUntilTerminated, Response);
  end;
end;

// ============================================================================
// INITIALISIERUNG
// ============================================================================

function InitializeSetup(): Boolean;
begin
  Result := True;
  
  // Zufallsgenerator initialisieren
  Randomize();
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
end;
