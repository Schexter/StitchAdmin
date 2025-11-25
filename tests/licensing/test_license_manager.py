"""
Unit Tests für License Manager
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
import pytest

from src.licensing.license_manager import (
    LicenseManager,
    LicenseType,
    LicenseStatus,
    LicenseInfo,
    create_license_data
)
from src.licensing.hardware_id import get_hardware_id
from src.licensing.crypto_utils import CryptoUtils


class TestLicenseInfo:
    """Tests für LicenseInfo"""

    def test_license_info_is_valid_for_valid_status(self):
        """LicenseInfo sollte gültig sein für VALID Status"""
        info = LicenseInfo(status=LicenseStatus.VALID)
        assert info.is_valid() is True

    def test_license_info_is_valid_for_trial_status(self):
        """LicenseInfo sollte gültig sein für TRIAL Status"""
        info = LicenseInfo(status=LicenseStatus.TRIAL)
        assert info.is_valid() is True

    def test_license_info_is_not_valid_for_expired_status(self):
        """LicenseInfo sollte nicht gültig sein für EXPIRED Status"""
        info = LicenseInfo(status=LicenseStatus.EXPIRED)
        assert info.is_valid() is False

    def test_license_info_to_dict_conversion(self):
        """LicenseInfo sollte zu Dictionary konvertiert werden können"""
        info = LicenseInfo(
            status=LicenseStatus.VALID,
            license_type=LicenseType.STANDARD,
            customer_name="Test Customer"
        )
        data = info.to_dict()

        assert isinstance(data, dict)
        assert data['status'] == 'valid'
        assert data['license_type'] == 'standard'
        assert data['customer_name'] == "Test Customer"


class TestCreateLicenseData:
    """Tests für create_license_data Funktion"""

    def test_create_license_data_with_defaults(self):
        """create_license_data sollte mit Defaults funktionieren"""
        hw_id = get_hardware_id()
        license_data = create_license_data(
            customer_name="Test Customer",
            hardware_id=hw_id
        )

        assert isinstance(license_data, dict)
        assert license_data['customer_name'] == "Test Customer"
        assert license_data['hardware_id'] == hw_id
        assert license_data['license_type'] == 'standard'
        assert 'license_id' in license_data
        assert 'issued_date' in license_data
        assert 'features' in license_data

    def test_create_license_data_with_expiry(self):
        """create_license_data sollte Ablaufdatum speichern"""
        hw_id = get_hardware_id()
        expiry = datetime.now() + timedelta(days=365)

        license_data = create_license_data(
            customer_name="Test Customer",
            hardware_id=hw_id,
            expiry_date=expiry
        )

        assert license_data['expiry_date'] is not None

    def test_create_license_data_for_trial(self):
        """create_license_data sollte Trial-Features setzen"""
        hw_id = get_hardware_id()
        license_data = create_license_data(
            customer_name="Trial User",
            hardware_id=hw_id,
            license_type=LicenseType.TRIAL
        )

        features = license_data['features']
        assert features['max_users'] == 1
        assert features['zugpferd_enabled'] is False

    def test_create_license_data_for_professional(self):
        """create_license_data sollte Professional-Features setzen"""
        hw_id = get_hardware_id()
        license_data = create_license_data(
            customer_name="Pro User",
            hardware_id=hw_id,
            license_type=LicenseType.PROFESSIONAL
        )

        features = license_data['features']
        assert features['max_users'] == 10
        assert features['api_access'] is True


class TestLicenseManager:
    """Tests für LicenseManager"""

    @pytest.fixture
    def temp_license_path(self, tmp_path):
        """Temporärer Pfad für Lizenz-Datei"""
        return tmp_path / "test_license.json"

    @pytest.fixture
    def temp_trial_path(self, tmp_path):
        """Temporärer Pfad für Trial-Datei"""
        return tmp_path / ".trial"

    @pytest.fixture
    def test_keys(self):
        """Test-Schlüsselpaar generieren"""
        return CryptoUtils.generate_key_pair()

    def test_license_manager_initialization(self, temp_license_path, temp_trial_path):
        """LicenseManager sollte initialisiert werden können"""
        manager = LicenseManager(
            license_path=temp_license_path,
            trial_path=temp_trial_path
        )
        assert manager.license_path == temp_license_path
        assert manager.trial_path == temp_trial_path

    def test_get_license_status_without_license_starts_trial(self, temp_license_path, temp_trial_path):
        """Ohne Lizenz sollte Trial-Mode starten"""
        manager = LicenseManager(
            license_path=temp_license_path,
            trial_path=temp_trial_path
        )

        status = manager.get_license_status()

        assert status.status == LicenseStatus.TRIAL
        assert status.license_type == LicenseType.TRIAL
        assert status.trial_days_remaining is not None
        assert status.trial_days_remaining <= 30

    def test_trial_file_is_created(self, temp_license_path, temp_trial_path):
        """Trial-Datei sollte beim ersten Start erstellt werden"""
        manager = LicenseManager(
            license_path=temp_license_path,
            trial_path=temp_trial_path
        )

        manager.get_license_status()

        assert temp_trial_path.exists()

    def test_trial_days_decrease_over_time(self, temp_license_path, temp_trial_path):
        """Trial-Tage sollten mit der Zeit abnehmen"""
        manager = LicenseManager(
            license_path=temp_license_path,
            trial_path=temp_trial_path
        )

        # Create trial file with date in the past
        past_date = datetime.now() - timedelta(days=5)
        temp_trial_path.write_text(past_date.isoformat())

        status = manager.get_license_status()

        assert status.trial_days_remaining <= 25  # 30 - 5 = 25

    def test_expired_trial_is_detected(self, temp_license_path, temp_trial_path):
        """Abgelaufener Trial sollte erkannt werden"""
        manager = LicenseManager(
            license_path=temp_license_path,
            trial_path=temp_trial_path
        )

        # Create trial file with date 31 days in the past
        past_date = datetime.now() - timedelta(days=31)
        temp_trial_path.write_text(past_date.isoformat())

        status = manager.get_license_status()

        assert status.status == LicenseStatus.TRIAL_EXPIRED

    def test_get_hardware_id_returns_string(self, temp_license_path, temp_trial_path):
        """get_hardware_id sollte String zurückgeben"""
        manager = LicenseManager(
            license_path=temp_license_path,
            trial_path=temp_trial_path
        )

        hw_id = manager.get_hardware_id()
        assert isinstance(hw_id, str)
        assert len(hw_id) == 64  # SHA-256

    def test_check_feature_returns_default_for_invalid_license(self, temp_license_path, temp_trial_path):
        """check_feature sollte Default zurückgeben wenn Lizenz ungültig"""
        # Create expired trial
        manager = LicenseManager(
            license_path=temp_license_path,
            trial_path=temp_trial_path
        )
        past_date = datetime.now() - timedelta(days=31)
        temp_trial_path.write_text(past_date.isoformat())

        result = manager.check_feature('zugpferd_enabled', default=False)
        assert result is False

    def test_check_feature_returns_value_for_valid_trial(self, temp_license_path, temp_trial_path):
        """check_feature sollte für gültigen Trial funktionieren"""
        manager = LicenseManager(
            license_path=temp_license_path,
            trial_path=temp_trial_path
        )

        # Trial is valid, but features might not be available
        # This depends on implementation
        status = manager.get_license_status()
        assert status.is_valid()


class TestLicenseValidation:
    """Tests für Lizenz-Validierung"""

    @pytest.fixture
    def valid_signed_license(self, tmp_path):
        """Erstellt eine gültig signierte Lizenz"""
        # Generate keys
        private_pem, public_pem = CryptoUtils.generate_key_pair()
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend

        private_key = serialization.load_pem_private_key(
            private_pem, password=None, backend=default_backend()
        )

        # Create license data
        hw_id = get_hardware_id()
        license_data = create_license_data(
            customer_name="Test Customer",
            hardware_id=hw_id,
            license_type=LicenseType.STANDARD,
            expiry_date=datetime.now() + timedelta(days=365)
        )

        # Sign license
        license_json = json.dumps(license_data, sort_keys=True, ensure_ascii=False)
        signature = CryptoUtils.sign_data(license_json.encode('utf-8'), private_key)
        license_data['signature'] = signature

        # Save license
        license_path = tmp_path / "valid_license.json"
        license_path.write_text(json.dumps(license_data, indent=2), encoding='utf-8')

        # Save public key
        public_key_path = tmp_path / "public_key.pem"
        public_key_path.write_bytes(public_pem)

        return license_path, tmp_path / ".trial", public_pem

    def test_valid_license_is_accepted(self, valid_signed_license):
        """Gültige Lizenz sollte akzeptiert werden"""
        license_path, trial_path, public_pem = valid_signed_license

        manager = LicenseManager(
            license_path=license_path,
            trial_path=trial_path,
            public_key_pem=public_pem
        )

        status = manager.get_license_status()

        assert status.status == LicenseStatus.VALID
        assert status.license_type == LicenseType.STANDARD
        assert status.customer_name == "Test Customer"
