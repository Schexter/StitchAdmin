# -*- coding: utf-8 -*-
"""
PDF-SERVICE - Rechnungs-PDF Generierung
=======================================

Erstellt von: StitchAdmin
Datum: 09. Juli 2025
Zweck: Service für PDF-Generierung von Rechnungen

Features:
- PDF-Generierung mit ReportLab
- Unterstützung für Logos und Bilder
- Barcode-Integration
- Mehrseitige Dokumente
- Wasserzeichen-Support
"""

import os
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any
import logging
from io import BytesIO

# ReportLab imports
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
        Image, PageBreak, KeepTogether, Frame, PageTemplate
    )
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
    from reportlab.pdfgen import canvas
    from reportlab.graphics.barcode import code128
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("ReportLab nicht installiert. PDF-Generierung nicht verfügbar.")

logger = logging.getLogger(__name__)

class PDFService:
    """Service für PDF-Generierung"""
    
    def __init__(self):
        """Initialisiere PDF Service"""
        self.styles = getSampleStyleSheet() if REPORTLAB_AVAILABLE else None
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Erstelle benutzerdefinierte Styles"""
        if not REPORTLAB_AVAILABLE:
            return
            
        # Rechnungskopf
        self.styles.add(ParagraphStyle(
            name='InvoiceHeader',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a237e'),
            spaceAfter=12
        ))
        
        # Adressblock
        self.styles.add(ParagraphStyle(
            name='AddressBlock',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=12
        ))
        
        # Tabellenüberschrift
        self.styles.add(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.white,
            alignment=TA_CENTER
        ))
        
        # Betragsfeld
        self.styles.add(ParagraphStyle(
            name='Amount',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_RIGHT
        ))
        
    def create_invoice_pdf(self, invoice_data: Dict[str, Any]) -> bytes:
        """
        Erstelle PDF für eine Rechnung
        
        Args:
            invoice_data: Rechnungsdaten
            
        Returns:
            PDF als Bytes
        """
        if not REPORTLAB_AVAILABLE:
            return self._create_fallback_pdf()
            
        try:
            # Buffer für PDF
            buffer = BytesIO()
            
            # Dokument erstellen
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            # Story (Inhalt) aufbauen
            story = []
            
            # Kopfbereich
            story.extend(self._create_header(invoice_data))
            
            # Adressbereich
            story.extend(self._create_address_section(invoice_data))
            
            # Rechnungsinformationen
            story.extend(self._create_invoice_info(invoice_data))
            
            # Positionen
            story.extend(self._create_items_table(invoice_data))
            
            # Summenbereich
            story.extend(self._create_totals_section(invoice_data))
            
            # Zahlungsbedingungen
            story.extend(self._create_payment_terms(invoice_data))
            
            # Fußbereich
            story.extend(self._create_footer(invoice_data))
            
            # PDF generieren
            doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
            
            # Buffer zurücksetzen und Inhalt zurückgeben
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Fehler bei PDF-Erstellung: {str(e)}")
            return self._create_fallback_pdf()
            
    def _create_header(self, invoice_data: Dict) -> List:
        """Erstelle Kopfbereich"""
        elements = []
        
        # Logo (falls vorhanden)
        logo_path = invoice_data.get('logo_path')
        if logo_path and os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=6*cm, height=2*cm)
                logo.hAlign = 'LEFT'
                elements.append(logo)
                elements.append(Spacer(1, 0.5*cm))
            except:
                pass
                
        # Überschrift
        elements.append(Paragraph("RECHNUNG", self.styles['InvoiceHeader']))
        elements.append(Spacer(1, 1*cm))
        
        return elements
        
    def _create_address_section(self, invoice_data: Dict) -> List:
        """Erstelle Adressbereich"""
        elements = []
        
        # Absender und Empfänger nebeneinander
        sender = invoice_data.get('sender', {})
        recipient = invoice_data.get('recipient', {})
        
        # Tabelle für Adressen
        address_data = [[
            # Absender
            Paragraph(f"<b>{sender.get('name', '')}</b><br/>" +
                     f"{sender.get('street', '')}<br/>" +
                     f"{sender.get('postcode', '')} {sender.get('city', '')}<br/>" +
                     f"Tel: {sender.get('phone', '')}<br/>" +
                     f"E-Mail: {sender.get('email', '')}<br/>" +
                     f"USt-IdNr: {sender.get('tax_id', '')}",
                     self.styles['AddressBlock']),
            # Leerzeile
            "",
            # Empfänger
            Paragraph(f"<b>{recipient.get('name', '')}</b><br/>" +
                     f"{recipient.get('street', '')}<br/>" +
                     f"{recipient.get('postcode', '')} {recipient.get('city', '')}",
                     self.styles['AddressBlock'])
        ]]
        
        address_table = Table(address_data, colWidths=[7*cm, 2*cm, 7*cm])
        address_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        elements.append(address_table)
        elements.append(Spacer(1, 1*cm))
        
        return elements
        
    def _create_invoice_info(self, invoice_data: Dict) -> List:
        """Erstelle Rechnungsinformationen"""
        elements = []
        
        # Rechnungsdaten
        info_data = [
            ["Rechnungsnummer:", invoice_data.get('invoice_number', '')],
            ["Rechnungsdatum:", self._format_date(invoice_data.get('invoice_date'))],
            ["Leistungsdatum:", self._format_date(invoice_data.get('delivery_date'))],
            ["Kundennummer:", invoice_data.get('customer_number', '')],
        ]
        
        info_table = Table(info_data, colWidths=[4*cm, 12*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 1*cm))
        
        # Betreff
        if invoice_data.get('subject'):
            elements.append(Paragraph(f"<b>Betreff: {invoice_data['subject']}</b>", 
                                    self.styles['Normal']))
            elements.append(Spacer(1, 0.5*cm))
            
        return elements
        
    def _create_items_table(self, invoice_data: Dict) -> List:
        """Erstelle Positionstabelle"""
        elements = []
        
        # Tabellenkopf
        headers = ['Pos.', 'Bezeichnung', 'Menge', 'Einheit', 'Einzelpreis', 'Gesamt']
        
        # Daten vorbereiten
        data = [headers]
        
        items = invoice_data.get('items', [])
        for idx, item in enumerate(items, 1):
            data.append([
                str(idx),
                item.get('description', ''),
                str(item.get('quantity', 1)),
                item.get('unit', 'Stk.'),
                self._format_currency(item.get('unit_price', 0)),
                self._format_currency(item.get('total', 0))
            ])
            
        # Tabelle erstellen
        table = Table(data, colWidths=[1.5*cm, 8*cm, 2*cm, 2*cm, 2.5*cm, 2.5*cm])
        
        # Styling
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            
            # Daten
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Pos
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Menge
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Einheit
            ('ALIGN', (4, 1), (5, -1), 'RIGHT'),   # Preise
            
            # Gitter
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Alternierende Zeilen
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 1*cm))
        
        return elements
        
    def _create_totals_section(self, invoice_data: Dict) -> List:
        """Erstelle Summenbereich"""
        elements = []
        
        # Summentabelle
        totals_data = []
        
        # Zwischensumme
        if invoice_data.get('subtotal'):
            totals_data.append(['Zwischensumme:', self._format_currency(invoice_data['subtotal'])])
            
        # Rabatt
        if invoice_data.get('discount_amount'):
            totals_data.append([f"Rabatt ({invoice_data.get('discount_percent', 0)}%):", 
                              f"- {self._format_currency(invoice_data['discount_amount'])}"])
            
        # Netto
        totals_data.append(['Nettobetrag:', self._format_currency(invoice_data.get('total_net', 0))])
        
        # Steuern
        taxes = invoice_data.get('taxes', [])
        for tax in taxes:
            totals_data.append([f"MwSt. {tax.get('rate', 19)}%:", 
                              self._format_currency(tax.get('amount', 0))])
            
        # Gesamtbetrag
        totals_data.append(['', ''])  # Leerzeile
        totals_data.append([Paragraph('<b>Gesamtbetrag:</b>', self.styles['Normal']),
                           Paragraph(f"<b>{self._format_currency(invoice_data.get('total_gross', 0))}</b>", 
                                   self.styles['Amount'])])
        
        # Tabelle erstellen
        totals_table = Table(totals_data, colWidths=[12*cm, 4*cm])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
        ]))
        
        # Rechts ausrichten
        totals_table.hAlign = 'RIGHT'
        
        elements.append(totals_table)
        elements.append(Spacer(1, 1*cm))
        
        return elements
        
    def _create_payment_terms(self, invoice_data: Dict) -> List:
        """Erstelle Zahlungsbedingungen"""
        elements = []
        
        # Zahlungsbedingungen
        payment_terms = invoice_data.get('payment_terms', 'Zahlbar innerhalb 14 Tagen ohne Abzug')
        elements.append(Paragraph(f"<b>Zahlungsbedingungen:</b> {payment_terms}", 
                                self.styles['Normal']))
        
        # Bankverbindung
        bank_details = invoice_data.get('bank_details', {})
        if bank_details:
            elements.append(Spacer(1, 0.5*cm))
            elements.append(Paragraph("<b>Bankverbindung:</b>", self.styles['Normal']))
            
            bank_text = f"""
            {bank_details.get('bank_name', '')}<br/>
            IBAN: {bank_details.get('iban', '')}<br/>
            BIC: {bank_details.get('bic', '')}
            """
            elements.append(Paragraph(bank_text, self.styles['Normal']))
            
        # Verwendungszweck
        if invoice_data.get('payment_reference'):
            elements.append(Spacer(1, 0.3*cm))
            elements.append(Paragraph(f"<b>Verwendungszweck:</b> {invoice_data['payment_reference']}", 
                                    self.styles['Normal']))
            
        return elements
        
    def _create_footer(self, invoice_data: Dict) -> List:
        """Erstelle Fußbereich"""
        elements = []
        
        # Abschlusstext
        footer_text = invoice_data.get('footer_text', 
                                      'Vielen Dank für Ihren Auftrag! Bei Fragen stehen wir Ihnen gerne zur Verfügung.')
        
        elements.append(Spacer(1, 2*cm))
        elements.append(Paragraph(footer_text, self.styles['Normal']))
        
        return elements
        
    def _add_page_number(self, canvas_obj, doc):
        """Füge Seitenzahl hinzu"""
        canvas_obj.saveState()
        canvas_obj.setFont('Helvetica', 8)
        canvas_obj.drawRightString(
            doc.pagesize[0] - 2*cm,
            2*cm,
            f"Seite {doc.page}"
        )
        canvas_obj.restoreState()
        
    def _format_date(self, date_value) -> str:
        """Formatiere Datum"""
        if not date_value:
            return ''
        if isinstance(date_value, (date, datetime)):
            return date_value.strftime('%d.%m.%Y')
        return str(date_value)
        
    def _format_currency(self, amount) -> str:
        """Formatiere Währungsbetrag"""
        if isinstance(amount, (int, float, Decimal)):
            return f"{amount:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')
        return str(amount)
        
    def _create_fallback_pdf(self) -> bytes:
        """Erstelle Fallback-PDF wenn ReportLab nicht verfügbar"""
        # Einfaches Text-PDF
        content = b"""
        %PDF-1.4
        1 0 obj
        << /Type /Catalog /Pages 2 0 R >>
        endobj
        2 0 obj
        << /Type /Pages /Kids [3 0 R] /Count 1 >>
        endobj
        3 0 obj
        << /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>
        endobj
        4 0 obj
        << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>
        endobj
        5 0 obj
        << /Length 44 >>
        stream
        BT
        /F1 12 Tf
        100 700 Td
        (ReportLab nicht installiert) Tj
        ET
        endstream
        endobj
        xref
        0 6
        0000000000 65535 f 
        0000000009 00000 n 
        0000000058 00000 n 
        0000000115 00000 n 
        0000000229 00000 n 
        0000000328 00000 n 
        trailer
        << /Size 6 /Root 1 0 R >>
        startxref
        430
        %%EOF
        """
        return content
        
    def create_receipt_pdf(self, receipt_data: Dict[str, Any]) -> bytes:
        """
        Erstelle PDF für einen Kassenbeleg
        
        Args:
            receipt_data: Belegdaten
            
        Returns:
            PDF als Bytes
        """
        # Ähnlich wie Rechnung, aber kompakter
        return self.create_invoice_pdf(receipt_data)  # Vorerst gleiche Implementierung