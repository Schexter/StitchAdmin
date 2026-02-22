# -*- coding: utf-8 -*-
"""
Multi-Tenant SaaS - Tenant & UserTenant Models
Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime
from .models import db


class Tenant(db.Model):
    """
    Mandant/Firma - Jeder Kunde bekommt einen eigenen isolierten Datenbereich.
    Subdomain-basiert: firma.stitchadmin.de
    """
    __tablename__ = 'tenants'

    id = db.Column(db.Integer, primary_key=True)

    # Identifikation
    slug = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)

    # Domain & Subdomain
    subdomain = db.Column(db.String(100), unique=True, nullable=False, index=True)
    custom_domain = db.Column(db.String(200), unique=True, nullable=True)

    # Status & Abo
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    plan_tier = db.Column(db.String(50), default='starter')
    trial_ends_at = db.Column(db.DateTime, nullable=True)

    # Kontakt
    contact_email = db.Column(db.String(120), nullable=False)
    contact_phone = db.Column(db.String(50))

    # Adresse
    street = db.Column(db.String(200))
    postal_code = db.Column(db.String(20))
    city = db.Column(db.String(100))
    country = db.Column(db.String(100), default='Deutschland')

    # Branding
    logo_path = db.Column(db.String(500))
    primary_color = db.Column(db.String(7), default='#1a6b5a')
    secondary_color = db.Column(db.String(7), default='#6c757d')

    # Einstellungen (JSON)
    settings = db.Column(db.JSON, default=dict)

    # Oeffentliche Website
    website_enabled = db.Column(db.Boolean, default=False)
    website_published = db.Column(db.Boolean, default=False)

    # Storage
    storage_used_mb = db.Column(db.Integer, default=0)
    storage_limit_mb = db.Column(db.Integer, default=10240)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    user_memberships = db.relationship('UserTenant', back_populates='tenant',
                                       cascade='all, delete-orphan', lazy='dynamic')

    def __repr__(self):
        return f'<Tenant {self.subdomain}: {self.name}>'

    def is_trial_expired(self):
        if self.plan_tier != 'trial' or not self.trial_ends_at:
            return False
        return datetime.utcnow() > self.trial_ends_at

    @staticmethod
    def get_by_subdomain(subdomain):
        return Tenant.query.filter_by(subdomain=subdomain, is_active=True).first()

    @staticmethod
    def get_by_slug(slug):
        return Tenant.query.filter_by(slug=slug, is_active=True).first()


class UserTenant(db.Model):
    """
    Many-to-Many: User gehoert zu einem oder mehreren Tenants.
    Speichert Rolle und Berechtigungen pro Tenant.
    """
    __tablename__ = 'user_tenants'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)

    # Rolle innerhalb dieses Tenants
    role = db.Column(db.String(50), default='user')
    # system_admin, tenant_admin, manager, user, readonly

    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_primary = db.Column(db.Boolean, default=False)

    # Tenant-spezifische Berechtigungen
    permissions_json = db.Column(db.JSON, default=dict)

    # Timestamps
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_accessed = db.Column(db.DateTime)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'tenant_id', name='unique_user_tenant'),
        db.Index('idx_user_tenant_active', 'user_id', 'tenant_id', 'is_active'),
    )

    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='tenant_memberships')
    tenant = db.relationship('Tenant', back_populates='user_memberships')

    def __repr__(self):
        return f'<UserTenant user={self.user_id} tenant={self.tenant_id} role={self.role}>'


__all__ = ['Tenant', 'UserTenant']
