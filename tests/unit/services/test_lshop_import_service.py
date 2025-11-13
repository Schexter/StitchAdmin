"""
Unit Tests für L-Shop Import Service
Testet den Excel-Import von L-Shop Artikeldaten
"""

import pytest
import pandas as pd
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from src.services.lshop_import_service import LShopImportService
from src.models.models import Article, Brand, ProductCategory, Supplier


@pytest.fixture
def import_service(app):
    """Fixture für LShopImportService"""
    with app.app_context():
        service = LShopImportService()
        yield service


@pytest.fixture
def sample_excel_file():
    """Fixture für temporäre Excel-Testdatei"""
    # Erstelle temporäre Excel-Datei
    temp_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.xlsx')

    # Beispiel-Daten
    data = {
        'Artikelnummer': ['ART001', 'ART002', 'ART003'],
        'Bezeichnung': ['T-Shirt Weiß', 'Polo Blau', 'Hoodie Schwarz'],
        'Hersteller': ['Fruit of the Loom', 'Gildan', 'Fruit of the Loom'],
        'Farbe': ['Weiß', 'Blau', 'Schwarz'],
        'Größe': ['M', 'L', 'XL'],
        'Einzelpreis': ['8.50', '12.30', '25.00'],
        'Kartonpreis': ['7.20', '10.50', '22.00'],
        'EAN': ['4260123456789', '4260123456790', '4260123456791'],
        'Kategorie': ['Textilien', 'Textilien', 'Textilien'],
        'Lagerstatus': ['verfügbar', 'verfügbar', 'Auslauf']
    }

    df = pd.DataFrame(data)
    df.to_excel(temp_file.name, index=False)
    temp_file.close()

    yield temp_file.name

    # Cleanup
    try:
        os.unlink(temp_file.name)
    except:
        pass


@pytest.fixture
def sample_excel_with_header():
    """Fixture für Excel mit Header-Zeilen"""
    temp_file = tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.xlsx')

    # Excel mit Header-Zeilen (z.B. Firmenlogo, Titel, etc.)
    data = {
        'A': ['L-Shop GmbH', 'Artikelliste 2025', '', 'Artikelnummer', 'ART001', 'ART002'],
        'B': ['', '', '', 'Bezeichnung', 'T-Shirt', 'Polo'],
        'C': ['', '', '', 'Preis', '8.50', '12.30']
    }

    df = pd.DataFrame(data)
    df.to_excel(temp_file.name, index=False, header=False)
    temp_file.close()

    yield temp_file.name

    try:
        os.unlink(temp_file.name)
    except:
        pass


class TestLShopImportServiceInit:
    """Tests für Initialisierung"""

    def test_init_creates_instance(self, import_service):
        """Test: Service-Instanz wird erstellt"""
        assert import_service is not None
        assert isinstance(import_service, LShopImportService)

    def test_init_sets_default_values(self, import_service):
        """Test: Default-Werte werden gesetzt"""
        assert import_service.excel_path is None
        assert import_service.header_row is None
        assert import_service.df is None

    def test_init_has_field_mapping(self, import_service):
        """Test: Feldmapping ist definiert"""
        assert hasattr(import_service, 'stitchadmin_fields')
        assert isinstance(import_service.stitchadmin_fields, dict)
        assert len(import_service.stitchadmin_fields) > 0

        # Prüfe wichtige Felder
        assert 'supplier_article_number' in import_service.stitchadmin_fields
        assert 'article_number' in import_service.stitchadmin_fields
        assert 'name' in import_service.stitchadmin_fields
        assert 'single_price' in import_service.stitchadmin_fields


