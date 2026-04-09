"""AIClientFactory 测试"""
import pytest
from app.ai.factory import AIClientFactory
from app.ai.client import AIClient


class TestAIClientFactory:
    def test_builtin_providers(self):
        providers = AIClientFactory.get_supported_providers()
        assert "openai" in providers
        assert "anthropic" in providers
        assert "ollama" in providers

    def test_create_openai_client(self):
        client = AIClientFactory.create("openai", {"api_key": "test", "model": "gpt-4"})
        assert client.model == "gpt-4"
        assert "openai" in client.base_url

    def test_create_anthropic_client(self):
        client = AIClientFactory.create("anthropic", {"api_key": "test", "model": "claude-3"})
        assert client.model == "claude-3"
        assert "anthropic" in client.base_url

    def test_create_ollama_client(self):
        client = AIClientFactory.create("ollama", {"model": "llama3"})
        assert client.model == "llama3"
        assert "localhost" in client.base_url

    def test_invalid_provider(self):
        with pytest.raises(ValueError, match="Unsupported"):
            AIClientFactory.create("invalid", {})

    def test_custom_registration(self):
        class TestClient(AIClient):
            def chat(self, *args, **kwargs):
                pass
            def chat_stream(self, *args, **kwargs):
                yield "test"

        AIClientFactory.register("test", lambda cfg: TestClient(), {"model": "default"})
        assert "test" in AIClientFactory.get_supported_providers()

        client = AIClientFactory.create("test", {})
        assert isinstance(client, TestClient)

        AIClientFactory.unregister("test")
        assert "test" not in AIClientFactory.get_supported_providers()

    def test_is_provider_supported(self):
        assert AIClientFactory.is_provider_supported("openai") is True
        assert AIClientFactory.is_provider_supported("invalid") is False

    def test_unregister_nonexistent(self):
        assert AIClientFactory.unregister("nonexistent") is False
