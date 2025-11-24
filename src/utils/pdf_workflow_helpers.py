# -*- coding: utf-8 -*-
"""
PDF Workflow Helpers
====================
Helper-Funktionen für PDF-Generierung im Workflow
Sammelt Daten aus Models und ruft PDF-Service auf

Erstellt von: Hans Hahn - Alle Rechte vorbehalten
"""

import os
from datetime import datetime
from src.services.pdf_service import PDFService
from src.models.company_settings import CompanySettings
from src.models.branding_settings import BrandingSettings


def generate_packing_list_pdf(packing_list, save_to_disk=True):
    """
    Generiert PDF für eine Packliste

    Args:
        packing_list: PackingList Model-Instanz
        save_to_disk: Ob PDF auf Festplatte gespeichert werden soll

    Returns:
        str: Pfad zur generierten PDF-Datei (falls save_to_disk=True)
        bytes: PDF als Bytes (falls save_to_disk=False)
    """
    # Firmen & Branding-Daten holen
    company_settings = CompanySettings.get_settings()
    branding_settings = BrandingSettings.get_settings()

    # Logo-Pfad
    logo_path = None
    if branding_settings and branding_settings.logo_path:
        logo_full_path = os.path.join('src', 'static', branding_settings.logo_path)
        if os.path.exists(logo_full_path):
            logo_path = logo_full_path

    # Daten für PDF zusammenstellen
    pdf_data = {
        # Firmendaten
        'company_name': company_settings.company_name if company_settings else 'StitchAdmin',
        'company_street': company_settings.street if company_settings else '',
        'company_postcode': company_settings.postcode if company_settings else '',
        'company_city': company_settings.city if company_settings else '',
        'logo_path': logo_path,

        # Packlisten-Daten
        'packing_list_number': packing_list.packing_list_number,
        'created_at': packing_list.created_at,

        # Kunden-Daten
        'customer_name': _get_customer_name(packing_list.customer),
        'order_number': packing_list.order.order_number if packing_list.order else '-',

        # Carton-Info (bei Teillieferungen)
        'carton_label': packing_list.carton_label,

        # Artikel
        'items': packing_list.get_items_list(),

        # Notizen
        'customer_notes': packing_list.customer_notes,
        'packing_notes': packing_list.packing_notes,

        # Gewicht & Maße
        'total_weight': packing_list.total_weight,
        'package_length': packing_list.package_length,
        'package_width': packing_list.package_width,
        'package_height': packing_list.package_height,

        # QK-Status
        'qc_performed': packing_list.qc_performed,
        'qc_by': packing_list.qc_user.username if packing_list.qc_user else None,
        'qc_date': packing_list.qc_date,
    }

    # PDF generieren
    pdf_service = PDFService()

    if save_to_disk:
        # Dateiname generieren
        filename = f"packliste_{packing_list.packing_list_number}.pdf"
        pdf_dir = os.path.join('instance', 'uploads', 'packing_lists')
        os.makedirs(pdf_dir, exist_ok=True)
        output_path = os.path.join(pdf_dir, filename)

        # PDF erstellen & speichern
        pdf_service.create_packing_list_pdf(pdf_data, output_path=output_path)

        return output_path
    else:
        # PDF als Bytes zurückgeben
        return pdf_service.create_packing_list_pdf(pdf_data)


def generate_delivery_note_pdf(delivery_note, save_to_disk=True):
    """
    Generiert PDF für einen Lieferschein

    Args:
        delivery_note: DeliveryNote Model-Instanz
        save_to_disk: Ob PDF auf Festplatte gespeichert werden soll

    Returns:
        str: Pfad zur generierten PDF-Datei (falls save_to_disk=True)
        bytes: PDF als Bytes (falls save_to_disk=False)
    """
    # Firmen & Branding-Daten holen
    company_settings = CompanySettings.get_settings()
    branding_settings = BrandingSettings.get_settings()

    # Logo-Pfad
    logo_path = None
    if branding_settings and branding_settings.logo_path:
        logo_full_path = os.path.join('src', 'static', branding_settings.logo_path)
        if os.path.exists(logo_full_path):
            logo_path = logo_full_path

    # Kunde
    customer = delivery_note.customer
    customer_address = _format_customer_address(customer)

    # Daten für PDF zusammenstellen
    pdf_data = {
        # Firmendaten
        'company_name': company_settings.company_name if company_settings else 'StitchAdmin',
        'company_street': company_settings.street if company_settings else '',
        'company_postcode': company_settings.postcode if company_settings else '',
        'company_city': company_settings.city if company_settings else '',
        'logo_path': logo_path,

        # Lieferschein-Daten
        'delivery_note_number': delivery_note.delivery_note_number,
        'delivery_date': delivery_note.delivery_date,

        # Kunden-Daten
        'customer_name': _get_customer_name(customer),
        'customer_street': customer_address.get('street', ''),
        'customer_postcode': customer_address.get('postcode', ''),
        'customer_city': customer_address.get('city', ''),
        'order_number': delivery_note.order.order_number if delivery_note.order else '-',

        # Versand-Informationen
        'shipping_method': delivery_note.delivery_method,
        'tracking_number': delivery_note.post_entry.tracking_number if delivery_note.post_entry else None,

        # Artikel
        'items': delivery_note.get_items_list(),

        # Notizen
        'notes': delivery_note.notes,

        # Paketinfo
        'total_cartons': delivery_note.packing_list.total_cartons if delivery_note.packing_list else 1,
        'total_weight': delivery_note.packing_list.total_weight if delivery_note.packing_list else None,

        # Unterschrift (falls vorhanden)
        'signature_image': delivery_note.signature_image,
        'signature_name': delivery_note.signature_name,
        'signature_date': delivery_note.signature_date,
    }

    # PDF generieren
    pdf_service = PDFService()

    if save_to_disk:
        # Dateiname generieren
        filename = f"lieferschein_{delivery_note.delivery_note_number}.pdf"
        pdf_dir = os.path.join('instance', 'uploads', 'delivery_notes')
        os.makedirs(pdf_dir, exist_ok=True)
        output_path = os.path.join(pdf_dir, filename)

        # PDF erstellen & speichern
        pdf_service.create_delivery_note_pdf(pdf_data, output_path=output_path)

        return output_path
    else:
        # PDF als Bytes zurückgeben
        return pdf_service.create_delivery_note_pdf(pdf_data)


def _get_customer_name(customer):
    """Hilfsfunktion: Kundenname formatieren"""
    if not customer:
        return ''

    if customer.company_name:
        return customer.company_name
    else:
        return f"{customer.first_name or ''} {customer.last_name or ''}".strip()


def _format_customer_address(customer):
    """Hilfsfunktion: Kundenadresse formatieren"""
    if not customer:
        return {'street': '', 'postcode': '', 'city': ''}

    return {
        'street': customer.street or '',
        'postcode': customer.postcode or '',
        'city': customer.city or ''
    }


__all__ = [
    'generate_packing_list_pdf',
    'generate_delivery_note_pdf'
]
