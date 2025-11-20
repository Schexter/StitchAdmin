"""
StitchAdmin 2.0 - Lizenz-Manager
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Verwaltet Lizenzierung mit:
- Trial-Mode (30 Tage ohne Lizenz)
- Vollversion (mit gültiger Lizenz-Datei)
- Hardware-Binding (Lizenz an Hardware-ID gebunden)
- Ablaufdatum-Prüfung
- Feature-Flags (zukünftige Erweiterungen)

Lizenz-Format (JSON):
{
    "license_id": "UUID",
    "customer_name": "Kundenname",
    "hardware_id": "SHA-256 Hash",
    "issued_date": "ISO-8601",
    "expiry_date": "ISO-8601 oder null für unbegrenzt",
    "license_type": "trial|standard|professional|enterprise",
    "features": {
        "max_users": 5,
        "max_orders_per_month": 1000,
        "zugpferd_enabled": true,
        "api_access": false
    },
    "version": "1.0",
    "signature": "Base64-encoded RSA signature"
}
"""

import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass, asdict
import uuid

from .hardware_id import get_hardware_id
from .crypto_utils import CryptoUtils

logger = logging.getLogger(__name__)


class LicenseType(Enum):
    """Lizenz-Typen"""
    TRIAL = "trial"
    STANDARD = "standard"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class LicenseStatus(Enum):
    """Lizenz-Status"""
    VALID = "valid"                      # Lizenz gültig
    EXPIRED = "expired"                  # Lizenz abgelaufen
    HARDWARE_MISMATCH = "hardware_mismatch"  # Falsche Hardware
    INVALID_SIGNATURE = "invalid_signature"  # Ungültige Signatur
    NOT_FOUND = "not_found"              # Keine Lizenz gefunden
    TRIAL = "trial"                      # Trial-Mode aktiv
    TRIAL_EXPIRED = "trial_expired"      # Trial abgelaufen


