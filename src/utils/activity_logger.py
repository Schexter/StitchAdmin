# -*- coding: utf-8 -*-
"""
Zentraler Aktivitaets-Logger fuer Audit-Trail (DB-basiert)
==========================================================
Ersetzt die duplizierten log_activity()-Funktionen in den Controllern.

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import logging
from flask import request
from flask_login import current_user

logger = logging.getLogger(__name__)


def log_activity(action, details, username=None):
    """
    Protokolliert Benutzeraktivitaeten in der Datenbank.

    Args:
        action: Aktion (login, logout, create_order, etc.)
        details: Detaillierte Beschreibung
        username: Optional - wird automatisch von current_user geholt
    """
    from src.models.models import db, ActivityLog

    try:
        if username is None:
            if current_user and current_user.is_authenticated:
                username = current_user.username
            else:
                username = 'system'

        ip_address = None
        user_agent = None
        try:
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')[:200]
        except RuntimeError:
            pass  # Ausserhalb eines Request-Kontexts

        activity = ActivityLog(
            username=username,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.session.add(activity)
        db.session.commit()
    except Exception as e:
        logger.error(f"Fehler beim Protokollieren: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
