# -*- coding: utf-8 -*-
"""
Photo Service - Foto-Upload und -Verwaltung
===========================================
Unterstützt mobile Kamera-Uploads für QM und Dokumentation

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

import os
import uuid
from datetime import datetime
from PIL import Image
from werkzeug.utils import secure_filename
import logging

logger = logging.getLogger(__name__)

# Erlaubte Foto-Formate
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Thumbnail-Größen
THUMBNAIL_SIZE = (400, 400)
PREVIEW_SIZE = (800, 800)


class PhotoService:
    """Service für Foto-Upload und -Verwaltung"""

    def __init__(self, upload_base_dir='instance/uploads'):
        """
        Initialisiert Photo Service

        Args:
            upload_base_dir: Basis-Verzeichnis für Uploads
        """
        self.upload_base_dir = upload_base_dir
        self.photos_dir = os.path.join(upload_base_dir, 'photos')
        self.thumbnails_dir = os.path.join(upload_base_dir, 'thumbnails')

        # Verzeichnisse erstellen
        os.makedirs(self.photos_dir, exist_ok=True)
        os.makedirs(self.thumbnails_dir, exist_ok=True)

    def allowed_file(self, filename):
        """Prüft ob Dateiendung erlaubt ist"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def save_photo(self, file_storage, photo_type='other', description='', entity_type='order', entity_id=None):
        """
        Speichert ein hochgeladenes Foto

        Args:
            file_storage: Werkzeug FileStorage Objekt
            photo_type: Art des Fotos (color, position, sample, qc, other)
            description: Beschreibung
            entity_type: Art der Entität (order, packing_list, etc.)
            entity_id: ID der Entität

        Returns:
            dict: Foto-Informationen mit Pfaden
        """
        if not file_storage:
            return None

        if not self.allowed_file(file_storage.filename):
            raise ValueError(f"Dateiformat nicht erlaubt: {file_storage.filename}")

        # Eindeutigen Dateinamen generieren
        ext = file_storage.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{ext}"

        # Pfade
        photo_path = os.path.join(self.photos_dir, unique_filename)
        thumbnail_path = os.path.join(self.thumbnails_dir, f"thumb_{unique_filename}")

        # Original speichern
        file_storage.save(photo_path)

        # Thumbnail generieren
        try:
            self._create_thumbnail(photo_path, thumbnail_path)
        except Exception as e:
            logger.warning(f"Thumbnail konnte nicht erstellt werden: {e}")
            thumbnail_path = None

        # Relative Pfade für Datenbank
        relative_photo_path = os.path.relpath(photo_path, self.upload_base_dir)
        relative_thumbnail_path = os.path.relpath(thumbnail_path, self.upload_base_dir) if thumbnail_path else None

        # Foto-Info zurückgeben
        return {
            'path': relative_photo_path,
            'thumbnail_path': relative_thumbnail_path,
            'type': photo_type,
            'description': description,
            'filename': file_storage.filename,
            'timestamp': datetime.now().isoformat(),
            'entity_type': entity_type,
            'entity_id': entity_id,
            'size': os.path.getsize(photo_path)
        }

    def save_base64_photo(self, base64_data, photo_type='other', description='', entity_type='order', entity_id=None):
        """
        Speichert ein Base64-kodiertes Foto (z.B. von Kamera)

        Args:
            base64_data: Base64-String (mit oder ohne data:image/... prefix)
            photo_type: Art des Fotos
            description: Beschreibung
            entity_type: Art der Entität
            entity_id: ID der Entität

        Returns:
            dict: Foto-Informationen
        """
        import base64
        from io import BytesIO

        # Base64-Header entfernen falls vorhanden
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]

        # Dekodieren
        try:
            image_data = base64.b64decode(base64_data)
        except Exception as e:
            raise ValueError(f"Base64-Dekodierung fehlgeschlagen: {e}")

        # Eindeutigen Dateinamen generieren
        unique_filename = f"{uuid.uuid4().hex}.jpg"

        # Pfade
        photo_path = os.path.join(self.photos_dir, unique_filename)
        thumbnail_path = os.path.join(self.thumbnails_dir, f"thumb_{unique_filename}")

        # Bild speichern
        try:
            img = Image.open(BytesIO(image_data))

            # Orientierung korrigieren (EXIF)
            try:
                from PIL import ExifTags
                for orientation in ExifTags.TAGS.keys():
                    if ExifTags.TAGS[orientation] == 'Orientation':
                        break
                exif = img._getexif()
                if exif is not None:
                    orientation_value = exif.get(orientation)
                    if orientation_value == 3:
                        img = img.rotate(180, expand=True)
                    elif orientation_value == 6:
                        img = img.rotate(270, expand=True)
                    elif orientation_value == 8:
                        img = img.rotate(90, expand=True)
            except (AttributeError, KeyError, IndexError):
                pass

            # Größe reduzieren falls zu groß (max 1920px)
            max_size = (1920, 1920)
            if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)

            # Speichern
            img.save(photo_path, 'JPEG', quality=85, optimize=True)

        except Exception as e:
            raise ValueError(f"Bild konnte nicht verarbeitet werden: {e}")

        # Thumbnail generieren
        try:
            self._create_thumbnail(photo_path, thumbnail_path)
        except Exception as e:
            logger.warning(f"Thumbnail konnte nicht erstellt werden: {e}")
            thumbnail_path = None

        # Relative Pfade für Datenbank
        relative_photo_path = os.path.relpath(photo_path, self.upload_base_dir)
        relative_thumbnail_path = os.path.relpath(thumbnail_path, self.upload_base_dir) if thumbnail_path else None

        # Foto-Info zurückgeben
        return {
            'path': relative_photo_path,
            'thumbnail_path': relative_thumbnail_path,
            'type': photo_type,
            'description': description,
            'filename': unique_filename,
            'timestamp': datetime.now().isoformat(),
            'entity_type': entity_type,
            'entity_id': entity_id,
            'size': os.path.getsize(photo_path)
        }

    def _create_thumbnail(self, source_path, thumbnail_path):
        """
        Erstellt ein Thumbnail

        Args:
            source_path: Pfad zum Original
            thumbnail_path: Pfad für Thumbnail
        """
        try:
            img = Image.open(source_path)

            # EXIF-Orientierung berücksichtigen
            try:
                from PIL import ExifTags
                for orientation in ExifTags.TAGS.keys():
                    if ExifTags.TAGS[orientation] == 'Orientation':
                        break
                exif = img._getexif()
                if exif is not None:
                    orientation_value = exif.get(orientation)
                    if orientation_value == 3:
                        img = img.rotate(180, expand=True)
                    elif orientation_value == 6:
                        img = img.rotate(270, expand=True)
                    elif orientation_value == 8:
                        img = img.rotate(90, expand=True)
            except (AttributeError, KeyError, IndexError):
                pass

            # Thumbnail erstellen (zentriert croppen)
            img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

            # Als JPEG speichern
            img.save(thumbnail_path, 'JPEG', quality=80, optimize=True)

        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Thumbnails: {e}")
            raise

    def delete_photo(self, photo_path, thumbnail_path=None):
        """
        Löscht ein Foto und sein Thumbnail

        Args:
            photo_path: Relativer Pfad zum Foto
            thumbnail_path: Relativer Pfad zum Thumbnail (optional)
        """
        # Vollständige Pfade
        full_photo_path = os.path.join(self.upload_base_dir, photo_path)
        full_thumbnail_path = os.path.join(self.upload_base_dir, thumbnail_path) if thumbnail_path else None

        # Foto löschen
        if os.path.exists(full_photo_path):
            try:
                os.remove(full_photo_path)
                logger.info(f"Foto gelöscht: {photo_path}")
            except Exception as e:
                logger.error(f"Fehler beim Löschen des Fotos: {e}")

        # Thumbnail löschen
        if full_thumbnail_path and os.path.exists(full_thumbnail_path):
            try:
                os.remove(full_thumbnail_path)
                logger.info(f"Thumbnail gelöscht: {thumbnail_path}")
            except Exception as e:
                logger.error(f"Fehler beim Löschen des Thumbnails: {e}")

    def get_photo_url(self, photo_path):
        """
        Gibt URL für Foto zurück

        Args:
            photo_path: Relativer Pfad zum Foto

        Returns:
            str: URL zum Foto
        """
        if not photo_path:
            return None
        return f"/uploads/{photo_path}"

    def get_thumbnail_url(self, thumbnail_path):
        """
        Gibt URL für Thumbnail zurück

        Args:
            thumbnail_path: Relativer Pfad zum Thumbnail

        Returns:
            str: URL zum Thumbnail
        """
        if not thumbnail_path:
            return None
        return f"/uploads/{thumbnail_path}"


__all__ = ['PhotoService', 'ALLOWED_EXTENSIONS', 'MAX_FILE_SIZE']
