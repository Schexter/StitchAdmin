"""
StitchAdmin 2.0 - Update-Checker
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Prüft auf verfügbare Updates über einen Remote-Endpoint.

Update-Server JSON-Format:
{
    "latest_version": "2.1.0",
    "release_date": "2025-12-01",
    "download_url": "https://your-server.com/downloads/stitchadmin-2.1.0.exe",
    "release_notes": "- Feature X\n- Bugfix Y",
    "critical": false,
    "min_version": "2.0.0"
}
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any

import requests

from .version import CURRENT_VERSION, Version

logger = logging.getLogger(__name__)


@dataclass
class UpdateInfo:
    """Update-Informationen"""
    update_available: bool
    latest_version: Optional[Version] = None
    current_version: Optional[Version] = None
    download_url: Optional[str] = None
    release_notes: Optional[str] = None
    release_date: Optional[datetime] = None
    is_critical: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary"""
        return {
            'update_available': self.update_available,
            'latest_version': str(self.latest_version) if self.latest_version else None,
            'current_version': str(self.current_version) if self.current_version else None,
            'download_url': self.download_url,
            'release_notes': self.release_notes,
            'release_date': self.release_date.isoformat() if self.release_date else None,
            'is_critical': self.is_critical,
            'error': self.error
        }


