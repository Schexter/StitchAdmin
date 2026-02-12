# -*- coding: utf-8 -*-
"""
DOCUMENT PDF SERVICE
====================
Zentrale PDF-Generierung für alle Dokumente mit:
- Konfigurierbare Speicherpfade (StorageSettings)
- ZugPferd-Integration für Rechnungen
- Einheitliche Dateinamen
- Firmenlogo-Integration

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import io
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

# ReportLab
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab nicht installiert!")

# ZugPferd Service
try:
    from src.services.zugpferd_service import ZugpferdService
    ZUGPFERD_AVAILABLE = True
except ImportError:
    ZUGPFERD_AVAILABLE = False


class DocumentPDFService:
    """Zentrale PDF-Generierung für alle Dokument-Typen"""
    
    def __init__(self):
        """Initialisiere PDF-Service"""
        self.storage_settings = None
        self.company_settings = None
        self._load_settings()
    
    def _load_settings(self):
        """Lade Einstellungen aus Datenbank"""
        try:
            from src.models.storage_settings import StorageSettings
            self.storage_settings = StorageSettings.get_settings()
        except Exception as e:
            logger.warning(f"StorageSettings nicht verfügbar: {e}")
        
        try:
            from src.models.company_settings import CompanySettings
            self.company_settings = CompanySettings.get_settings()
        except Exception as e:
            logger.warning(f"CompanySettings nicht verfügbar: {e}")
    
    def get_save_path(self, doc_type: str, doc_nummer: str, kunde_name: str = None, 
                      datum: date = None, extension: str = 'pdf') -> Tuple[str, str]:
        """
        Ermittelt Speicherpfad und Dateinamen basierend auf Einstellungen
        
        Args:
            doc_type: Dokumenttyp (angebot, auftrag, lieferschein, rechnung, etc.)
            doc_nummer: Dokumentnummer
            kunde_name: Kundenname (optional)
            datum: Datum (optional, default: heute)
            extension: Dateiendung (default: pdf)
        
        Returns:
            Tuple (vollständiger_pfad, dateiname)
        """
        if datum is None:
            datum = date.today()
        
        if self.storage_settings and self.storage_settings.base_path:
            # Pfad aus Einstellungen
            dir_path = self.storage_settings.get_full_path(doc_type, kunde_name, datum)
            filename = self.storage_settings.get_filename(doc_type, doc_nummer, kunde_name, datum, extension)
        else:
            # Fallback: uploads-Ordner
            from flask import current_app
            base = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            dir_path = os.path.join(base, 'pdfs', doc_type + 's')
            
            # Einfacher Dateiname
            safe_nummer = doc_nummer.replace('/', '-').replace('\\', '-')
            filename = f"{safe_nummer}.{extension}"
        
        # Ordner erstellen
        os.makedirs(dir_path, exist_ok=True)
        
        return dir_path, filename
    
    def save_pdf(self, pdf_bytes: bytes, doc_type: str, doc_nummer: str, 
                 kunde_name: str = None, datum: date = None) -> str:
        """
        Speichert PDF an konfigurierten Speicherort
        
        Returns:
            Vollständiger Dateipfad
        """
        dir_path, filename = self.get_save_path(doc_type, doc_nummer, kunde_name, datum)
        full_path = os.path.join(dir_path, filename)
        
        with open(full_path, 'wb') as f:
            f.write(pdf_bytes)
        
        logger.info(f"PDF gespeichert: {full_path}")
        return full_path
    
    def get_company_header_data(self) -> Dict[str, Any]:
        """Lädt Firmendaten für PDF-Header"""
        if self.company_settings:
            return {
                'name': self.company_settings.display_name,
                'street': f"{self.company_settings.street or ''} {self.company_settings.house_number or ''}".strip(),
                'city': f"{self.company_settings.postal_code or ''} {self.company_settings.city or ''}".strip(),
                'phone': self.company_settings.phone or '',
                'email': self.company_settings.email or '',
                'website': self.company_settings.website or '',
                'tax_id': self.company_settings.tax_id or '',
                'vat_id': self.company_settings.vat_id or '',
                'bank_name': self.company_settings.bank_name or '',
                'iban': self.company_settings.iban or '',
                'bic': self.company_settings.bic or '',
                'logo_path': self.company_settings.logo_path,
                'small_business': self.company_settings.small_business,
                'small_business_text': self.company_settings.small_business_text,
            }
        else:
            # Fallback
            return {
                'name': 'StitchAdmin GmbH',
                'street': 'Musterstraße 123',
                'city': '12345 Musterstadt',
                'phone': '0123-456789',
                'email': 'info@stitchadmin.de',
                'website': '',
                'tax_id': '',
                'vat_id': '',
                'bank_name': 'Musterbank',
                'iban': 'DE89 3704 0044 0532 0130 00',
                'bic': 'COBADEFFXXX',
                'logo_path': None,
                'small_business': False,
                'small_business_text': '',
            }
    
    def generate_document_pdf(self, dokument, doc_type: str = None) -> bytes:
        """
        Generiert PDF für beliebigen Dokumenttyp
        
        Args:
            dokument: BusinessDocument-Instanz
            doc_type: Optional override für Dokumenttyp
        
        Returns:
            PDF als Bytes
        """
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("ReportLab nicht installiert!")
        
        # Dokumenttyp ermitteln
        if doc_type is None:
            doc_type = dokument.dokument_typ
        
        # Mapping Typ -> Titel
        titel_map = {
            'angebot': 'ANGEBOT',
            'auftragsbestaetigung': 'AUFTRAGSBESTÄTIGUNG',
            'auftrag': 'AUFTRAGSBESTÄTIGUNG',
            'lieferschein': 'LIEFERSCHEIN',
            'rechnung': 'RECHNUNG',
            'anzahlung': 'ANZAHLUNGSRECHNUNG',
            'teilrechnung': 'TEILRECHNUNG',
            'gutschrift': 'GUTSCHRIFT',
        }
        
        titel = titel_map.get(doc_type, 'DOKUMENT')
        
        return self._generate_generic_pdf(dokument, titel)
    
    def generate_rechnung_pdf(self, rechnung, with_zugpferd: bool = True) -> bytes:
        """
        Generiert Rechnungs-PDF mit optionaler ZugPferd-Integration
        
        Args:
            rechnung: BusinessDocument-Instanz
            with_zugpferd: ZugPferd-XML einbetten (default: True)
        
        Returns:
            PDF als Bytes
        """
        if not REPORTLAB_AVAILABLE:
            raise RuntimeError("ReportLab nicht installiert!")
        
        # Basis-PDF generieren
        pdf_bytes = self._generate_base_invoice_pdf(rechnung)
        
        # ZugPferd-Integration
        if with_zugpferd and ZUGPFERD_AVAILABLE:
            try:
                zugpferd_service = ZugpferdService()
                
                # Invoice-Data für ZugPferd aufbereiten
                invoice_data = self._prepare_zugpferd_data(rechnung)
                
                # XML generieren
                xml_string = zugpferd_service.create_invoice_xml(
                    invoice_data, 
                    profile=zugpferd_service.PROFILE_BASIC
                )
                
                # XML in PDF einbetten
                pdf_bytes = zugpferd_service.create_pdf_with_xml(
                    pdf_bytes, 
                    xml_string,
                    filename='factur-x.xml'
                )
                
                logger.info(f"ZugPferd-XML eingebettet für {rechnung.dokument_nummer}")
                
            except Exception as e:
                logger.error(f"ZugPferd-Integration fehlgeschlagen: {e}")
                # Fallback: PDF ohne XML
        
        return pdf_bytes
    
    def _generate_generic_pdf(self, dokument, titel: str) -> bytes:
        """
        Generiert generisches PDF für alle Dokumenttypen
        (Angebot, Auftragsbestätigung, Lieferschein)
        """
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=25*mm
        )
        
        styles = getSampleStyleSheet()
        
        # Custom Styles
        style_header = ParagraphStyle('Header', parent=styles['Heading1'], fontSize=18, spaceAfter=10)
        style_normal = ParagraphStyle('Normal2', parent=styles['Normal'], fontSize=10, leading=14)
        style_small = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, leading=10)
        
        elements = []
        company = self.get_company_header_data()
        
        # === LOGO & KOPFBEREICH ===
        logo_cell = ""
        if company['logo_path']:
            try:
                from flask import current_app
                logo_full_path = os.path.join(current_app.static_folder, company['logo_path'])
                if os.path.exists(logo_full_path):
                    logo_cell = Image(logo_full_path, width=50*mm, height=20*mm)
            except:
                pass
        
        if not logo_cell:
            logo_cell = Paragraph(f"<b>{company['name']}</b>", style_header)
        
        company_info = f"""
        <b>{company['name']}</b><br/>
        {company['street']}<br/>
        {company['city']}<br/>
        Tel: {company['phone']}<br/>
        {company['email']}
        """
        
        header_table = Table([
            [logo_cell, Paragraph(company_info.strip(), style_small)]
        ], colWidths=[90*mm, 80*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10*mm))
        
        # === EMPFÄNGERADRESSE ===
        adresse = dokument.rechnungsadresse or dokument.lieferadresse or {}
        empfaenger = f"""
        {adresse.get('company', '') or adresse.get('name', '')}<br/>
        {adresse.get('contact', '') or ''}<br/>
        {adresse.get('street', '')} {adresse.get('house_number', '')}<br/>
        {adresse.get('postal_code', '')} {adresse.get('city', '')}
        """
        elements.append(Paragraph(empfaenger.strip(), style_normal))
        elements.append(Spacer(1, 10*mm))
        
        # === DOKUMENTTITEL ===
        elements.append(Paragraph(f"<b>{titel}</b>", style_header))
        elements.append(Spacer(1, 5*mm))
        
        # === DOKUMENTINFOS ===
        info_data = [
            [f'{titel}-Nr.:', dokument.dokument_nummer],
            ['Datum:', dokument.dokument_datum.strftime('%d.%m.%Y') if dokument.dokument_datum else '-'],
        ]
        
        if dokument.gueltig_bis:
            info_data.append(['Gültig bis:', dokument.gueltig_bis.strftime('%d.%m.%Y')])
        if dokument.kundenreferenz:
            info_data.append(['Ihre Referenz:', dokument.kundenreferenz])
        
        info_table = Table(info_data, colWidths=[40*mm, 60*mm])
        info_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 8*mm))
        
        # === BETREFF & EINLEITUNG ===
        if dokument.betreff:
            elements.append(Paragraph(f"<b>Betreff: {dokument.betreff}</b>", style_normal))
            elements.append(Spacer(1, 3*mm))
        
        if dokument.einleitung:
            elements.append(Paragraph(dokument.einleitung, style_normal))
            elements.append(Spacer(1, 5*mm))
        
        # === POSITIONEN ===
        pos_data = [['Pos.', 'Bezeichnung', 'Menge', 'Einheit', 'Einzelpreis', 'Gesamt']]
        
        for pos in dokument.positionen:
            bezeichnung = pos.bezeichnung
            if pos.beschreibung:
                bezeichnung += f"\n{pos.beschreibung}"
            
            pos_data.append([
                str(pos.position),
                Paragraph(bezeichnung, style_small),
                self._format_number(pos.menge, decimals=2),
                pos.einheit or 'Stk.',
                self._format_currency(pos.einzelpreis_netto),
                self._format_currency(pos.netto_gesamt)
            ])
        
        col_widths = [12*mm, 75*mm, 18*mm, 15*mm, 25*mm, 25*mm]
        pos_table = Table(pos_data, colWidths=col_widths, repeatRows=1)
        pos_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
        ]))
        elements.append(pos_table)
        elements.append(Spacer(1, 5*mm))
        
        # === SUMMEN ===
        summen_data = []
        summen_data.append(['', 'Nettobetrag:', self._format_currency(dokument.summe_netto or 0)])
        
        if company['small_business']:
            summen_data.append(['', 'MwSt.:', 'entfällt'])
        else:
            summen_data.append(['', 'MwSt. 19%:', self._format_currency(dokument.summe_mwst or 0)])
        
        summen_data.append(['', 'Gesamtbetrag:', self._format_currency(dokument.summe_brutto or 0)])
        
        summen_table = Table(summen_data, colWidths=[100*mm, 40*mm, 30*mm])
        summen_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (1, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (1, -1), (-1, -1), 1, colors.black),
        ]))
        elements.append(summen_table)
        elements.append(Spacer(1, 10*mm))
        
        # === SCHLUSSBEMERKUNG ===
        if dokument.schlussbemerkung:
            elements.append(Paragraph(dokument.schlussbemerkung, style_normal))
        
        # === FOOTER ===
        if company['tax_id'] or company['vat_id']:
            elements.append(Spacer(1, 10*mm))
            footer_text = []
            if company['tax_id']:
                footer_text.append(f"Steuernummer: {company['tax_id']}")
            if company['vat_id']:
                footer_text.append(f"USt-IdNr.: {company['vat_id']}")
            elements.append(Paragraph(" | ".join(footer_text), style_small))
        
        # PDF erstellen
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _generate_base_invoice_pdf(self, rechnung) -> bytes:
        """Generiert Basis-PDF für Rechnung"""
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=25*mm
        )
        
        styles = getSampleStyleSheet()
        
        # Custom Styles
        style_header = ParagraphStyle(
            'Header', 
            parent=styles['Heading1'], 
            fontSize=18,
            spaceAfter=10
        )
        style_normal = ParagraphStyle(
            'Normal2', 
            parent=styles['Normal'], 
            fontSize=10, 
            leading=14
        )
        style_small = ParagraphStyle(
            'Small', 
            parent=styles['Normal'], 
            fontSize=8, 
            leading=10
        )
        style_right = ParagraphStyle(
            'Right',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_RIGHT
        )
        
        elements = []
        company = self.get_company_header_data()
        
        # === LOGO & KOPFBEREICH ===
        header_data = []
        
        # Logo (falls vorhanden)
        logo_cell = ""
        if company['logo_path']:
            try:
                from flask import current_app
                logo_full_path = os.path.join(current_app.static_folder, company['logo_path'])
                if os.path.exists(logo_full_path):
                    logo_cell = Image(logo_full_path, width=50*mm, height=20*mm)
            except:
                pass
        
        if not logo_cell:
            logo_cell = Paragraph(f"<b>{company['name']}</b>", style_header)
        
        # Firmenadresse rechts
        company_info = f"""
        <b>{company['name']}</b><br/>
        {company['street']}<br/>
        {company['city']}<br/>
        Tel: {company['phone']}<br/>
        {company['email']}
        """
        
        header_table = Table([
            [logo_cell, Paragraph(company_info.strip(), style_small)]
        ], colWidths=[90*mm, 80*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10*mm))
        
        # === EMPFÄNGERADRESSE ===
        adresse = rechnung.rechnungsadresse or {}
        empfaenger = f"""
        {adresse.get('company', '') or adresse.get('name', '')}<br/>
        {adresse.get('contact', '') or ''}<br/>
        {adresse.get('street', '')} {adresse.get('house_number', '')}<br/>
        {adresse.get('postal_code', '')} {adresse.get('city', '')}
        """
        elements.append(Paragraph(empfaenger.strip(), style_normal))
        elements.append(Spacer(1, 10*mm))
        
        # === DOKUMENTTITEL ===
        from src.models.document_workflow import DokumentTyp
        titel = "RECHNUNG"
        if rechnung.dokument_typ == DokumentTyp.ANZAHLUNG.value:
            titel = "ANZAHLUNGSRECHNUNG"
        elif rechnung.dokument_typ == DokumentTyp.TEILRECHNUNG.value:
            titel = "TEILRECHNUNG"
        elif rechnung.dokument_typ == DokumentTyp.GUTSCHRIFT.value:
            titel = "GUTSCHRIFT"
        
        elements.append(Paragraph(f"<b>{titel}</b>", style_header))
        elements.append(Spacer(1, 5*mm))
        
        # === DOKUMENTINFOS ===
        info_data = [
            ['Rechnungs-Nr.:', rechnung.dokument_nummer],
            ['Rechnungsdatum:', rechnung.dokument_datum.strftime('%d.%m.%Y') if rechnung.dokument_datum else '-'],
            ['Leistungsdatum:', rechnung.leistungsdatum.strftime('%d.%m.%Y') if rechnung.leistungsdatum else '-'],
            ['Fällig bis:', rechnung.faelligkeitsdatum.strftime('%d.%m.%Y') if rechnung.faelligkeitsdatum else '-'],
        ]
        
        if rechnung.kundenreferenz:
            info_data.append(['Ihre Referenz:', rechnung.kundenreferenz])
        
        info_table = Table(info_data, colWidths=[40*mm, 60*mm])
        info_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 8*mm))
        
        # === BETREFF & EINLEITUNG ===
        if rechnung.betreff:
            elements.append(Paragraph(f"<b>Betreff: {rechnung.betreff}</b>", style_normal))
            elements.append(Spacer(1, 3*mm))
        
        if rechnung.einleitung:
            elements.append(Paragraph(rechnung.einleitung, style_normal))
            elements.append(Spacer(1, 5*mm))
        
        # === POSITIONEN ===
        pos_data = [['Pos.', 'Bezeichnung', 'Menge', 'Einheit', 'Einzelpreis', 'Gesamt']]
        
        for pos in rechnung.positionen:
            bezeichnung = pos.bezeichnung
            if pos.beschreibung:
                bezeichnung += f"\n{pos.beschreibung}"
            
            pos_data.append([
                str(pos.position),
                Paragraph(bezeichnung, style_small),
                self._format_number(pos.menge, decimals=2),
                pos.einheit or 'Stk.',
                self._format_currency(pos.einzelpreis_netto),
                self._format_currency(pos.netto_gesamt)
            ])
        
        col_widths = [12*mm, 75*mm, 18*mm, 15*mm, 25*mm, 25*mm]
        pos_table = Table(pos_data, colWidths=col_widths, repeatRows=1)
        pos_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),
            ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),
        ]))
        elements.append(pos_table)
        elements.append(Spacer(1, 5*mm))
        
        # === SUMMEN ===
        summen_data = []
        
        # Rabatt (falls vorhanden)
        if rechnung.rabatt_betrag and rechnung.rabatt_betrag > 0:
            summen_data.append(['', 'Zwischensumme:', self._format_currency(rechnung.summe_netto + rechnung.rabatt_betrag)])
            summen_data.append(['', f'Rabatt ({rechnung.rabatt_prozent or 0}%):', f'-{self._format_currency(rechnung.rabatt_betrag)}'])
        
        summen_data.append(['', 'Nettobetrag:', self._format_currency(rechnung.summe_netto or 0)])
        
        # Kleinunternehmer?
        if company['small_business']:
            summen_data.append(['', 'MwSt.:', 'entfällt'])
            summen_data.append(['', '', Paragraph(f"<i>{company['small_business_text']}</i>", style_small)])
        else:
            summen_data.append(['', 'MwSt. 19%:', self._format_currency(rechnung.summe_mwst or 0)])
        
        summen_data.append(['', 'Gesamtbetrag:', self._format_currency(rechnung.summe_brutto or 0)])
        
        summen_table = Table(summen_data, colWidths=[100*mm, 40*mm, 30*mm])
        summen_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (1, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (1, -1), (-1, -1), 1, colors.black),
        ]))
        elements.append(summen_table)
        elements.append(Spacer(1, 10*mm))
        
        # === ZAHLUNGSINFO ===
        if rechnung.zahlungstext:
            elements.append(Paragraph(f"<b>Zahlungsbedingungen:</b> {rechnung.zahlungstext}", style_small))
            elements.append(Spacer(1, 5*mm))
        
        # === BANKVERBINDUNG ===
        bank_text = f"""
        <b>Bankverbindung:</b><br/>
        {company['name']} | IBAN: {company['iban']} | BIC: {company['bic']}
        """
        elements.append(Paragraph(bank_text, style_small))
        
        # === SCHLUSSBEMERKUNG ===
        if rechnung.schlussbemerkung:
            elements.append(Spacer(1, 5*mm))
            elements.append(Paragraph(rechnung.schlussbemerkung, style_normal))
        
        # === FOOTER ===
        if company['tax_id'] or company['vat_id']:
            elements.append(Spacer(1, 10*mm))
            footer_text = []
            if company['tax_id']:
                footer_text.append(f"Steuernummer: {company['tax_id']}")
            if company['vat_id']:
                footer_text.append(f"USt-IdNr.: {company['vat_id']}")
            elements.append(Paragraph(" | ".join(footer_text), style_small))
        
        # PDF erstellen
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    def _prepare_zugpferd_data(self, rechnung) -> Dict[str, Any]:
        """Bereitet Rechnungsdaten für ZugPferd-Service auf"""
        company = self.get_company_header_data()
        adresse = rechnung.rechnungsadresse or {}
        
        # Positionen
        items = []
        for pos in rechnung.positionen:
            items.append({
                'position': pos.position,
                'description': pos.bezeichnung,
                'quantity': float(pos.menge),
                'unit': pos.einheit or 'Stück',
                'unit_price': float(pos.einzelpreis_netto),
                'tax_rate': float(pos.mwst_satz or 19),
                'total_net': float(pos.netto_gesamt or 0),
            })
        
        return {
            'invoice_number': rechnung.dokument_nummer,
            'invoice_date': rechnung.dokument_datum,
            'delivery_date': rechnung.leistungsdatum or rechnung.dokument_datum,
            'due_date': rechnung.faelligkeitsdatum,
            'payment_reference': rechnung.dokument_nummer,
            'payment_terms': rechnung.zahlungstext or 'Zahlbar innerhalb 14 Tagen',
            'currency': 'EUR',
            'items': items,
            'seller': {
                'name': company['name'],
                'street': company['street'],
                'postcode': company['city'].split()[0] if company['city'] else '',
                'city': ' '.join(company['city'].split()[1:]) if company['city'] else '',
                'country': 'DE',
                'tax_number': company['vat_id'] or company['tax_id'],
            },
            'buyer': {
                'name': adresse.get('company') or adresse.get('name', ''),
                'street': f"{adresse.get('street', '')} {adresse.get('house_number', '')}".strip(),
                'postcode': adresse.get('postal_code', ''),
                'city': adresse.get('city', ''),
                'country': 'DE',
            },
            'total_net': float(rechnung.summe_netto or 0),
            'total_tax': float(rechnung.summe_mwst or 0),
            'total_gross': float(rechnung.summe_brutto or 0),
        }
    
    def _format_currency(self, value, symbol: str = '€') -> str:
        """Formatiert Betrag als Währung (deutsch)"""
        if value is None:
            value = 0
        return f"{value:,.2f} {symbol}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    def _format_number(self, value, decimals: int = 2) -> str:
        """Formatiert Zahl (deutsch)"""
        if value is None:
            value = 0
        format_str = f"{{:,.{decimals}f}}"
        return format_str.format(value).replace(',', 'X').replace('.', ',').replace('X', '.')


# Singleton-Instanz
_pdf_service = None

def get_pdf_service() -> DocumentPDFService:
    """Gibt Singleton-Instanz des PDF-Service zurück"""
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = DocumentPDFService()
    return _pdf_service
