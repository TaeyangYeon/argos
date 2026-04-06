"""
Unit tests for the secure key manager.

Tests all functionality of the KeyManager class including encryption,
storage, retrieval, and security features using isolated temporary directories.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from core.exceptions import RuntimeProcessingError
from core.key_manager import KeyManager
from core.providers.base_provider import ProviderStatus


class TestKeyManager:
    """Tests for the KeyManager class."""
    
    def test_save_and_load_roundtrip(self, tmp_path):
        """Test saving and loading a key returns the original value."""
        key_manager = KeyManager(storage_dir=tmp_path)
        original_key = "sk-test-key-12345"
        
        key_manager.save("openai", original_key)
        loaded_key = key_manager.load("openai")
        
        assert loaded_key == original_key
    
    def test_load_returns_none_if_not_exists(self, tmp_path):
        """Test loading a non-existent key returns None."""
        key_manager = KeyManager(storage_dir=tmp_path)
        
        result = key_manager.load("nonexistent")
        
        assert result is None
    
    def test_delete_removes_key(self, tmp_path):
        """Test deleting a key removes it from storage."""
        key_manager = KeyManager(storage_dir=tmp_path)
        
        # Save a key
        key_manager.save("openai", "test-key")
        assert key_manager.exists("openai") is True
        
        # Delete the key
        key_manager.delete("openai")
        assert key_manager.exists("openai") is False
    
    def test_exists_returns_true_after_save(self, tmp_path):
        """Test exists returns True after saving a key."""
        key_manager = KeyManager(storage_dir=tmp_path)
        
        key_manager.save("claude", "test-claude-key")
        
        assert key_manager.exists("claude") is True
    
    def test_exists_returns_false_before_save(self, tmp_path):
        """Test exists returns False for unsaved keys."""
        key_manager = KeyManager(storage_dir=tmp_path)
        
        assert key_manager.exists("gemini") is False
    
    def test_save_empty_key_raises_value_error(self, tmp_path):
        """Test saving empty key raises ValueError."""
        key_manager = KeyManager(storage_dir=tmp_path)
        
        with pytest.raises(ValueError, match="API key must not be empty"):
            key_manager.save("openai", "")
        
        with pytest.raises(ValueError, match="API key must not be empty"):
            key_manager.save("openai", "   ")
    
    def test_list_saved_providers(self, tmp_path):
        """Test listing saved providers returns correct names."""
        key_manager = KeyManager(storage_dir=tmp_path)
        
        # Save keys for multiple providers
        key_manager.save("openai", "openai-key")
        key_manager.save("claude", "claude-key")
        key_manager.save("gemini", "gemini-key")
        
        providers = key_manager.list_saved_providers()
        
        assert len(providers) == 3
        assert "openai" in providers
        assert "claude" in providers
        assert "gemini" in providers
    
    def test_list_saved_providers_empty_directory(self, tmp_path):
        """Test listing providers in empty directory returns empty list."""
        key_manager = KeyManager(storage_dir=tmp_path)
        
        providers = key_manager.list_saved_providers()
        
        assert providers == []
    
    def test_get_provider_status_connected(self, tmp_path):
        """Test provider status is CONNECTED when key exists."""
        key_manager = KeyManager(storage_dir=tmp_path)
        
        key_manager.save("openai", "test-key")
        status = key_manager.get_provider_status("openai")
        
        assert status == ProviderStatus.CONNECTED
    
    def test_get_provider_status_disconnected(self, tmp_path):
        """Test provider status is DISCONNECTED when no key exists."""
        key_manager = KeyManager(storage_dir=tmp_path)
        
        status = key_manager.get_provider_status("openai")
        
        assert status == ProviderStatus.DISCONNECTED
    
    def test_encrypted_file_is_not_plaintext(self, tmp_path):
        """Test that encrypted files do not contain plaintext keys."""
        key_manager = KeyManager(storage_dir=tmp_path)
        original_key = "sk-super-secret-key-12345"
        
        key_manager.save("openai", original_key)
        
        # Read the encrypted file directly
        encrypted_file = tmp_path / ".openai.enc"
        with open(encrypted_file, 'rb') as f:
            encrypted_data = f.read()
        
        # Verify the original key is NOT present in the encrypted data
        assert original_key.encode('utf-8') not in encrypted_data
        assert b"sk-super-secret-key" not in encrypted_data
    
    def test_key_file_not_logged(self, tmp_path, caplog):
        """Test that API keys are never logged in plaintext."""
        import logging
        
        key_manager = KeyManager(storage_dir=tmp_path)
        secret_key = "sk-very-secret-key-should-not-be-logged"
        
        # Capture all log levels
        with caplog.at_level(logging.DEBUG):
            key_manager.save("openai", secret_key)
            loaded_key = key_manager.load("openai")
        
        # Verify the secret key never appears in any log message
        all_log_text = " ".join([record.message for record in caplog.records])
        assert secret_key not in all_log_text
        assert "sk-very-secret-key" not in all_log_text
        assert "should-not-be-logged" not in all_log_text
    
    def test_save_overwrites_existing_key(self, tmp_path):
        """Test that saving overwrites existing keys silently."""
        key_manager = KeyManager(storage_dir=tmp_path)
        
        # Save initial key
        key_manager.save("openai", "first-key")
        assert key_manager.load("openai") == "first-key"
        
        # Overwrite with new key
        key_manager.save("openai", "second-key")
        assert key_manager.load("openai") == "second-key"
    
    def test_multiple_providers_independent(self, tmp_path):
        """Test that multiple providers have independent encrypted storage."""
        key_manager = KeyManager(storage_dir=tmp_path)
        
        # Save different keys for different providers
        key_manager.save("openai", "openai-specific-key")
        key_manager.save("claude", "claude-specific-key")
        
        # Verify each provider has its own key
        assert key_manager.load("openai") == "openai-specific-key"
        assert key_manager.load("claude") == "claude-specific-key"
        
        # Delete one provider's key
        key_manager.delete("openai")
        assert key_manager.exists("openai") is False
        assert key_manager.exists("claude") is True
        assert key_manager.load("claude") == "claude-specific-key"
    
    def test_storage_directory_creation(self, tmp_path):
        """Test that storage directory is created if it doesn't exist."""
        non_existent_dir = tmp_path / "new_storage"
        assert not non_existent_dir.exists()
        
        key_manager = KeyManager(storage_dir=non_existent_dir)
        
        # Directory should be created during initialization
        assert non_existent_dir.exists()
        assert non_existent_dir.is_dir()
        
        # Should be able to save keys
        key_manager.save("test", "test-key")
        assert key_manager.exists("test") is True
    
    def test_key_file_permissions(self, tmp_path):
        """Test that key files are created with secure permissions."""
        key_manager = KeyManager(storage_dir=tmp_path)
        
        key_manager.save("openai", "test-key")
        
        # Check file permissions
        key_file = tmp_path / ".openai.enc"
        file_mode = key_file.stat().st_mode
        
        # Should be owner read/write only (0o600)
        assert oct(file_mode)[-3:] == "600"
    
    def test_encryption_key_file_permissions(self, tmp_path):
        """Test that the master encryption key file has secure permissions."""
        key_manager = KeyManager(storage_dir=tmp_path)
        
        # Trigger creation of encryption key by saving something
        key_manager.save("test", "test-key")
        
        # Check encryption key file permissions
        key_file = tmp_path / ".argos.key"
        assert key_file.exists()
        
        file_mode = key_file.stat().st_mode
        # Should be owner read/write only (0o600)
        assert oct(file_mode)[-3:] == "600"
    
    def test_delete_nonexistent_key_no_error(self, tmp_path):
        """Test that deleting a non-existent key doesn't raise an error."""
        key_manager = KeyManager(storage_dir=tmp_path)
        
        # Should not raise an error
        key_manager.delete("nonexistent")
    
    def test_load_decryption_failure_raises_runtime_error(self, tmp_path):
        """Test that decryption failures raise RuntimeProcessingError."""
        key_manager = KeyManager(storage_dir=tmp_path)
        
        # Create a file with invalid encrypted data that will fail decryption
        key_file = tmp_path / ".test.enc"
        key_file.write_bytes(b"invalid encrypted data that cannot be decrypted")
        
        with pytest.raises(RuntimeProcessingError, match="Invalid encryption token"):
            key_manager.load("test")
    
    def test_encryption_key_reuse(self, tmp_path):
        """Test that the same encryption key is reused across KeyManager instances."""
        # Create first key manager and save a key
        key_manager1 = KeyManager(storage_dir=tmp_path)
        key_manager1.save("openai", "test-key")
        
        # Create second key manager with same storage directory
        key_manager2 = KeyManager(storage_dir=tmp_path)
        
        # Should be able to load the key saved by the first instance
        loaded_key = key_manager2.load("openai")
        assert loaded_key == "test-key"