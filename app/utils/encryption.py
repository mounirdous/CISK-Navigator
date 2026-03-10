"""
Encryption utilities for sensitive data
"""

import base64
import os

from cryptography.fernet import Fernet


class EncryptionService:
    """Service for encrypting/decrypting sensitive data like SSO client secrets"""

    _fernet = None

    @classmethod
    def _get_fernet(cls):
        """Get or create Fernet cipher instance"""
        if cls._fernet is None:
            key = os.environ.get("ENCRYPTION_KEY")
            if not key:
                raise ValueError(
                    "ENCRYPTION_KEY environment variable not set. "
                    "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )
            cls._fernet = Fernet(key.encode())
        return cls._fernet

    @classmethod
    def encrypt(cls, plaintext: str) -> str:
        """
        Encrypt a string.

        Args:
            plaintext: The string to encrypt

        Returns:
            Base64-encoded encrypted string
        """
        if not plaintext:
            return None

        fernet = cls._get_fernet()
        encrypted = fernet.encrypt(plaintext.encode())
        return base64.b64encode(encrypted).decode()

    @classmethod
    def decrypt(cls, encrypted_text: str) -> str:
        """
        Decrypt a string.

        Args:
            encrypted_text: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string
        """
        if not encrypted_text:
            return None

        try:
            fernet = cls._get_fernet()
            encrypted = base64.b64decode(encrypted_text.encode())
            decrypted = fernet.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")

    @classmethod
    def generate_key(cls) -> str:
        """
        Generate a new encryption key.

        Returns:
            Base64-encoded Fernet key
        """
        return Fernet.generate_key().decode()
