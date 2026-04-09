"""左侧边栏模块

显示笔记列表、文件夹和标签。
支持嵌套文件夹结构，体现 Skills 的嵌套和渐进式披露特性。
支持拖拽笔记到文件夹。
"""

import platform
import subprocess
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal, Slot, QMimeData, QPoint, QRect
from PySide6.QtGui import QAction, QDrag, QPainter, QColor, QFont, QPolygon, QIcon
from PySide6.QtWidgets import (
    QDialog,
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
from ..core.note_naming import validate_note_name, sanitize_note_name


class NewNoteDialog(QDialog):
    """新建笔记对话框 - 自定义小巧按钮"""

    def __init__(self, parent=None, folder_name: str = ""):
        super().__init__(parent)
        self.folder_name = folder_name
        self.note_title = ""
        self.setWindowTitle("新建笔记")
        self.setMinimumWidth(320)
        self.setStyleSheet("""
            QDialog {
                background-color: #FBF7F2;
            }
            QLabel {
                color: #3D3428;
                font-size: 13px;
            }
            QLineEdit {
                background-color: #FFFEF9;
                border: 1px solid #E8DFD5;
                border-radius: 4px;
                padding: 6px 8px;
                font-size: 13px;
                color: #3D3428;
            }
            QLineEdit:focus {
                border-color: #D4A574;
            }
        """)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 标题标签
        label = QLabel("请输入笔记标题:")
        layout.addWidget(label)

        # 输入框
        self.title_input = QLineEdit()
        if self.folder_name:
            self.title_input.setPlaceholderText(f"将在「{self.folder_name}」文件夹中创建")
        else:
            self.title_input.setPlaceholderText("笔记标题（支持中英文、数字、空格等）")
        self.title_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.title_input)

        # 错误提示标签
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("""
            QLabel {
                color: #E74C3C;
                font-size: 11px;
            }
        """)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        # 提示信息
        hint_label = QLabel("提示：不能使用 <>:\"/\\|?* 等特殊字符，不能以空格或点号开头结尾")
        hint_label.setStyleSheet("""
            QLabel {
                color: #8B7B6B;
                font-size: 10px;
            }
        """)
        layout.addWidget(hint_label)

        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        # 取消按钮 - 小巧紧凑
        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(50, 24)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5EDE4;
                color: #5A4A3A;
                border: 1px solid #E8DFD5;
                border-radius: 4px;
                font-size: 12px;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background-color: #E8DFD5;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        # 确定按钮 - 小巧紧凑
        self.confirm_btn = QPushButton("确定")
        self.confirm_btn.setFixedSize(50, 24)
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #D4A574, stop:1 #C49564);
                color: #FFFEF9;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                padding: 2px 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #C49564, stop:1 #B48554);
            }
            QPushButton:disabled {
                background: #E8DFD5;
                color: #8B7B6B;
            }
        """)
        self.confirm_btn.clicked.connect(self._on_confirm)
        self.confirm_btn.setDefault(True)
        btn_layout.addWidget(self.confirm_btn)

        layout.addLayout(btn_layout)

    def _on_text_changed(self, text: str) -> None:
        """文本改变时验证"""
        is_valid, error_msg = validate_note_name(text.strip())
        if not is_valid and text.strip():
            self.error_label.setText(error_msg)
            self.error_label.show()
            self.confirm_btn.setEnabled(False)
        else:
            self.error_label.hide()
            self.confirm_btn.setEnabled(True)

    def _on_confirm(self) -> None:
        """确定按钮点击"""
        raw_title = self.title_input.text().strip()
        if not raw_title:
            self.title_input.setFocus()
            return

        # 验证名称
        is_valid, error_msg = validate_note_name(raw_title)
        if not is_valid:
            self.error_label.setText(error_msg)
            self.error_label.show()
            return

        # 清理名称
        self.note_title = sanitize_note_name(raw_title)
        self.accept()


class DraggableListWidget(QListWidget):
    """支持拖拽到文件夹的列表控件"""

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

    def drawBranches(self, painter: QPainter, rect: QRect, index) -> None:
        """自定义绘制展开/收起按钮，使用三角形指示器"""
        item = self.itemFromIndex(index)
        if item is None:
            return

        # 【修复】无论是否有子节点，都先填充背景色，覆盖 Qt 默认的黑底
        painter.fillRect(rect, QColor("#FFFEF9"))  # 象牙白背景

        # 无子节点时不绘制三角形，直接返回
        if item.childCount() == 0:
            return

        # 三角形参数
        size = 8  # 三角形大小

        # 计算三角形位置：紧挨文字左侧
        # 需要考虑 indentation
        indentation = self.indentation()
        depth = 0
        parent = item.parent()
        while parent:
            depth += 1
            parent = parent.parent()

        # 三角形放在当前层级缩进之后
        x = rect.left() + depth * indentation + 4
        y = rect.top() + (rect.height() - size) // 2

        # 设置绘制样式
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 三角形颜色（与文字颜色协调）
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#8B5A2B"))  # 棕色

        if item.isExpanded():
            # 展开状态：向下三角形 ▼
            points = [
                (x, y),
                (x + size, y),
                (x + size // 2, y + size)
            ]
        else:
            # 收起状态：向右三角形 ▶
            points = [
                (x, y),
                (x + size, y + size // 2),
                (x, y + size)
            ]

        polygon = QPolygon()
        for px, py in points:
            polygon.append(QPoint(px, py))
        painter.drawPolygon(polygon)

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
    note_selection_rejected = Signal(str)  # (note_id) 笔记选择被拒绝，需要恢复选中状态

    def __init__(self):
        super().__init__()
        self.setObjectName("sidebar")  # 设置对象名称用于样式匹配

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

        self.new_folder_btn = QPushButton()
        self.new_folder_btn.setToolTip("新建文件夹")
        self.new_folder_btn.setFixedSize(22, 22)
        self.new_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_folder_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #D4A574, stop:1 #C49564);
                border: none;
                border-radius: 4px;
                padding: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #C49564, stop:1 #B48554);
            }
        """)
        add_icon_path = Path(__file__).parent.parent.parent / "assets" / "add.svg"
        if add_icon_path.exists():
            self.new_folder_btn.setIcon(QIcon(str(add_icon_path)))
            self.new_folder_btn.setIconSize(self.new_folder_btn.size())
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
            QTreeWidget::branch:!has-children {
                background-color: transparent;
                border-image: none;
                image: none;
            }
        """)
        layout.addWidget(self.folder_tree)

        # 笔记列表标题
        notes_label = QLabel("笔记")
        notes_label.setStyleSheet("font-weight: 600; color: #5A4A3A;")
        layout.addWidget(notes_label)

        # 笔记列表（支持拖拽到文件夹）
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
        self.new_button = QPushButton(" 新建笔记")
        self.new_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #D4A574, stop:1 #C49564);
                color: #FFFEF9;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #C49564, stop:1 #B48554);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #B48554, stop:1 #A47544);
            }
        """)
        add_icon_path = Path(__file__).parent.parent.parent / "assets" / "add.svg"
        if add_icon_path.exists():
            self.new_button.setIcon(QIcon(str(add_icon_path)))
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
        """加载笔记列表（按标题自然排序）"""
        self.note_list.clear()

        note_manager = get_note_manager()

        if filter_tag:
            notes = note_manager.get_notes_by_tag(filter_tag)
            # 标签筛选时也按标题排序
            notes.sort(key=lambda n: note_manager._natural_sort_key(n.title))
        elif self._current_folder:
            notes = note_manager.list_notes(folder=self._current_folder)
        else:
            notes = note_manager.list_notes()

        for note in notes:
            item = QListWidgetItem(note.title)
            item.setData(Qt.ItemDataRole.UserRole, note.id)
            item.setToolTip(f"创建: {note.created_at.strftime('%Y-%m-%d %H:%M')} | 更新: {note.updated_at.strftime('%Y-%m-%d %H:%M')}")

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

    def restore_note_selection(self, note_id: str) -> None:
        """恢复笔记列表中的选中状态（当笔记切换被取消时）"""
        for i in range(self.note_list.count()):
            item = self.note_list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == note_id:
                self.note_list.setCurrentItem(item)
                break

    @Slot(QListWidgetItem)
    def _on_note_clicked(self, item: QListWidgetItem) -> None:
        """笔记被点击"""
        note_id = item.data(Qt.ItemDataRole.UserRole)
        self._current_note_id = note_id  # 记录当前选中的笔记ID
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
        dialog = NewNoteDialog(self, self._current_folder)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            note_manager = get_note_manager()
            note = note_manager.create_note(dialog.note_title, folder=self._current_folder)

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
        self._apply_menu_style(menu)

        # 在系统中查看
        open_action = QAction("在系统中查看", self)
        open_action.triggered.connect(lambda: self._open_note_in_system(note_id))
        menu.addAction(open_action)

        rename_action = QAction("重命名", self)
        rename_action.triggered.connect(lambda: self._rename_note(note_id))
        menu.addAction(rename_action)

        delete_action = QAction("删除", self)
        delete_action.triggered.connect(lambda: self._delete_note(note_id))
        menu.addAction(delete_action)

        folders = note_manager.list_folders()
        if folders:
            move_menu = menu.addMenu("移动到")
            self._apply_menu_style(move_menu)

            no_folder_action = QAction("无文件夹", self)
            no_folder_action.triggered.connect(lambda: self._move_note_to_folder(note_id, ""))
            move_menu.addAction(no_folder_action)

            for folder in folders:
                path = self._get_folder_path(folder.name, note_manager)
                action = QAction(path, self)
                action.triggered.connect(lambda checked, f=folder.name: self._move_note_to_folder(note_id, f))
                move_menu.addAction(action)

        menu.exec(self.note_list.mapToGlobal(pos))

    def _open_note_in_system(self, note_id: str) -> None:
        """在系统文件管理器中打开笔记文件"""
        note_manager = get_note_manager()
        note = note_manager.get_note(note_id)

        if not note:
            return

        # 获取笔记文件路径
        note_file = note_manager._get_note_file(note_id)

        if not note_file.exists():
            return

        # 根据操作系统选择打开方式
        system = platform.system()

        try:
            if system == "Windows":
                # Windows: 使用 explorer 打开文件所在文件夹并选中文件
                subprocess.run(["explorer", "/select,", str(note_file)], check=True)
            elif system == "Darwin":  # macOS
                # macOS: 使用 open 命令打开文件所在文件夹
                subprocess.run(["open", "-R", str(note_file)], check=True)
            else:  # Linux
                # Linux: 使用 xdg-open 打开文件所在文件夹
                subprocess.run(["xdg-open", str(note_file.parent)], check=True)
        except Exception as e:
            # 如果打开失败，尝试使用通用方法
            try:
                if system == "Windows":
                    import os
                    os.startfile(str(note_file.parent))
                else:
                    subprocess.run(["xdg-open", str(note_file.parent)], check=True)
            except Exception:
                pass

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
        self._apply_menu_style(menu)

        if not folder_name:  # "全部笔记"
            new_note_action = QAction("新建笔记", self)
            new_note_action.triggered.connect(lambda: self._create_note_in_folder(""))
            menu.addAction(new_note_action)

            new_folder_action = QAction("新建文件夹", self)
            new_folder_action.triggered.connect(lambda: self._create_folder(None))
            menu.addAction(new_folder_action)

            refresh_all_action = QAction("刷新所有文件夹概要", self)
            refresh_all_action.triggered.connect(self._refresh_all_folder_skills)
            menu.addAction(refresh_all_action)
        else:
            new_note_action = QAction("新建笔记", self)
            new_note_action.triggered.connect(lambda: self._create_note_in_folder(folder_name))
            menu.addAction(new_note_action)

            new_sub_action = QAction("新建子文件夹", self)
            new_sub_action.triggered.connect(lambda: self._create_folder(folder_name))
            menu.addAction(new_sub_action)

            rename_action = QAction("重命名", self)
            rename_action.triggered.connect(lambda: self._rename_folder(folder_name))
            menu.addAction(rename_action)

            delete_action = QAction("删除", self)
            delete_action.triggered.connect(lambda: self._delete_folder(folder_name))
            menu.addAction(delete_action)

            refresh_action = QAction("刷新文件夹概要", self)
            refresh_action.triggered.connect(lambda: self._refresh_folder_skill(folder_name))
            menu.addAction(refresh_action)

        menu.exec(self.folder_tree.mapToGlobal(pos))

    def _apply_menu_style(self, menu: QMenu) -> None:
        """应用紧凑菜单样式"""
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFEF9;
                border: 1px solid #E8DFD5;
                border-radius: 6px;
                padding: 4px 0px;
            }
            QMenu::item {
                padding: 6px 24px 6px 12px;
                color: #3D3428;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: #FDF6ED;
                color: #8B5A2B;
            }
            QMenu::separator {
                height: 1px;
                background-color: #E8DFD5;
                margin: 4px 8px;
            }
        """)

    def _create_note_in_folder(self, folder_name: str) -> None:
        """在指定文件夹中创建新笔记"""
        dialog = NewNoteDialog(self, folder_name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            note_manager = get_note_manager()
            note = note_manager.create_note(dialog.note_title, folder=folder_name)

            self._current_folder = folder_name
            self.refresh()
            self.note_created.emit(note)

    def _rename_note(self, note_id: str) -> None:
        """重命名笔记"""
        note_manager = get_note_manager()
        note = note_manager.get_note(note_id)

        if not note:
            return

        new_title, ok = QInputDialog.getText(
            self,
            "重命名笔记",
            "请输入新标题:",
            text=note.title,
        )

        if ok and new_title and new_title != note.title:
            note_manager.update_note(note_id, title=new_title)
            self.refresh()
            # 重新选中该笔记以更新显示
            for i in range(self.note_list.count()):
                item = self.note_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == note_id:
                    self.note_list.setCurrentItem(item)
                    # 重新加载笔记以更新标题
                    updated_note = note_manager.get_note(note_id)
                    if updated_note:
                        self.note_selected.emit(updated_note)
                    break

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