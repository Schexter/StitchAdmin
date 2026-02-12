# -*- coding: utf-8 -*-
"""
StitchAdmin 2.0 - Backup Manager
Automatische Sicherung vor Updates und manuelle Backups

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import sys
import json
import shutil
import zipfile
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List, Dict

class BackupManager:
    """
    Verwaltet Backups für StitchAdmin
    
    Backup-Struktur:
    {backup_folder}/
    ├── backup_2025-01-15_14-30-00_pre_update/
    │   ├── database/
    │   │   └── stitchadmin.db
    │   ├── config/
    │   │   ├── .env
    │   │   ├── company.json
    │   │   └── ...
    │   ├── uploads/
    │   │   └── ... (optional)
    │   └── backup_info.json
    └── backup_2025-01-15_14-30-00_pre_update.zip (komprimiert)
    """
    
    # Backup-Typen
    TYPE_MANUAL = 'manual'
    TYPE_PRE_UPDATE = 'pre_update'
    TYPE_SCHEDULED = 'scheduled'
    TYPE_PRE_MIGRATION = 'pre_migration'
    
    def __init__(self, app_dir: Path = None, backup_dir: Path = None):
        """
        Initialisiert den Backup-Manager
        
        Args:
            app_dir: Anwendungsverzeichnis (wo die App installiert ist)
            backup_dir: Backup-Verzeichnis (aus Konfiguration oder Standard)
        """
        self.app_dir = Path(app_dir) if app_dir else Path(__file__).parent.parent.parent
        
        # Backup-Verzeichnis ermitteln
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            # Versuche aus .env zu laden
            self.backup_dir = self._get_backup_dir_from_config()
        
        # Stelle sicher, dass Backup-Verzeichnis existiert
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Standard-Einstellungen
        self.max_backups = 10  # Maximale Anzahl Backups behalten
        self.include_uploads = False  # Uploads sind oft groß
        self.compress = True  # ZIP-Kompression
        
    def _get_backup_dir_from_config(self) -> Path:
        """Liest Backup-Verzeichnis aus Konfiguration"""
        # Versuche .env zu lesen
        env_file = self.app_dir / '.env'
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('BACKUP_FOLDER='):
                        path = line.split('=', 1)[1].strip()
                        if path:
                            return Path(path)
        
        # Versuche company.json zu lesen
        config_file = self.app_dir / 'config' / 'company.json'
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                path = config.get('paths', {}).get('backups')
                if path:
                    return Path(path)
        
        # Standard-Verzeichnis
        return self.app_dir / 'backups'
    
    def create_backup(self, 
                      backup_type: str = TYPE_MANUAL,
                      description: str = '',
                      include_uploads: bool = None) -> Tuple[bool, str, Optional[Path]]:
        """
        Erstellt ein vollständiges Backup
        
        Args:
            backup_type: Art des Backups (manual, pre_update, scheduled, pre_migration)
            description: Optionale Beschreibung
            include_uploads: Uploads einschließen? (überschreibt Standard)
        
        Returns:
            Tuple[success, message, backup_path]
        """
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_name = f"backup_{timestamp}_{backup_type}"
        backup_path = self.backup_dir / backup_name
        
        include_uploads = include_uploads if include_uploads is not None else self.include_uploads
        
        try:
            # Erstelle Backup-Verzeichnis
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # 1. Datenbank sichern
            db_backup_path = backup_path / 'database'
            db_backup_path.mkdir(exist_ok=True)
            self._backup_database(db_backup_path)
            
            # 2. Konfiguration sichern
            config_backup_path = backup_path / 'config'
            config_backup_path.mkdir(exist_ok=True)
            self._backup_config(config_backup_path)
            
            # 3. Uploads sichern (optional)
            if include_uploads:
                uploads_backup_path = backup_path / 'uploads'
                uploads_backup_path.mkdir(exist_ok=True)
                self._backup_uploads(uploads_backup_path)
            
            # 4. Backup-Info erstellen
            backup_info = {
                'version': self._get_app_version(),
                'timestamp': datetime.now().isoformat(),
                'type': backup_type,
                'description': description,
                'include_uploads': include_uploads,
                'files': self._list_backup_files(backup_path),
                'database_checksum': self._calculate_checksum(db_backup_path / 'stitchadmin.db'),
                'hostname': os.environ.get('COMPUTERNAME', 'unknown'),
            }
            
            info_file = backup_path / 'backup_info.json'
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(backup_info, f, indent=2, ensure_ascii=False)
            
            # 5. Optional: ZIP-Kompression
            zip_path = None
            if self.compress:
                zip_path = self._compress_backup(backup_path)
                # Original-Verzeichnis nach Kompression löschen
                shutil.rmtree(backup_path)
                backup_path = zip_path
            
            # 6. Alte Backups aufräumen
            self._cleanup_old_backups()
            
            return True, f"Backup erfolgreich erstellt: {backup_path.name}", backup_path
            
        except Exception as e:
            # Bei Fehler: Aufräumen
            if backup_path.exists():
                shutil.rmtree(backup_path, ignore_errors=True)
            return False, f"Backup fehlgeschlagen: {str(e)}", None
    
    def _backup_database(self, target_dir: Path):
        """Sichert die SQLite-Datenbank"""
        # Finde Datenbank
        possible_paths = [
            self.app_dir / 'instance' / 'stitchadmin.db',
            self.app_dir / 'instance' / 'app.db',
            self.app_dir / 'stitchadmin.db',
        ]
        
        db_path = None
        for path in possible_paths:
            if path.exists():
                db_path = path
                break
        
        if not db_path:
            raise FileNotFoundError("Datenbank nicht gefunden!")
        
        # SQLite Online-Backup (sicher auch bei laufender Anwendung)
        target_db = target_dir / 'stitchadmin.db'
        
        # Verbinde zur Quell-Datenbank
        source_conn = sqlite3.connect(str(db_path))
        target_conn = sqlite3.connect(str(target_db))
        
        # Backup durchführen
        source_conn.backup(target_conn)
        
        source_conn.close()
        target_conn.close()
    
    def _backup_config(self, target_dir: Path):
        """Sichert Konfigurationsdateien"""
        # .env Datei
        env_file = self.app_dir / '.env'
        if env_file.exists():
            shutil.copy2(env_file, target_dir / '.env')
        
        # config/ Verzeichnis
        config_dir = self.app_dir / 'config'
        if config_dir.exists():
            for item in config_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, target_dir / item.name)
    
    def _backup_uploads(self, target_dir: Path):
        """Sichert Upload-Verzeichnis"""
        uploads_dir = self.app_dir / 'instance' / 'uploads'
        if uploads_dir.exists():
            shutil.copytree(uploads_dir, target_dir, dirs_exist_ok=True)
    
    def _compress_backup(self, backup_path: Path) -> Path:
        """Komprimiert Backup als ZIP"""
        zip_path = backup_path.with_suffix('.zip')
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(backup_path):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(backup_path)
                    zipf.write(file_path, arcname)
        
        return zip_path
    
    def _list_backup_files(self, backup_path: Path) -> List[Dict]:
        """Listet alle Dateien im Backup"""
        files = []
        for root, dirs, filenames in os.walk(backup_path):
            for filename in filenames:
                file_path = Path(root) / filename
                files.append({
                    'path': str(file_path.relative_to(backup_path)),
                    'size': file_path.stat().st_size,
                })
        return files
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Berechnet SHA256-Checksum einer Datei"""
        if not file_path.exists():
            return ''
        
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _get_app_version(self) -> str:
        """Ermittelt die aktuelle App-Version"""
        try:
            # Versuche aus build_config zu lesen
            sys.path.insert(0, str(self.app_dir))
            from build_config import APP_VERSION
            return APP_VERSION
        except:
            pass
        
        # Versuche aus version.txt zu lesen
        version_file = self.app_dir / 'version.txt'
        if version_file.exists():
            return version_file.read_text().strip()
        
        return 'unknown'
    
    def _cleanup_old_backups(self):
        """Löscht alte Backups über dem Limit"""
        backups = self.list_backups()
        
        if len(backups) > self.max_backups:
            # Sortiere nach Datum (älteste zuerst)
            backups_sorted = sorted(backups, key=lambda x: x['timestamp'])
            
            # Lösche älteste
            to_delete = len(backups) - self.max_backups
            for backup in backups_sorted[:to_delete]:
                self.delete_backup(backup['path'])
    
    def list_backups(self) -> List[Dict]:
        """Listet alle verfügbaren Backups"""
        backups = []
        
        for item in self.backup_dir.iterdir():
            if item.name.startswith('backup_'):
                backup_info = self._read_backup_info(item)
                if backup_info:
                    backups.append({
                        'name': item.name,
                        'path': str(item),
                        'timestamp': backup_info.get('timestamp', ''),
                        'type': backup_info.get('type', 'unknown'),
                        'version': backup_info.get('version', 'unknown'),
                        'description': backup_info.get('description', ''),
                        'size': self._get_size(item),
                        'is_compressed': item.suffix == '.zip',
                    })
        
        # Sortiere nach Datum (neueste zuerst)
        backups.sort(key=lambda x: x['timestamp'], reverse=True)
        return backups
    
    def _read_backup_info(self, backup_path: Path) -> Optional[Dict]:
        """Liest Backup-Info aus einem Backup"""
        try:
            if backup_path.suffix == '.zip':
                # ZIP-Datei
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    with zipf.open('backup_info.json') as f:
                        return json.load(f)
            else:
                # Verzeichnis
                info_file = backup_path / 'backup_info.json'
                if info_file.exists():
                    with open(info_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
        except:
            pass
        return None
    
    def _get_size(self, path: Path) -> int:
        """Ermittelt Größe einer Datei oder eines Verzeichnisses"""
        if path.is_file():
            return path.stat().st_size
        
        total = 0
        for item in path.rglob('*'):
            if item.is_file():
                total += item.stat().st_size
        return total
    
    def restore_backup(self, backup_path: str, 
                       restore_database: bool = True,
                       restore_config: bool = True,
                       restore_uploads: bool = False) -> Tuple[bool, str]:
        """
        Stellt ein Backup wieder her
        
        Args:
            backup_path: Pfad zum Backup (ZIP oder Verzeichnis)
            restore_database: Datenbank wiederherstellen?
            restore_config: Konfiguration wiederherstellen?
            restore_uploads: Uploads wiederherstellen?
        
        Returns:
            Tuple[success, message]
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            return False, f"Backup nicht gefunden: {backup_path}"
        
        try:
            # Temporäres Verzeichnis für Extraktion
            temp_dir = None
            
            if backup_path.suffix == '.zip':
                temp_dir = self.backup_dir / f"_restore_temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                temp_dir.mkdir()
                
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    zipf.extractall(temp_dir)
                
                source_dir = temp_dir
            else:
                source_dir = backup_path
            
            # 1. Datenbank wiederherstellen
            if restore_database:
                db_source = source_dir / 'database' / 'stitchadmin.db'
                if db_source.exists():
                    db_target = self.app_dir / 'instance' / 'stitchadmin.db'
                    
                    # Backup der aktuellen DB (für Notfall)
                    if db_target.exists():
                        emergency_backup = db_target.with_suffix('.db.bak')
                        shutil.copy2(db_target, emergency_backup)
                    
                    shutil.copy2(db_source, db_target)
            
            # 2. Konfiguration wiederherstellen
            if restore_config:
                config_source = source_dir / 'config'
                if config_source.exists():
                    for item in config_source.iterdir():
                        if item.is_file():
                            if item.name == '.env':
                                target = self.app_dir / '.env'
                            else:
                                target = self.app_dir / 'config' / item.name
                            shutil.copy2(item, target)
            
            # 3. Uploads wiederherstellen
            if restore_uploads:
                uploads_source = source_dir / 'uploads'
                if uploads_source.exists():
                    uploads_target = self.app_dir / 'instance' / 'uploads'
                    shutil.copytree(uploads_source, uploads_target, dirs_exist_ok=True)
            
            # Aufräumen
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir)
            
            return True, "Backup erfolgreich wiederhergestellt!"
            
        except Exception as e:
            # Aufräumen bei Fehler
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            return False, f"Wiederherstellung fehlgeschlagen: {str(e)}"
    
    def delete_backup(self, backup_path: str) -> Tuple[bool, str]:
        """Löscht ein Backup"""
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            return False, f"Backup nicht gefunden: {backup_path}"
        
        try:
            if backup_path.is_file():
                backup_path.unlink()
            else:
                shutil.rmtree(backup_path)
            
            return True, f"Backup gelöscht: {backup_path.name}"
        except Exception as e:
            return False, f"Löschen fehlgeschlagen: {str(e)}"


# Singleton-Instanz für einfachen Zugriff
_backup_manager = None

def get_backup_manager() -> BackupManager:
    """Gibt die Backup-Manager Instanz zurück"""
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager()
    return _backup_manager


# CLI-Interface
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='StitchAdmin Backup Manager')
    subparsers = parser.add_subparsers(dest='command', help='Verfügbare Befehle')
    
    # backup create
    create_parser = subparsers.add_parser('create', help='Backup erstellen')
    create_parser.add_argument('--type', default='manual', 
                               choices=['manual', 'pre_update', 'scheduled'],
                               help='Backup-Typ')
    create_parser.add_argument('--description', default='', help='Beschreibung')
    create_parser.add_argument('--include-uploads', action='store_true',
                               help='Uploads einschließen')
    
    # backup list
    list_parser = subparsers.add_parser('list', help='Backups auflisten')
    
    # backup restore
    restore_parser = subparsers.add_parser('restore', help='Backup wiederherstellen')
    restore_parser.add_argument('backup', help='Backup-Name oder Pfad')
    restore_parser.add_argument('--no-database', action='store_true',
                                help='Datenbank nicht wiederherstellen')
    restore_parser.add_argument('--no-config', action='store_true',
                                help='Konfiguration nicht wiederherstellen')
    restore_parser.add_argument('--include-uploads', action='store_true',
                                help='Uploads wiederherstellen')
    
    # backup delete
    delete_parser = subparsers.add_parser('delete', help='Backup löschen')
    delete_parser.add_argument('backup', help='Backup-Name oder Pfad')
    
    args = parser.parse_args()
    
    manager = BackupManager()
    
    if args.command == 'create':
        success, message, path = manager.create_backup(
            backup_type=args.type,
            description=args.description,
            include_uploads=args.include_uploads
        )
        print(message)
        sys.exit(0 if success else 1)
    
    elif args.command == 'list':
        backups = manager.list_backups()
        if not backups:
            print("Keine Backups gefunden.")
        else:
            print(f"\n{'Name':<50} {'Datum':<20} {'Typ':<12} {'Größe':<10}")
            print("-" * 95)
            for backup in backups:
                size_mb = backup['size'] / (1024 * 1024)
                timestamp = backup['timestamp'][:19].replace('T', ' ')
                print(f"{backup['name']:<50} {timestamp:<20} {backup['type']:<12} {size_mb:.1f} MB")
    
    elif args.command == 'restore':
        # Finde Backup
        backup_path = Path(args.backup)
        if not backup_path.exists():
            backup_path = manager.backup_dir / args.backup
        
        success, message = manager.restore_backup(
            str(backup_path),
            restore_database=not args.no_database,
            restore_config=not args.no_config,
            restore_uploads=args.include_uploads
        )
        print(message)
        sys.exit(0 if success else 1)
    
    elif args.command == 'delete':
        backup_path = Path(args.backup)
        if not backup_path.exists():
            backup_path = manager.backup_dir / args.backup
        
        success, message = manager.delete_backup(str(backup_path))
        print(message)
        sys.exit(0 if success else 1)
    
    else:
        parser.print_help()
