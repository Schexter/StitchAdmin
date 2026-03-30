# -*- coding: utf-8 -*-
"""
FILE STORAGE SERVICE
====================
Einheitlicher Dateizugriff fuer alle Storage-Backends:
- Lokal (Einzelplatz)
- Geteilter Ordner (Netzwerk/SMB)
- Cloud-Sync (Nextcloud/Dropbox-Ordner lokal)
- WebDAV (Remote-Zugriff)

In der Datenbank werden NUR relative Pfade gespeichert.
Der Service loest den vollstaendigen Pfad je nach Backend auf.

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import shutil
import hashlib
import logging
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class FileStorageService:
    """Zentraler Service fuer alle Dateioperationen"""

    def __init__(self, settings=None):
        """
        Args:
            settings: StorageSettings-Objekt oder None (laedt automatisch)
        """
        self._settings = settings

    @property
    def settings(self):
        """Lazy-Load StorageSettings"""
        if self._settings is None:
            from src.models.storage_settings import StorageSettings
            self._settings = StorageSettings.get_settings()
        return self._settings

    @property
    def base_path(self):
        """Effektiver Basispfad (konfiguriert oder Default)"""
        bp = self.settings.base_path
        if bp:
            return os.path.normpath(bp)
        return os.path.normpath(os.path.join(os.path.expanduser('~'), 'StitchAdmin', 'Dokumente'))

    # =========================================================================
    # PFAD-AUFLOESUNG: relativ <-> absolut
    # =========================================================================

    def resolve_path(self, relative_path):
        """
        Loest einen relativen DB-Pfad zum vollstaendigen Dateisystempfad auf.

        Args:
            relative_path: z.B. 'Kunden/K-2026-0042/logos/firmenlogo.png'

        Returns:
            Absoluter Pfad als String oder None wenn relative_path leer
        """
        if not relative_path:
            return None

        # Bereits absolut? Direkt zurueckgeben (Abwaertskompatibilitaet)
        if os.path.isabs(relative_path):
            return os.path.normpath(relative_path)

        return os.path.normpath(os.path.join(self.base_path, relative_path))

    def to_relative(self, absolute_path):
        """
        Konvertiert einen absoluten Pfad in einen relativen DB-Pfad.

        Args:
            absolute_path: z.B. 'C:\\StitchAdmin\\Dokumente\\Kunden\\logo.png'

        Returns:
            Relativer Pfad oder der Original-Pfad wenn nicht unter base_path
        """
        if not absolute_path:
            return ''

        abs_norm = os.path.normpath(absolute_path)
        base_norm = self.base_path

        try:
            rel = os.path.relpath(abs_norm, base_norm)
            # Wenn der relative Pfad mit .. beginnt, liegt er nicht unter base_path
            if rel.startswith('..'):
                return absolute_path
            return rel.replace('\\', '/')
        except ValueError:
            # Verschiedene Laufwerke (z.B. C: vs D:)
            return absolute_path

    def resolve_for_doc_type(self, doc_type, kunde_name=None, datum=None):
        """
        Gibt den vollstaendigen Ordnerpfad fuer einen Dokumenttyp zurueck.
        Nutzt die StorageSettings-Konfiguration (inkl. NAS-Archive).

        Returns:
            Absoluter Ordnerpfad
        """
        return self.settings.get_full_path(doc_type, kunde_name, datum)

    # =========================================================================
    # DATEI-OPERATIONEN
    # =========================================================================

    def save_file(self, file_data, doc_type, filename, kunde_name=None, datum=None):
        """
        Speichert eine Datei im konfigurierten Storage-Backend.

        Args:
            file_data: bytes, BytesIO, oder Werkzeug FileStorage
            doc_type: Dokumenttyp ('rechnung', 'angebot', 'design', etc.)
            filename: Gewuenschter Dateiname
            kunde_name: Kundenname fuer Ordnerstruktur
            datum: Datum fuer Ordnerstruktur (default: heute)

        Returns:
            dict mit 'success', 'relative_path', 'absolute_path', 'file_hash'
        """
        if datum is None:
            datum = date.today()

        try:
            # Zielordner ermitteln und erstellen
            target_dir = self.settings.get_full_path(doc_type, kunde_name, datum)
            os.makedirs(target_dir, exist_ok=True)

            # Sicheren Dateinamen generieren
            safe_name = self._safe_filename(filename)
            target_path = os.path.join(target_dir, safe_name)

            # Dateiname eindeutig machen wenn noetig
            target_path = self._unique_path(target_path)

            # Datei schreiben
            file_bytes = self._read_file_data(file_data)
            with open(target_path, 'wb') as f:
                f.write(file_bytes)

            # Hash berechnen
            file_hash = hashlib.sha256(file_bytes).hexdigest()

            # Relativen Pfad fuer DB
            relative_path = self.to_relative(target_path)

            logger.info(f"Datei gespeichert: {relative_path} ({len(file_bytes)} bytes)")

            # Cloud-Sync wenn aktiviert
            cloud_result = None
            if self.settings.should_cloud_sync(doc_type):
                cloud_result = self._cloud_sync(target_path, doc_type, kunde_name, datum, safe_name)

            return {
                'success': True,
                'relative_path': relative_path,
                'absolute_path': target_path,
                'filename': os.path.basename(target_path),
                'file_hash': file_hash,
                'file_size': len(file_bytes),
                'cloud_synced': cloud_result.get('success', False) if cloud_result else False
            }

        except Exception as e:
            logger.error(f"Fehler beim Speichern: {e}")
            return {'success': False, 'error': str(e)}

    def get_file(self, relative_path):
        """
        Liest eine Datei aus dem Storage.

        Args:
            relative_path: Relativer Pfad aus der DB

        Returns:
            dict mit 'success', 'data' (bytes), 'absolute_path', 'exists'
        """
        abs_path = self.resolve_path(relative_path)
        if not abs_path:
            return {'success': False, 'exists': False, 'error': 'Kein Pfad angegeben'}

        if os.path.exists(abs_path):
            try:
                with open(abs_path, 'rb') as f:
                    data = f.read()
                return {
                    'success': True,
                    'exists': True,
                    'data': data,
                    'absolute_path': abs_path,
                    'filename': os.path.basename(abs_path),
                    'file_size': len(data)
                }
            except Exception as e:
                return {'success': False, 'exists': True, 'error': str(e)}

        # Datei lokal nicht gefunden - versuche Cloud-Download
        if self.settings.cloud_enabled:
            return self._cloud_download(relative_path)

        return {'success': False, 'exists': False, 'error': f'Datei nicht gefunden: {abs_path}'}

    def file_exists(self, relative_path):
        """Prueft ob eine Datei existiert"""
        abs_path = self.resolve_path(relative_path)
        return abs_path is not None and os.path.exists(abs_path)

    def delete_file(self, relative_path):
        """
        Loescht eine Datei aus dem Storage.

        Returns:
            dict mit 'success', 'message'
        """
        abs_path = self.resolve_path(relative_path)
        if not abs_path or not os.path.exists(abs_path):
            return {'success': False, 'error': 'Datei nicht gefunden'}

        try:
            os.remove(abs_path)
            logger.info(f"Datei geloescht: {relative_path}")
            return {'success': True, 'message': 'Datei geloescht'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def move_file(self, relative_path, new_doc_type, kunde_name=None, datum=None):
        """
        Verschiebt eine Datei in einen anderen Dokumenttyp-Ordner.

        Returns:
            dict mit 'success', 'new_relative_path'
        """
        abs_path = self.resolve_path(relative_path)
        if not abs_path or not os.path.exists(abs_path):
            return {'success': False, 'error': 'Quelldatei nicht gefunden'}

        try:
            target_dir = self.settings.get_full_path(new_doc_type, kunde_name, datum)
            os.makedirs(target_dir, exist_ok=True)

            filename = os.path.basename(abs_path)
            new_path = os.path.join(target_dir, filename)
            new_path = self._unique_path(new_path)

            shutil.move(abs_path, new_path)

            new_relative = self.to_relative(new_path)
            logger.info(f"Datei verschoben: {relative_path} -> {new_relative}")

            return {'success': True, 'new_relative_path': new_relative, 'new_absolute_path': new_path}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # =========================================================================
    # VERZEICHNIS-OPERATIONEN (fuer File Browser)
    # =========================================================================

    def list_directory(self, relative_path='', doc_type=None, extensions=None):
        """
        Listet Inhalte eines Verzeichnisses.

        Args:
            relative_path: Relativer Pfad oder '' fuer Root
            doc_type: Optional - direkt einen Dokumenttyp-Ordner listen
            extensions: Optional - nur bestimmte Dateitypen (z.B. ['.dst', '.png'])

        Returns:
            dict mit 'items' (Liste von Dateien/Ordnern), 'current_path'
        """
        if doc_type:
            abs_path = self.settings.get_full_path(doc_type)
        elif relative_path:
            abs_path = self.resolve_path(relative_path)
        else:
            abs_path = self.base_path

        if not abs_path or not os.path.exists(abs_path):
            return {'items': [], 'current_path': abs_path or '', 'error': 'Pfad nicht gefunden'}

        items = []
        try:
            for entry in sorted(os.listdir(abs_path)):
                if entry.startswith('.'):
                    continue

                full = os.path.join(abs_path, entry)
                is_dir = os.path.isdir(full)

                if not is_dir and extensions:
                    ext = os.path.splitext(entry)[1].lower()
                    if ext not in extensions:
                        continue

                item = {
                    'name': entry,
                    'relative_path': self.to_relative(full),
                    'absolute_path': full,
                    'is_dir': is_dir,
                }

                if not is_dir:
                    try:
                        stat = os.stat(full)
                        item['size'] = stat.st_size
                        item['size_display'] = self._format_size(stat.st_size)
                        item['modified'] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                    except OSError:
                        pass

                items.append(item)

        except PermissionError:
            return {'items': [], 'current_path': abs_path, 'error': 'Keine Berechtigung'}
        except Exception as e:
            return {'items': [], 'current_path': abs_path, 'error': str(e)}

        return {
            'items': items,
            'current_path': abs_path,
            'relative_path': self.to_relative(abs_path),
            'breadcrumbs': self._breadcrumbs(abs_path)
        }

    def get_storage_roots(self):
        """
        Gibt alle konfigurierten Speicherorte zurueck (fuer File Browser Root-Ansicht).

        Returns:
            Liste von dicts mit 'name', 'path', 'type', 'available'
        """
        roots = []

        # Basispfad
        bp = self.base_path
        roots.append({
            'name': 'Dokumente',
            'path': bp,
            'type': 'base',
            'available': os.path.exists(bp)
        })

        # Separate Archive
        s = self.settings
        archives = [
            ('Design-Archiv', s.design_archiv_path, s.design_archiv_aktiv),
            ('Stickdateien', s.stickdateien_path, s.stickdateien_aktiv),
            ('Freigaben-Archiv', s.freigaben_archiv_path, s.freigaben_archiv_aktiv),
            ('Motiv-Archiv', s.motiv_archiv_path, s.motiv_archiv_aktiv),
        ]

        for name, path, active in archives:
            if active and path:
                roots.append({
                    'name': name,
                    'path': os.path.normpath(path),
                    'type': 'archive',
                    'available': os.path.exists(path)
                })

        return roots

    def get_file_url(self, relative_path):
        """
        Generiert einen Hyperlink/URL zum Oeffnen einer Datei.

        Fuer lokale Dateien: file:///C:/... (oeffnet im OS-Standard-Programm)
        Fuer Cloud-Dateien: WebDAV-URL

        Returns:
            URL als String
        """
        abs_path = self.resolve_path(relative_path)
        if not abs_path:
            return None

        # file:// URL generieren (funktioniert lokal + Netzwerk)
        # Backslashes zu Forward-Slashes
        file_url = abs_path.replace('\\', '/')

        # UNC-Pfade: \\server\share -> file://server/share
        if file_url.startswith('//'):
            return f"file:{file_url}"

        # Lokale Pfade: C:/... -> file:///C:/...
        return f"file:///{file_url}"

    def get_folder_url(self, relative_path='', doc_type=None):
        """
        Generiert einen Hyperlink zum Oeffnen eines Ordners im Explorer/Finder.

        Returns:
            file:// URL als String
        """
        if doc_type:
            abs_path = self.settings.get_full_path(doc_type)
        elif relative_path:
            abs_path = self.resolve_path(relative_path)
        else:
            abs_path = self.base_path

        if not abs_path:
            return None

        file_url = abs_path.replace('\\', '/')
        if file_url.startswith('//'):
            return f"file:{file_url}"
        return f"file:///{file_url}"

    # =========================================================================
    # MIGRATION: Absolute -> Relative Pfade
    # =========================================================================

    def migrate_absolute_paths(self, model_class, path_field='file_path', dry_run=True):
        """
        Migriert absolute Pfade in der DB zu relativen Pfaden.

        Args:
            model_class: SQLAlchemy Model-Klasse
            path_field: Name des Pfad-Feldes
            dry_run: True = nur anzeigen, False = tatsaechlich aendern

        Returns:
            dict mit 'total', 'migrated', 'skipped', 'details'
        """
        from src.models import db

        records = model_class.query.all()
        results = {'total': len(records), 'migrated': 0, 'skipped': 0, 'details': []}

        for record in records:
            old_path = getattr(record, path_field, None)
            if not old_path:
                results['skipped'] += 1
                continue

            if not os.path.isabs(old_path):
                results['skipped'] += 1
                continue

            new_path = self.to_relative(old_path)
            if new_path == old_path:
                # Konnte nicht konvertiert werden (anderes Laufwerk etc.)
                results['skipped'] += 1
                results['details'].append(f"SKIP: {old_path} (nicht unter base_path)")
                continue

            results['details'].append(f"{old_path} -> {new_path}")
            results['migrated'] += 1

            if not dry_run:
                setattr(record, path_field, new_path)

        if not dry_run:
            try:
                db.session.commit()
                logger.info(f"Migration: {results['migrated']} Pfade konvertiert in {model_class.__name__}")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Migration fehlgeschlagen: {e}")
                results['error'] = str(e)

        return results

    # =========================================================================
    # HILFSFUNKTIONEN
    # =========================================================================

    def _safe_filename(self, filename):
        """Bereinigt Dateinamen"""
        # Nur den Dateinamen, nicht den Pfad
        filename = os.path.basename(filename)
        # Ungueltige Zeichen ersetzen
        invalid = '<>:"/\\|?*'
        for c in invalid:
            filename = filename.replace(c, '_')
        # Fuehrende Punkte entfernen (versteckte Dateien)
        filename = filename.lstrip('.')
        return filename or 'unnamed'

    def _unique_path(self, path):
        """Macht einen Dateipfad eindeutig durch Nummerierung"""
        if not os.path.exists(path):
            return path

        base, ext = os.path.splitext(path)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        return f"{base}_{counter}{ext}"

    def _read_file_data(self, file_data):
        """Liest Datei-Daten aus verschiedenen Quellen"""
        if isinstance(file_data, bytes):
            return file_data
        elif hasattr(file_data, 'read'):
            # BytesIO, FileStorage, etc.
            file_data.seek(0)
            return file_data.read()
        else:
            raise ValueError(f"Unbekannter Dateityp: {type(file_data)}")

    def _format_size(self, size_bytes):
        """Formatiert Dateigroesse"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def _breadcrumbs(self, abs_path):
        """Erzeugt Breadcrumb-Navigation"""
        crumbs = []
        base_norm = os.path.normpath(self.base_path)

        # Relative Teile aufloesen
        try:
            rel = os.path.relpath(abs_path, base_norm)
            if rel == '.' or rel.startswith('..'):
                # Nicht unter base_path - vollstaendigen Pfad zeigen
                parts = abs_path.replace('\\', '/').split('/')
                current = ''
                for part in parts:
                    if part:
                        current = f"{current}/{part}" if current else part
                        crumbs.append({'name': part, 'path': current})
            else:
                # Unter base_path - ab dort anzeigen
                crumbs.append({'name': 'Dokumente', 'path': base_norm})
                parts = rel.replace('\\', '/').split('/')
                current = base_norm
                for part in parts:
                    if part and part != '.':
                        current = os.path.join(current, part)
                        crumbs.append({'name': part, 'path': current})
        except ValueError:
            crumbs.append({'name': abs_path, 'path': abs_path})

        return crumbs

    def _cloud_sync(self, local_path, doc_type, kunde_name, datum, filename):
        """Synchronisiert eine Datei in die Cloud"""
        try:
            from src.services.webdav_service import WebDAVService
            webdav = WebDAVService(self.settings)
            return webdav.upload_file(local_path, doc_type, kunde_name, datum, filename)
        except Exception as e:
            logger.warning(f"Cloud-Sync fehlgeschlagen: {e}")
            return {'success': False, 'error': str(e)}

    def _cloud_download(self, relative_path):
        """Versucht eine Datei aus der Cloud zu laden"""
        try:
            from src.services.webdav_service import WebDAVService
            webdav = WebDAVService(self.settings)

            cloud_path = self.settings.cloud_base_path.rstrip('/') + '/' + relative_path.replace('\\', '/')
            data = webdav.download_file(cloud_path)

            if data:
                # Lokal cachen
                abs_path = self.resolve_path(relative_path)
                if abs_path:
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    with open(abs_path, 'wb') as f:
                        f.write(data)
                    logger.info(f"Cloud-Download gecacht: {relative_path}")

                return {
                    'success': True,
                    'exists': True,
                    'data': data,
                    'absolute_path': abs_path,
                    'filename': os.path.basename(relative_path),
                    'file_size': len(data),
                    'source': 'cloud'
                }
            return {'success': False, 'exists': False, 'error': 'Datei auch in Cloud nicht gefunden'}
        except Exception as e:
            return {'success': False, 'exists': False, 'error': str(e)}
