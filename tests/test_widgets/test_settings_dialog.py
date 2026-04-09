"""Settings Dialog 测试"""
import pytest


class TestSettingsDialogImports:
    """Settings Dialog 模块导入测试"""

    def test_settings_dialog_import(self):
        from app.widgets.settings_dialog import SettingsDialog
        assert SettingsDialog is not None
