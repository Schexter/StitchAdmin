"""
Unit Tests für Activity Logger
Testet die Aktivitäts-Protokollierung
"""

import pytest
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from src.utils import activity_logger


@pytest.fixture
def temp_log_file(monkeypatch):
    """Fixture für temporäre Log-Datei"""
    # Erstelle temporäre Datei
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
    temp_file.close()

    # Setze ACTIVITY_LOG_FILE auf temporäre Datei
    monkeypatch.setattr(activity_logger, 'ACTIVITY_LOG_FILE', temp_file.name)

    yield temp_file.name

    # Cleanup
    try:
        os.unlink(temp_file.name)
    except:
        pass


@pytest.fixture
def sample_logs():
    """Fixture für Beispiel-Logs"""
    return [
        {
            'id': 1,
            'timestamp': '2025-01-01T10:00:00',
            'username': 'user1',
            'action': 'login',
            'details': 'Benutzer hat sich angemeldet',
            'ip_address': '192.168.1.1'
        },
        {
            'id': 2,
            'timestamp': '2025-01-01T10:05:00',
            'username': 'user2',
            'action': 'create_article',
            'details': 'Artikel ART001 erstellt',
            'ip_address': '192.168.1.2'
        },
        {
            'id': 3,
            'timestamp': '2025-01-01T10:10:00',
            'username': 'user1',
            'action': 'update_customer',
            'details': 'Kunde CUST001 aktualisiert',
            'ip_address': '192.168.1.1'
        }
    ]


class TestLogActivity:
    """Tests für log_activity Funktion"""

    def test_log_activity_basic(self, temp_log_file):
        """Test: Einfacher Log-Eintrag"""
        activity_logger.log_activity(
            username='testuser',
            action='login',
            details='Test Login'
        )

        logs = activity_logger.load_activity_logs()
        assert len(logs) == 1
        assert logs[0]['username'] == 'testuser'
        assert logs[0]['action'] == 'login'
        assert logs[0]['details'] == 'Test Login'
        assert logs[0]['ip_address'] == 'N/A'
        assert logs[0]['id'] == 1

    def test_log_activity_with_ip(self, temp_log_file):
        """Test: Log-Eintrag mit IP-Adresse"""
        activity_logger.log_activity(
            username='testuser',
            action='login',
            details='Test Login',
            ip_address='127.0.0.1'
        )

        logs = activity_logger.load_activity_logs()
        assert logs[0]['ip_address'] == '127.0.0.1'

    def test_log_activity_timestamp(self, temp_log_file):
        """Test: Timestamp wird korrekt gesetzt"""
        before = datetime.now()
        activity_logger.log_activity('user', 'action', 'details')
        after = datetime.now()

        logs = activity_logger.load_activity_logs()
        timestamp = datetime.fromisoformat(logs[0]['timestamp'])

        assert before <= timestamp <= after

    def test_log_activity_multiple_entries(self, temp_log_file):
        """Test: Mehrere Log-Einträge"""
        activity_logger.log_activity('user1', 'login', 'Login 1')
        activity_logger.log_activity('user2', 'logout', 'Logout 2')
        activity_logger.log_activity('user3', 'create', 'Create 3')

        logs = activity_logger.load_activity_logs()
        assert len(logs) == 3
        assert logs[0]['username'] == 'user1'
        assert logs[1]['username'] == 'user2'
        assert logs[2]['username'] == 'user3'

    def test_log_activity_incremental_ids(self, temp_log_file):
        """Test: IDs werden inkrementell vergeben"""
        activity_logger.log_activity('user1', 'action1', 'details1')
        activity_logger.log_activity('user2', 'action2', 'details2')
        activity_logger.log_activity('user3', 'action3', 'details3')

        logs = activity_logger.load_activity_logs()
        assert logs[0]['id'] == 1
        assert logs[1]['id'] == 2
        assert logs[2]['id'] == 3

    def test_log_activity_max_1000_entries(self, temp_log_file):
        """Test: Maximal 1000 Einträge werden gespeichert"""
        # Erstelle 1050 Einträge
        for i in range(1050):
            activity_logger.log_activity(f'user{i}', 'action', f'details {i}')

        logs = activity_logger.load_activity_logs()
        assert len(logs) == 1000
        # Die ältesten 50 sollten gelöscht sein
        assert logs[0]['details'] == 'details 50'
        assert logs[-1]['details'] == 'details 1049'


