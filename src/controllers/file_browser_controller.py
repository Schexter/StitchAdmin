"""
Design File Browser - Datei-Browser fuer Design-Auswahl
Nutzt StorageSettings fuer konfigurierbare Speicherpfade.

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required

file_browser_bp = Blueprint('file_browser', __name__, url_prefix='/file_browser')

# Design-Dateitypen
DESIGN_EXTENSIONS = {'.dst', '.pes', '.jef', '.exp', '.svg', '.ai', '.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff'}

FILE_ICONS = {
    '.dst': 'bi-file-earmark-binary',
    '.pes': 'bi-file-earmark-code',
    '.jef': 'bi-file-earmark-code',
    '.exp': 'bi-file-earmark-code',
    '.svg': 'bi-file-earmark-image',
    '.ai': 'bi-file-earmark-richtext',
    '.pdf': 'bi-file-earmark-pdf',
    '.png': 'bi-file-earmark-image',
    '.jpg': 'bi-file-earmark-image',
    '.jpeg': 'bi-file-earmark-image',
    '.bmp': 'bi-file-earmark-image',
    '.tiff': 'bi-file-earmark-image',
}


def _get_storage_service():
    """Lazy-Load des FileStorageService"""
    from src.services.file_storage_service import FileStorageService
    return FileStorageService()


@file_browser_bp.route('/browse')
@login_required
def browse():
    """Datei-Browser fuer Design-Auswahl"""
    current_path = request.args.get('path', '')
    filter_type = request.args.get('filter', 'design')  # design, all, images

    storage = _get_storage_service()

    # Kein Pfad angegeben -> zeige konfigurierte Speicherorte
    if not current_path:
        roots = storage.get_storage_roots()
        # Erste verfuegbare Root als Default
        for root in roots:
            if root['available']:
                current_path = root['path']
                break
        if not current_path:
            return jsonify({'error': 'Kein Speicherpfad konfiguriert', 'roots': roots}), 404

    current_path = os.path.normpath(current_path)

    if not os.path.exists(current_path):
        return jsonify({'error': 'Pfad nicht gefunden', 'path': current_path}), 404

    # Extensions-Filter
    extensions = None
    if filter_type == 'design':
        extensions = DESIGN_EXTENSIONS
    elif filter_type == 'images':
        extensions = {'.png', '.jpg', '.jpeg', '.svg', '.bmp', '.tiff', '.gif', '.webp'}

    items = []
    try:
        # Parent-Verzeichnis
        parent_path = os.path.dirname(current_path)
        if parent_path != current_path and parent_path:
            items.append({
                'name': '..',
                'path': parent_path,
                'type': 'directory',
                'icon': 'bi-arrow-up-circle',
                'is_parent': True
            })

        for entry in sorted(os.listdir(current_path)):
            if entry.startswith('.'):
                continue

            full_path = os.path.join(current_path, entry)
            is_dir = os.path.isdir(full_path)

            if is_dir:
                items.append({
                    'name': entry,
                    'path': full_path,
                    'relative_path': storage.to_relative(full_path),
                    'type': 'directory',
                    'icon': 'bi-folder',
                    'is_parent': False
                })
            else:
                ext = os.path.splitext(entry)[1].lower()
                if extensions and ext not in extensions:
                    continue

                try:
                    stat = os.stat(full_path)
                    items.append({
                        'name': entry,
                        'path': full_path,
                        'relative_path': storage.to_relative(full_path),
                        'type': 'file',
                        'icon': FILE_ICONS.get(ext, 'bi-file-earmark'),
                        'size': stat.st_size,
                        'size_mb': round(stat.st_size / 1024 / 1024, 2),
                        'modified': stat.st_mtime,
                        'is_parent': False,
                        'file_url': storage.get_file_url(storage.to_relative(full_path))
                    })
                except OSError:
                    continue

    except PermissionError:
        return jsonify({'error': 'Keine Berechtigung fuer diesen Pfad'}), 403
    except Exception as e:
        return jsonify({'error': f'Fehler: {str(e)}'}), 500

    # Speicherorte fuer Root-Navigation
    roots = storage.get_storage_roots()

    return jsonify({
        'current_path': current_path,
        'relative_path': storage.to_relative(current_path),
        'items': items,
        'breadcrumbs': storage._breadcrumbs(current_path),
        'roots': roots
    })


@file_browser_bp.route('/roots')
@login_required
def get_roots():
    """Gibt alle konfigurierten Speicherorte zurueck"""
    storage = _get_storage_service()
    return jsonify({'roots': storage.get_storage_roots()})


@file_browser_bp.route('/modal')
@login_required
def modal():
    """Datei-Browser Modal"""
    return render_template('file_browser/modal.html')


@file_browser_bp.route('/get_file_info')
@login_required
def get_file_info():
    """Detaillierte Datei-Informationen"""
    file_path = request.args.get('path')

    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'Datei nicht gefunden'}), 404

    try:
        stat = os.stat(file_path)
        storage = _get_storage_service()
        import mimetypes

        file_info = {
            'name': os.path.basename(file_path),
            'path': file_path,
            'relative_path': storage.to_relative(file_path),
            'size': stat.st_size,
            'size_mb': round(stat.st_size / 1024 / 1024, 2),
            'modified': stat.st_mtime,
            'created': stat.st_ctime,
            'mime_type': mimetypes.guess_type(file_path)[0] or 'unknown',
            'file_url': storage.get_file_url(storage.to_relative(file_path))
        }

        # Design-Analyse wenn moeglich
        try:
            from src.utils.file_analysis import analyze_design_file
            file_info['analysis'] = analyze_design_file(file_path)
        except Exception:
            file_info['analysis'] = None

        return jsonify(file_info)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@file_browser_bp.route('/open')
@login_required
def open_file():
    """
    Oeffnet eine Datei zum Download/Anzeige.
    Wird fuer Hyperlinks in der Anwendung genutzt.
    """
    relative_path = request.args.get('path', '')
    if not relative_path:
        return jsonify({'error': 'Kein Pfad angegeben'}), 400

    storage = _get_storage_service()
    result = storage.get_file(relative_path)

    if not result['success']:
        return jsonify({'error': result.get('error', 'Datei nicht gefunden')}), 404

    abs_path = result['absolute_path']
    return send_file(abs_path, as_attachment=False)


@file_browser_bp.route('/download')
@login_required
def download_file():
    """Datei herunterladen"""
    relative_path = request.args.get('path', '')
    if not relative_path:
        return jsonify({'error': 'Kein Pfad angegeben'}), 400

    storage = _get_storage_service()
    result = storage.get_file(relative_path)

    if not result['success']:
        return jsonify({'error': result.get('error', 'Datei nicht gefunden')}), 404

    abs_path = result['absolute_path']
    return send_file(abs_path, as_attachment=True, download_name=result['filename'])


# Erstellt von Hans Hahn - Alle Rechte vorbehalten
