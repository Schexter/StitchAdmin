# -*- coding: utf-8 -*-
"""
StitchAdmin 2.0 - Update Controller
Web-Interface für Backup und Update Management

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from pathlib import Path
import os

# Blueprint erstellen
update_bp = Blueprint('updates', __name__, url_prefix='/updates')


def require_admin(f):
    """Decorator: Nur Admins haben Zugriff"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Diese Funktion ist nur für Administratoren verfügbar.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


def get_backup_manager():
    """Gibt den Backup-Manager zurück"""
    from src.updates.backup_manager import BackupManager
    app_dir = Path(current_app.root_path).parent
    return BackupManager(app_dir=app_dir)


def get_update_manager():
    """Gibt den Update-Manager zurück"""
    from src.updates.update_manager import UpdateManager
    app_dir = Path(current_app.root_path).parent
    return UpdateManager(app_dir=app_dir)


# ============================================================================
# BACKUP ROUTES
# ============================================================================

@update_bp.route('/backups')
@login_required
@require_admin
def backup_list():
    """Zeigt alle Backups an"""
    manager = get_backup_manager()
    backups = manager.list_backups()
    
    # Formatiere Größen
    for backup in backups:
        size_mb = backup['size'] / (1024 * 1024)
        backup['size_formatted'] = f"{size_mb:.1f} MB"
        
        # Formatiere Datum
        if backup['timestamp']:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(backup['timestamp'])
                backup['date_formatted'] = dt.strftime('%d.%m.%Y %H:%M')
            except:
                backup['date_formatted'] = backup['timestamp'][:19]
    
    return render_template('updates/backup_list.html', backups=backups)


@update_bp.route('/backups/create', methods=['POST'])
@login_required
@require_admin
def backup_create():
    """Erstellt ein neues Backup"""
    manager = get_backup_manager()
    
    backup_type = request.form.get('type', 'manual')
    description = request.form.get('description', '')
    include_uploads = request.form.get('include_uploads') == 'on'
    
    success, message, backup_path = manager.create_backup(
        backup_type=backup_type,
        description=description,
        include_uploads=include_uploads
    )
    
    if success:
        flash(f'Backup erfolgreich erstellt: {Path(backup_path).name}', 'success')
    else:
        flash(f'Backup fehlgeschlagen: {message}', 'error')
    
    return redirect(url_for('updates.backup_list'))


@update_bp.route('/backups/<path:backup_name>/restore', methods=['POST'])
@login_required
@require_admin
def backup_restore(backup_name):
    """Stellt ein Backup wieder her"""
    manager = get_backup_manager()
    
    # Finde Backup-Pfad
    backup_path = manager.backup_dir / backup_name
    
    restore_database = request.form.get('restore_database') == 'on'
    restore_config = request.form.get('restore_config') == 'on'
    restore_uploads = request.form.get('restore_uploads') == 'on'
    
    success, message = manager.restore_backup(
        str(backup_path),
        restore_database=restore_database,
        restore_config=restore_config,
        restore_uploads=restore_uploads
    )
    
    if success:
        flash(f'Backup erfolgreich wiederhergestellt! Bitte starten Sie StitchAdmin neu.', 'success')
    else:
        flash(f'Wiederherstellung fehlgeschlagen: {message}', 'error')
    
    return redirect(url_for('updates.backup_list'))


@update_bp.route('/backups/<path:backup_name>/delete', methods=['POST'])
@login_required
@require_admin
def backup_delete(backup_name):
    """Löscht ein Backup"""
    manager = get_backup_manager()
    
    backup_path = manager.backup_dir / backup_name
    
    success, message = manager.delete_backup(str(backup_path))
    
    if success:
        flash(f'Backup gelöscht: {backup_name}', 'success')
    else:
        flash(f'Löschen fehlgeschlagen: {message}', 'error')
    
    return redirect(url_for('updates.backup_list'))


@update_bp.route('/backups/<path:backup_name>/download')
@login_required
@require_admin
def backup_download(backup_name):
    """Lädt ein Backup herunter"""
    from flask import send_file
    
    manager = get_backup_manager()
    backup_path = manager.backup_dir / backup_name
    
    if not backup_path.exists():
        flash('Backup nicht gefunden', 'error')
        return redirect(url_for('updates.backup_list'))
    
    return send_file(
        str(backup_path),
        as_attachment=True,
        download_name=backup_name
    )


# ============================================================================
# UPDATE ROUTES
# ============================================================================

