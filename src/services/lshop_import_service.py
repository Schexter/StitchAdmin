"""
L-Shop Import Service - REPARIERT mit ID-Generierung
Erstellt von Hans Hahn - Alle Rechte vorbehalten

PROBLEM IDENTIFIZIERT:
- Artikel werden nicht in die Datenbank importiert
- Debug zeigt "Final Commit - 0 Artikel verarbeitet"  
- Artikel werden erstellt aber nicht persistiert

URSACHE:
- Article-Model erwartet ein 'id' Feld für Primary Key
- LShop-Import setzt nur 'article_number' aber nicht 'id'
- SQLAlchemy kann Artikel nicht speichern ohne Primary Key

LÖSUNG:
- Automatische ID-Generierung bei Artikel-Erstellung
- Verwendung der generate_article_id() Funktion aus Controller
- Korrekte Zuordnung von ID und article_number

REPARATUR-DATUM: 04.07.2025 14:35 Uhr
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime
from flask import current_app
from src.models import db, Article, ArticleVariant, ArticleSupplier, Supplier, Brand, ProductCategory
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
        
    def generate_article_id(self):
        """Generiere neue Artikel-ID für StitchAdmin - KOMPLETT NEU"""
        import uuid
        from datetime import datetime
        
        # STRATEGIE 1: Timestamp-basierte ID (Sekunden seit Epoche)
        timestamp = int(datetime.now().timestamp())
        candidate_id = f"ART{timestamp % 999999:06d}"  # Letzte 6 Stellen
        
        # Prüfe ob diese ID bereits existiert
        existing = Article.query.filter_by(id=candidate_id).first()
        if not existing:
            return candidate_id
        
        # STRATEGIE 2: UUID-basierte ID (falls Timestamp belegt)
        uuid_str = str(uuid.uuid4()).replace('-', '')[:8]
        candidate_id = f"ART{uuid_str[:6].upper()}"
        
        existing = Article.query.filter_by(id=candidate_id).first()
        if not existing:
            return candidate_id
        
        # STRATEGIE 3: Millisekunden-basiert (letzte Option)
        millis = int(datetime.now().timestamp() * 1000)
        candidate_id = f"ART{millis % 999999:06d}"
        
        # Falls auch das belegt ist, füge Zufallszahl hinzu
        import random
        for i in range(100):  # Max 100 Versuche
            random_suffix = random.randint(1000, 9999)
            candidate_id = f"ART{random_suffix:04d}{i:02d}"
            existing = Article.query.filter_by(id=candidate_id).first()
            if not existing:
                return candidate_id
        
        # Absoluter Fallback: UUID
        return f"ART{str(uuid.uuid4())[:8].replace('-', '').upper()}"
        
    def create_or_get_brand(self, brand_name):
        """Erstelle oder hole Brand-Objekt"""
        if not brand_name or brand_name.strip() == '':
            return None
        
        brand_name = brand_name.strip()
        brand = Brand.query.filter_by(name=brand_name).first()
        if not brand:
            brand = Brand(
                name=brand_name,
                active=True,
                created_by=current_user.username if current_user and current_user.is_authenticated else 'L-Shop Import',
                created_at=datetime.utcnow()
            )
            db.session.add(brand)
            try:
                db.session.flush()  # Um ID zu erhalten ohne full commit
            except:
                pass  # Falls flush fehlschlägt, wird bei commit behandelt
        return brand

    def create_or_get_category(self, category_name):
        """Erstelle oder hole ProductCategory-Objekt"""
        if not category_name or category_name.strip() == '':
            return None
        
        category_name = category_name.strip()
        category = ProductCategory.query.filter_by(name=category_name).first()
        if not category:
            category = ProductCategory(
                name=category_name,
                active=True,
                sort_order=999,
                created_by=current_user.username if current_user and current_user.is_authenticated else 'L-Shop Import',
                created_at=datetime.utcnow()
            )
            db.session.add(category)
            try:
                db.session.flush()  # Um ID zu erhalten ohne full commit
            except:
                pass  # Falls flush fehlschlägt, wird bei commit behandelt
        return category
        
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
                
            # VE/KARTON
            elif (col_clean == 'VE/Kart.' or col_clean == 'VE' or 
                  'karton' in col_lower or 've' in col_lower):
                mapping['units_per_carton'] = col_clean
                
            # FARBE
            elif col_clean == 'Farbe' or col_clean == 'Color':
                mapping['color'] = col_clean
                
            # GRÖßE
            elif col_clean == 'Größe' or col_clean == 'Size':
                mapping['size'] = col_clean
                
            # PREISE - L-Shop spezifisch
            elif col_clean == 'Einzel':
                mapping['single_price'] = col_clean
            elif col_clean == 'Karton':
                mapping['carton_price'] = col_clean
            elif col_clean == '10 Kart':
                mapping['ten_carton_price'] = col_clean
                
            # Weitere Preise
            elif 'einzelpreis' in col_lower:
                mapping['single_price'] = col_clean
            elif 'kartonpreis' in col_lower:
                mapping['carton_price'] = col_clean
            elif '10' in col_clean and 'karton' in col_lower:
                mapping['ten_carton_price'] = col_clean
                
        return mapping
    
    def analyze_excel(self, file_path):
        """Analysiert Excel-Datei und ermittelt Header-Zeile"""
        try:
            # Versuche verschiedene Header-Zeilen zu finden
            df = None
            header_row = None
            
            # Teste die ersten 10 Zeilen als mögliche Header
            for row in range(10):
                try:
                    test_df = pd.read_excel(file_path, header=row, engine='openpyxl')
                    if len(test_df.columns) > 3 and len(test_df) > 1:
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
        """Importiert Artikel mit dem gegebenen Spalten-Mapping - REPARIERT"""
        if self.df is None:
            return {'success': False, 'error': 'Keine Excel-Daten verfügbar'}
        
        try:
            imported_count = 0
            updated_count = 0
            skipped_count = 0
            error_count = 0
            errors = []
            
            # *** REPARATUR: Session-Rollback bei Beginn ***
            try:
                db.session.rollback()  # Bereinige vorherige Fehler
            except:
                pass
            
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
                    
                    # *** REPARATUR: ID-Generierung ***
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
                    
                    # *** NEUE EINFACHE ID-GENERIERUNG ***
                    article_id = self.generate_article_id()
                    
                    # DEBUG für erste 3 Artikel
                    if index < 3:
                        print(f"DEBUG: Versuche Artikel zu erstellen - {article_id} - {article_data.get('article_number')} - {article_data.get('name')}")
                    
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
                        updated_count += 1
                        
                        if index < 3:
                            print(f"DEBUG: Artikel aktualisiert: {existing_article.id}")
                    else:
                        # *** REPARATUR: Erstelle neuen Artikel mit korrekter ID ***
                        if index < 3:
                            print(f"DEBUG: Erstelle neuen Artikel: {article_id}")
                        
                        # *** NEUE REPARATUR: Erstelle Marken und Kategorien automatisch ***
                        brand_obj = self.create_or_get_brand(article_data.get('manufacturer'))
                        category_obj = self.create_or_get_category(article_data.get('category'))
                            
                        article = Article(
                            id=article_id,  # *** REPARATUR: ID explizit setzen ***
                            article_number=article_data.get('article_number'),
                            supplier_article_number=article_data.get('supplier_article_number'),
                            name=article_data.get('name', 'Unbenannter Artikel'),
                            product_type=article_data.get('product_type'),
                            brand=article_data.get('manufacturer'),  # *** REPARATUR: manufacturer → brand ***
                            brand_id=brand_obj.id if brand_obj else None,  # *** NEU: Foreign Key ***
                            category=article_data.get('category'),  # String (legacy)
                            category_id=category_obj.id if category_obj else None,  # *** NEU: Foreign Key ***
                            manufacturer_number=article_data.get('manufacturer_number'),
                            color=article_data.get('color'),
                            size=article_data.get('size'),
                            material=article_data.get('material'),
                            units_per_carton=self._safe_int(article_data.get('units_per_carton')),
                            purchase_price_single=self._safe_float(article_data.get('single_price')),
                            purchase_price_carton=self._safe_float(article_data.get('carton_price')),
                            purchase_price_10carton=self._safe_float(article_data.get('ten_carton_price')),
                            description=article_data.get('description'),
                            supplier='L-Shop',
                            active=True,
                            stock=0,
                            min_stock=0,
                            price=0,  # Wird später kalkuliert
                            weight=0,
                            created_by=current_user.username if current_user and current_user.is_authenticated else 'L-Shop Import',
                            created_at=datetime.utcnow()
                        )
                        
                        # Kalkuliere Preise falls EK-Preise vorhanden
                        if article.purchase_price_single > 0:
                            try:
                                article.calculate_prices()
                            except:
                                # Fallback: Einfache Kalkulation
                                article.price = article.purchase_price_single * 2.0
                        
                        db.session.add(article)
                        imported_count += 1
                        
                        if index < 3:
                            print(f"DEBUG: Artikel zur Session hinzugefügt: {article.id} - {article.article_number}")
                    
                    # Commit in Batches mit Fehlerbehandlung
                    if (imported_count + updated_count) % 50 == 0:
                        try:
                            db.session.commit()
                            if index < 200:  # Debug für erste 200 Zeilen
                                print(f"DEBUG: Batch-Commit bei Zeile {index+1} erfolgreich")
                        except Exception as commit_error:
                            db.session.rollback()
                            error_count += 1
                            error_msg = f"Batch-Commit Fehler bei Zeile {index+1}: {str(commit_error)}"
                            errors.append(error_msg)
                            print(f"DEBUG COMMIT ERROR: {error_msg}")
                
                except Exception as e:
                    error_count += 1
                    error_msg = f"Zeile {index+1}: {str(e)}"
                    errors.append(error_msg)
                    print(f"DEBUG ERROR: {error_msg}")
                    continue
            
            # Final commit
            print(f"DEBUG: Final Commit - {imported_count} neue Artikel, {updated_count} aktualisiert")
            db.session.commit()
            print(f"DEBUG: Commit erfolgreich!")
            
            return {
                'success': True,
                'imported_count': imported_count,
                'updated_count': updated_count,
                'skipped_count': skipped_count,
                'error_count': error_count,
                'errors': errors[:10],  # Nur erste 10 Fehler zeigen
                'total_processed': len(self.df)
            }
            
        except Exception as e:
            db.session.rollback()
            error_msg = f'Fehler beim Import: {e}'
            print(f"DEBUG CRITICAL ERROR: {error_msg}")
            return {
                'success': False,
                'error': str(e),
                'message': error_msg
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
