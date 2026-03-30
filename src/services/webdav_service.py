# -*- coding: utf-8 -*-
"""
WebDAV / Nextcloud Service
==========================
Dokumente automatisch in Nextcloud / WebDAV-Cloud ablegen.

Unterstuetzt:
- Nextcloud (WebDAV-Endpunkt: /remote.php/dav/files/USERNAME/)
- Generisches WebDAV (WD MyCloud, Synology, ownCloud)
- Hetzner Storage Box (WebDAV)

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import logging
import requests
from urllib.parse import quote as url_quote

logger = logging.getLogger(__name__)


class WebDAVService:
    """Service fuer WebDAV-Uploads (Nextcloud, WD Cloud, etc.)"""

    def __init__(self, settings=None):
        """
        Args:
            settings: StorageSettings-Objekt oder None (laedt automatisch)
        """
        if settings is None:
            from src.models.storage_settings import StorageSettings
            settings = StorageSettings.get_settings()
        self.settings = settings
        self._session = None

    @property
    def is_configured(self):
        """Prueft ob Cloud-Speicher konfiguriert und aktiviert ist"""
        s = self.settings
        return (s.cloud_enabled and s.cloud_url and s.cloud_username and s.cloud_password)

    @property
    def webdav_base_url(self):
        """Generiert die WebDAV-Basis-URL je nach Cloud-Typ"""
        s = self.settings
        url = s.cloud_url.rstrip('/')

        if s.cloud_type == 'nextcloud':
            # Nextcloud WebDAV: /remote.php/dav/files/USERNAME/
            return f"{url}/remote.php/dav/files/{url_quote(s.cloud_username)}/"
        elif s.cloud_type == 'hetzner_storage':
            # Hetzner Storage Box: https://uXXXXXX.your-storagebox.de/
            return f"{url}/"
        else:
            # Generisches WebDAV
            return f"{url}/"

    @property
    def session(self):
        """Erstellt eine requests-Session mit Auth"""
        if self._session is None:
            self._session = requests.Session()
            self._session.auth = (self.settings.cloud_username, self.settings.cloud_password)
            self._session.headers.update({
                'User-Agent': 'StitchAdmin/2.0'
            })
        return self._session

    def test_connection(self):
        """
        Testet die Verbindung zum WebDAV-Server.

        Returns:
            dict mit 'success', 'message', 'space_used', 'space_free'
        """
        if not self.is_configured:
            return {'success': False, 'message': 'Cloud-Speicher nicht konfiguriert'}

        try:
            # PROPFIND auf Root-Verzeichnis
            url = self.webdav_base_url
            response = self.session.request(
                'PROPFIND', url,
                headers={'Depth': '0', 'Content-Type': 'application/xml'},
                timeout=10
            )

            if response.status_code in (200, 207):
                return {
                    'success': True,
                    'message': f'Verbindung erfolgreich ({self.settings.cloud_type})',
                    'status_code': response.status_code
                }
            elif response.status_code == 401:
                return {'success': False, 'message': 'Authentifizierung fehlgeschlagen (Benutzername/Passwort falsch)'}
            elif response.status_code == 404:
                return {'success': False, 'message': 'WebDAV-Endpunkt nicht gefunden. URL pruefen!'}
            else:
                return {'success': False, 'message': f'Unerwarteter Status: {response.status_code}'}

        except requests.exceptions.ConnectionError:
            return {'success': False, 'message': 'Server nicht erreichbar. URL pruefen!'}
        except requests.exceptions.Timeout:
            return {'success': False, 'message': 'Verbindung Timeout (Server antwortet nicht)'}
        except Exception as e:
            return {'success': False, 'message': f'Fehler: {str(e)}'}

    def _ensure_directory(self, cloud_path):
        """
        Erstellt Verzeichnisse rekursiv auf dem WebDAV-Server (MKCOL).

        Args:
            cloud_path: z.B. '/StitchAdmin/Dokumente/Rechnungen/2026/03'
        """
        parts = cloud_path.strip('/').split('/')
        current = ''

        for part in parts:
            current = f"{current}/{part}"
            url = self.webdav_base_url.rstrip('/') + url_quote(current)

            try:
                resp = self.session.request('MKCOL', url, timeout=10)
                # 201 = erstellt, 405 = existiert bereits, 301 = existiert
                if resp.status_code not in (201, 405, 301, 409):
                    logger.debug(f"MKCOL {current}: Status {resp.status_code}")
            except Exception as e:
                logger.warning(f"MKCOL {current} fehlgeschlagen: {e}")

    def upload_file(self, local_path, doc_type, kunde_name=None, datum=None, filename=None):
        """
        Laedt eine Datei auf den WebDAV-Server hoch.

        Args:
            local_path: Lokaler Dateipfad (oder BytesIO-Objekt)
            doc_type: Dokumenttyp ('rechnung', 'angebot', etc.)
            kunde_name: Kundenname fuer Ordnerstruktur
            datum: Datum fuer Ordnerstruktur
            filename: Dateiname (falls nicht aus local_path ableitbar)

        Returns:
            dict mit 'success', 'message', 'cloud_url'
        """
        if not self.is_configured:
            return {'success': False, 'message': 'Cloud nicht konfiguriert'}

        if not self.settings.should_cloud_sync(doc_type):
            return {'success': False, 'message': f'Sync fuer {doc_type} deaktiviert'}

        try:
            # Cloud-Pfad ermitteln
            cloud_dir = self.settings.get_cloud_path(doc_type, kunde_name, datum)
            self._ensure_directory(cloud_dir)

            # Dateiname ermitteln
            if filename is None:
                if isinstance(local_path, str):
                    filename = os.path.basename(local_path)
                else:
                    filename = 'dokument.pdf'

            # Upload-URL
            cloud_file_path = f"{cloud_dir}/{filename}"
            url = self.webdav_base_url.rstrip('/') + url_quote(cloud_file_path)

            # Datei lesen
            if isinstance(local_path, str):
                with open(local_path, 'rb') as f:
                    data = f.read()
            elif hasattr(local_path, 'read'):
                # BytesIO oder aehnlich
                local_path.seek(0)
                data = local_path.read()
            else:
                data = local_path  # Schon bytes

            # PUT-Request
            resp = self.session.put(
                url,
                data=data,
                headers={'Content-Type': 'application/octet-stream'},
                timeout=60
            )

            if resp.status_code in (200, 201, 204):
                logger.info(f"Cloud-Upload erfolgreich: {cloud_file_path}")
                return {
                    'success': True,
                    'message': 'Upload erfolgreich',
                    'cloud_path': cloud_file_path,
                    'cloud_url': url
                }
            else:
                logger.error(f"Cloud-Upload fehlgeschlagen: {resp.status_code} - {resp.text[:200]}")
                return {
                    'success': False,
                    'message': f'Upload fehlgeschlagen (Status {resp.status_code})'
                }

        except FileNotFoundError:
            return {'success': False, 'message': f'Lokale Datei nicht gefunden: {local_path}'}
        except Exception as e:
            logger.error(f"Cloud-Upload Fehler: {e}")
            return {'success': False, 'message': f'Fehler: {str(e)}'}

    def upload_bytes(self, data, filename, doc_type, kunde_name=None, datum=None):
        """
        Laedt Bytes direkt hoch (z.B. PDF aus BytesIO).

        Args:
            data: bytes oder BytesIO
            filename: Dateiname
            doc_type: Dokumenttyp
            kunde_name: Kundenname
            datum: Datum

        Returns:
            dict mit 'success', 'message', 'cloud_path'
        """
        return self.upload_file(data, doc_type, kunde_name, datum, filename)

    def list_files(self, cloud_path):
        """
        Listet Dateien in einem Cloud-Verzeichnis.

        Args:
            cloud_path: z.B. '/StitchAdmin/Dokumente/Rechnungen/2026'

        Returns:
            Liste von dicts mit 'name', 'size', 'modified', 'is_dir'
        """
        if not self.is_configured:
            return []

        try:
            url = self.webdav_base_url.rstrip('/') + url_quote(cloud_path)
            resp = self.session.request(
                'PROPFIND', url,
                headers={'Depth': '1', 'Content-Type': 'application/xml'},
                timeout=15
            )

            if resp.status_code not in (200, 207):
                return []

            # Einfaches XML-Parsing (ohne lxml-Abhaengigkeit)
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.text)

            ns = {'d': 'DAV:'}
            files = []

            for response in root.findall('.//d:response', ns):
                href = response.find('d:href', ns)
                if href is None:
                    continue

                name = href.text.rstrip('/').split('/')[-1]
                if not name:
                    continue

                props = response.find('.//d:propstat/d:prop', ns)
                is_dir = props.find('d:resourcetype/d:collection', ns) is not None if props is not None else False

                size_el = props.find('d:getcontentlength', ns) if props is not None else None
                size = int(size_el.text) if size_el is not None and size_el.text else 0

                mod_el = props.find('d:getlastmodified', ns) if props is not None else None
                modified = mod_el.text if mod_el is not None else ''

                files.append({
                    'name': name,
                    'size': size,
                    'modified': modified,
                    'is_dir': is_dir
                })

            return files

        except Exception as e:
            logger.error(f"Cloud-Listing Fehler: {e}")
            return []

    def download_file(self, cloud_path):
        """
        Laedt eine Datei aus der Cloud herunter.

        Args:
            cloud_path: Pfad in der Cloud

        Returns:
            bytes oder None
        """
        if not self.is_configured:
            return None

        try:
            url = self.webdav_base_url.rstrip('/') + url_quote(cloud_path)
            resp = self.session.get(url, timeout=30)

            if resp.status_code == 200:
                return resp.content
            return None

        except Exception as e:
            logger.error(f"Cloud-Download Fehler: {e}")
            return None
