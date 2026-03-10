"""左侧边栏模块

显示笔记列表、文件夹和标签。
支持嵌套文件夹结构，体现 Skills 的嵌套和渐进式披露特性。
支持拖拽笔记到文件夹。
"""

from typing import Any

from PySide6.QtCore import Qt, Signal, Slot, QMimeData, QRect
from PySide6.QtGui import QAction, QDrag, QPainter, QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
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

from ..core.note_manager import Note, Folder, get_note_manager


class DraggableListWidget(QListWidget):
    """支持拖拽的列表控件"""

    note_dragged = Signal(str, str)  # (note_id, target_folder)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setDragDropMode(QListWidget.DragDropMode.DragOnly)
        self._drag_item: QListWidgetItem | None = None

    def startDrag(self, supportedActions):
        """开始拖拽"""
        item = self.currentItem()
        if item is None:
            return

        self._drag_item = item

        # 创建拖拽数据
        mime_data = QMimeData()
        note_id = item.data(Qt.ItemDataRole.UserRole)
        mime_data.setText(f"note:{note_id}")
        mime_data.setData("application/x-note-id", note_id.encode())

        # 创建拖拽对象
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.MoveAction)


class DropableTreeWidget(QTreeWidget):
    """支持放置的树形控件"""

    note_dropped = Signal(str, str)  # (note_id, target_folder)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(False)
        self.setDropIndicatorShown(True)
        self._drag_over_item: QTreeWidgetItem | None = None

    def drawBranches(self, painter: QPainter, rect: QRect, item: QTreeWidgetItem) -> None:
        """自定义绘制展开/收起按钮，使用简单的+/-"""
        # 检查是否有子项
        if item.childCount() == 0:
            return

        # 计算按钮位置
        button_size = 12
        button_rect = QRect(
            rect.left() + 2,
            rect.top() + (rect.height() - button_size) // 2,
            button_size,
            button_size
        )

        # 设置绘制样式
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制背景圆
        painter.setBrush(QColor("#FDF6ED"))
        painter.setPen(QColor("#D4A574"))
        painter.drawEllipse(button_rect)

        # 绘制+或-
        painter.setPen(QColor("#8B5A2B"))
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)

        if item.isExpanded():
            # 展开状态，绘制-
            painter.drawText(button_rect, Qt.AlignmentFlag.AlignCenter, "-")
        else:
            # 收起状态，绘制+
            painter.drawText(button_rect, Qt.AlignmentFlag.AlignCenter, "+")

        painter.restore()

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasFormat("application/x-note-id"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """拖拽移动事件"""
        if event.mimeData().hasFormat("application/x-note-id"):
            # 获取鼠标位置的项
            item = self.itemAt(event.pos())
            if item:
                self._drag_over_item = item
                self.setCurrentItem(item)
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        """拖拽离开事件"""
        self._drag_over_item = None

    def dropEvent(self, event):
        """放置事件"""
        if event.mimeData().hasFormat("application/x-note-id"):
            note_id = bytes(event.mimeData().data("application/x-note-id")).decode()

            # 获取目标文件夹
            item = self.itemAt(event.pos())
            if item:
                folder_name = item.data(0, Qt.ItemDataRole.UserRole)
                # folder_name 为空字符串表示"全部笔记"，移动到根目录
                self.note_dropped.emit(note_id, folder_name)

            event.acceptProposedAction()
        else:
            event.ignore()


class Sidebar(QWidget):
    """左侧边栏

    体现 Skills 的嵌套和渐进式披露特性：
    - 文件夹可嵌套（子技能）
    - 树形结构默认折叠（渐进式披露）
    - 支持拖拽笔记到文件夹
    """

    note_selected = Signal(Note)
    note_created = Signal(Note)
    note_deleted = Signal(str)
    note_moved = Signal(str, str, str)  # (note_id, old_folder, new_folder)

    def __init__(self):
        super().__init__()

        self._current_folder = ""  # 当前选中的文件夹路径
        self._current_note_id = ""  # 当前选中的笔记 ID
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

        # 文件夹区域标题
        folder_header = QHBoxLayout()
        folder_label = QLabel("文件夹")
        folder_label.setStyleSheet("font-weight: 600; color: #5A4A3A;")
        folder_header.addWidget(folder_label)
        folder_header.addStretch()

        self.new_folder_btn = QPushButton("+ 新建")
        self.new_folder_btn.setToolTip("新建文件夹")
        self.new_folder_btn.setMinimumWidth(60)
        folder_header.addWidget(self.new_folder_btn)
        layout.addLayout(folder_header)

        # 树形文件夹列表（支持嵌套和放置）
        self.folder_tree = DropableTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setMaximumHeight(200)
        self.folder_tree.setIndentation(20)
        self.folder_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #FFFEF9;
                border: 1px solid #E8DFD5;
                border-radius: 12px;
                padding: 6px;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 4px 6px;
                border-radius: 4px;
                color: #4A3F35;
            }
            QTreeWidget::item:selected {
                background-color: #FDF6ED;
                color: #8B5A2B;
            }
            QTreeWidget::item:hover:!selected {
                background-color: #FDF8F0;
            }
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                background-color: transparent;
                border-image: none;
            }
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {
                background-color: transparent;
                border-image: none;
            }
        """)
        layout.addWidget(self.folder_tree)

        # 笔记列表标题
        notes_label = QLabel("笔记")
        notes_label.setStyleSheet("font-weight: 600; color: #5A4A3A;")
        layout.addWidget(notes_label)

        # 笔记列表（支持拖拽）
        self.note_list = DraggableListWidget()
        layout.addWidget(self.note_list, 1)

        # 标签筛选标题
        tags_label = QLabel("标签")
        tags_label.setStyleSheet("font-weight: 600; color: #5A4A3A;")
        layout.addWidget(tags_label)

        # 标签列表
        self.tag_list = QListWidget()
        self.tag_list.setMaximumHeight(80)
        layout.addWidget(self.tag_list)

        # 新建笔记按钮
        self.new_button = QPushButton("新建笔记")
        layout.addWidget(self.new_button)

    def _connect_signals(self) -> None:
        """连接信号"""
        self.search_input.textChanged.connect(self._on_search)
        self.note_list.itemClicked.connect(self._on_note_clicked)
        self.note_list.itemDoubleClicked.connect(self._on_note_double_clicked)
        self.tag_list.itemClicked.connect(self._on_tag_clicked)
        self.folder_tree.itemClicked.connect(self._on_folder_clicked)
        self.new_button.clicked.connect(self.create_new_note)
        self.new_folder_btn.clicked.connect(self._create_root_folder)

        # 拖拽信号
        self.folder_tree.note_dropped.connect(self._on_note_dropped)

        # 右键菜单
        self.note_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.note_list.customContextMenuRequested.connect(self._show_note_context_menu)

        self.folder_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_tree.customContextMenuRequested.connect(self._show_folder_context_menu)

    def refresh(self) -> None:
        """刷新列表"""
        self._load_folders()
        self._load_notes()
        self._load_tags()

    def _load_folders(self) -> None:
        """加载文件夹树"""
        self.folder_tree.clear()

        note_manager = get_note_manager()
        folders = note_manager.list_folders()

        # 创建 "全部笔记" 根节点
        root_item = QTreeWidgetItem(self.folder_tree, ["📁 全部笔记"])
        root_item.setData(0, Qt.ItemDataRole.UserRole, "")
        root_item.setExpanded(True)

        # 构建文件夹树
        folder_dict = {f.name: f for f in folders}

        # 找出顶层文件夹（没有父文件夹的）
        top_folders = [f for f in folders if not f.parent]

        for folder in top_folders:
            self._add_folder_to_tree(root_item, folder, folder_dict)

        # 选中当前文件夹
        self._select_current_folder()

    def _add_folder_to_tree(
        self,
        parent_item: QTreeWidgetItem,
        folder: Folder,
        folder_dict: dict[str, Folder]
    ) -> None:
        """递归添加文件夹到树中"""
        item = QTreeWidgetItem(parent_item, [f"📁 {folder.name}"])
        item.setData(0, Qt.ItemDataRole.UserRole, folder.name)

        # 渐进式披露：默认折叠
        item.setExpanded(False)

        # 查找子文件夹
        note_manager = get_note_manager()
        all_folders = note_manager.list_folders()
        child_folders = [f for f in all_folders if f.parent == folder.name]

        for child in child_folders:
            self._add_folder_to_tree(item, child, folder_dict)

    def _select_current_folder(self) -> None:
        """选中当前文件夹"""
        if not self._current_folder:
            # 选中 "全部笔记"
            root = self.folder_tree.topLevelItem(0)
            if root:
                self.folder_tree.setCurrentItem(root)
            return

        # 查找并选中对应的文件夹项
        def find_folder_item(parent: QTreeWidgetItem | None, folder_name: str) -> QTreeWidgetItem | None:
            count = self.folder_tree.topLevelItemCount() if parent is None else parent.childCount()

            for i in range(count):
                item = self.folder_tree.topLevelItem(i) if parent is None else parent.child(i)
                if item.data(0, Qt.ItemDataRole.UserRole) == folder_name:
                    return item
                # 递归查找子项
                result = find_folder_item(item, folder_name)
                if result:
                    return result
            return None

        item = find_folder_item(None, self._current_folder)
        if item:
            self.folder_tree.setCurrentItem(item)
            # 展开父节点以显示选中项
            parent = item.parent()
            while parent:
                parent.setExpanded(True)
                parent = parent.parent()

    def _load_notes(self, filter_tag: str | None = None) -> None:
        """加载笔记列表"""
        self.note_list.clear()

        note_manager = get_note_manager()

        if filter_tag:
            notes = note_manager.get_notes_by_tag(filter_tag)
        elif self._current_folder:
            notes = note_manager.list_notes(folder=self._current_folder)
        else:
            notes = note_manager.list_notes()

        for note in notes:
            item = QListWidgetItem(note.title)
            item.setData(Qt.ItemDataRole.UserRole, note.id)
            item.setToolTip(f"更新: {note.updated_at.strftime('%Y-%m-%d %H:%M')}")

            if note.tags:
                item.setText(f"{note.title} {' '.join(f'#{t}' for t in note.tags)}")

            self.note_list.addItem(item)

    def _load_tags(self) -> None:
        """加载标签列表"""
        self.tag_list.clear()

        note_manager = get_note_manager()
        tags = note_manager.list_tags()

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

    @Slot(QTreeWidgetItem)
    def _on_folder_clicked(self, item: QTreeWidgetItem) -> None:
        """文件夹被点击"""
        self._current_folder = item.data(0, Qt.ItemDataRole.UserRole)
        self._load_notes()

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
            note = note_manager.create_note(title, folder=self._current_folder)

            self.refresh()
            self.note_created.emit(note)

    @Slot()
    def _create_root_folder(self) -> None:
        """创建根文件夹"""
        self._create_folder(None)

    def _create_folder(self, parent_folder: str | None) -> None:
        """创建文件夹

        Args:
            parent_folder: 父文件夹名称，None 表示根文件夹
        """
        name, ok = QInputDialog.getText(
            self,
            "新建文件夹",
            "请输入文件夹名称:",
        )

        if ok and name:
            note_manager = get_note_manager()
            note_manager.create_folder(name, parent=parent_folder or "")
            self.refresh()

    def _show_note_context_menu(self, pos: Any) -> None:
        """显示笔记右键菜单"""
        item = self.note_list.itemAt(pos)
        if not item:
            return

        note_id = item.data(Qt.ItemDataRole.UserRole)
        note_manager = get_note_manager()
        note = note_manager.get_note(note_id)

        menu = QMenu(self)

        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self._delete_note(note_id))
        menu.addAction(delete_action)

        menu.addSeparator()

        # 移动到文件夹
        folders = note_manager.list_folders()
        if folders:
            move_menu = menu.addMenu("移动到")

            no_folder_action = QAction("无文件夹", self)
            no_folder_action.triggered.connect(lambda: self._move_note_to_folder(note_id, ""))
            move_menu.addAction(no_folder_action)

            move_menu.addSeparator()

            for folder in folders:
                # 显示完整路径（包含父文件夹）
                path = self._get_folder_path(folder.name, note_manager)
                action = QAction(path, self)
                action.triggered.connect(lambda checked, f=folder.name: self._move_note_to_folder(note_id, f))
                move_menu.addAction(action)

        menu.exec(self.note_list.mapToGlobal(pos))

    def _get_folder_path(self, folder_name: str, note_manager: Any) -> str:
        """获取文件夹的完整路径"""
        folders = {f.name: f for f in note_manager.list_folders()}

        parts = [folder_name]
        current = folders.get(folder_name)
        while current and current.parent:
            parts.insert(0, current.parent)
            current = folders.get(current.parent)

        return " / ".join(parts)

    def _show_folder_context_menu(self, pos: Any) -> None:
        """显示文件夹右键菜单"""
        item = self.folder_tree.itemAt(pos)
        if not item:
            return

        folder_name = item.data(0, Qt.ItemDataRole.UserRole)

        menu = QMenu(self)

        if not folder_name:  # "全部笔记"
            new_folder_action = QAction("新建文件夹", self)
            new_folder_action.triggered.connect(lambda: self._create_folder(None))
            menu.addAction(new_folder_action)

            menu.addSeparator()

            # 刷新所有文件夹概要
            refresh_all_action = QAction("刷新所有文件夹概要", self)
            refresh_all_action.triggered.connect(self._refresh_all_folder_skills)
            menu.addAction(refresh_all_action)
        else:
            # 新建子文件夹
            new_sub_action = QAction("新建子文件夹", self)
            new_sub_action.triggered.connect(lambda: self._create_folder(folder_name))
            menu.addAction(new_sub_action)

            menu.addSeparator()

            rename_action = QAction("重命名", self)
            rename_action.triggered.connect(lambda: self._rename_folder(folder_name))
            menu.addAction(rename_action)

            delete_action = QAction("删除", self)
            delete_action.triggered.connect(lambda: self._delete_folder(folder_name))
            menu.addAction(delete_action)

            menu.addSeparator()

            # 刷新文件夹概要
            refresh_action = QAction("刷新文件夹概要", self)
            refresh_action.triggered.connect(lambda: self._refresh_folder_skill(folder_name))
            menu.addAction(refresh_action)

        menu.exec(self.folder_tree.mapToGlobal(pos))

    def _delete_note(self, note_id: str) -> None:
        """删除笔记"""
        note_manager = get_note_manager()
        note = note_manager.get_note(note_id)

        if note:
            note_manager.delete_note(note_id)
            self.refresh()
            self.note_deleted.emit(note_id)

    def _move_note_to_folder(self, note_id: str, folder_name: str) -> None:
        """移动笔记到文件夹"""
        note_manager = get_note_manager()
        note = note_manager.get_note(note_id)
        old_folder = note.folder if note else ""

        note_manager.update_note(note_id, folder=folder_name)
        self.refresh()

        # 发出移动信号，用于触发 SKILL.md 更新
        self.note_moved.emit(note_id, old_folder, folder_name)

    @Slot(str, str)
    def _on_note_dropped(self, note_id: str, folder_name: str) -> None:
        """处理笔记拖拽放置"""
        self._move_note_to_folder(note_id, folder_name)

    def _rename_folder(self, old_name: str) -> None:
        """重命名文件夹"""
        new_name, ok = QInputDialog.getText(
            self,
            "重命名文件夹",
            "请输入新名称:",
            text=old_name,
        )

        if ok and new_name and new_name != old_name:
            note_manager = get_note_manager()
            note_manager.rename_folder(old_name, new_name)
            if self._current_folder == old_name:
                self._current_folder = new_name
            self.refresh()

    def _delete_folder(self, name: str) -> None:
        """删除文件夹"""
        note_manager = get_note_manager()
        note_manager.delete_folder(name)
        if self._current_folder == name:
            self._current_folder = ""
        self.refresh()

    def _refresh_folder_skill(self, folder_name: str) -> None:
        """刷新单个文件夹 SKILL"""
        from ..core.folder_skill_updater import get_folder_skill_updater
        updater = get_folder_skill_updater()
        updater.refresh_folder_skill_immediate(folder_name)

    def _refresh_all_folder_skills(self) -> None:
        """刷新所有文件夹 SKILL"""
        from ..core.folder_skill_updater import get_folder_skill_updater
        updater = get_folder_skill_updater()
        updater.refresh_all_folder_skills()