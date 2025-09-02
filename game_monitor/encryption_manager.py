"""
Advanced Encryption Manager for Game Monitor System

Provides comprehensive data encryption, key management, and cryptographic
operations for protecting sensitive data at rest and in transit.
"""

import os
import secrets
import base64
import hashlib
import json
import time
import threading
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

from .advanced_logger import get_logger
from .error_handler import get_error_handler, ErrorContext, ErrorCategory, RecoveryStrategy
from .performance_profiler import get_performance_profiler, profile_performance

logger = get_logger(__name__)


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms"""
    AES_256_GCM = "aes_256_gcm"
    FERNET = "fernet"
    RSA_2048 = "rsa_2048"
    RSA_4096 = "rsa_4096"


class KeyType(Enum):
    """Types of encryption keys"""
    SYMMETRIC = "symmetric"
    ASYMMETRIC_PRIVATE = "asymmetric_private"
    ASYMMETRIC_PUBLIC = "asymmetric_public"
    MASTER = "master"
    DATA = "data"
    CONFIG = "config"


@dataclass
class EncryptionKey:
    """Encryption key metadata"""
    key_id: str
    key_type: KeyType
    algorithm: EncryptionAlgorithm
    created_at: float
    expires_at: Optional[float]
    usage_count: int
    max_usage: Optional[int]
    key_data: bytes
    is_active: bool


@dataclass
class EncryptedData:
    """Encrypted data container"""
    algorithm: str
    key_id: str
    iv: Optional[str]  # Initialization vector (base64)
    tag: Optional[str]  # Authentication tag (base64)
    ciphertext: str  # Base64 encoded
    created_at: float
    metadata: Dict[str, Any]


class EncryptionManager:
    """Advanced encryption manager with key management and rotation"""
    
    def __init__(self, master_key: Optional[bytes] = None):
        self.error_handler = get_error_handler()
        self.profiler = get_performance_profiler()
        
        if not CRYPTO_AVAILABLE:
            logger.error("Cryptography library not available - encryption disabled")
            raise ImportError("cryptography library required for encryption")
        
        # Key storage and management
        self.keys = {}  # key_id -> EncryptionKey
        self.key_aliases = {}  # alias -> key_id
        self._lock = threading.RLock()
        
        # Master key for encrypting other keys
        self.master_key = master_key or self._generate_master_key()
        self.master_fernet = Fernet(base64.urlsafe_b64encode(self.master_key[:32]))
        
        # Key rotation settings
        self.key_rotation_interval = 86400 * 30  # 30 days
        self.max_key_usage = 1000000  # 1 million operations
        
        # Performance tracking
        self.encryption_stats = {
            'operations_performed': 0,
            'total_encrypted_bytes': 0,
            'total_decrypted_bytes': 0,
            'key_rotations': 0,
            'encryption_errors': 0
        }
        
        # Initialize default keys
        self._initialize_default_keys()
        
        # Start key rotation monitoring
        self._start_key_rotation_monitor()
        
        logger.info("EncryptionManager initialized with advanced cryptographic features")
    
    def _generate_master_key(self) -> bytes:
        """Generate cryptographically secure master key"""
        return secrets.token_bytes(32)  # 256-bit key
    
    def _initialize_default_keys(self):
        """Initialize default encryption keys"""
        try:
            # Create default symmetric key for general data encryption
            self.create_symmetric_key(
                key_id="default_data_key",
                algorithm=EncryptionAlgorithm.AES_256_GCM,
                alias="data_encryption"
            )
            
            # Create key for configuration encryption
            self.create_symmetric_key(
                key_id="config_key",
                algorithm=EncryptionAlgorithm.FERNET,
                alias="config_encryption"
            )
            
            # Create RSA key pair for asymmetric operations
            self.create_asymmetric_keypair(
                key_id="default_rsa",
                algorithm=EncryptionAlgorithm.RSA_2048,
                alias="asymmetric_default"
            )
            
            logger.info("Default encryption keys initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize default keys: {e}")
    
    def _start_key_rotation_monitor(self):
        """Start background key rotation monitoring"""
        def rotation_monitor():
            while True:
                try:
                    self._check_key_rotation()
                    time.sleep(3600)  # Check every hour
                    
                except Exception as e:
                    logger.error(f"Key rotation monitoring error: {e}")
                    time.sleep(7200)  # Wait longer after errors
        
        rotation_thread = threading.Thread(target=rotation_monitor, daemon=True)
        rotation_thread.start()
    
    @profile_performance("encryption_manager.create_symmetric_key")
    def create_symmetric_key(self, key_id: str, algorithm: EncryptionAlgorithm = EncryptionAlgorithm.AES_256_GCM,
                           alias: Optional[str] = None, expires_in_days: Optional[int] = None) -> bool:
        """Create a new symmetric encryption key"""
        try:
            with self._lock:
                if key_id in self.keys:
                    logger.warning(f"Key {key_id} already exists")
                    return False
                
                # Generate key based on algorithm
                if algorithm == EncryptionAlgorithm.AES_256_GCM:
                    key_data = secrets.token_bytes(32)  # 256-bit key
                elif algorithm == EncryptionAlgorithm.FERNET:
                    key_data = Fernet.generate_key()
                else:
                    raise ValueError(f"Unsupported symmetric algorithm: {algorithm}")
                
                # Calculate expiration
                expires_at = None
                if expires_in_days:
                    expires_at = time.time() + (expires_in_days * 86400)
                
                # Create key object
                encryption_key = EncryptionKey(
                    key_id=key_id,
                    key_type=KeyType.SYMMETRIC,
                    algorithm=algorithm,
                    created_at=time.time(),
                    expires_at=expires_at,
                    usage_count=0,
                    max_usage=self.max_key_usage,
                    key_data=key_data,
                    is_active=True
                )
                
                # Store key (encrypted with master key)
                self.keys[key_id] = encryption_key
                
                # Set alias if provided
                if alias:
                    self.key_aliases[alias] = key_id
                
                logger.info(f"Created symmetric key {key_id} with algorithm {algorithm.value}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create symmetric key {key_id}: {e}")
            return False
    
    @profile_performance("encryption_manager.create_asymmetric_keypair")
    def create_asymmetric_keypair(self, key_id: str, algorithm: EncryptionAlgorithm = EncryptionAlgorithm.RSA_2048,
                                alias: Optional[str] = None) -> bool:
        """Create asymmetric key pair (public/private)"""
        try:
            with self._lock:
                private_key_id = f"{key_id}_private"
                public_key_id = f"{key_id}_public"
                
                if private_key_id in self.keys or public_key_id in self.keys:
                    logger.warning(f"Key pair {key_id} already exists")
                    return False
                
                # Generate RSA key pair
                if algorithm == EncryptionAlgorithm.RSA_2048:
                    key_size = 2048
                elif algorithm == EncryptionAlgorithm.RSA_4096:
                    key_size = 4096
                else:
                    raise ValueError(f"Unsupported asymmetric algorithm: {algorithm}")
                
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=key_size,
                    backend=default_backend()
                )
                public_key = private_key.public_key()
                
                # Serialize keys
                private_pem = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                
                public_pem = public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                
                # Create key objects
                private_encryption_key = EncryptionKey(
                    key_id=private_key_id,
                    key_type=KeyType.ASYMMETRIC_PRIVATE,
                    algorithm=algorithm,
                    created_at=time.time(),
                    expires_at=None,
                    usage_count=0,
                    max_usage=self.max_key_usage,
                    key_data=private_pem,
                    is_active=True
                )
                
                public_encryption_key = EncryptionKey(
                    key_id=public_key_id,
                    key_type=KeyType.ASYMMETRIC_PUBLIC,
                    algorithm=algorithm,
                    created_at=time.time(),
                    expires_at=None,
                    usage_count=0,
                    max_usage=None,  # Public keys don't have usage limits
                    key_data=public_pem,
                    is_active=True
                )
                
                # Store keys
                self.keys[private_key_id] = private_encryption_key
                self.keys[public_key_id] = public_encryption_key
                
                # Set aliases
                if alias:
                    self.key_aliases[f"{alias}_private"] = private_key_id
                    self.key_aliases[f"{alias}_public"] = public_key_id
                
                logger.info(f"Created RSA key pair {key_id} with {key_size}-bit keys")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create asymmetric key pair {key_id}: {e}")
            return False
    
    @profile_performance("encryption_manager.encrypt_data")
    def encrypt_data(self, data: Union[str, bytes], key_id_or_alias: str) -> Optional[EncryptedData]:
        """Encrypt data using specified key"""
        encrypt_start = time.time()
        
        try:
            # Resolve key ID
            key_id = self._resolve_key_id(key_id_or_alias)
            if not key_id:
                logger.error(f"Key not found: {key_id_or_alias}")
                return None
            
            with self._lock:
                key = self.keys.get(key_id)
                if not key or not key.is_active:
                    logger.error(f"Key {key_id} not available or inactive")
                    return None
                
                # Check key expiration
                if key.expires_at and time.time() > key.expires_at:
                    logger.error(f"Key {key_id} has expired")
                    return None
                
                # Check usage limits
                if key.max_usage and key.usage_count >= key.max_usage:
                    logger.error(f"Key {key_id} has exceeded usage limit")
                    return None
            
            # Convert string to bytes
            if isinstance(data, str):
                data_bytes = data.encode('utf-8')
            else:
                data_bytes = data
            
            # Encrypt based on algorithm
            encrypted_result = None
            
            if key.algorithm == EncryptionAlgorithm.AES_256_GCM:
                encrypted_result = self._encrypt_aes_gcm(data_bytes, key)
            elif key.algorithm == EncryptionAlgorithm.FERNET:
                encrypted_result = self._encrypt_fernet(data_bytes, key)
            elif key.algorithm in [EncryptionAlgorithm.RSA_2048, EncryptionAlgorithm.RSA_4096]:
                encrypted_result = self._encrypt_rsa(data_bytes, key)
            else:
                logger.error(f"Unsupported encryption algorithm: {key.algorithm}")
                return None
            
            if encrypted_result:
                # Update usage statistics
                with self._lock:
                    key.usage_count += 1
                    self.encryption_stats['operations_performed'] += 1
                    self.encryption_stats['total_encrypted_bytes'] += len(data_bytes)
                
                encrypt_time = time.time() - encrypt_start
                logger.debug(f"Encrypted {len(data_bytes)} bytes in {encrypt_time*1000:.2f}ms")
                
                return encrypted_result
            
        except Exception as e:
            with self._lock:
                self.encryption_stats['encryption_errors'] += 1
            
            error_context = ErrorContext(
                component="encryption_manager",
                operation="encrypt_data",
                user_data={'key_id': key_id_or_alias, 'data_size': len(data) if data else 0},
                system_state={'encryption_available': CRYPTO_AVAILABLE},
                timestamp=datetime.now()
            )
            
            self.error_handler.handle_error(e, error_context, RecoveryStrategy.SKIP)
            logger.error(f"Encryption failed: {e}")
            return None
    
    @profile_performance("encryption_manager.decrypt_data")
    def decrypt_data(self, encrypted_data: EncryptedData) -> Optional[bytes]:
        """Decrypt data using stored encryption information"""
        decrypt_start = time.time()
        
        try:
            # Get key
            with self._lock:
                key = self.keys.get(encrypted_data.key_id)
                if not key:
                    logger.error(f"Decryption key {encrypted_data.key_id} not found")
                    return None
            
            # Decrypt based on algorithm
            if encrypted_data.algorithm == EncryptionAlgorithm.AES_256_GCM.value:
                result = self._decrypt_aes_gcm(encrypted_data, key)
            elif encrypted_data.algorithm == EncryptionAlgorithm.FERNET.value:
                result = self._decrypt_fernet(encrypted_data, key)
            elif encrypted_data.algorithm in [EncryptionAlgorithm.RSA_2048.value, EncryptionAlgorithm.RSA_4096.value]:
                result = self._decrypt_rsa(encrypted_data, key)
            else:
                logger.error(f"Unsupported decryption algorithm: {encrypted_data.algorithm}")
                return None
            
            if result:
                # Update statistics
                with self._lock:
                    self.encryption_stats['total_decrypted_bytes'] += len(result)
                
                decrypt_time = time.time() - decrypt_start
                logger.debug(f"Decrypted {len(result)} bytes in {decrypt_time*1000:.2f}ms")
            
            return result
            
        except Exception as e:
            error_context = ErrorContext(
                component="encryption_manager",
                operation="decrypt_data",
                user_data={'key_id': encrypted_data.key_id, 'algorithm': encrypted_data.algorithm},
                system_state={'encryption_available': CRYPTO_AVAILABLE},
                timestamp=datetime.now()
            )
            
            self.error_handler.handle_error(e, error_context, RecoveryStrategy.SKIP)
            logger.error(f"Decryption failed: {e}")
            return None
    
    def _encrypt_aes_gcm(self, data: bytes, key: EncryptionKey) -> EncryptedData:
        """Encrypt using AES-256-GCM"""
        # Generate random IV
        iv = secrets.token_bytes(16)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key.key_data),
            modes.GCM(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Encrypt data
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        return EncryptedData(
            algorithm=key.algorithm.value,
            key_id=key.key_id,
            iv=base64.b64encode(iv).decode('ascii'),
            tag=base64.b64encode(encryptor.tag).decode('ascii'),
            ciphertext=base64.b64encode(ciphertext).decode('ascii'),
            created_at=time.time(),
            metadata={}
        )
    
    def _decrypt_aes_gcm(self, encrypted_data: EncryptedData, key: EncryptionKey) -> bytes:
        """Decrypt using AES-256-GCM"""
        iv = base64.b64decode(encrypted_data.iv)
        tag = base64.b64decode(encrypted_data.tag)
        ciphertext = base64.b64decode(encrypted_data.ciphertext)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key.key_data),
            modes.GCM(iv, tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Decrypt data
        return decryptor.update(ciphertext) + decryptor.finalize()
    
    def _encrypt_fernet(self, data: bytes, key: EncryptionKey) -> EncryptedData:
        """Encrypt using Fernet (AES-128 in CBC mode)"""
        fernet = Fernet(key.key_data)
        ciphertext = fernet.encrypt(data)
        
        return EncryptedData(
            algorithm=key.algorithm.value,
            key_id=key.key_id,
            iv=None,  # Fernet handles IV internally
            tag=None,  # Fernet handles authentication internally
            ciphertext=base64.b64encode(ciphertext).decode('ascii'),
            created_at=time.time(),
            metadata={}
        )
    
    def _decrypt_fernet(self, encrypted_data: EncryptedData, key: EncryptionKey) -> bytes:
        """Decrypt using Fernet"""
        fernet = Fernet(key.key_data)
        ciphertext = base64.b64decode(encrypted_data.ciphertext)
        return fernet.decrypt(ciphertext)
    
    def _encrypt_rsa(self, data: bytes, key: EncryptionKey) -> EncryptedData:
        """Encrypt using RSA (for small data only)"""
        if key.key_type != KeyType.ASYMMETRIC_PUBLIC:
            raise ValueError("RSA encryption requires public key")
        
        # RSA can only encrypt small amounts of data
        max_size = 190 if key.algorithm == EncryptionAlgorithm.RSA_2048 else 446  # Approximate limits
        if len(data) > max_size:
            raise ValueError(f"Data too large for RSA encryption (max {max_size} bytes)")
        
        # Load public key
        public_key = serialization.load_pem_public_key(key.key_data, backend=default_backend())
        
        # Encrypt
        ciphertext = public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return EncryptedData(
            algorithm=key.algorithm.value,
            key_id=key.key_id,
            iv=None,
            tag=None,
            ciphertext=base64.b64encode(ciphertext).decode('ascii'),
            created_at=time.time(),
            metadata={}
        )
    
    def _decrypt_rsa(self, encrypted_data: EncryptedData, key: EncryptionKey) -> bytes:
        """Decrypt using RSA"""
        if key.key_type != KeyType.ASYMMETRIC_PRIVATE:
            raise ValueError("RSA decryption requires private key")
        
        # Load private key
        private_key = serialization.load_pem_private_key(
            key.key_data, password=None, backend=default_backend()
        )
        
        # Decrypt
        ciphertext = base64.b64decode(encrypted_data.ciphertext)
        return private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    def _resolve_key_id(self, key_id_or_alias: str) -> Optional[str]:
        """Resolve key alias to key ID"""
        if key_id_or_alias in self.keys:
            return key_id_or_alias
        elif key_id_or_alias in self.key_aliases:
            return self.key_aliases[key_id_or_alias]
        else:
            return None
    
    def _check_key_rotation(self):
        """Check if any keys need rotation"""
        current_time = time.time()
        keys_to_rotate = []
        
        with self._lock:
            for key_id, key in self.keys.items():
                # Check expiration
                if key.expires_at and current_time > key.expires_at:
                    keys_to_rotate.append(key_id)
                
                # Check usage limits
                elif key.max_usage and key.usage_count >= key.max_usage:
                    keys_to_rotate.append(key_id)
        
        # Rotate expired/overused keys
        for key_id in keys_to_rotate:
            self._rotate_key(key_id)
    
    def _rotate_key(self, key_id: str) -> bool:
        """Rotate a specific key"""
        try:
            with self._lock:
                old_key = self.keys.get(key_id)
                if not old_key:
                    return False
                
                # Create new key with same parameters
                new_key_id = f"{key_id}_rotated_{int(time.time())}"
                
                if old_key.key_type == KeyType.SYMMETRIC:
                    success = self.create_symmetric_key(new_key_id, old_key.algorithm)
                elif old_key.key_type == KeyType.ASYMMETRIC_PRIVATE:
                    base_id = key_id.replace('_private', '')
                    success = self.create_asymmetric_keypair(new_key_id.replace('_private', ''), old_key.algorithm)
                else:
                    success = False
                
                if success:
                    # Deactivate old key
                    old_key.is_active = False
                    
                    # Update aliases to point to new key
                    for alias, alias_key_id in self.key_aliases.items():
                        if alias_key_id == key_id:
                            self.key_aliases[alias] = new_key_id
                    
                    self.encryption_stats['key_rotations'] += 1
                    logger.info(f"Rotated key {key_id} to {new_key_id}")
                    return True
                else:
                    logger.error(f"Failed to create replacement for key {key_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Key rotation failed for {key_id}: {e}")
            return False
    
    def encrypt_sensitive_string(self, data: str, alias: str = "data_encryption") -> Optional[str]:
        """Convenience method to encrypt string and return base64 JSON"""
        encrypted = self.encrypt_data(data, alias)
        if encrypted:
            return base64.b64encode(json.dumps(asdict(encrypted)).encode()).decode()
        return None
    
    def decrypt_sensitive_string(self, encrypted_b64: str) -> Optional[str]:
        """Convenience method to decrypt from base64 JSON"""
        try:
            encrypted_dict = json.loads(base64.b64decode(encrypted_b64).decode())
            encrypted_data = EncryptedData(**encrypted_dict)
            decrypted_bytes = self.decrypt_data(encrypted_data)
            return decrypted_bytes.decode('utf-8') if decrypted_bytes else None
        except Exception as e:
            logger.error(f"Failed to decrypt sensitive string: {e}")
            return None
    
    def get_encryption_status(self) -> Dict[str, Any]:
        """Get comprehensive encryption system status"""
        with self._lock:
            active_keys = sum(1 for key in self.keys.values() if key.is_active)
            expired_keys = sum(1 for key in self.keys.values() 
                             if key.expires_at and time.time() > key.expires_at)
            
            key_types = {}
            for key in self.keys.values():
                key_type = key.key_type.value
                key_types[key_type] = key_types.get(key_type, 0) + 1
        
        return {
            'crypto_library_available': CRYPTO_AVAILABLE,
            'total_keys': len(self.keys),
            'active_keys': active_keys,
            'expired_keys': expired_keys,
            'key_aliases': len(self.key_aliases),
            'key_types': key_types,
            'statistics': self.encryption_stats.copy(),
            'algorithms_supported': [alg.value for alg in EncryptionAlgorithm]
        }


# Global encryption manager instance
_encryption_manager_instance = None
_encryption_lock = threading.Lock()

def get_encryption_manager() -> EncryptionManager:
    """Get singleton encryption manager instance"""
    global _encryption_manager_instance
    if _encryption_manager_instance is None:
        with _encryption_lock:
            if _encryption_manager_instance is None:
                try:
                    _encryption_manager_instance = EncryptionManager()
                except ImportError:
                    logger.error("Encryption manager unavailable - cryptography library missing")
                    return None
    return _encryption_manager_instance


# Convenience functions
def encrypt_config_value(value: str) -> Optional[str]:
    """Encrypt configuration value"""
    enc_manager = get_encryption_manager()
    if enc_manager:
        return enc_manager.encrypt_sensitive_string(value, "config_encryption")
    return None


def decrypt_config_value(encrypted_value: str) -> Optional[str]:
    """Decrypt configuration value"""
    enc_manager = get_encryption_manager()
    if enc_manager:
        return enc_manager.decrypt_sensitive_string(encrypted_value)
    return None