class TestLoadActivityLogs:
    """Tests für load_activity_logs Funktion"""

    def test_load_nonexistent_file(self, temp_log_file):
        """Test: Nicht existierende Datei"""
        os.unlink(temp_log_file)  # Lösche temp Datei

        logs = activity_logger.load_activity_logs()
        assert logs == []

    def test_load_empty_file(self, temp_log_file):
        """Test: Leere Datei"""
        with open(temp_log_file, 'w') as f:
            f.write('[]')

        logs = activity_logger.load_activity_logs()
        assert logs == []

    def test_load_valid_logs(self, temp_log_file, sample_logs):
        """Test: Gültige Logs laden"""
        with open(temp_log_file, 'w') as f:
            json.dump(sample_logs, f)

        logs = activity_logger.load_activity_logs()
        assert len(logs) == 3
        assert logs[0]['username'] == 'user1'
        assert logs[1]['username'] == 'user2'

    def test_load_corrupted_file(self, temp_log_file):
        """Test: Korrupte JSON-Datei"""
        with open(temp_log_file, 'w') as f:
            f.write('{ invalid json }')

        # Sollte leere Liste zurückgeben bei Fehler
        logs = activity_logger.load_activity_logs()
        assert logs == []


class TestSaveActivityLogs:
    """Tests für save_activity_logs Funktion"""

    def test_save_empty_logs(self, temp_log_file):
        """Test: Leere Logs speichern"""
        activity_logger.save_activity_logs([])

        with open(temp_log_file, 'r') as f:
            data = json.load(f)

        assert data == []

    def test_save_logs(self, temp_log_file, sample_logs):
        """Test: Logs speichern"""
        activity_logger.save_activity_logs(sample_logs)

        with open(temp_log_file, 'r') as f:
            data = json.load(f)

        assert len(data) == 3
        assert data[0]['username'] == 'user1'
        assert data[1]['action'] == 'create_article'

    def test_save_logs_formatting(self, temp_log_file, sample_logs):
        """Test: Logs werden formatiert gespeichert"""
        activity_logger.save_activity_logs(sample_logs)

        with open(temp_log_file, 'r') as f:
            content = f.read()

        # JSON sollte eingerückt sein (indent=2)
        assert '  {' in content or '  "id"' in content


class TestGetUserActivities:
    """Tests für get_user_activities Funktion"""

    def test_get_user_activities_basic(self, temp_log_file, sample_logs):
        """Test: Aktivitäten eines Benutzers abrufen"""
        activity_logger.save_activity_logs(sample_logs)

        user1_logs = activity_logger.get_user_activities('user1')
        assert len(user1_logs) == 2
        assert all(log['username'] == 'user1' for log in user1_logs)

    def test_get_user_activities_nonexistent_user(self, temp_log_file, sample_logs):
        """Test: Nicht existierender Benutzer"""
        activity_logger.save_activity_logs(sample_logs)

        logs = activity_logger.get_user_activities('nonexistent')
        assert logs == []

    def test_get_user_activities_with_limit(self, temp_log_file):
        """Test: Limit-Parameter"""
        # Erstelle 10 Logs für user1
        logs = [
            {
                'id': i,
                'timestamp': f'2025-01-01T10:{i:02d}:00',
                'username': 'user1',
                'action': 'action',
                'details': f'details {i}',
                'ip_address': 'N/A'
            }
            for i in range(10)
        ]
        activity_logger.save_activity_logs(logs)

        user_logs = activity_logger.get_user_activities('user1', limit=5)
        assert len(user_logs) == 5
        # Sollte die neuesten 5 zurückgeben
        assert user_logs[0]['id'] == 5
        assert user_logs[-1]['id'] == 9

    def test_get_user_activities_empty_logs(self, temp_log_file):
        """Test: Leere Logs"""
        logs = activity_logger.get_user_activities('anyuser')
        assert logs == []


class TestGetRecentActivities:
    """Tests für get_recent_activities Funktion"""

    def test_get_recent_activities_basic(self, temp_log_file, sample_logs):
        """Test: Neueste Aktivitäten abrufen"""
        activity_logger.save_activity_logs(sample_logs)

        recent = activity_logger.get_recent_activities()
        assert len(recent) == 3
        # Sollte in umgekehrter Reihenfolge sein (neueste zuerst)
        assert recent[0]['id'] == 3
        assert recent[1]['id'] == 2
        assert recent[2]['id'] == 1

    def test_get_recent_activities_with_limit(self, temp_log_file):
        """Test: Limit-Parameter"""
        logs = [
            {
                'id': i,
                'timestamp': f'2025-01-01T10:{i:02d}:00',
                'username': f'user{i}',
                'action': 'action',
                'details': f'details {i}',
                'ip_address': 'N/A'
            }
            for i in range(10)
        ]
        activity_logger.save_activity_logs(logs)

        recent = activity_logger.get_recent_activities(limit=3)
        assert len(recent) == 3
        # Neueste zuerst
        assert recent[0]['id'] == 9
        assert recent[1]['id'] == 8
        assert recent[2]['id'] == 7

    def test_get_recent_activities_empty_logs(self, temp_log_file):
        """Test: Leere Logs"""
        recent = activity_logger.get_recent_activities()
        assert recent == []


