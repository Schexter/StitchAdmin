# -*- coding: utf-8 -*-
"""
Verschlüsselung für sensible Daten (E-Mail Passwörter etc.)
StitchAdmin 2.0
Erstellt von Hans Hahn - Alle Rechte vorbehalten
"""

from cryptography.fernet import Fernet
import os
import base64


class EncryptionService:
    """
    Service für Verschlüsselung von Passwörtern und sensiblen Daten
    Verwendet Fernet (symmetrische Verschlüsselung)
    """
    
    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_key(self):
        """
        Holt den Verschlüsselungs-Key oder erstellt einen neuen
        WICHTIG: Key muss sicher gespeichert werden!
        """
        key_file = os.path.join(os.path.dirname(__file__), '..', '..', 'instance', 'encryption.key')
        
        # Stelle sicher, dass instance-Ordner existiert
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Neuen Key generieren
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            # Wichtig: Datei-Berechtigung setzen (nur Owner kann lesen)
            os.chmod(key_file, 0o600)
            return key
    
    def encrypt(self, plaintext: str) -> str:
        """
        Verschlüsselt einen String
        
        Args:
            plaintext: Zu verschlüsselnder Text
            
        Returns:
            Verschlüsselter Text als Base64-String
        """
        if not plaintext:
            return None
        
        encrypted_bytes = self.cipher.encrypt(plaintext.encode('utf-8'))
        return base64.b64encode(encrypted_bytes).decode('utf-8')
    
    def decrypt(self, encrypted_text: str) -> str:
        """
        Entschlüsselt einen String
        
        Args:
            encrypted_text: Verschlüsselter Text (Base64)
            
        Returns:
            Entschlüsselter Klartext
        """
        if not encrypted_text:
            return None
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_text.encode('utf-8'))
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            print(f"Decryption error: {e}")
            return None


# Globale Instanz
_encryption_service = None

def get_encryption_service():
    """Gibt die globale EncryptionService-Instanz zurück"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


# Helper-Funktionen für einfache Nutzung
def encrypt_password(password: str) -> str:
    """Verschlüsselt ein Passwort"""
    return get_encryption_service().encrypt(password)


def decrypt_password(encrypted_password: str) -> str:
    """Entschlüsselt ein Passwort"""
    return get_encryption_service().decrypt(encrypted_password)
