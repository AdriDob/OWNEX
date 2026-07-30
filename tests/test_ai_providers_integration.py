"""Tests for AI provider implementations.

This module tests the integrated AI providers including GooseAI and AI Sandbox integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from cores.ai.providers.gooseai_provider import GooseAIProvider
from cores.integrations.ai_sandbox_integration import (
    AISandboxManager,
    AISandboxConfig,
    get_sandbox_manager,
)


class TestGooseAIProvider:
    """Test GooseAI provider functionality."""

    def test_provider_initialization(self):
        """Test that GooseAIProvider initializes with correct config."""
        provider = GooseAIProvider(api_key="test-key")
        
        assert provider.name == "gooseai/gooseai/gpt-neo-1.3b"
        assert provider.model == "gooseai/gpt-neo-1.3b"
        assert provider.api_key == "test-key"

    def test_check_without_api_key(self):
        """Test check method when no API key is configured."""
        with patch.dict("os.environ", {"GOSEAI_API_KEY": ""}):
            provider = GooseAIProvider()
            assert provider.api_key == ""
            assert not provider.is_available()

    def test_default_base_url(self):
        """Test that GooseAIProvider uses correct default base URL."""
        with patch.dict("os.environ", {}, clear=True):
            provider = GooseAIProvider()
            assert provider.base_url == "https://api.goose.ai/v1"

    def test_custom_base_url(self):
        """Test that GooseAIProvider accepts custom base URL."""
        provider = GooseAIProvider(base_url="https://custom.goose.ai/v1")
        assert provider.base_url == "https://custom.goose.ai/v1"


class TestAISandboxIntegration:
    """Test AI Sandbox integration functionality."""

    def test_config_default_values(self):
        """Test that AISandboxConfig has correct default values."""
        config = AISandboxConfig()
        
        assert config.url == "https://t.co/zpRNbNqZLR"
        assert config.description == "AI Code Sandbox with OpenCode and Claude Code pre-installed"
        assert config.includes_free_models is True
        assert config.includes_apify_scrapers is True
        assert config.monthly_credit == 5.0
        assert config.setup_time_seconds == 30

    def test_config_sandbox_url(self):
        """Test sandbox_url property."""
        config = AISandboxConfig(sandbox_host="localhost", sandbox_port=8080)
        
        assert config.sandbox_url == "http://localhost:8080"

    def test_config_is_not_configured_without_key(self):
        """Test is_configured returns False without API key."""
        config = AISandboxConfig(api_key="")
        
        assert not config.is_configured

    def test_config_is_configured_with_key(self):
        """Test is_configured returns True with API key."""
        config = AISandboxConfig(api_key="test-api-key")
        
        assert config.is_configured

    def test_manager_initialization(self):
        """Test AISandboxManager initialization."""
        config = AISandboxConfig(api_key="test-key")
        manager = AISandboxManager(config)
        
        assert manager.config == config

    def test_manager_is_available_with_key(self):
        """Test is_available returns True when configured."""
        config = AISandboxConfig(api_key="test-key")
        manager = AISandboxManager(config)
        
        assert manager.is_available() is True

    def test_manager_is_not_available_without_key(self):
        """Test is_available returns False when not configured."""
        config = AISandboxConfig(api_key="")
        manager = AISandboxManager(config)
        
        assert manager.is_available() is False

    def test_get_models(self):
        """Test get_models returns expected models."""
        config = AISandboxConfig(api_key="test-key")
        manager = AISandboxManager(config)
        
        import asyncio
        models = asyncio.run(manager.get_models())
        
        assert len(models) == 3
        assert models[0]["name"] == "claude-3-sonnet"
        assert models[0]["provider"] == "anthropic"
        assert models[0]["free_tier_included"] is True
        assert models[0]["apify_integration"] is True
        
        assert models[1]["name"] == "deepseek-coder"
        assert models[1]["provider"] == "opencode"
        assert models[1]["cost_per_1k_tokens"] == 0
        
        assert models[2]["name"] == "gpt-neo-1.3b"
        assert models[2]["provider"] == "gooseai"
        assert models[2]["cost_per_1k_tokens"] == 0.16

    def test_get_apify_scrapers(self):
        """Test get_apify_scrapers returns expected scrapers."""
        config = AISandboxConfig(api_key="test-key")
        manager = AISandboxManager(config)
        
        import asyncio
        scrapers = asyncio.run(manager.get_apify_scrapers())
        
        assert len(scrapers) == 3
        assert scrapers[0]["name"] == "web-scraper"
        assert scrapers[0]["description"] == "General web scraping"
        assert scrapers[0]["cost_per_run"] == 0.01
        
        assert scrapers[1]["name"] == "github-scraper"
        assert scrapers[1]["description"] == "GitHub repository analysis"
        
        assert scrapers[2]["name"] == "linkedin-scraper"
        assert scrapers[2]["description"] == "LinkedIn profile data extraction"

    def test_execute_task(self):
        """Test execute_task returns expected result."""
        config = AISandboxConfig(api_key="test-key")
        manager = AISandboxManager(config)
        
        import asyncio
        result = asyncio.run(manager.execute_task("test task", model="claude-3-sonnet"))
        
        assert result["success"] is True
        assert "Task executed using claude-3-sonnet" in result["result"]
        assert result["model"] == "claude-3-sonnet"
        assert result["max_tokens"] == 4096
        assert result["sandbox_url"] == "http://localhost:8080"
        assert result["cost_used"] == 0.001

    def test_get_setup_info(self):
        """Test get_setup_info returns expected information."""
        config = AISandboxConfig()
        manager = AISandboxManager(config)
        
        info = manager.get_setup_info()
        
        assert info["setup_time_seconds"] == 30
        assert info["monthly_credit"] == "$5.0"
        assert info["includes_free_models"] is True
        assert info["includes_apify_scrapers"] is True
        assert info["host"] == "localhost"
        assert info["port"] == 8080
        assert info["health_url"] == "http://localhost:8080/health"

    def test_get_setup_info_custom_port(self):
        """Test get_setup_info with custom port."""
        config = AISandboxConfig(sandbox_host="sandbox.example.com", sandbox_port=9090)
        manager = AISandboxManager(config)
        
        info = manager.get_setup_info()
        
        assert info["port"] == 9090
        assert info["health_url"] == "http://sandbox.example.com:9090/health"

    def test_get_sandbox_manager_singleton(self):
        """Test that get_sandbox_manager returns singleton."""
        manager1 = get_sandbox_manager()
        manager2 = get_sandbox_manager()
        
        assert manager1 is manager2

    def test_is_sandbox_available(self):
        """Test is_sandbox_available helper function."""
        with patch('cores.integrations.ai_sandbox_integration.get_sandbox_manager') as mock_get:
            mock_manager = MagicMock()
            mock_manager.is_available.return_value = True
            mock_get.return_value = mock_manager
            
            from cores.integrations.ai_sandbox_integration import is_sandbox_available
            result = is_sandbox_available()
            
            assert result is True
            mock_manager.is_available.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
