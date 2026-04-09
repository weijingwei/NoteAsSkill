"""Ollama Client 测试"""
import pytest
from unittest.mock import patch, MagicMock
from app.ai.ollama_client import OllamaClient


@pytest.fixture
def mock_sys_config():
    """Mock system config to avoid real dependency"""
    with patch("app.ai.ollama_client.get_system_config_instance") as mock:
        sys_config = MagicMock()
        sys_config.api_request_timeout = 30
        sys_config.api_stream_timeout = 60
        sys_config.timeout.return_value = 10
        mock.return_value = sys_config
        yield sys_config


class TestOllamaClient:
    def test_instantiation(self, mock_sys_config):
        client = OllamaClient(model="llama3")
        assert client.model == "llama3"

    def test_default_base_url(self, mock_sys_config):
        client = OllamaClient()
        assert "localhost:11434" in client.base_url

    def test_default_model(self, mock_sys_config):
        client = OllamaClient()
        assert client.model == "llama2"

    def test_validate_config(self, mock_sys_config):
        client = OllamaClient(model="llama3")
        assert client.validate_config() is True

    def test_validate_config_no_model(self, mock_sys_config):
        client = OllamaClient(model="")
        assert client.validate_config() is False

    def test_custom_base_url(self, mock_sys_config):
        client = OllamaClient(base_url="http://my-server:8080")
        assert "my-server:8080" in client.base_url