class TestGetActivitiesByAction:
    """Tests für get_activities_by_action Funktion"""

    def test_get_activities_by_action_basic(self, temp_log_file, sample_logs):
        """Test: Aktivitäten nach Aktion filtern"""
        activity_logger.save_activity_logs(sample_logs)

        login_logs = activity_logger.get_activities_by_action('login')
        assert len(login_logs) == 1
        assert login_logs[0]['action'] == 'login'

    def test_get_activities_by_action_multiple(self, temp_log_file):
        """Test: Mehrere Aktivitäten gleicher Aktion"""
        logs = [
            {'id': 1, 'timestamp': '2025-01-01T10:00:00', 'username': 'user1',
             'action': 'login', 'details': 'Login 1', 'ip_address': 'N/A'},
            {'id': 2, 'timestamp': '2025-01-01T10:01:00', 'username': 'user2',
             'action': 'logout', 'details': 'Logout 1', 'ip_address': 'N/A'},
            {'id': 3, 'timestamp': '2025-01-01T10:02:00', 'username': 'user3',
             'action': 'login', 'details': 'Login 2', 'ip_address': 'N/A'},
        ]
        activity_logger.save_activity_logs(logs)

        login_logs = activity_logger.get_activities_by_action('login')
        assert len(login_logs) == 2
        # Neueste zuerst
        assert login_logs[0]['id'] == 3
        assert login_logs[1]['id'] == 1

    def test_get_activities_by_action_nonexistent(self, temp_log_file, sample_logs):
        """Test: Nicht existierende Aktion"""
        activity_logger.save_activity_logs(sample_logs)

        logs = activity_logger.get_activities_by_action('nonexistent')
        assert logs == []

    def test_get_activities_by_action_with_limit(self, temp_log_file):
        """Test: Limit-Parameter"""
        logs = [
            {
                'id': i,
                'timestamp': f'2025-01-01T10:{i:02d}:00',
                'username': f'user{i}',
                'action': 'test_action',
                'details': f'details {i}',
                'ip_address': 'N/A'
            }
            for i in range(10)
        ]
        activity_logger.save_activity_logs(logs)

        action_logs = activity_logger.get_activities_by_action('test_action', limit=3)
        assert len(action_logs) == 3
        # Neueste zuerst
        assert action_logs[0]['id'] == 9
        assert action_logs[1]['id'] == 8
        assert action_logs[2]['id'] == 7


class TestIntegration:
    """Integrationstests für Activity Logger"""

    def test_full_workflow(self, temp_log_file):
        """Test: Vollständiger Workflow"""
        # 1. Logs erstellen
        activity_logger.log_activity('admin', 'login', 'Admin logged in', '192.168.1.1')
        activity_logger.log_activity('user1', 'create_order', 'Order O001 created', '192.168.1.2')
        activity_logger.log_activity('admin', 'update_settings', 'Settings updated', '192.168.1.1')
        activity_logger.log_activity('user2', 'login', 'User2 logged in', '192.168.1.3')

        # 2. Alle Logs abrufen
        all_logs = activity_logger.load_activity_logs()
        assert len(all_logs) == 4

        # 3. Admin-Aktivitäten abrufen
        admin_logs = activity_logger.get_user_activities('admin')
        assert len(admin_logs) == 2
        assert all(log['username'] == 'admin' for log in admin_logs)

        # 4. Login-Aktivitäten abrufen
        login_logs = activity_logger.get_activities_by_action('login')
        assert len(login_logs) == 2

        # 5. Neueste Aktivitäten abrufen
        recent = activity_logger.get_recent_activities(limit=2)
        assert len(recent) == 2
        assert recent[0]['username'] == 'user2'  # Neueste
        assert recent[1]['username'] == 'admin'

    def test_persistence(self, temp_log_file):
        """Test: Logs bleiben nach Neustart erhalten"""
        # Erstelle Logs
        activity_logger.log_activity('user1', 'action1', 'details1')
        activity_logger.log_activity('user2', 'action2', 'details2')

        # "Neustart" simulieren - Logs neu laden
        logs = activity_logger.load_activity_logs()
        assert len(logs) == 2
        assert logs[0]['username'] == 'user1'
        assert logs[1]['username'] == 'user2'
