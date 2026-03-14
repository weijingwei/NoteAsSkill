"""Anthropic 客户端实现"""

from typing import Any, Iterator

from anthropic import Anthropic

from .client import AIClient


class AnthropicClient(AIClient):
    """Anthropic API 客户端"""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.anthropic.com",
        model: str = "claude-3-opus-20240229",
    ):
        super().__init__(api_key, base_url, model)
        self._client: Anthropic | None = None

    def _get_client(self) -> Anthropic:
        """获取或创建 Anthropic 客户端"""
        if self._client is None:
            self._client = Anthropic(
                api_key=self.api_key,
                base_url=self.base_url if self.base_url else None,
            )
        return self._client

    def validate_config(self) -> bool:
        """验证配置是否有效"""
        return bool(self.api_key and self.model)

    def chat(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """发送聊天消息"""
        client = self._get_client()

        # 提取 system 消息
        system_message = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                chat_messages.append(msg)

        response = client.messages.create(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", 4096),
            system=system_message if system_message else None,
            messages=chat_messages,
        )

        # 处理响应内容，兼容 ThinkingBlock 等不同类型
        if response.content:
            for block in response.content:
                # 跳过 ThinkingBlock，只返回文本内容
                if hasattr(block, 'text'):
                    return block.text
                # 处理其他可能的类型
                if hasattr(block, 'type') and block.type == 'text':
                    return getattr(block, 'text', '')
        return ""

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> Iterator[str]:
        """发送聊天消息（流式响应）"""
        client = self._get_client()

        # 提取 system 消息
        system_message = ""
        chat_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                chat_messages.append(msg)

        with client.messages.stream(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", 4096),
            system=system_message if system_message else None,
            messages=chat_messages,
        ) as stream:
            for text in stream.text_stream:
                yield text