@dataclass
class LicenseInfo:
    """Lizenz-Informationen"""
    status: LicenseStatus
    license_type: Optional[LicenseType] = None
    customer_name: Optional[str] = None
    expiry_date: Optional[datetime] = None
    days_remaining: Optional[int] = None
    features: Optional[Dict[str, Any]] = None
    trial_days_remaining: Optional[int] = None
    message: str = ""

    def is_valid(self) -> bool:
        """Prüft, ob Lizenz gültig ist (inkl. Trial)"""
        return self.status in [LicenseStatus.VALID, LicenseStatus.TRIAL]

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary"""
        data = asdict(self)
        data['status'] = self.status.value
        if self.license_type:
            data['license_type'] = self.license_type.value
        if self.expiry_date:
            data['expiry_date'] = self.expiry_date.isoformat()
        return data


class LicenseManager:
    """
    Lizenz-Manager für StitchAdmin 2.0

    Verwaltet Trial-Mode, Lizenz-Validierung und Feature-Checks.
    """

    # Default paths
    LICENSE_FILE = Path("license.json")
    TRIAL_FILE = Path("instance/.trial")
    PUBLIC_KEY_EMBEDDED = None  # Will be set during build

    # Trial settings
    TRIAL_DAYS = 30

    def __init__(
        self,
        license_path: Optional[Path] = None,
        trial_path: Optional[Path] = None,
        public_key_pem: Optional[bytes] = None
    ):
        """
        Initialisiert den Lizenz-Manager.

        Args:
            license_path: Pfad zur Lizenz-Datei (Standard: license.json)
            trial_path: Pfad zur Trial-Info-Datei (Standard: instance/.trial)
            public_key_pem: Public Key für Signatur-Verifikation (embedded)
        """
        self.license_path = license_path or self.LICENSE_FILE
        self.trial_path = trial_path or self.TRIAL_FILE
        self.public_key_pem = public_key_pem
        self._license_cache: Optional[Dict] = None
        self._public_key = None

        logger.debug(f"LicenseManager initialisiert: {self.license_path}")

    def get_license_status(self) -> LicenseInfo:
        """
        Ermittelt den aktuellen Lizenz-Status.

        Returns:
            LicenseInfo: Lizenz-Informationen und Status

        Flow:
            1. Prüfe ob Lizenz-Datei existiert
            2. Wenn ja: Validiere Lizenz
            3. Wenn nein: Prüfe Trial-Mode
            4. Wenn Trial abgelaufen: Return TRIAL_EXPIRED
        """
        logger.info("Prüfe Lizenz-Status...")

        # Try to load and validate license
        if self.license_path.exists():
            logger.debug(f"Lizenz-Datei gefunden: {self.license_path}")
            license_info = self._validate_license_file()

            if license_info.status == LicenseStatus.VALID:
                logger.info(f"✅ Gültige Lizenz: {license_info.license_type.value}")
                return license_info
            else:
                logger.warning(f"❌ Lizenz ungültig: {license_info.status.value}")
                # Fall through to trial mode

        # No valid license - check trial mode
        logger.debug("Keine gültige Lizenz - prüfe Trial-Mode...")
        return self._check_trial_mode()

    def _validate_license_file(self) -> LicenseInfo:
        """
        Validiert Lizenz-Datei.

        Returns:
            LicenseInfo: Validierungs-Ergebnis
        """
        try:
            # Load license data
            license_data = json.loads(self.license_path.read_text(encoding='utf-8'))
            logger.debug(f"Lizenz geladen: {license_data.get('license_id', 'N/A')[:16]}...")

            # Extract signature
            signature = license_data.pop('signature', None)
            if not signature:
                return LicenseInfo(
                    status=LicenseStatus.INVALID_SIGNATURE,
                    message="Keine Signatur in Lizenz-Datei"
                )

            # Verify signature
            if not self._verify_license_signature(license_data, signature):
                return LicenseInfo(
                    status=LicenseStatus.INVALID_SIGNATURE,
                    message="Ungültige Lizenz-Signatur"
                )

            # Check hardware ID
            current_hw_id = get_hardware_id()
            license_hw_id = license_data.get('hardware_id')

            if current_hw_id != license_hw_id:
                logger.warning(f"Hardware-ID Mismatch: {current_hw_id[:16]}... != {license_hw_id[:16]}...")
                return LicenseInfo(
                    status=LicenseStatus.HARDWARE_MISMATCH,
                    message="Lizenz gilt nicht für diese Hardware"
                )

            # Check expiry date
            expiry_date_str = license_data.get('expiry_date')
            expiry_date = None
            days_remaining = None

            if expiry_date_str:
                expiry_date = datetime.fromisoformat(expiry_date_str)
                days_remaining = (expiry_date - datetime.now()).days

                if days_remaining < 0:
                    logger.warning(f"Lizenz abgelaufen seit {abs(days_remaining)} Tagen")
                    return LicenseInfo(
                        status=LicenseStatus.EXPIRED,
                        expiry_date=expiry_date,
                        days_remaining=days_remaining,
                        message=f"Lizenz abgelaufen seit {abs(days_remaining)} Tagen"
                    )

            # All checks passed - license valid
            license_type_str = license_data.get('license_type', 'standard')
            license_type = LicenseType(license_type_str)

            return LicenseInfo(
                status=LicenseStatus.VALID,
                license_type=license_type,
                customer_name=license_data.get('customer_name'),
                expiry_date=expiry_date,
                days_remaining=days_remaining,
                features=license_data.get('features', {}),
                message=f"Gültige {license_type.value} Lizenz"
            )

        except Exception as e:
            logger.error(f"Fehler bei Lizenz-Validierung: {e}", exc_info=True)
            return LicenseInfo(
                status=LicenseStatus.INVALID_SIGNATURE,
                message=f"Lizenz-Validierung fehlgeschlagen: {str(e)}"
            )

    def _verify_license_signature(self, license_data: Dict, signature: str) -> bool:
        """
        Verifiziert Lizenz-Signatur.

        Args:
            license_data: Lizenz-Daten (ohne Signatur)
            signature: Base64-kodierte Signatur

        Returns:
            bool: True wenn Signatur gültig
        """
        try:
            # Load public key
            if self._public_key is None:
                if self.public_key_pem:
                    # Use embedded public key (for production build)
                    self._public_key = CryptoUtils.load_public_key_from_bytes(self.public_key_pem)
                else:
                    # Development: Load from file
                    public_key_path = Path("admin_tools/public_key.pem")
                    if not public_key_path.exists():
                        logger.error("Public Key nicht gefunden")
                        return False
                    self._public_key = CryptoUtils.load_public_key(public_key_path)

            # Create canonical JSON (sorted keys for consistent signature)
            license_json = json.dumps(license_data, sort_keys=True, ensure_ascii=False)
            license_bytes = license_json.encode('utf-8')

            # Verify signature
            return CryptoUtils.verify_signature(license_bytes, signature, self._public_key)

        except Exception as e:
            logger.error(f"Fehler bei Signatur-Verifikation: {e}", exc_info=True)
            return False

    def _check_trial_mode(self) -> LicenseInfo:
        """
        Prüft Trial-Mode Status.

        Returns:
            LicenseInfo: Trial-Status
        """
        # Check if trial file exists
        if not self.trial_path.exists():
            # First start - create trial file
            logger.info("Erstelle Trial-Datei (Erststart)")
            self._create_trial_file()

        # Read trial start date
        try:
            trial_start_str = self.trial_path.read_text(encoding='utf-8').strip()
            trial_start = datetime.fromisoformat(trial_start_str)

            # Calculate remaining days
            trial_end = trial_start + timedelta(days=self.TRIAL_DAYS)
            days_remaining = (trial_end - datetime.now()).days

            if days_remaining >= 0:
                logger.info(f"Trial-Mode aktiv: {days_remaining} Tage verbleibend")
                return LicenseInfo(
                    status=LicenseStatus.TRIAL,
                    license_type=LicenseType.TRIAL,
                    trial_days_remaining=days_remaining,
                    expiry_date=trial_end,
                    days_remaining=days_remaining,
                    message=f"Trial-Version ({days_remaining} Tage verbleibend)"
                )
            else:
                logger.warning(f"Trial-Mode abgelaufen seit {abs(days_remaining)} Tagen")
                return LicenseInfo(
                    status=LicenseStatus.TRIAL_EXPIRED,
                    trial_days_remaining=0,
                    message=f"Trial-Version abgelaufen (seit {abs(days_remaining)} Tagen)"
                )

        except Exception as e:
            logger.error(f"Fehler beim Lesen der Trial-Datei: {e}", exc_info=True)
            # Re-create trial file
            self._create_trial_file()
            return self._check_trial_mode()

    def _create_trial_file(self) -> None:
        """Erstellt Trial-Datei mit aktuellem Datum"""
        try:
            # Ensure directory exists
            self.trial_path.parent.mkdir(parents=True, exist_ok=True)

            # Write current datetime
            trial_start = datetime.now()
            self.trial_path.write_text(trial_start.isoformat(), encoding='utf-8')

            logger.info(f"Trial-Datei erstellt: {self.trial_path}")

        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Trial-Datei: {e}", exc_info=True)
            raise

    def check_feature(self, feature_name: str, default: Any = False) -> Any:
        """
        Prüft, ob ein Feature aktiviert ist.

        Args:
            feature_name: Name des Features
            default: Default-Wert falls nicht in Lizenz definiert

        Returns:
            Any: Feature-Wert aus Lizenz oder Default

        Example:
            >>> if license_manager.check_feature('zugpferd_enabled'):
            >>>     # ZUGFeRD feature verfügbar
        """
        license_info = self.get_license_status()

        if not license_info.is_valid():
            return default

        if license_info.features:
            return license_info.features.get(feature_name, default)

        return default

    def get_hardware_id(self) -> str:
        """
        Gibt die Hardware-ID für Support/Lizenzierung zurück.

        Returns:
            str: Hardware-ID
        """
        return get_hardware_id()


# Convenience function
def create_license_data(
    customer_name: str,
    hardware_id: str,
    license_type: LicenseType = LicenseType.STANDARD,
    expiry_date: Optional[datetime] = None,
    features: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Erstellt Lizenz-Daten Dictionary (ohne Signatur).

    Args:
        customer_name: Kundenname
        hardware_id: Hardware-ID des Ziel-Systems
        license_type: Lizenz-Typ
        expiry_date: Ablaufdatum (None = unbegrenzt)
        features: Feature-Dictionary

    Returns:
        Dict: Lizenz-Daten (noch ohne Signatur)
    """
    # Default features based on license type
    if features is None:
        if license_type == LicenseType.TRIAL:
            features = {
                "max_users": 1,
                "max_orders_per_month": 50,
                "zugpferd_enabled": False,
                "api_access": False
            }
        elif license_type == LicenseType.STANDARD:
            features = {
                "max_users": 3,
                "max_orders_per_month": 500,
                "zugpferd_enabled": True,
                "api_access": False
            }
        elif license_type == LicenseType.PROFESSIONAL:
            features = {
                "max_users": 10,
                "max_orders_per_month": 2000,
                "zugpferd_enabled": True,
                "api_access": True
            }
        else:  # ENTERPRISE
            features = {
                "max_users": -1,  # unlimited
                "max_orders_per_month": -1,  # unlimited
                "zugpferd_enabled": True,
                "api_access": True
            }

    license_data = {
        "license_id": str(uuid.uuid4()),
        "customer_name": customer_name,
        "hardware_id": hardware_id,
        "issued_date": datetime.now().isoformat(),
        "expiry_date": expiry_date.isoformat() if expiry_date else None,
        "license_type": license_type.value,
        "features": features,
        "version": "1.0"
    }

    return license_data


