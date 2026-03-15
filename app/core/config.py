"""配置管理模块

负责加载、保存和管理应用配置，支持跨平台路径处理。

设计模式：单例模式 (Singleton Pattern)
- 使用 SingletonMeta 元类确保全局只有一个配置实例
- 线程安全的单例实现
- 支持测试时清除实例

使用方式：
    # 获取配置实例
    config = get_config()
    
    # 访问配置
    provider = config.ai_provider
    theme = config.theme
    
    # 修改配置
    config.theme = "dark"
    config.save()
"""
from pathlib import Path
from typing import Any

import yaml

from .singleton import SingletonMeta


def get_system_config() -> dict[str, Any]:
    """获取系统配置（从项目根目录 config.yaml）

    Returns:
        系统配置字典
    """
    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def get_version() -> str:
    """获取应用版本号

    Returns:
        版本号字符串，如 "v0.2.62"
    """
    system_config = get_system_config()
    return system_config.get("version", "v0.0.0")


class Config(metaclass=SingletonMeta):
    """应用配置管理类
    
    使用单例模式确保全局只有一个配置实例。
    支持嵌套配置访问、自动保存等功能。
    
    设计模式：单例模式
    - SingletonMeta 元类确保线程安全的单例
    - 全局访问点：get_config() 函数
    - 支持测试时清除实例：SingletonMeta.clear_instance(Config)
    """

    DEFAULT_CONFIG = {
        "app": {
            "theme": "light",
            "auto_save": True,
            "auto_save_interval": 30,
            "auto_generate_skill": True,
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
        "folder_skill": {
            "enabled": True,
            "auto_update": True,
            "update_delay": 30,
            "generation_mode": "hybrid",
        },
        "git": {
            "enabled": False,
            "remote_url": "",
            "branch": "main",
            "auto_sync": False,
            "commit_message": "更新笔记",
        },
        "mcp": {
            "enabled": False,
            "servers": {},
        },
    }

    def __init__(self, config_path: Path | None = None):
        """初始化配置管理器

        Args:
            config_path: 配置文件路径，默认为 notebook/.config.yaml
        """
        if config_path is None:
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

    @property
    def folder_skill_enabled(self) -> bool:
        """是否启用文件夹 SKILL"""
        return self.get("folder_skill.enabled", True)

    @folder_skill_enabled.setter
    def folder_skill_enabled(self, value: bool) -> None:
        self.set("folder_skill.enabled", value)

    @property
    def folder_skill_auto_update(self) -> bool:
        """是否自动更新文件夹 SKILL"""
        return self.get("folder_skill.auto_update", True)

    @folder_skill_auto_update.setter
    def folder_skill_auto_update(self, value: bool) -> None:
        self.set("folder_skill.auto_update", value)

    @property
    def folder_skill_update_delay(self) -> int:
        """文件夹 SKILL 延迟更新时间（秒）"""
        return self.get("folder_skill.update_delay", 30)

    @folder_skill_update_delay.setter
    def folder_skill_update_delay(self, value: int) -> None:
        self.set("folder_skill.update_delay", value)

    @property
    def folder_skill_generation_mode(self) -> str:
        """文件夹 SKILL 生成模式：simple | ai | hybrid"""
        return self.get("folder_skill.generation_mode", "hybrid")

    @folder_skill_generation_mode.setter
    def folder_skill_generation_mode(self, value: str) -> None:
        self.set("folder_skill.generation_mode", value)

    @property
    def git_enabled(self) -> bool:
        """是否启用 git 同步"""
        return self.get("git.enabled", False)

    @git_enabled.setter
    def git_enabled(self, value: bool) -> None:
        self.set("git.enabled", value)

    @property
    def git_remote_url(self) -> str:
        """git 远程仓库地址"""
        return self.get("git.remote_url", "")

    @git_remote_url.setter
    def git_remote_url(self, value: str) -> None:
        self.set("git.remote_url", value)

    @property
    def git_branch(self) -> str:
        """git 分支名称"""
        return self.get("git.branch", "main")

    @git_branch.setter
    def git_branch(self, value: str) -> None:
        self.set("git.branch", value)

    @property
    def git_auto_sync(self) -> bool:
        """是否自动同步"""
        return self.get("git.auto_sync", False)

    @git_auto_sync.setter
    def git_auto_sync(self, value: bool) -> None:
        self.set("git.auto_sync", value)

    @property
    def git_commit_message(self) -> str:
        """默认提交信息"""
        return self.get("git.commit_message", "更新笔记")

    @git_commit_message.setter
    def git_commit_message(self, value: str) -> None:
        self.set("git.commit_message", value)

    @property
    def mcp_enabled(self) -> bool:
        """是否启用 MCP"""
        return self.get("mcp.enabled", False)

    @mcp_enabled.setter
    def mcp_enabled(self, value: bool) -> None:
        self.set("mcp.enabled", value)

    @property
    def mcp_servers(self) -> dict[str, dict]:
        """MCP 服务器配置"""
        return self.get("mcp.servers", {})

    @mcp_servers.setter
    def mcp_servers(self, value: dict[str, dict]) -> None:
        self.set("mcp.servers", value)

    def get_mcp_server(self, name: str) -> dict | None:
        """获取指定 MCP 服务器配置"""
        servers = self.mcp_servers
        return servers.get(name)

    def set_mcp_server(self, name: str, config: dict) -> None:
        """设置 MCP 服务器配置"""
        servers = self.mcp_servers.copy()
        servers[name] = config
        self.mcp_servers = servers

    def remove_mcp_server(self, name: str) -> bool:
        """删除 MCP 服务器配置"""
        servers = self.mcp_servers
        if name in servers:
            del servers[name]
            self.mcp_servers = servers
            return True
        return False


def get_config() -> Config:
    """获取全局配置实例
    
    使用单例模式，返回唯一的配置实例。
    
    Returns:
        Config 实例
    """
    return Config()


def reload_config() -> Config:
    """重新加载配置
    
    清除现有实例并创建新的配置实例。
    
    Returns:
        新的 Config 实例
    """
    SingletonMeta.clear_instance(Config)
    return Config()
