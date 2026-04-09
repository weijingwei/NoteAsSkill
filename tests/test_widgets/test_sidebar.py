"""Sidebar 组件测试"""
import pytest


class TestSidebarImports:
    """Sidebar 模块导入测试"""

    def test_sidebar_import(self):
        from app.widgets.sidebar import Sidebar
        assert Sidebar is not None

    def test_new_note_dialog_import(self):
        from app.widgets.sidebar import NewNoteDialog
        assert NewNoteDialog is not None

    def test_draggable_list_widget_import(self):
        from app.widgets.sidebar import DraggableListWidget
        assert DraggableListWidget is not None

    def test_dropable_tree_widget_import(self):
        from app.widgets.sidebar import DropableTreeWidget
        assert DropableTreeWidget is not None


class TestNewNoteDialog:
    """NewNoteDialog 基础测试"""

    def test_dialog_creation(self, qtbot):
        from app.widgets.sidebar import NewNoteDialog
        dialog = NewNoteDialog()
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "新建笔记"
        assert dialog.note_title == ""

    def test_dialog_with_folder(self, qtbot):
        from app.widgets.sidebar import NewNoteDialog
        dialog = NewNoteDialog(folder_name="test-folder")
        qtbot.addWidget(dialog)
        assert dialog.folder_name == "test-folder"

    def test_empty_title_enables_confirm(self, qtbot):
        """空标题时确认按钮保持启用（验证由 _on_confirm 处理空输入）"""
        from app.widgets.sidebar import NewNoteDialog
        dialog = NewNoteDialog()
        qtbot.addWidget(dialog)

        # 空标题时按钮仍为启用状态，点击时会阻止提交
        dialog.title_input.setText("")
        assert dialog.confirm_btn.isEnabled()
        assert dialog.error_label.isHidden()

    def test_valid_title_enables_confirm(self, qtbot):
        from app.widgets.sidebar import NewNoteDialog
        dialog = NewNoteDialog()
        qtbot.addWidget(dialog)

        # 有效标题时应启用确认按钮
        dialog.title_input.setText("Valid Title")
        assert dialog.confirm_btn.isEnabled()
        assert dialog.error_label.isHidden()


class TestDraggableListWidget:
    """DraggableListWidget 基础测试"""

    def test_drag_enabled(self, qtbot):
        from app.widgets.sidebar import DraggableListWidget
        widget = DraggableListWidget()
        qtbot.addWidget(widget)
        assert widget.dragEnabled()


class TestDropableTreeWidget:
    """DropableTreeWidget 基础测试"""

    def test_drop_enabled(self, qtbot):
        from app.widgets.sidebar import DropableTreeWidget
        widget = DropableTreeWidget()
        qtbot.addWidget(widget)
        assert widget.acceptDrops()
