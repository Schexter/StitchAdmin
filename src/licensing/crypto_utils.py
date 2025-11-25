"""
StitchAdmin 2.0 - Kryptographie-Utils für Lizenzierung
Erstellt von Hans Hahn - Alle Rechte vorbehalten

Implementiert RSA-basierte Verschlüsselung und Signierung für Lizenzen:
- Generierung von RSA Key-Pairs (2048-bit)
- Signierung von Lizenz-Daten (private key)
- Verifizierung von Signaturen (public key)
- Serialisierung von Keys im PEM-Format

WICHTIG: Private Keys NIEMALS in Git committen!
"""

import base64
import logging
from pathlib import Path
from typing import Tuple, Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

logger = logging.getLogger(__name__)


class CryptoUtils:
    """
    Kryptographie-Utilities für Lizenz-Management.

    Verwendet RSA-2048 für asymmetrische Verschlüsselung.
    """

    # RSA key size (2048 bits is secure and fast enough)
    KEY_SIZE = 2048

    # Public exponent (65537 is standard)
    PUBLIC_EXPONENT = 65537

    @staticmethod
    def generate_key_pair() -> Tuple[bytes, bytes]:
        """
        Generiert ein neues RSA-Schlüsselpaar.

        Returns:
            Tuple[bytes, bytes]: (private_key_pem, public_key_pem)

        Example:
            >>> private_pem, public_pem = CryptoUtils.generate_key_pair()
        """
        logger.info("Generiere neues RSA-Schlüsselpaar (2048 bit)...")

        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=CryptoUtils.PUBLIC_EXPONENT,
            key_size=CryptoUtils.KEY_SIZE,
            backend=default_backend()
        )

        # Serialize private key to PEM format
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        # Get public key from private key
        public_key = private_key.public_key()

        # Serialize public key to PEM format
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        logger.info("Schlüsselpaar erfolgreich generiert")
        return private_pem, public_pem

    @staticmethod
    def save_key_pair(
        private_key_pem: bytes,
        public_key_pem: bytes,
        private_key_path: Path,
        public_key_path: Path
    ) -> None:
        """
        Speichert Schlüsselpaar in PEM-Dateien.

        Args:
            private_key_pem: Private Key im PEM-Format
            public_key_pem: Public Key im PEM-Format
            private_key_path: Pfad für Private Key Datei
            public_key_path: Pfad für Public Key Datei

        Raises:
            IOError: Bei Schreibfehlern
        """
        logger.info(f"Speichere Schlüsselpaar: {private_key_path.name}, {public_key_path.name}")

        try:
            # Save private key
            private_key_path.write_bytes(private_key_pem)
            logger.info(f"Private Key gespeichert: {private_key_path}")

            # Save public key
            public_key_path.write_bytes(public_key_pem)
            logger.info(f"Public Key gespeichert: {public_key_path}")

        except Exception as e:
            logger.error(f"Fehler beim Speichern der Keys: {e}", exc_info=True)
            raise IOError(f"Schlüssel konnten nicht gespeichert werden: {e}")

    @staticmethod
    def load_private_key(private_key_path: Path) -> rsa.RSAPrivateKey:
        """
        Lädt einen Private Key aus PEM-Datei.

        Args:
            private_key_path: Pfad zur Private Key Datei

        Returns:
            rsa.RSAPrivateKey: Geladener Private Key

        Raises:
            FileNotFoundError: Wenn Key-Datei nicht existiert
            ValueError: Wenn Key-Format ungültig
        """
        logger.debug(f"Lade Private Key: {private_key_path}")

        if not private_key_path.exists():
            raise FileNotFoundError(f"Private Key nicht gefunden: {private_key_path}")

        try:
            private_pem = private_key_path.read_bytes()
            private_key = serialization.load_pem_private_key(
                private_pem,
                password=None,
                backend=default_backend()
            )
            logger.debug("Private Key erfolgreich geladen")
            return private_key

        except Exception as e:
            logger.error(f"Fehler beim Laden des Private Keys: {e}", exc_info=True)
            raise ValueError(f"Private Key konnte nicht geladen werden: {e}")

    @staticmethod
    def load_public_key(public_key_path: Path) -> rsa.RSAPublicKey:
        """
        Lädt einen Public Key aus PEM-Datei.

        Args:
            public_key_path: Pfad zur Public Key Datei

        Returns:
            rsa.RSAPublicKey: Geladener Public Key

        Raises:
            FileNotFoundError: Wenn Key-Datei nicht existiert
            ValueError: Wenn Key-Format ungültig
        """
        logger.debug(f"Lade Public Key: {public_key_path}")

        if not public_key_path.exists():
            raise FileNotFoundError(f"Public Key nicht gefunden: {public_key_path}")

        try:
            public_pem = public_key_path.read_bytes()
            public_key = serialization.load_pem_public_key(
                public_pem,
                backend=default_backend()
            )
            logger.debug("Public Key erfolgreich geladen")
            return public_key

        except Exception as e:
            logger.error(f"Fehler beim Laden des Public Keys: {e}", exc_info=True)
            raise ValueError(f"Public Key konnte nicht geladen werden: {e}")

    @staticmethod
    def sign_data(data: bytes, private_key: rsa.RSAPrivateKey) -> str:
        """
        Signiert Daten mit Private Key (RSA-PSS).

        Args:
            data: Zu signierende Daten
            private_key: Private Key für Signatur

        Returns:
            str: Base64-kodierte Signatur

        Raises:
            ValueError: Bei Signierungsfehler
        """
        logger.debug(f"Signiere Daten ({len(data)} bytes)...")

        try:
            # Sign data using RSA-PSS with SHA-256
            signature = private_key.sign(
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            # Encode signature as base64 for storage
            signature_b64 = base64.b64encode(signature).decode('utf-8')

            logger.debug(f"Signatur erstellt: {len(signature)} bytes → {len(signature_b64)} chars (base64)")
            return signature_b64

        except Exception as e:
            logger.error(f"Fehler beim Signieren: {e}", exc_info=True)
            raise ValueError(f"Daten konnten nicht signiert werden: {e}")

    @staticmethod
    def verify_signature(
        data: bytes,
        signature_b64: str,
        public_key: rsa.RSAPublicKey
    ) -> bool:
        """
        Verifiziert eine Signatur mit Public Key.

        Args:
            data: Original-Daten
            signature_b64: Base64-kodierte Signatur
            public_key: Public Key zur Verifikation

        Returns:
            bool: True wenn Signatur gültig, False sonst
        """
        logger.debug(f"Verifiziere Signatur für Daten ({len(data)} bytes)...")

        try:
            # Decode signature from base64
            signature = base64.b64decode(signature_b64)

            # Verify signature using RSA-PSS with SHA-256
            public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            logger.debug("✅ Signatur gültig")
            return True

        except Exception as e:
            logger.warning(f"❌ Signatur ungültig: {e}")
            return False

    @staticmethod
    def load_public_key_from_bytes(public_key_pem: bytes) -> rsa.RSAPublicKey:
        """
        Lädt einen Public Key aus PEM-Bytes (eingebettet in App).

        Args:
            public_key_pem: Public Key im PEM-Format (bytes)

        Returns:
            rsa.RSAPublicKey: Geladener Public Key

        Raises:
            ValueError: Wenn Key-Format ungültig
        """
        logger.debug("Lade Public Key aus Bytes...")

        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem,
                backend=default_backend()
            )
            logger.debug("Public Key erfolgreich aus Bytes geladen")
            return public_key

        except Exception as e:
            logger.error(f"Fehler beim Laden des Public Keys aus Bytes: {e}", exc_info=True)
            raise ValueError(f"Public Key konnte nicht aus Bytes geladen werden: {e}")


