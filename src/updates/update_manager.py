# -*- coding: utf-8 -*-
"""
StitchAdmin 2.0 - Update Manager
Verwaltet Updates und Rollbacks

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import sys
import json
import shutil
import hashlib
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass

from .backup_manager import BackupManager


@dataclass
class UpdateInfo:
    """Informationen über ein verfügbares Update"""
    version: str
    release_date: str
    changelog: List[str]
    download_url: str = ''
    file_path: str = ''
    checksum: str = ''
    size_bytes: int = 0
    min_version: str = ''  # Mindestversion für dieses Update
    breaking_changes: bool = False
    requires_restart: bool = True


@dataclass
class UpdateResult:
    """Ergebnis einer Update-Operation"""
    success: bool
    message: str
    old_version: str = ''
    new_version: str = ''
    backup_path: str = ''
    requires_restart: bool = True


class UpdateManager:
    """
    Verwaltet Updates für StitchAdmin
    
    Update-Paket Struktur (ZIP):
    update_2.0.1/
    ├── update_info.json      # Update-Metadaten
    ├── files/                # Neue/geänderte Dateien
    │   ├── app.py
    │   ├── src/
    │   └── ...
    ├── migrations/           # Datenbank-Migrationen
    │   └── 001_add_column.sql
    └── scripts/              # Pre/Post-Update Scripts
        ├── pre_update.py
        └── post_update.py
    """
    
    # Update-Status
    STATUS_IDLE = 'idle'
    STATUS_CHECKING = 'checking'
    STATUS_DOWNLOADING = 'downloading'
    STATUS_BACKING_UP = 'backing_up'
    STATUS_INSTALLING = 'installing'
    STATUS_MIGRATING = 'migrating'
    STATUS_VALIDATING = 'validating'
    STATUS_ROLLING_BACK = 'rolling_back'
    STATUS_COMPLETE = 'complete'
    STATUS_FAILED = 'failed'
    
    def __init__(self, app_dir: Path = None):
        """
        Initialisiert den Update-Manager
        
        Args:
            app_dir: Anwendungsverzeichnis
        """
        self.app_dir = Path(app_dir) if app_dir else Path(__file__).parent.parent.parent
        self.backup_manager = BackupManager(app_dir=self.app_dir)
        
        self.status = self.STATUS_IDLE
        self.progress = 0
        self.progress_message = ''
        
        # Geschützte Verzeichnisse/Dateien (werden nicht überschrieben)
        self.protected_paths = [
            'instance/',
            'config/',
            'backups/',
            'logs/',
            '.env',
            'Kunden/',
            'uploads/',
        ]
        
        # Update-Verlauf
        self.update_history_file = self.app_dir / 'config' / 'update_history.json'
    
    def get_current_version(self) -> str:
        """Ermittelt die aktuell installierte Version"""
        # 1. Versuche aus version.txt
        version_file = self.app_dir / 'version.txt'
        if version_file.exists():
            return version_file.read_text().strip()
        
        # 2. Versuche aus build_config
        try:
            sys.path.insert(0, str(self.app_dir))
            from build_config import APP_VERSION
            return APP_VERSION
        except:
            pass
        
        # 3. Versuche aus config
        config_file = self.app_dir / 'config' / 'app_info.json'
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f).get('version', 'unknown')
        
        return 'unknown'
    
    def set_current_version(self, version: str):
        """Setzt die aktuelle Version"""
        # version.txt aktualisieren
        version_file = self.app_dir / 'version.txt'
        version_file.write_text(version)
        
        # config/app_info.json aktualisieren
        config_file = self.app_dir / 'config' / 'app_info.json'
        config_file.parent.mkdir(exist_ok=True)
        
        app_info = {}
        if config_file.exists():
            with open(config_file, 'r') as f:
                app_info = json.load(f)
        
        app_info['version'] = version
        app_info['updated_at'] = datetime.now().isoformat()
        
        with open(config_file, 'w') as f:
            json.dump(app_info, f, indent=2)
    
    def _set_status(self, status: str, progress: int = None, message: str = ''):
        """Setzt den aktuellen Status"""
        self.status = status
        if progress is not None:
            self.progress = progress
        self.progress_message = message
    
    def read_update_package(self, package_path: str) -> Tuple[bool, str, Optional[UpdateInfo]]:
        """
        Liest Informationen aus einem Update-Paket
        
        Args:
            package_path: Pfad zur Update-ZIP-Datei
        
        Returns:
            Tuple[success, message, UpdateInfo]
        """
        package_path = Path(package_path)
        
        if not package_path.exists():
            return False, f"Update-Paket nicht gefunden: {package_path}", None
        
        if package_path.suffix != '.zip':
            return False, "Update-Paket muss eine ZIP-Datei sein", None
        
        try:
            with zipfile.ZipFile(package_path, 'r') as zipf:
                # Suche update_info.json
                info_files = [f for f in zipf.namelist() if f.endswith('update_info.json')]
                
                if not info_files:
                    return False, "Keine update_info.json im Paket gefunden", None
                
                with zipf.open(info_files[0]) as f:
                    info_data = json.load(f)
                
                update_info = UpdateInfo(
                    version=info_data.get('version', 'unknown'),
                    release_date=info_data.get('release_date', ''),
                    changelog=info_data.get('changelog', []),
                    file_path=str(package_path),
                    checksum=info_data.get('checksum', ''),
                    size_bytes=package_path.stat().st_size,
                    min_version=info_data.get('min_version', ''),
                    breaking_changes=info_data.get('breaking_changes', False),
                    requires_restart=info_data.get('requires_restart', True),
                )
                
                return True, "Update-Paket erfolgreich gelesen", update_info
                
        except zipfile.BadZipFile:
            return False, "Ungültige ZIP-Datei", None
        except json.JSONDecodeError:
            return False, "Ungültige update_info.json", None
        except Exception as e:
            return False, f"Fehler beim Lesen des Update-Pakets: {e}", None
    
    def validate_update(self, update_info: UpdateInfo) -> Tuple[bool, str]:
        """
        Validiert ob ein Update installiert werden kann
        
        Args:
            update_info: Update-Informationen
        
        Returns:
            Tuple[can_install, message]
        """
        current_version = self.get_current_version()
        
        # Prüfe ob Update neuer ist
        if not self._version_greater(update_info.version, current_version):
            return False, f"Update-Version ({update_info.version}) ist nicht neuer als aktuelle Version ({current_version})"
        
        # Prüfe Mindestversion
        if update_info.min_version:
            if not self._version_greater_or_equal(current_version, update_info.min_version):
                return False, f"Dieses Update erfordert mindestens Version {update_info.min_version}. Aktuelle Version: {current_version}"
        
        # Prüfe Checksum wenn vorhanden
        if update_info.checksum and update_info.file_path:
            actual_checksum = self._calculate_file_checksum(update_info.file_path)
            if actual_checksum != update_info.checksum:
                return False, "Checksum stimmt nicht überein - Download möglicherweise beschädigt"
        
        return True, "Update kann installiert werden"
    
    def install_update(self, package_path: str, 
                       create_backup: bool = True) -> UpdateResult:
        """
        Installiert ein Update-Paket
        
        Args:
            package_path: Pfad zur Update-ZIP-Datei
            create_backup: Vorher Backup erstellen?
        
        Returns:
            UpdateResult
        """
        old_version = self.get_current_version()
        backup_path = ''
        
        try:
            # 1. Update-Paket lesen
            self._set_status(self.STATUS_CHECKING, 5, "Lese Update-Paket...")
            success, message, update_info = self.read_update_package(package_path)
            
            if not success:
                return UpdateResult(False, message, old_version)
            
            # 2. Update validieren
            self._set_status(self.STATUS_CHECKING, 10, "Validiere Update...")
            can_install, message = self.validate_update(update_info)
            
            if not can_install:
                return UpdateResult(False, message, old_version)
            
            # 3. Backup erstellen
            if create_backup:
                self._set_status(self.STATUS_BACKING_UP, 20, "Erstelle Backup...")
                success, message, backup = self.backup_manager.create_backup(
                    backup_type=BackupManager.TYPE_PRE_UPDATE,
                    description=f"Vor Update auf {update_info.version}"
                )
                
                if not success:
                    return UpdateResult(False, f"Backup fehlgeschlagen: {message}", old_version)
                
                backup_path = str(backup)
            
            # 4. Update installieren
            self._set_status(self.STATUS_INSTALLING, 40, "Installiere Dateien...")
            success, message = self._install_files(package_path, update_info)
            
            if not success:
                # Rollback bei Fehler
                if backup_path:
                    self._set_status(self.STATUS_ROLLING_BACK, 0, "Rollback...")
                    self.backup_manager.restore_backup(backup_path)
                return UpdateResult(False, f"Installation fehlgeschlagen: {message}", old_version, backup_path=backup_path)
            
            # 5. Migrationen ausführen
            self._set_status(self.STATUS_MIGRATING, 70, "Führe Migrationen aus...")
            success, message = self._run_migrations(package_path)
            
            if not success:
                # Rollback bei Fehler
                if backup_path:
                    self._set_status(self.STATUS_ROLLING_BACK, 0, "Rollback...")
                    self.backup_manager.restore_backup(backup_path)
                return UpdateResult(False, f"Migration fehlgeschlagen: {message}", old_version, backup_path=backup_path)
            
            # 6. Post-Update Script ausführen
            self._set_status(self.STATUS_INSTALLING, 85, "Führe Post-Update aus...")
            self._run_post_update_script(package_path)
            
            # 7. Version aktualisieren
            self._set_status(self.STATUS_VALIDATING, 95, "Finalisiere Update...")
            self.set_current_version(update_info.version)
            
            # 8. Update-Historie speichern
            self._save_update_history(old_version, update_info.version, backup_path)
            
            # Fertig!
            self._set_status(self.STATUS_COMPLETE, 100, "Update erfolgreich!")
            
            return UpdateResult(
                success=True,
                message=f"Update auf Version {update_info.version} erfolgreich!",
                old_version=old_version,
                new_version=update_info.version,
                backup_path=backup_path,
                requires_restart=update_info.requires_restart
            )
            
        except Exception as e:
            self._set_status(self.STATUS_FAILED, 0, str(e))
            
            # Rollback bei Fehler
            if backup_path:
                try:
                    self.backup_manager.restore_backup(backup_path)
                except:
                    pass
            
            return UpdateResult(
                success=False,
                message=f"Update fehlgeschlagen: {str(e)}",
                old_version=old_version,
                backup_path=backup_path
            )
    
    def _install_files(self, package_path: str, update_info: UpdateInfo) -> Tuple[bool, str]:
        """Installiert die Update-Dateien"""
        try:
            with zipfile.ZipFile(package_path, 'r') as zipf:
                # Finde das files/ Verzeichnis im ZIP
                files_prefix = None
                for name in zipf.namelist():
                    if '/files/' in name:
                        files_prefix = name.split('/files/')[0] + '/files/'
                        break
                
                if not files_prefix:
                    return False, "Kein files/ Verzeichnis im Update-Paket"
                
                # Extrahiere Dateien
                for zip_info in zipf.infolist():
                    if not zip_info.filename.startswith(files_prefix):
                        continue
                    
                    # Relativer Pfad ohne files/ Prefix
                    relative_path = zip_info.filename[len(files_prefix):]
                    
                    if not relative_path:
                        continue
                    
                    # Prüfe ob Pfad geschützt ist
                    if any(relative_path.startswith(p) for p in self.protected_paths):
                        continue
                    
                    target_path = self.app_dir / relative_path
                    
                    if zip_info.is_dir():
                        target_path.mkdir(parents=True, exist_ok=True)
                    else:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Datei extrahieren
                        with zipf.open(zip_info) as source:
                            with open(target_path, 'wb') as target:
                                target.write(source.read())
            
            return True, "Dateien erfolgreich installiert"
            
        except Exception as e:
            return False, str(e)
    
    def _run_migrations(self, package_path: str) -> Tuple[bool, str]:
        """Führt Datenbank-Migrationen aus"""
        try:
            with zipfile.ZipFile(package_path, 'r') as zipf:
                # Finde das migrations/ Verzeichnis
                migration_files = sorted([
                    f for f in zipf.namelist() 
                    if '/migrations/' in f and f.endswith('.sql')
                ])
                
                if not migration_files:
                    return True, "Keine Migrationen erforderlich"
                
                # Datenbank-Verbindung
                import sqlite3
                db_path = self.app_dir / 'instance' / 'stitchadmin.db'
                
                if not db_path.exists():
                    return True, "Keine Datenbank vorhanden - Migrationen übersprungen"
                
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                for migration_file in migration_files:
                    with zipf.open(migration_file) as f:
                        sql = f.read().decode('utf-8')
                        
                        # Führe SQL aus
                        cursor.executescript(sql)
                
                conn.commit()
                conn.close()
                
                return True, f"{len(migration_files)} Migration(en) ausgeführt"
                
        except Exception as e:
            return False, str(e)
    
    def _run_post_update_script(self, package_path: str):
        """Führt Post-Update Script aus (falls vorhanden)"""
        try:
            with zipfile.ZipFile(package_path, 'r') as zipf:
                # Suche post_update.py
                post_scripts = [f for f in zipf.namelist() if f.endswith('post_update.py')]
                
                if not post_scripts:
                    return
                
                # Extrahiere in temporäres Verzeichnis und führe aus
                with tempfile.TemporaryDirectory() as temp_dir:
                    script_path = Path(temp_dir) / 'post_update.py'
                    
                    with zipf.open(post_scripts[0]) as source:
                        script_path.write_bytes(source.read())
                    
                    # Führe Script aus
                    import subprocess
                    subprocess.run([sys.executable, str(script_path)], 
                                   cwd=str(self.app_dir),
                                   capture_output=True)
        except:
            pass  # Post-Update Fehler sind nicht kritisch
    
    def _save_update_history(self, old_version: str, new_version: str, backup_path: str):
        """Speichert Update in Historie"""
        history = []
        
        if self.update_history_file.exists():
            with open(self.update_history_file, 'r') as f:
                history = json.load(f)
        
        history.append({
            'timestamp': datetime.now().isoformat(),
            'from_version': old_version,
            'to_version': new_version,
            'backup_path': backup_path,
        })
        
        self.update_history_file.parent.mkdir(exist_ok=True)
        with open(self.update_history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def get_update_history(self) -> List[Dict]:
        """Gibt die Update-Historie zurück"""
        if not self.update_history_file.exists():
            return []
        
        with open(self.update_history_file, 'r') as f:
            return json.load(f)
    
    def rollback_to_backup(self, backup_path: str) -> Tuple[bool, str]:
        """
        Führt Rollback zu einem Backup durch
        
        Args:
            backup_path: Pfad zum Backup
        
        Returns:
            Tuple[success, message]
        """
        self._set_status(self.STATUS_ROLLING_BACK, 0, "Starte Rollback...")
        
        try:
            # Restore durchführen
            success, message = self.backup_manager.restore_backup(
                backup_path,
                restore_database=True,
                restore_config=True,
                restore_uploads=False  # Uploads normalerweise nicht überschreiben
            )
            
            if success:
                # Version aus Backup wiederherstellen
                backup_info = self.backup_manager._read_backup_info(Path(backup_path))
                if backup_info and backup_info.get('version'):
                    self.set_current_version(backup_info['version'])
                
                self._set_status(self.STATUS_COMPLETE, 100, "Rollback erfolgreich!")
            else:
                self._set_status(self.STATUS_FAILED, 0, message)
            
            return success, message
            
        except Exception as e:
            self._set_status(self.STATUS_FAILED, 0, str(e))
            return False, str(e)
    
    def _version_greater(self, v1: str, v2: str) -> bool:
        """Prüft ob v1 > v2"""
        try:
            def parse_version(v):
                return [int(x) for x in v.replace('-', '.').split('.')[:3]]
            
            return parse_version(v1) > parse_version(v2)
        except:
            return v1 > v2
    
    def _version_greater_or_equal(self, v1: str, v2: str) -> bool:
        """Prüft ob v1 >= v2"""
        return v1 == v2 or self._version_greater(v1, v2)
    
    def _calculate_file_checksum(self, file_path: str) -> str:
        """Berechnet SHA256-Checksum einer Datei"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()


