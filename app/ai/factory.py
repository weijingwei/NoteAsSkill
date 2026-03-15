"""AI 客户端工厂模块

使用抽象工厂模式创建 AI 客户端实例。
支持动态注册新的提供商，符合开闭原则。

设计模式：抽象工厂模式 (Abstract Factory Pattern)
- 将客户端创建逻辑封装在工厂中
- 通过注册机制支持扩展
- 客户端代码只需知道工厂接口

优势：
- 开闭原则：新增提供商无需修改现有代码
- 单一职责：创建逻辑集中管理
- 依赖倒置：客户端依赖抽象接口

使用方式：
    # 创建客户端
    client = AIClientFactory.create("openai", {"api_key": "xxx"})
    
    # 注册新的提供商
    AIClientFactory.register("custom", create_custom_client, {"default": "config"})
    
    # 获取支持的提供商列表
    providers = AIClientFactory.get_supported_providers()
"""
from typing import Callable

from .client import AIClient


ClientFactory = Callable[[dict], AIClient]


class AIClientFactory:
    """AI 客户端工厂
    
    使用注册机制管理不同提供商的客户端创建逻辑。
    支持运行时动态注册新的提供商。
    
    设计模式：抽象工厂模式
    - 将客户端创建逻辑封装在工厂中
    - 通过注册机制支持扩展
    - 客户端代码只需知道工厂接口
    
    Attributes:
        _registry: 提供商名称到工厂函数的映射
        _defaults: 提供商的默认配置
    """
    
    _registry: dict[str, ClientFactory] = {}
    _defaults: dict[str, dict] = {}
    
    @classmethod
    def register(
        cls, 
        provider: str, 
        factory: ClientFactory,
        default_config: dict | None = None
    ) -> None:
        """注册 AI 提供商
        
        Args:
            provider: 提供商名称（如 'openai', 'anthropic'）
            factory: 创建客户端的工厂函数，接收配置字典，返回 AIClient 实例
            default_config: 默认配置，创建客户端时会与用户配置合并
        """
        cls._registry[provider] = factory
        if default_config:
            cls._defaults[provider] = default_config
    
    @classmethod
    def create(cls, provider: str, config: dict | None = None) -> AIClient:
        """创建 AI 客户端
        
        Args:
            provider: 提供商名称
            config: 配置字典（可选，会与默认配置合并）
            
        Returns:
            AI 客户端实例
            
        Raises:
            ValueError: 不支持的提供商
        """
        if provider not in cls._registry:
            raise ValueError(f"Unsupported AI provider: {provider}. "
                           f"Supported providers: {list(cls._registry.keys())}")
        
        final_config = cls._defaults.get(provider, {}).copy()
        if config:
            final_config.update(config)
        
        return cls._registry[provider](final_config)
    
    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """获取支持的提供商列表
        
        Returns:
            已注册的提供商名称列表
        """
        return list(cls._registry.keys())
    
    @classmethod
    def is_provider_supported(cls, provider: str) -> bool:
        """检查提供商是否支持
        
        Args:
            provider: 提供商名称
            
        Returns:
            是否已注册
        """
        return provider in cls._registry
    
    @classmethod
    def unregister(cls, provider: str) -> bool:
        """注销提供商
        
        Args:
            provider: 提供商名称
            
        Returns:
            是否成功注销（如果不存在则返回 False）
        """
        if provider in cls._registry:
            del cls._registry[provider]
            cls._defaults.pop(provider, None)
            return True
        return False


def _create_openai_client(config: dict) -> AIClient:
    """创建 OpenAI 客户端
    
    Args:
        config: 配置字典，包含 api_key, base_url, model 等
        
    Returns:
        OpenAIClient 实例
    """
    from .openai_client import OpenAIClient
    return OpenAIClient(
        api_key=config.get("api_key", ""),
        base_url=config.get("base_url", "https://api.openai.com/v1"),
        model=config.get("model", "gpt-4"),
    )


def _create_anthropic_client(config: dict) -> AIClient:
    """创建 Anthropic 客户端
    
    Args:
        config: 配置字典，包含 api_key, base_url, model 等
        
    Returns:
        AnthropicClient 实例
    """
    from .anthropic_client import AnthropicClient
    return AnthropicClient(
        api_key=config.get("api_key", ""),
        base_url=config.get("base_url", "https://api.anthropic.com"),
        model=config.get("model", "claude-3-opus-20240229"),
    )


def _create_ollama_client(config: dict) -> AIClient:
    """创建 Ollama 客户端
    
    Args:
        config: 配置字典，包含 base_url, model 等
        
    Returns:
        OllamaClient 实例
    """
    from .ollama_client import OllamaClient
    return OllamaClient(
        base_url=config.get("base_url", "http://localhost:11434"),
        model=config.get("model", "llama2"),
    )


def _register_builtin_providers() -> None:
    """注册内置的 AI 提供商
    
    在模块加载时自动调用，注册 OpenAI、Anthropic、Ollama 三个内置提供商。
    """
    AIClientFactory.register(
        "openai",
        _create_openai_client,
        {"base_url": "https://api.openai.com/v1", "model": "gpt-4"}
    )
    
    AIClientFactory.register(
        "anthropic",
        _create_anthropic_client,
        {"base_url": "https://api.anthropic.com", "model": "claude-3-opus-20240229"}
    )
    
    AIClientFactory.register(
        "ollama",
        _create_ollama_client,
        {"base_url": "http://localhost:11434", "model": "llama2"}
    )


_register_builtin_providers()
