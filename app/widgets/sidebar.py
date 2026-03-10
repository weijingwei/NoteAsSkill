"""左侧边栏模块

显示笔记列表、文件夹和标签。
"""

from typing import Any

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.note_manager import Note, get_note_manager


class Sidebar(QWidget):
    """左侧边栏"""

    note_selected = Signal(Note)
    note_created = Signal(Note)
    note_deleted = Signal(str)

    def __init__(self):
        super().__init__()

        self._init_ui()
        self._connect_signals()
        self.refresh()

    def _init_ui(self) -> None:
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索笔记...")
        layout.addWidget(self.search_input)

        # 笔记列表
        self.note_list = QListWidget()
        layout.addWidget(self.note_list, 1)

        # 标签筛选
        tags_label = QLabel("标签筛选")
        layout.addWidget(tags_label)

        self.tag_list = QListWidget()
        self.tag_list.setMaximumHeight(120)
        layout.addWidget(self.tag_list)

        # 新建按钮
        self.new_button = QPushButton("新建笔记")
        layout.addWidget(self.new_button)

    def _connect_signals(self) -> None:
        """连接信号"""
        self.search_input.textChanged.connect(self._on_search)
        self.note_list.itemClicked.connect(self._on_note_clicked)
        self.note_list.itemDoubleClicked.connect(self._on_note_double_clicked)
        self.tag_list.itemClicked.connect(self._on_tag_clicked)
        self.new_button.clicked.connect(self.create_new_note)

        # 右键菜单
        self.note_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.note_list.customContextMenuRequested.connect(self._show_note_context_menu)

    def refresh(self) -> None:
        """刷新列表"""
        self._load_notes()
        self._load_tags()

    def _load_notes(self, filter_tag: str | None = None) -> None:
        """加载笔记列表"""
        self.note_list.clear()

        note_manager = get_note_manager()

        if filter_tag:
            notes = note_manager.get_notes_by_tag(filter_tag)
        else:
            notes = note_manager.list_notes()

        for note in notes:
            item = QListWidgetItem(note.title)
            item.setData(Qt.ItemDataRole.UserRole, note.id)
            item.setToolTip(f"更新: {note.updated_at.strftime('%Y-%m-%d %H:%M')}")

            # 显示标签
            if note.tags:
                item.setText(f"{note.title} {' '.join(f'#{t}' for t in note.tags)}")

            self.note_list.addItem(item)

    def _load_tags(self) -> None:
        """加载标签列表"""
        self.tag_list.clear()

        note_manager = get_note_manager()
        tags = note_manager.list_tags()

        # 添加"全部"选项
        all_item = QListWidgetItem("全部")
        all_item.setData(Qt.ItemDataRole.UserRole, "")
        self.tag_list.addItem(all_item)

        for tag in sorted(tags):
            item = QListWidgetItem(f"#{tag}")
            item.setData(Qt.ItemDataRole.UserRole, tag)
            self.tag_list.addItem(item)

    @Slot(str)
    def _on_search(self, text: str) -> None:
        """搜索笔记"""
        self.note_list.clear()

        if not text:
            self._load_notes()
            return

        note_manager = get_note_manager()
        notes = note_manager.search_notes(text)

        for note in notes:
            item = QListWidgetItem(note.title)
            item.setData(Qt.ItemDataRole.UserRole, note.id)
            self.note_list.addItem(item)

    @Slot(QListWidgetItem)
    def _on_note_clicked(self, item: QListWidgetItem) -> None:
        """笔记被点击"""
        note_id = item.data(Qt.ItemDataRole.UserRole)
        note_manager = get_note_manager()
        note = note_manager.get_note(note_id)

        if note:
            self.note_selected.emit(note)

    @Slot(QListWidgetItem)
    def _on_note_double_clicked(self, item: QListWidgetItem) -> None:
        """笔记被双击"""
        self._on_note_clicked(item)

    @Slot(QListWidgetItem)
    def _on_tag_clicked(self, item: QListWidgetItem) -> None:
        """标签被点击"""
        tag = item.data(Qt.ItemDataRole.UserRole)
        self._load_notes(tag if tag else None)

    @Slot()
    def create_new_note(self) -> None:
        """创建新笔记"""
        title, ok = QInputDialog.getText(
            self,
            "新建笔记",
            "请输入笔记标题:",
        )

        if ok and title:
            note_manager = get_note_manager()
            note = note_manager.create_note(title)

            self.refresh()
            self.note_created.emit(note)

    def _show_note_context_menu(self, pos: Any) -> None:
        """显示笔记右键菜单"""
        item = self.note_list.itemAt(pos)
        if not item:
            return

        note_id = item.data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)

        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self._delete_note(note_id))
        menu.addAction(delete_action)

        menu.exec(self.note_list.mapToGlobal(pos))

    def _delete_note(self, note_id: str) -> None:
        """删除笔记"""
        note_manager = get_note_manager()
        note = note_manager.get_note(note_id)

        if note:
            note_manager.delete_note(note_id)
            self.refresh()
            self.note_deleted.emit(note_id)