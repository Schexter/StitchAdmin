# -*- coding: utf-8 -*-
"""
Automatisches Tenant-Filtering via SQLAlchemy Session Events.
Filtert alle SELECT-Queries und setzt tenant_id bei INSERT automatisch.

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

import logging
from flask import g, has_request_context
from sqlalchemy import event
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def get_current_tenant_id():
    """
    Aktuellen Tenant aus Flask-Kontext holen.
    Gibt None zurueck wenn:
    - Kein Request-Kontext (CLI, Migrations, Tests)
    - System-Admin hat Bypass aktiviert
    - Kein Tenant aufgeloest
    """
    if not has_request_context():
        return None

    if getattr(g, 'bypass_tenant_filter', False):
        return None

    return getattr(g, 'current_tenant_id', None)


def is_tenant_model(model_class):
    """Prueft ob ein Model tenant_id hat (TenantMixin nutzt)."""
    return hasattr(model_class, 'tenant_id')


def init_tenant_filtering(app):
    """
    Registriert SQLAlchemy Event Listener fuer automatisches Tenant-Filtering.
    Wird nur aktiviert wenn MULTI_TENANT_ENABLED=True.
    """
    if not app.config.get('MULTI_TENANT_ENABLED', False):
        logger.info("Multi-Tenant Filtering ist DEAKTIVIERT (Feature-Flag)")
        return

    logger.info("Multi-Tenant Filtering wird aktiviert...")

    @event.listens_for(Session, "do_orm_execute")
    def _auto_filter_select(orm_execute_state):
        """
        Automatisch WHERE tenant_id = X zu allen SELECT-Queries hinzufuegen.
        """
        tenant_id = get_current_tenant_id()
        if tenant_id is None:
            return

        if not orm_execute_state.is_select:
            return

        # Mapper/Entity aus Statement extrahieren
        if not orm_execute_state.is_orm_statement:
            return

        # Versuche das Model aus den column_descriptions zu holen
        try:
            for desc in orm_execute_state.statement.column_descriptions:
                entity = desc.get('entity')
                if entity and is_tenant_model(entity):
                    orm_execute_state.statement = orm_execute_state.statement.filter(
                        entity.tenant_id == tenant_id
                    )
                    break
        except Exception:
            # Bei Fehler nicht filtern (z.B. raw SQL, subqueries)
            pass

    @event.listens_for(Session, "before_flush")
    def _auto_set_tenant_on_insert(session, flush_context, instances):
        """
        Automatisch tenant_id bei neuen Objekten setzen.
        """
        tenant_id = get_current_tenant_id()
        if tenant_id is None:
            return

        for instance in session.new:
            if is_tenant_model(instance.__class__):
                if instance.tenant_id is None:
                    instance.tenant_id = tenant_id

    logger.info("Multi-Tenant Filtering AKTIV")


__all__ = ['init_tenant_filtering', 'get_current_tenant_id', 'is_tenant_model']
