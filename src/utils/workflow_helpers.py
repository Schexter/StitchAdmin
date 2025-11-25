# -*- coding: utf-8 -*-
"""
Workflow Helper Functions
=========================
Helper-Funktionen für automatische Workflow-Übergänge

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

import json
from datetime import datetime, date
from src.models import db, PackingList, DeliveryNote, PostEntry
from src.models.company_settings import CompanySettings
from src.utils.pdf_workflow_helpers import generate_packing_list_pdf, generate_delivery_note_pdf
import logging

logger = logging.getLogger(__name__)


def create_packing_list_from_production(production, order=None):
    """
    Erstellt Packliste automatisch nach Produktionsabschluss

    Args:
        production: Production Model-Instanz
        order: Order Model-Instanz (optional, falls nicht via production.order verfügbar)

    Returns:
        PackingList: Erstellte Packliste
    """
    from src.models.models import Order

    # Order holen
    if not order:
        order = Order.query.get(production.order_id) if hasattr(production, 'order_id') else None

    if not order:
        raise ValueError("Kein Auftrag gefunden für Produktion")

    # Packlisten-Nummer generieren
    packing_list_number = PackingList.generate_packing_list_number()

    # Artikel aus Auftrag sammeln
    items = []
    if order.items:
        for order_item in order.items:
            items.append({
                'article_id': order_item.article_id if hasattr(order_item, 'article_id') else None,
                'name': order_item.article_name if hasattr(order_item, 'article_name') else str(order_item),
                'quantity': order_item.quantity if hasattr(order_item, 'quantity') else 1,
                'ean': order_item.ean if hasattr(order_item, 'ean') else '',
                'sku': order_item.sku if hasattr(order_item, 'sku') else ''
            })

    # Packliste erstellen
    packing_list = PackingList(
        packing_list_number=packing_list_number,
        order_id=order.id if order else None,
        production_id=production.id if hasattr(production, 'id') else None,
        customer_id=order.customer_id if order else None,
        status='ready',  # Bereit zur Verpackung
        items=json.dumps(items, ensure_ascii=False) if items else None,
        customer_notes=order.customer_notes if order and hasattr(order, 'customer_notes') else None,
        created_by=production.completed_by if hasattr(production, 'completed_by') else None
    )

    db.session.add(packing_list)
    db.session.flush()  # Um ID zu bekommen

    logger.info(f"Packliste {packing_list_number} erstellt für Auftrag {order.order_number if order else 'unknown'}")

    # PDF generieren
    try:
        pdf_path = generate_packing_list_pdf(packing_list, save_to_disk=True)
        packing_list.pdf_path = pdf_path
        logger.info(f"PDF für Packliste {packing_list_number} erstellt: {pdf_path}")
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Packlisten-PDFs: {e}")

    return packing_list


def create_post_entry_from_packing_list(packing_list):
    """
    Erstellt PostEntry (Postbuch-Eintrag) aus Packliste

    Args:
        packing_list: PackingList Model-Instanz

    Returns:
        PostEntry: Erstellter Postbuch-Eintrag
    """
    # PostEntry-Nummer generieren
    year = datetime.now().year
    prefix = f"POST-{year}-"

    last_entry = PostEntry.query.filter(
        PostEntry.entry_number.like(f"{prefix}%")
    ).order_by(PostEntry.id.desc()).first()

    if last_entry:
        try:
            last_num = int(last_entry.entry_number.split('-')[-1])
            new_num = last_num + 1
        except (ValueError, IndexError):
            new_num = 1
    else:
        new_num = 1

    entry_number = f"{prefix}{new_num:06d}"

    # Empfänger (Kunde)
    customer = packing_list.customer
    recipient_name = ''
    recipient_address = ''

    if customer:
        if customer.company_name:
            recipient_name = customer.company_name
        else:
            recipient_name = f"{customer.first_name or ''} {customer.last_name or ''}".strip()

        recipient_address = f"{customer.street or ''}\n{customer.postal_code or ''} {customer.city or ''}".strip()

    # Absender (Firma)
    company_settings = CompanySettings.get_settings()
    sender_name = company_settings.company_name if company_settings else 'StitchAdmin'
    sender_address = ''
    if company_settings:
        sender_address = f"{company_settings.street or ''}\n{company_settings.postal_code or ''} {company_settings.city or ''}".strip()

    # PostEntry erstellen
    post_entry = PostEntry(
        entry_number=entry_number,
        entry_date=datetime.utcnow(),
        direction='outbound',  # Ausgehend
        type='paket',
        sender=sender_name,
        sender_address=sender_address,
        recipient=recipient_name,
        recipient_address=recipient_address,
        customer_id=packing_list.customer_id,
        order_id=packing_list.order_id,
        status='open',  # Noch nicht versendet
        packing_list_id=packing_list.id,
        is_auto_created=True
    )

    db.session.add(post_entry)
    db.session.flush()

    logger.info(f"PostEntry {entry_number} erstellt für Packliste {packing_list.packing_list_number}")

    return post_entry


def create_delivery_note_from_packing_list(packing_list):
    """
    Erstellt Lieferschein aus Packliste

    Args:
        packing_list: PackingList Model-Instanz

    Returns:
        DeliveryNote: Erstellter Lieferschein
    """
    # Lieferschein-Nummer generieren
    delivery_note_number = DeliveryNote.generate_delivery_note_number()

    # Items aus Packliste übernehmen
    items = packing_list.get_items_list()

    # Lieferschein erstellen
    delivery_note = DeliveryNote(
        delivery_note_number=delivery_note_number,
        order_id=packing_list.order_id,
        packing_list_id=packing_list.id,
        customer_id=packing_list.customer_id,
        post_entry_id=packing_list.post_entry_id,
        delivery_date=date.today(),
        items=json.dumps(items, ensure_ascii=False) if items else None,
        delivery_method='shipping',  # Standard: Versand
        status='ready',
        created_by=packing_list.packed_by
    )

    db.session.add(delivery_note)
    db.session.flush()

    logger.info(f"Lieferschein {delivery_note_number} erstellt für Packliste {packing_list.packing_list_number}")

    # PDF generieren
    try:
        pdf_path = generate_delivery_note_pdf(delivery_note, save_to_disk=True)
        delivery_note.pdf_path = pdf_path
        logger.info(f"PDF für Lieferschein {delivery_note_number} erstellt: {pdf_path}")
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Lieferschein-PDFs: {e}")

    # PostEntry aktualisieren (falls vorhanden)
    if packing_list.post_entry:
        packing_list.post_entry.delivery_note_id = delivery_note.id
        packing_list.post_entry.status = 'in_progress'
        logger.info(f"PostEntry aktualisiert: Lieferschein verknüpft")

    return delivery_note


def complete_production_workflow(production, order=None, current_user=None):
    """
    Vollständiger Workflow-Durchlauf bei Produktionsabschluss

    Args:
        production: Production Model-Instanz
        order: Order Model-Instanz (optional)
        current_user: Aktueller Benutzer (optional)

    Returns:
        dict: Ergebnis mit erstellten Objekten
    """
    from src.models.models import Order

    result = {
        'success': False,
        'packing_list': None,
        'post_entry': None,
        'errors': []
    }

    try:
        # Order holen
        if not order:
            order = Order.query.get(production.order_id) if hasattr(production, 'order_id') else None

        if not order:
            result['errors'].append("Kein Auftrag gefunden")
            return result

        # Settings prüfen
        company_settings = CompanySettings.get_settings()
        auto_create = order.auto_create_packing_list if hasattr(order, 'auto_create_packing_list') else True

        if company_settings and hasattr(company_settings, 'auto_create_packing_list'):
            auto_create = auto_create and company_settings.auto_create_packing_list

        if not auto_create:
            result['success'] = True
            result['message'] = 'Automatische Packlisten-Erstellung deaktiviert'
            return result

        # Packliste erstellen
        packing_list = create_packing_list_from_production(production, order)
        result['packing_list'] = packing_list

        # PostEntry erstellen
        post_entry = create_post_entry_from_packing_list(packing_list)
        result['post_entry'] = post_entry

        # Verknüpfungen aktualisieren
        packing_list.post_entry_id = post_entry.id

        if order:
            order.packing_list_id = packing_list.id
            order.workflow_status = 'packing'

        db.session.commit()

        result['success'] = True
        result['message'] = f"Packliste {packing_list.packing_list_number} und PostEntry {post_entry.entry_number} erstellt"

        logger.info(f"Produktions-Workflow abgeschlossen: {result['message']}")

    except Exception as e:
        logger.error(f"Fehler im Produktions-Workflow: {e}", exc_info=True)
        result['errors'].append(str(e))
        db.session.rollback()

    return result


__all__ = [
    'create_packing_list_from_production',
    'create_post_entry_from_packing_list',
    'create_delivery_note_from_packing_list',
    'complete_production_workflow'
]
