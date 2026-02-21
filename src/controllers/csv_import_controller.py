# -*- coding: utf-8 -*-
"""
CSV Import Controller
=====================
Upload, Mapping, Validierung und Ausfuehrung von CSV-Imports

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from functools import wraps

from src.models import db
from src.models.csv_import import CSVImportJob
from src.services.csv_import_service import CSVImportService, FIELD_MAPPINGS

import logging
logger = logging.getLogger(__name__)

csv_import_bp = Blueprint('csv_import', __name__, url_prefix='/import')

IMPORT_TYPES = {
    'customer': 'Kunden',
    'article': 'Artikel',
    'booking': 'Buchungen',
    'bank_statement': 'Bankauszug',
}


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Nur Administratoren haben Zugriff.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@csv_import_bp.route('/')
@login_required
@admin_required
def index():
    """Upload-Formular"""
    return render_template('csv_import/upload.html',
                         import_types=IMPORT_TYPES)


@csv_import_bp.route('/upload', methods=['POST'])
@login_required
@admin_required
def upload():
    """CSV-Datei hochladen und Format erkennen"""
    file = request.files.get('file')
    import_type = request.form.get('import_type')

    if not file or not file.filename:
        flash('Bitte eine Datei auswaehlen.', 'warning')
        return redirect(url_for('csv_import.index'))

    if import_type not in IMPORT_TYPES:
        flash('Ungueltiger Import-Typ.', 'danger')
        return redirect(url_for('csv_import.index'))

    if not file.filename.lower().endswith(('.csv', '.txt', '.tsv')):
        flash('Nur CSV/TXT-Dateien sind erlaubt.', 'warning')
        return redirect(url_for('csv_import.index'))

    service = CSVImportService()
    file_content = file.read()

    job = service.create_import_job(
        file_content=file_content,
        filename=file.filename,
        import_type=import_type,
        user=current_user.username if current_user else 'system',
    )

    flash(f'Datei "{file.filename}" hochgeladen. Bitte Spalten zuordnen.', 'success')
    return redirect(url_for('csv_import.mapping', job_id=job.id))


@csv_import_bp.route('/<int:job_id>/mapping', methods=['GET', 'POST'])
@login_required
@admin_required
def mapping(job_id):
    """Spalten-Mapping bearbeiten"""
    job = CSVImportJob.query.get_or_404(job_id)
    service = CSVImportService()

    if request.method == 'POST':
        # Mapping speichern
        new_mapping = {}
        for header in job.detected_headers:
            field = request.form.get(f'map_{header}')
            if field and field != '_skip':
                new_mapping[header] = field

        job.column_mapping = new_mapping
        job.status = 'mapped'
        db.session.commit()

        flash('Spalten-Zuordnung gespeichert.', 'success')
        return redirect(url_for('csv_import.validate', job_id=job.id))

    # Vorschau-Daten laden
    preview = service.get_preview_data(job, max_rows=5)
    available_fields = FIELD_MAPPINGS.get(job.import_type, {}).get('fields', {})

    return render_template('csv_import/mapping.html',
                         job=job,
                         preview=preview,
                         available_fields=available_fields,
                         import_types=IMPORT_TYPES)


@csv_import_bp.route('/<int:job_id>/validate', methods=['GET', 'POST'])
@login_required
@admin_required
def validate(job_id):
    """Validierung und Vorschau"""
    job = CSVImportJob.query.get_or_404(job_id)
    service = CSVImportService()

    result = service.validate_import(job)
    preview = service.get_preview_data(job, max_rows=10)

    return render_template('csv_import/preview.html',
                         job=job,
                         result=result,
                         preview=preview,
                         import_types=IMPORT_TYPES)


@csv_import_bp.route('/<int:job_id>/execute', methods=['POST'])
@login_required
@admin_required
def execute(job_id):
    """Import ausfuehren"""
    job = CSVImportJob.query.get_or_404(job_id)
    service = CSVImportService()

    result = service.execute_import(job)

    flash(f'Import abgeschlossen: {result["imported"]} importiert, '
          f'{result["skipped"]} uebersprungen, {len(result["errors"])} Fehler.',
          'success' if not result['errors'] else 'warning')

    return redirect(url_for('csv_import.result', job_id=job.id))


@csv_import_bp.route('/<int:job_id>/result')
@login_required
@admin_required
def result(job_id):
    """Import-Ergebnis"""
    job = CSVImportJob.query.get_or_404(job_id)
    return render_template('csv_import/result.html',
                         job=job,
                         import_types=IMPORT_TYPES)


@csv_import_bp.route('/history')
@login_required
@admin_required
def history():
    """Import-Historie"""
    jobs = CSVImportJob.query.order_by(CSVImportJob.created_at.desc()).limit(50).all()
    return render_template('csv_import/upload.html',
                         import_types=IMPORT_TYPES,
                         history=jobs)
