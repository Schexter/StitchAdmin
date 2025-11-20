"""
StitchAdmin 2.0 - Versions-Management
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Zentrale Versions-Informationen für die Anwendung.
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class Version:
    """Versions-Informationen"""
    major: int
    minor: int
    patch: int
    build: str = ""  # e.g., "beta", "rc1", ""

    def __str__(self) -> str:
        """String-Repräsentation: 2.0.0 oder 2.0.0-beta"""
        version_str = f"{self.major}.{self.minor}.{self.patch}"
        if self.build:
            version_str += f"-{self.build}"
        return version_str

    def to_tuple(self) -> Tuple[int, int, int]:
        """Gibt Version als Tuple zurück für Vergleiche"""
        return (self.major, self.minor, self.patch)

    def __lt__(self, other: 'Version') -> bool:
        """Ermöglicht Version-Vergleiche: v1 < v2"""
        return self.to_tuple() < other.to_tuple()

    def __le__(self, other: 'Version') -> bool:
        return self.to_tuple() <= other.to_tuple()

    def __gt__(self, other: 'Version') -> bool:
        return self.to_tuple() > other.to_tuple()

    def __ge__(self, other: 'Version') -> bool:
        return self.to_tuple() >= other.to_tuple()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return False
        return self.to_tuple() == other.to_tuple()

    @staticmethod
    def from_string(version_str: str) -> 'Version':
        """
        Parst Version aus String.

        Args:
            version_str: Version string (z.B. "2.0.0" oder "2.0.0-beta")

        Returns:
            Version: Geparste Version

        Example:
            >>> Version.from_string("2.0.0-beta")
            Version(major=2, minor=0, patch=0, build='beta')
        """
        # Split build suffix if exists
        build = ""
        if "-" in version_str:
            version_str, build = version_str.split("-", 1)

        # Parse version numbers
        parts = version_str.split(".")
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0

        return Version(major=major, minor=minor, patch=patch, build=build)


# Current version
CURRENT_VERSION = Version(
    major=2,
    minor=0,
    patch=0,
    build=""  # Leave empty for release, use "beta", "rc1", etc. for pre-releases
)

# Application metadata
APP_NAME = "StitchAdmin"
APP_FULL_NAME = "StitchAdmin 2.0"
APP_AUTHOR = "Hans Hahn"
APP_COPYRIGHT = f"© 2025 {APP_AUTHOR} - Alle Rechte vorbehalten"
APP_WEBSITE = "https://your-website.com"  # TODO: Update with actual URL
APP_SUPPORT_EMAIL = "support@your-domain.com"  # TODO: Update with actual email


def get_version_string() -> str:
    """
    Gibt die aktuelle Version als String zurück.

    Returns:
        str: Version (z.B. "2.0.0")
    """
    return str(CURRENT_VERSION)


def get_full_version_info() -> str:
    """
    Gibt vollständige Versions-Informationen zurück.

    Returns:
        str: Vollständige Info (z.B. "StitchAdmin 2.0 - Version 2.0.0")
    """
    return f"{APP_FULL_NAME} - Version {CURRENT_VERSION}"


if __name__ == "__main__":
    print("=" * 60)
    print("StitchAdmin 2.0 - Version Info")
    print("=" * 60)
    print(f"\nApp Name:    {APP_FULL_NAME}")
    print(f"Version:     {CURRENT_VERSION}")
    print(f"Author:      {APP_AUTHOR}")
    print(f"Copyright:   {APP_COPYRIGHT}")
    print(f"Website:     {APP_WEBSITE}")
    print(f"Support:     {APP_SUPPORT_EMAIL}")
    print("\n" + "=" * 60)

    # Test version comparison
    print("\nVersion Comparison Test:")
    v1 = Version(2, 0, 0)
    v2 = Version(2, 0, 1)
    v3 = Version(2, 1, 0)

    print(f"  {v1} < {v2}: {v1 < v2}")
    print(f"  {v2} < {v3}: {v2 < v3}")
    print(f"  {v1} == {v1}: {v1 == v1}")

    # Test version parsing
    print("\nVersion Parsing Test:")
    parsed = Version.from_string("2.5.3-beta")
    print(f"  '2.5.3-beta' -> {parsed}")
    print("=" * 60)
