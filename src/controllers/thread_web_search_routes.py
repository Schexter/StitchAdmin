# GARN-WEB-SUCHSYSTEM CONTROLLER-ERWEITERUNG
# Erstellt von Hans Hahn - Alle Rechte vorbehalten
# Datum: 08.07.2025

# Diese Routen müssen zum thread_controller_db.py hinzugefügt werden:

@thread_bp.route('/web-search')
@login_required
def web_search():
    """Garn-Web-Suchseite anzeigen"""
    return render_template('threads/web_search.html')


@thread_bp.route('/search-web', methods=['POST'])
@login_required
def search_web():
    """Führt Web-Suche nach Garnen durch"""
    manufacturer = request.form.get('manufacturer', '').strip()
    color_number = request.form.get('color_number', '').strip()
    color_name = request.form.get('color_name', '').strip()
    
    if not manufacturer or not color_number:
        return jsonify({
            'success': False,
            'error': 'Hersteller und Farbnummer sind erforderlich'
        })
    
    try:
        from src.services.thread_web_search_service import search_thread_web
        
        # Web-Suche durchführen
        result = search_thread_web(manufacturer, color_number, color_name or None)
        
        if result['success']:
            # Aktivität protokollieren
            log_activity(
                'thread_web_search',
                f'Web-Suche durchgeführt: {manufacturer} {color_number} - {len(result["search_results"])} Ergebnisse'
            )
        
        return jsonify(result)
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'Garn-Web-Suchsystem nicht verfügbar. Führen Sie INSTALL_WEBSHOP_AUTOMATION.bat aus.'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@thread_bp.route('/<thread_id>/search-web')
@login_required
def search_existing_thread_web(thread_id):
    """Sucht ein existierendes Garn im Web"""
    thread = Thread.query.get_or_404(thread_id)
    
    try:
        from src.services.thread_web_search_service import search_thread_web
        
        # Web-Suche für existierendes Garn
        result = search_thread_web(
            thread.manufacturer,
            thread.color_number,
            thread.color_name_de
        )
        
        if result['success']:
            # Aktivität protokollieren
            log_activity(
                'thread_web_search_existing',
                f'Web-Suche für existierendes Garn: {thread.manufacturer} {thread.color_number}'
            )
            
            return render_template('threads/web_search_result.html',
                                 thread=thread,
                                 search_result=result)
        else:
            flash(f'Web-Suche fehlgeschlagen: {result["error"]}', 'error')
            return redirect(url_for('thread.show', thread_id=thread_id))
            
    except ImportError:
        flash('Garn-Web-Suchsystem nicht verfügbar. Führen Sie INSTALL_WEBSHOP_AUTOMATION.bat aus.', 'warning')
        return redirect(url_for('thread.show', thread_id=thread_id))
    except Exception as e:
        flash(f'Fehler bei Web-Suche: {str(e)}', 'error')
        return redirect(url_for('thread.show', thread_id=thread_id))


@thread_bp.route('/low-stock-search')
@login_required
def low_stock_search():
    """Zeigt Nachbestellvorschläge für Garne mit niedrigem Lagerbestand"""
    try:
        from src.services.thread_web_search_service import search_low_stock_threads
        
        # Suche nach Garnen mit niedrigem Lagerbestand
        suggestions = search_low_stock_threads()
        
        # Aktivität protokollieren
        log_activity(
            'thread_low_stock_search',
            f'Nachbestellvorschläge generiert: {len(suggestions)} Garne'
        )
        
        return render_template('threads/low_stock_search.html',
                             suggestions=suggestions)
        
    except ImportError:
        flash('Garn-Web-Suchsystem nicht verfügbar. Führen Sie INSTALL_WEBSHOP_AUTOMATION.bat aus.', 'warning')
        return redirect(url_for('thread.index'))
    except Exception as e:
        flash(f'Fehler bei Nachbestellvorschlägen: {str(e)}', 'error')
        return redirect(url_for('thread.index'))


@thread_bp.route('/price-comparison/<manufacturer>/<color_number>')
@login_required
def price_comparison(manufacturer, color_number):
    """Zeigt Preisvergleich für ein Garn"""
    try:
        from src.services.thread_web_search_service import ThreadWebSearchService
        
        search_service = ThreadWebSearchService()
        price_comparison = search_service.get_price_comparison(manufacturer, color_number)
        
        return jsonify(price_comparison)
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'Garn-Web-Suchsystem nicht verfügbar'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@thread_bp.route('/manufacturers')
@login_required
def get_manufacturers():
    """Gibt verfügbare Garnhersteller zurück"""
    try:
        from src.services.thread_web_search_service import ThreadWebSearchService
        
        search_service = ThreadWebSearchService()
        manufacturers = list(search_service.thread_manufacturers.keys())
        
        return jsonify({
            'success': True,
            'manufacturers': manufacturers
        })
        
    except ImportError:
        return jsonify({
            'success': False,
            'error': 'Garn-Web-Suchsystem nicht verfügbar'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@thread_bp.route('/search-suggestions')
@login_required
def search_suggestions():
    """Gibt Suchvorschläge basierend auf Lagerbestand zurück"""
    # Hole Garne mit niedrigem Lagerbestand
    low_stock_threads = ThreadStock.query.join(Thread).filter(
        ThreadStock.quantity <= ThreadStock.min_stock,
        Thread.active == True
    ).limit(10).all()
    
    suggestions = []
    for stock in low_stock_threads:
        thread = stock.thread
        suggestions.append({
            'id': thread.id,
            'manufacturer': thread.manufacturer,
            'color_number': thread.color_number,
            'color_name': thread.color_name_de,
            'current_stock': stock.quantity,
            'min_stock': stock.min_stock,
            'urgency': 'high' if stock.quantity == 0 else 'medium'
        })
    
    return jsonify({
        'success': True,
        'suggestions': suggestions
    })


@thread_bp.route('/auto-search-all-low-stock', methods=['POST'])
@login_required
def auto_search_all_low_stock():
    """Startet automatische Suche für alle Garne mit niedrigem Lagerbestand"""
    try:
        from src.services.thread_web_search_service import search_low_stock_threads
        
        # Starte Background-Task (vereinfacht)
        suggestions = search_low_stock_threads()
        
        flash(f'Automatische Suche abgeschlossen. {len(suggestions)} Nachbestellvorschläge gefunden.', 'success')
        
        return redirect(url_for('thread.low_stock_search'))
        
    except ImportError:
        flash('Garn-Web-Suchsystem nicht verfügbar. Führen Sie INSTALL_WEBSHOP_AUTOMATION.bat aus.', 'warning')
        return redirect(url_for('thread.index'))
    except Exception as e:
        flash(f'Fehler bei automatischer Suche: {str(e)}', 'error')
        return redirect(url_for('thread.index'))
