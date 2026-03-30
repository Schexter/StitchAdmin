# -*- coding: utf-8 -*-
"""
Platform Admin Controller - SaaS-Verwaltung
Nur fuer System-Admins: Tenants verwalten, Plaene zuweisen, Zahlungen erfassen

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from src.models import db
from src.models.tenant import Tenant, TenantPayment, UserTenant, PLAN_CONFIG
from src.models.models import User
import logging

logger = logging.getLogger(__name__)

platform_admin_bp = Blueprint('platform_admin', __name__, url_prefix='/platform')


def require_system_admin(f):
    """Decorator: Nur System-Admins (Plattform-Betreiber) duerfen zugreifen"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Kein Zugriff - nur fuer Plattform-Administratoren.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


# ==========================================
# DASHBOARD - Uebersicht aller Tenants
# ==========================================

@platform_admin_bp.route('/')
@login_required
@require_system_admin
def dashboard():
    """Platform Admin Dashboard - Tenant-Uebersicht und KPIs"""
    tenants = Tenant.query.order_by(Tenant.created_at.desc()).all()

    # KPIs berechnen
    total_tenants = len(tenants)
    active_tenants = sum(1 for t in tenants if t.is_active and t.is_plan_active)
    trial_tenants = sum(1 for t in tenants if t.plan_tier == 'trial')
    paying_tenants = sum(1 for t in tenants if t.plan_tier in ('starter', 'professional', 'enterprise')
                         and t.billing_status == 'active')

    # MRR (Monthly Recurring Revenue)
    mrr = sum(t.price_monthly for t in tenants
              if t.plan_tier in ('starter', 'professional', 'enterprise')
              and t.billing_status == 'active')

    # Letzte Zahlungen
    recent_payments = TenantPayment.query.order_by(
        TenantPayment.created_at.desc()
    ).limit(10).all()

    return render_template('platform_admin/dashboard.html',
                           tenants=tenants,
                           total_tenants=total_tenants,
                           active_tenants=active_tenants,
                           trial_tenants=trial_tenants,
                           paying_tenants=paying_tenants,
                           mrr=mrr,
                           recent_payments=recent_payments,
                           plan_config=PLAN_CONFIG)


# ==========================================
# TENANT DETAIL & BEARBEITEN
# ==========================================

@platform_admin_bp.route('/tenant/<int:tenant_id>')
@login_required
@require_system_admin
def tenant_detail(tenant_id):
    """Tenant-Detailansicht"""
    tenant = Tenant.query.get_or_404(tenant_id)
    members = UserTenant.query.filter_by(tenant_id=tenant_id).all()
    payments = TenantPayment.query.filter_by(tenant_id=tenant_id).order_by(
        TenantPayment.created_at.desc()
    ).limit(20).all()

    return render_template('platform_admin/tenant_detail.html',
                           tenant=tenant,
                           members=members,
                           payments=payments,
                           plan_config=PLAN_CONFIG)


@platform_admin_bp.route('/tenant/<int:tenant_id>/update-plan', methods=['POST'])
@login_required
@require_system_admin
def update_plan(tenant_id):
    """Plan eines Tenants aendern"""
    tenant = Tenant.query.get_or_404(tenant_id)
    new_plan = request.form.get('plan_tier')
    billing_status = request.form.get('billing_status', 'active')

    if new_plan not in PLAN_CONFIG:
        flash('Ungueltiger Plan.', 'danger')
        return redirect(url_for('platform_admin.tenant_detail', tenant_id=tenant_id))

    old_plan = tenant.plan_tier
    tenant.plan_tier = new_plan
    tenant.billing_status = billing_status

    if new_plan != 'trial':
        tenant.trial_ends_at = None
        if not tenant.next_billing_date:
            tenant.next_billing_date = date.today() + timedelta(days=30)

    tenant.storage_limit_mb = PLAN_CONFIG[new_plan].get('storage_mb', 10240)

    db.session.commit()

    logger.info(f"Plan geaendert: Tenant {tenant.name} ({tenant.subdomain}): "
                f"{old_plan} -> {new_plan}, Status: {billing_status}")
    flash(f'Plan fuer {tenant.name} auf {PLAN_CONFIG[new_plan]["label"]} geaendert.', 'success')
    return redirect(url_for('platform_admin.tenant_detail', tenant_id=tenant_id))


@platform_admin_bp.route('/tenant/<int:tenant_id>/toggle-active', methods=['POST'])
@login_required
@require_system_admin
def toggle_active(tenant_id):
    """Tenant aktivieren/deaktivieren"""
    tenant = Tenant.query.get_or_404(tenant_id)
    tenant.is_active = not tenant.is_active
    db.session.commit()

    status = 'aktiviert' if tenant.is_active else 'deaktiviert'
    flash(f'Tenant {tenant.name} wurde {status}.', 'success')
    return redirect(url_for('platform_admin.tenant_detail', tenant_id=tenant_id))


# ==========================================
# ZAHLUNGEN ERFASSEN
# ==========================================

@platform_admin_bp.route('/tenant/<int:tenant_id>/add-payment', methods=['POST'])
@login_required
@require_system_admin
def add_payment(tenant_id):
    """Manuelle Zahlung erfassen"""
    tenant = Tenant.query.get_or_404(tenant_id)

    amount = request.form.get('amount', '0')
    method = request.form.get('payment_method', 'bank_transfer')
    reference = request.form.get('reference', '')
    description = request.form.get('description', '')
    period_months = int(request.form.get('period_months', 1))

    try:
        amount = Decimal(amount.replace(',', '.'))
    except Exception:
        flash('Ungueltiger Betrag.', 'danger')
        return redirect(url_for('platform_admin.tenant_detail', tenant_id=tenant_id))

    today = date.today()
    period_start = today
    period_end = today + timedelta(days=30 * period_months)

    # Rechnungsnummer generieren
    year = today.year
    count = TenantPayment.query.filter(
        TenantPayment.created_at >= datetime(year, 1, 1)
    ).count() + 1
    invoice_number = f'SA-{year}-{count:04d}'

    payment = TenantPayment(
        tenant_id=tenant_id,
        amount=amount,
        payment_method=method,
        reference=reference,
        description=description or f'{tenant.plan_label} - {today.strftime("%B %Y")}',
        period_start=period_start,
        period_end=period_end,
        status='completed',
        invoice_number=invoice_number,
        created_by=current_user.username,
    )
    db.session.add(payment)

    # Billing-Status aktualisieren
    tenant.billing_status = 'active'
    tenant.last_payment_date = today
    tenant.last_payment_amount = amount
    tenant.next_billing_date = period_end

    db.session.commit()

    logger.info(f"Zahlung erfasst: {amount}€ fuer Tenant {tenant.name} ({invoice_number})")
    flash(f'Zahlung von {amount}€ erfasst (Rechnung: {invoice_number}).', 'success')
    return redirect(url_for('platform_admin.tenant_detail', tenant_id=tenant_id))
