# WEBSHOP AUTOMATION CONTROLLER ERWEITERUNG
# Erstellt von Hans Hahn - Alle Rechte vorbehalten
# Datum: 08.07.2025

# Diese Routen müssen zum supplier_controller_db.py hinzugefügt werden:

@supplier_bp.route('/<supplier_id>/webshop/<order_id>')
@login_required
def open_webshop_for_order(supplier_id, order_id):
    """Öffnet Webshop mit automatischem Warenkorb-Management"""
    supplier = Supplier.query.get_or_404(supplier_id)
    order = SupplierOrder.query.get_or_404(order_id)
    
    # Prüfe Berechtigungen
    if not current_user.is_admin and order.created_by != current_user.username:
        flash('Keine Berechtigung für diese Bestellung', 'error')
        return redirect(url_for('suppliers.show', supplier_id=supplier_id))
    
    # Webshop-URL prüfen
    if not supplier.webshop_url:
        flash('Kein Webshop für diesen Lieferanten konfiguriert', 'warning')
        return redirect(url_for('suppliers.show', supplier_id=supplier_id))
    
    # Bestellpositionen vorbereiten
    order_items = order.get_items()
    
    # Einfache Weiterleitung zur Webshop-URL (ohne Automation)
    if not request.args.get('automate'):
        return redirect(supplier.webshop_url)
    
    # Automation starten (falls aktiviert)
    try:
        from src.services.webshop_automation_service import create_automation_session
        
        # Passwort entschlüsseln
        password = None
        if supplier.webshop_password_encrypted:
            password = decrypt_password(supplier.webshop_password_encrypted)
        
        supplier_data = {
            'webshop_url': supplier.webshop_url,
            'webshop_username': supplier.webshop_username,
            'webshop_password': password,
            'webshop_type': supplier.webshop_type or 'generic'
        }
        
        # Automation starten (nicht-headless für Benutzerinteraktion)
        result = create_automation_session(supplier_data, order_items, headless=False)
        
        if result['success']:
            flash(f"Webshop-Automation gestartet! {result['search_results']['total_added']} Artikel hinzugefügt.", 'success')
            
            # Protokolliere Aktivität
            activity = ActivityLog(
                username=current_user.username,
                action='webshop_automation_started',
                details=f'Automation für {supplier.name} gestartet - {len(order_items)} Artikel',
                ip_address=request.remote_addr
            )
            db.session.add(activity)
            db.session.commit()
            
            # Zeige Ergebnisse
            return render_template('suppliers/webshop_automation_result.html',
                                 supplier=supplier,
                                 order=order,
                                 automation_result=result)
        else:
            flash(f"Webshop-Automation fehlgeschlagen: {result.get('error', 'Unbekannter Fehler')}", 'error')
            return redirect(supplier.webshop_url)
            
    except ImportError:
        flash('Webshop-Automation nicht verfügbar. Selenium nicht installiert.', 'warning')
        return redirect(supplier.webshop_url)
    except Exception as e:
        flash(f'Fehler bei Webshop-Automation: {str(e)}', 'error')
        return redirect(supplier.webshop_url)


@supplier_bp.route('/<supplier_id>/test-webshop')
@login_required
def test_webshop_connection(supplier_id):
    """Testet die Webshop-Verbindung und Login"""
    supplier = Supplier.query.get_or_404(supplier_id)
    
    if not supplier.webshop_url:
        return jsonify({
            'success': False,
            'error': 'Keine Webshop-URL konfiguriert'
        })
    
    try:
        from src.services.webshop_automation_service import WebshopAutomationService
        
        automation = WebshopAutomationService(headless=True, timeout=10)
        
        if not automation.setup_driver():
            return jsonify({
                'success': False,
                'error': 'Chrome-Driver konnte nicht gestartet werden'
            })
        
        # Teste URL-Erreichbarkeit
        automation.driver.get(supplier.webshop_url)
        time.sleep(2)
        
        result = {
            'success': True,
            'url_reachable': True,
            'page_title': automation.driver.title,
            'current_url': automation.driver.current_url
        }
        
        # Teste Login falls Credentials vorhanden
        if supplier.webshop_username and supplier.webshop_password_encrypted:
            password = decrypt_password(supplier.webshop_password_encrypted)
            
            login_success = automation.login_to_webshop(
                supplier.webshop_url,
                supplier.webshop_username,
                password,
                supplier.webshop_type or 'generic'
            )
            
            result['login_tested'] = True
            result['login_success'] = login_success
        else:
            result['login_tested'] = False
            result['login_success'] = None
        
        automation.close_driver()
        return jsonify(result)
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'Selenium nicht installiert'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@supplier_bp.route('/automation-status')
@login_required
def automation_status():
    """Gibt den Status der Webshop-Automation zurück"""
    try:
        import selenium
        selenium_available = True
        selenium_version = selenium.__version__
    except ImportError:
        selenium_available = False
        selenium_version = None
    
    try:
        import chromedriver_autoinstaller
        chromedriver_available = True
    except ImportError:
        chromedriver_available = False
    
    return jsonify({
        'selenium_available': selenium_available,
        'selenium_version': selenium_version,
        'chromedriver_available': chromedriver_available,
        'automation_ready': selenium_available and chromedriver_available
    })
