"""Anthropic Client 测试"""
import pytest
from app.ai.anthropic_client import AnthropicClient


class TestAnthropicClient:
    def test_instantiation(self):
        client = AnthropicClient(api_key="test", model="claude-3")
        assert client.model == "claude-3"
        assert "anthropic" in client.base_url

    def test_default_base_url(self):
        client = AnthropicClient(api_key="test")
        assert "api.anthropic.com" in client.base_url

    def test_validate_config_with_model_and_key(self):
        client = AnthropicClient(api_key="test", model="claude-3")
        assert client.validate_config() is True

    def test_validate_config_without_model(self):
        client = AnthropicClient(api_key="test", model="")
        assert client.validate_config() is False

    def test_validate_config_without_api_key(self):
        client = AnthropicClient(api_key="", model="claude-3")
        assert client.validate_config() is False
