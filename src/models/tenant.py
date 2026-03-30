# -*- coding: utf-8 -*-
"""
Multi-Tenant SaaS - Tenant & UserTenant Models
Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, date
from .models import db


# Plan-Definitionen: Limits und Features pro Tier
PLAN_CONFIG = {
    'trial': {
        'label': 'Testphase',
        'price_monthly': 0,
        'max_users': 3,
        'max_customers': 50,
        'max_orders': 100,
        'storage_mb': 1024,
        'modules': [
            'customers', 'orders', 'articles', 'invoices',
            'machines', 'production', 'settings', 'users',
        ],
    },
    'starter': {
        'label': 'Starter',
        'price_monthly': 49,
        'max_users': 5,
        'max_customers': 500,
        'max_orders': 2000,
        'storage_mb': 5120,
        'modules': [
            'customers', 'orders', 'articles', 'invoices',
            'machines', 'production', 'shipping', 'suppliers',
            'settings', 'users', 'designs', 'file_browser',
        ],
    },
    'professional': {
        'label': 'Professional',
        'price_monthly': 99,
        'max_users': 15,
        'max_customers': 5000,
        'max_orders': 20000,
        'storage_mb': 20480,
        'modules': [
            'customers', 'orders', 'articles', 'invoices',
            'machines', 'production', 'shipping', 'suppliers',
            'settings', 'users', 'designs', 'file_browser',
            'crm', 'shop', 'email_integration', 'calendar',
            'offers', 'buchhaltung', 'contracts', 'csv_import',
        ],
    },
    'enterprise': {
        'label': 'Enterprise',
        'price_monthly': 199,
        'max_users': 999,
        'max_customers': 999999,
        'max_orders': 999999,
        'storage_mb': 102400,
        'modules': '__all__',  # Alle Module freigeschaltet
    },
}


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

    # Billing
    billing_status = db.Column(db.String(30), default='active')
    # active, past_due, grace_period, suspended, cancelled
    billing_cycle = db.Column(db.String(20), default='monthly')  # monthly, yearly
    next_billing_date = db.Column(db.Date, nullable=True)
    last_payment_date = db.Column(db.Date, nullable=True)
    last_payment_amount = db.Column(db.Numeric(10, 2), nullable=True)
    stripe_customer_id = db.Column(db.String(100), nullable=True)
    stripe_subscription_id = db.Column(db.String(100), nullable=True)
    tax_id = db.Column(db.String(50), nullable=True)  # USt-ID

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
    payments = db.relationship('TenantPayment', backref='tenant',
                               lazy='dynamic', order_by='TenantPayment.created_at.desc()')

    def __repr__(self):
        return f'<Tenant {self.subdomain}: {self.name}>'

    @property
    def plan_config(self):
        return PLAN_CONFIG.get(self.plan_tier, PLAN_CONFIG['starter'])

    @property
    def plan_label(self):
        return self.plan_config['label']

    @property
    def price_monthly(self):
        return self.plan_config['price_monthly']

    def is_trial_expired(self):
        if self.plan_tier != 'trial' or not self.trial_ends_at:
            return False
        return datetime.utcnow() > self.trial_ends_at

    @property
    def trial_days_remaining(self):
        if self.plan_tier != 'trial' or not self.trial_ends_at:
            return None
        delta = self.trial_ends_at - datetime.utcnow()
        return max(0, delta.days)

    @property
    def is_plan_active(self):
        """Pruefen ob der Plan aktiv und bezahlt ist"""
        if self.plan_tier == 'trial':
            return not self.is_trial_expired()
        return self.billing_status in ('active', 'grace_period')

    def has_module_access(self, module_name):
        """Pruefen ob dieses Modul im aktuellen Plan enthalten ist"""
        if not self.is_plan_active:
            return False
        modules = self.plan_config.get('modules', [])
        if modules == '__all__':
            return True
        return module_name in modules

    def get_limit(self, key):
        """Limit-Wert aus Plan-Config holen (max_users, max_customers, etc.)"""
        return self.plan_config.get(key, 0)

    def check_limit(self, key, current_count):
        """Pruefen ob ein Limit erreicht ist. True = noch Platz"""
        limit = self.get_limit(key)
        return current_count < limit

    @staticmethod
    def get_by_subdomain(subdomain):
        return Tenant.query.filter_by(subdomain=subdomain, is_active=True).first()

    @staticmethod
    def get_by_slug(slug):
        return Tenant.query.filter_by(slug=slug, is_active=True).first()


class TenantPayment(db.Model):
    """
    Zahlungshistorie pro Tenant - manuell oder via Stripe
    """
    __tablename__ = 'tenant_payments'

    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenants.id'), nullable=False, index=True)

    # Zahlungs-Details
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='EUR')
    payment_method = db.Column(db.String(50))  # bank_transfer, stripe, manual
    reference = db.Column(db.String(200))  # Ueberweisungsreferenz / Stripe Payment ID
    description = db.Column(db.String(300))  # z.B. "Professional Plan - Maerz 2026"

    # Zeitraum
    period_start = db.Column(db.Date, nullable=True)
    period_end = db.Column(db.Date, nullable=True)

    # Status
    status = db.Column(db.String(30), default='completed')
    # pending, completed, failed, refunded

    # Rechnungsdaten
    invoice_number = db.Column(db.String(50), nullable=True)
    invoice_pdf_path = db.Column(db.String(500), nullable=True)

    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_by = db.Column(db.String(100))

    def __repr__(self):
        return f'<TenantPayment {self.amount}€ for tenant={self.tenant_id}>'


__all__ = ['Tenant', 'UserTenant', 'TenantPayment', 'PLAN_CONFIG']


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
