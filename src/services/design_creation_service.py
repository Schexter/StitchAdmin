# -*- coding: utf-8 -*-
"""
DESIGN-ERSTELLUNGS-SERVICE
==========================
Workflow für Fremd- und Eigenerstellung von Designs

Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import os
import uuid
import logging
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List

from flask import current_app

from src.models import db
from src.models.models import Order, Supplier, ActivityLog, CompanySettings

logger = logging.getLogger(__name__)


class DesignCreationService:
    """
    Service für den Design-Erstellungs-Workflow
    
    Zwei Pfade:
    1. Fremderstellung → DesignOrder + E-Mail an Lieferant
    2. Eigenerstellung → TODO für Grafik-Team + Auftragszettel
    """
    
    def __init__(self):
        pass
    
    # ============================================
    # FREMDERSTELLUNG (Extern)
    # ============================================
    
    def create_external_design_order(
        self,
        order: Order,
        supplier_id: str,
        specs: Dict,
        created_by: str,
        send_email: bool = True
    ) -> Dict:
        """
        Erstellt eine Design-Bestellung bei externem Lieferanten
        
        Args:
            order: Der Kundenauftrag
            supplier_id: ID des Lieferanten (Puncher/Grafiker)
            specs: Dict mit Design-Spezifikationen
            created_by: Username des Erstellers
            send_email: Ob E-Mail automatisch gesendet werden soll
            
        Returns:
            Dict mit Ergebnis
        """
        try:
            from src.models.design import DesignOrder
            
            supplier = Supplier.query.get(supplier_id)
            if not supplier:
                return {'success': False, 'error': 'Lieferant nicht gefunden'}
            
            # Design-Bestellnummer generieren
            year = datetime.now().year
            count = DesignOrder.query.filter(
                DesignOrder.design_order_number.like(f'DO-{year}-%')
            ).count() + 1
            order_number = f"DO-{year}-{count:04d}"
            
            # DesignOrder erstellen
            design_order = DesignOrder(
                id=str(uuid.uuid4()),
                design_order_number=order_number,
                order_id=order.id,
                supplier_id=supplier_id,
                customer_id=order.customer_id,
                
                # Typ
                design_type=specs.get('design_type', 'embroidery'),
                order_type=specs.get('order_type', 'new_design'),
                
                # Allgemein
                design_name=specs.get('design_name', f"Design für {order.order_number}"),
                design_description=specs.get('description', ''),
                
                # Stickerei-Spezifikationen
                target_width_mm=specs.get('width_mm'),
                target_height_mm=specs.get('height_mm'),
                max_stitch_count=specs.get('max_stitch_count'),
                max_colors=specs.get('max_colors'),
                stitch_density=specs.get('stitch_density', 'normal'),
                underlay_type=specs.get('underlay_type', 'standard'),
                fabric_type=specs.get('fabric_type'),
                
                # Druck-Spezifikationen (falls relevant)
                target_print_width_cm=specs.get('print_width_cm'),
                target_print_height_cm=specs.get('print_height_cm'),
                print_method=specs.get('print_method'),
                min_dpi=specs.get('min_dpi', 300),
                needs_transparent_bg=specs.get('needs_transparent_bg', False),
                needs_white_underbase=specs.get('needs_white_underbase', False),
                
                # Vorlage
                source_file_path=specs.get('source_file_path'),
                source_file_name=specs.get('source_file_name'),
                special_requirements=specs.get('special_requirements', ''),
                
                # Status
                status='draft',
                priority=specs.get('priority', 'normal'),
                
                # Metadaten
                created_by=created_by,
                request_date=datetime.utcnow()
            )
            
            # Garnfarben setzen falls vorhanden
            if specs.get('thread_colors'):
                design_order.set_requested_thread_colors(specs['thread_colors'])
            
            # Referenzbilder hinzufügen
            if specs.get('reference_images'):
                for img in specs['reference_images']:
                    design_order.add_reference_image(img.get('path'), img.get('description', ''))
            
            db.session.add(design_order)
            db.session.commit()
            
            result = {
                'success': True,
                'design_order': design_order,
                'order_number': order_number,
                'message': f'Design-Bestellung {order_number} erstellt'
            }
            
            # E-Mail senden
            if send_email and supplier.email:
                email_result = self.send_design_order_email(design_order)
                result['email_sent'] = email_result.get('success', False)
                result['email_message'] = email_result.get('message', '')
            
            # Activity Log
            activity = ActivityLog(
                username=created_by,
                action='design_order_created',
                details=f'Design-Bestellung {order_number} erstellt für Auftrag {order.order_number}, Lieferant: {supplier.name}'
            )
            db.session.add(activity)
            db.session.commit()
            
            logger.info(f"External design order created: {order_number}")
            
            return result
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating external design order: {e}")
            return {'success': False, 'error': str(e)}
    
    def send_design_order_email(self, design_order) -> Dict:
        """
        Sendet Design-Bestellung per E-Mail an Lieferant
        
        Args:
            design_order: Die DesignOrder
            
        Returns:
            Dict mit Ergebnis
        """
        try:
            from src.services.email_service import EmailService
            
            supplier = design_order.supplier
            if not supplier or not supplier.email:
                return {'success': False, 'error': 'Keine Lieferanten-E-Mail vorhanden'}
            
            order = design_order.order
            company = CompanySettings.get_settings()
            
            # E-Mail-Content
            subject = f"Design-Anfrage {design_order.design_order_number} - {company.company_name}"
            
            # HTML-Body erstellen
            html_body = self._build_design_order_email_html(design_order, company)
            text_body = self._build_design_order_email_text(design_order, company)
            
            # Anhänge vorbereiten
            attachments = []
            
            # Quell-Datei anhängen falls vorhanden
            if design_order.source_file_path and os.path.exists(design_order.source_file_path):
                attachments.append({
                    'path': design_order.source_file_path,
                    'filename': design_order.source_file_name or 'Vorlage',
                    'content_type': 'application/octet-stream'
                })
            
            # Referenzbilder anhängen
            for ref in design_order.get_reference_images():
                if ref.get('path') and os.path.exists(ref['path']):
                    attachments.append({
                        'path': ref['path'],
                        'filename': os.path.basename(ref['path']),
                        'content_type': 'image/png'
                    })
            
            # E-Mail senden
            email_service = EmailService()
            result = email_service.send_email(
                to=supplier.email,
                subject=subject,
                body=text_body,
                html_body=html_body,
                attachments=attachments if attachments else None
            )
            
            if result.get('success'):
                # Status aktualisieren
                design_order.status = 'sent'
                design_order.request_sent_at = datetime.utcnow()
                design_order.request_sent_to = supplier.email
                design_order.add_communication(
                    f'Design-Anfrage per E-Mail gesendet an {supplier.email}',
                    comm_type='email_sent',
                    sender='system'
                )
                db.session.commit()
                
                return {
                    'success': True,
                    'message': f'E-Mail gesendet an {supplier.email}'
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'E-Mail konnte nicht gesendet werden')
                }
                
        except Exception as e:
            logger.error(f"Error sending design order email: {e}")
            return {'success': False, 'error': str(e)}
    
    def _build_design_order_email_html(self, design_order, company) -> str:
        """Erstellt HTML-Content für Design-Anfrage E-Mail"""
        
        order = design_order.order
        
        # Spezifikationen formatieren
        specs_html = ""
        if design_order.design_type == 'embroidery':
            specs_html = f"""
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                <tr style="background: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Größe</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">
                        {design_order.target_width_mm or '?'} x {design_order.target_height_mm or '?'} mm
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Max. Stichzahl</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">
                        {design_order.max_stitch_count or 'Keine Vorgabe'}
                    </td>
                </tr>
                <tr style="background: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Max. Farben</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">
                        {design_order.max_colors or 'Keine Vorgabe'}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Stoffart</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">
                        {design_order.fabric_type or 'Nicht angegeben'}
                    </td>
                </tr>
                <tr style="background: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Stichdichte</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">
                        {design_order.stitch_density or 'Normal'}
                    </td>
                </tr>
            </table>
            """
        elif design_order.design_type in ('print', 'dtf'):
            specs_html = f"""
            <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                <tr style="background: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Größe</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">
                        {design_order.target_print_width_cm or '?'} x {design_order.target_print_height_cm or '?'} cm
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Druckmethode</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">
                        {design_order.print_method or 'Nicht angegeben'}
                    </td>
                </tr>
                <tr style="background: #f8f9fa;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Min. DPI</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">
                        {design_order.min_dpi or 300}
                    </td>
                </tr>
            </table>
            """
        
        # Garnfarben falls vorhanden
        colors_html = ""
        thread_colors = design_order.get_requested_thread_colors()
        if thread_colors:
            colors_html = "<p><strong>Gewünschte Garnfarben:</strong></p><ul>"
            for color in thread_colors:
                colors_html += f"<li>{color.get('color_name', '')} ({color.get('color_code', '')})</li>"
            colors_html += "</ul>"
        
        priority_badge = {
            'low': '<span style="background: #6c757d; color: white; padding: 3px 8px; border-radius: 3px;">Niedrig</span>',
            'normal': '<span style="background: #0d6efd; color: white; padding: 3px 8px; border-radius: 3px;">Normal</span>',
            'high': '<span style="background: #ffc107; color: black; padding: 3px 8px; border-radius: 3px;">Hoch</span>',
            'urgent': '<span style="background: #dc3545; color: white; padding: 3px 8px; border-radius: 3px;">EILIG</span>'
        }.get(design_order.priority, '')
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 700px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: white; padding: 25px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0; font-size: 24px;">{design_order.type_icon} Design-Anfrage</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">{design_order.design_order_number}</p>
            </div>
            
            <div style="padding: 30px; background: #f8f9fa; border-radius: 0 0 8px 8px;">
                <p>Guten Tag,</p>
                
                <p>wir bitten um Erstellung eines <strong>{design_order.type_display}</strong>s:</p>
                
                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #e0e0e0;">
                    <h3 style="margin-top: 0; color: #2563eb;">
                        {design_order.design_name}
                        {priority_badge}
                    </h3>
                    
                    <p><strong>Für Auftrag:</strong> {order.order_number if order else 'N/A'}</p>
                    
                    {specs_html}
                    
                    {colors_html}
                    
                    {'<p><strong>Besondere Anforderungen:</strong></p><p style="background: #fff3cd; padding: 10px; border-radius: 5px;">' + design_order.special_requirements + '</p>' if design_order.special_requirements else ''}
                    
                    {'<p><strong>Beschreibung:</strong></p><p>' + design_order.design_description + '</p>' if design_order.design_description else ''}
                </div>
                
                <div style="background: #e8f5e9; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <strong>📎 Anhänge:</strong><br>
                    {self._build_attachments_info_html(design_order)}
                </div>
                
                <p>Bitte senden Sie uns ein Angebot mit Preis und Lieferzeit.</p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 25px 0;">
                
                <p>Mit freundlichen Grüßen<br>
                <strong>{company.company_name}</strong></p>
                
                <p style="font-size: 12px; color: #888; margin-top: 20px;">
                    {company.street} {company.house_number or ''}<br>
                    {company.postal_code} {company.city}<br>
                    {f'Tel: {company.phone}' if company.phone else ''}<br>
                    {company.email or ''}
                </p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _build_design_order_email_text(self, design_order, company) -> str:
        """Erstellt Text-Content für Design-Anfrage E-Mail"""
        
        order = design_order.order
        
        text = f"""
