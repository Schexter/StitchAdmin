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

    def create_packing_list_pdf(self, packing_list_data: Dict[str, Any], output_path: str = None) -> bytes:
        """
        Erstelle PDF für eine Packliste

        Args:
            packing_list_data: Packlisten-Daten
            output_path: Optionaler Pfad zum Speichern

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

            # Story aufbauen
            story = []

            # Header
            story.extend(self._create_packing_list_header(packing_list_data))

            # Kundeninfo & Auftrag
            story.extend(self._create_packing_list_info(packing_list_data))

            # Artikeltabelle
            story.extend(self._create_packing_list_items(packing_list_data))

            # Kundenvorgaben
            if packing_list_data.get('customer_notes'):
                story.extend(self._create_customer_notes_section(packing_list_data))

            # QK-Bereich
            story.extend(self._create_qc_section(packing_list_data))

            # Verpackungs-Bereich
            story.extend(self._create_packing_section(packing_list_data))

            # QR-Code
            story.extend(self._create_qr_code_section(packing_list_data))

            # PDF generieren
            doc.build(story)

            # Speichern falls Pfad angegeben
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(buffer.getvalue())

            # Buffer zurücksetzen und Inhalt zurückgeben
            buffer.seek(0)
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Fehler bei Packlisten-PDF-Erstellung: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_pdf()

    def _create_packing_list_header(self, data: Dict) -> List:
        """Erstelle Header für Packliste"""
        elements = []

        # Logo (falls vorhanden)
        logo_path = data.get('logo_path')
        if logo_path and os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=6*cm, height=2*cm)
                logo.hAlign = 'LEFT'
                elements.append(logo)
                elements.append(Spacer(1, 0.5*cm))
            except Exception as e:
                logger.warning(f"Logo konnte nicht geladen werden: {e}")

        # Firma links, PACKLISTE rechts
        header_data = [[
            Paragraph(f"<b>{data.get('company_name', 'StitchAdmin')}</b><br/>" +
                     f"{data.get('company_street', '')}<br/>" +
                     f"{data.get('company_postcode', '')} {data.get('company_city', '')}",
                     self.styles['Normal']),
            Paragraph("<b>PACKLISTE</b><br/>" +
                     f"{data.get('packing_list_number', '')}<br/>" +
                     f"{self._format_date(data.get('created_at', datetime.now()))}",
                     self.styles['Heading2'])
        ]]

        header_table = Table(header_data, colWidths=[10*cm, 6*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))

        elements.append(header_table)
        elements.append(Spacer(1, 1*cm))

        return elements

    def _create_packing_list_info(self, data: Dict) -> List:
        """Erstelle Info-Bereich für Packliste"""
        elements = []

        # Kunden & Auftragsinfo
        info_data = [
            ["Kunde:", data.get('customer_name', '')],
            ["Auftrag:", data.get('order_number', '')],
        ]

        # Carton-Info bei Teillieferung
        if data.get('carton_label'):
            info_data.append(["Lieferung:", data['carton_label']])

        info_table = Table(info_data, colWidths=[4*cm, 12*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        elements.append(info_table)
        elements.append(Spacer(1, 1*cm))

        return elements

    def _create_packing_list_items(self, data: Dict) -> List:
        """Erstelle Artikeltabelle für Packliste"""
        elements = []

        # Überschrift
        elements.append(Paragraph("<b>ARTIKELLISTE</b>", self.styles['Heading3']))
        elements.append(Spacer(1, 0.3*cm))

        # Tabellenkopf
        headers = ['Pos.', 'Artikel', 'Menge', 'EAN/SKU']

        # Daten vorbereiten
        table_data = [headers]

        items = data.get('items', [])
        for idx, item in enumerate(items, 1):
            table_data.append([
                str(idx),
                item.get('name', item.get('description', '')),
                str(item.get('quantity', 1)),
                item.get('ean', item.get('sku', '-'))
            ])

        # Tabelle erstellen
        table = Table(table_data, colWidths=[2*cm, 9*cm, 3*cm, 4*cm])

        # Styling
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # Daten
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Pos
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Menge
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # EAN

            # Gitter
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

            # Alternierende Zeilen
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 1*cm))

        return elements

    def _create_customer_notes_section(self, data: Dict) -> List:
        """Erstelle Kundenvorgaben-Bereich"""
        elements = []

        elements.append(Paragraph("<b>KUNDENVORGABEN:</b>", self.styles['Heading3']))
        elements.append(Spacer(1, 0.2*cm))

        # Kundenvorgaben in Box
        notes_data = [[Paragraph(data.get('customer_notes', ''), self.styles['Normal'])]]
        notes_table = Table(notes_data, colWidths=[16*cm])
        notes_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fff3cd')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#ffc107')),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))

        elements.append(notes_table)
        elements.append(Spacer(1, 1*cm))

        return elements

    def _create_qc_section(self, data: Dict) -> List:
        """Erstelle QK-Bereich"""
        elements = []

        elements.append(Paragraph("<b>QUALITÄTSKONTROLLE:</b>", self.styles['Heading3']))
        elements.append(Spacer(1, 0.3*cm))

        # QK-Checkboxen
        qc_items = [
            "☐ Stickqualität geprüft",
            "☐ Farben korrekt",
            "☐ Vollständigkeit geprüft",
            "☐ Keine Beschädigungen"
        ]

        for item in qc_items:
            elements.append(Paragraph(item, self.styles['Normal']))
            elements.append(Spacer(1, 0.2*cm))

        # Unterschriftenfelder
        elements.append(Spacer(1, 0.5*cm))
        sig_data = [
            ["Geprüft von:", "_" * 40, "Datum:", "_" * 20]
        ]
        sig_table = Table(sig_data, colWidths=[3*cm, 7*cm, 2*cm, 4*cm])
        sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ]))

        elements.append(sig_table)
        elements.append(Spacer(1, 1*cm))

        return elements

    def _create_packing_section(self, data: Dict) -> List:
        """Erstelle Verpackungs-Bereich"""
        elements = []

        elements.append(Paragraph("<b>VERPACKUNG:</b>", self.styles['Heading3']))
        elements.append(Spacer(1, 0.3*cm))

        # Gewicht & Maße
        packing_data = [
            ["Gewicht:", "_" * 15 + " kg"],
            ["Maße (L×B×H):", "_" * 10 + " × " + "_" * 10 + " × " + "_" * 10 + " cm"],
        ]

        packing_table = Table(packing_data, colWidths=[4*cm, 12*cm])
        packing_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(packing_table)
        elements.append(Spacer(1, 0.5*cm))

        # Unterschriftenfeld
        sig_data = [
            ["Verpackt von:", "_" * 40, "Datum:", "_" * 20]
        ]
        sig_table = Table(sig_data, colWidths=[3*cm, 7*cm, 2*cm, 4*cm])
        sig_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ]))

        elements.append(sig_table)
        elements.append(Spacer(1, 1*cm))

        return elements

    def _create_qr_code_section(self, data: Dict) -> List:
        """Erstelle QR-Code für Tracking"""
        elements = []

        try:
            # QR-Code mit Packlisten-Nummer
            from reportlab.graphics.barcode import qr
            from reportlab.graphics.shapes import Drawing

            qr_code = qr.QrCodeWidget(data.get('packing_list_number', ''))
            qr_drawing = Drawing(3*cm, 3*cm)
            qr_drawing.add(qr_code)

            # QR-Code zentrieren
            qr_table = Table([[qr_drawing]], colWidths=[16*cm])
            qr_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ]))

            elements.append(qr_table)

        except Exception as e:
            logger.warning(f"QR-Code konnte nicht erstellt werden: {e}")

        return elements

    def create_delivery_note_pdf(self, delivery_note_data: Dict[str, Any], output_path: str = None) -> bytes:
        """
        Erstelle PDF für einen Lieferschein

        Args:
            delivery_note_data: Lieferschein-Daten
            output_path: Optionaler Pfad zum Speichern

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

            # Story aufbauen
            story = []

            # Header
            story.extend(self._create_delivery_note_header(delivery_note_data))

            # Lieferadresse
            story.extend(self._create_delivery_address(delivery_note_data))

            # Lieferinfo
            story.extend(self._create_delivery_info(delivery_note_data))

            # Artikeltabelle
            story.extend(self._create_delivery_items(delivery_note_data))

            # Paketinfo
            story.extend(self._create_package_info(delivery_note_data))

            # Unterschriftenfeld
            story.extend(self._create_signature_field(delivery_note_data))

            # Fußzeile
            story.extend(self._create_delivery_footer())

            # PDF generieren
            doc.build(story)

            # Speichern falls Pfad angegeben
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(buffer.getvalue())

            # Buffer zurücksetzen und Inhalt zurückgeben
            buffer.seek(0)
            return buffer.getvalue()

        except Exception as e:
            logger.error(f"Fehler bei Lieferschein-PDF-Erstellung: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._create_fallback_pdf()

    def _create_delivery_note_header(self, data: Dict) -> List:
        """Erstelle Header für Lieferschein"""
        elements = []

        # Logo (falls vorhanden)
        logo_path = data.get('logo_path')
        if logo_path and os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=6*cm, height=2*cm)
                logo.hAlign = 'LEFT'
                elements.append(logo)
                elements.append(Spacer(1, 0.5*cm))
            except Exception as e:
                logger.warning(f"Logo konnte nicht geladen werden: {e}")

        # Firma links, LIEFERSCHEIN rechts
        header_data = [[
            Paragraph(f"<b>{data.get('company_name', 'StitchAdmin')}</b><br/>" +
                     f"{data.get('company_street', '')}<br/>" +
                     f"{data.get('company_postcode', '')} {data.get('company_city', '')}",
                     self.styles['Normal']),
            Paragraph("<b>LIEFERSCHEIN</b><br/>" +
                     f"{data.get('delivery_note_number', '')}<br/>" +
                     f"{self._format_date(data.get('delivery_date', datetime.now()))}",
                     self.styles['Heading2'])
        ]]

        header_table = Table(header_data, colWidths=[10*cm, 6*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))

        elements.append(header_table)
        elements.append(Spacer(1, 1*cm))

        return elements

    def _create_delivery_address(self, data: Dict) -> List:
        """Erstelle Lieferadresse"""
        elements = []

        elements.append(Paragraph("<b>LIEFERANSCHRIFT:</b>", self.styles['Heading3']))
        elements.append(Spacer(1, 0.3*cm))

        # Adresse in Box
        address = f"<b>{data.get('customer_name', '')}</b><br/>" + \
                 f"{data.get('customer_street', '')}<br/>" + \
                 f"{data.get('customer_postcode', '')} {data.get('customer_city', '')}"

        address_data = [[Paragraph(address, self.styles['Normal'])]]
        address_table = Table(address_data, colWidths=[16*cm])
        address_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.grey),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))

        elements.append(address_table)
        elements.append(Spacer(1, 1*cm))

        return elements

    def _create_delivery_info(self, data: Dict) -> List:
        """Erstelle Lieferinformationen"""
        elements = []

        # Lieferinfo
        info_data = [
            ["Auftragsnummer:", data.get('order_number', '')],
            ["Lieferdatum:", self._format_date(data.get('delivery_date', datetime.now()))],
        ]

        # Versandart & Tracking (falls vorhanden)
        if data.get('shipping_method'):
            info_data.append(["Versandart:", data['shipping_method']])

        if data.get('tracking_number'):
            info_data.append(["Sendungsnummer:", data['tracking_number']])

        info_table = Table(info_data, colWidths=[4*cm, 12*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        elements.append(info_table)
        elements.append(Spacer(1, 1*cm))

        return elements

    def _create_delivery_items(self, data: Dict) -> List:
        """Erstelle Artikeltabelle für Lieferschein"""
        elements = []

        # Überschrift
        elements.append(Paragraph("<b>GELIEFERTE ARTIKEL</b>", self.styles['Heading3']))
        elements.append(Spacer(1, 0.3*cm))

        # Tabellenkopf
        headers = ['Pos.', 'Bezeichnung', 'Menge', 'Einheit']

        # Daten vorbereiten
        table_data = [headers]

        items = data.get('items', [])
        for idx, item in enumerate(items, 1):
            table_data.append([
                str(idx),
                item.get('name', item.get('description', '')),
                str(item.get('quantity', 1)),
                item.get('unit', 'Stk.')
            ])

        # Tabelle erstellen
        table = Table(table_data, colWidths=[2*cm, 10*cm, 2*cm, 2*cm])

        # Styling
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),

            # Daten
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Pos
            ('ALIGN', (2, 1), (3, -1), 'CENTER'),  # Menge & Einheit

            # Gitter
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

            # Alternierende Zeilen
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
        ]))

        elements.append(table)
        elements.append(Spacer(1, 1*cm))

        return elements

    def _create_package_info(self, data: Dict) -> List:
        """Erstelle Paket-Informationen"""
        elements = []

        # Paketinfo
        package_data = []

        if data.get('total_cartons'):
            package_data.append(["Anzahl Pakete:", str(data['total_cartons'])])

        if data.get('total_weight'):
            package_data.append(["Gesamtgewicht:", f"{data['total_weight']} kg"])

        if package_data:
            package_table = Table(package_data, colWidths=[4*cm, 12*cm])
            package_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
            ]))

            elements.append(package_table)
            elements.append(Spacer(1, 1*cm))

        return elements

    def _create_signature_field(self, data: Dict) -> List:
        """Erstelle Unterschriftenfeld"""
        elements = []

        elements.append(Paragraph("<b>UNTERSCHRIFT EMPFÄNGER:</b>", self.styles['Heading3']))
        elements.append(Spacer(1, 1*cm))

        # Unterschriftenfelder
        sig_data = [
            ["_" * 80],
            ["Name (Druckschrift)"],
            [""],
            ["_" * 40 + "        " + "_" * 30],
            ["Unterschrift                                 Datum"]
        ]

        sig_table = Table(sig_data, colWidths=[16*cm])
        sig_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))

        elements.append(sig_table)
        elements.append(Spacer(1, 1*cm))

        return elements

    def _create_delivery_footer(self) -> List:
        """Erstelle Fußzeile für Lieferschein"""
        elements = []

        # Rechtlicher Hinweis
        footer_text = "Dies ist kein steuerliches Dokument. Die Rechnung folgt separat."

        elements.append(Spacer(1, 1*cm))

        footer_data = [[Paragraph(footer_text, self.styles['Normal'])]]
        footer_table = Table(footer_data, colWidths=[16*cm])
        footer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8f9fa')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))

        elements.append(footer_table)

        return elements