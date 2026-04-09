"""AIClient 抽象基类测试"""
import pytest
from app.ai.client import (
    AIClient, Message, ToolCall, ToolResult, ChatResponse, MCPToolSchema, create_client
)


class TestMessage:
    def test_to_dict(self):
        msg = Message(role="user", content="hello")
        assert msg.to_dict() == {"role": "user", "content": "hello"}


class TestToolCall:
    def test_defaults(self):
        tc = ToolCall(id="1", name="test", arguments={"key": "value"})
        assert tc.id == "1"
        assert tc.name == "test"
        assert tc.arguments == {"key": "value"}


class TestToolResult:
    def test_defaults(self):
        tr = ToolResult(tool_call_id="1", name="test", content="result")
        assert tr.is_error is False


class TestChatResponse:
    def test_defaults(self):
        resp = ChatResponse(content="test")
        assert resp.tool_calls is None
        assert resp.finish_reason == "stop"


class TestMCPToolSchema:
    def test_to_dict(self):
        schema = MCPToolSchema(name="test", description="desc", input_schema={"type": "object"})
        d = schema.to_dict()
        assert d["name"] == "test"
        assert d["description"] == "desc"
        assert d["input_schema"] == {"type": "object"}


class TestAIClientAbstract:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            AIClient()

    def test_subclass_must_implement(self):
        class IncompleteClient(AIClient):
            pass

        with pytest.raises(TypeError):
            IncompleteClient()

    def test_complete_subclass(self):
        class CompleteClient(AIClient):
            def chat(self, *args, **kwargs):
                return ChatResponse(content="ok")
            def chat_stream(self, *args, **kwargs):
                yield ChatResponse(content="ok")

        client = CompleteClient(api_key="k", base_url="u", model="m")
        assert client.api_key == "k"
        assert client.base_url == "u"
        assert client.model == "m"

    def test_validate_config(self):
        class CompleteClient(AIClient):
            def chat(self, *args, **kwargs):
                return ChatResponse(content="ok")
            def chat_stream(self, *args, **kwargs):
                yield ChatResponse(content="ok")

        assert CompleteClient(model="m").validate_config() is True
        assert CompleteClient(model="").validate_config() is False

    def test_get_config(self):
        class CompleteClient(AIClient):
            def chat(self, *args, **kwargs):
                return ChatResponse(content="ok")
            def chat_stream(self, *args, **kwargs):
                yield ChatResponse(content="ok")

        client = CompleteClient(api_key="k", base_url="u", model="m")
        cfg = client.get_config()
        assert cfg == {"api_key": "k", "base_url": "u", "model": "m"}

    def test_set_config(self):
        class CompleteClient(AIClient):
            def chat(self, *args, **kwargs):
                return ChatResponse(content="ok")
            def chat_stream(self, *args, **kwargs):
                yield ChatResponse(content="ok")

        client = CompleteClient()
        client.set_config({"api_key": "new", "base_url": "new-url", "model": "new-model"})
        assert client.api_key == "new"
        assert client.base_url == "new-url"
        assert client.model == "new-model"

    def test_list_models_default(self):
        class CompleteClient(AIClient):
            def chat(self, *args, **kwargs):
                return ChatResponse(content="ok")
            def chat_stream(self, *args, **kwargs):
                yield ChatResponse(content="ok")

        assert CompleteClient().list_models() == []

    def test_create_client_compat(self):
        client = create_client("openai", {"api_key": "test", "model": "gpt-4"})
        assert client is not None
        assert client.model == "gpt-4"