@update_bp.route('/')
@login_required
@require_admin
def index():
    """Update-Übersicht"""
    manager = get_update_manager()
    
    current_version = manager.get_current_version()
    update_history = manager.get_update_history()
    
    # Letzte Updates formatieren
    for entry in update_history:
        if entry.get('timestamp'):
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(entry['timestamp'])
                entry['date_formatted'] = dt.strftime('%d.%m.%Y %H:%M')
            except:
                entry['date_formatted'] = entry['timestamp'][:19]
    
    return render_template('updates/index.html',
                         current_version=current_version,
                         update_history=update_history[-10:])  # Letzte 10


@update_bp.route('/install', methods=['GET', 'POST'])
@login_required
@require_admin
def install():
    """Update installieren"""
    if request.method == 'POST':
        # Prüfe ob Datei hochgeladen wurde
        if 'update_file' not in request.files:
            flash('Keine Datei ausgewählt', 'error')
            return redirect(url_for('updates.install'))
        
        file = request.files['update_file']
        
        if file.filename == '':
            flash('Keine Datei ausgewählt', 'error')
            return redirect(url_for('updates.install'))
        
        if not file.filename.endswith('.zip'):
            flash('Bitte wählen Sie eine ZIP-Datei', 'error')
            return redirect(url_for('updates.install'))
        
        # Speichere Datei temporär
        import tempfile
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir) / secure_filename(file.filename)
        file.save(str(temp_path))
        
        # Lese Update-Info
        manager = get_update_manager()
        success, message, update_info = manager.read_update_package(str(temp_path))
        
        if not success:
            flash(f'Ungültiges Update-Paket: {message}', 'error')
            # Aufräumen
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
            return redirect(url_for('updates.install'))
        
        # Zeige Bestätigungsseite
        return render_template('updates/confirm_install.html',
                             update_info=update_info,
                             temp_path=str(temp_path),
                             current_version=manager.get_current_version())
    
    return render_template('updates/install.html')


@update_bp.route('/install/confirm', methods=['POST'])
@login_required
@require_admin
def install_confirm():
    """Bestätigt und führt Update durch"""
    temp_path = request.form.get('temp_path')
    create_backup = request.form.get('create_backup') != 'off'
    
    if not temp_path or not Path(temp_path).exists():
        flash('Update-Datei nicht mehr verfügbar. Bitte erneut hochladen.', 'error')
        return redirect(url_for('updates.install'))
    
    manager = get_update_manager()
    result = manager.install_update(temp_path, create_backup=create_backup)
    
    # Aufräumen
    import shutil
    shutil.rmtree(Path(temp_path).parent, ignore_errors=True)
    
    if result.success:
        flash(f'Update erfolgreich! {result.old_version} → {result.new_version}', 'success')
        if result.requires_restart:
            flash('Bitte starten Sie StitchAdmin neu, um das Update abzuschließen.', 'warning')
    else:
        flash(f'Update fehlgeschlagen: {result.message}', 'error')
        if result.backup_path:
            flash(f'Ein Backup wurde erstellt: {Path(result.backup_path).name}', 'info')
    
    return redirect(url_for('updates.index'))


@update_bp.route('/rollback', methods=['POST'])
@login_required
@require_admin
def rollback():
    """Führt Rollback zu einem Backup durch"""
    backup_path = request.form.get('backup_path')
    
    if not backup_path:
        flash('Kein Backup ausgewählt', 'error')
        return redirect(url_for('updates.backup_list'))
    
    manager = get_update_manager()
    success, message = manager.rollback_to_backup(backup_path)
    
    if success:
        flash('Rollback erfolgreich! Bitte starten Sie StitchAdmin neu.', 'success')
    else:
        flash(f'Rollback fehlgeschlagen: {message}', 'error')
    
    return redirect(url_for('updates.index'))


# ============================================================================
# API ROUTES
# ============================================================================

@update_bp.route('/api/status')
@login_required
@require_admin
def api_status():
    """Gibt den aktuellen Update-Status zurück (für AJAX)"""
    manager = get_update_manager()
    
    return jsonify({
        'status': manager.status,
        'progress': manager.progress,
        'message': manager.progress_message,
        'current_version': manager.get_current_version()
    })


@update_bp.route('/api/backup/quick', methods=['POST'])
@login_required
@require_admin
def api_quick_backup():
    """Erstellt schnell ein Backup (für AJAX)"""
    manager = get_backup_manager()
    
    success, message, backup_path = manager.create_backup(
        backup_type='manual',
        description='Schnelles Backup über API'
    )
    
    return jsonify({
        'success': success,
        'message': message,
        'backup_name': Path(backup_path).name if backup_path else None
    })
