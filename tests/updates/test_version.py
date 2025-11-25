"""
Unit Tests für Version Management
"""

import pytest
from src.updates.version import Version, CURRENT_VERSION, get_version_string, get_full_version_info


class TestVersion:
    """Tests für Version Klasse"""

    def test_version_string_representation(self):
        """Version sollte als String dargestellt werden"""
        version = Version(major=2, minor=0, patch=1)
        assert str(version) == "2.0.1"

    def test_version_string_with_build(self):
        """Version mit Build sollte korrekt dargestellt werden"""
        version = Version(major=2, minor=0, patch=1, build="beta")
        assert str(version) == "2.0.1-beta"

    def test_version_to_tuple(self):
        """Version sollte zu Tuple konvertiert werden"""
        version = Version(major=2, minor=0, patch=1)
        assert version.to_tuple() == (2, 0, 1)

    def test_version_comparison_less_than(self):
        """Version-Vergleich: <"""
        v1 = Version(2, 0, 0)
        v2 = Version(2, 0, 1)
        assert v1 < v2

    def test_version_comparison_greater_than(self):
        """Version-Vergleich: >"""
        v1 = Version(2, 1, 0)
        v2 = Version(2, 0, 1)
        assert v1 > v2

    def test_version_comparison_equal(self):
        """Version-Vergleich: =="""
        v1 = Version(2, 0, 1)
        v2 = Version(2, 0, 1)
        assert v1 == v2

    def test_version_comparison_less_equal(self):
        """Version-Vergleich: <="""
        v1 = Version(2, 0, 0)
        v2 = Version(2, 0, 1)
        v3 = Version(2, 0, 1)
        assert v1 <= v2
        assert v2 <= v3

    def test_version_comparison_greater_equal(self):
        """Version-Vergleich: >="""
        v1 = Version(2, 1, 0)
        v2 = Version(2, 0, 1)
        v3 = Version(2, 0, 1)
        assert v1 >= v2
        assert v2 >= v3

    def test_version_from_string_simple(self):
        """Version aus String parsen (einfach)"""
        version = Version.from_string("2.0.1")
        assert version.major == 2
        assert version.minor == 0
        assert version.patch == 1
        assert version.build == ""

    def test_version_from_string_with_build(self):
        """Version aus String parsen (mit Build)"""
        version = Version.from_string("2.0.1-beta")
        assert version.major == 2
        assert version.minor == 0
        assert version.patch == 1
        assert version.build == "beta"

    def test_version_from_string_minimal(self):
        """Version aus minimalem String parsen"""
        version = Version.from_string("2")
        assert version.major == 2
        assert version.minor == 0
        assert version.patch == 0

    def test_version_from_string_partial(self):
        """Version aus partiellem String parsen"""
        version = Version.from_string("2.1")
        assert version.major == 2
        assert version.minor == 1
        assert version.patch == 0


class TestCurrentVersion:
    """Tests für aktuelle Version"""

    def test_current_version_exists(self):
        """CURRENT_VERSION sollte existieren"""
        assert CURRENT_VERSION is not None

    def test_current_version_is_version_instance(self):
        """CURRENT_VERSION sollte Version-Instanz sein"""
        assert isinstance(CURRENT_VERSION, Version)

    def test_get_version_string_returns_string(self):
        """get_version_string sollte String zurückgeben"""
        version_str = get_version_string()
        assert isinstance(version_str, str)
        assert len(version_str) > 0

    def test_get_full_version_info_returns_string(self):
        """get_full_version_info sollte String zurückgeben"""
        info = get_full_version_info()
        assert isinstance(info, str)
        assert "StitchAdmin" in info
        assert "Version" in info


class TestVersionComparisons:
    """Tests für komplexe Version-Vergleiche"""

    def test_major_version_comparison(self):
        """Major Version Vergleich"""
        v1 = Version(1, 9, 9)
        v2 = Version(2, 0, 0)
        assert v1 < v2

    def test_minor_version_comparison(self):
        """Minor Version Vergleich"""
        v1 = Version(2, 1, 9)
        v2 = Version(2, 2, 0)
        assert v1 < v2

    def test_patch_version_comparison(self):
        """Patch Version Vergleich"""
        v1 = Version(2, 0, 1)
        v2 = Version(2, 0, 2)
        assert v1 < v2

    def test_version_sorting(self):
        """Versionen sollten sortiert werden können"""
        versions = [
            Version(2, 0, 2),
            Version(2, 1, 0),
            Version(1, 9, 9),
            Version(2, 0, 1),
        ]
        sorted_versions = sorted(versions)

        assert sorted_versions[0] == Version(1, 9, 9)
        assert sorted_versions[1] == Version(2, 0, 1)
        assert sorted_versions[2] == Version(2, 0, 2)
        assert sorted_versions[3] == Version(2, 1, 0)
