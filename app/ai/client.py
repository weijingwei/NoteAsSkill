"""AI 客户端抽象基类

定义统一的 AI 客户端接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass
class Message:
    """消息数据类"""

    role: str  # "user" | "assistant" | "system"
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


class AIClient(ABC):
    """AI 客户端抽象基类"""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        model: str = "",
    ):
        """初始化 AI 客户端

        Args:
            api_key: API 密钥
            base_url: API 基础 URL
            model: 模型名称
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> str:
        """发送聊天消息

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Returns:
            AI 响应内容
        """
        pass

    @abstractmethod
    def chat_stream(
        self,
        messages: list[dict[str, str]],
        **kwargs: Any,
    ) -> Iterator[str]:
        """发送聊天消息（流式响应）

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Yields:
            AI 响应内容片段
        """
        pass

    def validate_config(self) -> bool:
        """验证配置是否有效

        Returns:
            配置是否有效
        """
        return bool(self.model)

    def get_config(self) -> dict[str, str]:
        """获取当前配置

        Returns:
            配置字典
        """
        return {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "model": self.model,
        }

    def set_config(self, config: dict[str, str]) -> None:
        """设置配置

        Args:
            config: 配置字典
        """
        if "api_key" in config:
            self.api_key = config["api_key"]
        if "base_url" in config:
            self.base_url = config["base_url"]
        if "model" in config:
            self.model = config["model"]


def create_client(provider: str, config: dict[str, Any]) -> AIClient:
    """创建 AI 客户端

    Args:
        provider: 提供商名称（openai, anthropic, ollama）
        config: 配置字典

    Returns:
        AI 客户端实例

    Raises:
        ValueError: 不支持的提供商
    """
    # 延迟导入避免循环依赖
    if provider == "openai":
        from .openai_client import OpenAIClient
        return OpenAIClient(
            api_key=config.get("api_key", ""),
            base_url=config.get("base_url", "https://api.openai.com/v1"),
            model=config.get("model", "gpt-4"),
        )
    elif provider == "anthropic":
        from .anthropic_client import AnthropicClient
        return AnthropicClient(
            api_key=config.get("api_key", ""),
            base_url=config.get("base_url", "https://api.anthropic.com"),
            model=config.get("model", "claude-3-opus-20240229"),
        )
    elif provider == "ollama":
        from .ollama_client import OllamaClient
        return OllamaClient(
            base_url=config.get("base_url", "http://localhost:11434"),
            model=config.get("model", "llama2"),
        )
    else:
        raise ValueError(f"Unsupported AI provider: {provider}")