# CLI-Interface
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='StitchAdmin Update Manager')
    subparsers = parser.add_subparsers(dest='command', help='Verfügbare Befehle')
    
    # version
    version_parser = subparsers.add_parser('version', help='Zeigt aktuelle Version')
    
    # install
    install_parser = subparsers.add_parser('install', help='Update installieren')
    install_parser.add_argument('package', help='Pfad zum Update-Paket (.zip)')
    install_parser.add_argument('--no-backup', action='store_true',
                                help='Kein Backup vor Update erstellen')
    
    # info
    info_parser = subparsers.add_parser('info', help='Update-Paket Info anzeigen')
    info_parser.add_argument('package', help='Pfad zum Update-Paket (.zip)')
    
    # history
    history_parser = subparsers.add_parser('history', help='Update-Historie anzeigen')
    
    # rollback
    rollback_parser = subparsers.add_parser('rollback', help='Rollback zu Backup')
    rollback_parser.add_argument('backup', help='Pfad zum Backup')
    
    args = parser.parse_args()
    
    manager = UpdateManager()
    
    if args.command == 'version':
        print(f"StitchAdmin Version: {manager.get_current_version()}")
    
    elif args.command == 'install':
        result = manager.install_update(
            args.package,
            create_backup=not args.no_backup
        )
        
        print(f"\n{'='*60}")
        if result.success:
            print(f"✓ {result.message}")
            print(f"  Von: {result.old_version} → Nach: {result.new_version}")
            if result.backup_path:
                print(f"  Backup: {result.backup_path}")
            if result.requires_restart:
                print(f"\n  ⚠ Bitte starten Sie StitchAdmin neu!")
        else:
            print(f"✗ {result.message}")
        print(f"{'='*60}\n")
        
        sys.exit(0 if result.success else 1)
    
    elif args.command == 'info':
        success, message, info = manager.read_update_package(args.package)
        
        if success:
            print(f"\nUpdate-Paket Information:")
            print(f"{'='*40}")
            print(f"Version:        {info.version}")
            print(f"Datum:          {info.release_date}")
            print(f"Größe:          {info.size_bytes / (1024*1024):.1f} MB")
            print(f"Min. Version:   {info.min_version or 'Keine'}")
            print(f"Breaking:       {'Ja' if info.breaking_changes else 'Nein'}")
            print(f"\nChangelog:")
            for item in info.changelog:
                print(f"  • {item}")
        else:
            print(f"Fehler: {message}")
    
    elif args.command == 'history':
        history = manager.get_update_history()
        
        if not history:
            print("Keine Update-Historie vorhanden.")
        else:
            print(f"\n{'Datum':<20} {'Von':<12} {'Nach':<12}")
            print("-" * 50)
            for entry in reversed(history[-10:]):
                timestamp = entry['timestamp'][:19].replace('T', ' ')
                print(f"{timestamp:<20} {entry['from_version']:<12} {entry['to_version']:<12}")
    
    elif args.command == 'rollback':
        success, message = manager.rollback_to_backup(args.backup)
        print(message)
        sys.exit(0 if success else 1)
    
    else:
        parser.print_help()
