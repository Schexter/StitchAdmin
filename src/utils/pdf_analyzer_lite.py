"""
PDF-Analyse Modul für Garnfarben-Extraktion (Minimale Version ohne pandas)
Extrahiert Farbtabellen aus PDF-Dateien verschiedener Hersteller
"""

import os
import re
import PyPDF2
import pdfplumber
from typing import List, Dict, Any, Optional

class ThreadColorPDFAnalyzerLite:
    """Analysiert PDF-Dateien und extrahiert Garnfarben-Informationen (ohne pandas/tabula)"""
    
    def __init__(self):
        self.color_patterns = {
            'hex': r'#[0-9A-Fa-f]{6}',
            'rgb': r'(?:rgb|RGB)\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)',
            'pantone': r'(?:Pantone|PANTONE|PMS)\s*(\d{3,4}[A-Z]?)',
            'madeira_number': r'(?:^|\s)(\d{4})(?:\s|$)',
            'gunold_number': r'(?:^|\s)(6\d{4})(?:\s|$)',
            'generic_color_number': r'(?:^|\s)(\d{3,5})(?:\s|$)'
        }
        
        # Häufige Farbnamen
        self.color_names = {
            'de': ['schwarz', 'weiß', 'weiss', 'rot', 'blau', 'grün', 'gruen', 'gelb', 
                   'orange', 'violett', 'pink', 'grau', 'braun', 'beige', 'gold', 
                   'silber', 'türkis', 'tuerkis', 'lila', 'rosa', 'dunkelblau', 
                   'hellblau', 'dunkelgrün', 'hellgrün', 'dunkelrot', 'hellrot'],
            'en': ['black', 'white', 'red', 'blue', 'green', 'yellow', 'orange', 
                   'violet', 'purple', 'pink', 'grey', 'gray', 'brown', 'beige', 
                   'gold', 'silver', 'turquoise', 'cyan', 'navy', 'light blue',
                   'dark blue', 'light green', 'dark green', 'maroon', 'coral']
        }
        
    def analyze_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Hauptmethode zur PDF-Analyse
        
        Returns:
            Dict mit:
            - success: bool
            - colors: List[Dict] - gefundene Farben
            - manufacturer: str - erkannter Hersteller
            - message: str - Status/Fehlermeldung
        """
        try:
            colors = []
            manufacturer = self._detect_manufacturer(pdf_path)
            
            # Text mit pdfplumber extrahieren
            text_colors = self._extract_from_text(pdf_path)
            colors.extend(text_colors)
            
            # Duplikate entfernen basierend auf Farbnummer
            unique_colors = self._remove_duplicates(colors)
            
            return {
                'success': True,
                'colors': unique_colors,
                'manufacturer': manufacturer,
                'colors_found': len(unique_colors),
                'message': f'{len(unique_colors)} Farben erfolgreich extrahiert'
            }
            
        except Exception as e:
            return {
                'success': False,
                'colors': [],
                'manufacturer': '',
                'colors_found': 0,
                'message': f'Fehler bei der PDF-Analyse: {str(e)}'
            }
    
    def _detect_manufacturer(self, pdf_path: str) -> str:
        """Versucht den Hersteller aus dem PDF zu erkennen"""
        manufacturers = {
            'madeira': ['madeira', 'madeirausa', 'madeira.de'],
            'gunold': ['gunold', 'günnold'],
            'mettler': ['mettler'],
            'isacord': ['isacord'],
            'robison': ['robison', 'robison-anton'],
            'sulky': ['sulky'],
            'brother': ['brother'],
            'polyneon': ['polyneon']
        }
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Prüfe erste Seite
                first_page_text = pdf.pages[0].extract_text().lower() if pdf.pages else ''
                
                for manufacturer, keywords in manufacturers.items():
                    for keyword in keywords:
                        if keyword in first_page_text:
                            return manufacturer.capitalize()
                            
        except:
            pass
            
        return 'Unbekannt'
    
    def _parse_table(self, table: List[List]) -> List[Dict]:
        """Parst eine Tabelle und extrahiert Farbinformationen"""
        colors = []
        
        if not table or len(table) < 2:
            return colors
        
        # Versuche Spalten zu identifizieren
        headers = []
        header_row = None
        
        # Finde Header-Zeile
        for i, row in enumerate(table[:5]):  # Nur erste 5 Zeilen prüfen
            if row and any(row):
                # Prüfe ob Zeile Header-Keywords enthält
                row_text = ' '.join([str(cell).lower() if cell else '' for cell in row])
                if any(keyword in row_text for keyword in ['color', 'farbe', 'nummer', 'number', 'name', 'pantone', 'hex']):
                    headers = [str(cell).lower() if cell else '' for cell in row]
                    header_row = i
                    break
        
        # Identifiziere Spalten-Indizes
        col_indices = {
            'number': -1,
            'name': -1,
            'hex': -1,
            'pantone': -1,
            'rgb': -1
        }
        
        if headers:
            for i, header in enumerate(headers):
                if any(term in header for term in ['nummer', 'number', 'no', 'code']):
                    col_indices['number'] = i
                elif any(term in header for term in ['name', 'bezeichnung', 'farbe']):
                    col_indices['name'] = i
                elif 'hex' in header:
                    col_indices['hex'] = i
                elif 'pantone' in header or 'pms' in header:
                    col_indices['pantone'] = i
                elif 'rgb' in header:
                    col_indices['rgb'] = i
        
        # Parse Datenzeilen
        start_row = header_row + 1 if header_row is not None else 0
        
        for row in table[start_row:]:
            if not row or not any(row):
                continue
            
            color_data = {
                'color_number': '',
                'color_name_de': '',
                'color_name_en': '',
                'hex_color': '',
                'pantone': ''
            }
            
            # Wenn wir Spalten identifiziert haben
            if col_indices['number'] >= 0:
                # Strukturierte Extraktion
                if col_indices['number'] < len(row) and row[col_indices['number']]:
                    number = str(row[col_indices['number']]).strip()
                    if re.match(r'^\d{3,5}$', number):
                        color_data['color_number'] = number
                
                if col_indices['name'] >= 0 and col_indices['name'] < len(row) and row[col_indices['name']]:
                    name = str(row[col_indices['name']]).strip()
                    # Erkenne Sprache
                    if any(de_word in name.lower() for de_word in self.color_names['de']):
                        color_data['color_name_de'] = name
                    else:
                        color_data['color_name_en'] = name
                
                if col_indices['hex'] >= 0 and col_indices['hex'] < len(row) and row[col_indices['hex']]:
                    hex_val = str(row[col_indices['hex']]).strip()
                    if re.match(self.color_patterns['hex'], hex_val):
                        color_data['hex_color'] = hex_val
                
                if col_indices['pantone'] >= 0 and col_indices['pantone'] < len(row) and row[col_indices['pantone']]:
                    color_data['pantone'] = str(row[col_indices['pantone']]).strip()
            
            else:
                # Fallback: Parse ganze Zeile
                row_text = ' '.join([str(cell) if cell else '' for cell in row])
                parsed = self._parse_text_line(row_text)
                if parsed:
                    color_data = parsed
            
            # Nur hinzufügen wenn Farbnummer vorhanden
            if color_data.get('color_number'):
                colors.append(color_data)
        
        return colors
    
    def _extract_from_text(self, pdf_path: str) -> List[Dict]:
        """Extrahiert Farben aus dem Fließtext"""
        colors = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # Versuche zuerst strukturierte Tabellen
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            table_colors = self._parse_table(table)
                            colors.extend(table_colors)
                    
                    # Dann normaler Text
                    text = page.extract_text()
                    if text:
                        # Verbesserte Zeilenerkennung
                        lines = text.split('\n')
                        
                        # Sammle zusammengehörige Zeilen
                        i = 0
                        while i < len(lines):
                            line = lines[i].strip()
                            
                            # Prüfe ob Zeile mit Farbnummer beginnt
                            if re.match(r'^\d{3,5}\s', line):
                                # Sammle nächste Zeilen die evtl. zur Farbe gehören
                                combined_line = line
                                j = i + 1
                                while j < len(lines) and j < i + 3:  # Max 3 Zeilen
                                    next_line = lines[j].strip()
                                    # Wenn nächste Zeile keine neue Farbnummer ist
                                    if not re.match(r'^\d{3,5}\s', next_line):
                                        combined_line += ' ' + next_line
                                        j += 1
                                    else:
                                        break
                                
                                color_data = self._parse_text_line(combined_line)
                                if color_data:
                                    colors.append(color_data)
                                i = j
                            else:
                                # Normale Zeile
                                color_data = self._parse_text_line(line)
                                if color_data:
                                    colors.append(color_data)
                                i += 1
                            
        except Exception as e:
            print(f"Text-Extraktion fehlgeschlagen: {e}")
            
        return colors
    
    def _parse_text_line(self, line: str) -> Optional[Dict]:
        """Parst eine Textzeile und extrahiert Farbinformationen"""
        line = line.strip()
        if not line:
            return None
            
        # Suche nach Farbnummer
        color_number = None
        
        # Verbesserte Muster für Madeira
        # Muster 1: Nummer am Zeilenanfang (auch 3-stellig)
        match = re.match(r'^(\d{3,5})\s*', line)
        if match:
            color_number = match.group(1)
            remaining_text = line[match.end():]
        else:
            # Muster 2: Madeira-spezifisch (z.B. "No. 1234" oder "Nr. 1234")
            match = re.search(r'(?:No\.|Nr\.|#)\s*(\d{3,5})', line, re.IGNORECASE)
            if match:
                color_number = match.group(1)
                remaining_text = line
            else:
                # Muster 3: Nummer irgendwo in der Zeile
                for pattern_name, pattern in self.color_patterns.items():
                    if pattern_name.endswith('_number'):
                        match = re.search(pattern, line)
                        if match:
                            color_number = match.group(1)
                            remaining_text = line
                            break
                else:
                    return None
        
        if not color_number:
            return None
            
        color_data = {
            'color_number': color_number,
            'color_name_de': '',
            'color_name_en': '',
            'hex_color': '',
            'pantone': ''
        }
        
        # Extrahiere Hex-Farbe
        hex_match = re.search(self.color_patterns['hex'], line)
        if hex_match:
            color_data['hex_color'] = hex_match.group(0)
        
        # Extrahiere Pantone
        pantone_match = re.search(self.color_patterns['pantone'], line)
        if pantone_match:
            color_data['pantone'] = pantone_match.group(0)
        
        # RGB zu Hex konvertieren
        rgb_match = re.search(self.color_patterns['rgb'], line)
        if rgb_match and not color_data['hex_color']:
            r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
            color_data['hex_color'] = f'#{r:02x}{g:02x}{b:02x}'
        
        # Extrahiere Farbnamen
        line_lower = line.lower()
        
        # Entferne bereits gefundene Muster für bessere Namenerkennung
        clean_text = line_lower
        clean_text = re.sub(r'\d+', '', clean_text)  # Entferne Zahlen
        clean_text = re.sub(self.color_patterns['hex'], '', clean_text)
        clean_text = re.sub(self.color_patterns['pantone'].lower(), '', clean_text)
        
        # Suche nach Farbnamen
        words = clean_text.split()
        for word in words:
            word = word.strip('.,;:!?()[]{}')
            if word in self.color_names['de']:
                color_data['color_name_de'] = word.capitalize()
                break
            elif word in self.color_names['en']:
                color_data['color_name_en'] = word.capitalize()
                break
        
        # Wenn kein Name gefunden, versuche längere Begriffe
        if not color_data['color_name_de'] and not color_data['color_name_en']:
            for name in self.color_names['de']:
                if name in clean_text:
                    color_data['color_name_de'] = name.capitalize()
                    break
            for name in self.color_names['en']:
                if name in clean_text:
                    color_data['color_name_en'] = name.capitalize()
                    break
        
        return color_data
    
    def _remove_duplicates(self, colors: List[Dict]) -> List[Dict]:
        """Entfernt Duplikate basierend auf Farbnummer"""
        seen = set()
        unique_colors = []
        
        for color in colors:
            key = color.get('color_number')
            if key and key not in seen:
                seen.add(key)
                unique_colors.append(color)
                
        return unique_colors