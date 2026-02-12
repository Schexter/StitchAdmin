# -*- coding: utf-8 -*-
"""
Design-Freigabe PDF Generator
Erstellt eine PDF mit Design-Vorschau und Unterschriftsfeld für Kundenfreigabe
"""

import os
import io
from datetime import datetime
from collections import Counter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from PIL import Image as PILImage

import logging
logger = logging.getLogger(__name__)


def extract_dominant_colors(image_path, num_colors=8, min_percentage=3):
    """
    Extrahiert die dominanten Farben aus einem Bild

    Args:
        image_path: Pfad zum Bild
        num_colors: Maximale Anzahl Farben zu extrahieren
        min_percentage: Mindestanteil in % um als relevante Farbe zu gelten

    Returns:
        Liste von Dicts mit hex, rgb, percentage, name
    """
    try:
        with PILImage.open(image_path) as img:
            # Bild auf kleine Größe reduzieren für schnellere Analyse
            img = img.convert('RGB')
            img = img.resize((150, 150), PILImage.Resampling.LANCZOS)

            # Alle Pixel extrahieren
            pixels = list(img.getdata())
            total_pixels = len(pixels)

            # Farben quantisieren (ähnliche Farben zusammenfassen)
            # Auf 32er-Stufen runden für Gruppierung
            def quantize_color(rgb):
                return tuple(((c // 32) * 32) + 16 for c in rgb)

            quantized = [quantize_color(p) for p in pixels]
            color_counts = Counter(quantized)

            # Top-Farben ermitteln
            dominant = color_counts.most_common(num_colors * 2)

            result = []
            for rgb, count in dominant:
                percentage = (count / total_pixels) * 100
                if percentage < min_percentage:
                    continue

                # Weiß/Hintergrund-Farben überspringen
                if all(c > 240 for c in rgb):  # Fast weiß
                    continue
                if all(c < 15 for c in rgb):  # Fast schwarz (optional behalten)
                    pass

                hex_color = '#{:02x}{:02x}{:02x}'.format(*rgb)
                color_name = get_color_name(rgb)

                result.append({
                    'hex': hex_color,
                    'rgb': rgb,
                    'percentage': round(percentage, 1),
                    'name': color_name
                })

                if len(result) >= num_colors:
                    break

            return result

    except Exception as e:
        logger.error(f"Fehler bei Farbextraktion: {e}")
        return []


def get_color_name(rgb):
    """
    Gibt einen deutschen Farbnamen für einen RGB-Wert zurück
    """
    r, g, b = rgb

    # Graustufen
    if abs(r - g) < 30 and abs(g - b) < 30 and abs(r - b) < 30:
        avg = (r + g + b) / 3
        if avg < 30:
            return "Schwarz"
        elif avg < 80:
            return "Dunkelgrau"
        elif avg < 160:
            return "Grau"
        elif avg < 220:
            return "Hellgrau"
        else:
            return "Weiß"

    # Farbton bestimmen (vereinfacht)
    max_val = max(r, g, b)
    min_val = min(r, g, b)

    if max_val == min_val:
        return "Grau"

    # Sättigung
    saturation = (max_val - min_val) / max_val if max_val > 0 else 0

    # Dominante Farbe
    if r >= g and r >= b:
        if r - g > 50 and r - b > 50:
            if saturation > 0.5:
                return "Rot" if g < 100 else "Orange"
            return "Rosa" if b > g else "Koralle"
        elif abs(r - g) < 40 and b < r * 0.5:
            return "Gelb" if r > 200 else "Olive"

    if g >= r and g >= b:
        if g - r > 30 and g - b > 30:
            return "Grün" if saturation > 0.4 else "Mint"
        elif abs(g - b) < 30 and r < g * 0.7:
            return "Türkis"

    if b >= r and b >= g:
        if b - r > 30 and b - g > 30:
            if r > g:
                return "Violett" if r > 100 else "Blau"
            return "Blau" if saturation > 0.5 else "Hellblau"

    # Mischfarben
    if r > 200 and g > 200 and b < 100:
        return "Gelb"
    if r > 200 and g < 100 and b > 200:
        return "Magenta"
    if r < 100 and g > 200 and b > 200:
        return "Cyan"
    if r > 150 and g > 100 and b < 100:
        return "Orange"
    if r > 100 and g < 100 and b > 100:
        return "Lila"
    if r < 100 and g > 100 and b < 100:
        return "Dunkelgrün"
    if r > 150 and g > 80 and g < 150 and b > 80 and b < 150:
        return "Braun"

    return "Farbig"


def get_textile_info_from_order(order):
    """
    Sammelt Textil-Informationen aus den Auftragspositionen

    Returns:
        Dict mit textile_types, textile_colors, textile_sizes
    """
    textile_types = set()
    textile_colors = set()
    textile_sizes = set()

    try:
        for item in order.items.all():
            if item.article:
                textile_types.add(item.article.name)
            if item.textile_color:
                textile_colors.add(item.textile_color)
            if item.textile_size:
                textile_sizes.add(item.textile_size)
    except Exception as e:
        logger.error(f"Fehler beim Lesen der Textil-Infos: {e}")

    return {
        'types': list(textile_types),
        'colors': list(textile_colors),
        'sizes': list(textile_sizes)
    }


def create_design_approval_pdf(
    order,
    design,
    company_settings,
    design_image_path=None,
    output_path=None
):
    """
    Erstellt eine Design-Freigabe PDF

    Args:
        order: Order-Objekt
        design: OrderDesign-Objekt (oder None für einfache Aufträge)
        company_settings: CompanySettings-Objekt
        design_image_path: Pfad zum Design-Bild
        output_path: Speicherpfad für PDF (optional, sonst BytesIO)

    Returns:
        BytesIO oder Dateipfad
    """

    # Output-Buffer oder Datei
    if output_path:
        buffer = output_path
    else:
        buffer = io.BytesIO()

    # PDF erstellen
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    # Styles
    styles = getSampleStyleSheet()

    # Bestehende Styles überschreiben oder neue hinzufügen
    if 'CustomTitle' not in [s for s in styles.byName]:
        styles.add(ParagraphStyle(
            name='CustomTitle',
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=10*mm,
            fontName='Helvetica-Bold'
        ))
    if 'Subtitle' not in [s for s in styles.byName]:
        styles.add(ParagraphStyle(
            name='Subtitle',
            fontSize=12,
            leading=14,
            alignment=TA_CENTER,
            spaceAfter=5*mm,
            textColor=colors.grey
        ))
    if 'SectionHeader' not in [s for s in styles.byName]:
        styles.add(ParagraphStyle(
            name='SectionHeader',
            fontSize=12,
            leading=14,
            fontName='Helvetica-Bold',
            spaceBefore=5*mm,
            spaceAfter=3*mm
        ))
    if 'Small' not in [s for s in styles.byName]:
        styles.add(ParagraphStyle(
            name='Small',
            fontSize=8,
            leading=10,
            textColor=colors.grey
        ))
    if 'Footer' not in [s for s in styles.byName]:
        styles.add(ParagraphStyle(
            name='Footer',
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.grey
        ))

    # Content
    content = []

    # === HEADER ===
    company_name = company_settings.company_name if company_settings else "StitchAdmin"

    # Firmenlogo (falls vorhanden)
    if company_settings and company_settings.logo_path:
        try:
            logo_path = company_settings.logo_path
            if os.path.exists(logo_path):
                logo = Image(logo_path, width=50*mm, height=20*mm)
                logo.hAlign = 'LEFT'
                content.append(logo)
                content.append(Spacer(1, 5*mm))
        except Exception as e:
            logger.warning(f"Logo konnte nicht geladen werden: {e}")

    content.append(Paragraph("DESIGN-FREIGABE", styles['CustomTitle']))
    content.append(Paragraph(
        f"Bitte prüfen und unterschreiben Sie dieses Dokument",
        styles['Subtitle']
    ))

    content.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    content.append(Spacer(1, 5*mm))

    # === AUFTRAGS-INFORMATIONEN ===
    content.append(Paragraph("Auftragsinformationen", styles['SectionHeader']))

    # Kunde
    customer_name = order.customer.display_name if order.customer else "Unbekannt"

    order_data = [
        ["Auftragsnummer:", order.order_number or str(order.id)],
        ["Datum:", datetime.now().strftime("%d.%m.%Y")],
        ["Kunde:", customer_name],
    ]

    if order.customer and order.customer.company_name and order.customer.company_name != customer_name:
        order_data.append(["Firma:", order.customer.company_name])

    order_table = Table(order_data, colWidths=[50*mm, 100*mm])
    order_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    content.append(order_table)
    content.append(Spacer(1, 5*mm))

    # === TEXTIL-INFORMATIONEN ===
    textile_info = get_textile_info_from_order(order)

    if textile_info['types'] or textile_info['colors'] or textile_info['sizes']:
        content.append(Paragraph("Textil-Informationen", styles['SectionHeader']))

        textile_data = []
        if textile_info['types']:
            textile_data.append(["Textil:", ", ".join(textile_info['types'])])
        if textile_info['colors']:
            textile_data.append(["Textilfarbe:", ", ".join(textile_info['colors'])])
        if textile_info['sizes']:
            # Größen sortieren
            sizes = textile_info['sizes']
            size_order = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', '2XL', '3XL', '4XL']
            sorted_sizes = sorted(sizes, key=lambda x: size_order.index(x) if x in size_order else 100)
            textile_data.append(["Größen:", ", ".join(sorted_sizes)])

        if textile_data:
            textile_table = Table(textile_data, colWidths=[50*mm, 100*mm])
            textile_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            content.append(textile_table)
            content.append(Spacer(1, 5*mm))

    # === DESIGN-DETAILS ===
    content.append(Paragraph("Design-Details", styles['SectionHeader']))

    design_data = []

    if design:
        # Multi-Position Design
        design_data.append(["Position:", design.get_position_label()])

        # Typ-Label korrekt ermitteln
        design_type_labels = {
            'stick': 'Stickerei',
            'druck': 'Druck',
            'flex': 'Flex/Flock',
            # Legacy-Typen auf neue mappen
            'dtf': 'Druck',
            'flock': 'Flex/Flock'
        }
        design_type_label = design_type_labels.get(design.design_type, design.design_type or 'Stickerei')
        design_data.append(["Veredelungsart:", design_type_label])

        if design.design_name:
            design_data.append(["Bezeichnung:", design.design_name])

        # Details je nach Typ
        if design.design_type == 'stick':
            if design.stitch_count:
                design_data.append(["Stichzahl:", f"{design.stitch_count:,}".replace(",", ".")])
            if design.width_mm and design.height_mm:
                design_data.append(["Größe:", f"{design.width_mm} x {design.height_mm} mm"])
            if design.thread_colors:
                try:
                    import json
                    colors_data = json.loads(design.thread_colors) if isinstance(design.thread_colors, str) else design.thread_colors
                    if isinstance(colors_data, list):
                        color_str = ", ".join([c.get('color', '') for c in colors_data if c.get('color')])
                        if color_str:
                            design_data.append(["Garnfarben:", color_str])
                except:
                    pass
        else:
            # Druck-Details
            if design.print_width_cm and design.print_height_cm:
                design_data.append(["Größe:", f"{design.print_width_cm} x {design.print_height_cm} cm"])
            if design.print_colors:
                design_data.append(["Anzahl Farben:", str(design.print_colors)])
            if design.print_method:
                design_data.append(["Druckverfahren:", design.print_method])
    else:
        # Einfacher Auftrag (ohne Multi-Position)
        if order.embroidery_position:
            design_data.append(["Position:", order.embroidery_position])
        if order.stitch_count:
            design_data.append(["Stichzahl:", f"{order.stitch_count:,}".replace(",", ".")])
        if order.design_width_mm and order.design_height_mm:
            design_data.append(["Größe:", f"{order.design_width_mm} x {order.design_height_mm} mm"])
        if order.thread_colors:
            design_data.append(["Garnfarben:", order.thread_colors])
        if order.description:
            design_data.append(["Beschreibung:", order.description[:100]])

    # Design-Details Tabelle anzeigen
    if design_data:
        design_table = Table(design_data, colWidths=[50*mm, 100*mm])
        design_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3*mm),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        content.append(design_table)

    content.append(Spacer(1, 5*mm))

    # === DESIGN-VORSCHAU ===
    content.append(Paragraph("Design-Vorschau", styles['SectionHeader']))

    if design_image_path and os.path.exists(design_image_path):
        try:
            # Bildgröße ermitteln und anpassen
            with PILImage.open(design_image_path) as img:
                img_width, img_height = img.size

            # Max 150mm breit, 100mm hoch
            max_width = 150*mm
            max_height = 100*mm

            aspect = img_width / img_height
            if img_width > img_height:
                display_width = min(max_width, img_width * 0.264583)  # px to mm
                display_height = display_width / aspect
            else:
                display_height = min(max_height, img_height * 0.264583)
                display_width = display_height * aspect

            # Begrenzung
            if display_width > max_width:
                display_width = max_width
                display_height = display_width / aspect
            if display_height > max_height:
                display_height = max_height
                display_width = display_height * aspect

            design_img = Image(design_image_path, width=display_width, height=display_height)
            design_img.hAlign = 'CENTER'

            # Rahmen um das Bild
            img_table = Table([[design_img]], colWidths=[160*mm])
            img_table.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 1, colors.grey),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 5*mm),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5*mm),
            ]))
            content.append(img_table)

        except Exception as e:
            logger.error(f"Fehler beim Laden des Design-Bildes: {e}")
            content.append(Paragraph(
                "[Design-Bild konnte nicht geladen werden]",
                styles['Normal']
            ))
    else:
        # Platzhalter
        placeholder_table = Table(
            [["Design-Vorschau nicht verfügbar"]],
            colWidths=[160*mm],
            rowHeights=[60*mm]
        )
        placeholder_table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.grey),
        ]))
        content.append(placeholder_table)

    content.append(Spacer(1, 5*mm))

    # === AUTOMATISCH ERKANNTE FARBEN (für Druck/Flex-Designs) ===
    is_print_design = design and design.design_type in ['druck', 'flex', 'dtf', 'flock']

    if is_print_design and design_image_path and os.path.exists(design_image_path):
        detected_colors = extract_dominant_colors(design_image_path, num_colors=6, min_percentage=3)

        if detected_colors:
            content.append(Paragraph("Erkannte Druckfarben", styles['SectionHeader']))

            # Farbtabelle erstellen mit Farbbox, Name und HEX
            color_rows = []
            for col_info in detected_colors:
                # Farbbox als kleines gefärbtes Quadrat (über Tabelle simuliert)
                hex_code = col_info['hex']
                color_name = col_info['name']
                percentage = col_info['percentage']

                color_rows.append([
                    f"■ {color_name}",
                    hex_code.upper(),
                    f"{percentage}%"
                ])

            if color_rows:
                # Header
                color_table_data = [["Farbe", "HEX-Code", "Anteil"]] + color_rows

                color_table = Table(color_table_data, colWidths=[60*mm, 40*mm, 30*mm])
                color_table.setStyle(TableStyle([
                    # Header
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
                    # Content
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2*mm),
                    ('TOPPADDING', (0, 0), (-1, -1), 2*mm),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                content.append(color_table)

                content.append(Spacer(1, 2*mm))
                content.append(Paragraph(
                    "<i>Hinweis: Farben wurden automatisch aus dem Design-Bild erkannt. "
                    "Finale Druckfarben können abweichen.</i>",
                    styles['Small']
                ))

            content.append(Spacer(1, 5*mm))

    # === PRÜF-HINWEISE ===
    content.append(Paragraph("<b>Bitte prüfen Sie vor der Freigabe:</b>", styles['Normal']))
    content.append(Spacer(1, 2*mm))

    # Typ-spezifische Prüfpunkte
    if design and design.design_type == 'stick':
        check_items = [
            "☐ Position auf dem Textil korrekt",
            "☐ Garnfarben stimmen",
            "☐ Größe ist passend",
            "☐ Texte/Schriften korrekt geschrieben",
        ]
    else:
        check_items = [
            "☐ Position auf dem Textil korrekt",
            "☐ Druckfarben stimmen",
            "☐ Größe ist passend",
            "☐ Texte/Schriften korrekt geschrieben",
        ]

    check_text = "    ".join(check_items)
    content.append(Paragraph(check_text, styles['Normal']))

    content.append(Spacer(1, 8*mm))

    # === FREIGABE-BEREICH ===
    content.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    content.append(Spacer(1, 5*mm))

    content.append(Paragraph("Freigabe durch den Kunden", styles['SectionHeader']))

    content.append(Paragraph(
        "Ich habe das oben gezeigte Design geprüft und bestätige, dass es meinen "
        "Vorstellungen entspricht. Mit meiner Unterschrift gebe ich das Design zur "
        "Produktion frei.",
        styles['Normal']
    ))
    content.append(Spacer(1, 3*mm))

    content.append(Paragraph(
        "<b>Hinweis:</b> Nach der Freigabe sind Änderungen am Design nicht mehr möglich.",
        styles['Small']
    ))

    content.append(Spacer(1, 8*mm))

    # Unterschriftsfelder
    signature_data = [
        ["☐  Design freigegeben", "☐  Änderungen gewünscht (siehe Rückseite)"],
    ]
    sig_table = Table(signature_data, colWidths=[85*mm, 85*mm])
    sig_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5*mm),
    ]))
    content.append(sig_table)

    content.append(Spacer(1, 10*mm))

    # Unterschrift und Datum
    signature_fields = [
        ["_" * 40, "_" * 25],
        ["Ort, Datum", "Unterschrift"],
    ]
    sig_fields_table = Table(signature_fields, colWidths=[85*mm, 85*mm])
    sig_fields_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 1), (-1, 1), 2*mm),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
        ('TEXTCOLOR', (0, 1), (-1, 1), colors.grey),
    ]))
    content.append(sig_fields_table)

    content.append(Spacer(1, 15*mm))

    # === FOOTER ===
    content.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    content.append(Spacer(1, 3*mm))

    footer_text = f"{company_name}"
    if company_settings:
        if company_settings.phone:
            footer_text += f" • Tel: {company_settings.phone}"
        if company_settings.email:
            footer_text += f" • {company_settings.email}"

    content.append(Paragraph(footer_text, styles['Footer']))
    content.append(Paragraph(
        f"Erstellt am {datetime.now().strftime('%d.%m.%Y um %H:%M Uhr')}",
        styles['Footer']
    ))

    # PDF generieren
    doc.build(content)

    if not output_path:
        buffer.seek(0)

    return buffer


