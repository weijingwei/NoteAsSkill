"""OpenAI Client 测试"""
import pytest
from app.ai.openai_client import OpenAIClient


class TestOpenAIClient:
    def test_instantiation(self):
        client = OpenAIClient(api_key="test", model="gpt-4")
        assert client.model == "gpt-4"
        assert "openai" in client.base_url

    def test_default_base_url(self):
        client = OpenAIClient(api_key="test")
        assert "api.openai.com" in client.base_url

    def test_validate_config_with_model_and_key(self):
        client = OpenAIClient(api_key="test", model="gpt-4")
        assert client.validate_config() is True

    def test_validate_config_without_model(self):
        client = OpenAIClient(api_key="test", model="")
        assert client.validate_config() is False

    def test_validate_config_without_api_key(self):
        client = OpenAIClient(api_key="", model="gpt-4")
        assert client.validate_config() is False
