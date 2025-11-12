"""
Unit Tests für Form Helpers
Testet alle Formular-Verarbeitungsfunktionen
"""

import pytest
from datetime import datetime, date
from werkzeug.datastructures import ImmutableMultiDict
from src.utils.form_helpers import (
    parse_date_from_form,
    parse_datetime_from_form,
    parse_float_from_form,
    parse_int_from_form,
    safe_get_form_value,
    validate_required_fields
)


@pytest.mark.unit
class TestFormHelpers:
    """Test-Klasse für Form Helpers"""

    # ==========================================
    # parse_date_from_form Tests
    # ==========================================

    def test_parse_date_valid(self):
        """Test: Gültiges Datum parsen"""
        result = parse_date_from_form('2025-11-12', 'test_date')
        assert isinstance(result, date)
        assert result.year == 2025
        assert result.month == 11
        assert result.day == 12

    def test_parse_date_empty_string(self):
        """Test: Leerer String gibt None zurück"""
        assert parse_date_from_form('', 'test_date') is None
        assert parse_date_from_form('   ', 'test_date') is None

    def test_parse_date_none(self):
        """Test: None gibt None zurück"""
        assert parse_date_from_form(None, 'test_date') is None

    def test_parse_date_invalid_format(self, app):
        """Test: Ungültiges Format gibt None zurück"""
        with app.test_request_context():
            result = parse_date_from_form('12.11.2025', 'test_date')  # Falsches Format
            assert result is None

    def test_parse_date_invalid_date(self, app):
        """Test: Ungültiges Datum gibt None zurück"""
        with app.test_request_context():
            result = parse_date_from_form('2025-13-45', 'test_date')  # Ungültiges Datum
            assert result is None

    # ==========================================
    # parse_datetime_from_form Tests
    # ==========================================

    def test_parse_datetime_valid(self):
        """Test: Gültiges DateTime parsen"""
        result = parse_datetime_from_form('2025-11-12T14:30', 'test_datetime')
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 11
        assert result.day == 12
        assert result.hour == 14
        assert result.minute == 30

    def test_parse_datetime_date_only(self):
        """Test: Nur Datum (ohne Zeit) parsen"""
        result = parse_datetime_from_form('2025-11-12', 'test_datetime')
        assert isinstance(result, datetime)
        assert result.hour == 0
        assert result.minute == 0

    def test_parse_datetime_empty(self):
        """Test: Leerer String gibt None zurück"""
        assert parse_datetime_from_form('', 'test_datetime') is None
        assert parse_datetime_from_form('   ', 'test_datetime') is None

    def test_parse_datetime_invalid(self, app):
        """Test: Ungültiges Format gibt None zurück"""
        with app.test_request_context():
            result = parse_datetime_from_form('invalid', 'test_datetime')
            assert result is None

    # ==========================================
    # parse_float_from_form Tests
    # ==========================================

    def test_parse_float_valid_dot(self):
        """Test: Gültige Float-Zahl mit Punkt"""
        result = parse_float_from_form('12.50', 'price')
        assert result == 12.50

    def test_parse_float_valid_comma(self):
        """Test: Deutsche Dezimalzahl mit Komma"""
        result = parse_float_from_form('12,50', 'price')
        assert result == 12.50

    def test_parse_float_integer(self):
        """Test: Ganzzahl als Float"""
        result = parse_float_from_form('42', 'price')
        assert result == 42.0

    def test_parse_float_empty_with_default(self):
        """Test: Leerer String gibt Default zurück"""
        result = parse_float_from_form('', 'price', default=0.0)
        assert result == 0.0

    def test_parse_float_invalid_with_default(self, app):
        """Test: Ungültige Zahl gibt Default zurück"""
        with app.test_request_context():
            result = parse_float_from_form('abc', 'price', default=0.0)
            assert result == 0.0

    def test_parse_float_negative(self):
        """Test: Negative Zahl"""
        result = parse_float_from_form('-10.5', 'price')
        assert result == -10.5

    # ==========================================
    # parse_int_from_form Tests
    # ==========================================

    def test_parse_int_valid(self):
        """Test: Gültige Ganzzahl"""
        result = parse_int_from_form('42', 'quantity')
        assert result == 42

    def test_parse_int_empty_with_default(self):
        """Test: Leerer String gibt Default zurück"""
        result = parse_int_from_form('', 'quantity', default=1)
        assert result == 1

    def test_parse_int_invalid_with_default(self, app):
        """Test: Ungültige Zahl gibt Default zurück"""
        with app.test_request_context():
            result = parse_int_from_form('abc', 'quantity', default=0)
            assert result == 0

    def test_parse_int_float_string(self, app):
        """Test: Float-String gibt Default zurück (nicht konvertierbar zu int)"""
        with app.test_request_context():
            result = parse_int_from_form('12.5', 'quantity', default=0)
            assert result == 0

    def test_parse_int_negative(self):
        """Test: Negative Ganzzahl"""
        result = parse_int_from_form('-5', 'quantity')
        assert result == -5

    # ==========================================
    # safe_get_form_value Tests
    # ==========================================

    def test_safe_get_existing_value(self):
        """Test: Existierender Wert abrufen"""
        form_data = ImmutableMultiDict([('name', 'Test User')])
        result = safe_get_form_value(form_data, 'name')
        assert result == 'Test User'

    def test_safe_get_missing_value_with_default(self):
        """Test: Fehlender Wert gibt Default zurück"""
        form_data = ImmutableMultiDict([])
        result = safe_get_form_value(form_data, 'name', default='Unknown')
        assert result == 'Unknown'

    def test_safe_get_strip_whitespace(self):
        """Test: Whitespace wird entfernt"""
        form_data = ImmutableMultiDict([('name', '  Test User  ')])
        result = safe_get_form_value(form_data, 'name', strip=True)
        assert result == 'Test User'

    def test_safe_get_no_strip(self):
        """Test: Whitespace bleibt erhalten wenn strip=False"""
        form_data = ImmutableMultiDict([('name', '  Test User  ')])
        result = safe_get_form_value(form_data, 'name', strip=False)
        assert result == '  Test User  '

    def test_safe_get_empty_string_default(self):
        """Test: Leerer String als Default"""
        form_data = ImmutableMultiDict([])
        result = safe_get_form_value(form_data, 'name')
        assert result == ''

    # ==========================================
    # validate_required_fields Tests
    # ==========================================

    def test_validate_all_fields_present(self):
        """Test: Alle Pflichtfelder vorhanden"""
        form_data = ImmutableMultiDict([
            ('name', 'Test'),
            ('email', 'test@example.com'),
            ('phone', '123456')
        ])
        result = validate_required_fields(form_data, ['name', 'email', 'phone'])
        assert result is True

    def test_validate_missing_field(self, app):
        """Test: Fehlendes Pflichtfeld"""
        with app.test_request_context():
            form_data = ImmutableMultiDict([
                ('name', 'Test'),
                ('email', '')  # Leer
            ])
            result = validate_required_fields(form_data, ['name', 'email', 'phone'])
            assert result is False

    def test_validate_empty_field(self, app):
        """Test: Leeres Pflichtfeld"""
        with app.test_request_context():
            form_data = ImmutableMultiDict([
                ('name', 'Test'),
                ('email', '   ')  # Nur Whitespace
            ])
            result = validate_required_fields(form_data, ['name', 'email'])
            assert result is False

    def test_validate_no_required_fields(self):
        """Test: Keine Pflichtfelder definiert"""
        form_data = ImmutableMultiDict([('name', 'Test')])
        result = validate_required_fields(form_data, [])
        assert result is True

    def test_validate_partial_missing(self, app):
        """Test: Teilweise fehlende Felder"""
        with app.test_request_context():
            form_data = ImmutableMultiDict([
                ('field1', 'Value1'),
                ('field2', 'Value2'),
                ('field3', '')  # Leer
            ])
            result = validate_required_fields(form_data, ['field1', 'field2', 'field3', 'field4'])
            assert result is False
