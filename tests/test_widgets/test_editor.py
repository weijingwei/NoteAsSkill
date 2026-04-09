"""Editor 组件测试"""
import pytest


class TestEditorImports:
    """Editor 模块导入测试"""

    def test_editor_import(self):
        from app.widgets.editor import Editor
        assert Editor is not None
