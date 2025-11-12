"""
Unit Tests für Jinja2 Filters
Testet alle Template-Filter-Funktionen
"""

import pytest
from datetime import datetime, date
from src.utils.filters import (
    format_date,
    format_datetime,
    format_datetime_full,
    format_time,
    calculate_age,
    time_ago,
    nl2br
)


@pytest.mark.unit
class TestFilters:
    """Test-Klasse für Jinja2 Filters"""

    # ==========================================
    # format_date Tests
    # ==========================================

    def test_format_date_valid(self):
        """Test: Datum formatieren (DD.MM.YYYY)"""
        test_date = date(2025, 11, 12)
        result = format_date(test_date)
        assert result == '12.11.2025'

    def test_format_date_datetime_object(self):
        """Test: DateTime-Objekt als Datum formatieren"""
        test_datetime = datetime(2025, 11, 12, 14, 30)
        result = format_date(test_datetime)
        assert result == '12.11.2025'

    def test_format_date_none(self):
        """Test: None gibt leeren String zurück"""
        result = format_date(None)
        assert result == ""

    def test_format_date_string_passthrough(self):
        """Test: String wird durchgereicht"""
        result = format_date("Bereits formatiert")
        assert result == "Bereits formatiert"

    # ==========================================
    # format_datetime Tests
    # ==========================================

    def test_format_datetime_valid(self):
        """Test: DateTime formatieren (DD.MM.YYYY HH:MM)"""
        test_datetime = datetime(2025, 11, 12, 14, 30)
        result = format_datetime(test_datetime)
        assert result == '12.11.2025 14:30'

    def test_format_datetime_none(self):
        """Test: None gibt leeren String zurück"""
        result = format_datetime(None)
        assert result == ""

    def test_format_datetime_string_passthrough(self):
        """Test: String wird durchgereicht"""
        result = format_datetime("Bereits formatiert")
        assert result == "Bereits formatiert"

    def test_format_datetime_midnight(self):
        """Test: Mitternacht korrekt formatieren"""
        test_datetime = datetime(2025, 11, 12, 0, 0)
        result = format_datetime(test_datetime)
        assert result == '12.11.2025 00:00'

    # ==========================================
    # format_datetime_full Tests
    # ==========================================

    def test_format_datetime_full_valid(self):
        """Test: DateTime mit Sekunden (DD.MM.YYYY HH:MM:SS)"""
        test_datetime = datetime(2025, 11, 12, 14, 30, 45)
        result = format_datetime_full(test_datetime)
        assert result == '12.11.2025 14:30:45'

    def test_format_datetime_full_none(self):
        """Test: None gibt leeren String zurück"""
        result = format_datetime_full(None)
        assert result == ""

    def test_format_datetime_full_zero_seconds(self):
        """Test: Null Sekunden korrekt anzeigen"""
        test_datetime = datetime(2025, 11, 12, 14, 30, 0)
        result = format_datetime_full(test_datetime)
        assert result == '12.11.2025 14:30:00'

    # ==========================================
    # format_time Tests
    # ==========================================

    def test_format_time_valid(self):
        """Test: Zeit formatieren (HH:MM)"""
        test_datetime = datetime(2025, 11, 12, 14, 30)
        result = format_time(test_datetime)
        assert result == '14:30'

    def test_format_time_none(self):
        """Test: None gibt leeren String zurück"""
        result = format_time(None)
        assert result == ""

    def test_format_time_midnight(self):
        """Test: Mitternacht formatieren"""
        test_datetime = datetime(2025, 11, 12, 0, 0)
        result = format_time(test_datetime)
        assert result == '00:00'

    # ==========================================
    # calculate_age Tests
    # ==========================================

    def test_calculate_age_adult(self):
        """Test: Alter für Erwachsenen berechnen"""
        # Jemand geboren am 1.1.1990 ist heute ~35 Jahre alt
        birth_date = date(1990, 1, 1)
        age = calculate_age(birth_date)
        assert age >= 34  # Mindestens 34, je nach aktuellem Datum

    def test_calculate_age_child(self):
        """Test: Alter für Kind berechnen"""
        # Kind geboren vor 5 Jahren
        today = date.today()
        birth_date = date(today.year - 5, today.month, today.day)
        age = calculate_age(birth_date)
        assert age == 5

    def test_calculate_age_birthday_not_yet(self):
        """Test: Geburtstag dieses Jahr noch nicht gehabt"""
        today = date.today()
        # Geboren vor 10 Jahren, aber Geburtstag ist morgen
        if today.month == 12 and today.day == 31:
            # Spezialfall Silvester
            birth_date = date(today.year - 10, 1, 1)
            age = calculate_age(birth_date)
            assert age == 10
        else:
            birth_date = date(today.year - 10, today.month, today.day + 1)
            age = calculate_age(birth_date)
            assert age == 9  # Noch nicht 10

    def test_calculate_age_none(self):
        """Test: None gibt None zurück"""
        result = calculate_age(None)
        assert result is None

    # ==========================================
    # time_ago Tests
    # ==========================================

    def test_time_ago_just_now(self):
        """Test: Gerade eben"""
        now = datetime.now()
        result = time_ago(now)
        assert result == "gerade eben"

    def test_time_ago_minutes(self):
        """Test: Vor X Minuten"""
        from datetime import timedelta
        time = datetime.now() - timedelta(minutes=5)
        result = time_ago(time)
        assert "vor 5 Minute" in result

    def test_time_ago_hours(self):
        """Test: Vor X Stunden"""
        from datetime import timedelta
        time = datetime.now() - timedelta(hours=2)
        result = time_ago(time)
        assert "vor 2 Stunde" in result

    def test_time_ago_days(self):
        """Test: Vor X Tagen"""
        from datetime import timedelta
        time = datetime.now() - timedelta(days=3)
        result = time_ago(time)
        assert "vor 3 Tag" in result

    def test_time_ago_months(self):
        """Test: Vor X Monaten"""
        from datetime import timedelta
        time = datetime.now() - timedelta(days=60)  # ~2 Monate
        result = time_ago(time)
        assert "vor 2 Monat" in result or "vor 1 Monat" in result

    def test_time_ago_years(self):
        """Test: Vor X Jahren"""
        from datetime import timedelta
        time = datetime.now() - timedelta(days=730)  # ~2 Jahre
        result = time_ago(time)
        assert "vor 2 Jahr" in result

    def test_time_ago_none(self):
        """Test: None gibt leeren String zurück"""
        result = time_ago(None)
        assert result == ""

    def test_time_ago_string_passthrough(self):
        """Test: String wird durchgereicht"""
        result = time_ago("vor langer Zeit")
        assert result == "vor langer Zeit"

    # ==========================================
    # nl2br Tests
    # ==========================================

    def test_nl2br_single_newline(self):
        """Test: Einzelner Zeilenumbruch zu <br>"""
        text = "Zeile 1\nZeile 2"
        result = nl2br(text)
        assert result == "Zeile 1<br>Zeile 2"

    def test_nl2br_multiple_newlines(self):
        """Test: Mehrere Zeilenumbrüche"""
        text = "Zeile 1\nZeile 2\nZeile 3"
        result = nl2br(text)
        assert result == "Zeile 1<br>Zeile 2<br>Zeile 3"

    def test_nl2br_no_newlines(self):
        """Test: Kein Zeilenumbruch"""
        text = "Nur eine Zeile"
        result = nl2br(text)
        assert result == "Nur eine Zeile"

    def test_nl2br_empty_string(self):
        """Test: Leerer String"""
        result = nl2br("")
        assert result == ""

    def test_nl2br_none(self):
        """Test: None gibt leeren String zurück"""
        result = nl2br(None)
        assert result == ""

    def test_nl2br_double_newlines(self):
        """Test: Doppelte Zeilenumbrüche (Absätze)"""
        text = "Absatz 1\n\nAbsatz 2"
        result = nl2br(text)
        assert result == "Absatz 1<br><br>Absatz 2"