# Convenience functions for common operations
def generate_and_save_keys(
    private_key_path: str = "private_key.pem",
    public_key_path: str = "public_key.pem"
) -> None:
    """
    Generiert und speichert ein neues Schlüsselpaar.

    Args:
        private_key_path: Pfad für Private Key (Standard: private_key.pem)
        public_key_path: Pfad für Public Key (Standard: public_key.pem)
    """
    private_path = Path(private_key_path)
    public_path = Path(public_key_path)

    # Generate keys
    private_pem, public_pem = CryptoUtils.generate_key_pair()

    # Save keys
    CryptoUtils.save_key_pair(private_pem, public_pem, private_path, public_path)

    print(f"✅ Schlüsselpaar generiert und gespeichert:")
    print(f"   Private Key: {private_path.absolute()}")
    print(f"   Public Key:  {public_path.absolute()}")
    print(f"\n⚠️  WICHTIG: Private Key NIEMALS in Git committen!")


if __name__ == "__main__":
    # Test/Debug-Modus
    logging.basicConfig(level=logging.DEBUG)

    print("=" * 60)
    print("StitchAdmin 2.0 - Crypto Utils Test")
    print("=" * 60)

    try:
        # Test 1: Generate key pair
        print("\n1️⃣  Generiere Schlüsselpaar...")
        private_pem, public_pem = CryptoUtils.generate_key_pair()
        print(f"   ✅ Private Key: {len(private_pem)} bytes")
        print(f"   ✅ Public Key:  {len(public_pem)} bytes")

        # Test 2: Load keys from bytes
        print("\n2️⃣  Lade Keys aus Bytes...")
        public_key = CryptoUtils.load_public_key_from_bytes(public_pem)
        private_key = serialization.load_pem_private_key(
            private_pem, password=None, backend=default_backend()
        )
        print(f"   ✅ Keys geladen")

        # Test 3: Sign data
        print("\n3️⃣  Signiere Test-Daten...")
        test_data = b"StitchAdmin 2.0 - Test License Data"
        signature = CryptoUtils.sign_data(test_data, private_key)
        print(f"   ✅ Signatur: {signature[:40]}...")

        # Test 4: Verify signature (valid)
        print("\n4️⃣  Verifiziere Signatur (gültig)...")
        is_valid = CryptoUtils.verify_signature(test_data, signature, public_key)
        print(f"   {'✅' if is_valid else '❌'} Signatur gültig: {is_valid}")

        # Test 5: Verify signature (invalid data)
        print("\n5️⃣  Verifiziere Signatur (ungültige Daten)...")
        tampered_data = b"StitchAdmin 2.0 - MANIPULATED Data"
        is_valid = CryptoUtils.verify_signature(tampered_data, signature, public_key)
        print(f"   {'✅' if not is_valid else '❌'} Signatur ungültig: {not is_valid}")

        # Test 6: Verify signature (invalid signature)
        print("\n6️⃣  Verifiziere Signatur (ungültige Signatur)...")
        fake_signature = base64.b64encode(b"fake" * 64).decode('utf-8')
        is_valid = CryptoUtils.verify_signature(test_data, fake_signature, public_key)
        print(f"   {'✅' if not is_valid else '❌'} Signatur ungültig: {not is_valid}")

        print("\n" + "=" * 60)
        print("✅ Alle Tests erfolgreich!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Fehler: {e}\n")
        raise
