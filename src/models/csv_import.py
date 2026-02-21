# -*- coding: utf-8 -*-
"""
CSV Import Model
================
Tracking von CSV-Import-Jobs (Status, Mapping, Fehler)

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime
from src.models import db


class CSVImportJob(db.Model):
    """Einzelner CSV-Import-Vorgang"""
    __tablename__ = 'csv_import_jobs'

    id = db.Column(db.Integer, primary_key=True)

    # Import-Typ
    import_type = db.Column(db.String(30), nullable=False)  # customer, article, booking, bank_statement

    # Datei-Info
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500))
    encoding = db.Column(db.String(20), default='utf-8')
    delimiter = db.Column(db.String(5), default=';')

    # Status: uploaded, mapped, validated, imported, error
    status = db.Column(db.String(20), default='uploaded')

    # Spalten-Mapping (JSON: {"csv_header": "db_field"})
    column_mapping = db.Column(db.JSON)
    detected_headers = db.Column(db.JSON)

    # Ergebnis
    total_rows = db.Column(db.Integer, default=0)
    imported_rows = db.Column(db.Integer, default=0)
    skipped_rows = db.Column(db.Integer, default=0)
    error_rows = db.Column(db.Integer, default=0)
    error_details = db.Column(db.JSON)

    # Meta
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(100))
    completed_at = db.Column(db.DateTime)

    def __repr__(self):
        return f"<CSVImportJob {self.id} {self.import_type} [{self.status}]>"
