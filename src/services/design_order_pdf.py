"""
Design-Order PDF Generator
Erstellt professionelle PDF-Beauftragungen für externe Puncher/Designer

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas
from datetime import datetime
import os


class DesignOrderPDFGenerator:
    """Generiert PDF-Beauftragungen für Design-Bestellungen"""
    
    def __init__(self, design_order):
        self.order = design_order
        self.styles = getSampleStyleSheet()
        self._setup_styles()
        
    def _setup_styles(self):
        """Definiert Custom-Styles"""
        # Titel
        self.styles.add(ParagraphStyle(
            name='DocTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=6*mm,
            textColor=colors.HexColor('#1a365d')
        ))
        
        # Untertitel
        self.styles.add(ParagraphStyle(
            name='DocSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=4*mm,
            textColor=colors.HexColor('#4a5568')
        ))
        
        # Section Header
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceBefore=8*mm,
            spaceAfter=4*mm,
            textColor=colors.HexColor('#2d3748'),
            borderPadding=(0, 0, 2*mm, 0)
        ))
        
        # Info Label
        self.styles.add(ParagraphStyle(
            name='InfoLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#718096')
        ))
        
        # Info Value
        self.styles.add(ParagraphStyle(
            name='InfoValue',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#1a202c')
        ))
        
        # Hinweis
        self.styles.add(ParagraphStyle(
            name='Notice',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#c53030'),
            spaceAfter=2*mm
        ))
    
    def generate(self):
        """Erstellt die PDF und gibt den Pfad zurück"""
        # Ausgabepfad
        from flask import current_app
        output_dir = os.path.join(current_app.root_path, '..', 'uploads', 'design_orders')
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"Beauftragung_{self.order.design_order_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = os.path.join(output_dir, filename)
        
        # PDF erstellen
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            leftMargin=20*mm,
            rightMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        # Content aufbauen
        story = []
        
        # Header
        story.extend(self._build_header())
        
        # Empfänger & Auftragsinfo
        story.extend(self._build_order_info())
        
        # Design-Spezifikation
        story.extend(self._build_specification())
        
        # Farbvorgaben
        story.extend(self._build_color_section())
        
        # Vorlage/Referenz
        story.extend(self._build_source_section())
        
        # Besondere Anforderungen
        story.extend(self._build_requirements())
        
        # Lieferung & Zahlung
        story.extend(self._build_delivery_info())
        
        # Footer
        story.extend(self._build_footer())
        
        # PDF generieren
        doc.build(story)
        
        return output_path
    
    def _build_header(self):
        """Erstellt den Header mit Firmenlogo und Bestellnummer"""
        elements = []
        
        # Firmeninfo laden
        try:
            from src.models.company_settings import CompanySettings
            company = CompanySettings.get_settings()
            company_name = company.company_name or 'Mustermann Stickerei'
            company_address = f"{company.street or ''}\n{company.postal_code or ''} {company.city or ''}"
        except:
            company_name = 'Mustermann Stickerei'
            company_address = ''
        
        # Header-Tabelle
        header_data = [
            [
                Paragraph(f"<b>{company_name}</b><br/><font size='9'>{company_address.replace(chr(10), '<br/>')}</font>", self.styles['Normal']),
                Paragraph(f"<b>DESIGN-BEAUFTRAGUNG</b><br/><font size='14' color='#2d3748'>{self.order.design_order_number}</font>", 
                         ParagraphStyle('Right', parent=self.styles['Normal'], alignment=TA_RIGHT, fontSize=10))
            ]
        ]
        
        header_table = Table(header_data, colWidths=[90*mm, 80*mm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        elements.append(header_table)
        
        # Datum
        elements.append(Spacer(1, 4*mm))
        elements.append(Paragraph(
            f"Datum: {datetime.now().strftime('%d.%m.%Y')}",
            ParagraphStyle('DateRight', parent=self.styles['Normal'], alignment=TA_RIGHT, fontSize=9)
        ))
        
        # Trennlinie
        elements.append(Spacer(1, 4*mm))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        
        return elements
    
    def _build_order_info(self):
        """Erstellt den Empfänger- und Auftragsinfo-Block"""
        elements = []
        
        # Zwei-Spalten Layout
        left_data = []
        right_data = []
        
        # Empfänger (links)
        left_data.append(["AN:", ""])
        if self.order.supplier:
            left_data.append([self.order.supplier.name, ""])
            if self.order.supplier.contact_person:
                left_data.append([f"z.Hd. {self.order.supplier.contact_person}", ""])
            if self.order.supplier.email:
                left_data.append([self.order.supplier.email, ""])
        else:
            left_data.append(["[Lieferant nicht angegeben]", ""])
        
        # Auftragsart (rechts)
        type_checks = {
            'embroidery': 'Stickprogramm (DST)',
            'print': 'Druckdatei',
            'dtf': 'DTF-Design'
        }
        
        right_data.append(["AUFTRAGSART:", ""])
        for t, label in type_checks.items():
            check = "☑" if self.order.design_type == t else "☐"
            right_data.append([f"{check} {label}", ""])
        
        # Order-Type
        order_types = {
            'new_design': 'Neuerstellung',
            'revision': 'Überarbeitung',
            'conversion': 'Konvertierung'
        }
        right_data.append(["", ""])
        right_data.append([f"Art: {order_types.get(self.order.order_type, self.order.order_type or '-')}", ""])
        
        # Tabellen erstellen
        elements.append(Spacer(1, 6*mm))
        
        info_table_data = []
        max_rows = max(len(left_data), len(right_data))
        
        for i in range(max_rows):
            left_val = left_data[i][0] if i < len(left_data) else ""
            right_val = right_data[i][0] if i < len(right_data) else ""
            info_table_data.append([left_val, right_val])
        
        info_table = Table(info_table_data, colWidths=[90*mm, 80*mm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(info_table)
        
        return elements
    
    def _build_specification(self):
        """Erstellt die Design-Spezifikation"""
        elements = []
        
        elements.append(Spacer(1, 6*mm))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        elements.append(Paragraph("DESIGN-SPEZIFIKATION", self.styles['SectionHeader']))
        
        # Design-Name
        elements.append(Paragraph(f"<b>Name:</b> {self.order.design_name or '-'}", self.styles['InfoValue']))
        
        if self.order.design_description:
            elements.append(Spacer(1, 2*mm))
            elements.append(Paragraph(f"<b>Beschreibung:</b><br/>{self.order.design_description}", self.styles['InfoValue']))
        
        elements.append(Spacer(1, 4*mm))
        
        # Spezifikations-Tabelle je nach Typ
        if self.order.design_type == 'embroidery':
            spec_data = self._get_embroidery_spec_data()
        else:
            spec_data = self._get_print_spec_data()
        
        if spec_data:
            spec_table = Table(spec_data, colWidths=[45*mm, 45*mm, 45*mm, 35*mm])
            spec_table.setStyle(TableStyle([
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f7fafc')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 4),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(spec_table)
        
        return elements
    
    def _get_embroidery_spec_data(self):
        """Stickerei-Spezifikationsdaten"""
        data = [
            ["Breite (mm)", "Höhe (mm)", "Max. Stiche", "Max. Farben"]
        ]
        
        data.append([
            f"{self.order.target_width_mm or '-'} mm",
            f"{self.order.target_height_mm or '-'} mm",
            f"{self.order.max_stitch_count or '-'}",
            f"{self.order.max_colors or '-'}"
        ])
        
        # Zweite Zeile
        density_labels = {'normal': 'Normal', 'dicht': 'Dicht', 'locker': 'Locker'}
        underlay_labels = {'keine': 'Keine', 'leicht': 'Leicht', 'standard': 'Standard', 'stark': 'Stark'}
        
        data.append(["Stichdichte", "Unterlage", "Stoffart", ""])
        data.append([
            density_labels.get(self.order.stitch_density, self.order.stitch_density or '-'),
            underlay_labels.get(self.order.underlay_type, self.order.underlay_type or '-'),
            self.order.fabric_type or '-',
            ""
        ])
        
        return data
    
    def _get_print_spec_data(self):
        """Druck-Spezifikationsdaten"""
        data = [
            ["Breite (cm)", "Höhe (cm)", "Min. DPI", "Farbmodus"]
        ]
        
        data.append([
            f"{self.order.target_print_width_cm or '-'} cm",
            f"{self.order.target_print_height_cm or '-'} cm",
            f"{self.order.min_dpi or 300}",
            (self.order.color_mode or 'CMYK').upper()
        ])
        
        # Zweite Zeile
        data.append(["Druckmethode", "Transparenz", "Weiß-Unterlage", ""])
        data.append([
            self.order.print_method or '-',
            "Ja" if self.order.needs_transparent_bg else "Nein",
            "Ja" if self.order.needs_white_underbase else "Nein",
            ""
        ])
        
        return data
    
    def _build_color_section(self):
        """Erstellt den Farbvorgaben-Block"""
        elements = []
        
        elements.append(Spacer(1, 4*mm))
        elements.append(Paragraph("FARBVORGABEN", self.styles['SectionHeader']))
        
        if self.order.design_type == 'embroidery':
            colors_data = self.order.get_requested_thread_colors()
            if colors_data:
                # Farbtabelle
                table_data = [["Nr", "Farbe", "Garncode", "Muster"]]
                
                for i, color in enumerate(colors_data, 1):
                    rgb = color.get('rgb', '#CCCCCC')
                    table_data.append([
                        str(i),
                        color.get('color_name', '-'),
                        color.get('color_code', '-'),
                        ""  # Hier könnte ein Farbfeld sein
                    ])
                
                color_table = Table(table_data, colWidths=[15*mm, 60*mm, 40*mm, 25*mm])
                color_table.setStyle(TableStyle([
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f7fafc')),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                    ('PADDING', (0, 0), (-1, -1), 4),
                    ('ALIGN', (0, 0), (0, -1), 'CENTER'),
                ]))
                elements.append(color_table)
            else:
                elements.append(Paragraph("Keine spezifischen Farbvorgaben - bitte passende Farben vorschlagen.", 
                                         self.styles['InfoValue']))
        else:
            colors_data = self.order.get_requested_print_colors()
            if colors_data:
                for color in colors_data:
                    if color.get('type') == 'pantone':
                        elements.append(Paragraph(f"• Pantone {color.get('code', '-')}: {color.get('name', '')}", 
                                                 self.styles['InfoValue']))
                    elif color.get('type') == 'cmyk':
                        elements.append(Paragraph(
                            f"• CMYK: C{color.get('c', 0)} M{color.get('m', 0)} Y{color.get('y', 0)} K{color.get('k', 0)}", 
                            self.styles['InfoValue']))
            else:
                elements.append(Paragraph("Farben gemäß Vorlage.", self.styles['InfoValue']))
        
        return elements
    
    def _build_source_section(self):
        """Erstellt den Vorlagen-Block"""
        elements = []
        
        elements.append(Spacer(1, 4*mm))
        elements.append(Paragraph("KUNDENVORLAGE", self.styles['SectionHeader']))
        
        if self.order.source_file_name:
            elements.append(Paragraph(f"<b>Datei:</b> {self.order.source_file_name}", self.styles['InfoValue']))
            elements.append(Paragraph(f"<i>Datei ist dieser Beauftragung beigefügt.</i>", self.styles['InfoLabel']))
        else:
            elements.append(Paragraph("Keine Vorlage-Datei vorhanden.", self.styles['InfoValue']))
        
        # Referenzbilder
        ref_images = self.order.get_reference_images()
        if ref_images:
            elements.append(Spacer(1, 2*mm))
            elements.append(Paragraph(f"<b>Referenzbilder:</b> {len(ref_images)} Stück", self.styles['InfoValue']))
        
        return elements
    
    def _build_requirements(self):
        """Erstellt den Block für besondere Anforderungen"""
        elements = []
        
        if self.order.special_requirements:
            elements.append(Spacer(1, 4*mm))
            elements.append(Paragraph("BESONDERE ANFORDERUNGEN", self.styles['SectionHeader']))
            
            # Anforderungen als Liste
            for line in self.order.special_requirements.split('\n'):
                if line.strip():
                    elements.append(Paragraph(f"• {line.strip()}", self.styles['InfoValue']))
        
        return elements
    
    def _build_delivery_info(self):
        """Erstellt den Liefer- und Zahlungsinfo-Block"""
        elements = []
        
        elements.append(Spacer(1, 6*mm))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        elements.append(Paragraph("LIEFERUNG", self.styles['SectionHeader']))
        
        # Liefertermin
        delivery_date = self.order.expected_delivery.strftime('%d.%m.%Y') if self.order.expected_delivery else '-'
        elements.append(Paragraph(f"<b>Gewünschte Lieferung:</b> {delivery_date}", self.styles['InfoValue']))
        
        # Priorität
        priority_labels = {'low': 'Niedrig', 'normal': 'Normal', 'high': 'Hoch', 'urgent': 'Eilig (+25%)'}
        priority_checks = ""
        for p, label in priority_labels.items():
            check = "☑" if self.order.priority == p else "☐"
            priority_checks += f"{check} {label}  "
        elements.append(Paragraph(f"<b>Priorität:</b> {priority_checks}", self.styles['InfoValue']))
        
        # Lieferformat
        if self.order.design_type == 'embroidery':
            elements.append(Paragraph("<b>Lieferformat:</b> DST (Tajima)", self.styles['InfoValue']))
        else:
            elements.append(Paragraph("<b>Lieferformat:</b> PDF/PNG (300+ DPI)", self.styles['InfoValue']))
        
        # Lieferung per E-Mail
        try:
            from src.models.company_settings import CompanySettings
            company = CompanySettings.get_settings()
            email = company.email or 'bestellung@example.de'
        except:
            email = 'bestellung@example.de'
        
        elements.append(Paragraph(f"<b>Lieferung per:</b> E-Mail an {email}", self.styles['InfoValue']))
        
        # Zahlungsbedingungen
        elements.append(Spacer(1, 4*mm))
        elements.append(Paragraph("ZAHLUNGSBEDINGUNGEN", self.styles['SectionHeader']))
        
        if self.order.deposit_required:
            deposit_pct = int(self.order.deposit_percent or 50)
            elements.append(Paragraph(f"☑ {deposit_pct}% Anzahlung vor Beginn", self.styles['InfoValue']))
            elements.append(Paragraph(f"☐ Restbetrag nach Lieferung", self.styles['InfoValue']))
        else:
            elements.append(Paragraph(f"☐ Anzahlung vor Beginn", self.styles['InfoValue']))
            elements.append(Paragraph(f"☑ Vollständige Zahlung nach Lieferung", self.styles['InfoValue']))
        
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph(f"<b>Verwendungszweck:</b> {self.order.design_order_number}", self.styles['InfoValue']))
        
        return elements
    
    def _build_footer(self):
        """Erstellt den Footer mit Kontakt und Unterschriftsfeld"""
        elements = []
        
        elements.append(Spacer(1, 8*mm))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
        
        # Kontakt
        try:
            from src.models.company_settings import CompanySettings
            company = CompanySettings.get_settings()
            contact = f"{company.contact_person or 'Ansprechpartner'} | Tel: {company.phone or '-'} | {company.email or '-'}"
        except:
            contact = "Kontakt bei Rückfragen: -"
        
        elements.append(Spacer(1, 4*mm))
        elements.append(Paragraph(f"<b>Kontakt bei Rückfragen:</b><br/>{contact}", self.styles['InfoValue']))
        
        # Unterschriftsfeld
        elements.append(Spacer(1, 10*mm))
        
        sig_data = [
            ["Datum: _____________________", "Unterschrift: _________________________________"]
        ]
        sig_table = Table(sig_data, colWidths=[70*mm, 100*mm])
        sig_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ]))
        elements.append(sig_table)
        
        return elements
