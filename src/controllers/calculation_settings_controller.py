"""
Calculation Settings Controller - Preiskalkulation & Betriebskosten
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from src.models import (
    db,
    OperatingCostCategory,
    OperatingCost,
    CalculationMode,
    Machine
)

# Blueprint
calc_settings_bp = Blueprint('calculation_settings', __name__, url_prefix='/settings/calculation')

@calc_settings_bp.route('/')
@login_required
def index():
    """Übersicht Kalkulationseinstellungen"""
    # Initialisiere Standard-Kategorien und Modi falls nicht vorhanden
    categories = OperatingCostCategory.get_default_categories()
    modes = CalculationMode.initialize_system_modes()

    # Aktive Modi
    active_modes = CalculationMode.query.filter_by(active=True).all()
    default_mode = CalculationMode.get_default_mode()

    # Statistiken
    total_monthly_costs = OperatingCost.get_total_monthly_costs()
    hourly_rate = OperatingCost.get_total_hourly_rate()

    # Kosten pro Kategorie
    category_costs = []
    for category in categories:
        category_costs.append({
            'category': category,
            'monthly_cost': category.get_total_monthly_cost()
        })

    # Maschinen mit Stundensätzen
    machines = Machine.query.all()
    for machine in machines:
        if not machine.calculated_hourly_rate:
            machine.calculate_hourly_rate()
            db.session.commit()

    return render_template('settings/calculation/index.html',
                         categories=categories,
                         category_costs=category_costs,
                         modes=active_modes,
                         default_mode=default_mode,
                         total_monthly_costs=total_monthly_costs,
                         hourly_rate=hourly_rate,
                         machines=machines)

# ==================== BETRIEBSKOSTEN ====================

@calc_settings_bp.route('/operating-costs')
@login_required
def operating_costs():
    """Betriebskosten verwalten"""
    categories = OperatingCostCategory.query.filter_by(active=True).order_by(OperatingCostCategory.sort_order).all()
    costs = OperatingCost.query.filter_by(active=True).order_by(OperatingCost.category_id, OperatingCost.name).all()
    machines = Machine.query.all()

    return render_template('settings/calculation/operating_costs.html',
                         categories=categories,
                         costs=costs,
                         machines=machines)

@calc_settings_bp.route('/operating-costs/add', methods=['POST'])
@login_required
def add_operating_cost():
    """Neue Betriebskosten hinzufügen"""
    try:
        cost = OperatingCost(
            category_id=int(request.form['category_id']),
            name=request.form['name'],
            description=request.form.get('description'),
            amount=float(request.form['amount']),
            interval=request.form['interval'],
            distribute_over_machines=request.form.get('distribute_over_machines') == 'true',
            specific_machine_id=request.form.get('specific_machine_id') or None,
            created_by=current_user.username
        )

        db.session.add(cost)
        db.session.commit()

        flash(f'Betriebskosten "{cost.name}" erfolgreich hinzugefügt', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Hinzufügen: {str(e)}', 'danger')

    return redirect(url_for('calculation_settings.operating_costs'))

@calc_settings_bp.route('/operating-costs/<int:cost_id>/edit', methods=['POST'])
@login_required
def edit_operating_cost(cost_id):
    """Betriebskosten bearbeiten"""
    try:
        cost = OperatingCost.query.get_or_404(cost_id)

        cost.category_id = int(request.form['category_id'])
        cost.name = request.form['name']
        cost.description = request.form.get('description')
        cost.amount = float(request.form['amount'])
        cost.interval = request.form['interval']
        cost.distribute_over_machines = request.form.get('distribute_over_machines') == 'true'
        cost.specific_machine_id = request.form.get('specific_machine_id') or None
        cost.updated_by = current_user.username

        db.session.commit()

        flash(f'Betriebskosten "{cost.name}" erfolgreich aktualisiert', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Aktualisieren: {str(e)}', 'danger')

    return redirect(url_for('calculation_settings.operating_costs'))

@calc_settings_bp.route('/operating-costs/<int:cost_id>/delete', methods=['POST'])
@login_required
def delete_operating_cost(cost_id):
    """Betriebskosten löschen"""
    try:
        cost = OperatingCost.query.get_or_404(cost_id)
        name = cost.name

        db.session.delete(cost)
        db.session.commit()

        flash(f'Betriebskosten "{name}" erfolgreich gelöscht', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Löschen: {str(e)}', 'danger')

    return redirect(url_for('calculation_settings.operating_costs'))

# ==================== MASCHINENSTUNDENSÄTZE ====================

@calc_settings_bp.route('/machine-rates')
@login_required
def machine_rates():
    """Maschinenstundensätze konfigurieren"""
    machines = Machine.query.all()

    # Berechne Stundensätze für alle Maschinen
    for machine in machines:
        if not machine.calculated_hourly_rate:
            machine.calculate_hourly_rate()

    db.session.commit()

    return render_template('settings/calculation/machine_rates.html',
                         machines=machines)

@calc_settings_bp.route('/machine-rates/<machine_id>/update', methods=['POST'])
@login_required
def update_machine_rate(machine_id):
    """Maschinenstundensatz aktualisieren"""
    try:
        machine = Machine.query.get_or_404(machine_id)

        # Anschaffung
        machine.purchase_price = float(request.form.get('purchase_price') or 0)
        machine.depreciation_years = int(request.form.get('depreciation_years') or 10)
        machine.expected_lifetime_hours = int(request.form.get('expected_lifetime_hours') or 20000)

        # Betriebskosten
        machine.energy_cost_per_hour = float(request.form.get('energy_cost_per_hour') or 0)
        machine.maintenance_cost_per_hour = float(request.form.get('maintenance_cost_per_hour') or 0)
        machine.space_cost_per_hour = float(request.form.get('space_cost_per_hour') or 0)

        # Custom Rate
        machine.use_custom_rate = request.form.get('use_custom_rate') == 'true'
        if machine.use_custom_rate:
            machine.custom_hourly_rate = float(request.form.get('custom_hourly_rate') or 0)

        # Personalkosten
        machine.labor_cost_per_hour = float(request.form.get('labor_cost_per_hour') or 35.0)

        # Neu berechnen
        machine.calculate_hourly_rate()
        machine.updated_by = current_user.username

        db.session.commit()

        flash(f'Maschinenstundensatz für "{machine.name}" erfolgreich aktualisiert', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Aktualisieren: {str(e)}', 'danger')

    return redirect(url_for('calculation_settings.machine_rates'))

# ==================== KALKULATIONSMODI ====================

@calc_settings_bp.route('/modes')
@login_required
def modes():
    """Kalkulationsmodi verwalten"""
    modes = CalculationMode.query.filter_by(active=True).all()
    default_mode = CalculationMode.get_default_mode()

    return render_template('settings/calculation/modes.html',
                         modes=modes,
                         default_mode=default_mode)

@calc_settings_bp.route('/modes/<int:mode_id>/set-default', methods=['POST'])
@login_required
def set_default_mode(mode_id):
    """Setze Standard-Kalkulationsmodus"""
    try:
        # Alle auf False
        CalculationMode.query.update({'is_default': False})

        # Gewählten auf True
        mode = CalculationMode.query.get_or_404(mode_id)
        mode.is_default = True

        db.session.commit()

        flash(f'"{mode.display_name}" ist jetzt der Standard-Kalkulationsmodus', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')

    return redirect(url_for('calculation_settings.modes'))

@calc_settings_bp.route('/modes/<int:mode_id>/update', methods=['POST'])
@login_required
def update_mode(mode_id):
    """Kalkulationsmodus aktualisieren (nur Custom)"""
    try:
        mode = CalculationMode.query.get_or_404(mode_id)

        if mode.is_system_mode and mode.name != 'custom':
            flash('System-Modi können nicht bearbeitet werden', 'warning')
            return redirect(url_for('calculation_settings.modes'))

        # Komponenten aktualisieren
        components = {
            'base_factor': request.form.get('base_factor') == 'true',
            'material_costs': request.form.get('material_costs') == 'true',
            'machine_time': request.form.get('machine_time') == 'true',
            'labor_costs': request.form.get('labor_costs') == 'true',
            'operating_costs': request.form.get('operating_costs') == 'true',
            'complexity_markup': request.form.get('complexity_markup') == 'true',
            'quantity_discount': request.form.get('quantity_discount') == 'true'
        }

        mode.set_components(components)
        mode.default_profit_margin = float(request.form.get('default_profit_margin') or 25.0)
        mode.default_safety_buffer = float(request.form.get('default_safety_buffer') or 5.0)
        mode.updated_by = current_user.username

        db.session.commit()

        flash(f'Kalkulationsmodus "{mode.display_name}" erfolgreich aktualisiert', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')

    return redirect(url_for('calculation_settings.modes'))

# ==================== API ====================

@calc_settings_bp.route('/api/calculate-preview', methods=['POST'])
@login_required
def calculate_preview():
    """API: Kalkulationsvorschau berechnen"""
    try:
        data = request.get_json()

        # Basis-Daten
        base_price = float(data.get('base_price', 0))
        mode_id = int(data.get('mode_id', 0))
        machine_id = data.get('machine_id')
        production_time_minutes = int(data.get('production_time_minutes', 0))

        # Hole Modus
        mode = CalculationMode.query.get(mode_id) if mode_id else CalculationMode.get_default_mode()
        components = mode.get_components()

        # Berechne Komponenten
        result = {
            'mode_name': mode.display_name,
            'components': {},
            'total': 0
        }

        # 1. Basis (Faktor)
        if components.get('base_factor'):
            result['components']['base'] = base_price * 1.5  # Vereinfacht

        # 2. Maschinenkosten
        if components.get('machine_time') and machine_id and production_time_minutes > 0:
            machine = Machine.query.get(machine_id)
            if machine:
                hours = production_time_minutes / 60
                rate = machine.get_hourly_rate()
                result['components']['machine_cost'] = rate * hours

        # 3. Personalkosten
        if components.get('labor_costs') and machine_id and production_time_minutes > 0:
            machine = Machine.query.get(machine_id)
            if machine:
                hours = production_time_minutes / 60
                result['components']['labor_cost'] = machine.get_labor_cost_per_hour() * hours

        # 4. Betriebskosten
        if components.get('operating_costs') and production_time_minutes > 0:
            hours = production_time_minutes / 60
            hourly_rate = OperatingCost.get_total_hourly_rate()
            result['components']['operating_cost'] = hourly_rate * hours

        # Summe
        result['total'] = sum(result['components'].values())

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 400
