"""
Unit Tests für Hardware-ID Generator
"""

import pytest
from src.licensing.hardware_id import HardwareIDGenerator, get_hardware_id


class TestHardwareIDGenerator:
    """Tests für HardwareIDGenerator"""

    def test_get_hardware_id_returns_string(self):
        """Hardware-ID sollte ein String sein"""
        hw_id = get_hardware_id()
        assert isinstance(hw_id, str)

    def test_hardware_id_is_sha256(self):
        """Hardware-ID sollte SHA-256 Hash sein (64 Zeichen)"""
        hw_id = get_hardware_id()
        assert len(hw_id) == 64
        # Should be hexadecimal
        assert all(c in '0123456789abcdef' for c in hw_id.lower())

    def test_hardware_id_is_consistent(self):
        """Hardware-ID sollte bei mehrfachen Aufrufen gleich bleiben"""
        hw_id1 = get_hardware_id()
        hw_id2 = get_hardware_id()
        assert hw_id1 == hw_id2

    def test_get_hardware_info_display_returns_dict(self):
        """get_hardware_info_display sollte Dictionary zurückgeben"""
        info = HardwareIDGenerator.get_hardware_info_display()
        assert isinstance(info, dict)

    def test_hardware_info_contains_expected_keys(self):
        """Hardware-Info sollte erwartete Felder enthalten"""
        info = HardwareIDGenerator.get_hardware_info_display()
        expected_keys = [
            'platform',
            'platform_release',
            'platform_version',
            'processor',
            'machine',
            'hardware_id'
        ]
        for key in expected_keys:
            assert key in info

    def test_get_cpu_info_returns_string_or_none(self):
        """_get_cpu_info sollte String oder None zurückgeben"""
        result = HardwareIDGenerator._get_cpu_info()
        assert result is None or isinstance(result, str)

    def test_get_system_uuid_returns_string_or_none(self):
        """_get_system_uuid sollte String oder None zurückgeben"""
        result = HardwareIDGenerator._get_system_uuid()
        assert result is None or isinstance(result, str)

    def test_get_mac_address_returns_string_or_none(self):
        """_get_mac_address sollte String oder None zurückgeben"""
        result = HardwareIDGenerator._get_mac_address()
        assert result is None or isinstance(result, str)

    def test_mac_address_format(self):
        """MAC-Adresse sollte korrektes Format haben (falls vorhanden)"""
        mac = HardwareIDGenerator._get_mac_address()
        if mac:
            # Should be in format XX:XX:XX:XX:XX:XX
            assert len(mac) == 17
            assert mac.count(':') == 5
