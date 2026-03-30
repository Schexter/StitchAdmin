# -*- coding: utf-8 -*-
"""
Plan-Gating Decorator - Prueft ob der aktuelle Tenant
Zugriff auf ein Modul/Feature hat basierend auf seinem Plan.

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

from functools import wraps
from flask import g, flash, redirect, url_for, render_template
from flask_login import current_user


def require_plan_module(module_name):
    """
    Decorator: Prueft ob der Tenant des aktuellen Users
    Zugriff auf das angegebene Modul hat.

    Usage:
        @require_plan_module('crm')
        def crm_dashboard():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            tenant = getattr(g, 'current_tenant', None)

            # Kein Tenant-Kontext -> kein Gating (Single-Tenant Modus)
            if tenant is None:
                return f(*args, **kwargs)

            # Plan aktiv?
            if not tenant.is_plan_active:
                flash('Ihr Plan ist abgelaufen oder nicht aktiv. '
                      'Bitte kontaktieren Sie den Support.', 'warning')
                return redirect(url_for('dashboard'))

            # Modul im Plan enthalten?
            if not tenant.has_module_access(module_name):
                flash(f'Das Modul "{module_name}" ist in Ihrem aktuellen Plan '
                      f'({tenant.plan_label}) nicht enthalten. '
                      f'Bitte upgraden Sie Ihren Plan.', 'warning')
                return redirect(url_for('dashboard'))

            return f(*args, **kwargs)
        return decorated
    return decorator


def require_plan_limit(limit_key, count_func):
    """
    Decorator: Prueft ob ein Limit noch nicht erreicht ist.

    Usage:
        @require_plan_limit('max_customers', lambda: Customer.query.count())
        def new_customer():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            tenant = getattr(g, 'current_tenant', None)

            # Kein Tenant-Kontext -> kein Gating
            if tenant is None:
                return f(*args, **kwargs)

            current_count = count_func()
            if not tenant.check_limit(limit_key, current_count):
                limit = tenant.get_limit(limit_key)
                flash(f'Limit erreicht: Ihr Plan ({tenant.plan_label}) '
                      f'erlaubt maximal {limit}. '
                      f'Bitte upgraden Sie Ihren Plan.', 'warning')
                return redirect(url_for('dashboard'))

            return f(*args, **kwargs)
        return decorated
    return decorator


def get_tenant_plan_info():
    """
    Gibt Plan-Infos des aktuellen Tenants zurueck (fuer Templates).
    Returns dict mit plan_tier, plan_label, limits, etc.
    """
    tenant = getattr(g, 'current_tenant', None)
    if tenant is None:
        return None

    return {
        'plan_tier': tenant.plan_tier,
        'plan_label': tenant.plan_label,
        'price_monthly': tenant.price_monthly,
        'is_trial': tenant.plan_tier == 'trial',
        'trial_days_remaining': tenant.trial_days_remaining,
        'is_plan_active': tenant.is_plan_active,
        'billing_status': tenant.billing_status,
        'storage_used_mb': tenant.storage_used_mb,
        'storage_limit_mb': tenant.storage_limit_mb,
    }
