"""Ollama 客户端实现"""

import json
from typing import Any, Iterator

import requests

from .client import AIClient


class OllamaClient(AIClient):
    """Ollama 本地 API 客户端"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama2",
        api_key: str = "",  # Ollama 不需要 API key，保留参数以统一接口
    ):
        super().__init__(api_key, base_url, model)

    def validate_config(self) -> bool:
        """验证配置是否有效"""
        return bool(self.base_url and self.model)

    def _get_api_url(self, endpoint: str) -> str:
        """获取完整 API URL"""
        base = self.base_url.rstrip("/")
        return f"{base}/api/{endpoint}"

    def chat(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """发送聊天消息"""
        url = self._get_api_url("chat")

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 4096),
            },
        }

        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()

        data = response.json()
        return data.get("message", {}).get("content", "")

    def chat_stream(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> Iterator[str]:
        """发送聊天消息（流式响应）"""
        url = self._get_api_url("chat")

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", 4096),
            },
        }

        response = requests.post(url, json=payload, stream=True, timeout=120)
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                if "message" in data and "content" in data["message"]:
                    content = data["message"]["content"]
                    if content:
                        yield content

    def list_models(self) -> list[str]:
        """列出可用的模型"""
        url = self._get_api_url("tags")

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception:
            return []

    def pull_model(self, model_name: str) -> bool:
        """拉取模型"""
        url = self._get_api_url("pull")

        try:
            response = requests.post(
                url,
                json={"name": model_name, "stream": False},
                timeout=300,
            )
            response.raise_for_status()
            return True
        except Exception:
            return False