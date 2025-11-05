"""
Backup Controller - Backup und Restore Funktionalität
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_file
from functools import wraps
import json
import os
import zipfile
import shutil
from datetime import datetime
from src.utils.activity_logger import log_activity

# Blueprint erstellen
backup_bp = Blueprint('backup', __name__, url_prefix='/backup')

BACKUP_DIR = 'backups'

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Bitte melden Sie sich an.', 'info')
            return redirect(url_for('login'))
        if not session.get('is_admin', False):
            flash('Keine Berechtigung für diese Aktion.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def ensure_backup_dir():
    """Stelle sicher dass Backup-Verzeichnis existiert"""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

@backup_bp.route('/')
@admin_required
def index():
    """Backup-Übersicht"""
    ensure_backup_dir()
    
    # Liste existierende Backups
    backups = []
    for filename in os.listdir(BACKUP_DIR):
        if filename.endswith('.zip'):
            filepath = os.path.join(BACKUP_DIR, filename)
            stats = os.stat(filepath)
            backups.append({
                'filename': filename,
                'size': stats.st_size,
                'created': datetime.fromtimestamp(stats.st_mtime),
                'size_mb': round(stats.st_size / 1024 / 1024, 2)
            })
    
    # Nach Datum sortieren (neueste zuerst)
    backups.sort(key=lambda x: x['created'], reverse=True)
    
    return render_template('backup/index.html', backups=backups)

@backup_bp.route('/create', methods=['POST'])
@admin_required
def create():
    """Neues Backup erstellen"""
    ensure_backup_dir()
    
    # Backup-Name mit Timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'stitchadmin_backup_{timestamp}.zip'
    backup_path = os.path.join(BACKUP_DIR, backup_name)
    
    # Dateien die gesichert werden sollen
    files_to_backup = [
        'users.json',
        'activity_log.json',
        'system_settings.json',
        'login_attempts.json',
        'password_reset_tokens.json'
    ]
    
    # ZIP-Archiv erstellen
    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files_to_backup:
            if os.path.exists(file):
                zipf.write(file)
        
        # Konfigurationsdateien
        if os.path.exists('.env'):
            zipf.write('.env')
    
    log_activity(session['username'], 'backup_created', f'Backup erstellt: {backup_name}')
    flash(f'Backup "{backup_name}" wurde erfolgreich erstellt!', 'success')
    
    return redirect(url_for('backup.index'))

@backup_bp.route('/download/<filename>')
@admin_required
def download(filename):
    """Backup herunterladen"""
    # Sicherheitsprüfung für Dateinamen
    if '..' in filename or '/' in filename or '\\' in filename:
        flash('Ungültiger Dateiname!', 'danger')
        return redirect(url_for('backup.index'))
    
    backup_path = os.path.join(BACKUP_DIR, filename)
    
    if not os.path.exists(backup_path):
        flash('Backup nicht gefunden!', 'danger')
        return redirect(url_for('backup.index'))
    
    log_activity(session['username'], 'backup_download', f'Backup heruntergeladen: {filename}')
    
    return send_file(backup_path, as_attachment=True, download_name=filename)

@backup_bp.route('/restore/<filename>', methods=['POST'])
@admin_required
def restore(filename):
    """Backup wiederherstellen"""
    # Sicherheitsprüfung für Dateinamen
    if '..' in filename or '/' in filename or '\\' in filename:
        flash('Ungültiger Dateiname!', 'danger')
        return redirect(url_for('backup.index'))
    
    backup_path = os.path.join(BACKUP_DIR, filename)
    
    if not os.path.exists(backup_path):
        flash('Backup nicht gefunden!', 'danger')
        return redirect(url_for('backup.index'))
    
    try:
        # Aktuelle Dateien sichern
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_backup_dir = f'temp_backup_{timestamp}'
        os.makedirs(temp_backup_dir)
        
        # ZIP entpacken
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            # Erst in temporäres Verzeichnis entpacken
            zipf.extractall(temp_backup_dir)
        
        # Dateien wiederherstellen
        restored_files = []
        for file in os.listdir(temp_backup_dir):
            if file != '.env':  # .env nicht automatisch überschreiben
                src = os.path.join(temp_backup_dir, file)
                dst = file
                
                # Aktuelle Datei sichern falls vorhanden
                if os.path.exists(dst):
                    shutil.copy2(dst, f'{dst}.before_restore_{timestamp}')
                
                # Wiederherstellen
                shutil.copy2(src, dst)
                restored_files.append(file)
        
        # Temporäres Verzeichnis aufräumen
        shutil.rmtree(temp_backup_dir)
        
        log_activity(session['username'], 'backup_restored', f'Backup wiederhergestellt: {filename}')
        flash(f'Backup erfolgreich wiederhergestellt! Dateien: {", ".join(restored_files)}', 'success')
        
    except Exception as e:
        flash(f'Fehler beim Wiederherstellen: {str(e)}', 'danger')
    
    return redirect(url_for('backup.index'))

@backup_bp.route('/delete/<filename>', methods=['POST'])
@admin_required
def delete(filename):
    """Backup löschen"""
    # Sicherheitsprüfung für Dateinamen
    if '..' in filename or '/' in filename or '\\' in filename:
        flash('Ungültiger Dateiname!', 'danger')
        return redirect(url_for('backup.index'))
    
    backup_path = os.path.join(BACKUP_DIR, filename)
    
    if os.path.exists(backup_path):
        os.remove(backup_path)
        log_activity(session['username'], 'backup_deleted', f'Backup gelöscht: {filename}')
        flash(f'Backup "{filename}" wurde gelöscht!', 'success')
    else:
        flash('Backup nicht gefunden!', 'danger')
    
    return redirect(url_for('backup.index'))