class TestGenerateArticleId:
    """Tests für Artikel-ID-Generierung"""

    def test_generate_article_id_format(self, import_service):
        """Test: Generierte ID hat korrektes Format"""
        article_id = import_service.generate_article_id()

        assert article_id is not None
        assert isinstance(article_id, str)
        assert article_id.startswith('ART')
        assert len(article_id) >= 7  # ART + mindestens 4 Zeichen

    def test_generate_article_id_unique(self, import_service):
        """Test: Generierte IDs sind einzigartig"""
        id1 = import_service.generate_article_id()
        id2 = import_service.generate_article_id()

        # IDs sollten unterschiedlich sein (mit hoher Wahrscheinlichkeit)
        assert id1 != id2

    def test_generate_article_id_checks_existing(self, import_service, db_session):
        """Test: Prüft ob ID bereits existiert"""
        # Erstelle einen Artikel mit einer ID
        existing_id = import_service.generate_article_id()
        article = Article(
            id=existing_id,
            article_number='TEST001',
            name='Test Artikel',
            supplier='Test'
        )
        db_session.add(article)
        db_session.commit()

        # Generiere neue ID - sollte unterschiedlich sein
        new_id = import_service.generate_article_id()
        assert new_id != existing_id


class TestBrandManagement:
    """Tests für Marken-Verwaltung"""

    def test_create_or_get_brand_creates_new(self, import_service, db_session):
        """Test: Neue Marke wird erstellt"""
        brand_name = 'Test Brand'

        brand = import_service.create_or_get_brand(brand_name)

        assert brand is not None
        assert brand.name == brand_name
        assert brand.active is True

        # Prüfe Datenbank
        db_brand = Brand.query.filter_by(name=brand_name).first()
        assert db_brand is not None
        assert db_brand.id == brand.id

    def test_create_or_get_brand_gets_existing(self, import_service, db_session):
        """Test: Existierende Marke wird wiederverwendet"""
        brand_name = 'Existing Brand'

        # Erstelle Marke
        existing_brand = Brand(name=brand_name, active=True)
        db_session.add(existing_brand)
        db_session.commit()
        existing_id = existing_brand.id

        # Hole Marke
        brand = import_service.create_or_get_brand(brand_name)

        assert brand is not None
        assert brand.id == existing_id
        assert brand.name == brand_name

        # Sollte keine neue Marke erstellt haben
        brand_count = Brand.query.filter_by(name=brand_name).count()
        assert brand_count == 1

    def test_create_or_get_brand_empty_name(self, import_service):
        """Test: Leerer Name gibt None zurück"""
        brand = import_service.create_or_get_brand('')
        assert brand is None

        brand = import_service.create_or_get_brand(None)
        assert brand is None


class TestCategoryManagement:
    """Tests für Kategorie-Verwaltung"""

    def test_create_or_get_category_creates_new(self, import_service, db_session):
        """Test: Neue Kategorie wird erstellt"""
        category_name = 'Test Category'

        category = import_service.create_or_get_category(category_name)

        assert category is not None
        assert category.name == category_name
        assert category.active is True

    def test_create_or_get_category_gets_existing(self, import_service, db_session):
        """Test: Existierende Kategorie wird wiederverwendet"""
        category_name = 'Existing Category'

        # Erstelle Kategorie
        existing_category = ProductCategory(name=category_name, active=True)
        db_session.add(existing_category)
        db_session.commit()
        existing_id = existing_category.id

        # Hole Kategorie
        category = import_service.create_or_get_category(category_name)

        assert category is not None
        assert category.id == existing_id

        # Sollte keine neue Kategorie erstellt haben
        category_count = ProductCategory.query.filter_by(name=category_name).count()
        assert category_count == 1

    def test_create_or_get_category_empty_name(self, import_service):
        """Test: Leerer Name gibt None zurück"""
        category = import_service.create_or_get_category('')
        assert category is None


class TestFieldMapping:
    """Tests für Feld-Mapping"""

    def test_get_available_target_fields(self, import_service):
        """Test: Verfügbare Zielfelder abrufen"""
        fields = import_service.get_available_target_fields()

        assert isinstance(fields, dict)
        assert len(fields) > 0
        assert 'supplier_article_number' in fields
        assert 'article_number' in fields
        assert 'name' in fields

    def test_get_default_column_mapping(self, import_service, sample_excel_file):
        """Test: Standard-Spalten-Mapping"""
        import_service.analyze_excel(sample_excel_file)

        mapping = import_service.get_default_column_mapping()

        assert isinstance(mapping, dict)
        # Sollte automatisch erkannte Mappings enthalten
        # z.B. 'Artikelnummer' -> 'article_number'


