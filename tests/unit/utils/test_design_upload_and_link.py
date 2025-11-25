"""
Unit Tests für Design Upload und Link Manager
Testet File Upload und Design-Link-Management
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

from src.utils.design_upload import (
    save_design_file,
    get_file_type,
    analyze_print_file,
    check_for_link,
    save_link,
    get_link,
    needs_graphics_manager,
    should_show_graphics_manager
)

from src.utils.design_link_manager import (
    DesignLinkManager,
    process_design_link,
    check_link_exists,
    get_link_status,
    requires_graphics_manager
)


@pytest.fixture
def temp_upload_dir(tmp_path, monkeypatch):
    """Fixture für temporäres Upload-Verzeichnis"""
    upload_dir = tmp_path / "uploads/designs"
    upload_dir.mkdir(parents=True)
    monkeypatch.setattr('src.utils.design_upload.os.makedirs', lambda path, exist_ok=True: None)
    return str(upload_dir)


@pytest.fixture
def temp_link_dir(tmp_path, monkeypatch):
    """Fixture für temporäres Link-Verzeichnis"""
    link_dir = tmp_path / "data/links"
    link_dir.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return str(link_dir)


@pytest.fixture
def mock_file_obj():
    """Fixture für Mock-Datei-Objekt"""
    mock_file = Mock()
    mock_file.filename = 'test_design.dst'
    mock_file.save = Mock()
    return mock_file


@pytest.fixture
def design_link_manager(tmp_path):
    """Fixture für DesignLinkManager mit temp directories"""
    manager = DesignLinkManager()
    manager.links_folder = str(tmp_path / "design_links")
    manager.graphics_manager_folder = str(tmp_path / "graphics_manager")
    manager.ensure_directories()
    return manager


class TestGetFileType:
    """Tests für Dateityp-Erkennung"""

    def test_get_file_type_embroidery_dst(self):
        """Test: DST-Datei wird als Stickerei erkannt"""
        assert get_file_type('design.dst') == 'embroidery'

    def test_get_file_type_embroidery_pes(self):
        """Test: PES-Datei wird als Stickerei erkannt"""
        assert get_file_type('design.pes') == 'embroidery'

    def test_get_file_type_embroidery_various(self):
        """Test: Verschiedene Stick-Formate"""
        assert get_file_type('test.jef') == 'embroidery'
        assert get_file_type('test.exp') == 'embroidery'
        assert get_file_type('test.vp3') == 'embroidery'
        assert get_file_type('test.vp4') == 'embroidery'

    def test_get_file_type_print_png(self):
        """Test: PNG als Druck erkannt"""
        assert get_file_type('image.png') == 'print'

    def test_get_file_type_print_various(self):
        """Test: Verschiedene Druck-Formate"""
        assert get_file_type('logo.jpg') == 'print'
        assert get_file_type('design.svg') == 'print'
        assert get_file_type('vector.ai') == 'print'
        assert get_file_type('doc.pdf') == 'print'

    def test_get_file_type_unknown(self):
        """Test: Unbekannter Dateityp"""
        assert get_file_type('unknown.xyz') == 'unknown'

    def test_get_file_type_no_extension(self):
        """Test: Datei ohne Erweiterung"""
        assert get_file_type('filename') == 'unknown'

    def test_get_file_type_case_insensitive(self):
        """Test: Groß-/Kleinschreibung egal"""
        assert get_file_type('DESIGN.DST') == 'embroidery'
        assert get_file_type('IMAGE.PNG') == 'print'


class TestSaveDesignFile:
    """Tests für Design-File-Upload"""

    def test_save_design_file_no_file(self):
        """Test: Kein File-Objekt"""
        result = save_design_file(None)

        assert result['success'] is False
        assert 'error' in result

    def test_save_design_file_no_filename(self):
        """Test: File-Objekt ohne Dateiname"""
        mock_file = Mock()
        mock_file.filename = None

        result = save_design_file(mock_file)

        assert result['success'] is False

    @patch('os.makedirs')
    @patch('src.utils.design_upload.analyze_dst_file_robust')
    def test_save_design_file_dst_success(self, mock_analyze, mock_makedirs, mock_file_obj, tmp_path):
        """Test: Erfolgreicher DST-Upload"""
        mock_analyze.return_value = {'success': True, 'total_stitches': 1000}

        # Mock save to actual temp file
        def save_side_effect(filepath):
            open(filepath, 'wb').write(b'DST DATA')

        mock_file_obj.save.side_effect = save_side_effect

        with patch('src.utils.design_upload.os.path.join', side_effect=lambda *args: str(tmp_path / args[-1])):
            result = save_design_file(mock_file_obj, order_id='ORD001')

        assert result['success'] is True
        assert 'filename' in result
        assert 'storage_path' in result
        assert result['file_type'] == 'embroidery'

    def test_save_design_file_with_order_id(self, mock_file_obj):
        """Test: Dateiname wird mit Order-ID erweitert"""
        with patch('src.utils.design_upload.os.makedirs'):
            with patch('src.utils.design_upload.analyze_dst_file_robust', return_value={}):
                result = save_design_file(mock_file_obj, order_id='ORD123')

                if result['success']:
                    assert 'ORD123' in result['filename']


class TestAnalyzePrintFile:
    """Tests für Druck-Datei-Analyse"""

    @pytest.mark.skip(reason="PIL optional dependency")
    def test_analyze_print_file_png(self, tmp_path):
        """Test: PNG-Analyse (wenn PIL verfügbar)"""
        from PIL import Image

        # Erstelle Test-PNG
        img = Image.new('RGB', (100, 100), color='red')
        img_path = tmp_path / "test.png"
        img.save(img_path)

        result = analyze_print_file(str(img_path))

        assert result['success'] is True
        assert result['width_px'] == 100
        assert result['height_px'] == 100

    def test_analyze_print_file_unsupported(self, tmp_path):
        """Test: Nicht unterstütztes Format"""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b'%PDF-1.4')

        result = analyze_print_file(str(pdf_path))

        # Sollte limited analysis zurückgeben
        assert isinstance(result, dict)


class TestLinkManagement:
    """Tests für Link-Verwaltung"""

    def test_save_link_success(self, tmp_path, monkeypatch):
        """Test: Link erfolgreich speichern"""
        monkeypatch.chdir(tmp_path)

        result = save_link('ORD001', 'https://example.com/design.png')

        assert result['success'] is True
        assert 'storage_path' in result
        assert 'link:' in result['storage_path']

    def test_get_link_exists(self, tmp_path, monkeypatch):
        """Test: Gespeicherten Link abrufen"""
        monkeypatch.chdir(tmp_path)

        # Speichere Link
        save_link('ORD002', 'https://example.com/design2.svg')

        # Hole Link
        link = get_link('ORD002')

        assert link == 'https://example.com/design2.svg'

    def test_get_link_not_exists(self):
        """Test: Nicht existierender Link"""
        link = get_link('NONEXISTENT')

        assert link is None

    def test_check_for_link_true(self, tmp_path, monkeypatch):
        """Test: Link-Existenz-Check positiv"""
        monkeypatch.chdir(tmp_path)

        save_link('ORD003', 'https://example.com/test.dst')

        assert check_for_link('ORD003') is True

    def test_check_for_link_false(self):
        """Test: Link-Existenz-Check negativ"""
        assert check_for_link('NOTHERE') is False


class TestGraphicsManagerLogic:
    """Tests für Grafikmanager-Logik"""

    def test_needs_graphics_manager_no_link(self):
        """Test: Grafikmanager wird benötigt wenn kein Link"""
        # Kein Link -> Grafikmanager nötig
        result = needs_graphics_manager('ORD_NOLINK')

        assert result is True

    def test_needs_graphics_manager_with_link(self, tmp_path, monkeypatch):
        """Test: Kein Grafikmanager wenn Link vorhanden"""
        monkeypatch.chdir(tmp_path)

        save_link('ORD_LINK', 'https://example.com/ready.dst')

        result = needs_graphics_manager('ORD_LINK')

        assert result is False

    def test_should_show_graphics_manager_no_link(self):
        """Test: Grafikmanager anzeigen wenn kein Link"""
        result = should_show_graphics_manager('ORD_SHOW')

        assert result is True

    def test_should_show_graphics_manager_with_link(self, tmp_path, monkeypatch):
        """Test: Grafikmanager nicht anzeigen wenn Link"""
        monkeypatch.chdir(tmp_path)

        save_link('ORD_HIDE', 'https://example.com/file.pes')

        result = should_show_graphics_manager('ORD_HIDE')

        assert result is False


class TestDesignLinkManagerInit:
    """Tests für DesignLinkManager Initialisierung"""

    def test_init_creates_instance(self, design_link_manager):
        """Test: Instanz wird erstellt"""
        assert design_link_manager is not None
        assert isinstance(design_link_manager, DesignLinkManager)

    def test_init_creates_directories(self, design_link_manager):
        """Test: Verzeichnisse werden erstellt"""
        assert os.path.exists(design_link_manager.links_folder)
        assert os.path.exists(design_link_manager.graphics_manager_folder)


class TestURLValidation:
    """Tests für URL-Validierung"""

    def test_validate_url_valid_https(self, design_link_manager):
        """Test: Gültige HTTPS-URL"""
        assert design_link_manager._validate_url('https://example.com/file.png') is True

    def test_validate_url_valid_http(self, design_link_manager):
        """Test: Gültige HTTP-URL"""
        assert design_link_manager._validate_url('http://example.com/design.dst') is True

    def test_validate_url_invalid_no_scheme(self, design_link_manager):
        """Test: URL ohne Schema"""
        assert design_link_manager._validate_url('example.com/file.png') is False

    def test_validate_url_invalid_empty(self, design_link_manager):
        """Test: Leere URL"""
        assert design_link_manager._validate_url('') is False


class TestPlatformDetection:
    """Tests für Plattform-Erkennung"""

    def test_detect_platform_dropbox(self, design_link_manager):
        """Test: Dropbox erkennen"""
        platform = design_link_manager._detect_platform_type('www.dropbox.com')
        assert platform == 'dropbox'

    def test_detect_platform_google_drive(self, design_link_manager):
        """Test: Google Drive erkennen"""
        platform = design_link_manager._detect_platform_type('drive.google.com')
        assert platform == 'google_drive'

    def test_detect_platform_onedrive(self, design_link_manager):
        """Test: OneDrive erkennen"""
        platform = design_link_manager._detect_platform_type('onedrive.live.com')
        assert platform == 'onedrive'

    def test_detect_platform_design_platforms(self, design_link_manager):
        """Test: Design-Plattformen erkennen"""
        assert design_link_manager._detect_platform_type('www.behance.net') == 'behance'
        assert design_link_manager._detect_platform_type('dribbble.com') == 'dribbble'
        assert design_link_manager._detect_platform_type('pinterest.com') == 'pinterest'
        assert design_link_manager._detect_platform_type('instagram.com') == 'instagram'

    def test_detect_platform_generic_website(self, design_link_manager):
        """Test: Generische Website"""
        platform = design_link_manager._detect_platform_type('www.example.com')
        assert platform == 'website'


class TestRequiresGraphicsManager:
    """Tests für Grafikmanager-Anforderung"""

    def test_requires_graphics_manager_embroidery_file(self, design_link_manager):
        """Test: Stickerei-Datei braucht keinen Grafikmanager"""
        link_info = {
            'is_direct_file': True,
            'file_extension': 'dst'
        }

        assert design_link_manager._requires_graphics_manager(link_info) is False

    def test_requires_graphics_manager_vector_file(self, design_link_manager):
        """Test: Vektor-Datei braucht keinen Grafikmanager"""
        link_info = {
            'is_direct_file': True,
            'file_extension': 'svg'
        }

        assert design_link_manager._requires_graphics_manager(link_info) is False

    def test_requires_graphics_manager_image_file(self, design_link_manager):
        """Test: Bild braucht Grafikmanager"""
        link_info = {
            'is_direct_file': True,
            'file_extension': 'jpg'
        }

        assert design_link_manager._requires_graphics_manager(link_info) is True

    def test_requires_graphics_manager_design_platform(self, design_link_manager):
        """Test: Design-Plattform braucht Grafikmanager"""
        link_info = {
            'platform_type': 'behance'
        }

        assert design_link_manager._requires_graphics_manager(link_info) is True


class TestProcessDesignLink:
    """Tests für Design-Link-Verarbeitung"""

    @patch('requests.head')
    def test_process_design_link_success(self, mock_head, design_link_manager):
        """Test: Erfolgreiche Link-Verarbeitung"""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'image/png', 'content-length': '1024'}
        mock_response.history = []
        mock_head.return_value = mock_response

        result = design_link_manager.process_design_link(
            'https://example.com/design.png',
            'ORD001',
            user='testuser'
        )

        assert result['success'] is True
        assert 'link_data' in result
        assert result['link_data']['order_id'] == 'ORD001'

    def test_process_design_link_invalid_url(self, design_link_manager):
        """Test: Ungültige URL"""
        result = design_link_manager.process_design_link(
            'not a url',
            'ORD002'
        )

        assert result['success'] is False
        assert result['requires_graphics_manager'] is True


class TestLinkDataManagement:
    """Tests für Link-Daten-Verwaltung"""

    def test_save_and_get_link_data(self, design_link_manager):
        """Test: Link-Daten speichern und abrufen"""
        link_data = {
            'order_id': 'ORD999',
            'url': 'https://example.com/test.dst',
            'status': 'pending'
        }

        design_link_manager._save_link_data('ORD999', link_data)

        retrieved = design_link_manager.get_link_data('ORD999')

        assert retrieved is not None
        assert retrieved['order_id'] == 'ORD999'
        assert retrieved['url'] == 'https://example.com/test.dst'

    def test_update_link_status(self, design_link_manager):
        """Test: Link-Status aktualisieren"""
        # Erstelle Link
        link_data = {
            'order_id': 'ORD888',
            'url': 'https://example.com/test.png',
            'status': 'pending'
        }
        design_link_manager._save_link_data('ORD888', link_data)

        # Update Status
        success = design_link_manager.update_link_status(
            'ORD888',
            'completed',
            user='admin',
            notes='Verarbeitung abgeschlossen'
        )

        assert success is True

        # Prüfe Update
        updated = design_link_manager.get_link_data('ORD888')
        assert updated['status'] == 'completed'
        assert 'notes' in updated


class TestGraphicsManagerTasks:
    """Tests für Grafikmanager-Aufgaben"""

    @patch('requests.head')
    def test_create_graphics_manager_task(self, mock_head, design_link_manager):
        """Test: Grafikmanager-Aufgabe erstellen"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.history = []
        mock_head.return_value = mock_response

        # Erstelle Link
        link_result = design_link_manager.process_design_link(
            'https://example.com/image.jpg',
            'ORD777'
        )

        # Erstelle Aufgabe
        task_result = design_link_manager.create_graphics_manager_task(
            'ORD777',
            link_result['link_data'],
            user='admin'
        )

        assert task_result['success'] is True
        assert 'task_data' in task_result

    def test_get_graphics_manager_task(self, design_link_manager):
        """Test: Aufgabe abrufen"""
        # Erstelle Aufgabe direkt
        task_data = {
            'order_id': 'ORD666',
            'status': 'pending',
            'type': 'link_processing'
        }

        import json
        task_file = os.path.join(design_link_manager.graphics_manager_folder, 'ORD666_task.json')
        with open(task_file, 'w') as f:
            json.dump(task_data, f)

        # Hole Aufgabe
        retrieved = design_link_manager.get_graphics_manager_task('ORD666')

        assert retrieved is not None
        assert retrieved['order_id'] == 'ORD666'


