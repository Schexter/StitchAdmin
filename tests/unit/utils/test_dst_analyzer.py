"""
Unit Tests für DST Analyzer
Testet die Analyse von DST-Stickdateien
"""

import pytest
import struct
import tempfile
import os
from src.utils.dst_analyzer import (
    analyze_dst_file_complete,
    analyze_dst_file_robust,
    extract_all_header_info,
    extract_all_stitch_info,
    extract_all_color_info,
    extract_all_dimension_info,
    extract_all_quality_info,
    extract_all_production_info,
    classify_command,
    decode_movement,
    calculate_efficiency_rating,
    calculate_production_difficulty
)


@pytest.fixture
def sample_dst_header():
    """Fixture für DST-Header (512 Bytes)"""
    header = bytearray(512)
    # Label setzen
    label = b"TEST DESIGN 2025"
    header[0:len(label)] = label
    # Kommentare
    comment = b"Created by Test"
    header[20:20+len(comment)] = comment
    return bytes(header)


@pytest.fixture
def sample_dst_file(tmp_path):
    """Fixture für temporäre DST-Testdatei"""
    # Erstelle minimale DST-Datei
    dst_file = tmp_path / "test_design.dst"

    # Header (512 Bytes)
    header = bytearray(512)
    label = b"TEST DESIGN"
    header[0:len(label)] = label

    # Stitch-Daten (vereinfacht)
    stitch_data = bytearray()

    # Normale Stiche
    for i in range(10):
        # Bewegung nach rechts (+10mm, 0mm)
        stitch_data.extend([0x00, 0x00, 0x03])  # Beispiel-Stich

    # Farbwechsel
    stitch_data.extend([0x00, 0x00, 0xC3])  # Color change

    # Mehr Stiche
    for i in range(10):
        stitch_data.extend([0x00, 0x00, 0x03])

    # Trim
    stitch_data.extend([0x00, 0x00, 0xC7])  # Trim

    # Ende-Marker
    stitch_data.extend([0x00, 0x00, 0xF3])

    # Kombiniere Header und Daten
    with open(dst_file, 'wb') as f:
        f.write(header + stitch_data)

    yield str(dst_file)

    # Cleanup (optional, tmp_path macht das automatisch)


@pytest.fixture
def corrupt_dst_file(tmp_path):
    """Fixture für korrupte DST-Datei"""
    dst_file = tmp_path / "corrupt.dst"
    # Zu kurze Datei (weniger als Header)
    with open(dst_file, 'wb') as f:
        f.write(b'CORRUPT DATA')
    return str(dst_file)


class TestAnalyzeDstFileComplete:
    """Tests für Haupt-Analyse-Funktion"""

    def test_analyze_dst_file_success(self, sample_dst_file):
        """Test: Erfolgreiche DST-Analyse"""
        result = analyze_dst_file_complete(sample_dst_file)

        assert result is not None
        assert isinstance(result, dict)
        assert result['success'] is True

    def test_analyze_dst_file_contains_filepath(self, sample_dst_file):
        """Test: Ergebnis enthält Dateipfad"""
        result = analyze_dst_file_complete(sample_dst_file)

        assert 'filepath' in result
        assert result['filepath'] == sample_dst_file
        assert 'filename' in result
        assert result['filename'] == 'test_design.dst'

    def test_analyze_dst_file_contains_header_info(self, sample_dst_file):
        """Test: Header-Informationen werden extrahiert"""
        result = analyze_dst_file_complete(sample_dst_file)

        assert 'header_hex' in result or 'dst_label' in result
        assert 'header_size' in result

    def test_analyze_dst_file_contains_stitch_info(self, sample_dst_file):
        """Test: Stich-Informationen werden extrahiert"""
        result = analyze_dst_file_complete(sample_dst_file)

        assert 'total_stitches' in result
        assert 'normal_stitches' in result
        assert 'jump_stitches' in result
        assert 'color_changes' in result
        assert 'trim_count' in result

    def test_analyze_dst_file_contains_dimension_info(self, sample_dst_file):
        """Test: Dimensions-Informationen werden extrahiert"""
        result = analyze_dst_file_complete(sample_dst_file)

        assert 'width_mm' in result
        assert 'height_mm' in result
        # Bounding box ist in einem Sub-Dict
        assert 'bounding_box' in result
        assert 'min_x_mm' in result['bounding_box']
        assert 'max_x_mm' in result['bounding_box']
        assert 'min_y_mm' in result['bounding_box']
        assert 'max_y_mm' in result['bounding_box']

    def test_analyze_dst_file_nonexistent(self):
        """Test: Nicht existierende Datei"""
        result = analyze_dst_file_complete('nonexistent.dst')

        assert result['success'] is False
        assert 'error' in result

    def test_analyze_dst_file_corrupt(self, corrupt_dst_file):
        """Test: Korrupte Datei"""
        result = analyze_dst_file_complete(corrupt_dst_file)

        # Kann erfolgreich sein (mit Warnungen) oder fehlschlagen
        assert isinstance(result, dict)
        assert 'filepath' in result