class TestExcelAnalysis:
    """Tests für Excel-Analyse"""

    def test_analyze_excel_success(self, import_service, sample_excel_file):
        """Test: Excel-Datei erfolgreich analysieren"""
        result = import_service.analyze_excel(sample_excel_file)

        assert result['success'] is True
        assert result['header_row'] is not None
        assert result['total_rows'] > 0
        assert 'columns' in result
        assert len(result['columns']) > 0

    def test_analyze_excel_sets_attributes(self, import_service, sample_excel_file):
        """Test: Attribute werden gesetzt nach Analyse"""
        import_service.analyze_excel(sample_excel_file)

        assert import_service.excel_path == sample_excel_file
        assert import_service.header_row is not None
        assert import_service.df is not None
        assert isinstance(import_service.df, pd.DataFrame)

    def test_analyze_excel_invalid_file(self, import_service):
        """Test: Ungültige Datei"""
        result = import_service.analyze_excel('nonexistent.xlsx')

        assert result['success'] is False
        assert 'error' in result

    def test_analyze_excel_detects_columns(self, import_service, sample_excel_file):
        """Test: Spalten werden erkannt"""
        result = import_service.analyze_excel(sample_excel_file)

        columns = result['columns']
        assert 'Artikelnummer' in columns
        assert 'Bezeichnung' in columns
        assert 'Einzelpreis' in columns


class TestDataValidation:
    """Tests für Datenvalidierung"""

    def test_validate_data_success(self, import_service, sample_excel_file):
        """Test: Gültige Daten werden validiert"""
        import_service.analyze_excel(sample_excel_file)

        result = import_service.validate_data()

        assert result['valid'] is True
        assert result['total_rows'] > 0

    def test_validate_data_before_analysis(self, import_service):
        """Test: Validierung ohne vorherige Analyse"""
        result = import_service.validate_data()

        assert result['valid'] is False
        assert 'error' in result


class TestImportPreview:
    """Tests für Import-Vorschau"""

    def test_get_import_preview(self, import_service, sample_excel_file):
        """Test: Import-Vorschau generieren"""
        import_service.analyze_excel(sample_excel_file)
        mapping = import_service.get_default_column_mapping()

        preview = import_service.get_import_preview(limit=2)

        assert 'preview' in preview
        assert isinstance(preview['preview'], list)
        assert len(preview['preview']) <= 2

    def test_get_import_preview_without_analysis(self, import_service):
        """Test: Vorschau ohne Analyse"""
        preview = import_service.get_import_preview()

        assert preview['success'] is False


class TestHelperMethods:
    """Tests für Hilfsmethoden"""

    def test_safe_int_valid(self, import_service):
        """Test: Gültige Integer-Konvertierung"""
        assert import_service._safe_int('123') == 123
        assert import_service._safe_int(456) == 456
        assert import_service._safe_int('0') == 0

    def test_safe_int_invalid(self, import_service):
        """Test: Ungültige Integer-Konvertierung"""
        assert import_service._safe_int('abc') == 0
        assert import_service._safe_int(None) == 0
        assert import_service._safe_int('') == 0
        assert import_service._safe_int('12.5') == 12  # Wird zu Int

    def test_safe_float_valid(self, import_service):
        """Test: Gültige Float-Konvertierung"""
        assert import_service._safe_float('12.50') == 12.50
        assert import_service._safe_float('8,99') == 8.99  # Komma zu Punkt
        assert import_service._safe_float(15.75) == 15.75

    def test_safe_float_invalid(self, import_service):
        """Test: Ungültige Float-Konvertierung"""
        assert import_service._safe_float('abc') == 0.0
        assert import_service._safe_float(None) == 0.0
        assert import_service._safe_float('') == 0.0

    def test_safe_float_handles_comma(self, import_service):
        """Test: Komma als Dezimaltrennzeichen"""
        assert import_service._safe_float('10,50') == 10.50
        assert import_service._safe_float('1.234,56') == 1234.56