class UpdateChecker:
    """
    Prüft auf verfügbare Updates.

    Cached das Ergebnis für eine bestimmte Zeit, um Server-Last zu reduzieren.
    """

    # Update server endpoint (will be configured)
    UPDATE_URL = "https://your-update-server.com/api/latest-version"  # TODO: Update with actual URL

    # Cache settings
    CACHE_FILE = Path("instance/.update_cache")
    CACHE_DURATION_HOURS = 24  # Check for updates max once per day

    # Request timeout
    REQUEST_TIMEOUT = 10  # seconds

    def __init__(self, update_url: Optional[str] = None, cache_file: Optional[Path] = None):
        """
        Initialisiert Update-Checker.

        Args:
            update_url: Custom Update-Server URL
            cache_file: Custom Cache-Datei Pfad
        """
        self.update_url = update_url or self.UPDATE_URL
        self.cache_file = cache_file or self.CACHE_FILE

        logger.debug(f"UpdateChecker initialisiert: {self.update_url}")

    def check_for_updates(self, force: bool = False) -> UpdateInfo:
        """
        Prüft auf verfügbare Updates.

        Args:
            force: Cache ignorieren und sofort prüfen

        Returns:
            UpdateInfo: Update-Informationen
        """
        logger.info("Prüfe auf Updates...")

        # Check cache first (unless forced)
        if not force:
            cached_info = self._load_from_cache()
            if cached_info:
                logger.debug("Update-Info aus Cache geladen")
                return cached_info

        # Fetch from server
        try:
            logger.debug(f"Frage Update-Server ab: {self.update_url}")

            response = requests.get(
                self.update_url,
                timeout=self.REQUEST_TIMEOUT,
                headers={'User-Agent': f'StitchAdmin/{CURRENT_VERSION}'}
            )

            response.raise_for_status()
            data = response.json()

            # Parse response
            update_info = self._parse_update_response(data)

            # Cache the result
            self._save_to_cache(update_info)

            return update_info

        except requests.exceptions.Timeout:
            logger.warning("Update-Check: Timeout")
            return UpdateInfo(
                update_available=False,
                current_version=CURRENT_VERSION,
                error="Verbindung zum Update-Server zeitüberschreitung"
            )

        except requests.exceptions.ConnectionError:
            logger.warning("Update-Check: Keine Verbindung zum Server")
            return UpdateInfo(
                update_available=False,
                current_version=CURRENT_VERSION,
                error="Keine Verbindung zum Update-Server"
            )

        except requests.exceptions.HTTPError as e:
            logger.warning(f"Update-Check: HTTP-Fehler {e.response.status_code}")
            return UpdateInfo(
                update_available=False,
                current_version=CURRENT_VERSION,
                error=f"Update-Server Fehler: {e.response.status_code}"
            )

        except Exception as e:
            logger.error(f"Update-Check Fehler: {e}", exc_info=True)
            return UpdateInfo(
                update_available=False,
                current_version=CURRENT_VERSION,
                error=f"Fehler beim Update-Check: {str(e)}"
            )

    def _parse_update_response(self, data: Dict[str, Any]) -> UpdateInfo:
        """
        Parst Update-Server Response.

        Args:
            data: JSON-Response vom Update-Server

        Returns:
            UpdateInfo: Geparste Update-Informationen
        """
        try:
            latest_version_str = data.get('latest_version')
            if not latest_version_str:
                raise ValueError("Keine Version in Update-Response")

            latest_version = Version.from_string(latest_version_str)

            # Check if update available
            update_available = latest_version > CURRENT_VERSION

            # Parse optional fields
            release_date = None
            if 'release_date' in data:
                release_date = datetime.fromisoformat(data['release_date'])

            update_info = UpdateInfo(
                update_available=update_available,
                latest_version=latest_version,
                current_version=CURRENT_VERSION,
                download_url=data.get('download_url'),
                release_notes=data.get('release_notes'),
                release_date=release_date,
                is_critical=data.get('critical', False)
            )

            if update_available:
                logger.info(f"✅ Update verfügbar: {CURRENT_VERSION} → {latest_version}")
            else:
                logger.info(f"✅ Aktuellste Version installiert: {CURRENT_VERSION}")

            return update_info

        except Exception as e:
            logger.error(f"Fehler beim Parsen der Update-Response: {e}", exc_info=True)
            raise ValueError(f"Ungültige Update-Response: {e}")

    def _load_from_cache(self) -> Optional[UpdateInfo]:
        """
        Lädt Update-Info aus Cache.

        Returns:
            Optional[UpdateInfo]: Gecachte Info oder None wenn abgelaufen
        """
        if not self.cache_file.exists():
            logger.debug("Kein Update-Cache vorhanden")
            return None

        try:
            cache_data = json.loads(self.cache_file.read_text(encoding='utf-8'))

            # Check cache age
            cached_at_str = cache_data.get('cached_at')
            if not cached_at_str:
                return None

            cached_at = datetime.fromisoformat(cached_at_str)
            cache_age = datetime.now() - cached_at

            if cache_age > timedelta(hours=self.CACHE_DURATION_HOURS):
                logger.debug(f"Update-Cache abgelaufen ({cache_age.total_seconds()/3600:.1f}h alt)")
                return None

            # Parse cached update info
            update_data = cache_data.get('update_info', {})

            latest_version = None
            if update_data.get('latest_version'):
                latest_version = Version.from_string(update_data['latest_version'])

            current_version = None
            if update_data.get('current_version'):
                current_version = Version.from_string(update_data['current_version'])

            release_date = None
            if update_data.get('release_date'):
                release_date = datetime.fromisoformat(update_data['release_date'])

            return UpdateInfo(
                update_available=update_data.get('update_available', False),
                latest_version=latest_version,
                current_version=current_version,
                download_url=update_data.get('download_url'),
                release_notes=update_data.get('release_notes'),
                release_date=release_date,
                is_critical=update_data.get('is_critical', False),
                error=update_data.get('error')
            )

        except Exception as e:
            logger.warning(f"Fehler beim Laden des Update-Cache: {e}")
            return None

    def _save_to_cache(self, update_info: UpdateInfo) -> None:
        """
        Speichert Update-Info im Cache.

        Args:
            update_info: Zu cachende Update-Informationen
        """
        try:
            # Ensure directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'update_info': update_info.to_dict()
            }

            self.cache_file.write_text(
                json.dumps(cache_data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )

            logger.debug(f"Update-Info gecacht: {self.cache_file}")

        except Exception as e:
            logger.warning(f"Fehler beim Speichern des Update-Cache: {e}")

    def clear_cache(self) -> None:
        """Löscht Update-Cache"""
        if self.cache_file.exists():
            self.cache_file.unlink()
            logger.info("Update-Cache gelöscht")


# Convenience function
def check_for_updates(force: bool = False) -> UpdateInfo:
    """
    Convenience-Funktion zum direkten Update-Check.

    Args:
        force: Cache ignorieren

    Returns:
        UpdateInfo: Update-Informationen
    """
    checker = UpdateChecker()
    return checker.check_for_updates(force=force)


if __name__ == "__main__":
    # Test/Debug-Modus
    logging.basicConfig(level=logging.DEBUG)

    print("=" * 60)
    print("StitchAdmin 2.0 - Update Checker Test")
    print("=" * 60)

    try:
        checker = UpdateChecker()

        print(f"\n📌 Aktuelle Version: {CURRENT_VERSION}")
        print(f"📡 Update-Server: {checker.update_url}")

        print("\n🔍 Prüfe auf Updates...")
        update_info = checker.check_for_updates(force=True)

        if update_info.error:
            print(f"\n❌ Fehler: {update_info.error}")
        elif update_info.update_available:
            print(f"\n✅ Update verfügbar!")
            print(f"   Aktuelle Version: {update_info.current_version}")
            print(f"   Neue Version:     {update_info.latest_version}")
            if update_info.release_date:
                print(f"   Release-Datum:    {update_info.release_date.strftime('%d.%m.%Y')}")
            if update_info.is_critical:
                print(f"   ⚠️  KRITISCHES Update!")
            if update_info.download_url:
                print(f"   Download:         {update_info.download_url}")
            if update_info.release_notes:
                print(f"\n   Release Notes:\n{update_info.release_notes}")
        else:
            print(f"\n✅ Aktuellste Version installiert: {update_info.current_version}")

        print("\n" + "=" * 60)

    except Exception as e:
        print(f"\n❌ Fehler: {e}\n")
        raise
