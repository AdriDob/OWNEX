"""Tests for Devin AI provider."""

import pytest
from unittest.mock import Mock, patch
from cores.ai.providers.devin_provider import DevinProvider


class TestDevinProvider:
    """Test suite for Devin provider."""

    def test_init_default(self):
        """Test default initialization."""
        provider = DevinProvider()
        assert provider.devin_path == "devin"
        assert provider.model == "default"
        assert provider._available is None

    def test_init_custom(self):
        """Test custom initialization."""
        provider = DevinProvider(devin_path="/custom/path/devin", model="swe-1.6-slow")
        assert provider.devin_path == "/custom/path/devin"
        assert provider.model == "swe-1.6-slow"

    def test_name_property(self):
        """Test provider name property."""
        provider = DevinProvider(model="swe-1.6-slow")
        assert provider.name == "devin/swe-1.6-slow"

    @patch('subprocess.run')
    def test_check_available(self, mock_run):
        """Test check when Devin is available."""
        mock_run.return_value = Mock(returncode=0)
        provider = DevinProvider()
        assert provider.is_available() is True
        mock_run.assert_called_once_with(["devin", "--version"], capture_output=True, timeout=10, text=True)

    @patch('subprocess.run')
    def test_check_unavailable_file_not_found(self, mock_run):
        """Test check when Devin binary is not found."""
        mock_run.side_effect = FileNotFoundError()
        provider = DevinProvider()
        assert provider.is_available() is False

    @patch('subprocess.run')
    def test_check_unavailable_timeout(self, mock_run):
        """Test check when Devin times out."""
        mock_run.side_effect = __import__('subprocess').TimeoutExpired("devin", 10)
        provider = DevinProvider()
        assert provider.is_available() is False

    def test_format_prompt(self):
        """Test prompt formatting."""
        provider = DevinProvider()
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]
        prompt = provider._format_prompt(messages)
        assert "System: You are a helpful assistant." in prompt
        assert "User: Hello!" in prompt
        assert "Assistant: Hi there!" in prompt
        assert "User: How are you?" in prompt
        assert "Please provide a concise response." in prompt

    @patch('subprocess.run')
    def test_chat_success(self, mock_run):
        """Test successful chat call."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Devin response here",
            stderr=""
        )
        provider = DevinProvider()
        provider._available = True  # Skip availability check
        
        messages = [{"role": "user", "content": "Test message"}]
        result = provider.chat(messages)
        
        assert result == "Devin response here"
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_chat_error(self, mock_run):
        """Test chat call with error."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Error occurred"
        )
        provider = DevinProvider()
        provider._available = True
        
        messages = [{"role": "user", "content": "Test message"}]
        result = provider.chat(messages)
        
        assert result == ""

    @patch('subprocess.run')
    def test_chat_timeout(self, mock_run):
        """Test chat call with timeout."""
        mock_run.side_effect = __import__('subprocess').TimeoutExpired("devin", 120)
        provider = DevinProvider()
        provider._available = True
        
        messages = [{"role": "user", "content": "Test message"}]
        result = provider.chat(messages)
        
        assert result == ""
        assert provider._available is False

    def test_get_config(self):
        """Test get_config method."""
        provider = DevinProvider(devin_path="/custom/devin", model="custom-model")
        config = provider.get_config()
        
        assert config["provider"] == "devin/custom-model"
        assert config["model"] == "custom-model"
        assert config["devin_path"] == "/custom/devin"
        assert "available" in config

    def test_is_available_caching(self):
        """Test that availability check is cached."""
        provider = DevinProvider()
        provider._available = True
        
        # Should return cached value without calling subprocess
        assert provider.is_available() is True
        assert provider._available is True