Design-Anfrage {design_order.design_order_number}
{'=' * 50}

Guten Tag,

wir bitten um Erstellung eines {design_order.type_display}s:

DESIGN: {design_order.design_name}
Für Auftrag: {order.order_number if order else 'N/A'}
Priorität: {design_order.priority_display}

SPEZIFIKATIONEN:
"""
        
        if design_order.design_type == 'embroidery':
            text += f"""
- Größe: {design_order.target_width_mm or '?'} x {design_order.target_height_mm or '?'} mm
- Max. Stichzahl: {design_order.max_stitch_count or 'Keine Vorgabe'}
- Max. Farben: {design_order.max_colors or 'Keine Vorgabe'}
- Stoffart: {design_order.fabric_type or 'Nicht angegeben'}
- Stichdichte: {design_order.stitch_density or 'Normal'}
"""
        elif design_order.design_type in ('print', 'dtf'):
            text += f"""
- Größe: {design_order.target_print_width_cm or '?'} x {design_order.target_print_height_cm or '?'} cm
- Druckmethode: {design_order.print_method or 'Nicht angegeben'}
- Min. DPI: {design_order.min_dpi or 300}
"""
        
        if design_order.special_requirements:
            text += f"\nBESONDERE ANFORDERUNGEN:\n{design_order.special_requirements}\n"
        
        if design_order.design_description:
            text += f"\nBESCHREIBUNG:\n{design_order.design_description}\n"

        text += f"""