def get_design_image_path(order, design, app_root):
    """
    Ermittelt den Pfad zum Design-Bild

    Args:
        order: Order-Objekt
        design: OrderDesign-Objekt (oder None)
        app_root: Flask app.root_path

    Returns:
        Vollständiger Dateipfad oder None
    """
    file_path = None

    if design and design.design_file_path:
        file_path = design.design_file_path
        logger.info(f"Design-Bild aus design.design_file_path: {file_path}")
    elif hasattr(order, 'design_file_path') and order.design_file_path:
        file_path = order.design_file_path
        logger.info(f"Design-Bild aus order.design_file_path: {file_path}")
    elif hasattr(order, 'design_file') and order.design_file:
        file_path = order.design_file
        logger.info(f"Design-Bild aus order.design_file: {file_path}")

    if not file_path:
        logger.warning("Kein Design-Bild-Pfad gefunden")
        return None

    # Pfad normalisieren (Windows Backslashes zu Forward Slashes)
    file_path = file_path.replace('\\', '/')
    logger.info(f"Normalisierter Pfad: {file_path}")

    # Mögliche Pfade durchprobieren
    # app_root könnte /mnt/c/.../StitchAdmin2.0 oder /mnt/c/.../StitchAdmin2.0/src sein
    base_dir = app_root
    if base_dir.endswith('src'):
        base_dir = os.path.dirname(base_dir)

    possible_paths = [
        # Standard: static/uploads/designs/...
        os.path.join(base_dir, 'static', 'uploads', file_path),
        os.path.join(base_dir, 'static', 'uploads', os.path.basename(file_path)),
        os.path.join(base_dir, 'static', 'uploads', 'designs', os.path.basename(file_path)),
        # Alternative: src/static/uploads/...
        os.path.join(base_dir, 'src', 'static', 'uploads', file_path),
        os.path.join(base_dir, 'src', 'static', 'uploads', os.path.basename(file_path)),
        # Alternative: uploads/designs/...
        os.path.join(base_dir, 'uploads', 'designs', os.path.basename(file_path)),
        # Direkt relativ
        os.path.join(base_dir, file_path),
        os.path.join(app_root, file_path),
        file_path,  # Absoluter Pfad
    ]

    for path in possible_paths:
        normalized_path = os.path.normpath(path)
        logger.debug(f"Prüfe Pfad: {normalized_path}")
        if os.path.exists(normalized_path):
            logger.info(f"Design-Bild gefunden: {normalized_path}")
            return normalized_path

    logger.warning(f"Design-Bild nicht gefunden. Geprüfte Pfade: {possible_paths}")
    return None
