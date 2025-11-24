# -*- coding: utf-8 -*-
"""
Photo Upload Controller
=======================
API für Foto-Uploads (inkl. mobile Kamera)

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from src.models import db, Order, PackingList
from src.services.photo_service import PhotoService, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from src.models.activity_log import ActivityLog
import logging

logger = logging.getLogger(__name__)

photo_upload_bp = Blueprint('photo_upload', __name__, url_prefix='/api/photos')


def log_activity(action, details):
    """Aktivität protokollieren"""
    try:
        activity = ActivityLog(
            username=current_user.username if current_user.is_authenticated else 'System',
            action=action,
            details=details,
            ip_address=request.remote_addr
        )
        db.session.add(activity)
        db.session.commit()
    except Exception as e:
        logger.error(f"Fehler beim Protokollieren: {e}")


@photo_upload_bp.route('/upload/order/<order_id>', methods=['POST'])
@login_required
def upload_order_photo(order_id):
    """
    Upload Foto für einen Auftrag
    Unterstützt:
    - Datei-Upload (multipart/form-data)
    - Base64-Upload (JSON) für Kamera
    """
    order = Order.query.get_or_404(order_id)

    photo_service = PhotoService()

    try:
        # Check if it's a base64 upload (from camera)
        if request.is_json:
            data = request.get_json()
            base64_data = data.get('photo')
            photo_type = data.get('type', 'other')
            description = data.get('description', '')

            if not base64_data:
                return jsonify({'error': 'Kein Foto-Daten vorhanden'}), 400

            # Base64-Foto speichern
            photo_info = photo_service.save_base64_photo(
                base64_data=base64_data,
                photo_type=photo_type,
                description=description,
                entity_type='order',
                entity_id=order_id
            )

        # File upload (traditional)
        else:
            if 'photo' not in request.files:
                return jsonify({'error': 'Keine Datei hochgeladen'}), 400

            file = request.files['photo']

            if file.filename == '':
                return jsonify({'error': 'Keine Datei ausgewählt'}), 400

            if not photo_service.allowed_file(file.filename):
                return jsonify({'error': f'Dateiformat nicht erlaubt. Erlaubt: {", ".join(ALLOWED_EXTENSIONS)}'}), 400

            # Foto-Typ und Beschreibung aus Form
            photo_type = request.form.get('type', 'other')
            description = request.form.get('description', '')

            # Foto speichern
            photo_info = photo_service.save_photo(
                file_storage=file,
                photo_type=photo_type,
                description=description,
                entity_type='order',
                entity_id=order_id
            )

        # Foto zum Auftrag hinzufügen
        order.add_photo(
            photo_path=photo_info['path'],
            photo_type=photo_info['type'],
            description=photo_info['description']
        )

        db.session.commit()

        # Aktivität loggen
        log_activity(
            'photo_upload',
            f"Foto zu Auftrag {order.order_number} hochgeladen (Typ: {photo_type})"
        )

        # URLs für Response
        photo_info['url'] = photo_service.get_photo_url(photo_info['path'])
        photo_info['thumbnail_url'] = photo_service.get_thumbnail_url(photo_info.get('thumbnail_path'))

        return jsonify({
            'success': True,
            'message': 'Foto erfolgreich hochgeladen',
            'photo': photo_info
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Fehler beim Foto-Upload: {e}", exc_info=True)
        return jsonify({'error': 'Interner Server-Fehler'}), 500


@photo_upload_bp.route('/upload/packing-list/<int:packing_list_id>/qc', methods=['POST'])
@login_required
def upload_qc_photo(packing_list_id):
    """
    Upload QC-Foto für Packliste
    """
    packing_list = PackingList.query.get_or_404(packing_list_id)

    photo_service = PhotoService()

    try:
        # Check if it's a base64 upload (from camera)
        if request.is_json:
            data = request.get_json()
            base64_data = data.get('photo')
            description = data.get('description', '')

            if not base64_data:
                return jsonify({'error': 'Kein Foto-Daten vorhanden'}), 400

            # Base64-Foto speichern
            photo_info = photo_service.save_base64_photo(
                base64_data=base64_data,
                photo_type='qc',
                description=description,
                entity_type='packing_list',
                entity_id=packing_list_id
            )

        # File upload
        else:
            if 'photo' not in request.files:
                return jsonify({'error': 'Keine Datei hochgeladen'}), 400

            file = request.files['photo']

            if file.filename == '':
                return jsonify({'error': 'Keine Datei ausgewählt'}), 400

            if not photo_service.allowed_file(file.filename):
                return jsonify({'error': f'Dateiformat nicht erlaubt'}), 400

            description = request.form.get('description', '')

            # Foto speichern
            photo_info = photo_service.save_photo(
                file_storage=file,
                photo_type='qc',
                description=description,
                entity_type='packing_list',
                entity_id=packing_list_id
            )

        # Foto zu Packliste hinzufügen
        packing_list.add_qc_photo(photo_info['path'])

        db.session.commit()

        # Aktivität loggen
        log_activity(
            'qc_photo_upload',
            f"QC-Foto zu Packliste {packing_list.packing_list_number} hochgeladen"
        )

        # URLs für Response
        photo_info['url'] = photo_service.get_photo_url(photo_info['path'])
        photo_info['thumbnail_url'] = photo_service.get_thumbnail_url(photo_info.get('thumbnail_path'))

        return jsonify({
            'success': True,
            'message': 'QC-Foto erfolgreich hochgeladen',
            'photo': photo_info
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Fehler beim QC-Foto-Upload: {e}", exc_info=True)
        return jsonify({'error': 'Interner Server-Fehler'}), 500


@photo_upload_bp.route('/delete/order/<order_id>/<path:photo_path>', methods=['DELETE'])
@login_required
def delete_order_photo(order_id, photo_path):
    """
    Löscht Foto von einem Auftrag
    """
    order = Order.query.get_or_404(order_id)

    photo_service = PhotoService()

    try:
        # Foto aus Auftrag entfernen
        order.remove_photo(photo_path)

        # Foto-Datei löschen
        photo_service.delete_photo(photo_path)

        db.session.commit()

        # Aktivität loggen
        log_activity(
            'photo_delete',
            f"Foto von Auftrag {order.order_number} gelöscht"
        )

        return jsonify({
            'success': True,
            'message': 'Foto erfolgreich gelöscht'
        }), 200

    except Exception as e:
        logger.error(f"Fehler beim Foto-Löschen: {e}", exc_info=True)
        return jsonify({'error': 'Interner Server-Fehler'}), 500


@photo_upload_bp.route('/info', methods=['GET'])
@login_required
def upload_info():
    """
    Gibt Upload-Informationen zurück
    """
    return jsonify({
        'allowed_extensions': list(ALLOWED_EXTENSIONS),
        'max_file_size': MAX_FILE_SIZE,
        'max_file_size_mb': MAX_FILE_SIZE / (1024 * 1024),
        'photo_types': [
            {'value': 'color', 'label': 'Farben'},
            {'value': 'position', 'label': 'Position'},
            {'value': 'sample', 'label': 'Musterstück'},
            {'value': 'qc', 'label': 'Qualitätskontrolle'},
            {'value': 'other', 'label': 'Sonstiges'}
        ]
    })


__all__ = ['photo_upload_bp']
