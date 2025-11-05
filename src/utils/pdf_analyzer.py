"""
PDF-Analyse Modul für Garnfarben-Extraktion
Extrahiert Farbtabellen aus PDF-Dateien verschiedener Hersteller
"""

import os
import re
import PyPDF2
import pdfplumber
import tabula
import pandas as pd
from typing import List, Dict, Any, Optional

class ThreadColorPDFAnalyzer:
    """Analysiert PDF-Dateien und extrahiert Garnfarben-Informationen"""
    
    def __init__(self):
        self.color_patterns = {
            'hex': r'#[0-9A-Fa-f]{6}',
            'rgb': r'(?:rgb|RGB)\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)',
            'pantone': r'(?:Pantone|PANTONE|PMS)\s*(\d{3,4}[A-Z]?)',
            'madeira_number': r'(?:^|\s)(\d{4})(?:\s|$)',
            'gunold_number': r'(?:^|\s)(6\d{4})(?:\s|$)',  # Gunold oft mit 6 beginnend
            'generic_color_number': r'(?:^|\s)(\d{3,5})(?:\s|$)'
        }
        
        # Häufige Farbnamen
        self.color_names = {
            'de': ['schwarz', 'weiß', 'weiss', 'rot', 'blau', 'grün', 'gruen', 'gelb', 
                   'orange', 'violett', 'pink', 'grau', 'braun', 'beige', 'gold', 
                   'silber', 'türkis', 'tuerkis'],
            'en': ['black', 'white', 'red', 'blue', 'green', 'yellow', 'orange', 
                   'violet', 'purple', 'pink', 'grey', 'gray', 'brown', 'beige', 
                   'gold', 'silver', 'turquoise', 'cyan']
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
            # Versuche verschiedene Extraktionsmethoden
            colors = []
            manufacturer = self._detect_manufacturer(pdf_path)
            
            # Methode 1: Tabellen mit tabula extrahieren
            table_colors = self._extract_from_tables(pdf_path)
            colors.extend(table_colors)
            
            # Methode 2: Text mit pdfplumber extrahieren
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
    
    def _extract_from_tables(self, pdf_path: str) -> List[Dict]:
        """Extrahiert Farben aus Tabellen im PDF"""
        colors = []
        
        try:
            # Extrahiere alle Tabellen
            tables = tabula.read_pdf(pdf_path, pages='all', multiple_tables=True, 
                                   pandas_options={'header': None})
            
            for table_idx, df in enumerate(tables):
                if df.empty:
                    continue
                    
                # Versuche Spalten zu identifizieren
                for idx, row in df.iterrows():
                    color_data = self._parse_table_row(row)
                    if color_data:
                        colors.append(color_data)
                        
        except Exception as e:
            print(f"Tabellen-Extraktion fehlgeschlagen: {e}")
            
        return colors
    
    def _extract_from_text(self, pdf_path: str) -> List[Dict]:
        """Extrahiert Farben aus dem Fließtext"""
        colors = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    # Suche nach Farbmustern in jeder Zeile
                    lines = text.split('\n')
                    for line in lines:
                        color_data = self._parse_text_line(line)
                        if color_data:
                            colors.append(color_data)
                            
        except Exception as e:
            print(f"Text-Extraktion fehlgeschlagen: {e}")
            
        return colors
    
    def _parse_table_row(self, row: pd.Series) -> Optional[Dict]:
        """Parst eine Tabellenzeile und extrahiert Farbinformationen"""
        row_text = ' '.join([str(cell) for cell in row if pd.notna(cell)])
        
        # Suche nach Farbnummer
        color_number = None
        for pattern_name, pattern in self.color_patterns.items():
            if pattern_name.endswith('_number'):
                match = re.search(pattern, row_text)
                if match:
                    color_number = match.group(1)
                    break
        
        if not color_number:
            return None
            
        # Extrahiere weitere Informationen
        color_data = {
            'color_number': color_number,
            'color_name_de': '',
            'color_name_en': '',
            'hex_color': '',
            'pantone': ''
        }
        
        # Suche Hex-Farbe
        hex_match = re.search(self.color_patterns['hex'], row_text)
        if hex_match:
            color_data['hex_color'] = hex_match.group(0)
        
        # Suche Pantone
        pantone_match = re.search(self.color_patterns['pantone'], row_text)
        if pantone_match:
            color_data['pantone'] = pantone_match.group(0)
        
        # Suche Farbnamen
        row_lower = row_text.lower()
        for lang, names in self.color_names.items():
            for name in names:
                if name in row_lower:
                    if lang == 'de':
                        color_data['color_name_de'] = name.capitalize()
                    else:
                        color_data['color_name_en'] = name.capitalize()
                    break
        
        return color_data if any([color_data['hex_color'], color_data['pantone'], 
                                  color_data['color_name_de'], color_data['color_name_en']]) else None
    
    def _parse_text_line(self, line: str) -> Optional[Dict]:
        """Parst eine Textzeile und extrahiert Farbinformationen"""
        # Ähnlich wie _parse_table_row, aber für Fließtext optimiert
        line = line.strip()
        if not line:
            return None
            
        # Suche nach Farbnummer am Zeilenanfang
        color_number_match = re.match(r'^(\d{3,5})\s+', line)
        if not color_number_match:
            return None
            
        color_number = color_number_match.group(1)
        remaining_text = line[color_number_match.end():]
        
        color_data = {
            'color_number': color_number,
            'color_name_de': '',
            'color_name_en': '',
            'hex_color': '',
            'pantone': ''
        }
        
        # Extrahiere Hex-Farbe
        hex_match = re.search(self.color_patterns['hex'], remaining_text)
        if hex_match:
            color_data['hex_color'] = hex_match.group(0)
        
        # Extrahiere Pantone
        pantone_match = re.search(self.color_patterns['pantone'], remaining_text)
        if pantone_match:
            color_data['pantone'] = pantone_match.group(0)
        
        # RGB zu Hex konvertieren
        rgb_match = re.search(self.color_patterns['rgb'], remaining_text)
        if rgb_match and not color_data['hex_color']:
            r, g, b = int(rgb_match.group(1)), int(rgb_match.group(2)), int(rgb_match.group(3))
            color_data['hex_color'] = f'#{r:02x}{g:02x}{b:02x}'
        
        # Extrahiere Farbnamen
        # Entferne bereits gefundene Muster
        clean_text = remaining_text
        for pattern in [self.color_patterns['hex'], self.color_patterns['pantone'], 
                       self.color_patterns['rgb']]:
            clean_text = re.sub(pattern, '', clean_text)
        
        # Suche nach Farbnamen
        words = clean_text.lower().split()
        for word in words:
            if word in self.color_names['de']:
                color_data['color_name_de'] = word.capitalize()
                break
            elif word in self.color_names['en']:
                color_data['color_name_en'] = word.capitalize()
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
    
    def _rgb_to_hex(self, r: int, g: int, b: int) -> str:
        """Konvertiert RGB zu Hex"""
        return f'#{r:02x}{g:02x}{b:02x}'