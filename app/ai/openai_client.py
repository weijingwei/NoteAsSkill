"""OpenAI 客户端实现"""

import os
import sys
from typing import Any, Iterator

import httpx
from openai import OpenAI

from .client import AIClient

# 设置环境变量确保 UTF-8 编码
os.environ['PYTHONIOENCODING'] = 'utf-8'


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
            # 清理 API Key，移除可能导致 HTTP Header 错误的字符
            clean_api_key = self._clean_api_key(self.api_key)
            # 创建自定义 httpx 客户端，确保编码正确
            http_client = httpx.Client(
                timeout=60.0,
                follow_redirects=True,
            )
            self._client = OpenAI(
                api_key=clean_api_key,
                base_url=self.base_url if self.base_url else None,
                http_client=http_client,
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
        import json
        # 使用 JSON 序列化/反序列化来确保所有字符串都是 UTF-8
        try:
            json_str = json.dumps(messages, ensure_ascii=False)
            return json.loads(json_str)
        except Exception:
            # 如果 JSON 方法失败，使用原始方法
            encoded_messages = []
            for msg in messages:
                encoded_msg = {}
                for key, value in msg.items():
                    if isinstance(value, str):
                        try:
                            encoded_msg[key] = value.encode('utf-8').decode('utf-8')
                        except UnicodeEncodeError:
                            encoded_msg[key] = value.encode('utf-8', errors='replace').decode('utf-8')
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

        response = client.chat.completions.create(
            model=self.model,
            messages=encoded_messages,
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

        # 确保消息编码正确
        encoded_messages = self._ensure_utf8_encoding(messages)

        try:
            stream = client.chat.completions.create(
                model=self.model,
                messages=encoded_messages,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 4096),
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            # 包装异常，添加更多信息
            raise Exception(f"API调用失败: {type(e).__name__}: {repr(e)}") from e