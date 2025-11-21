"""
EINFACHER Design-Workflow Controller
Löst die spezifischen Probleme wie besprochen
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from flask import Blueprint, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
import os

from src.utils.design_upload import (
    save_design_file, 
    save_link, 
    get_link, 
    should_show_graphics_manager,
    needs_graphics_manager
)

# Blueprint
design_workflow_bp = Blueprint('design_workflow', __name__, url_prefix='/orders')

@design_workflow_bp.route('/<order_id>/design/upload', methods=['POST'])
def upload_design_file(order_id):
    """Design-Datei hochladen - NUR PFAD SPEICHERN"""
    try:
        from src.models.models import Order, db
        
        order = Order.query.get_or_404(order_id)
        
        if 'design_file' not in request.files:
            flash('Keine Datei ausgewählt!', 'danger')
            return redirect(url_for('orders.show', order_id=order_id))
        
        file = request.files['design_file']
        
        # Datei speichern - NUR PFAD
        result = save_design_file(file, order_id)
        
        if result['success']:
            # NUR PFAD SPEICHERN - GRÖSSE EGAL
            order.design_file_path = result['storage_path']
            
            # Analyse-Daten speichern falls vorhanden
            if result.get('analysis'):
                import json
                order.file_analysis = json.dumps(result['analysis'])
            
            # Status aktualisieren
            if order.design_status == 'none':
                order.design_status = 'customer_provided'
            
            order.updated_at = datetime.now()
            order.updated_by = session.get('username')
            
            db.session.commit()
            flash('Design-Datei erfolgreich hochgeladen!', 'success')
        else:
            flash(f'Fehler: {result["error"]}', 'danger')
        
        return redirect(url_for('orders.show', order_id=order_id))
        
    except Exception as e:
        flash(f'Fehler beim Upload: {str(e)}', 'danger')
        return redirect(url_for('orders.show', order_id=order_id))

@design_workflow_bp.route('/<order_id>/design/link', methods=['POST'])
def save_design_link(order_id):
    """Design-Link speichern - NUR PFAD"""
    try:
        from src.models.models import Order, db
        
        order = Order.query.get_or_404(order_id)
        
        url = request.form.get('design_url', '').strip()
        if not url:
            flash('Keine URL angegeben!', 'danger')
            return redirect(url_for('orders.show', order_id=order_id))
        
        # Link speichern - NUR PFAD
        result = save_link(order_id, url)
        
        if result['success']:
            # NUR PFAD SPEICHERN
            order.design_file_path = result['storage_path']
            
            # Status aktualisieren
            if order.design_status == 'none':
                order.design_status = 'customer_provided'
            
            order.updated_at = datetime.now()
            order.updated_by = session.get('username')
            
            db.session.commit()
            flash('Design-Link erfolgreich gespeichert!', 'success')
        else:
            flash(f'Fehler: {result["error"]}', 'danger')
        
        return redirect(url_for('orders.show', order_id=order_id))
        
    except Exception as e:
        flash(f'Fehler beim Link speichern: {str(e)}', 'danger')
        return redirect(url_for('orders.show', order_id=order_id))

@design_workflow_bp.route('/<order_id>/design/graphics_manager_check', methods=['POST'])
def graphics_manager_check(order_id):
    """
    Prüft ob Grafikmanager benötigt wird
    WICHTIG: Vorher abfragen wie gewünscht
    """
    try:
        action = request.form.get('action')
        
        if action == 'check_link':
            # Prüfe ob Link vorhanden
            link = get_link(order_id)
            if link:
                # Link da -> Frage ob bearbeitet werden soll
                return jsonify({
                    'has_link': True,
                    'link': link,
                    'message': 'Link vorhanden. Soll bearbeitet werden?'
                })
            else:
                # Kein Link -> Grafikmanager anzeigen
                return jsonify({
                    'has_link': False,
                    'show_graphics_manager': True,
                    'message': 'Kein Link vorhanden. Grafikmanager verfügbar.'
                })
        
        elif action == 'edit_link':
            # Benutzer will Link bearbeiten
            return jsonify({
                'redirect': url_for('design_workflow.edit_link', order_id=order_id)
            })
        
        elif action == 'use_graphics_manager':
            # Benutzer will Grafikmanager verwenden
            return jsonify({
                'redirect': url_for('design_workflow.graphics_manager', order_id=order_id)
            })
        
    except Exception as e:
        return jsonify({'error': str(e)})

@design_workflow_bp.route('/<order_id>/design/edit_link')
def edit_link(order_id):
    """Link bearbeiten"""
    try:
        from src.models.models import Order
        
        order = Order.query.get_or_404(order_id)
        link = get_link(order_id)
        
        return f"""
        <h3>Link bearbeiten - Bestellung {order_id}</h3>
        <form method="POST" action="{url_for('design_workflow.save_design_link', order_id=order_id)}">
            <input type="url" name="design_url" value="{link or ''}" required>
            <button type="submit">Speichern</button>
        </form>
        <a href="{url_for('orders.show', order_id=order_id)}">Zurück</a>
        """
    except Exception as e:
        flash(f'Fehler: {str(e)}', 'danger')
        return redirect(url_for('orders.show', order_id=order_id))

@design_workflow_bp.route('/<order_id>/design/graphics_manager')
def graphics_manager(order_id):
    """Grafikmanager - nur wenn KEIN Link da ist"""
    try:
        from src.models.models import Order
        
        order = Order.query.get_or_404(order_id)
        
        # Prüfe ob Link vorhanden
        if not should_show_graphics_manager(order_id):
            flash('Grafikmanager nicht verfügbar - Link vorhanden!', 'info')
            return redirect(url_for('orders.show', order_id=order_id))
        
        return f"""
        <h3>Grafikmanager - Bestellung {order_id}</h3>
        <p>Hier kann das Design bearbeitet werden.</p>
        <a href="{url_for('orders.show', order_id=order_id)}">Zurück</a>
        """
    except Exception as e:
        flash(f'Fehler: {str(e)}', 'danger')
        return redirect(url_for('orders.show', order_id=order_id))

# Template-Funktionen
def register_template_helpers(app):
    """Registriert Template-Hilfsfunktionen"""
    
    @app.template_filter('is_design_link')
    def is_design_link(design_path):
        """Prüft ob es ein Link ist"""
        return design_path and design_path.startswith('link:')
    
    @app.template_filter('extract_link_url')
    def extract_link_url(design_path):
        """Extrahiert URL aus Link"""
        if design_path and design_path.startswith('link:'):
            return design_path[5:]
        return design_path
    
    @app.template_filter('show_graphics_manager')
    def show_graphics_manager(order_id):
        """Bestimmt ob Grafikmanager angezeigt werden soll"""
        return should_show_graphics_manager(order_id)

# Blueprint registrieren
def register_design_workflow_blueprint(app):
    """Registriert Blueprint"""
    app.register_blueprint(design_workflow_bp)
    register_template_helpers(app)
    print("[OK] Einfacher Design-Workflow Blueprint registriert")
