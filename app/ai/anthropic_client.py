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
            # 清理 API Key，移除可能导致 HTTP Header 错误的字符
            clean_api_key = self._clean_api_key(self.api_key)
            self._client = Anthropic(
                api_key=clean_api_key,
                base_url=self.base_url if self.base_url else None,
            )
        return self._client

    def _clean_api_key(self, api_key: str) -> str:
        """清理 API Key，移除非法字符

        HTTP Header 只能包含 ASCII 字符，需要移除或替换非 ASCII 字符
        """
        if not api_key:
            return api_key

        # 移除常见的错误前缀（如 "公司:" 等）
        import re
        # 如果包含冒号，只取冒号后的部分
        if ':' in api_key:
            parts = api_key.split(':', 1)
            if len(parts) == 2:
                # 检查冒号前是否包含非 ASCII 字符
                prefix = parts[0]
                try:
                    prefix.encode('ascii')
                    # 前缀是 ASCII，可能是合法格式（如 "Bearer"）
                    return api_key.strip()
                except UnicodeEncodeError:
                    # 前缀包含非 ASCII 字符，丢弃前缀
                    api_key = parts[1].strip()

        # 确保只保留 ASCII 字符
        try:
            # 尝试编码为 ASCII，如果失败则移除非 ASCII 字符
            return api_key.encode('ascii', errors='ignore').decode('ascii')
        except Exception:
            return api_key.strip()

    def _ensure_utf8_encoding(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        """确保消息编码为 UTF-8"""
        encoded_messages = []
        for msg in messages:
            encoded_msg = {}
            for key, value in msg.items():
                if isinstance(value, str):
                    # 确保字符串是 UTF-8 编码
                    encoded_msg[key] = value.encode('utf-8').decode('utf-8')
                else:
                    encoded_msg[key] = value
            encoded_messages.append(encoded_msg)
        return encoded_messages

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

        # 确保消息编码正确
        encoded_messages = self._ensure_utf8_encoding(messages)

        # 提取 system 消息
        system_message = ""
        chat_messages = []
        for msg in encoded_messages:
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

        # 确保消息编码正确
        encoded_messages = self._ensure_utf8_encoding(messages)

        # 提取 system 消息
        system_message = ""
        chat_messages = []
        for msg in encoded_messages:
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

    def list_models(self) -> list[str]:
        """列出可用的模型

        Anthropic 没有公开的模型列表 API，这里返回已知的模型列表。
        实际可用模型请参考 Anthropic 官方文档。
        """
        return [
            "claude-sonnet-4-20250514",
            "claude-sonnet-4-20250507",
            "claude-3-5-sonnet-20240620",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-5-haiku-20240620",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]