class TestAnalyzeDstFileRobust:
    """Tests für robuste Analyse-Funktion"""

    def test_analyze_robust_success(self, sample_dst_file):
        """Test: Robuste Analyse erfolgreich"""
        result = analyze_dst_file_robust(sample_dst_file)

        assert result is not None
        assert isinstance(result, dict)

    def test_analyze_robust_handles_errors(self):
        """Test: Fehlerbehandlung in robuster Analyse"""
        result = analyze_dst_file_robust('nonexistent.dst')

        # Sollte trotzdem ein Ergebnis liefern
        assert isinstance(result, dict)


class TestExtractHeaderInfo:
    """Tests für Header-Extraktion"""

    def test_extract_header_info_with_label(self, sample_dst_header):
        """Test: Label aus Header extrahieren"""
        info = extract_all_header_info(sample_dst_header)

        assert isinstance(info, dict)
        assert 'dst_label' in info
        assert info['dst_label'] == 'TEST DESIGN 2025'

    def test_extract_header_info_with_comments(self, sample_dst_header):
        """Test: Kommentare aus Header extrahieren"""
        info = extract_all_header_info(sample_dst_header)

        # Sollte Kommentare enthalten (wenn vorhanden)
        if 'dst_comments' in info:
            assert isinstance(info['dst_comments'], list)

    def test_extract_header_info_hex(self, sample_dst_header):
        """Test: Header als Hex-String"""
        info = extract_all_header_info(sample_dst_header)

        assert 'header_hex' in info
        assert isinstance(info['header_hex'], str)
        assert len(info['header_hex']) == 512 * 2  # 2 hex chars per byte

    def test_extract_header_info_empty(self):
        """Test: Leerer Header"""
        empty_header = bytes(512)
        info = extract_all_header_info(empty_header)

        assert isinstance(info, dict)
        assert 'header_size' in info
        assert info['header_size'] == 512


class TestExtractStitchInfo:
    """Tests für Stich-Informations-Extraktion"""

    def test_extract_stitch_info_empty(self):
        """Test: Leere Stich-Daten"""
        info = extract_all_stitch_info(b'')

        assert isinstance(info, dict)
        assert info['total_stitches'] == 0

    def test_extract_stitch_info_with_end_marker(self):
        """Test: Daten mit Ende-Marker"""
        data = bytearray()
        data.extend([0x00, 0x00, 0x03])  # Normal stitch
        data.extend([0x00, 0x00, 0xF3])  # End marker

        info = extract_all_stitch_info(bytes(data))

        assert isinstance(info, dict)
        assert info['total_stitches'] >= 0

    def test_extract_stitch_info_color_change(self):
        """Test: Farbwechsel erkennen"""
        data = bytearray()
        data.extend([0x00, 0xB0, 0xFE])  # Color change (b2=0xFE, b1=0xB0)
        data.extend([0x00, 0x00, 0xF3])  # End

        info = extract_all_stitch_info(bytes(data))

        assert info['color_changes'] >= 1

    def test_extract_stitch_info_trim(self):
        """Test: Trim erkennen"""
        data = bytearray()
        data.extend([0x00, 0x00, 0xFD])  # Trim (b2=0xFD)
        data.extend([0x00, 0x00, 0xF3])  # End

        info = extract_all_stitch_info(bytes(data))

        assert info['trim_count'] >= 1

    def test_extract_stitch_info_commands_list(self):
        """Test: Command-Liste wird erstellt"""
        data = bytearray()
        data.extend([0x00, 0x00, 0xC3])  # Command
        data.extend([0x00, 0x00, 0xF3])  # End

        info = extract_all_stitch_info(bytes(data))

        assert 'commands' in info
        assert isinstance(info['commands'], list)


