"""
Dashboard Layout API
Erstellt von Hans Hahn - Alle Rechte vorbehalten

API-Endpoints für:
- Dashboard-Layout speichern
- Dashboard-Layout laden
- Modul-Sichtbarkeit umschalten
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from src.models.models import db
from src.models.user_permissions import DashboardLayout, Module
from src.utils.permissions import has_module_permission

# Blueprint für Dashboard-API
dashboard_api_bp = Blueprint('dashboard_api', __name__, url_prefix='/api/dashboard')


@dashboard_api_bp.route('/layout', methods=['GET'])
@login_required
def get_layout():
    """Lädt das Dashboard-Layout des aktuellen Users"""
    layout = DashboardLayout.query.filter_by(user_id=current_user.id).first()
    
    if not layout:
        # Erstelle Default-Layout
        layout = DashboardLayout.create_default_layout(current_user.id)
        db.session.add(layout)
        db.session.commit()
    
    return jsonify({
        'success': True,
        'layout': layout.to_dict()
    })


@dashboard_api_bp.route('/layout', methods=['POST'])
@login_required
def save_layout():
    """
    Speichert das Dashboard-Layout des Users
    
    Erwartet JSON:
    {
        "modules": [
            {"module_id": 1, "order": 1, "visible": true, "size": "normal"},
            {"module_id": 2, "order": 2, "visible": false, "size": "normal"}
        ]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'modules' not in data:
            return jsonify({
                'success': False,
                'error': 'Ungültige Daten'
            }), 400
        
        # Hole oder erstelle Layout
        layout = DashboardLayout.query.filter_by(user_id=current_user.id).first()
        
        if not layout:
            layout = DashboardLayout(user_id=current_user.id)
            db.session.add(layout)
        
        # Validiere Module-IDs
        module_ids = [m['module_id'] for m in data['modules']]
        valid_modules = Module.query.filter(Module.id.in_(module_ids)).count()
        
        if valid_modules != len(module_ids):
            return jsonify({
                'success': False,
                'error': 'Ungültige Modul-IDs'
            }), 400
        
        # Aktualisiere Layout
        layout.layout_config = {
            'modules': data['modules'],
            'theme': data.get('theme', 'light'),
            'compact_mode': data.get('compact_mode', False)
        }
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Layout gespeichert',
            'layout': layout.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_api_bp.route('/module/<int:module_id>/toggle', methods=['POST'])
@login_required
def toggle_module_visibility(module_id):
    """Schaltet die Sichtbarkeit eines Moduls um"""
    try:
        # Prüfe ob User Berechtigung hat
        module = Module.query.get_or_404(module_id)
        
        # Hole Layout
        layout = DashboardLayout.query.filter_by(user_id=current_user.id).first()
        
        if not layout:
            layout = DashboardLayout.create_default_layout(current_user.id)
            db.session.add(layout)
        
        # Finde Modul in Config
        modules = layout.layout_config.get('modules', [])
        module_found = False
        
        for m in modules:
            if m['module_id'] == module_id:
                m['visible'] = not m.get('visible', True)
                module_found = True
                break
        
        # Wenn nicht gefunden, hinzufügen
        if not module_found:
            modules.append({
                'module_id': module_id,
                'order': len(modules) + 1,
                'visible': False,  # Toggle off
                'size': 'normal'
            })
        
        layout.layout_config['modules'] = modules
        db.session.commit()
        
        return jsonify({
            'success': True,
            'visible': any(m['module_id'] == module_id and m.get('visible', True) for m in modules)
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_api_bp.route('/reset', methods=['POST'])
@login_required
def reset_layout():
    """Setzt das Dashboard auf Standard zurück"""
    try:
        layout = DashboardLayout.query.filter_by(user_id=current_user.id).first()
        
        if layout:
            db.session.delete(layout)
        
        # Erstelle neues Default-Layout
        new_layout = DashboardLayout.create_default_layout(current_user.id)
        db.session.add(new_layout)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Dashboard zurückgesetzt',
            'layout': new_layout.to_dict()
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dashboard_api_bp.route('/modules/available', methods=['GET'])
@login_required
def get_available_modules():
    """Gibt alle verfügbaren Module für den User zurück"""
    from src.utils.permissions import get_user_modules

    modules = get_user_modules(current_user)

    return jsonify({
        'success': True,
        'modules': [m.to_dict() for m in modules]
    })


@dashboard_api_bp.route('/my-modules', methods=['GET'], endpoint='my_modules')
@login_required
def my_modules():
    """Zeigt die Modul-Verwaltungsseite des Users"""
    from flask import render_template
    from src.utils.permissions import get_user_modules

    # Hole alle verfügbaren Module für den User
    all_modules = get_user_modules(current_user)

    # Hole das Layout des Users
    layout = DashboardLayout.query.filter_by(user_id=current_user.id).first()

    if not layout:
        layout = DashboardLayout.create_default_layout(current_user.id)
        db.session.add(layout)
        db.session.commit()

    # Erstelle eine Map von Modul-ID zu Visibility
    layout_config = layout.layout_config or {}
    modules_config = layout_config.get('modules', [])
    visibility_map = {m['module_id']: m.get('visible', True) for m in modules_config}
    order_map = {m['module_id']: m.get('order', 999) for m in modules_config}

    # Erweitere Module mit Sichtbarkeit
    modules_with_visibility = []
    for module in all_modules:
        modules_with_visibility.append({
            'module': module,
            'visible': visibility_map.get(module.id, True),
            'order': order_map.get(module.id, 999)
        })

    # Sortiere nach Order
    modules_with_visibility.sort(key=lambda x: x['order'])

    return render_template('dashboard/my_modules.html',
                         modules=modules_with_visibility,
                         layout=layout)
