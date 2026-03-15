"""OpenAI 客户端实现"""

from typing import Any, Iterator

from openai import OpenAI

from .client import AIClient


class OpenAIClient(AIClient):
    """OpenAI API 客户端"""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4",
    ):
        super().__init__(api_key, base_url, model)
        self._client: OpenAI | None = None

    def _get_client(self) -> OpenAI:
        """获取或创建 OpenAI 客户端"""
        if self._client is None:
            self._client = OpenAI(
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

        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096),
        )

        return response.choices[0].message.content or ""

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> Iterator[str]:
        """发送聊天消息（流式响应）"""
        client = self._get_client()

        stream = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096),
            stream=True,
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content