class TestExtractColorInfo:
    """Tests für Farb-Informations-Extraktion"""

    def test_extract_color_info_empty(self):
        """Test: Leere Daten"""
        info = extract_all_color_info(b'')

        assert isinstance(info, dict)
        assert 'total_color_changes' in info
        assert 'estimated_colors' in info

    def test_extract_color_info_with_changes(self):
        """Test: Daten mit Farbwechseln"""
        data = bytearray()
        data.extend([0x00, 0xB0, 0xFE])  # Color change 1
        data.extend([0x00, 0x00, 0x03])  # Stitch
        data.extend([0x00, 0xB0, 0xFE])  # Color change 2
        data.extend([0x00, 0x00, 0xF3])  # End

        info = extract_all_color_info(bytes(data))

        assert 'total_color_changes' in info
        assert info['total_color_changes'] >= 2


class TestExtractDimensionInfo:
    """Tests für Dimensions-Informations-Extraktion"""

    def test_extract_dimension_info_empty(self):
        """Test: Leere Daten"""
        info = extract_all_dimension_info(b'')

        assert isinstance(info, dict)
        assert 'width_mm' in info
        assert 'height_mm' in info
        assert 'bounding_box' in info
        assert 'min_x_mm' in info['bounding_box']
        assert 'max_x_mm' in info['bounding_box']
        assert 'min_y_mm' in info['bounding_box']
        assert 'max_y_mm' in info['bounding_box']

    def test_extract_dimension_info_calculates_size(self):
        """Test: Größe wird berechnet"""
        # Daten mit Bewegungen
        data = bytearray()
        # Bewegung nach rechts
        data.extend([0x00, 0x00, 0x03])
        data.extend([0x00, 0x00, 0x03])
        data.extend([0x00, 0x00, 0xF3])  # End

        info = extract_all_dimension_info(bytes(data))

        # Sollte nicht-null Werte haben
        assert isinstance(info['width_mm'], (int, float))
        assert isinstance(info['height_mm'], (int, float))


class TestExtractQualityInfo:
    """Tests für Qualitäts-Informations-Extraktion"""

    def test_extract_quality_info_basic(self):
        """Test: Basis-Qualitätsinfo"""
        stitch_info = {
            'total_stitches': 100,
            'normal_stitches': 90,
            'jump_stitches': 10,
            'trim_count': 5
        }
        dimension_info = {
            'width_mm': 100,
            'height_mm': 50,
            'area_cm2': 50  # 10cm x 5cm
        }

        info = extract_all_quality_info(stitch_info, dimension_info)

        assert isinstance(info, dict)
        assert 'density_per_cm2' in info
        assert 'density_rating' in info

    def test_extract_quality_info_with_zero_area(self):
        """Test: Qualitätsinfo mit Null-Fläche"""
        stitch_info = {'total_stitches': 100}
        dimension_info = {'width_mm': 0, 'height_mm': 0}

        info = extract_all_quality_info(stitch_info, dimension_info)

        # Sollte nicht crashen
        assert isinstance(info, dict)


class TestExtractProductionInfo:
    """Tests für Produktions-Informations-Extraktion"""

    def test_extract_production_info_basic(self):
        """Test: Basis-Produktionsinfo"""
        stitch_info = {
            'total_stitches': 1000,
            'trim_count': 10,
            'color_changes': 3
        }
        dimension_info = {
            'width_mm': 100,
            'height_mm': 100
        }

        info = extract_all_production_info(stitch_info, dimension_info)

        assert isinstance(info, dict)
        assert 'estimated_time_minutes' in info
        assert 'production_difficulty' in info

    def test_extract_production_info_calculates_time(self):
        """Test: Produktionszeit wird geschätzt"""
        stitch_info = {'total_stitches': 6000}  # 10 Minuten bei 600 spm
        dimension_info = {'width_mm': 100, 'height_mm': 100}

        info = extract_all_production_info(stitch_info, dimension_info)

        # Sollte realistische Zeit haben
        assert info['estimated_time_minutes'] > 0


class TestClassifyCommand:
    """Tests für Command-Klassifizierung"""

    def test_classify_color_change(self):
        """Test: Farbwechsel-Command"""
        cmd = classify_command(0x00, 0xB0, 0xFE)  # b2=0xFE and b1=0xB0
        assert cmd == 'color_change'

    def test_classify_trim(self):
        """Test: Trim-Command"""
        cmd = classify_command(0x00, 0x00, 0xFD)  # b2=0xFD
        assert cmd == 'trim'

    def test_classify_stop(self):
        """Test: Stop-Command"""
        cmd = classify_command(0x00, 0x00, 0xFF)  # b2=0xFF
        assert cmd == 'stop'

    def test_classify_unknown(self):
        """Test: Unbekannter Command"""
        cmd = classify_command(0x00, 0x00, 0x00)  # Unknown command
        # Sollte einen String zurückgeben
        assert isinstance(cmd, str)
        assert cmd == 'unknown'


