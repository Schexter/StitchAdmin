"""
Zentraler Settings Controller für StitchAdmin
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from src.models import db
from src.models.models import PriceCalculationSettings, User, ProductCategory, Brand, Supplier

# Versuche erweiterte Settings zu importieren
try:
    from src.models.settings import TaxRate, PriceCalculationRule, ImportSettings
    ADVANCED_SETTINGS_AVAILABLE = True
except ImportError:
    ADVANCED_SETTINGS_AVAILABLE = False

# Blueprint für zentrale Einstellungen
settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/')
@login_required
def index():
    """Zentrale Einstellungen-Übersicht"""
    
    # Sammle alle aktuellen Einstellungen
    settings_overview = {
        'user_count': User.query.count(),
        'admin_count': User.query.filter_by(is_admin=True).count(),
        'category_count': ProductCategory.query.count() if ADVANCED_SETTINGS_AVAILABLE else 0,
        'brand_count': Brand.query.count() if ADVANCED_SETTINGS_AVAILABLE else 0,
        'supplier_count': Supplier.query.count(),
        'advanced_available': ADVANCED_SETTINGS_AVAILABLE
    }
    
    # Legacy Preiseinstellungen
    legacy_settings = {
        'price_factor_calculated': PriceCalculationSettings.get_setting('price_factor_calculated', 1.5),
        'price_factor_recommended': PriceCalculationSettings.get_setting('price_factor_recommended', 2.0)
    }
    
    # Erweiterte Einstellungen wenn verfügbar
    advanced_settings = {}
    if ADVANCED_SETTINGS_AVAILABLE:
        advanced_settings = {
            'tax_rates': TaxRate.query.filter_by(active=True).count(),
            'calculation_rules': PriceCalculationRule.query.filter_by(active=True).count(),
            'default_tax_rate': TaxRate.query.filter_by(is_default=True).first(),
            'default_calculation_rule': PriceCalculationRule.get_default_rule(),
            'import_settings_configured': ImportSettings.query.first() is not None
        }
    
    return render_template('settings/index.html',
                         settings_overview=settings_overview,
                         legacy_settings=legacy_settings,
                         advanced_settings=advanced_settings)

# ==================== BENUTZER-VERWALTUNG ====================

@settings_bp.route('/users')
@login_required
def users():
    """Benutzer-Verwaltung"""
    if not current_user.is_admin:
        flash('Nur Administratoren können Benutzer verwalten.', 'error')
        return redirect(url_for('settings.index'))
    
    users_list = User.query.order_by(User.username).all()
    return render_template('settings/users.html', users=users_list)

@settings_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
def new_user():
    """Neuen Benutzer erstellen"""
    if not current_user.is_admin:
        flash('Nur Administratoren können Benutzer erstellen.', 'error')
        return redirect(url_for('settings.index'))
    
    if request.method == 'POST':
        # Prüfe ob Username bereits existiert
        existing_user = User.query.filter_by(username=request.form.get('username')).first()
        if existing_user:
            flash('Benutzername bereits vergeben!', 'error')
            return render_template('settings/user_form.html', user=None)
        
        # Prüfe ob Email bereits existiert
        existing_email = User.query.filter_by(email=request.form.get('email')).first()
        if existing_email:
            flash('E-Mail-Adresse bereits vergeben!', 'error')
            return render_template('settings/user_form.html', user=None)
        
        # Erstelle neuen Benutzer
        user = User(
            username=request.form.get('username'),
            email=request.form.get('email'),
            is_admin=request.form.get('is_admin') == 'on',
            is_active=request.form.get('is_active', 'on') == 'on'
        )
        user.set_password(request.form.get('password'))
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'Benutzer {user.username} wurde erstellt!', 'success')
        return redirect(url_for('settings.users'))
    
    return render_template('settings/user_form.html', user=None)



# ==================== ARTIKEL-EINSTELLUNGEN ====================

@settings_bp.route('/articles')
@login_required
def articles():
    """Artikel-Einstellungen"""
    
    # Legacy Preiseinstellungen
    legacy_settings = {
        'price_factor_calculated': PriceCalculationSettings.get_setting('price_factor_calculated', 1.5),
        'price_factor_recommended': PriceCalculationSettings.get_setting('price_factor_recommended', 2.0)
    }
    
    # Statistiken
    stats = {
        'total_categories': ProductCategory.query.count() if ADVANCED_SETTINGS_AVAILABLE else 0,
        'active_categories': ProductCategory.query.filter_by(active=True).count() if ADVANCED_SETTINGS_AVAILABLE else 0,
        'total_brands': Brand.query.count() if ADVANCED_SETTINGS_AVAILABLE else 0,
        'active_brands': Brand.query.filter_by(active=True).count() if ADVANCED_SETTINGS_AVAILABLE else 0,
        'total_suppliers': Supplier.query.count(),
        'active_suppliers': Supplier.query.filter_by(active=True).count()
    }
    
    return render_template('settings/articles.html', 
                         legacy_settings=legacy_settings,
                         stats=stats,
                         advanced_available=ADVANCED_SETTINGS_AVAILABLE)

@settings_bp.route('/articles/pricing', methods=['GET', 'POST'])
@login_required
def articles_pricing():
    """Preis-Kalkulationseinstellungen"""
    
    if request.method == 'POST':
        # Legacy Einstellungen updaten
        factor_calculated = float(request.form.get('price_factor_calculated', 1.5))
        factor_recommended = float(request.form.get('price_factor_recommended', 2.0))
        
        PriceCalculationSettings.set_setting('price_factor_calculated', factor_calculated, 
                                            'Faktor für kalkulierte VK-Preise', current_user.username)
        PriceCalculationSettings.set_setting('price_factor_recommended', factor_recommended, 
                                            'Faktor für empfohlene VK-Preise', current_user.username)
        
        flash('Preiskalkulationseinstellungen wurden gespeichert!', 'success')
        return redirect(url_for('settings.articles'))
    
    # Aktuelle Einstellungen laden
    settings = {
        'price_factor_calculated': PriceCalculationSettings.get_setting('price_factor_calculated', 1.5),
        'price_factor_recommended': PriceCalculationSettings.get_setting('price_factor_recommended', 2.0)
    }
    
    return render_template('settings/articles_pricing.html', settings=settings)

# ==================== ERWEITERTE EINSTELLUNGEN ====================

@settings_bp.route('/advanced')
@login_required
def advanced():
    """Erweiterte Einstellungen (nur wenn verfügbar)"""
    if not ADVANCED_SETTINGS_AVAILABLE:
        flash('Erweiterte Einstellungen sind nicht verfügbar. Installiere die erweiterten Models.', 'warning')
        return redirect(url_for('settings.index'))
    
    # Sammle erweiterte Einstellungen
    tax_rates = TaxRate.query.order_by(TaxRate.rate.desc()).all()
    calculation_rules = PriceCalculationRule.query.order_by(PriceCalculationRule.priority).all()
    import_settings = ImportSettings.get_default_settings()
    
    stats = {
        'total_tax_rates': len(tax_rates),
        'active_tax_rates': len([t for t in tax_rates if t.active]),
        'default_tax_rate': next((t for t in tax_rates if t.is_default), None),
        'total_calculation_rules': len(calculation_rules),
        'active_calculation_rules': len([r for r in calculation_rules if r.active]),
        'import_configured': import_settings is not None
    }
    
    return render_template('settings/advanced.html',
                         tax_rates=tax_rates,
                         calculation_rules=calculation_rules,
                         import_settings=import_settings,
                         stats=stats)

# ==================== SYSTEM-EINSTELLUNGEN ====================

@settings_bp.route('/system')
@login_required
def system():
    """System-Einstellungen"""
    if not current_user.is_admin:
        flash('Nur Administratoren können System-Einstellungen einsehen.', 'error')
        return redirect(url_for('settings.index'))
    
    # System-Informationen
    import sys
    import platform
    
    system_info = {
        'python_version': sys.version,
        'platform': platform.platform(),
        'flask_debug': app.config.get('DEBUG', False) if 'app' in globals() else 'Unknown',
        'database_url': app.config.get('SQLALCHEMY_DATABASE_URI', 'Unknown') if 'app' in globals() else 'Unknown'
    }
    
    return render_template('settings/system.html', system_info=system_info)

# ==================== API ENDPOINTS ====================

@settings_bp.route('/api/test-calculation', methods=['POST'])
@login_required
def test_calculation():
    """API Endpoint zum Testen der Preiskalkulation"""
    try:
        purchase_price = float(request.json.get('purchase_price', 0))
        
        if not ADVANCED_SETTINGS_AVAILABLE:
            # Legacy Berechnung
            factor_calculated = PriceCalculationSettings.get_setting('price_factor_calculated', 1.5)
            factor_recommended = PriceCalculationSettings.get_setting('price_factor_recommended', 2.0)
            
            calculated = round(purchase_price * factor_calculated, 2)
            recommended = round(purchase_price * factor_recommended, 2)
            
            return jsonify({
                'success': True,
                'purchase_price': purchase_price,
                'calculated_net': calculated,
                'recommended_net': recommended,
                'calculated_gross': round(calculated * 1.19, 2),
                'recommended_gross': round(recommended * 1.19, 2),
                'tax_rate': 19.0,
                'rule_used': 'Legacy System'
            })
        else:
            # Erweiterte Berechnung
            rule_id = request.json.get('rule_id')
            if rule_id:
                rule = PriceCalculationRule.query.get(rule_id)
            else:
                rule = PriceCalculationRule.get_default_rule()
            
            if not rule:
                return jsonify({'success': False, 'error': 'Keine Kalkulationsregel gefunden'})
            
            calculated = rule.calculate_price(purchase_price, 'calculated')
            recommended = rule.calculate_price(purchase_price, 'recommended')
            
            tax_rate = rule.tax_rate.rate if rule.tax_rate else TaxRate.get_default_rate()
            tax_multiplier = 1 + (tax_rate / 100)
            
            return jsonify({
                'success': True,
                'purchase_price': purchase_price,
                'calculated_net': calculated,
                'recommended_net': recommended,
                'calculated_gross': round(calculated * tax_multiplier, 2),
                'recommended_gross': round(recommended * tax_multiplier, 2),
                'tax_rate': tax_rate,
                'rule_used': rule.name,
                'factors': {
                    'calculated': rule.factor_calculated,
                    'recommended': rule.factor_recommended
                }
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@settings_bp.route('/api/init-advanced', methods=['POST'])
@login_required
def init_advanced_settings():
    """Initialisiere erweiterte Einstellungen"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Nur Administratoren können das System initialisieren'})
    
    if not ADVANCED_SETTINGS_AVAILABLE:
        return jsonify({'success': False, 'error': 'Erweiterte Models nicht verfügbar'})
    
    try:
        # Standard MwSt-Sätze erstellen
        if not TaxRate.query.first():
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
        return jsonify({'success': True, 'message': 'Erweiterte Einstellungen wurden initialisiert'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# ==================== FEHLENDE BENUTZER-ROUTEN ====================
# Erstellt von Hans Hahn - Alle Rechte vorbehalten

@settings_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Benutzer bearbeiten"""
    if not current_user.is_admin:
        flash('Nur Administratoren können Benutzer bearbeiten.', 'error')
        return redirect(url_for('settings.index'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        # E-Mail aktualisieren
        new_email = request.form.get('email')
        if new_email != user.email:
            existing_email = User.query.filter_by(email=new_email).first()
            if existing_email and existing_email.id != user.id:
                flash('E-Mail-Adresse bereits vergeben!', 'error')
                return render_template('settings/user_form.html', user=user)
            user.email = new_email
        
        # Passwort aktualisieren (optional)
        new_password = request.form.get('password')
        if new_password:
            password_confirm = request.form.get('password_confirm')
            if new_password != password_confirm:
                flash('Passwörter stimmen nicht überein!', 'error')
                return render_template('settings/user_form.html', user=user)
            user.set_password(new_password)
        
        # Status aktualisieren
        user.is_active = request.form.get('is_active') == 'on'
        
        # Admin-Rechte (nicht für sich selbst)
        if user.id != current_user.id:
            user.is_admin = request.form.get('is_admin') == 'on'
        
        try:
            db.session.commit()
            flash(f'Benutzer {user.username} wurde erfolgreich aktualisiert!', 'success')
            return redirect(url_for('settings.users'))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Speichern: {str(e)}', 'error')
    
    return render_template('settings/user_form.html', user=user)

@settings_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    """Benutzer-Status umschalten"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Keine Berechtigung'})
    
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        return jsonify({'success': False, 'error': 'Sie können ihren eigenen Status nicht ändern'})
    
    try:
        user.is_active = request.json.get('active', not user.is_active)
        db.session.commit()
        
        status = 'aktiviert' if user.is_active else 'deaktiviert'
        return jsonify({'success': True, 'message': f'Benutzer {user.username} wurde {status}'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@settings_bp.route('/users/<int:user_id>/delete', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """Benutzer löschen"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Keine Berechtigung'})
    
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        return jsonify({'success': False, 'error': 'Sie können sich nicht selbst löschen'})
    
    try:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Benutzer {username} wurde gelöscht'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@settings_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
def reset_password(user_id):
    """Passwort zurücksetzen"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Keine Berechtigung'})
    
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        return jsonify({'success': False, 'error': 'Sie können ihr eigenes Passwort nicht zurücksetzen'})
    
    try:
        import secrets
        import string
        
        # Generiere sicheres Passwort
        characters = string.ascii_letters + string.digits + '!@#$%^&*'
        new_password = ''.join(secrets.choice(characters) for _ in range(12))
        
        user.set_password(new_password)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'new_password': new_password,
            'message': f'Neues Passwort für {user.username} generiert'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# ==================== KATEGORIEN ROUTEN ====================

@settings_bp.route('/categories')
@login_required
def categories():
    """Kategorien-Verwaltung"""
    if not current_user.is_admin:
        flash('Nur Administratoren können Kategorien verwalten.', 'error')
        return redirect(url_for('settings.index'))
    
    # Hole alle verwendeten Kategorien aus den Artikeln
    categories_query = db.session.query(
        Article.category,
        db.func.count(Article.id).label('article_count')
    ).filter(
        Article.category.isnot(None),
        Article.category != ''
    ).group_by(Article.category).order_by(Article.category).all()
    
    categories = []
    for cat_name, count in categories_query:
        categories.append({
            'name': cat_name,
            'article_count': count,
            'active': True  # Alle vorhandenen Kategorien sind aktiv
        })
    
    return render_template('settings/categories.html', categories=categories)

# ==================== SYSTEM-API ROUTEN ====================

@settings_bp.route('/api/system-info')
@login_required
def api_system_info():
    """System-Informationen API"""
    if not current_user.is_admin:
        return jsonify({'error': 'Keine Berechtigung'}), 403
    
    try:
        # Zähle Tabellen (vereinfacht)
        table_count = len(db.metadata.tables)
        
        return jsonify({
            'success': True,
            'table_count': table_count,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@settings_bp.route('/api/system-logs')
@login_required
def api_system_logs():
    """System-Logs API"""
    if not current_user.is_admin:
        return jsonify({'error': 'Keine Berechtigung'}), 403

    try:
        import os
        log_file = 'error_log.txt'

        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Nur die letzten 10 Zeilen
                recent_logs = lines[-10:] if len(lines) > 10 else lines
                return jsonify({
                    'success': True,
                    'logs': [line.strip() for line in recent_logs]
                })
        else:
            return jsonify({
                'success': True,
                'logs': ['Keine Log-Datei gefunden']
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== MARKEN-VERWALTUNG ====================

@settings_bp.route('/brands')
@login_required
def brands():
    """Marken-Verwaltung"""
    if not current_user.is_admin:
        flash('Nur Administratoren können Marken verwalten.', 'error')
        return redirect(url_for('settings.index'))

    brands_list = Brand.query.order_by(Brand.name).all()

    # Zähle Artikel pro Marke
    for brand in brands_list:
        brand.article_count = brand.articles.count()

    return render_template('settings/brands.html', brands=brands_list)

@settings_bp.route('/brands/new', methods=['GET', 'POST'])
@login_required
def new_brand():
    """Neue Marke erstellen"""
    if not current_user.is_admin:
        flash('Nur Administratoren können Marken erstellen.', 'error')
        return redirect(url_for('settings.index'))

    if request.method == 'POST':
        # Prüfe ob Name bereits existiert
        existing = Brand.query.filter_by(name=request.form.get('name')).first()
        if existing:
            flash('Eine Marke mit diesem Namen existiert bereits!', 'error')
            return render_template('settings/brand_form.html', brand=None)

        # Erstelle neue Marke
        brand = Brand(
            name=request.form.get('name'),
            description=request.form.get('description', ''),
            website=request.form.get('website', ''),
            logo_url=request.form.get('logo_url', ''),
            active=request.form.get('active', 'on') == 'on',
            created_by=current_user.username
        )

        db.session.add(brand)
        db.session.commit()

        flash(f'Marke {brand.name} wurde erstellt!', 'success')
        return redirect(url_for('settings.brands'))

    return render_template('settings/brand_form.html', brand=None)

@settings_bp.route('/brands/<int:brand_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_brand(brand_id):
    """Marke bearbeiten"""
    if not current_user.is_admin:
        flash('Nur Administratoren können Marken bearbeiten.', 'error')
        return redirect(url_for('settings.index'))

    brand = Brand.query.get_or_404(brand_id)

    if request.method == 'POST':
        # Prüfe ob Name bereits existiert (außer bei dieser Marke)
        existing = Brand.query.filter(
            Brand.name == request.form.get('name'),
            Brand.id != brand_id
        ).first()
        if existing:
            flash('Eine Marke mit diesem Namen existiert bereits!', 'error')
            return render_template('settings/brand_form.html', brand=brand)

        # Aktualisiere Marke
        brand.name = request.form.get('name')
        brand.description = request.form.get('description', '')
        brand.website = request.form.get('website', '')
        brand.logo_url = request.form.get('logo_url', '')
        brand.active = request.form.get('active', 'on') == 'on'
        brand.updated_at = datetime.utcnow()

        db.session.commit()

        flash(f'Marke {brand.name} wurde aktualisiert!', 'success')
        return redirect(url_for('settings.brands'))

    return render_template('settings/brand_form.html', brand=brand)

@settings_bp.route('/brands/<int:brand_id>/delete', methods=['POST'])
@login_required
def delete_brand(brand_id):
    """Marke löschen"""
    if not current_user.is_admin:
        flash('Nur Administratoren können Marken löschen.', 'error')
        return redirect(url_for('settings.index'))

    brand = Brand.query.get_or_404(brand_id)
    brand_name = brand.name

    # Prüfe ob Artikel diese Marke verwenden
    article_count = brand.articles.count()
    if article_count > 0:
        flash(f'Marke {brand_name} kann nicht gelöscht werden, da {article_count} Artikel diese Marke verwenden!', 'danger')
        return redirect(url_for('settings.brands'))

    db.session.delete(brand)
    db.session.commit()

    flash(f'Marke {brand_name} wurde gelöscht!', 'success')
    return redirect(url_for('settings.brands'))

@settings_bp.route('/brands/<int:brand_id>/toggle', methods=['POST'])
@login_required
def toggle_brand(brand_id):
    """Marke aktivieren/deaktivieren"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Keine Berechtigung'}), 403

    brand = Brand.query.get_or_404(brand_id)
    brand.active = not brand.active
    db.session.commit()

    return jsonify({
        'success': True,
        'active': brand.active,
        'message': f'Marke {brand.name} wurde {"aktiviert" if brand.active else "deaktiviert"}'
    })