ANHÄNGE:
{self._build_attachments_info_text(design_order)}

Bitte senden Sie uns ein Angebot mit Preis und Lieferzeit.

Mit freundlichen Grüßen
{company.company_name}

{company.street} {company.house_number or ''}
{company.postal_code} {company.city}
{f'Tel: {company.phone}' if company.phone else ''}
{company.email or ''}
        """
        
        return text
    
    # ============================================
    # EIGENERSTELLUNG (Intern)
    # ============================================
    
    def create_internal_design_task(
        self,
        order: Order,
        specs: Dict,
        created_by: str,
        generate_pdf: bool = True
    ) -> Dict:
        """
        Erstellt eine interne Design-Aufgabe (TODO)
        
        Args:
            order: Der Kundenauftrag
            specs: Dict mit Design-Spezifikationen
            created_by: Username des Erstellers
            generate_pdf: Ob Auftragszettel generiert werden soll
            
        Returns:
            Dict mit Ergebnis
        """
        try:
            from src.models.todo import Todo
            
            # TODO erstellen
            todo = Todo.create_design_todo(order, specs, created_by)
            
            db.session.add(todo)
            db.session.flush()  # Um ID zu bekommen
            
            result = {
                'success': True,
                'todo': todo,
                'message': f'Aufgabe erstellt: {todo.title}'
            }
            
            # Auftragszettel generieren
            if generate_pdf:
                pdf_result = self.generate_design_task_pdf(todo, order, specs)
                if pdf_result.get('success'):
                    todo.document_path = pdf_result['pdf_path']
                    todo.document_name = pdf_result['pdf_name']
                    result['pdf_path'] = pdf_result['pdf_path']
                    result['pdf_generated'] = True
            
            db.session.commit()
            
            # Activity Log
            activity = ActivityLog(
                username=created_by,
                action='design_task_created',
                details=f'Design-Aufgabe erstellt für Auftrag {order.order_number}'
            )
            db.session.add(activity)
            db.session.commit()
            
            logger.info(f"Internal design task created: {todo.id}")
            
            return result
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating internal design task: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_design_task_pdf(self, todo, order: Order, specs: Dict) -> Dict:
        """
        Generiert Auftragszettel als PDF
        
        Args:
            todo: Die TODO-Aufgabe
            order: Der Auftrag
            specs: Design-Spezifikationen
            
        Returns:
            Dict mit pdf_path und pdf_name
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.units import mm
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT
            
            # Verzeichnis erstellen
            try:
                base_path = current_app.instance_path
            except RuntimeError:
                base_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance')
            
            pdf_dir = os.path.join(base_path, 'design_tasks')
            os.makedirs(pdf_dir, exist_ok=True)
            
            # Dateiname
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_name = f"Auftragszettel_{order.order_number}_{timestamp}.pdf"
            pdf_path = os.path.join(pdf_dir, pdf_name)
            
            # PDF erstellen
            doc = SimpleDocTemplate(
                pdf_path,
                pagesize=A4,
                rightMargin=15*mm,
                leftMargin=15*mm,
                topMargin=15*mm,
                bottomMargin=15*mm
            )
            
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                name='Title2',
                fontSize=16,
                alignment=TA_CENTER,
                spaceAfter=10*mm
            ))
            styles.add(ParagraphStyle(
                name='SubHeader',
                fontSize=12,
                fontName='Helvetica-Bold',
                spaceBefore=5*mm,
                spaceAfter=3*mm
            ))
            
            story = []
            
            # Titel
            story.append(Paragraph(
                f"🎨 AUFTRAGSZETTEL - DESIGN-ERSTELLUNG",
                styles['Title2']
            ))
            
            # Auftragsdaten
            company = CompanySettings.get_settings()
            
            header_data = [
                ['Auftrag:', order.order_number, 'Datum:', datetime.now().strftime('%d.%m.%Y')],
                ['Kunde:', order.customer.display_name if order.customer else '-', 'Priorität:', specs.get('priority', 'Normal').upper()],
            ]
            
            header_table = Table(header_data, colWidths=[25*mm, 55*mm, 25*mm, 55*mm])
            header_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.9, 0.9, 0.9)),
                ('BACKGROUND', (2, 0), (2, -1), colors.Color(0.9, 0.9, 0.9)),
            ]))
            story.append(header_table)
            story.append(Spacer(1, 8*mm))
            
            # Design-Spezifikationen
            story.append(Paragraph("📐 DESIGN-SPEZIFIKATIONEN", styles['SubHeader']))
            
            design_type = specs.get('design_type', 'embroidery')
            type_label = {'embroidery': 'Stickerei', 'print': 'Druck', 'dtf': 'DTF'}.get(design_type, design_type)
            
            spec_data = [
                ['Design-Typ:', type_label],
                ['Größe:', f"{specs.get('width_mm', '?')} x {specs.get('height_mm', '?')} mm"],
            ]
            
            if design_type == 'embroidery':
                spec_data.extend([
                    ['Max. Stichzahl:', str(specs.get('max_stitch_count', 'Keine Vorgabe'))],
                    ['Max. Farben:', str(specs.get('max_colors', 'Keine Vorgabe'))],
                    ['Stoffart:', specs.get('fabric_type', 'Nicht angegeben')],
                ])
            
            if specs.get('position'):
                spec_data.append(['Position:', specs.get('position')])
            
            spec_table = Table(spec_data, colWidths=[45*mm, 120*mm])
            spec_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
            ]))
            story.append(spec_table)
            story.append(Spacer(1, 5*mm))
            
            # Garnfarben falls vorhanden
            if specs.get('thread_colors'):
                story.append(Paragraph("🧵 GARNFARBEN", styles['SubHeader']))
                
                color_data = [['#', 'Farbe', 'Code']]
                for i, color in enumerate(specs['thread_colors'], 1):
                    color_data.append([
                        str(i),
                        color.get('color_name', ''),
                        color.get('color_code', '')
                    ])
                
                color_table = Table(color_data, colWidths=[15*mm, 100*mm, 50*mm])
                color_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
                ]))
                story.append(color_table)
                story.append(Spacer(1, 5*mm))
            
            # Besondere Hinweise
            if specs.get('special_requirements') or specs.get('notes'):
                story.append(Paragraph("📝 HINWEISE", styles['SubHeader']))
                notes_text = specs.get('special_requirements', '') or specs.get('notes', '')
                story.append(Paragraph(notes_text, styles['Normal']))
                story.append(Spacer(1, 5*mm))
            
            # Kontrollfeld
            story.append(Paragraph("✅ ERLEDIGT", styles['SubHeader']))
            
            check_data = [
                ['☐ Design erstellt', '☐ Vorschau generiert', '☐ Stichzahl geprüft'],
                ['☐ Farben korrekt', '☐ Größe korrekt', '☐ Hochgeladen'],
            ]
            
            check_table = Table(check_data, colWidths=[55*mm, 55*mm, 55*mm])
            check_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(check_table)
            story.append(Spacer(1, 10*mm))
            
            # Unterschrift
            story.append(Paragraph("_" * 40 + "  " + "_" * 20, styles['Normal']))
            story.append(Paragraph("Bearbeiter                               Datum", styles['Normal']))
            
            # PDF generieren
            doc.build(story)
            
            return {
                'success': True,
                'pdf_path': pdf_path,
                'pdf_name': pdf_name
            }
            
        except Exception as e:
            logger.error(f"Error generating design task PDF: {e}")
            return {'success': False, 'error': str(e)}
    
    # ============================================
    # HILFSFUNKTIONEN
    # ============================================

    def _format_file_size(self, size_bytes: int) -> str:
        """Formatiert Dateigröße in lesbare Einheit"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def _build_attachments_info_html(self, design_order) -> str:
        """Erstellt HTML mit Anhang-Informationen inkl. Dateigrößen"""
        attachments_info = []

        # Quell-Datei
        if design_order.source_file_path:
            if os.path.exists(design_order.source_file_path):
                file_size = os.path.getsize(design_order.source_file_path)
                file_name = design_order.source_file_name or os.path.basename(design_order.source_file_path)
                attachments_info.append(
                    f'<li>📄 <strong>Kundenvorlage:</strong> {file_name} ({self._format_file_size(file_size)})</li>'
                )
            else:
                attachments_info.append('<li>📄 Kundenvorlage (Datei nicht gefunden)</li>')

        # Referenzbilder
        reference_images = design_order.get_reference_images()
        for ref in reference_images:
            ref_path = ref.get('path', '')
            ref_desc = ref.get('description', '')
            if ref_path and os.path.exists(ref_path):
                file_size = os.path.getsize(ref_path)
                file_name = os.path.basename(ref_path)
                desc_text = f' - {ref_desc}' if ref_desc else ''
                attachments_info.append(
                    f'<li>🖼️ <strong>Referenzbild:</strong> {file_name} ({self._format_file_size(file_size)}){desc_text}</li>'
                )

        if attachments_info:
            return '<ul style="margin: 5px 0; padding-left: 20px;">' + ''.join(attachments_info) + '</ul>'
        else:
            return '<small>Keine Anhänge vorhanden</small>'

    def _build_attachments_info_text(self, design_order) -> str:
        """Erstellt Text mit Anhang-Informationen inkl. Dateigrößen"""
        attachments_info = []

        # Quell-Datei
        if design_order.source_file_path:
            if os.path.exists(design_order.source_file_path):
                file_size = os.path.getsize(design_order.source_file_path)
                file_name = design_order.source_file_name or os.path.basename(design_order.source_file_path)
                attachments_info.append(f'- Kundenvorlage: {file_name} ({self._format_file_size(file_size)})')
            else:
                attachments_info.append('- Kundenvorlage (Datei nicht gefunden)')

        # Referenzbilder
        reference_images = design_order.get_reference_images()
        for ref in reference_images:
            ref_path = ref.get('path', '')
            ref_desc = ref.get('description', '')
            if ref_path and os.path.exists(ref_path):
                file_size = os.path.getsize(ref_path)
                file_name = os.path.basename(ref_path)
                desc_text = f' - {ref_desc}' if ref_desc else ''
                attachments_info.append(f'- Referenzbild: {file_name} ({self._format_file_size(file_size)}){desc_text}')

        if attachments_info:
            return '\n'.join(attachments_info)
        else:
            return 'Keine Anhänge vorhanden'

    def create_design_from_task(self, todo, result_file_path: str, created_by: str) -> Dict:
        """
        Erstellt ein Design in der Bibliothek aus einer abgeschlossenen Aufgabe

        Args:
            todo: Die abgeschlossene Todo-Aufgabe
            result_file_path: Pfad zur Ergebnis-Datei
            created_by: Username des Erstellers

        Returns:
            Dict mit Design-Objekt oder Fehler
        """
        try:
            from src.models.design import Design
            import uuid
            import hashlib

            order = todo.order

            # Design-Nummer generieren
            year = datetime.now().year
            count = Design.query.filter(
                Design.design_number.like(f'D-{year}-%')
            ).count() + 1
            design_number = f"D-{year}-{count:04d}"

            # Datei-Hash berechnen für Duplikat-Erkennung
            file_hash = None
            file_size_kb = None
            if result_file_path and os.path.exists(result_file_path):
                with open(result_file_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                file_size_kb = os.path.getsize(result_file_path) // 1024

            # Design erstellen
            design = Design(
                id=str(uuid.uuid4()),
                design_number=design_number,
                name=todo.title.replace('Design erstellen: ', ''),
                description=todo.description,

                # Typ
                design_type=todo.design_type or 'embroidery',
                category='Kundendesign',

                # Kundenverknüpfung
                customer_id=todo.customer_id,
                is_customer_design=True,

                # Dateien
                file_path=result_file_path,
                file_name=todo.result_file_name,
                file_type=os.path.splitext(todo.result_file_name or '')[1].lstrip('.').lower() if todo.result_file_name else None,
                file_size_kb=file_size_kb,
                file_hash=file_hash,

                # Maße aus Task
                width_mm=todo.design_width_mm,
                height_mm=todo.design_height_mm,
                stitch_count=todo.max_stitch_count,

                # Herkunft
                source='internal',

                # Status
                status='active',
                is_approved=False,  # Muss noch genehmigt werden

                # Metadaten
                created_at=datetime.utcnow(),
                created_by=created_by
            )

            # Garnfarben übernehmen falls vorhanden
            specs = todo.get_design_specs()
            if specs.get('thread_colors'):
                design.set_thread_colors(specs['thread_colors'])

            # Tags setzen
            tags = []
            if order:
                tags.append(order.order_number)
            if todo.customer_id:
                from src.models.models import Customer
                customer = Customer.query.get(todo.customer_id)
                if customer:
                    tags.append(customer.company_name or customer.last_name or '')
            design.set_tags(tags)

            # Stickdatei analysieren falls möglich
            if design.design_type == 'embroidery' and result_file_path:
                design.analyze_embroidery_file()

            db.session.add(design)
            db.session.commit()

            # Activity Log
            activity = ActivityLog(
                username=created_by,
                action='design_created',
                details=f'Design {design_number} erstellt aus Aufgabe für {order.order_number if order else "unbekannt"}'
            )
            db.session.add(activity)
            db.session.commit()

            logger.info(f"Design created from task: {design_number}")

            return {
                'success': True,
                'design': design,
                'design_number': design_number,
                'message': f'Design {design_number} erstellt und mit Kunde verknüpft'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating design from task: {e}")
            return {'success': False, 'error': str(e)}

    def create_design_from_external_order(self, design_order, delivered_file_path: str, created_by: str) -> Dict:
        """
        Erstellt ein Design in der Bibliothek aus einer externen Bestellung

        Args:
            design_order: Die DesignOrder
            delivered_file_path: Pfad zur gelieferten Datei
            created_by: Username

        Returns:
            Dict mit Design-Objekt oder Fehler
        """
        try:
            from src.models.design import Design
            import uuid
            import hashlib

            # Design-Nummer generieren
            year = datetime.now().year
            count = Design.query.filter(
                Design.design_number.like(f'D-{year}-%')
            ).count() + 1
            design_number = f"D-{year}-{count:04d}"

            # Datei-Hash berechnen
            file_hash = None
            file_size_kb = None
            if delivered_file_path and os.path.exists(delivered_file_path):
                with open(delivered_file_path, 'rb') as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                file_size_kb = os.path.getsize(delivered_file_path) // 1024

            # Design erstellen
            design = Design(
                id=str(uuid.uuid4()),
                design_number=design_number,
                name=design_order.design_name,
                description=design_order.design_description,

                # Typ
                design_type=design_order.design_type,
                category='Kundendesign',

                # Kundenverknüpfung
                customer_id=design_order.customer_id,
                is_customer_design=True,

                # Dateien
                file_path=delivered_file_path,
                file_name=design_order.delivered_file_name,
                file_type=os.path.splitext(design_order.delivered_file_name or '')[1].lstrip('.').lower() if design_order.delivered_file_name else None,
                file_size_kb=file_size_kb,
                file_hash=file_hash,

                # Maße
                width_mm=design_order.target_width_mm,
                height_mm=design_order.target_height_mm,

                # Herkunft
                source='external_order',
                source_order_id=design_order.id,
                supplier_id=design_order.supplier_id,
                creation_cost=design_order.total_price,

                # Status
                status='active',
                is_approved=False,

                # Metadaten
                created_at=datetime.utcnow(),
                created_by=created_by
            )

            # Garnfarben übernehmen
            if design_order.design_type == 'embroidery':
                colors = design_order.get_requested_thread_colors()
                if colors:
                    design.set_thread_colors(colors)

            # Stickdatei analysieren falls möglich
            if design.design_type == 'embroidery' and delivered_file_path:
                design.analyze_embroidery_file()

            db.session.add(design)

            # Verknüpfung in DesignOrder speichern
            design_order.final_design_id = design.id

            db.session.commit()

            # Activity Log
            activity = ActivityLog(
                username=created_by,
                action='design_created',
                details=f'Design {design_number} erstellt aus externer Bestellung {design_order.design_order_number}'
            )
            db.session.add(activity)
            db.session.commit()

            logger.info(f"Design created from external order: {design_number}")

            return {
                'success': True,
                'design': design,
                'design_number': design_number,
                'message': f'Design {design_number} erstellt und mit Kunde verknüpft'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating design from external order: {e}")
            return {'success': False, 'error': str(e)}

    def get_design_suppliers(self, design_type: str = None) -> List[Supplier]:
        """
        Holt alle Lieferanten die Design-Dienstleistungen anbieten
        
        Args:
            design_type: Optional filter nach Typ (embroidery, print, dtf)
        """
        query = Supplier.query.filter(Supplier.is_active == True)
        
        # Filter nach Lieferanten-Kategorie (falls vorhanden)
        # TODO: Supplier-Kategorien erweitern für Design-Services
        
        return query.order_by(Supplier.name).all()
    
    def get_pending_design_orders(self) -> List:
        """Holt alle offenen Design-Bestellungen"""
        from src.models.design import DesignOrder
        
        return DesignOrder.query.filter(
            DesignOrder.status.in_(['draft', 'sent', 'quoted', 'accepted', 'in_progress'])
        ).order_by(DesignOrder.created_at.desc()).all()
    
    def get_pending_design_tasks(self) -> List:
        """Holt alle offenen Design-Aufgaben"""
        from src.models.todo import Todo
        
        return Todo.query.filter(
            Todo.todo_type == 'design_creation',
            Todo.status.in_(['open', 'in_progress'])
        ).order_by(Todo.due_date.asc()).all()


# Singleton-Instanz
_service_instance = None

def get_design_creation_service() -> DesignCreationService:
    """Gibt die Service-Instanz zurück"""
    global _service_instance
    if _service_instance is None:
        _service_instance = DesignCreationService()
    return _service_instance
