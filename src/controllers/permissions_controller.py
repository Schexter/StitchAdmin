"""
Permissions Management Controller
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Admin-Interface für:
- Berechtigungsverwaltung pro User
- Modul-Verwaltung
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from src.models.models import db, User
from src.models.user_permissions import Module, ModulePermission, DashboardLayout
from datetime import datetime

# Blueprint erstellen
permissions_bp = Blueprint('permissions', __name__, url_prefix='/admin/permissions')


@permissions_bp.route('/')
@login_required
def index():
    """Übersicht: Berechtigungsverwaltung"""
    if not current_user.is_admin:
        flash('Keine Berechtigung für diese Seite', 'danger')
        return redirect(url_for('dashboard'))
    
    users = User.query.order_by(User.username).all()
    modules = Module.query.order_by(Module.sort_order).all()
    
    return render_template('permissions/index.html',
                         users=users,
                         modules=modules)


@permissions_bp.route('/user/<int:user_id>')
@login_required
def user_permissions(user_id):
    """Berechtigungen eines Users anzeigen & bearbeiten"""
    if not current_user.is_admin:
        flash('Keine Berechtigung', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    modules = Module.query.filter_by(is_active=True).order_by(Module.sort_order).all()
    
    # Hole bestehende Berechtigungen
    permissions = {}
    for perm in user.module_permissions:
        permissions[perm.module_id] = perm
    
    return render_template('permissions/user_permissions.html',
                         user=user,
                         modules=modules,
                         permissions=permissions)


@permissions_bp.route('/user/<int:user_id>/update', methods=['POST'])
@login_required
def update_user_permissions(user_id):
    """Aktualisiert Berechtigungen eines Users"""
    if not current_user.is_admin:
        flash('Keine Berechtigung', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    modules = Module.query.filter_by(is_active=True).all()
    
    # Lösche alle bestehenden Berechtigungen
    ModulePermission.query.filter_by(user_id=user_id).delete()
    
    # Erstelle neue Berechtigungen basierend auf Formular
    for module in modules:
        # Prüfe ob Checkboxen aktiviert
        can_view = request.form.get(f'module_{module.id}_view') == 'on'
        can_create = request.form.get(f'module_{module.id}_create') == 'on'
        can_edit = request.form.get(f'module_{module.id}_edit') == 'on'
        can_delete = request.form.get(f'module_{module.id}_delete') == 'on'
        
        # Nur speichern wenn mindestens eine Berechtigung gesetzt
        if any([can_view, can_create, can_edit, can_delete]):
            permission = ModulePermission(
                user_id=user_id,
                module_id=module.id,
                can_view=can_view,
                can_create=can_create,
                can_edit=can_edit,
                can_delete=can_delete,
                granted_by=current_user.id,
                granted_at=datetime.utcnow()
            )
            db.session.add(permission)
    
    try:
        db.session.commit()
        flash(f'Berechtigungen für {user.username} aktualisiert', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Speichern: {str(e)}', 'danger')
    
    return redirect(url_for('permissions.user_permissions', user_id=user_id))


@permissions_bp.route('/modules')
@login_required
def modules():
    """Modul-Verwaltung"""
    if not current_user.is_admin:
        flash('Keine Berechtigung', 'danger')
        return redirect(url_for('dashboard'))
    
    all_modules = Module.query.order_by(Module.sort_order).all()
    
    return render_template('permissions/modules.html',
                         modules=all_modules)


@permissions_bp.route('/module/<int:module_id>/toggle', methods=['POST'])
@login_required
def toggle_module(module_id):
    """Aktiviert/Deaktiviert ein Modul"""
    if not current_user.is_admin:
        return jsonify({'error': 'Keine Berechtigung'}), 403
    
    module = Module.query.get_or_404(module_id)
    module.is_active = not module.is_active
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'is_active': module.is_active
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@permissions_bp.route('/module/<int:module_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_module(module_id):
    """Modul bearbeiten"""
    if not current_user.is_admin:
        flash('Keine Berechtigung', 'danger')
        return redirect(url_for('dashboard'))
    
    module = Module.query.get_or_404(module_id)
    
    if request.method == 'POST':
        module.display_name = request.form.get('display_name')
        module.description = request.form.get('description')
        module.icon = request.form.get('icon')
        module.color = request.form.get('color')
        module.requires_admin = request.form.get('requires_admin') == 'on'
        module.default_enabled = request.form.get('default_enabled') == 'on'
        module.sort_order = int(request.form.get('sort_order', 0))
        
        try:
            db.session.commit()
            flash('Modul aktualisiert', 'success')
            return redirect(url_for('permissions.modules'))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler: {str(e)}', 'danger')
    
    return render_template('permissions/edit_module.html', module=module)


@permissions_bp.route('/quick-assign', methods=['POST'])
@login_required
def quick_assign():
    """Schnell-Zuweisung: Alle Module für einen User"""
    if not current_user.is_admin:
        return jsonify({'error': 'Keine Berechtigung'}), 403
    
    user_id = request.json.get('user_id')
    level = request.json.get('level', 'view')  # view, edit, full
    
    user = User.query.get_or_404(user_id)
    modules = Module.query.filter_by(is_active=True).all()
    
    # Lösche bestehende
    ModulePermission.query.filter_by(user_id=user_id).delete()
    
    # Erstelle neue basierend auf Level
    for module in modules:
        if module.requires_admin and not user.is_admin:
            continue
        
        if level == 'view':
            can_view, can_create, can_edit, can_delete = True, False, False, False
        elif level == 'edit':
            can_view, can_create, can_edit, can_delete = True, True, True, False
        else:  # full
            can_view, can_create, can_edit, can_delete = True, True, True, True
        
        permission = ModulePermission(
            user_id=user_id,
            module_id=module.id,
            can_view=can_view,
            can_create=can_create,
            can_edit=can_edit,
            can_delete=can_delete,
            granted_by=current_user.id
        )
        db.session.add(permission)
    
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
