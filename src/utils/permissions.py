"""
Permission Helper Functions & Decorators
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Hilfsfunktionen für:
- Berechtigungsprüfung
- Route-Decorators
- Template-Helper
"""

from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user


def has_module_permission(user, module_name, action='view'):
    """
    Prüft ob User Berechtigung für ein Modul hat
    
    Args:
        user: User-Objekt
        module_name: Name des Moduls (z.B. 'crm', 'production')
        action: Gewünschte Aktion ('view', 'create', 'edit', 'delete')
    
    Returns:
        bool: True wenn User Berechtigung hat, sonst False
    
    Beispiel:
        if has_module_permission(current_user, 'crm', 'edit'):
            # User darf Kunden bearbeiten
    """
    from src.models.user_permissions import Module, ModulePermission
    
    # Admin hat immer alle Rechte
    if user.is_admin:
        return True
    
    # Modul laden
    module = Module.query.filter_by(name=module_name, is_active=True).first()
    if not module:
        return False
    
    # Wenn Modul nur für Admins → Zugriff verweigern
    if module.requires_admin and not user.is_admin:
        return False
    
    # Berechtigung prüfen
    permission = ModulePermission.query.filter_by(
        user_id=user.id,
        module_id=module.id
    ).first()
    
    # Wenn keine explizite Berechtigung vorhanden
    if not permission:
        # Nutze Default-Einstellung des Moduls
        if action == 'view':
            return module.default_enabled
        else:
            return False  # Create/Edit/Delete standardmäßig nicht erlaubt
    
    # Prüfe je nach Action
    if action == 'view':
        return permission.can_view
    elif action == 'create':
        return permission.can_create
    elif action == 'edit':
        return permission.can_edit
    elif action == 'delete':
        return permission.can_delete
    
    return False


def get_user_modules(user):
    """
    Gibt alle Module zurück, auf die der User Zugriff hat
    
    Args:
        user: User-Objekt
    
    Returns:
        list: Liste von Module-Objekten mit Berechtigung
    
    Beispiel:
        modules = get_user_modules(current_user)
        for module in modules:
            print(f"User kann {module.display_name} nutzen")
    """
    from src.models.user_permissions import Module, ModulePermission
    
    # Admin sieht alle aktiven Module
    if user.is_admin:
        return Module.query.filter_by(is_active=True).order_by(Module.sort_order).all()
    
    # Normale User: Nur Module mit View-Berechtigung
    modules = []
    
    # Hole alle Berechtigungen des Users
    permissions = ModulePermission.query.filter_by(
        user_id=user.id,
        can_view=True
    ).all()
    
    permission_module_ids = [p.module_id for p in permissions]
    
    # Hole auch Module mit default_enabled=True (wenn keine explizite Berechtigung)
    all_modules = Module.query.filter_by(is_active=True).order_by(Module.sort_order).all()
    
    for module in all_modules:
        # Skip Admin-Only Module
        if module.requires_admin and not user.is_admin:
            continue
        
        # Modul hat explizite Berechtigung
        if module.id in permission_module_ids:
            modules.append(module)
        # Oder Modul ist default enabled und keine explizite Berechtigung vorhanden
        elif module.default_enabled and module.id not in [p.module_id for p in ModulePermission.query.filter_by(user_id=user.id).all()]:
            modules.append(module)
    
    return modules


def get_user_dashboard_modules(user, include_hidden=False):
    """
    Gibt Module für Dashboard zurück, sortiert nach User-Layout

    Args:
        user: User-Objekt
        include_hidden: Wenn True, auch ausgeblendete Module zurückgeben

    Returns:
        list: Liste von (module, visible, order) Tupeln
        Wenn include_hidden=False: Nur sichtbare Module
    """
    from src.models.user_permissions import DashboardLayout

    # Hole User-Layout
    layout = DashboardLayout.query.filter_by(user_id=user.id).first()

    # Hole verfügbare Module
    available_modules = get_user_modules(user)

    if not layout or not layout.layout_config.get('modules'):
        # Kein Layout → Standard-Reihenfolge (alle sichtbar)
        return [(m, True, idx) for idx, m in enumerate(available_modules)]

    # Layout vorhanden → sortiere nach User-Präferenzen
    result = []
    module_config = {mc['module_id']: mc for mc in layout.layout_config['modules']}

    for module in available_modules:
        config = module_config.get(module.id, {})
        visible = config.get('visible', True)
        order = config.get('order', 999)

        # Nur sichtbare Module hinzufügen (außer include_hidden ist True)
        if include_hidden or visible:
            result.append((module, visible, order))

    # Sortiere nach Order
    result.sort(key=lambda x: x[2])

    return result


def module_required(module_name, action='view', redirect_to='dashboard'):
    """
    Decorator für Routen: Prüft Modul-Berechtigung
    
    Args:
        module_name: Name des Moduls
        action: Erforderliche Aktion ('view', 'create', 'edit', 'delete')
        redirect_to: Wohin umleiten bei fehlender Berechtigung
    
    Beispiel:
        @app.route('/customers')
        @login_required
        @module_required('crm', 'view')
        def customer_index():
            return render_template('customers/index.html')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Bitte melden Sie sich an.', 'warning')
                return redirect(url_for('auth.login'))
            
            if not has_module_permission(current_user, module_name, action):
                flash(f'Keine Berechtigung für dieses Modul.', 'danger')
                return redirect(url_for(redirect_to))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def module_required_or_404(module_name, action='view'):
    """
    Decorator: Gibt 404 bei fehlender Berechtigung (für APIs)
    
    Beispiel:
        @app.route('/api/customers')
        @login_required
        @module_required_or_404('crm', 'view')
        def api_customers():
            return jsonify(customers)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)  # Unauthorized
            
            if not has_module_permission(current_user, module_name, action):
                abort(403)  # Forbidden
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Template-Helper registrieren (in app.py einbinden)
def register_permission_helpers(app):
    """
    Registriert Permission-Helper für Templates
    
    In app.py aufrufen:
        from src.utils.permissions import register_permission_helpers
        register_permission_helpers(app)
    
    Dann in Templates verfügbar:
        {% if has_permission('crm', 'edit') %}
            <button>Bearbeiten</button>
        {% endif %}
    """
    @app.context_processor
    def inject_permissions():
        def check_permission(module_name, action='view'):
            if not current_user.is_authenticated:
                return False
            return has_module_permission(current_user, module_name, action)
        
        def get_modules():
            if not current_user.is_authenticated:
                return []
            return get_user_modules(current_user)
        
        def get_dashboard_modules():
            if not current_user.is_authenticated:
                return []
            return get_user_dashboard_modules(current_user)
        
        return dict(
            has_permission=check_permission,
            get_user_modules=get_modules,
            get_dashboard_modules=get_dashboard_modules
        )
