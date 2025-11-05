"""
Settings Controller für erweiterte Preiskalkulation und MwSt-Verwaltung
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from src.models import db
from src.models.models import PriceCalculationSettings
from src.models.settings import TaxRate, PriceCalculationRule, ImportSettings

# Blueprint für Settings erweitern
settings_advanced_bp = Blueprint('settings_advanced', __name__, url_prefix='/settings/advanced')

@settings_advanced_bp.route('/')
@login_required
def index():
    """Erweiterte Einstellungen Übersicht"""
    # Hole aktuelle Einstellungen
    tax_rates = TaxRate.get_active_rates()
    calculation_rules = PriceCalculationRule.query.filter_by(active=True).order_by(PriceCalculationRule.priority).all()
    import_settings = ImportSettings.get_default_settings()
    
    # Legacy Einstellungen
    legacy_calculated = PriceCalculationSettings.get_setting('price_factor_calculated', 1.5)
    legacy_recommended = PriceCalculationSettings.get_setting('price_factor_recommended', 2.0)
    
    return render_template('settings/advanced/index.html',
                         tax_rates=tax_rates,
                         calculation_rules=calculation_rules,
                         import_settings=import_settings,
                         legacy_calculated=legacy_calculated,
                         legacy_recommended=legacy_recommended)

@settings_advanced_bp.route('/tax-rates')
@login_required
def tax_rates():
    """MwSt-Sätze verwalten"""
    rates = TaxRate.query.order_by(TaxRate.rate.desc()).all()
    return render_template('settings/advanced/tax_rates.html', tax_rates=rates)

@settings_advanced_bp.route('/tax-rates/new', methods=['GET', 'POST'])
@login_required
def new_tax_rate():
    """Neuen MwSt-Satz erstellen"""
    if request.method == 'POST':
        # Wenn als Standard markiert, andere Standards entfernen
        is_default = request.form.get('is_default') == 'on'
        if is_default:
            TaxRate.query.filter_by(is_default=True).update({'is_default': False})
        
        tax_rate = TaxRate(
            name=request.form.get('name'),
            rate=float(request.form.get('rate')),
            country=request.form.get('country', 'DE'),
            description=request.form.get('description', ''),
            active=request.form.get('active') == 'on',
            is_default=is_default,
            valid_from=datetime.strptime(request.form.get('valid_from'), '%Y-%m-%d').date() if request.form.get('valid_from') else None,
            valid_to=datetime.strptime(request.form.get('valid_to'), '%Y-%m-%d').date() if request.form.get('valid_to') else None,
            created_by=current_user.username
        )
        
        db.session.add(tax_rate)
        db.session.commit()
        
        flash(f'MwSt-Satz "{tax_rate.name}" wurde erstellt!', 'success')
        return redirect(url_for('settings_advanced.tax_rates'))
    
    return render_template('settings/advanced/tax_rate_form.html', tax_rate=None)

@settings_advanced_bp.route('/calculation-rules')
@login_required
def calculation_rules():
    """Preiskalkulationsregeln verwalten"""
    rules = PriceCalculationRule.query.order_by(PriceCalculationRule.priority).all()
    return render_template('settings/advanced/calculation_rules.html', rules=rules)

@settings_advanced_bp.route('/calculation-rules/new', methods=['GET', 'POST'])
@login_required
def new_calculation_rule():
    """Neue Kalkulationsregel erstellen"""
    if request.method == 'POST':
        rule = PriceCalculationRule(
            name=request.form.get('name'),
            description=request.form.get('description', ''),
            factor_calculated=float(request.form.get('factor_calculated', 1.5)),
            factor_recommended=float(request.form.get('factor_recommended', 2.0)),
            tax_rate_id=int(request.form.get('tax_rate_id')) if request.form.get('tax_rate_id') else None,
            include_tax_in_calculation=request.form.get('include_tax_in_calculation') == 'on',
            round_to_cents=int(request.form.get('round_to_cents', 1)),
            round_up_threshold=float(request.form.get('round_up_threshold', 0.5)),
            min_price=float(request.form.get('min_price')) if request.form.get('min_price') else None,
            max_markup_percent=float(request.form.get('max_markup_percent')) if request.form.get('max_markup_percent') else None,
            priority=int(request.form.get('priority', 100)),
            active=request.form.get('active') == 'on',
            created_by=current_user.username
        )
        
        # Kategorien und Lieferanten verarbeiten
        categories = request.form.getlist('categories')
        suppliers = request.form.getlist('suppliers')
        rule.set_categories([int(c) for c in categories if c])
        rule.set_suppliers(suppliers)
        
        db.session.add(rule)
        db.session.commit()
        
        flash(f'Kalkulationsregel "{rule.name}" wurde erstellt!', 'success')
        return redirect(url_for('settings_advanced.calculation_rules'))
    
    # Für Formular
    from src.models.models import ProductCategory, Supplier
    tax_rates = TaxRate.get_active_rates()
    categories = ProductCategory.query.filter_by(active=True).all()
    suppliers = Supplier.query.filter_by(active=True).all()
    
    return render_template('settings/advanced/calculation_rule_form.html', 
                         rule=None, 
                         tax_rates=tax_rates,
                         categories=categories,
                         suppliers=suppliers)

@settings_advanced_bp.route('/import-settings', methods=['GET', 'POST'])
@login_required
def import_settings():
    """Import-Einstellungen verwalten"""
    settings = ImportSettings.get_default_settings()
    
    if request.method == 'POST':
        if not settings:
            settings = ImportSettings(name='Standard Import Settings')
        
        settings.default_supplier = request.form.get('default_supplier', 'L-SHOP')
        settings.default_tax_rate_id = int(request.form.get('default_tax_rate_id')) if request.form.get('default_tax_rate_id') else None
        settings.default_calculation_rule_id = int(request.form.get('default_calculation_rule_id')) if request.form.get('default_calculation_rule_id') else None
        settings.update_existing_articles = request.form.get('update_existing_articles') == 'on'
        settings.create_missing_categories = request.form.get('create_missing_categories') == 'on'
        settings.create_missing_brands = request.form.get('create_missing_brands') == 'on'
        settings.auto_calculate_prices = request.form.get('auto_calculate_prices') == 'on'
        settings.import_only_active = request.form.get('import_only_active') == 'on'
        settings.min_stock_threshold = int(request.form.get('min_stock_threshold', 0))
        settings.price_update_strategy = request.form.get('price_update_strategy', 'calculate')
        settings.stock_update_strategy = request.form.get('stock_update_strategy', 'add')
        settings.updated_by = current_user.username
        
        if not settings.id:
            db.session.add(settings)
        
        db.session.commit()
        flash('Import-Einstellungen wurden gespeichert!', 'success')
        return redirect(url_for('settings_advanced.import_settings'))
    
    # Für Formular
    tax_rates = TaxRate.get_active_rates()
    calculation_rules = PriceCalculationRule.query.filter_by(active=True).all()
    
    return render_template('settings/advanced/import_settings.html',
                         settings=settings,
                         tax_rates=tax_rates,
                         calculation_rules=calculation_rules)

@settings_advanced_bp.route('/init-default-data', methods=['POST'])
@login_required
def init_default_data():
    """Initialisiere Standard-Daten für erweiterte Einstellungen"""
    try:
        # Standard MwSt-Sätze erstellen
        if not TaxRate.query.first():
            # Deutsche MwSt-Sätze
            standard_tax = TaxRate(
                name='Standard',
                rate=19.0,
                country='DE',
                description='Deutscher Standard-Mehrwertsteuersatz',
                active=True,
                is_default=True,
                valid_from=date(2007, 1, 1),
                created_by=current_user.username
            )
            
            reduced_tax = TaxRate(
                name='Ermäßigt',
                rate=7.0,
                country='DE',
                description='Deutscher ermäßigter Mehrwertsteuersatz',
                active=True,
                valid_from=date(2007, 1, 1),
                created_by=current_user.username
            )
            
            zero_tax = TaxRate(
                name='Befreit',
                rate=0.0,
                country='DE',
                description='Mehrwertsteuerbefreit',
                active=True,
                created_by=current_user.username
            )
            
            db.session.add_all([standard_tax, reduced_tax, zero_tax])
        
        # Standard Kalkulationsregel erstellen
        if not PriceCalculationRule.query.first():
            default_rule = PriceCalculationRule(
                name='Standard Kalkulation',
                description='Standard-Preiskalkulation für alle Artikel',
                factor_calculated=1.5,
                factor_recommended=2.0,
                tax_rate_id=1,  # Standard MwSt
                include_tax_in_calculation=False,
                round_to_cents=1,
                priority=100,
                active=True,
                created_by=current_user.username
            )
            db.session.add(default_rule)
        
        # Standard Import-Einstellungen
        if not ImportSettings.query.first():
            import_settings = ImportSettings(
                name='L-Shop Standard Import',
                default_supplier='L-SHOP',
                default_tax_rate_id=1,
                default_calculation_rule_id=1,
                update_existing_articles=True,
                create_missing_categories=True,
                create_missing_brands=True,
                auto_calculate_prices=True,
                import_only_active=True,
                price_update_strategy='calculate',
                stock_update_strategy='add',
                created_by=current_user.username
            )
            db.session.add(import_settings)
        
        db.session.commit()
        flash('Standard-Daten wurden erfolgreich initialisiert!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Initialisieren der Standard-Daten: {str(e)}', 'error')
    
    return redirect(url_for('settings_advanced.index'))

@settings_advanced_bp.route('/test-calculation', methods=['POST'])
@login_required  
def test_calculation():
    """Teste Preiskalkulation mit verschiedenen Parametern"""
    try:
        purchase_price = float(request.form.get('purchase_price', 0))
        rule_id = request.form.get('rule_id')
        
        if rule_id:
            rule = PriceCalculationRule.query.get(rule_id)
        else:
            rule = PriceCalculationRule.get_default_rule()
        
        if not rule:
            return jsonify({'error': 'Keine Kalkulationsregel gefunden'})
        
        calculated = rule.calculate_price(purchase_price, 'calculated')
        recommended = rule.calculate_price(purchase_price, 'recommended')
        
        # MwSt berechnen
        tax_rate = rule.tax_rate.rate if rule.tax_rate else 19.0
        tax_multiplier = 1 + (tax_rate / 100)
        
        return jsonify({
            'purchase_price': purchase_price,
            'calculated_net': calculated,
            'recommended_net': recommended,
            'calculated_gross': round(calculated * tax_multiplier, 2),
            'recommended_gross': round(recommended * tax_multiplier, 2),
            'tax_rate': tax_rate,
            'rule_name': rule.name,
            'factors': {
                'calculated': rule.factor_calculated,
                'recommended': rule.factor_recommended
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)})
