# -*- coding: utf-8 -*-
"""
Billing Controller - Tenant-seitiges Abrechnungs-Dashboard
Zeigt dem Tenant seinen Plan, Limits, Zahlungshistorie und Upgrade-Optionen.

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from flask_login import login_required, current_user
from src.models import db
from src.models.tenant import Tenant, TenantPayment, PLAN_CONFIG
import logging

logger = logging.getLogger(__name__)

billing_bp = Blueprint('billing', __name__, url_prefix='/billing')


def _get_user_tenant():
    """Holt den Tenant des aktuellen Users."""
    tenant = getattr(g, 'current_tenant', None)
    if tenant:
        return tenant

    # Fallback: Suche ueber UserTenant
    try:
        from src.models.tenant import UserTenant
        membership = UserTenant.query.filter_by(
            user_id=current_user.id, is_active=True
        ).first()
        if membership:
            return membership.tenant
    except Exception:
        pass

    # Fallback: Default-Tenant
    return Tenant.query.filter_by(slug='default').first()


@billing_bp.route('/')
@login_required
def overview():
    """Plan-Uebersicht und Billing-Dashboard fuer den Tenant"""
    tenant = _get_user_tenant()
    if not tenant:
        flash('Kein Tenant zugeordnet.', 'warning')
        return redirect(url_for('dashboard'))

    # Zahlungshistorie
    payments = TenantPayment.query.filter_by(
        tenant_id=tenant.id
    ).order_by(TenantPayment.created_at.desc()).limit(20).all()

    # Nutzungsstatistiken
    from src.models.models import User, Customer, Order
    from src.models.tenant import UserTenant

    user_count = UserTenant.query.filter_by(
        tenant_id=tenant.id, is_active=True
    ).count()
    customer_count = Customer.query.count()
    order_count = Order.query.count()

    usage = {
        'users': {
            'current': user_count,
            'limit': tenant.get_limit('max_users'),
        },
        'customers': {
            'current': customer_count,
            'limit': tenant.get_limit('max_customers'),
        },
        'orders': {
            'current': order_count,
            'limit': tenant.get_limit('max_orders'),
        },
        'storage': {
            'current': tenant.storage_used_mb,
            'limit': tenant.storage_limit_mb,
        },
    }

    # Prozentwerte berechnen
    for key, val in usage.items():
        if val['limit'] and val['limit'] > 0:
            val['percent'] = min(100, round(val['current'] / val['limit'] * 100, 1))
        else:
            val['percent'] = 0

    return render_template('billing/overview.html',
                           tenant=tenant,
                           payments=payments,
                           usage=usage,
                           plan_config=PLAN_CONFIG,
                           current_plan=tenant.plan_config)


@billing_bp.route('/request-upgrade', methods=['POST'])
@login_required
def request_upgrade():
    """Upgrade-Anfrage senden (wird spaeter per E-Mail oder Stripe abgewickelt)"""
    tenant = _get_user_tenant()
    if not tenant:
        flash('Kein Tenant zugeordnet.', 'warning')
        return redirect(url_for('dashboard'))

    requested_plan = request.form.get('plan_tier')
    if requested_plan not in PLAN_CONFIG:
        flash('Ungueltiger Plan.', 'danger')
        return redirect(url_for('billing.overview'))

    if requested_plan == tenant.plan_tier:
        flash('Sie nutzen bereits diesen Plan.', 'info')
        return redirect(url_for('billing.overview'))

    logger.info(f"Upgrade-Anfrage: Tenant {tenant.name} ({tenant.subdomain}) "
                f"moechte von {tenant.plan_tier} auf {requested_plan} wechseln. "
                f"User: {current_user.username}")

    flash(f'Ihre Upgrade-Anfrage auf "{PLAN_CONFIG[requested_plan]["label"]}" '
          f'wurde gesendet. Wir melden uns in Kuerze bei Ihnen!', 'success')
    return redirect(url_for('billing.overview'))
