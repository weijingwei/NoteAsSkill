"""AI 客户端抽象基类

定义统一的 AI 客户端接口。

设计模式：
- 模板方法模式 (Template Method Pattern): AIClient 基类定义算法骨架
- 适配器模式 (Adapter Pattern): 各具体客户端适配不同 AI 提供商的 API

使用方式：
    # 使用工厂创建客户端（推荐）
    from app.ai.factory import AIClientFactory
    client = AIClientFactory.create("openai", {"api_key": "xxx"})
    
    # 或直接实例化
    from app.ai.openai_client import OpenAIClient
    client = OpenAIClient(api_key="xxx", model="gpt-4")
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
    """AI 客户端抽象基类
    
    定义了所有 AI 客户端的公共接口。
    子类必须实现 chat() 和 chat_stream() 方法。
    
    设计模式：模板方法模式
    - 基类定义算法骨架（validate_config, get_config, set_config）
    - 子类实现具体步骤（chat, chat_stream）
    
    设计模式：适配器模式
    - 将不同 AI 提供商的 API 适配为统一接口
    - 客户端代码无需关心底层实现差异
    """
    
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

    def list_models(self) -> list[str]:
        """列出可用模型

        子类可以重写此方法以提供真实的模型列表。
        默认实现返回空列表。

        Returns:
            可用模型名称列表
        """
        return []

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
    """创建 AI 客户端（兼容旧代码的便捷函数）

    推荐使用 AIClientFactory.create() 代替此函数。
    
    Args:
        provider: 提供商名称（openai, anthropic, ollama）
        config: 配置字典

    Returns:
        AI 客户端实例

    Raises:
        ValueError: 不支持的提供商
    """
    from .factory import AIClientFactory
    return AIClientFactory.create(provider, config)
