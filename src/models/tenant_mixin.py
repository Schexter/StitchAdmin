# -*- coding: utf-8 -*-
"""
TenantMixin - Wird von allen mandantenspezifischen Models geerbt.
Fuegt tenant_id Spalte und Index hinzu.

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

from .models import db


class TenantMixin:
    """
    Mixin fuer mandantenspezifische Models.
    Fuegt tenant_id (FK zu tenants.id) hinzu.

    Usage:
        class Customer(TenantMixin, db.Model):
            __tablename__ = 'customers'
            ...
    """

    tenant_id = db.Column(
        db.Integer,
        db.ForeignKey('tenants.id', ondelete='CASCADE'),
        nullable=True,  # Erstmal nullable - wird nach Backfill auf NOT NULL gesetzt
        index=True
    )


__all__ = ['TenantMixin']
