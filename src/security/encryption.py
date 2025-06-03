"""Encryption utilities for data protection"""

import base64
import os
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from loguru import logger

from ..config import settings


class EncryptionManager:
    """Manage encryption operations"""
    
    def __init__(self):
        self.master_key = self._get_or_create_master_key()
        self.fernet = Fernet(self.master_key)
        self.aes_gcm = AESGCM(self.master_key[:32])  # Use first 32 bytes for AES-256
        
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key"""
        if settings.master_key:
            # Decode from base64 if provided
            return base64.urlsafe_b64decode(settings.master_key.encode())
        else:
            # Generate new key (for development only)
            logger.warning("Generating new master key - not for production use!")
            key = Fernet.generate_key()
            logger.info(f"Generated key: {key.decode()}")
            return key
            
    def encrypt_string(self, plaintext: str) -> str:
        """Encrypt a string using Fernet"""
        try:
            encrypted = self.fernet.encrypt(plaintext.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
            
    def decrypt_string(self, ciphertext: str) -> str:
        """Decrypt a string using Fernet"""
        try:
            decoded = base64.urlsafe_b64decode(ciphertext.encode())
            decrypted = self.fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
            
    def encrypt_data(self, data: bytes, associated_data: Optional[bytes] = None) -> Dict[str, bytes]:
        """Encrypt data using AES-GCM with authentication"""
        try:
            # Generate nonce
            nonce = os.urandom(12)
            
            # Encrypt
            ciphertext = self.aes_gcm.encrypt(
                nonce,
                data,
                associated_data
            )
            
            return {
                "nonce": nonce,
                "ciphertext": ciphertext,
                "associated_data": associated_data
            }
        except Exception as e:
            logger.error(f"Data encryption failed: {e}")
            raise
            
    def decrypt_data(
        self,
        nonce: bytes,
        ciphertext: bytes,
        associated_data: Optional[bytes] = None
    ) -> bytes:
        """Decrypt data using AES-GCM"""
        try:
            plaintext = self.aes_gcm.decrypt(
                nonce,
                ciphertext,
                associated_data
            )
            return plaintext
        except Exception as e:
            logger.error(f"Data decryption failed: {e}")
            raise
            
    def encrypt_field(self, field_value: Any, field_name: str) -> str:
        """Encrypt a specific field for storage"""
        # Convert to string representation
        value_str = str(field_value)
        
        # Add field name as context
        context = f"{field_name}:{value_str}"
        
        # Encrypt
        return self.encrypt_string(context)
        
    def decrypt_field(self, encrypted_value: str, field_name: str) -> str:
        """Decrypt a specific field"""
        # Decrypt
        decrypted = self.decrypt_string(encrypted_value)
        
        # Verify context
        if not decrypted.startswith(f"{field_name}:"):
            raise ValueError("Field name mismatch in decrypted data")
            
        # Extract value
        return decrypted[len(field_name) + 1:]
        
    def generate_key_pair(self) -> tuple[bytes, bytes]:
        """Generate RSA key pair for asymmetric encryption"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096
        )
        
        # Serialize private key
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Serialize public key
        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        return private_pem, public_pem
        
    def rotate_master_key(self, new_key: bytes) -> None:
        """Rotate the master encryption key"""
        logger.info("Starting master key rotation")
        
        # This would involve:
        # 1. Decrypt all data with old key
        # 2. Re-encrypt with new key
        # 3. Update key storage
        # 4. Verify all data is accessible
        
        # For now, just update the key
        self.master_key = new_key
        self.fernet = Fernet(new_key)
        self.aes_gcm = AESGCM(new_key[:32])
        
        logger.info("Master key rotation completed")


class FieldEncryptor:
    """Handle field-level encryption for documents"""
    
    def __init__(self, encryption_manager: EncryptionManager):
        self.encryption_manager = encryption_manager
        self.encrypted_fields = [
            "content",
            "user_email",
            "api_key",
            "personal_data"
        ]
        
    def encrypt_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields in a document"""
        encrypted_doc = document.copy()
        
        for field in self.encrypted_fields:
            if field in encrypted_doc:
                encrypted_doc[field] = self.encryption_manager.encrypt_field(
                    encrypted_doc[field],
                    field
                )
                encrypted_doc[f"{field}_encrypted"] = True
                
        return encrypted_doc
        
    def decrypt_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive fields in a document"""
        decrypted_doc = document.copy()
        
        for field in self.encrypted_fields:
            if f"{field}_encrypted" in decrypted_doc and decrypted_doc[f"{field}_encrypted"]:
                decrypted_doc[field] = self.encryption_manager.decrypt_field(
                    decrypted_doc[field],
                    field
                )
                del decrypted_doc[f"{field}_encrypted"]
                
        return decrypted_doc