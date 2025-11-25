"""
Unit Tests für Kryptographie-Utils
"""

import base64
from pathlib import Path
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from src.licensing.crypto_utils import CryptoUtils


class TestCryptoUtils:
    """Tests für CryptoUtils"""

    def test_generate_key_pair_returns_tuple(self):
        """generate_key_pair sollte Tuple mit 2 Elementen zurückgeben"""
        private_pem, public_pem = CryptoUtils.generate_key_pair()
        assert isinstance(private_pem, bytes)
        assert isinstance(public_pem, bytes)

    def test_generated_keys_are_pem_format(self):
        """Generierte Keys sollten im PEM-Format sein"""
        private_pem, public_pem = CryptoUtils.generate_key_pair()

        # PEM files start with specific headers
        assert private_pem.startswith(b'-----BEGIN PRIVATE KEY-----')
        assert public_pem.startswith(b'-----BEGIN PUBLIC KEY-----')

    def test_sign_and_verify_valid_data(self):
        """Signierte Daten sollten verifiziert werden können"""
        # Generate test keys
        private_pem, public_pem = CryptoUtils.generate_key_pair()
        private_key = CryptoUtils.load_public_key_from_bytes(private_pem)  # This will fail, need to fix
        # Actually load private key properly
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        private_key = serialization.load_pem_private_key(
            private_pem, password=None, backend=default_backend()
        )
        public_key = CryptoUtils.load_public_key_from_bytes(public_pem)

        # Sign data
        test_data = b"Test message for signing"
        signature = CryptoUtils.sign_data(test_data, private_key)

        # Verify signature
        is_valid = CryptoUtils.verify_signature(test_data, signature, public_key)
        assert is_valid is True

    def test_verify_fails_with_tampered_data(self):
        """Signatur-Verifikation sollte bei manipulierten Daten fehlschlagen"""
        # Generate test keys
        private_pem, public_pem = CryptoUtils.generate_key_pair()
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        private_key = serialization.load_pem_private_key(
            private_pem, password=None, backend=default_backend()
        )
        public_key = CryptoUtils.load_public_key_from_bytes(public_pem)

        # Sign original data
        original_data = b"Original message"
        signature = CryptoUtils.sign_data(original_data, private_key)

        # Try to verify with tampered data
        tampered_data = b"Tampered message"
        is_valid = CryptoUtils.verify_signature(tampered_data, signature, public_key)
        assert is_valid is False

    def test_verify_fails_with_invalid_signature(self):
        """Signatur-Verifikation sollte bei ungültiger Signatur fehlschlagen"""
        # Generate test keys
        private_pem, public_pem = CryptoUtils.generate_key_pair()
        public_key = CryptoUtils.load_public_key_from_bytes(public_pem)

        # Create fake signature
        fake_signature = base64.b64encode(b"fake signature" * 20).decode('utf-8')

        # Try to verify
        test_data = b"Test data"
        is_valid = CryptoUtils.verify_signature(test_data, fake_signature, public_key)
        assert is_valid is False

    def test_load_public_key_from_bytes(self):
        """load_public_key_from_bytes sollte PublicKey-Objekt zurückgeben"""
        _, public_pem = CryptoUtils.generate_key_pair()
        public_key = CryptoUtils.load_public_key_from_bytes(public_pem)
        assert isinstance(public_key, rsa.RSAPublicKey)

    def test_save_and_load_key_pair(self, tmp_path):
        """Gespeicherte Keys sollten wieder geladen werden können"""
        # Generate keys
        private_pem, public_pem = CryptoUtils.generate_key_pair()

        # Save to temporary files
        private_path = tmp_path / "test_private.pem"
        public_path = tmp_path / "test_public.pem"
        CryptoUtils.save_key_pair(private_pem, public_pem, private_path, public_path)

        # Verify files exist
        assert private_path.exists()
        assert public_path.exists()

        # Load keys back
        loaded_private = CryptoUtils.load_private_key(private_path)
        loaded_public = CryptoUtils.load_public_key(public_path)

        assert isinstance(loaded_private, rsa.RSAPrivateKey)
        assert isinstance(loaded_public, rsa.RSAPublicKey)

    def test_load_nonexistent_private_key_raises_error(self, tmp_path):
        """Laden eines nicht-existierenden Private Keys sollte Fehler werfen"""
        nonexistent_path = tmp_path / "nonexistent.pem"
        with pytest.raises(FileNotFoundError):
            CryptoUtils.load_private_key(nonexistent_path)

    def test_load_nonexistent_public_key_raises_error(self, tmp_path):
        """Laden eines nicht-existierenden Public Keys sollte Fehler werfen"""
        nonexistent_path = tmp_path / "nonexistent.pem"
        with pytest.raises(FileNotFoundError):
            CryptoUtils.load_public_key(nonexistent_path)

    def test_signature_is_base64_encoded(self):
        """Signatur sollte Base64-kodiert sein"""
        # Generate test keys
        private_pem, _ = CryptoUtils.generate_key_pair()
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend
        private_key = serialization.load_pem_private_key(
            private_pem, password=None, backend=default_backend()
        )

        # Sign data
        test_data = b"Test data"
        signature = CryptoUtils.sign_data(test_data, private_key)

        # Should be valid base64
        try:
            base64.b64decode(signature)
            is_valid_base64 = True
        except:
            is_valid_base64 = False

        assert is_valid_base64 is True