class TestImportArticles:
    """Tests für Artikel-Import (Integration)"""

    def test_import_articles_basic(self, import_service, sample_excel_file, db_session):
        """Test: Basis-Import von Artikeln"""
        # Analysiere Excel
        import_service.analyze_excel(sample_excel_file)

        # Erstelle Spalten-Mapping
        column_mapping = {
            'Artikelnummer': 'article_number',
            'Bezeichnung': 'name',
            'Einzelpreis': 'single_price',
            'Hersteller': 'manufacturer'
        }

        # Erstelle Lieferant
        supplier = Supplier(id='SUP001', name='L-Shop', active=True)
        db_session.add(supplier)
        db_session.commit()

        # Importiere mit Optionen
        options = {
            'supplier_id': 'SUP001',
            'update_existing': False,
            'skip_duplicates': True
        }

        result = import_service.import_articles(column_mapping, options)

        assert result['success'] is True
        assert result['imported'] > 0

        # Prüfe dass Artikel in DB sind
        articles = Article.query.all()
        assert len(articles) > 0

    def test_import_articles_creates_brands(self, import_service, sample_excel_file, db_session):
        """Test: Marken werden beim Import erstellt"""
        import_service.analyze_excel(sample_excel_file)

        column_mapping = {
            'Artikelnummer': 'article_number',
            'Bezeichnung': 'name',
            'Hersteller': 'manufacturer'
        }

        supplier = Supplier(id='SUP001', name='L-Shop', active=True)
        db_session.add(supplier)
        db_session.commit()

        options = {'supplier_id': 'SUP001'}

        # Import
        import_service.import_articles(column_mapping, options)

        # Prüfe ob Marken erstellt wurden
        brands = Brand.query.all()
        assert len(brands) > 0
        assert any(b.name == 'Fruit of the Loom' for b in brands)

    def test_import_articles_creates_categories(self, import_service, sample_excel_file, db_session):
        """Test: Kategorien werden beim Import erstellt"""
        import_service.analyze_excel(sample_excel_file)

        column_mapping = {
            'Artikelnummer': 'article_number',
            'Bezeichnung': 'name',
            'Kategorie': 'category'
        }

        supplier = Supplier(id='SUP001', name='L-Shop', active=True)
        db_session.add(supplier)
        db_session.commit()

        options = {'supplier_id': 'SUP001'}

        # Import
        import_service.import_articles(column_mapping, options)

        # Prüfe ob Kategorien erstellt wurden
        categories = ProductCategory.query.all()
        assert len(categories) > 0
        assert any(c.name == 'Textilien' for c in categories)


class TestIntegration:
    """Integrationstests für den gesamten Import-Workflow"""

    def test_full_import_workflow(self, import_service, sample_excel_file, db_session):
        """Test: Vollständiger Import-Workflow"""
        # 1. Analysiere Excel
        analysis_result = import_service.analyze_excel(sample_excel_file)
        assert analysis_result['success'] is True

        # 2. Hole Standard-Mapping
        mapping = import_service.get_default_column_mapping()
        assert len(mapping) > 0

        # 3. Validiere Daten
        validation = import_service.validate_data()
        assert validation['valid'] is True

        # 4. Hole Vorschau
        preview = import_service.get_import_preview(limit=1)
        assert len(preview['preview']) > 0

        # 5. Erstelle Lieferant
        supplier = Supplier(id='SUP001', name='L-Shop', active=True)
        db_session.add(supplier)
        db_session.commit()

        # 6. Importiere Artikel
        import_result = import_service.import_articles(
            mapping,
            {'supplier_id': 'SUP001'}
        )

        assert import_result['success'] is True
        assert import_result['imported'] > 0

        # 7. Prüfe Ergebnis
        articles = Article.query.all()
        assert len(articles) == import_result['imported']

        # Prüfe ersten Artikel
        article = articles[0]
        assert article.id is not None
        assert article.article_number is not None
        assert article.name is not None
