# -*- coding: utf-8 -*-
"""
Feedback / Bug-Report Model
============================
Integrierter Bug-Melder fuer alle Benutzer.

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime
from src.models import db


class FeedbackReport(db.Model):
    """Bug-Reports und Feedback von Benutzern"""
    __tablename__ = 'feedback_reports'

    id = db.Column(db.Integer, primary_key=True)
    typ = db.Column(db.String(20), default='bug')  # bug, feature, frage, sonstiges
    titel = db.Column(db.String(200), nullable=False)
    beschreibung = db.Column(db.Text)
    seite_url = db.Column(db.String(500))  # Auf welcher Seite war der User
    browser_info = db.Column(db.String(500))
    screenshot_path = db.Column(db.String(500))

    # Prioritaet
    prioritaet = db.Column(db.String(20), default='normal')  # niedrig, normal, hoch, kritisch

    # Status
    status = db.Column(db.String(20), default='neu')  # neu, in_arbeit, erledigt, abgelehnt

    # Bearbeitung
    antwort = db.Column(db.Text)
    bearbeitet_von = db.Column(db.String(80))
    bearbeitet_am = db.Column(db.DateTime)

    # Metadaten
    erstellt_von = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