class TestHelperFunctions:
    """Tests für Helper-Funktionen"""

    @patch('requests.head')
    def test_process_design_link_helper(self, mock_head, tmp_path, monkeypatch):
        """Test: Helper-Funktion process_design_link"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.history = []
        mock_head.return_value = mock_response

        # Temp manager
        from src.utils.design_link_manager import link_manager
        link_manager.links_folder = str(tmp_path / "links")
        link_manager.graphics_manager_folder = str(tmp_path / "graphics")
        link_manager.ensure_directories()

        result = process_design_link('https://example.com/test.dst', 'ORD555')

        assert result['success'] is True

    def test_check_link_exists_helper(self, design_link_manager, monkeypatch):
        """Test: Helper-Funktion check_link_exists"""
        # Mock link_manager
        monkeypatch.setattr('src.utils.design_link_manager.link_manager', design_link_manager)

        # Erstelle Link
        link_data = {'order_id': 'ORD444', 'url': 'https://test.com'}
        design_link_manager._save_link_data('ORD444', link_data)

        assert check_link_exists('ORD444') is True
        assert check_link_exists('NOTHERE') is False


class TestIntegration:
    """Integrationstests für Design Upload & Link Management"""

    @patch('requests.head')
    def test_full_link_workflow(self, mock_head, design_link_manager):
        """Test: Vollständiger Link-Workflow"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {'content-type': 'image/png'}
        mock_response.history = []
        mock_head.return_value = mock_response

        # 1. Link verarbeiten
        result = design_link_manager.process_design_link(
            'https://example.com/design.png',
            'ORD_FLOW',
            user='testuser'
        )

        assert result['success'] is True

        # 2. Link-Daten prüfen
        link_data = design_link_manager.get_link_data('ORD_FLOW')
        assert link_data is not None

        # 3. Grafikmanager-Task erstellen (wenn nötig)
        if result['requires_graphics_manager']:
            task_result = design_link_manager.create_graphics_manager_task(
                'ORD_FLOW',
                link_data,
                user='admin'
            )
            assert task_result['success'] is True

        # 4. Status aktualisieren
        success = design_link_manager.update_link_status('ORD_FLOW', 'in_progress')
        assert success is True

        # 5. Final status
        updated_data = design_link_manager.get_link_data('ORD_FLOW')
        assert updated_data['status'] == 'in_progress'
