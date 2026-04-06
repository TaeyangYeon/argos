"""
Secure API key encryption and storage for the Argos vision algorithm design system.

This module provides encrypted storage for API keys using Fernet encryption,
ensuring keys are never stored in plaintext and are protected by machine-local
encryption keys.

SECURITY: This module handles sensitive credentials. All API keys are encrypted
before storage and never logged in plaintext.
"""

from pathlib import Path
from typing import List, Optional

from cryptography.fernet import Fernet, InvalidToken

from core.exceptions import RuntimeProcessingError
from core.logger import get_logger
from core.providers.base_provider import ProviderStatus
from config.paths import CONFIG_DIR


class KeyManager:
    """
    Secure manager for encrypted API key storage.
    
    Uses Fernet encryption to store API keys in encrypted files with
    machine-local encryption keys for maximum security.
    """
    
    # SECURITY: Project salt for key derivation - never log this value
    _PROJECT_SALT = b"argos-vision-agent-v1"
    
    def __init__(self, storage_dir: Path = CONFIG_DIR):
        """
        Initialize the key manager with secure storage.
        
        Args:
            storage_dir: Directory for storing encrypted keys (default: CONFIG_DIR)
        """
        self._storage_dir = Path(storage_dir)
        self._logger = get_logger("key_manager")
        
        # Create storage directory if it doesn't exist
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Fernet encryption
        self._fernet = self._get_or_create_fernet_key()
    
    def _get_or_create_fernet_key(self) -> Fernet:
        """
        Get or create the Fernet encryption key for this machine.
        
        Returns:
            Fernet instance for encryption/decryption
        """
        key_file = self._storage_dir / ".argos.key"
        
        if key_file.exists():
            # SECURITY: Load existing key file - never log key contents
            try:
                with open(key_file, 'rb') as f:
                    key_data = f.read()
                return Fernet(key_data)
            except Exception as e:
                self._logger.error(f"Failed to load encryption key: {e}")
                raise RuntimeProcessingError(f"Failed to load encryption key: {e}")
        else:
            # SECURITY: Generate new Fernet key - never log key contents
            key_data = Fernet.generate_key()
            
            try:
                # SECURITY: Save key with restricted permissions (owner read/write only)
                with open(key_file, 'wb') as f:
                    f.write(key_data)
                key_file.chmod(0o600)
                
                self._logger.info("Generated new encryption key")
                return Fernet(key_data)
                
            except Exception as e:
                self._logger.error(f"Failed to save encryption key: {e}")
                raise RuntimeProcessingError(f"Failed to save encryption key: {e}")
    
    def save(self, provider_name: str, api_key: str) -> None:
        """
        Save an encrypted API key for a provider.
        
        Args:
            provider_name: Name of the provider (e.g., "openai", "claude")
            api_key: The API key to encrypt and store
            
        Raises:
            ValueError: If api_key is empty
            RuntimeProcessingError: If encryption or file operations fail
        """
        if not api_key or not api_key.strip():
            raise ValueError("API key must not be empty")
        
        # SECURITY: Never log the raw api_key value
        try:
            # Encrypt the API key
            encrypted_key = self._fernet.encrypt(api_key.encode('utf-8'))
            
            # Save to encrypted file
            key_file = self._storage_dir / f".{provider_name}.enc"
            with open(key_file, 'wb') as f:
                f.write(encrypted_key)
            
            # SECURITY: Set restrictive file permissions (owner read/write only)
            key_file.chmod(0o600)
            
            self._logger.info(f"Saved encrypted API key for provider: {provider_name}")
            
        except Exception as e:
            self._logger.error(f"Failed to save API key for {provider_name}: {e}")
            raise RuntimeProcessingError(f"Failed to save API key for {provider_name}: {e}")
    
    def load(self, provider_name: str) -> Optional[str]:
        """
        Load and decrypt an API key for a provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Decrypted API key string, or None if not found
            
        Raises:
            RuntimeProcessingError: If decryption fails
        """
        key_file = self._storage_dir / f".{provider_name}.enc"
        
        if not key_file.exists():
            return None
        
        try:
            # Load encrypted key
            with open(key_file, 'rb') as f:
                encrypted_key = f.read()
            
            # SECURITY: Decrypt and return - never log the decrypted value
            decrypted_key = self._fernet.decrypt(encrypted_key)
            return decrypted_key.decode('utf-8')
            
        except InvalidToken:
            self._logger.error(f"Invalid encryption token for {provider_name} - key may be corrupted")
            raise RuntimeProcessingError(f"Invalid encryption token for {provider_name}")
        except Exception as e:
            self._logger.error(f"Failed to load API key for {provider_name}: {e}")
            raise RuntimeProcessingError(f"Failed to load API key for {provider_name}: {e}")
    
    def delete(self, provider_name: str) -> None:
        """
        Delete the encrypted API key for a provider.
        
        Args:
            provider_name: Name of the provider
        """
        key_file = self._storage_dir / f".{provider_name}.enc"
        
        if key_file.exists():
            try:
                key_file.unlink()
                self._logger.info(f"Deleted API key for provider: {provider_name}")
            except Exception as e:
                self._logger.error(f"Failed to delete API key for {provider_name}: {e}")
                raise RuntimeProcessingError(f"Failed to delete API key for {provider_name}: {e}")
    
    def exists(self, provider_name: str) -> bool:
        """
        Check if an encrypted API key exists for a provider.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            True if encrypted key file exists, False otherwise
        """
        key_file = self._storage_dir / f".{provider_name}.enc"
        return key_file.exists()
    
    def list_saved_providers(self) -> List[str]:
        """
        Get list of provider names that have saved encrypted keys.
        
        Returns:
            List of provider names with saved keys
        """
        try:
            # Find all .*.enc files in storage directory
            encrypted_files = list(self._storage_dir.glob(".*.enc"))
            
            # Extract provider names (remove leading dot and .enc extension)
            provider_names = []
            for file_path in encrypted_files:
                filename = file_path.name
                if filename.startswith('.') and filename.endswith('.enc'):
                    # Remove leading dot and .enc extension
                    provider_name = filename[1:-4]  # Remove '.' and '.enc'
                    provider_names.append(provider_name)
            
            return sorted(provider_names)
            
        except Exception as e:
            self._logger.error(f"Failed to list saved providers: {e}")
            return []
    
    def get_provider_status(self, provider_name: str) -> ProviderStatus:
        """
        Get the connection status of a provider based on stored key.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            CONNECTED if key exists, DISCONNECTED otherwise
        """
        if self.exists(provider_name):
            return ProviderStatus.CONNECTED
        else:
            return ProviderStatus.DISCONNECTED