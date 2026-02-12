# -*- coding: utf-8 -*-
"""
STORAGE SETTINGS MODEL
======================
Zentrale Konfiguration für alle Speicherpfade

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime
import os
from src.models import db


class StorageSettings(db.Model):
    """Speicherpfad-Einstellungen für alle Dokumente"""
    __tablename__ = 'storage_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # === BASISPFADE ===
    # Hauptverzeichnis für Geschäftsdokumente (Angebote, Rechnungen, etc.)
    base_path = db.Column(db.String(500), default='')  # z.B. C:\StitchAdmin\Dokumente
    
    # === SEPARATE ARCHIVE (können auf NAS/Netzlaufwerk liegen) ===
    # Design-Archiv (DST, EMB, PES, etc.) - ABSOLUTER PFAD
    design_archiv_path = db.Column(db.String(500), default='')  # z.B. \\NAS\Designs oder Z:\Stickdateien
    design_archiv_aktiv = db.Column(db.Boolean, default=False)  # Separates Verzeichnis nutzen?
    
    # Stickdateien-Archiv (produktionsfertige Dateien) - ABSOLUTER PFAD
    stickdateien_path = db.Column(db.String(500), default='')  # z.B. \\NAS\Produktion\DST
    stickdateien_aktiv = db.Column(db.Boolean, default=False)
    
    # Freigaben-Archiv (Kunden-Freigabe-PDFs) - ABSOLUTER PFAD  
    freigaben_archiv_path = db.Column(db.String(500), default='')  # z.B. \\NAS\Freigaben
    freigaben_archiv_aktiv = db.Column(db.Boolean, default=False)
    
    # Motiv-Archiv (Grafiken, Vorlagen, AI/PSD) - ABSOLUTER PFAD
    motiv_archiv_path = db.Column(db.String(500), default='')  # z.B. \\NAS\Motive
    motiv_archiv_aktiv = db.Column(db.Boolean, default=False)
    
    # === DOKUMENT-PFADE (relativ zum base_path) ===
    # Angebote
    angebote_path = db.Column(db.String(200), default='Angebote')
    # Auftragsbestätigungen
    auftraege_path = db.Column(db.String(200), default='Auftragsbestätigungen')
    # Lieferscheine
    lieferscheine_path = db.Column(db.String(200), default='Lieferscheine')
    # Rechnungen (Ausgang)
    rechnungen_ausgang_path = db.Column(db.String(200), default='Rechnungen\\Ausgang')
    # Rechnungen (Eingang)
    rechnungen_eingang_path = db.Column(db.String(200), default='Rechnungen\\Eingang')
    # Gutschriften
    gutschriften_path = db.Column(db.String(200), default='Gutschriften')
    # Mahnungen
    mahnungen_path = db.Column(db.String(200), default='Mahnungen')
    
    # === DESIGN-PFADE (relativ zum base_path, falls kein separates Archiv) ===
    # DST-Dateien (Stickdateien)
    designs_path = db.Column(db.String(200), default='Designs')
    # Design-Freigabe PDFs
    design_freigaben_path = db.Column(db.String(200), default='Design-Freigaben')
    
    # === SONSTIGE PFADE ===
    # Backups
    backup_path = db.Column(db.String(200), default='Backups')
    # Temporäre Dateien
    temp_path = db.Column(db.String(200), default='Temp')
    # Importe (z.B. L-Shop Excel)
    import_path = db.Column(db.String(200), default='Importe')
    # Exporte
    export_path = db.Column(db.String(200), default='Exporte')
    
    # === ORDNERSTRUKTUR-OPTIONEN ===
    # Unterordner-Struktur für Dokumente
    # Optionen: 'flat', 'year', 'year_month', 'customer', 'customer_year'
    folder_structure = db.Column(db.String(50), default='year_month')
    
    # Kundenname in Dateinamen?
    include_customer_in_filename = db.Column(db.Boolean, default=True)
    
    # Datum in Dateinamen?
    include_date_in_filename = db.Column(db.Boolean, default=True)
    
    # === ARCHIVIERUNG ===
    # Automatische Archivierung nach X Jahren
    auto_archive = db.Column(db.Boolean, default=False)
    archive_after_years = db.Column(db.Integer, default=10)
    archive_path = db.Column(db.String(200), default='Archiv')
    
    # === METADATEN ===
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    @classmethod
    def get_settings(cls):
        """Hole oder erstelle Speichereinstellungen"""
        settings = cls.query.first()
        if not settings:
            settings = cls()
            db.session.add(settings)
            try:
                db.session.commit()
            except:
                db.session.rollback()
        return settings
    
    def get_full_path(self, doc_type, kunde_name=None, datum=None):
        """
        Generiert vollständigen Speicherpfad für einen Dokumenttyp
        
        Args:
            doc_type: 'angebot', 'auftrag', 'lieferschein', 'rechnung_ausgang', etc.
                      Spezial-Typen: 'design_archiv', 'stickdatei', 'freigabe_archiv', 'motiv_archiv'
            kunde_name: Kundenname für Ordnerstruktur (optional)
            datum: Datum für Ordnerstruktur (default: heute)
        
        Returns:
            Vollständiger Pfad als String
        """
        from datetime import date
        
        if datum is None:
            datum = date.today()
        
        # === SEPARATE ARCHIVE (absolute Pfade, z.B. NAS) ===
        # Diese haben Vorrang wenn aktiviert
        
        # Design-Archiv (DST, EMB, etc.)
        if doc_type in ('design_archiv', 'design', 'dst', 'emb', 'pes') and self.design_archiv_aktiv and self.design_archiv_path:
            return self._apply_subfolders(self.design_archiv_path, kunde_name, datum)
        
        # Stickdateien (produktionsfertig)
        if doc_type in ('stickdatei', 'stickdateien', 'produktion_dst') and self.stickdateien_aktiv and self.stickdateien_path:
            return self._apply_subfolders(self.stickdateien_path, kunde_name, datum)
        
        # Freigaben-Archiv
        if doc_type in ('freigabe_archiv', 'freigabe', 'design_freigabe', 'kundenfreigabe') and self.freigaben_archiv_aktiv and self.freigaben_archiv_path:
            return self._apply_subfolders(self.freigaben_archiv_path, kunde_name, datum)
        
        # Motiv-Archiv (Grafiken, Vorlagen)
        if doc_type in ('motiv_archiv', 'motiv', 'grafik', 'vorlage') and self.motiv_archiv_aktiv and self.motiv_archiv_path:
            return self._apply_subfolders(self.motiv_archiv_path, kunde_name, datum)
        
        # === STANDARD-PFADE (relativ zum base_path) ===
        base = self.base_path or os.path.join(os.path.expanduser('~'), 'StitchAdmin', 'Dokumente')
        
        # Dokumenttyp-Pfad Mapping
        type_paths = {
            'angebot': self.angebote_path,
            'auftrag': self.auftraege_path,
            'auftragsbestaetigung': self.auftraege_path,
            'lieferschein': self.lieferscheine_path,
            'rechnung': self.rechnungen_ausgang_path,
            'rechnung_ausgang': self.rechnungen_ausgang_path,
            'rechnung_eingang': self.rechnungen_eingang_path,
            'gutschrift': self.gutschriften_path,
            'mahnung': self.mahnungen_path,
            'design': self.designs_path,
            'design_freigabe': self.design_freigaben_path,
            'backup': self.backup_path,
            'import': self.import_path,
            'export': self.export_path,
        }
        
        doc_path = type_paths.get(doc_type, 'Sonstige')
        full_path = os.path.join(base, doc_path)
        
        # Unterordner-Struktur
        if self.folder_structure == 'year':
            full_path = os.path.join(full_path, str(datum.year))
        elif self.folder_structure == 'year_month':
            full_path = os.path.join(full_path, str(datum.year), f"{datum.month:02d}")
        elif self.folder_structure == 'customer' and kunde_name:
            # Kundenname bereinigen
            safe_name = self._sanitize_filename(kunde_name)
            full_path = os.path.join(full_path, safe_name)
        elif self.folder_structure == 'customer_year' and kunde_name:
            safe_name = self._sanitize_filename(kunde_name)
            full_path = os.path.join(full_path, safe_name, str(datum.year))
        
        return full_path
    
    def _apply_subfolders(self, base_path, kunde_name=None, datum=None):
        """
        Wendet Unterordner-Struktur auf einen Basispfad an
        
        Args:
            base_path: Absoluter Basispfad (z.B. NAS-Pfad)
            kunde_name: Kundenname (optional)
            datum: Datum (optional)
        
        Returns:
            Pfad mit Unterordnern
        """
        from datetime import date
        
        if datum is None:
            datum = date.today()
        
        full_path = base_path
        
        # Unterordner-Struktur anwenden
        if self.folder_structure == 'year':
            full_path = os.path.join(full_path, str(datum.year))
        elif self.folder_structure == 'year_month':
            full_path = os.path.join(full_path, str(datum.year), f"{datum.month:02d}")
        elif self.folder_structure == 'customer' and kunde_name:
            safe_name = self._sanitize_filename(kunde_name)
            full_path = os.path.join(full_path, safe_name)
        elif self.folder_structure == 'customer_year' and kunde_name:
            safe_name = self._sanitize_filename(kunde_name)
            full_path = os.path.join(full_path, safe_name, str(datum.year))
        
        return full_path
    
    def get_filename(self, doc_type, doc_nummer, kunde_name=None, datum=None, extension='pdf'):
        """
        Generiert Dateinamen basierend auf Einstellungen
        
        Args:
            doc_type: Dokumenttyp für Präfix
            doc_nummer: Dokumentnummer
            kunde_name: Kundenname (optional)
            datum: Datum (optional)
            extension: Dateiendung (default: pdf)
        
        Returns:
            Dateiname als String
        """
        from datetime import date
        
        if datum is None:
            datum = date.today()
        
        parts = []
        
        # Dokumentnummer (bereinigt)
        safe_nummer = doc_nummer.replace('/', '-').replace('\\', '-')
        parts.append(safe_nummer)
        
        # Datum
        if self.include_date_in_filename:
            parts.append(datum.strftime('%Y%m%d'))
        
        # Kundenname
        if self.include_customer_in_filename and kunde_name:
            safe_name = self._sanitize_filename(kunde_name)[:30]  # Max 30 Zeichen
            parts.append(safe_name)
        
        filename = '_'.join(parts)
        return f"{filename}.{extension}"
    
    def ensure_path_exists(self, doc_type, kunde_name=None, datum=None):
        """Erstellt Ordnerstruktur falls nicht vorhanden"""
        path = self.get_full_path(doc_type, kunde_name, datum)
        os.makedirs(path, exist_ok=True)
        return path
    
    def _sanitize_filename(self, name):
        """Bereinigt einen String für Verwendung als Datei-/Ordnername"""
        # Ungültige Zeichen ersetzen
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        # Mehrfache Unterstriche zusammenfassen
        while '__' in name:
            name = name.replace('__', '_')
        # Führende/trailing Leerzeichen und Punkte entfernen
        name = name.strip(' .')
        return name
    
    def validate_paths(self):
        """Prüft ob alle Pfade erreichbar/erstellbar sind"""
        errors = []
        warnings = []
        
        # === BASISPFAD PRÜFEN ===
        if self.base_path:
            result = self._check_path_access(self.base_path, "Basispfad")
            if result:
                errors.append(result)
        
        # === SEPARATE ARCHIVE PRÜFEN ===
        # Design-Archiv
        if self.design_archiv_aktiv and self.design_archiv_path:
            result = self._check_path_access(self.design_archiv_path, "Design-Archiv")
            if result:
                errors.append(result)
        
        # Stickdateien-Archiv
        if self.stickdateien_aktiv and self.stickdateien_path:
            result = self._check_path_access(self.stickdateien_path, "Stickdateien-Archiv")
            if result:
                errors.append(result)
        
        # Freigaben-Archiv
        if self.freigaben_archiv_aktiv and self.freigaben_archiv_path:
            result = self._check_path_access(self.freigaben_archiv_path, "Freigaben-Archiv")
            if result:
                errors.append(result)
        
        # Motiv-Archiv
        if self.motiv_archiv_aktiv and self.motiv_archiv_path:
            result = self._check_path_access(self.motiv_archiv_path, "Motiv-Archiv")
            if result:
                errors.append(result)
        
        return errors
    
    def _check_path_access(self, path, name):
        """
        Prüft ob ein Pfad erreichbar und beschreibbar ist
        Unterstützt lokale Pfade und Netzlaufwerke (UNC)
        
        Args:
            path: Zu prüfender Pfad
            name: Anzeigename für Fehlermeldungen
        
        Returns:
            Fehlermeldung oder None
        """
        if not path:
            return None
        
        # Normalisiere Pfad (wichtig für Netzlaufwerke)
        path = os.path.normpath(path)
        
        # Prüfe ob Netzlaufwerk (UNC-Pfad: \\server\share)
        is_unc = path.startswith('\\\\')
        
        # Prüfe ob Pfad existiert
        if os.path.exists(path):
            # Pfad existiert - prüfe Schreibrechte
            test_file = os.path.join(path, '.stitchadmin_write_test')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                return None  # Alles OK
            except PermissionError:
                return f"{name}: Keine Schreibrechte in '{path}'"
            except Exception as e:
                return f"{name}: Zugriffsfehler - {e}"
        
        # Pfad existiert nicht - versuche zu erstellen
        try:
            os.makedirs(path, exist_ok=True)
            return None  # Erfolgreich erstellt
        except PermissionError:
            if is_unc:
                return f"{name}: Netzlaufwerk '{path}' nicht erreichbar oder keine Berechtigung"
            else:
                return f"{name}: Keine Berechtigung zum Erstellen von '{path}'"
        except OSError as e:
            if is_unc:
                return f"{name}: Netzlaufwerk nicht verfügbar - {e}"
            else:
                return f"{name}: Pfad kann nicht erstellt werden - {e}"
    
    def create_folder_structure(self):
        """
        Erstellt die komplette Ordnerstruktur
        Inkl. separater Archive auf NAS/Netzlaufwerken
        """
        success = True
        created = []
        errors = []
        
        # === BASISPFAD & RELATIVE PFADE ===
        if self.base_path:
            relative_paths = [
                self.angebote_path,
                self.auftraege_path,
                self.lieferscheine_path,
                self.rechnungen_ausgang_path,
                self.rechnungen_eingang_path,
                self.gutschriften_path,
                self.mahnungen_path,
                self.designs_path,
                self.design_freigaben_path,
                self.backup_path,
                self.temp_path,
                self.import_path,
                self.export_path,
            ]
            
            for rel_path in relative_paths:
                if rel_path:
                    full_path = os.path.join(self.base_path, rel_path)
                    try:
                        os.makedirs(full_path, exist_ok=True)
                        created.append(full_path)
                    except Exception as e:
                        errors.append(f"{full_path}: {e}")
                        success = False
        
        # === SEPARATE ARCHIVE (absolute Pfade) ===
        separate_archives = []
        
        if self.design_archiv_aktiv and self.design_archiv_path:
            separate_archives.append(("Design-Archiv", self.design_archiv_path))
        
        if self.stickdateien_aktiv and self.stickdateien_path:
            separate_archives.append(("Stickdateien", self.stickdateien_path))
        
        if self.freigaben_archiv_aktiv and self.freigaben_archiv_path:
            separate_archives.append(("Freigaben", self.freigaben_archiv_path))
        
        if self.motiv_archiv_aktiv and self.motiv_archiv_path:
            separate_archives.append(("Motive", self.motiv_archiv_path))
        
        for name, path in separate_archives:
            try:
                os.makedirs(path, exist_ok=True)
                created.append(f"{name}: {path}")
            except Exception as e:
                errors.append(f"{name} ({path}): {e}")
                # Bei separaten Archiven nicht komplett abbrechen
        
        if errors:
            print(f"Ordner-Fehler: {errors}")
        
        return success
