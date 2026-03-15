"""系统配置访问模块

提供对 config.yaml 中系统配置的便捷访问。
"""

from typing import Any

from app.core.config import get_system_config


class SystemConfig:
    """系统配置访问类"""

    _instance: "SystemConfig | None" = None
    _config: dict[str, Any] = {}

    def __new__(cls) -> "SystemConfig":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self) -> None:
        """加载系统配置"""
        self._config = get_system_config()

    def reload(self) -> None:
        """重新加载配置"""
        self._load()

    @property
    def version(self) -> str:
        """应用版本号"""
        return self._config.get("version", "v0.0.0")

    @property
    def app_name(self) -> str:
        """应用名称"""
        return self._config.get("app", {}).get("name", "NoteAsSkill")

    @property
    def debug(self) -> bool:
        """调试模式"""
        return self._config.get("app", {}).get("debug", False)

    # UI 配置
    @property
    def ui(self) -> dict[str, Any]:
        """UI 配置"""
        return self._config.get("ui", {})

    @property
    def window(self) -> dict[str, Any]:
        """窗口配置"""
        return self.ui.get("window", {})

    @property
    def min_window_width(self) -> int:
        """最小窗口宽度"""
        return self.window.get("min_width", 1200)

    @property
    def min_window_height(self) -> int:
        """最小窗口高度"""
        return self.window.get("min_height", 800)

    @property
    def sidebar_width(self) -> int:
        """侧边栏宽度"""
        return self.window.get("sidebar_width", 280)

    @property
    def colors(self) -> dict[str, str]:
        """颜色配置"""
        return self.ui.get("colors", {})

    def color(self, name: str, default: str = "#000000") -> str:
        """获取颜色值

        Args:
            name: 颜色名称
            default: 默认值

        Returns:
            颜色值（如 "#D4A574"）
        """
        return self.colors.get(name, default)

    @property
    def fonts(self) -> dict[str, int]:
        """字体配置"""
        return self.ui.get("fonts", {})

    def font_size(self, name: str, default: int = 14) -> int:
        """获取字体大小

        Args:
            name: 字体大小名称（如 "small", "normal", "medium", "large"）
            default: 默认值

        Returns:
            字体大小
        """
        return self.fonts.get(f"size_{name}", default)

    @property
    def buttons(self) -> dict[str, int]:
        """按钮配置"""
        return self.ui.get("buttons", {})

    @property
    def icon_size(self) -> int:
        """图标大小"""
        return self.buttons.get("icon_size", 24)

    @property
    def icon_size_small(self) -> int:
        """小图标大小"""
        return self.buttons.get("icon_size_small", 20)

    @property
    def border_radius(self) -> int:
        """边框圆角"""
        return self.buttons.get("border_radius", 8)

    # 超时配置
    @property
    def timeouts(self) -> dict[str, int]:
        """超时配置"""
        return self._config.get("timeouts", {})

    def timeout(self, name: str, default: int = 30) -> int:
        """获取超时时间

        Args:
            name: 超时名称
            default: 默认值（秒）

        Returns:
            超时时间（秒）
        """
        return self.timeouts.get(name, default)

    @property
    def mcp_connection_timeout(self) -> int:
        """MCP 连接超时"""
        return self.timeout("mcp_connection", 15)

    @property
    def mcp_shutdown_timeout(self) -> int:
        """MCP 关闭超时"""
        return self.timeout("mcp_shutdown", 5)

    @property
    def api_request_timeout(self) -> int:
        """API 请求超时"""
        return self.timeout("api_request", 120)

    @property
    def api_stream_timeout(self) -> int:
        """API 流式请求超时"""
        return self.timeout("api_stream", 300)

    # API 配置
    @property
    def api(self) -> dict[str, Any]:
        """API 配置"""
        return self._config.get("api", {})

    def get_api_config(self, provider: str) -> dict[str, Any]:
        """获取指定提供商的 API 配置

        Args:
            provider: 提供商名称（openai, anthropic, ollama）

        Returns:
            API 配置字典
        """
        return self.api.get(provider, {})

    # Editor 配置
    @property
    def editor(self) -> dict[str, Any]:
        """编辑器配置"""
        return self._config.get("editor", {})

    @property
    def default_font_size(self) -> int:
        """默认字体大小"""
        return self.editor.get("default_font_size", 14)

    # Git 配置
    @property
    def git(self) -> dict[str, Any]:
        """Git 配置"""
        return self._config.get("git", {})

    @property
    def default_git_branch(self) -> str:
        """默认 Git 分支"""
        return self.git.get("default_branch", "main")

    @property
    def default_commit_message(self) -> str:
        """默认提交信息"""
        return self.git.get("default_commit_message", "更新笔记")

    # MCP 配置
    @property
    def mcp(self) -> dict[str, Any]:
        """MCP 配置"""
        return self._config.get("mcp", {})

    @property
    def mcp_default_timeout(self) -> int:
        """MCP 默认超时"""
        return self.mcp.get("default_timeout", 10)


# 全局实例
_system_config: SystemConfig | None = None


def get_system_config_instance() -> SystemConfig:
    """获取系统配置实例"""
    global _system_config
    if _system_config is None:
        _system_config = SystemConfig()
    return _system_config
