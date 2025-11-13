"""
Unit Tests für Customer History
Testet die Kunden-Historie-Verwaltung
"""

import pytest
import json
import os
import tempfile
from datetime import datetime
from src.utils import customer_history


@pytest.fixture
def temp_history_file(monkeypatch):
    """Fixture für temporäre Historie-Datei"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
    temp_file.close()

    monkeypatch.setattr(customer_history, 'CUSTOMER_HISTORY_FILE', temp_file.name)

    yield temp_file.name

    # Cleanup
    try:
        os.unlink(temp_file.name)
    except:
        pass


@pytest.fixture
def sample_history():
    """Fixture für Beispiel-Historie"""
    return {
        'CUST001': [
            {
                'timestamp': '2025-01-01T10:00:00',
                'action': 'created',
                'details': 'Kunde wurde erstellt',
                'user': 'admin'
            },
            {
                'timestamp': '2025-01-01T11:00:00',
                'action': 'updated',
                'details': 'Adresse aktualisiert',
                'user': 'user1'
            }
        ],
        'CUST002': [
            {
                'timestamp': '2025-01-02T10:00:00',
                'action': 'created',
                'details': 'Kunde wurde erstellt',
                'user': 'admin'
            }
        ]
    }


class TestLoadCustomerHistory:
    """Tests für load_customer_history Funktion"""

    def test_load_nonexistent_file(self, temp_history_file):
        """Test: Nicht existierende Datei"""
        os.unlink(temp_history_file)

        history = customer_history.load_customer_history()
        assert history == {}

    def test_load_empty_file(self, temp_history_file):
        """Test: Leere Datei"""
        with open(temp_history_file, 'w') as f:
            f.write('{}')

        history = customer_history.load_customer_history()
        assert history == {}

    def test_load_valid_history(self, temp_history_file, sample_history):
        """Test: Gültige Historie laden"""
        with open(temp_history_file, 'w') as f:
            json.dump(sample_history, f)

        history = customer_history.load_customer_history()
        assert len(history) == 2
        assert 'CUST001' in history
        assert 'CUST002' in history
        assert len(history['CUST001']) == 2

    def test_load_with_unicode(self, temp_history_file):
        """Test: Unicode-Zeichen korrekt laden"""
        unicode_history = {
            'CUST001': [
                {
                    'timestamp': '2025-01-01T10:00:00',
                    'action': 'updated',
                    'details': 'Straße geändert: Müller-Lüdenscheidt',
                    'user': 'admin'
                }
            ]
        }

        with open(temp_history_file, 'w', encoding='utf-8') as f:
            json.dump(unicode_history, f, ensure_ascii=False)

        history = customer_history.load_customer_history()
        assert 'Müller-Lüdenscheidt' in history['CUST001'][0]['details']


class TestSaveCustomerHistory:
    """Tests für save_customer_history Funktion"""

    def test_save_empty_history(self, temp_history_file):
        """Test: Leere Historie speichern"""
        customer_history.save_customer_history({})

        with open(temp_history_file, 'r') as f:
            data = json.load(f)

        assert data == {}

    def test_save_history(self, temp_history_file, sample_history):
        """Test: Historie speichern"""
        customer_history.save_customer_history(sample_history)

        with open(temp_history_file, 'r') as f:
            data = json.load(f)

        assert len(data) == 2
        assert 'CUST001' in data
        assert len(data['CUST001']) == 2

    def test_save_with_unicode(self, temp_history_file):
        """Test: Unicode-Zeichen korrekt speichern"""
        unicode_history = {
            'CUST001': [
                {
                    'timestamp': '2025-01-01T10:00:00',
                    'action': 'updated',
                    'details': 'Änderung: ÄÖÜßäöü',
                    'user': 'admin'
                }
            ]
        }

        customer_history.save_customer_history(unicode_history)

        with open(temp_history_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # ensure_ascii=False sollte Unicode korrekt speichern
        assert 'ÄÖÜßäöü' in content

    def test_save_formatting(self, temp_history_file, sample_history):
        """Test: Historie wird formatiert gespeichert"""
        customer_history.save_customer_history(sample_history)

        with open(temp_history_file, 'r') as f:
            content = f.read()

        # JSON sollte eingerückt sein (indent=2)
        assert '  "CUST001"' in content or '  {' in content


class TestAddCustomerHistory:
    """Tests für add_customer_history Funktion"""

    def test_add_to_new_customer(self, temp_history_file):
        """Test: Eintrag für neuen Kunden hinzufügen"""
        customer_history.add_customer_history(
            customer_id='CUST001',
            action='created',
            details='Kunde wurde erstellt'
        )

        history = customer_history.load_customer_history()
        assert 'CUST001' in history
        assert len(history['CUST001']) == 1
        assert history['CUST001'][0]['action'] == 'created'
        assert history['CUST001'][0]['details'] == 'Kunde wurde erstellt'
        assert history['CUST001'][0]['user'] == 'system'  # Default

    def test_add_to_existing_customer(self, temp_history_file, sample_history):
        """Test: Eintrag für existierenden Kunden hinzufügen"""
        customer_history.save_customer_history(sample_history)

        customer_history.add_customer_history(
            customer_id='CUST001',
            action='order_created',
            details='Auftrag O001 erstellt',
            user='admin'
        )

        history = customer_history.load_customer_history()
        assert len(history['CUST001']) == 3
        # Neueste zuerst (insert(0))
        assert history['CUST001'][0]['action'] == 'order_created'
        assert history['CUST001'][0]['user'] == 'admin'

    def test_add_with_custom_user(self, temp_history_file):
        """Test: Eintrag mit benutzerdefiniertem User"""
        customer_history.add_customer_history(
            customer_id='CUST001',
            action='updated',
            details='Kunde aktualisiert',
            user='testuser'
        )

        history = customer_history.load_customer_history()
        assert history['CUST001'][0]['user'] == 'testuser'

    def test_add_timestamp_is_valid(self, temp_history_file):
        """Test: Timestamp wird korrekt gesetzt"""
        before = datetime.now()
        customer_history.add_customer_history('CUST001', 'action', 'details')
        after = datetime.now()

        history = customer_history.load_customer_history()
        timestamp = datetime.fromisoformat(history['CUST001'][0]['timestamp'])

        assert before <= timestamp <= after

    def test_add_multiple_customers(self, temp_history_file):
        """Test: Mehrere Kunden"""
        customer_history.add_customer_history('CUST001', 'created', 'Kunde 1')
        customer_history.add_customer_history('CUST002', 'created', 'Kunde 2')
        customer_history.add_customer_history('CUST003', 'created', 'Kunde 3')

        history = customer_history.load_customer_history()
        assert len(history) == 3
        assert 'CUST001' in history
        assert 'CUST002' in history
        assert 'CUST003' in history

    def test_add_limit_100_entries(self, temp_history_file):
        """Test: Maximum 100 Einträge pro Kunde"""
        # Füge 105 Einträge hinzu
        for i in range(105):
            customer_history.add_customer_history(
                'CUST001',
                'action',
                f'Entry {i}'
            )

        history = customer_history.load_customer_history()
        assert len(history['CUST001']) == 100
        # Die neuesten 100 sollten behalten werden
        # Neueste ist Entry 104 (da insert(0) verwendet wird)
        assert history['CUST001'][0]['details'] == 'Entry 104'
        # Älteste ist Entry 5
        assert history['CUST001'][99]['details'] == 'Entry 5'

    def test_add_newest_first_order(self, temp_history_file):
        """Test: Neueste Einträge zuerst"""
        customer_history.add_customer_history('CUST001', 'action1', 'First')
        customer_history.add_customer_history('CUST001', 'action2', 'Second')
        customer_history.add_customer_history('CUST001', 'action3', 'Third')

        history = customer_history.load_customer_history()
        assert history['CUST001'][0]['details'] == 'Third'  # Neueste
        assert history['CUST001'][1]['details'] == 'Second'
        assert history['CUST001'][2]['details'] == 'First'  # Älteste


class TestGetCustomerHistory:
    """Tests für get_customer_history Funktion"""

    def test_get_existing_customer(self, temp_history_file, sample_history):
        """Test: Historie für existierenden Kunden abrufen"""
        customer_history.save_customer_history(sample_history)

        hist = customer_history.get_customer_history('CUST001')
        assert len(hist) == 2
        assert hist[0]['action'] == 'created'

    def test_get_nonexistent_customer(self, temp_history_file):
        """Test: Nicht existierender Kunde"""
        hist = customer_history.get_customer_history('NONEXISTENT')
        assert hist == []

    def test_get_with_limit(self, temp_history_file):
        """Test: Limit-Parameter"""
        # Erstelle 10 Einträge
        for i in range(10):
            customer_history.add_customer_history(
                'CUST001',
                'action',
                f'Entry {i}'
            )

        hist = customer_history.get_customer_history('CUST001', limit=5)
        assert len(hist) == 5
        # Sollte die neuesten 5 zurückgeben
        assert hist[0]['details'] == 'Entry 9'  # Neueste
        assert hist[4]['details'] == 'Entry 5'

    def test_get_default_limit_20(self, temp_history_file):
        """Test: Default Limit ist 20"""
        # Erstelle 30 Einträge
        for i in range(30):
            customer_history.add_customer_history(
                'CUST001',
                'action',
                f'Entry {i}'
            )

        hist = customer_history.get_customer_history('CUST001')
        assert len(hist) == 20  # Default limit

    def test_get_less_than_limit(self, temp_history_file):
        """Test: Weniger Einträge als Limit"""
        customer_history.add_customer_history('CUST001', 'action1', 'Entry 1')
        customer_history.add_customer_history('CUST001', 'action2', 'Entry 2')

        hist = customer_history.get_customer_history('CUST001', limit=10)
        assert len(hist) == 2  # Nur 2 Einträge vorhanden

    def test_get_empty_history(self, temp_history_file):
        """Test: Leere Historie"""
        # Datei existiert nicht
        hist = customer_history.get_customer_history('CUST001')
        assert hist == []


class TestClearCustomerHistory:
    """Tests für clear_customer_history Funktion"""

    def test_clear_existing_customer(self, temp_history_file, sample_history):
        """Test: Historie für existierenden Kunden löschen"""
        customer_history.save_customer_history(sample_history)

        customer_history.clear_customer_history('CUST001')

        history = customer_history.load_customer_history()
        assert 'CUST001' not in history
        assert 'CUST002' in history  # Andere Kunden bleiben

    def test_clear_nonexistent_customer(self, temp_history_file, sample_history):
        """Test: Nicht existierenden Kunden löschen"""
        customer_history.save_customer_history(sample_history)

        # Sollte keinen Fehler werfen
        customer_history.clear_customer_history('NONEXISTENT')

        history = customer_history.load_customer_history()
        assert len(history) == 2  # Keine Änderung

    def test_clear_last_customer(self, temp_history_file):
        """Test: Letzten Kunden löschen"""
        customer_history.add_customer_history('CUST001', 'created', 'Test')
        customer_history.clear_customer_history('CUST001')

        history = customer_history.load_customer_history()
        assert history == {}

    def test_clear_empty_history(self, temp_history_file):
        """Test: Leere Historie"""
        # Sollte keinen Fehler werfen
        customer_history.clear_customer_history('CUST001')

        history = customer_history.load_customer_history()
        assert history == {}


class TestIntegration:
    """Integrationstests für Customer History"""

    def test_full_workflow(self, temp_history_file):
        """Test: Vollständiger Workflow"""
        # 1. Kunde erstellt
        customer_history.add_customer_history(
            'CUST001',
            'created',
            'Kunde Max Mustermann erstellt',
            user='admin'
        )

        # 2. Adresse aktualisiert
        customer_history.add_customer_history(
            'CUST001',
            'updated',
            'Adresse geändert',
            user='user1'
        )

        # 3. Auftrag erstellt
        customer_history.add_customer_history(
            'CUST001',
            'order_created',
            'Auftrag O001 erstellt',
            user='user1'
        )

        # 4. Historie abrufen
        hist = customer_history.get_customer_history('CUST001')
        assert len(hist) == 3
        assert hist[0]['action'] == 'order_created'  # Neueste
        assert hist[1]['action'] == 'updated'
        assert hist[2]['action'] == 'created'  # Älteste

        # 5. Historie löschen
        customer_history.clear_customer_history('CUST001')
        hist = customer_history.get_customer_history('CUST001')
        assert hist == []

    def test_multiple_customers_workflow(self, temp_history_file):
        """Test: Mehrere Kunden gleichzeitig"""
        # Kunde 1
        customer_history.add_customer_history('CUST001', 'created', 'Kunde 1')
        customer_history.add_customer_history('CUST001', 'updated', 'Update 1')

        # Kunde 2
        customer_history.add_customer_history('CUST002', 'created', 'Kunde 2')
        customer_history.add_customer_history('CUST002', 'order', 'Auftrag 1')
        customer_history.add_customer_history('CUST002', 'payment', 'Zahlung')

        # Prüfe Historien sind unabhängig
        hist1 = customer_history.get_customer_history('CUST001')
        hist2 = customer_history.get_customer_history('CUST002')

        assert len(hist1) == 2
        assert len(hist2) == 3
        assert hist1[0]['details'] == 'Update 1'
        assert hist2[0]['details'] == 'Zahlung'

    def test_persistence(self, temp_history_file):
        """Test: Historie bleibt nach Neustart erhalten"""
        # Erstelle Historie
        customer_history.add_customer_history('CUST001', 'created', 'Kunde erstellt')
        customer_history.add_customer_history('CUST001', 'updated', 'Kunde aktualisiert')

        # "Neustart" simulieren - Historie neu laden
        history = customer_history.load_customer_history()
        assert 'CUST001' in history
        assert len(history['CUST001']) == 2
