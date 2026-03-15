"""AI 配置默认值模块

统一管理 AI 提供商的默认配置，避免配置值在多处重复定义。
"""

from typing import Any


class AIDefaults:
    """AI 提供商默认配置"""

    OPENAI: dict[str, Any] = {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4",
        "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
    }

    ANTHROPIC: dict[str, Any] = {
        "base_url": "https://api.anthropic.com",
        "default_model": "claude-3-opus-20240229",
        "models": [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ],
    }

    OLLAMA: dict[str, Any] = {
        "base_url": "http://localhost:11434",
        "default_model": "llama2",
        "models": [],
    }

    @classmethod
    def get_base_url(cls, provider: str) -> str:
        """获取指定提供商的默认 base URL

        Args:
            provider: 提供商名称

        Returns:
            默认 base URL
        """
        defaults = cls.get_defaults(provider)
        return defaults.get("base_url", "")

    @classmethod
    def get_default_model(cls, provider: str) -> str:
        """获取指定提供商的默认模型

        Args:
            provider: 提供商名称

        Returns:
            默认模型名称
        """
        defaults = cls.get_defaults(provider)
        return defaults.get("default_model", "")

    @classmethod
    def get_models(cls, provider: str) -> list[str]:
        """获取指定提供商的可用模型列表

        Args:
            provider: 提供商名称

        Returns:
            模型名称列表
        """
        defaults = cls.get_defaults(provider)
        return defaults.get("models", [])

    @classmethod
    def get_defaults(cls, provider: str) -> dict[str, Any]:
        """获取指定提供商的默认配置

        Args:
            provider: 提供商名称

        Returns:
            默认配置字典
        """
        provider_upper = provider.upper()
        if hasattr(cls, provider_upper):
            return getattr(cls, provider_upper).copy()
        return {}

    @classmethod
    def all_providers(cls) -> list[str]:
        """获取所有支持的提供商列表

        Returns:
            提供商名称列表
        """
        return ["openai", "anthropic", "ollama"]