if __name__ == "__main__":
    # Test/Debug-Modus
    logging.basicConfig(level=logging.DEBUG)

    print("=" * 60)
    print("StitchAdmin 2.0 - License Manager Test")
    print("=" * 60)

    try:
        # Create license manager
        manager = LicenseManager()

        # Get license status
        print("\n1️⃣  Lizenz-Status prüfen...")
        license_info = manager.get_license_status()

        print(f"\n   Status: {license_info.status.value}")
        print(f"   Typ: {license_info.license_type.value if license_info.license_type else 'N/A'}")
        print(f"   Nachricht: {license_info.message}")

        if license_info.trial_days_remaining is not None:
            print(f"   Trial-Tage: {license_info.trial_days_remaining}")

        if license_info.days_remaining is not None:
            print(f"   Verbleibende Tage: {license_info.days_remaining}")

        # Get hardware ID
        print("\n2️⃣  Hardware-ID...")
        hw_id = manager.get_hardware_id()
        print(f"   {hw_id}")

        # Check features
        print("\n3️⃣  Feature-Check...")
        zugpferd = manager.check_feature('zugpferd_enabled', default=False)
        print(f"   ZUGFeRD: {zugpferd}")

        print("\n" + "=" * 60)
        print("✅ Test abgeschlossen!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Fehler: {e}\n")
        raise
