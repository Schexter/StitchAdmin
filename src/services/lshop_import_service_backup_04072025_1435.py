"""
L-Shop Import Service - REPARIERT mit vollständigem Spalten-Mapping
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime
from flask import current_app
from src.models import db, Article, ArticleVariant, ArticleSupplier, Supplier
from flask_login import current_user

class LShopImportService:
    """Service für L-Shop Excel-Import mit vollständigem Spalten-Mapping"""
    
    def __init__(self):
        self.excel_path = None
        self.header_row = None
        self.df = None
        
        # VOLLSTÄNDIGES StitchAdmin Spalten-Mapping
        self.stitchadmin_fields = {
            'supplier_article_number': 'Lieferanten-Artikelnummer',
            'article_number': 'StitchAdmin-Artikelnummer', 
            'name': 'Bezeichnung',
            'product_type': 'Produkttyp',
            'manufacturer': 'Hersteller/Marke',
            'manufacturer_number': 'Herstellernummer',
            'color': 'Farbe',
            'size': 'Größe',
            'material': 'Material',
            'weight': 'Gewicht',
            'ean': 'EAN/Barcode',
            'units_per_carton': 'VE/Karton',
            'single_price': 'Einzelpreis',
            'carton_price': 'Kartonpreis',
            'ten_carton_price': '10-Karton-Preis',
            'wholesale_price': 'Großhandelspreis',
            'recommended_price': 'UVP',
            'catalog_page': 'Katalogseite',
            'description': 'Beschreibung',
            'category': 'Kategorie',
            'brand': 'Marke',
            'collection': 'Kollektion',
            'season': 'Saison',
            'gender': 'Zielgruppe',
            'care_instructions': 'Pflegehinweise',
            'composition': 'Materialzusammensetzung',
            'country_of_origin': 'Herkunftsland',
            'minimum_order': 'Mindestbestellmenge',
            'delivery_time': 'Lieferzeit',
            'stock_status': 'Lagerstatus',
            'discontinued': 'Auslaufartikel',
            'new_article': 'Neuartikel',
            'special_price': 'Aktionspreis',
            'image_url': 'Bild-URL',
            'technical_drawing': 'Technische Zeichnung',
            'size_chart': 'Größentabelle'
        }
        
    def get_available_target_fields(self):
        """Gibt alle verfügbaren StitchAdmin-Zielfelder zurück"""
        return self.stitchadmin_fields
        
    def get_column_mapping_preview(self):
        """Erstellt eine Vorschau für das Spalten-Mapping mit Beispieldaten"""
        if self.df is None:
            return {}
            
        preview = {}
        auto_mapping = self.get_default_column_mapping()
        
        for source_col in self.df.columns:
            # Konvertiere Beispielwerte zu Python-nativen Typen für JSON-Serialisierung
            sample_values = self.df[source_col].dropna().head(3).tolist()
            # Konvertiere pandas-Typen zu Python-nativen Typen
            sample_values = [self._convert_to_json_serializable(val) for val in sample_values]
            
            col_data = {
                'column_name': str(source_col),
                'sample_values': sample_values,
                'suggested_mapping': None,
                'data_type': str(self.df[source_col].dtype),
                'non_null_count': int(self.df[source_col].count()),
                'total_count': int(len(self.df))
            }
            
            # Finde vorgeschlagenes Mapping
            for target_field, mapped_col in auto_mapping.items():
                if mapped_col == source_col:
                    col_data['suggested_mapping'] = target_field
                    break
                    
            preview[str(source_col)] = col_data
            
        return preview
    
    def _convert_to_json_serializable(self, value):
        """Konvertiert pandas-Datentypen zu JSON-serialisierbaren Python-Typen"""
        if pd.isna(value):
            return None
        elif isinstance(value, (np.integer, np.int64, np.int32)):
            return int(value)
        elif isinstance(value, (np.floating, np.float64, np.float32)):
            return float(value)
        elif isinstance(value, np.bool_):
            return bool(value)
        elif isinstance(value, (np.datetime64, pd.Timestamp)):
            return str(value)
        else:
            return str(value)
    
    def get_default_column_mapping(self):
        """Intelligentes automatisches Mapping für L-Shop Spalten"""
        if self.df is None:
            return {}
            
        mapping = {}
        
        # L-Shop spezifische Spalten-Erkennung
        for idx, col in enumerate(self.df.columns):
            col_clean = str(col).strip()
            col_lower = col_clean.lower()
            
            # LIEFERANTEN-ARTIKELNUMMER (Wichtigster Fall!)
            if ('art. nr.:' in col_clean or 'art.nr.' in col_clean or 
                col_clean == 'Artnr.' or col_clean == 'Art.-Nr.' or
                'artikelnummer' in col_lower):
                mapping['supplier_article_number'] = col_clean
                
            # BEZEICHNUNG/NAME
            elif (col_clean == 'Artikel' or col_clean == 'Bezeichnung' or
                  col_clean == 'Name' or col_clean == 'Produktname'):
                mapping['name'] = col_clean
                
            # PRODUKTTYP
            elif (col_clean == 'Produktart' or col_clean == 'Produkttyp' or
                  col_clean == 'Typ' or col_clean == 'Art'):
                mapping['product_type'] = col_clean
                
            # HERSTELLER/MARKE
            elif (col_clean == 'Marke' or col_clean == 'Hersteller' or
                  col_clean == 'Brand' or col_clean == 'Manufacturer'):
                mapping['manufacturer'] = col_clean
                
            # HERSTELLERNUMMER
            elif ('herst' in col_lower and 'nr' in col_lower):
                mapping['manufacturer_number'] = col_clean
                
            # FARBE
            elif col_clean == 'Farbe' or col_clean == 'Color':
                mapping['color'] = col_clean
                
            # GRÖSSE
            elif col_clean == 'Größe' or col_clean == 'Size':
                mapping['size'] = col_clean
                
            # VERPACKUNGSEINHEIT
            elif ('ve' in col_lower and ('kart' in col_lower or 'carton' in col_lower)):
                mapping['units_per_carton'] = col_clean
            elif col_clean == 'VE' or col_clean == 'Verpackungseinheit':
                mapping['units_per_carton'] = col_clean
                
            # EINZELPREIS
            elif (col_clean == 'Einzelpreis' or col_clean == 'Einzel' or
                  'single' in col_lower):
                mapping['single_price'] = col_clean
                
            # KARTONPREIS
            elif (col_clean == 'Kartonpreis' or col_clean == 'Karton' or
                  'carton' in col_lower):
                mapping['carton_price'] = col_clean
                
            # 10-KARTON-PREIS
            elif ('10' in col_clean and ('kart' in col_lower or 'carton' in col_lower)):
                mapping['ten_carton_price'] = col_clean
                
            # EAN/BARCODE
            elif (col_clean == 'EAN' or col_clean == 'Barcode' or
                  col_clean == 'GTIN'):
                mapping['ean'] = col_clean
                
            # MATERIAL
            elif (col_clean == 'Material' or col_clean == 'Stoff' or
                  col_clean == 'Zusammensetzung'):
                mapping['material'] = col_clean
                
            # GEWICHT
            elif col_clean == 'Gewicht' or col_clean == 'Weight':
                mapping['weight'] = col_clean
                
            # KATALOGSEITE
            elif 'katalog' in col_lower:
                mapping['catalog_page'] = col_clean
                
            # BESCHREIBUNG
            elif (col_clean == 'Beschreibung' or col_clean == 'Description' or
                  col_clean == 'Details'):
                mapping['description'] = col_clean
        
        return mapping
    
    def validate_data(self):
        """Validiert die Excel-Daten vor dem Import"""
        if self.df is None:
            return {'valid': False, 'errors': ['Keine Daten geladen']}
            
        errors = []
        warnings = []
        valid_rows = 0
        
        for index, row in self.df.iterrows():
            # Skip komplett leere Zeilen
            if row.isna().all():
                continue
                
            row_valid = True
            
            # Prüfe Pflichtfelder (falls Mapping bereits gesetzt)
            if hasattr(self, 'column_mapping') and self.column_mapping:
                # Artikelnummer oder Name erforderlich
                has_article_info = False
                for field in ['supplier_article_number', 'article_number', 'name']:
                    if (field in self.column_mapping and 
                        self.column_mapping[field] in row and
                        pd.notna(row[self.column_mapping[field]]) and
                        str(row[self.column_mapping[field]]).strip()):
                        has_article_info = True
                        break
                        
                if not has_article_info:
                    errors.append(f'Zeile {index+1}: Artikelnummer oder Bezeichnung fehlt')
                    row_valid = False
            
            if row_valid:
                valid_rows += 1
                
        return {
            'valid': len(errors) == 0,
            'errors': errors[:10],  # Nur erste 10 Fehler
            'warnings': warnings,
            'valid_rows': valid_rows,
            'total_rows': len(self.df)
        }
        
    def analyze_excel(self, file_path):
        """Analysiert L-Shop Excel und gibt Struktur zurück"""
        try:
            # Versuche verschiedene Header-Positionen
            header_row = None
            df = None
            
            # Teste Header in Zeilen 0-10
            for row in range(11):
                try:
                    test_df = pd.read_excel(file_path, header=row, engine='openpyxl')
                    if len(test_df.columns) > 5:  # Mindestens 5 Spalten
                        # Prüfe ob sinnvolle Spaltennamen vorhanden
                        col_names = [str(col).lower() for col in test_df.columns]
                        if any(keyword in ' '.join(col_names) for keyword in 
                               ['art', 'artikel', 'bezeichnung', 'marke', 'preis']):
                            header_row = row
                            df = test_df
                            break
                except:
                    continue
            
            if df is None:
                # Fallback: Erste Zeile als Header
                df = pd.read_excel(file_path, header=0, engine='openpyxl')
                header_row = 0
            
            self.df = df
            self.header_row = header_row
            self.excel_path = file_path
            
            # Automatisches Mapping generieren
            auto_mapping = self.get_default_column_mapping()
            
            return {
                'success': True,
                'header_row': header_row,
                'total_rows': len(df),
                'columns': list(df.columns),
                'preview_data': df.head(5).to_dict('records'),
                'auto_mapping': auto_mapping,
                'available_fields': self.stitchadmin_fields,
                'sample_values': {col: df[col].dropna().head(3).tolist() 
                                for col in df.columns if not df[col].dropna().empty}
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': f'Fehler beim Analysieren der Excel-Datei: {e}'
            }
    
    def validate_data(self):
        """Validiert die Excel-Daten vor dem Import"""
        if self.df is None:
            return {'valid': False, 'errors': ['Keine Daten geladen']}
            
        errors = []
        warnings = []
        valid_rows = 0
        
        for index, row in self.df.iterrows():
            # Skip komplett leere Zeilen
            if row.isna().all():
                continue
                
            row_valid = True
            
            # Prüfe auf mindestens einen wichtigen Wert
            important_cols = ['Artikel', 'Art. Nr.:', 'Name', 'Bezeichnung']
            has_important_data = False
            
            for col in important_cols:
                if col in row and pd.notna(row[col]) and str(row[col]).strip():
                    has_important_data = True
                    break
                    
            if not has_important_data:
                warnings.append(f'Zeile {index+1}: Keine wichtigen Daten gefunden')
                row_valid = False
                
            if row_valid:
                valid_rows += 1
                
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'valid_rows': valid_rows,
            'total_rows': len(self.df)
        }
        
    def get_import_preview(self, limit=50):
        """Erstellt eine Vorschau der zu importierenden Artikel"""
        if self.df is None:
            return []
            
        preview = []
        auto_mapping = self.get_default_column_mapping()
        
        for index, row in self.df.head(limit).iterrows():
            # Skip leere Zeilen
            if row.isna().all():
                continue
                
            preview_item = {
                'row_number': index + 1,
                'mapped_data': {},
                'raw_data': {}
            }
            
            # Rohdaten für Anzeige
            for col in self.df.columns:
                if pd.notna(row[col]):
                    preview_item['raw_data'][col] = str(row[col]).strip()
                    
            # Gemappte Daten
            for target_field, source_col in auto_mapping.items():
                if source_col in row and pd.notna(row[source_col]):
                    value = str(row[source_col]).strip()
                    if value:
                        preview_item['mapped_data'][target_field] = value
                        
            # Generiere Artikelnummer falls nicht vorhanden
            if not preview_item['mapped_data'].get('article_number'):
                if preview_item['mapped_data'].get('supplier_article_number'):
                    base_number = preview_item['mapped_data']['supplier_article_number']
                    preview_item['mapped_data']['article_number'] = f"SA-{base_number}"
                else:
                    date_str = datetime.now().strftime('%Y%m%d')
                    preview_item['mapped_data']['article_number'] = f"SA-{date_str}-{len(preview)+1:04d}"
                    
            preview.append(preview_item)
            
        return preview
    
    def import_articles(self, column_mapping, options=None):
        """Importiert Artikel mit dem gegebenen Spalten-Mapping"""
        if self.df is None:
            return {'success': False, 'error': 'Keine Excel-Daten verfügbar'}
        
        try:
            imported_count = 0
            skipped_count = 0
            error_count = 0
            errors = []
            
            # DEBUG: Zeige Mapping-Info
            print(f"DEBUG: Column Mapping: {column_mapping}")
            print(f"DEBUG: DataFrame Columns: {list(self.df.columns)}")
            
            for index, row in self.df.iterrows():
                try:
                    # Skip leere Zeilen
                    if row.isna().all():
                        skipped_count += 1
                        continue
                    
                    # Erstelle Artikel-Daten basierend auf Mapping
                    article_data = {}
                    
                    for target_field, source_column in column_mapping.items():
                        if source_column:
                            # Konvertiere Index zu Spaltenname falls nötig
                            if source_column.isdigit():
                                col_index = int(source_column)
                                if col_index < len(self.df.columns):
                                    column_name = self.df.columns[col_index]
                                else:
                                    continue
                            else:
                                column_name = source_column
                                
                            if column_name in self.df.columns:
                                value = row[column_name]
                                if pd.notna(value) and str(value).strip():
                                    article_data[target_field] = str(value).strip()
                    
                    # DEBUG für erste 3 Zeilen
                    if index < 3:
                        print(f"DEBUG Zeile {index+1}: Extracted Data: {article_data}")
                    
                    # Verbesserte Validierung
                    has_required_data = bool(
                        article_data.get('supplier_article_number') or 
                        article_data.get('name')
                    )
                    
                    if not has_required_data:
                        if index < 3:  # Debug nur für erste Zeilen
                            print(f"DEBUG: Zeile {index+1} übersprungen - keine Pflichtdaten")
                        skipped_count += 1
                        continue
                    
                    # Generiere StitchAdmin-Artikelnummer falls nicht vorhanden
                    if not article_data.get('article_number'):
                        if article_data.get('supplier_article_number'):
                            # Verwende Lieferanten-Artikelnummer als Basis
                            base_number = article_data['supplier_article_number']
                            article_data['article_number'] = f"SA-{base_number}"
                        else:
                            # Generiere neue Nummer
                            date_str = datetime.now().strftime('%Y%m%d')
                            article_data['article_number'] = f"SA-{date_str}-{imported_count+1:04d}"
                    
                    # DEBUG für erste 3 Artikel
                    if index < 3:
                        print(f"DEBUG: Versuche Artikel zu erstellen - {article_data.get('article_number')} - {article_data.get('name')}")
                    
                    # Prüfe ob Artikel bereits existiert
                    existing_article = None
                    if article_data.get('supplier_article_number'):
                        existing_article = Article.query.filter_by(
                            supplier_article_number=article_data['supplier_article_number']
                        ).first()
                    
                    if not existing_article and article_data.get('article_number'):
                        existing_article = Article.query.filter_by(
                            article_number=article_data['article_number']
                        ).first()
                    
                    if existing_article:
                        # Update bestehenden Artikel
                        for field, value in article_data.items():
                            if hasattr(existing_article, field):
                                setattr(existing_article, field, value)
                        existing_article.updated_at = datetime.utcnow()
                    else:
                        # Erstelle neuen Artikel
                        if index < 3:
                            print(f"DEBUG: Erstelle neuen Artikel: {article_data.get('article_number')}")
                            
                        article = Article(
                            article_number=article_data.get('article_number'),
                            supplier_article_number=article_data.get('supplier_article_number'),
                            name=article_data.get('name', 'Unbenannter Artikel'),
                            manufacturer=article_data.get('manufacturer'),
                            manufacturer_number=article_data.get('manufacturer_number'),
                            color=article_data.get('color'),
                            size=article_data.get('size'),
                            material=article_data.get('material'),
                            ean=article_data.get('ean'),
                            units_per_carton=self._safe_int(article_data.get('units_per_carton')),
                            purchase_price_single=self._safe_float(article_data.get('single_price')),
                            purchase_price_carton=self._safe_float(article_data.get('carton_price')),
                            purchase_price_10carton=self._safe_float(article_data.get('ten_carton_price')),
                            description=article_data.get('description'),
                            import_source='L-Shop',
                            import_reference=f"Row {index+1}",
                            last_import_update=datetime.utcnow(),
                            created_by=current_user.username if current_user.is_authenticated else 'System',
                            active=True
                        )
                        db.session.add(article)
                        
                        if index < 3:
                            print(f"DEBUG: Artikel zur Session hinzugefügt: {article.article_number}")
                    
                    imported_count += 1
                    
                    # Commit in Batches
                    if imported_count % 50 == 0:
                        db.session.commit()
                
                except Exception as e:
                    error_count += 1
                    errors.append(f"Zeile {index+1}: {str(e)}")
                    continue
            
            # Final commit
            print(f"DEBUG: Final Commit - {imported_count} Artikel verarbeitet")
            db.session.commit()
            print(f"DEBUG: Commit erfolgreich!")
            
            return {
                'success': True,
                'imported_count': imported_count,
                'skipped_count': skipped_count,
                'error_count': error_count,
                'errors': errors[:10],  # Nur erste 10 Fehler zeigen
                'total_processed': len(self.df)
            }
            
        except Exception as e:
            db.session.rollback()
            return {
                'success': False,
                'error': str(e),
                'message': f'Fehler beim Import: {e}'
            }
    
    def _safe_int(self, value):
        """Sichere Integer-Konvertierung"""
        if value is None or value == '':
            return None
        try:
            return int(float(str(value)))
        except:
            return None
    
    def _safe_float(self, value):
        """Sichere Float-Konvertierung"""
        if value is None or value == '':
            return None
        try:
            # Ersetze Komma durch Punkt für deutsche Zahlen
            value_str = str(value).replace(',', '.')
            return float(value_str)
        except:
            return None