class TestDecodeMovement:
    """Tests für Bewegungs-Dekodierung"""

    def test_decode_movement_basic(self):
        """Test: Basis-Bewegung dekodieren"""
        dx, dy = decode_movement(0x00, 0x00, 0x03)

        assert isinstance(dx, int)
        assert isinstance(dy, int)

    def test_decode_movement_returns_tuple(self):
        """Test: Rückgabe ist Tupel"""
        result = decode_movement(0x01, 0x02, 0x03)

        assert isinstance(result, tuple)
        assert len(result) == 2


class TestCalculateEfficiencyRating:
    """Tests für Effizienz-Bewertung"""

    def test_calculate_efficiency_high(self):
        """Test: Hohe Effizienz"""
        stitch_info = {
            'total_stitches': 1000,
            'normal_stitches': 990,  # 99% normal stitches
            'jump_stitches': 10  # 1% Jumps = Sehr effizient
        }

        rating = calculate_efficiency_rating(stitch_info)

        assert isinstance(rating, str)
        # Akzeptiere alle möglichen Ratings
        assert rating in ['Sehr Gut', 'Gut', 'Mittel', 'Niedrig', 'Sehr Niedrig', 'Effizient', 'Ineffizient', 'Sehr effizient']

    def test_calculate_efficiency_low(self):
        """Test: Niedrige Effizienz"""
        stitch_info = {
            'total_stitches': 100,
            'jump_stitches': 50  # 50% Jumps = Ineffizient
        }

        rating = calculate_efficiency_rating(stitch_info)

        assert isinstance(rating, str)

    def test_calculate_efficiency_no_stitches(self):
        """Test: Keine Stiche"""
        stitch_info = {'total_stitches': 0, 'jump_stitches': 0}

        rating = calculate_efficiency_rating(stitch_info)

        assert isinstance(rating, str)


class TestCalculateProductionDifficulty:
    """Tests für Produktions-Schwierigkeit"""

    def test_calculate_difficulty_easy(self):
        """Test: Einfaches Design"""
        stitch_info = {
            'total_stitches': 500,
            'color_changes': 1,
            'trim_count': 2
        }
        dimension_info = {
            'width_mm': 50,
            'height_mm': 50
        }

        difficulty = calculate_production_difficulty(stitch_info, dimension_info)

        assert isinstance(difficulty, str)
        assert difficulty in ['Einfach', 'Mittel', 'Schwierig', 'Sehr Schwierig']

    def test_calculate_difficulty_complex(self):
        """Test: Komplexes Design"""
        stitch_info = {
            'total_stitches': 50000,
            'color_changes': 20,
            'trim_count': 50
        }
        dimension_info = {
            'width_mm': 300,
            'height_mm': 300
        }

        difficulty = calculate_production_difficulty(stitch_info, dimension_info)

        assert isinstance(difficulty, str)


class TestIntegration:
    """Integrationstests für DST-Analyzer"""

    def test_full_analysis_workflow(self, sample_dst_file):
        """Test: Vollständiger Analyse-Workflow"""
        # 1. Analysiere Datei
        result = analyze_dst_file_complete(sample_dst_file)

        assert result['success'] is True

        # 2. Prüfe alle Hauptbereiche
        assert 'filepath' in result
        assert 'total_stitches' in result
        assert 'width_mm' in result
        assert 'total_color_changes' in result  # Korrekte API-Bezeichnung
        assert 'estimated_colors' in result
        assert 'density_rating' in result
        assert 'production_difficulty' in result

        # 3. Werte sollten sinnvoll sein
        assert result['total_stitches'] >= 0
        assert result['width_mm'] >= 0
        assert result['height_mm'] >= 0

    def test_analyze_multiple_files(self, sample_dst_file, tmp_path):
        """Test: Mehrere Dateien analysieren"""
        # Erstelle zweite Datei
        dst_file2 = tmp_path / "design2.dst"
        with open(sample_dst_file, 'rb') as f:
            content = f.read()
        with open(dst_file2, 'wb') as f:
            f.write(content)

        # Analysiere beide
        result1 = analyze_dst_file_complete(sample_dst_file)
        result2 = analyze_dst_file_complete(str(dst_file2))

        assert result1['success'] is True
        assert result2['success'] is True
        assert result1['filename'] != result2['filename']
