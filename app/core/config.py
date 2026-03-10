"""配置管理模块

负责加载、保存和管理应用配置，支持跨平台路径处理。
"""

from pathlib import Path
from typing import Any

import yaml


class Config:
    """应用配置管理类"""

    DEFAULT_CONFIG = {
        "app": {
            "theme": "light",
            "auto_save": True,
            "auto_save_interval": 30,
            "auto_generate_skill": True,  # 自动生成 SKILL.md
        },
        "ai": {
            "provider": "openai",
            "openai": {
                "base_url": "https://api.openai.com/v1",
                "api_key": "",
                "model": "gpt-4",
            },
            "anthropic": {
                "base_url": "https://api.anthropic.com",
                "api_key": "",
                "model": "claude-3-opus-20240229",
            },
            "ollama": {
                "base_url": "http://localhost:11434",
                "model": "llama2",
            },
        },
        "editor": {
            "font_size": 14,
            "preview_mode": "split",
        },
    }

    def __init__(self, config_path: Path | None = None):
        """初始化配置管理器

        Args:
            config_path: 配置文件路径，默认为 notebook/.config.yaml
        """
        if config_path is None:
            # 使用项目目录下的 notebook/.config.yaml
            self.config_path = Path(__file__).parent.parent.parent / "notebook" / ".config.yaml"
        else:
            self.config_path = Path(config_path)

        self._config: dict[str, Any] = {}
        self.load()

    def load(self) -> dict[str, Any]:
        """加载配置文件

        Returns:
            配置字典
        """
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = self.DEFAULT_CONFIG.copy()
            self.save()

        return self._config

    def save(self) -> None:
        """保存配置到文件"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值

        支持点分隔的嵌套键，如 "ai.provider"

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """设置配置值

        支持点分隔的嵌套键，如 "ai.provider"

        Args:
            key: 配置键
            value: 配置值
        """
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    @property
    def ai_provider(self) -> str:
        """获取当前 AI 提供商"""
        return self.get("ai.provider", "openai")

    @ai_provider.setter
    def ai_provider(self, provider: str) -> None:
        """设置 AI 提供商"""
        self.set("ai.provider", provider)

    def get_ai_config(self, provider: str | None = None) -> dict[str, Any]:
        """获取指定 AI 提供商的配置

        Args:
            provider: AI 提供商名称，默认使用当前配置的提供商

        Returns:
            AI 配置字典
        """
        if provider is None:
            provider = self.ai_provider
        return self.get(f"ai.{provider}", {})

    def set_ai_config(self, provider: str, config: dict[str, Any]) -> None:
        """设置 AI 提供商配置

        Args:
            provider: AI 提供商名称
            config: 配置字典
        """
        self.set(f"ai.{provider}", config)

    @property
    def auto_save(self) -> bool:
        """是否启用自动保存"""
        return self.get("app.auto_save", True)

    @auto_save.setter
    def auto_save(self, value: bool) -> None:
        self.set("app.auto_save", value)

    @property
    def auto_save_interval(self) -> int:
        """自动保存间隔（秒）"""
        return self.get("app.auto_save_interval", 30)

    @auto_save_interval.setter
    def auto_save_interval(self, value: int) -> None:
        self.set("app.auto_save_interval", value)

    @property
    def auto_generate_skill(self) -> bool:
        """是否自动生成 SKILL.md"""
        return self.get("app.auto_generate_skill", True)

    @auto_generate_skill.setter
    def auto_generate_skill(self, value: bool) -> None:
        self.set("app.auto_generate_skill", value)

    @property
    def theme(self) -> str:
        """获取主题"""
        return self.get("app.theme", "light")

    @theme.setter
    def theme(self, value: str) -> None:
        self.set("app.theme", value)

    @property
    def editor_font_size(self) -> int:
        """编辑器字体大小"""
        return self.get("editor.font_size", 14)

    @editor_font_size.setter
    def editor_font_size(self, value: int) -> None:
        self.set("editor.font_size", value)

    @property
    def preview_mode(self) -> str:
        """预览模式"""
        return self.get("editor.preview_mode", "split")

    @preview_mode.setter
    def preview_mode(self, value: str) -> None:
        self.set("editor.preview_mode", value)


# 全局配置实例
_config: Config | None = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reload_config() -> Config:
    """重新加载配置"""
    global _config
    _config = Config()
    return _config