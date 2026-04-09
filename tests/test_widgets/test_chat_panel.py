"""Chat Panel 组件测试"""
import pytest


class TestChatPanelImports:
    """Chat Panel 模块导入测试"""

    def test_chat_panel_import(self):
        from app.widgets.chat_panel import ChatPanel
        assert ChatPanel is not None
