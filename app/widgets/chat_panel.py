"""AI 对话面板模块

提供 SKILL 生成、笔记问答和通用对话功能。
支持流式输出和思考状态显示。
"""

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QThread, Signal, Slot, QPoint, QSize, QEvent
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen, QIcon, QKeyEvent, QAction
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QListView,
    QDialog,
    QScrollArea,
    QCheckBox,
    QToolButton,
    QMenu,
    QApplication,
    QSizePolicy,
)

from ..ai.client import create_client
from ..core.config import get_config
from ..mcp.manager import MCPManager, MCPTool


class MessageItemWidget(QWidget):
    """消息项组件"""

    def __init__(self, sender: str, content: str, is_user: bool = False, parent=None):
        super().__init__(parent)
        self.sender = sender
        self.content = content
        self.is_user = is_user
        self._last_width = 0  # 记录上次宽度，避免重复计算
        self._init_ui()

    def _init_ui(self):
        """初始化界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 头像标签
        avatar_label = QLabel("👤" if self.is_user else "🤖")
        avatar_label.setStyleSheet("font-size: 16px;")
        avatar_label.setFixedSize(24, 24)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 使用 QTextEdit 显示文本，支持自动换行和复制
        self.content_edit = QTextEdit()
        self.content_edit.setPlainText(self.content)
        self.content_edit.setReadOnly(True)
        self.content_edit.setFrameStyle(QFrame.Shape.NoFrame)
        self.content_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.content_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # 使用 FixedPixelWidth 模式，这样可以精确控制换行宽度
        self.content_edit.setLineWrapMode(QTextEdit.LineWrapMode.FixedPixelWidth)
        self.content_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # 移除所有内边距
        self.content_edit.setViewportMargins(0, 0, 0, 0)
        self.content_edit.document().setDocumentMargin(0)
        self.content_edit.setStyleSheet("""
            QTextEdit {
                color: #3D3428;
                font-size: 13px;
                line-height: 1.4;
                padding: 0px;
                margin: 0px;
                background-color: transparent;
                border: none;
            }
        """)
        # 禁用 QTextEdit 的滚轮事件，让父级 QListWidget 处理滚动
        self.content_edit.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        # 初始化后更新高度
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, self._update_height)

        # 根据用户/AI 调整布局顺序
        if self.is_user:
            layout.addStretch()
            layout.addWidget(self.content_edit, 1)
            layout.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignTop)
        else:
            layout.addWidget(avatar_label, alignment=Qt.AlignmentFlag.AlignTop)
            layout.addWidget(self.content_edit, 1)
            layout.addStretch()

    def update_content(self, content: str):
        """更新内容并调整高度"""
        self.content = content
        self.content_edit.setPlainText(content)
        self._update_height()

    def _update_height(self, new_width: int = None):
        """根据内容更新高度
        
        Args:
            new_width: 新的宽度（可选，用于 resize 时直接传入）
        """
        if new_width is not None:
            # 使用传入的新宽度
            viewport_width = new_width
        else:
            # 获取 QTextEdit 的内容区域宽度
            viewport_width = self.content_edit.contentsRect().width()
            if viewport_width <= 0:
                viewport_width = self.content_edit.width() - 16
            if viewport_width <= 0:
                viewport_width = 400

        # 设置 FixedPixelWidth 模式的宽度，确保换行和高度计算一致
        self.content_edit.setLineWrapColumnOrWidth(int(viewport_width))

        doc = self.content_edit.document()
        # 使用相同的宽度计算高度
        doc.setTextWidth(viewport_width)
        # 计算高度
        height = doc.size().height()
        # 设置固定高度确保内容显示完整
        final_height = int(height) + 15
        self.content_edit.setFixedHeight(final_height)
        # 更新 widget 的最小高度
        self.setMinimumHeight(final_height + 12)  # 加上上下边距

    def sizeHint(self):
        """返回正确的大小提示"""
        # 返回 QTextEdit 的高度加上布局边距
        return QSize(self.width(), self.content_edit.height() + 12)

    def resizeEvent(self, event):
        """大小变化时重新计算高度"""
        super().resizeEvent(event)
        # 使用新尺寸中的宽度来更新高度
        new_width = event.size().width()
        # 减去头像和边距的宽度
        content_width = new_width - 24 - 16 - 16  # 头像24px + 间距8px*2 + 边距8px*2
        if content_width > 0:
            self._update_height(content_width)


class NoBorderComboBox(QComboBox):
    """无边框下拉框 - 解决 Windows 平台下拉列表黑边问题"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def showPopup(self) -> None:
        """显示下拉列表时移除容器边框"""
        super().showPopup()

        view = self.view()
        if view:
            container = view.window()
            if container:
                container.setWindowFlags(
                    container.windowFlags() |
                    Qt.WindowType.FramelessWindowHint |
                    Qt.WindowType.NoDropShadowWindowHint
                )

                container.setContentsMargins(0, 0, 0, 0)
                view.setGeometry(0, 0, container.width(), container.height())
                container.show()

    def paintEvent(self, event):
        """自定义绘制事件，绘制下拉箭头"""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        arrow_x = self.width() - 14
        arrow_y = self.height() // 2
        arrow_size = 5
        color = QColor(0x4A, 0x3F, 0x35)
        painter.setPen(QPen(color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        points = [
            QPoint(arrow_x - arrow_size, arrow_y - 2),
            QPoint(arrow_x, arrow_y + 3),
            QPoint(arrow_x + arrow_size, arrow_y - 2),
        ]
        path = QPainterPath()
        path.moveTo(points[0])
        path.lineTo(points[1])
        path.lineTo(points[2])
        painter.drawPath(path)


class ModelListWorker(QThread):
    """异步加载模型列表的工作线程"""

    models_loaded = Signal(list)
    load_error = Signal(str)

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self._client = client

    def run(self) -> None:
        try:
            if self._client is None:
                self.models_loaded.emit([])
                return
            models = self._client.list_models()
            self.models_loaded.emit(models or [])
        except Exception as e:
            self.load_error.emit(str(e))


class ModelSelector(QWidget):
    """模型选择器 - 使用 QToolButton + QFrame 弹出列表"""

    model_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._models: list[str] = []
        self._current_model: str = ""
        self._popup: QFrame | None = None
        self._list_widget: QListWidget | None = None
        self._filter_edit: QLineEdit | None = None
        self._is_loading = False
        self._init_ui()

    def _init_ui(self) -> None:
        """初始化界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 主按钮
        self._button = QToolButton()
        self._button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._button.setStyleSheet("""
            QToolButton {
                background-color: #FFFEF9;
                border: 1px solid #E8DFD5;
                border-radius: 4px;
                padding: 4px 20px 4px 8px;
                color: #4A3F35;
                font-size: 12px;
                min-width: 100px;
                text-align: left;
            }
            QToolButton:hover {
                border-color: #D4A574;
                background-color: #FDF8F0;
            }
            QToolButton::menu-indicator {
                subcontrol-position: right center;
                subcontrol-origin: padding;
                right: 6px;
                width: 12px;
            }
        """)
        self._button.clicked.connect(self._show_popup)
        layout.addWidget(self._button)

        # 设置初始文本
        self._update_button_text("选择模型")

    def _update_button_text(self, text: str) -> None:
        """更新按钮文本，长文本截断显示"""
        max_len = 20
        if len(text) > max_len:
            display_text = text[:max_len - 3] + "..."
            self._button.setToolTip(text)
        else:
            display_text = text
            self._button.setToolTip("")
        self._button.setText(display_text)

    def set_models(self, models: list[str]) -> None:
        """设置模型列表"""
        self._models = models

    def set_current_model(self, model: str) -> None:
        """设置当前模型"""
        self._current_model = model
        self._update_button_text(model)

    def current_model(self) -> str:
        """获取当前模型"""
        return self._current_model

    def show_loading(self) -> None:
        """显示加载状态"""
        self._is_loading = True
        self._button.setText("加载中...")
        self._button.setEnabled(False)

    def hide_loading(self) -> None:
        """隐藏加载状态"""
        self._is_loading = False
        self._button.setEnabled(True)
        if self._current_model:
            self._update_button_text(self._current_model)

    def show_error(self, error_msg: str) -> None:
        """显示错误状态"""
        self._is_loading = False
        self._button.setText(error_msg)
        self._button.setEnabled(True)
        self._button.setStyleSheet("""
            QToolButton {
                background-color: #FFF5F5;
                border: 1px solid #E8B0A0;
                border-radius: 4px;
                padding: 4px 20px 4px 8px;
                color: #8B5A2B;
                font-size: 12px;
                min-width: 100px;
                text-align: left;
            }
            QToolButton:hover {
                border-color: #D4A574;
                background-color: #FDF8F0;
            }
        """)

    def _show_popup(self) -> None:
        """显示弹出列表"""
        if self._is_loading:
            return

        # 关闭已有的弹出窗口
        self._close_popup()

        # 创建弹出容器
        self._popup = QFrame(self, Qt.WindowType.Popup)
        self._popup.setWindowFlags(
            Qt.WindowType.Popup |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self._popup.setStyleSheet("""
            QFrame {
                background-color: #FFFEF9;
                border: 1px solid #E8DFD5;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(self._popup)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # 搜索过滤框
        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("搜索模型...")
        self._filter_edit.setStyleSheet("""
            QLineEdit {
                background-color: #FFFEF9;
                border: 1px solid #E8DFD5;
                border-radius: 4px;
                padding: 6px 10px;
                color: #4A3F35;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #D4A574;
            }
        """)
        self._filter_edit.textChanged.connect(self._filter_models)
        layout.addWidget(self._filter_edit)

        # 创建列表
        self._list_widget = QListWidget()
        self._list_widget.setMaximumHeight(200)
        self._list_widget.setStyleSheet("""
            QListWidget {
                background-color: #FFFEF9;
                border: none;
                outline: none;
            }
            QListWidget::item {
                padding: 8px 12px;
                color: #5A4A3A;
                font-size: 12px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #FDF8F0;
            }
            QListWidget::item:selected {
                background-color: #FDF6ED;
                color: #8B5A2B;
            }
        """)

        # 添加模型项
        for model in self._models:
            item = QListWidgetItem(model)
            item.setData(Qt.ItemDataRole.UserRole, model)
            # 长名称设置 tooltip
            if len(model) > 30:
                item.setToolTip(model)
            self._list_widget.addItem(item)

        self._list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list_widget)

        # 定位弹出窗口
        button_rect = self._button.rect()
        popup_pos = self._button.mapToGlobal(button_rect.bottomLeft())
        popup_pos.setY(popup_pos.y() + 2)
        self._popup.move(popup_pos)

        # 设置宽度（按钮宽度的 1.5 倍）
        popup_width = int(self._button.width() * 1.5)
        self._popup.setFixedWidth(popup_width)

        self._popup.show()

        # 自动聚焦到搜索框
        self._filter_edit.setFocus()

        # 安装事件过滤器
        self._popup.installEventFilter(self)
        self._filter_edit.installEventFilter(self)

    def _close_popup(self) -> None:
        """关闭弹出窗口"""
        if self._popup:
            self._popup.close()
            self._popup.deleteLater()
            self._popup = None

    def _filter_models(self, filter_text: str) -> None:
        """过滤模型列表"""
        if not self._list_widget:
            return

        filter_lower = filter_text.lower()
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            model = item.data(Qt.ItemDataRole.UserRole)
            # 模糊匹配：包含过滤文本即显示
            item.setHidden(filter_lower not in model.lower())

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """选择模型项"""
        model = item.data(Qt.ItemDataRole.UserRole)
        self._current_model = model
        self._update_button_text(model)
        self._close_popup()
        self.model_changed.emit(model)

    def _navigate_list(self, direction: int) -> None:
        """导航列表项

        Args:
            direction: 1 向下，-1 向上
        """
        if not self._list_widget or self._list_widget.count() == 0:
            return

        current_row = self._list_widget.currentRow()

        # 找到下一个可见项
        for i in range(1, self._list_widget.count() + 1):
            next_row = (current_row + direction * i) % self._list_widget.count()
            if next_row < 0:
                next_row = self._list_widget.count() - 1
            item = self._list_widget.item(next_row)
            if item and not item.isHidden():
                self._list_widget.setCurrentRow(next_row)
                self._list_widget.scrollToItem(item)
                break

    def _select_current_item(self) -> None:
        """选择当前高亮项"""
        if not self._list_widget:
            return

        item = self._list_widget.currentItem()
        if item and not item.isHidden():
            self._on_item_clicked(item)

    def eventFilter(self, obj, event) -> bool:
        """事件过滤器 - 处理弹出窗口点击外部关闭和键盘导航"""
        # 键盘导航处理
        if obj == self._filter_edit and event.type() == QEvent.Type.KeyPress:
            key = event.key()

            if key == Qt.Key.Key_Down:
                # 向下移动选择
                self._navigate_list(1)
                return True
            elif key == Qt.Key.Key_Up:
                # 向上移动选择
                self._navigate_list(-1)
                return True
            elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
                # 确认选择
                self._select_current_item()
                return True
            elif key == Qt.Key.Key_Escape:
                # 关闭弹出窗口
                self._close_popup()
                return True

        # 原有的点击外部关闭逻辑
        if obj == self._popup and event.type() == QEvent.Type.MouseButtonPress:
            popup_rect = self._popup.rect()
            popup_rect.moveTo(self._popup.mapToGlobal(popup_rect.topLeft()))
            if not popup_rect.contains(event.globalPosition().toPoint()):
                self._close_popup()
                return True

        return super().eventFilter(obj, event)


class MCPToolSelector(QWidget):
    """MCP 工具选择器 - 多选下拉组件（参考 ModelSelector 实现）"""

    tools_changed = Signal(list)  # 选中工具名称列表

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tool_names: list[str] = []  # 工具名称列表
        self._selected: set[str] = set()  # 选中的工具名称
        self._popup: QFrame | None = None
        self._list_widget: QListWidget | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        """初始化界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 主按钮
        self._button = QToolButton()
        self._button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._button.setStyleSheet("""
            QToolButton {
                background-color: #FFFEF9;
                border: 1px solid #E8DFD5;
                border-radius: 4px;
                padding: 4px 16px 4px 8px;
                color: #4A3F35;
                font-size: 12px;
                min-width: 70px;
                text-align: center;
            }
            QToolButton:hover {
                border-color: #D4A574;
                background-color: #FDF8F0;
            }
        """)
        self._button.clicked.connect(self._show_popup)
        layout.addWidget(self._button)

        self._update_button_text()

    def _update_button_text(self) -> None:
        """更新按钮文本"""
        count = len(self._selected)
        if count == 0:
            self._button.setText("工具")
        else:
            self._button.setText(f"工具({count})")

    def set_tools(self, tool_names: list[str]) -> None:
        """设置工具名称列表"""
        self._tool_names = list(tool_names)
        # 保留仍然存在的选中项
        self._selected = self._selected & set(tool_names)
        self._update_button_text()

    def get_selected(self) -> list[str]:
        """获取选中的工具名称列表"""
        return list(self._selected)

    def _show_popup(self) -> None:
        """显示弹出列表"""
        self._close_popup()

        # 创建弹出容器
        self._popup = QFrame(self, Qt.WindowType.Popup)
        self._popup.setWindowFlags(
            Qt.WindowType.Popup |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self._popup.setStyleSheet("""
            QFrame {
                background-color: #FFFEF9;
                border: 1px solid #E8DFD5;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(self._popup)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        if not self._tool_names:
            # 无工具提示
            label = QLabel("暂无可用工具")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #8B7B6B; font-size: 12px; padding: 10px;")
            layout.addWidget(label)
        else:
            # 工具列表（带复选框）
            self._list_widget = QListWidget()
            self._list_widget.setMaximumHeight(200)
            self._list_widget.setStyleSheet("""
                QListWidget {
                    background-color: #FFFEF9;
                    border: none;
                    outline: none;
                }
                QListWidget::item {
                    padding: 6px 8px;
                    color: #3D3428;
                    font-size: 12px;
                    border-radius: 4px;
                }
                QListWidget::item:hover {
                    background-color: #FDF8F0;
                }
            """)

            for name in self._tool_names:
                item = QListWidgetItem()
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(
                    Qt.CheckState.Checked if name in self._selected else Qt.CheckState.Unchecked
                )
                item.setText(name)
                item.setData(Qt.ItemDataRole.UserRole, name)
                self._list_widget.addItem(item)

            self._list_widget.itemClicked.connect(self._on_item_clicked)
            layout.addWidget(self._list_widget)

            # 确定按钮
            confirm_btn = QPushButton("确定")
            confirm_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #D4A574, stop:1 #C49564);
                    color: #FFFEF9;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 #C49564, stop:1 #B48554);
                }
            """)
            confirm_btn.clicked.connect(self._on_confirm)
            layout.addWidget(confirm_btn)

        # 定位弹出窗口
        button_rect = self._button.rect()
        popup_pos = self._button.mapToGlobal(button_rect.bottomLeft())
        popup_pos.setY(popup_pos.y() + 2)
        self._popup.move(popup_pos)
        self._popup.setFixedWidth(220)
        self._popup.adjustSize()
        self._popup.show()

        # 安装事件过滤器
        self._popup.installEventFilter(self)

    def _close_popup(self) -> None:
        """关闭弹出窗口"""
        if self._popup:
            self._popup.close()
            self._popup.deleteLater()
            self._popup = None
            self._list_widget = None

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        """切换项的选中状态"""
        # 点击时切换复选框状态
        if item.checkState() == Qt.CheckState.Checked:
            item.setCheckState(Qt.CheckState.Unchecked)
        else:
            item.setCheckState(Qt.CheckState.Checked)

    def _on_confirm(self) -> None:
        """确认选择"""
        if self._list_widget:
            self._selected = set()
            for i in range(self._list_widget.count()):
                item = self._list_widget.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    name = item.data(Qt.ItemDataRole.UserRole)
                    self._selected.add(name)

        self._update_button_text()
        self._close_popup()
        self.tools_changed.emit(list(self._selected))

    def eventFilter(self, obj, event) -> bool:
        """事件过滤器"""
        if obj == self._popup and event.type() == QEvent.Type.MouseButtonPress:
            popup_rect = self._popup.rect()
            popup_rect.moveTo(self._popup.mapToGlobal(popup_rect.topLeft()))
            if not popup_rect.contains(event.globalPosition().toPoint()):
                self._close_popup()
                return True
        return super().eventFilter(obj, event)


class StreamChatWorker(QThread):
    """流式 AI 聊天工作线程"""

    chunk_received = Signal(str)
    thinking_started = Signal()
    thinking_ended = Signal()
    finished_with_error = Signal(str)
    tool_call_started = Signal(str, dict)  # tool_name, arguments
    tool_call_result = Signal(str, str, bool)  # tool_name, result, is_error

    def __init__(
        self,
        client: Any,
        messages: list[dict[str, str]],
        tools: list[MCPTool] | None = None,
        mcp_manager: MCPManager | None = None,
        use_stream: bool = True,
    ):
        super().__init__()
        self.client = client
        self.messages = messages
        self.tools = tools or []
        self.mcp_manager = mcp_manager
        self.use_stream = use_stream

    def run(self) -> None:
        try:
            # 构建工具 schema
            from ..ai.client import MCPToolSchema
            tool_schemas = [
                MCPToolSchema(
                    name=tool.name,
                    description=tool.description,
                    input_schema=tool.input_schema,
                )
                for tool in self.tools
            ] if self.tools else None

            # 工具调用循环
            current_messages = list(self.messages)
            max_iterations = 10  # 防止无限循环

            for iteration in range(max_iterations):
                self.thinking_started.emit()

                if self.use_stream:
                    full_content = ""
                    tool_calls = None

                    for response in self.client.chat_stream(current_messages, tool_schemas):
                        if response.content:
                            full_content += response.content
                            self.chunk_received.emit(response.content)
                        if response.tool_calls:
                            tool_calls = response.tool_calls

                    self.thinking_ended.emit()

                    # 检查是否有工具调用
                    if tool_calls:
                        # 执行工具调用
                        tool_results = self._execute_tool_calls(tool_calls)

                        # 更新消息历史
                        current_messages.append({
                            "role": "assistant",
                            "content": full_content,
                            "tool_calls": [
                                {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": str(tc.arguments)}}
                                for tc in tool_calls
                            ]
                        })

                        for result in tool_results:
                            current_messages.append({
                                "role": "tool",
                                "tool_call_id": result.tool_call_id,
                                "content": result.content,
                            })

                        # 继续循环，让 AI 处理工具结果
                        continue
                    else:
                        # 没有工具调用，结束
                        break
                else:
                    response = self.client.chat(current_messages, tool_schemas)
                    self.thinking_ended.emit()

                    if response.content:
                        self.chunk_received.emit(response.content)

                    if response.tool_calls:
                        tool_results = self._execute_tool_calls(response.tool_calls)

                        current_messages.append({
                            "role": "assistant",
                            "content": response.content,
                        })

                        for result in tool_results:
                            current_messages.append({
                                "role": "tool",
                                "tool_call_id": result.tool_call_id,
                                "content": result.content,
                            })

                        continue
                    else:
                        break

        except Exception as e:
            # 处理编码错误
            try:
                error_msg = str(e)
            except UnicodeEncodeError:
                error_msg = repr(e)
            self.finished_with_error.emit(error_msg)

    def _execute_tool_calls(self, tool_calls: list) -> list:
        """执行工具调用"""
        from ..ai.client import ToolResult

        results = []
        if not self.mcp_manager:
            return results

        for tool_call in tool_calls:
            self.tool_call_started.emit(tool_call.name, tool_call.arguments)

            try:
                # 调用 MCP 工具
                content, is_error = self.mcp_manager.call_tool(
                    tool_call.name,
                    tool_call.arguments
                )

                result = ToolResult(
                    tool_call_id=tool_call.id,
                    name=tool_call.name,
                    content=content,
                    is_error=is_error,
                )
                self.tool_call_result.emit(tool_call.name, content, is_error)
                results.append(result)

            except Exception as e:
                result = ToolResult(
                    tool_call_id=tool_call.id,
                    name=tool_call.name,
                    content=f"Error: {str(e)}",
                    is_error=True,
                )
                self.tool_call_result.emit(tool_call.name, result.content, True)
                results.append(result)

        return results


class MCPToolsDialog(QDialog):
    """MCP 工具选择对话框"""

    def __init__(self, tools: list[MCPTool], selected_tools: list[str], parent=None):
        super().__init__(parent)
        self._tools = tools
        self._selected_tools = list(selected_tools)
        self._checkboxes: dict[str, QCheckBox] = {}
        self.setWindowTitle("选择 MCP 工具")
        self.setMinimumSize(400, 300)
        self.setStyleSheet("QDialog { background-color: #FBF7F2; }")
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        if not self._tools:
            no_tools_label = QLabel("暂无可用的 MCP 工具\n请先在设置中配置并启用 MCP")
            no_tools_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_tools_label.setStyleSheet("color: #8B7B6B; font-size: 14px;")
            layout.addWidget(no_tools_label)
        else:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet("""
                QScrollArea {
                    border: 1px solid #E8DFD5;
                    border-radius: 8px;
                    background-color: #FFFEF9;
                }
            """)
            scroll_widget = QWidget()
            scroll_layout = QVBoxLayout(scroll_widget)
            scroll_layout.setSpacing(8)
            scroll_layout.setContentsMargins(12, 12, 12, 12)

            for tool in self._tools:
                checkbox = QCheckBox(f"{tool.name}")
                checkbox.setChecked(tool.name in self._selected_tools)
                checkbox.setStyleSheet("""
                    QCheckBox {
                        font-size: 13px;
                        color: #3D3428;
                    }
                    QCheckBox::indicator {
                        width: 16px;
                        height: 16px;
                    }
                """)
                if tool.description:
                    checkbox.setToolTip(tool.description)
                self._checkboxes[tool.name] = checkbox
                scroll_layout.addWidget(checkbox)

            scroll_layout.addStretch()
            scroll.setWidget(scroll_widget)
            layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5EDE4;
                color: #5A4A3A;
                border: 1px solid #E8DFD5;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #E8DFD5;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton("确定")
        confirm_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #D4A574, stop:1 #C49564);
                color: #FFFEF9;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #C49564, stop:1 #B48554);
            }
        """)
        confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)

    def _on_confirm(self) -> None:
        self._selected_tools = [
            name for name, checkbox in self._checkboxes.items()
            if checkbox.isChecked()
        ]
        self.accept()

    def get_selected_tools(self) -> list[str]:
        return self._selected_tools


class ChatPanel(QWidget):
    """AI 对话面板"""

    generate_skill_requested = Signal()

    MODE_SKILL = "生成 SKILL"
    MODE_CHAT = "AI 对话"

    def __init__(self):
        super().__init__()
        self.setObjectName("chat_panel")

        self._client: Any = None
        self._messages: list[dict[str, str]] = []
        self._worker: StreamChatWorker | None = None
        self._current_note_content: str = ""
        self._current_note_title: str = ""
        self._current_response: str = ""
        self._thinking_item: QListWidgetItem | None = None
        self._selected_mcp_tools: list[str] = []
        self._use_note_context: bool = True
        self._mcp_manager: MCPManager = MCPManager.get_instance()
        self._model_worker: ModelListWorker | None = None

        self._init_ui()
        self._connect_signals()
        self._load_client()
        self._load_model_list()
        self._load_mcp_servers()

    def _init_ui(self) -> None:
        """初始化界面 - 参考截图设计"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # ========== 顶部：模式选择 ==========
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        mode_label = QLabel("模式:")
        mode_label.setStyleSheet("color: #5A4A3A; font-size: 12px;")
        header_layout.addWidget(mode_label)

        self.mode_combo = NoBorderComboBox()
        view = QListView()
        view.setStyleSheet("""
            QListView {
                background-color: #FFFEF9;
                border: none;
                padding: 0px;
                outline: none;
            }
            QListView::item {
                padding: 4px 8px;
                min-height: 20px;
                background-color: #FFFEF9;
            }
            QListView::item:hover {
                background-color: #FDF8F0;
            }
            QListView::item:selected {
                background-color: #FDF6ED;
                color: #8B5A2B;
            }
        """)
        self.mode_combo.setView(view)
        self.mode_combo.addItems([self.MODE_CHAT, self.MODE_SKILL])
        self.mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #FFFEF9;
                border: 1px solid #E8DFD5;
                border-radius: 0;
                padding: 2px 6px;
                padding-right: 18px;
                color: #4A3F35;
                min-width: 140px;
            }
            QComboBox:hover {
                background-color: #FDF8F0;
            }
            QComboBox::drop-down {
                border: none;
                width: 18px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFEF9;
                border: none;
                border-radius: 0;
                padding: 0px;
                margin: 0px;
                selection-background-color: #FDF6ED;
                selection-color: #8B5A2B;
                outline: none;
                alternate-background-color: #FFFEF9;
            }
            QComboBox QAbstractItemView::item {
                padding: 4px 8px;
                min-height: 20px;
                background-color: #FFFEF9;
                border: none;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #FDF8F0;
            }
        """)
        header_layout.addWidget(self.mode_combo)
        header_layout.addStretch()

        # 新建会话按钮
        self.new_chat_btn = QToolButton()
        self.new_chat_btn.setFixedSize(24, 24)
        self.new_chat_btn.setToolTip("新建会话")
        self.new_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        plus_icon_path = Path(__file__).parent.parent.parent / "assets" / "plus.svg"
        if plus_icon_path.exists():
            self.new_chat_btn.setIcon(QIcon(str(plus_icon_path)))
        else:
            self.new_chat_btn.setText("+")
        self.new_chat_btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QToolButton:hover {
                background-color: #F5EDE4;
            }
        """)
        self.new_chat_btn.clicked.connect(self._on_new_chat)
        header_layout.addWidget(self.new_chat_btn)

        # 历史会话按钮
        self.history_btn = QToolButton()
        self.history_btn.setFixedSize(24, 24)
        self.history_btn.setToolTip("历史会话")
        self.history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        history_icon_path = Path(__file__).parent.parent.parent / "assets" / "history.svg"
        if history_icon_path.exists():
            self.history_btn.setIcon(QIcon(str(history_icon_path)))
        else:
            self.history_btn.setText("⏱")
        self.history_btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QToolButton:hover {
                background-color: #F5EDE4;
            }
        """)
        self.history_btn.clicked.connect(self._on_history)
        header_layout.addWidget(self.history_btn)

        layout.addLayout(header_layout)

        # ========== 消息列表 ==========
        self.message_list = QListWidget()
        self.message_list.setStyleSheet("""
            QListWidget {
                background-color: #FFFEF9;
                border: 1px solid #E8DFD5;
                border-radius: 8px;
                padding: 4px;
            }
            QListWidget::item {
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
            /* 隐藏垂直滚动条 */
            QListWidget::vertical-scroll-bar {
                width: 0px;
                background: transparent;
            }
        """)
        # 隐藏垂直滚动条但保持滚动功能
        self.message_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.message_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # 添加右键菜单
        self.message_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.message_list.customContextMenuRequested.connect(self._show_message_context_menu)
        layout.addWidget(self.message_list, 1)

        # ========== 输入区域（温暖主题） ==========
        input_container = QFrame()
        input_container.setStyleSheet("""
            QFrame {
                background-color: #FFFEF9;
                border: 1px solid #E8DFD5;
                border-radius: 12px;
            }
        """)
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(12, 10, 12, 10)
        input_layout.setSpacing(8)

        # ---- 输入框内部顶部工具栏（笔记显示） ----
        input_top_toolbar = QHBoxLayout()
        input_top_toolbar.setSpacing(8)

        # 当前文件/笔记显示
        self.current_file_label = QLabel("📄 未选择笔记")
        self.current_file_label.setStyleSheet("""
            QLabel {
                color: #8B7B6B;
                font-size: 12px;
            }
        """)
        input_top_toolbar.addWidget(self.current_file_label)

        # 图钉和关闭按钮容器（紧凑排列）
        note_controls = QHBoxLayout()
        note_controls.setSpacing(2)

        # 图钉图标（切换是否使用笔记上下文）
        self.eye_btn = QToolButton()
        self.eye_btn.setCheckable(True)
        self.eye_btn.setChecked(True)
        self.eye_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.eye_btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: none;
                color: #8B7B6B;
                font-size: 12px;
            }
            QToolButton:checked {
                color: #D4A574;
            }
            QToolButton:hover {
                color: #8B5A2B;
            }
        """)
        self.eye_btn.setText("📌")
        self.eye_btn.clicked.connect(self._on_eye_toggled)
        note_controls.addWidget(self.eye_btn)

        # 关闭按钮（清除当前笔记引用）
        self.close_note_btn = QToolButton()
        self.close_note_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_note_btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: none;
                color: #8B7B6B;
                font-size: 12px;
            }
            QToolButton:hover {
                color: #C75450;
            }
        """)
        self.close_note_btn.setText("✕")
        self.close_note_btn.clicked.connect(self._on_close_note)
        note_controls.addWidget(self.close_note_btn)

        input_top_toolbar.addLayout(note_controls)

        input_top_toolbar.addStretch()

        # MCP 工具选择器（放在右上角）
        self.mcp_tool_selector = MCPToolSelector()
        self.mcp_tool_selector.setMinimumWidth(100)
        input_top_toolbar.addWidget(self.mcp_tool_selector)

        input_layout.addLayout(input_top_toolbar)

        # ---- 输入框 ----
        self.input_edit = QTextEdit()
        self.input_edit.setMaximumHeight(80)
        self.input_edit.setPlaceholderText("输入消息...")
        self.input_edit.setStyleSheet("""
            QTextEdit {
                background-color: #FFFEF9;
                border: 2px solid #E8DFD5;
                border-radius: 10px;
                font-size: 13px;
                color: #3D3428;
                padding: 10px 16px;
                line-height: 1.6;
            }
            QTextEdit:focus {
                border-color: #D4A574;
                background-color: #FFFDF8;
            }
            QTextEdit:hover {
                border-color: #D4C4B0;
            }
        """)
        input_layout.addWidget(self.input_edit)

        # ---- 底部工具栏（模型选择、Image、Chat、Vault Chat） ----
        bottom_toolbar = QHBoxLayout()
        bottom_toolbar.setSpacing(8)

        # 模型选择器
        self.model_selector = ModelSelector()
        self.model_selector.setMinimumWidth(120)
        bottom_toolbar.addWidget(self.model_selector)

        bottom_toolbar.addStretch()

        # Image 按钮
        self.image_btn = QPushButton("📎 Image")
        self.image_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.image_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #8B7B6B;
                font-size: 12px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                color: #8B5A2B;
            }
        """)
        bottom_toolbar.addWidget(self.image_btn)

        input_layout.addLayout(bottom_toolbar)
        layout.addWidget(input_container)

    def _connect_signals(self) -> None:
        """连接信号"""
        self._mcp_manager.tools_updated.connect(self._on_mcp_tools_updated)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        self.model_selector.model_changed.connect(self._on_model_changed)
        self.mcp_tool_selector.tools_changed.connect(self._on_mcp_tools_changed)
        # 输入框回车键发送（Ctrl+Enter 换行）
        self.input_edit.installEventFilter(self)

    def _init_mcp_tools(self) -> None:
        """初始化 MCP 工具列表"""
        tool_names: list[str] = []
        servers = self._mcp_manager.get_servers()

        for server_name, server in servers.items():
            for tool in server.tools:
                tool_names.append(tool.name)

        self.mcp_tool_selector.set_tools(tool_names)

    def _load_mcp_servers(self) -> None:
        """加载并启动 MCP 服务器"""
        config = get_config()
        mcp_config = config.get("mcp", {})

        if not mcp_config.get("enabled", False):
            return

        servers_config = mcp_config.get("servers", {})

        if not servers_config:
            return

        # 加载服务器配置
        self._mcp_manager.load_servers(servers_config)

        # 启动所有服务器
        self._mcp_manager.start_all_servers()

    def _on_mcp_tools_changed(self, selected_tools: list[str]) -> None:
        """MCP 工具选择改变"""
        self._selected_mcp_tools = selected_tools

    def _on_model_changed(self, model: str) -> None:
        """模型改变"""
        config = get_config()
        provider = config.ai_provider
        ai_config = config.get_ai_config(provider)
        ai_config["model"] = model
        config.set_ai_config(provider, ai_config)
        config.save()

        # 更新客户端的模型
        if self._client is not None:
            self._client.model = model

    def _on_mode_changed(self, mode: str) -> None:
        """模式改变"""
        self._messages = []
        self.message_list.clear()

        if mode == self.MODE_SKILL:
            self.input_edit.setPlaceholderText("点击发送按钮生成 SKILL.md...")
        else:
            if self._current_note_title:
                self.input_edit.setPlaceholderText(f"关于「{self._current_note_title}」提问，或直接开始对话...")
            else:
                self.input_edit.setPlaceholderText("开始对话...")

    def _load_model_list(self) -> None:
        """异步加载模型列表"""
        config = get_config()
        provider = config.ai_provider
        ai_config = config.get_ai_config(provider)
        current_model = ai_config.get("model", "")

        # 立即显示当前模型（从配置）
        if current_model:
            self.model_selector.set_current_model(current_model)

        # 异步加载模型列表
        self.model_selector.show_loading()

        if self._model_worker is not None:
            self._model_worker.requestInterruption()
            self._model_worker.wait(1000)
            self._model_worker = None

        # 如果 client 为 None，不需要启动线程
        if self._client is None:
            self.model_selector.hide_loading()
            return

        self._model_worker = ModelListWorker(self._client, self)
        self._model_worker.models_loaded.connect(self._on_models_loaded)
        self._model_worker.load_error.connect(self._on_models_load_error)
        self._model_worker.finished.connect(self._on_model_worker_finished)
        self._model_worker.start()

    def _on_model_worker_finished(self) -> None:
        """模型加载线程完成"""
        if self._model_worker is not None:
            self._model_worker.deleteLater()
            self._model_worker = None

    def _on_models_loaded(self, models: list[str]) -> None:
        """模型列表加载成功"""
        self.model_selector.hide_loading()
        self.model_selector.set_models(models)

        config = get_config()
        provider = config.ai_provider
        ai_config = config.get_ai_config(provider)
        current_model = ai_config.get("model", "")
        if current_model:
            self.model_selector.set_current_model(current_model)

    def _on_models_load_error(self, error: str) -> None:
        """模型列表加载失败"""
        self.model_selector.show_error("加载失败")

    def eventFilter(self, obj, event) -> bool:
        """事件过滤器 - 处理回车键发送"""
        if obj == self.input_edit and event.type() == QEvent.Type.KeyPress:
            key_event = event
            if key_event.key() == Qt.Key.Key_Return or key_event.key() == Qt.Key.Key_Enter:
                # 检查是否按下了 Ctrl 或 Shift（用于换行）
                if key_event.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
                    # 插入换行符
                    self.input_edit.insertPlainText("\n")
                    return True
                else:
                    # 发送消息
                    self._on_send()
                    return True
        return super().eventFilter(obj, event)

    def resizeEvent(self, event) -> None:
        """窗口大小变化时重新计算所有消息项的高度"""
        super().resizeEvent(event)
        # 使用 QTimer 延迟执行，确保 resize 完成后再计算
        # 延迟时间增加到 200ms，减少频繁调用
        from PySide6.QtCore import QTimer
        QTimer.singleShot(200, self._adjust_all_message_heights)

    def _adjust_all_message_heights(self) -> None:
        """调整所有消息项的高度和换行"""
        # 获取消息列表的可用宽度
        list_width = self.message_list.viewport().width()
        # 减去列表内边距
        available_width = list_width - 8  # padding: 4px * 2
        
        for i in range(self.message_list.count()):
            item = self.message_list.item(i)
            if item:
                data = item.data(Qt.ItemDataRole.UserRole)
                if data and isinstance(data, dict):
                    widget = data.get("widget")
                    if widget and isinstance(widget, MessageItemWidget):
                        # 关键：强制设置 widget 的最大宽度，让它重新布局
                        # QListWidget.setItemWidget 设置的 widget 大小是固定的
                        # 需要手动限制其宽度才能触发重新布局
                        widget.setMaximumWidth(available_width)
                        # 计算内容区域宽度：总宽度 - 头像 - 间距 - 边距
                        # 头像24px + 间距8px + 左右边距16px = 48px
                        content_width = available_width - 48
                        if content_width > 0:
                            widget._update_height(content_width)
                        # 更新 item 的 size hint
                        item.setSizeHint(widget.sizeHint())
        # 强制刷新列表视图
        self.message_list.viewport().update()

    def _on_mcp_tools_updated(self, server_name: str, tools: list) -> None:
        """MCP 工具更新"""
        # 直接从 manager 获取所有工具并更新选择器
        all_tools = self._mcp_manager.get_all_tools()
        tool_names = [tool.name for tool in all_tools]
        self.mcp_tool_selector.set_tools(tool_names)

    def _on_eye_toggled(self) -> None:
        """眼睛按钮切换"""
        self._use_note_context = self.eye_btn.isChecked()
        if self._current_note_title:
            if self._use_note_context:
                self.current_file_label.setStyleSheet("""
                    QLabel {
                        color: #5A4A3A;
                        font-size: 12px;
                    }
                """)
            else:
                self.current_file_label.setStyleSheet("""
                    QLabel {
                        color: #8B7B6B;
                        font-size: 12px;
                    }
                """)

    def _on_close_note(self) -> None:
        """关闭当前笔记引用"""
        self._current_note_title = ""
        self._current_note_content = ""
        self._use_note_context = False
        self.eye_btn.setChecked(False)
        self.current_file_label.setText("📄 未选择笔记")
        self.current_file_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 12px;
            }
        """)

    def _on_new_chat(self) -> None:
        """新建会话"""
        # 清空消息列表
        self.message_list.clear()
        # 重置当前响应
        self._current_response = ""
        # 清空输入框
        self.input_edit.clear()
        # 如果有当前笔记，保持笔记上下文
        if self._current_note_title:
            self.input_edit.setPlaceholderText(f"关于「{self._current_note_title}」提问，或直接开始对话...")
        else:
            self.input_edit.setPlaceholderText("开始对话...")

    def _on_history(self) -> None:
        """历史会话 - 暂显示提示"""
        # TODO: 实现历史会话功能
        from PySide6.QtWidgets import QMessageBox
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("历史会话")
        msg_box.setText("历史会话功能即将上线")
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def _load_client(self) -> None:
        """加载 AI 客户端"""
        config = get_config()
        provider = config.ai_provider
        ai_config = config.get_ai_config(provider)
        try:
            self._client = create_client(provider, ai_config)
        except Exception:
            self._client = None

    def _on_send(self) -> None:
        """发送消息"""
        user_input = self.input_edit.toPlainText().strip()
        if not user_input:
            return

        self._add_message("用户", user_input, is_user=True)
        self.input_edit.clear()
        self._messages.append({"role": "user", "content": user_input})
        self._send_to_ai_stream()

    def _add_message(self, sender: str, content: str, is_user: bool = False) -> QListWidgetItem:
        """添加消息到列表"""
        item = QListWidgetItem()
        # 创建自定义消息组件
        message_widget = MessageItemWidget(sender, content, is_user)
        item.setData(Qt.ItemDataRole.UserRole, {"sender": sender, "content": content, "is_user": is_user, "widget": message_widget})
        self.message_list.addItem(item)
        self.message_list.setItemWidget(item, message_widget)
        # 延迟设置 size hint，确保 widget 已经布局完成
        # 延迟时间需要大于 MessageItemWidget 内部的 _update_height 延迟时间
        from PySide6.QtCore import QTimer
        QTimer.singleShot(150, lambda: item.setSizeHint(message_widget.sizeHint()))
        self.message_list.scrollToBottom()
        return item

    def _show_thinking(self) -> None:
        """显示思考中状态"""
        self._thinking_item = QListWidgetItem()
        # 创建思考中组件
        thinking_widget = MessageItemWidget("AI", "⋯ 思考中 ⋯", is_user=False)
        self._thinking_item.setData(Qt.ItemDataRole.UserRole, {"thinking": True, "widget": thinking_widget})
        self.message_list.addItem(self._thinking_item)
        self.message_list.setItemWidget(self._thinking_item, thinking_widget)
        # 延迟设置 size hint，保存引用避免 lambda 捕获问题
        item = self._thinking_item
        from PySide6.QtCore import QTimer
        QTimer.singleShot(150, lambda: item.setSizeHint(thinking_widget.sizeHint()) if item else None)
        self.message_list.scrollToBottom()

    def _hide_thinking(self) -> None:
        """隐藏思考中状态"""
        if self._thinking_item:
            row = self.message_list.row(self._thinking_item)
            if row >= 0:
                self.message_list.takeItem(row)
            self._thinking_item = None

    def _send_to_ai_stream(self) -> None:
        """发送消息到 AI（流式）"""
        if self._client is None:
            self._add_message("系统", "请先配置 AI 设置", is_user=False)
            return

        if not self._client.validate_config():
            self._add_message("系统", "AI 配置无效，请检查 API Key", is_user=False)
            return

        self._current_response = ""
        self._show_thinking()

        messages = self._messages.copy()
        if self._use_note_context and self._current_note_content:
            context = f"""当前笔记：「{self._current_note_title}」

笔记内容：
{self._current_note_content}

---
请基于以上笔记内容回答用户的问题。如果问题与笔记无关，请正常回答用户的问题。"""
            messages = [{"role": "system", "content": context}] + messages

        # 获取选中的工具
        selected_tools = self._get_selected_mcp_tools()

        self._worker = StreamChatWorker(
            self._client,
            messages,
            tools=selected_tools,
            mcp_manager=self._mcp_manager,
            use_stream=True,
        )
        self._worker.thinking_started.connect(lambda: None)
        self._worker.thinking_ended.connect(self._hide_thinking)
        self._worker.chunk_received.connect(self._on_chunk_received)
        self._worker.tool_call_started.connect(self._on_tool_call_started)
        self._worker.tool_call_result.connect(self._on_tool_call_result)
        self._worker.finished_with_error.connect(self._on_error)
        self._worker.finished.connect(self._on_stream_finished)
        self._worker.start()

    def _get_selected_mcp_tools(self) -> list[MCPTool]:
        """获取选中的 MCP 工具列表"""
        selected_names = set(self._selected_mcp_tools)
        tools = []
        for server in self._mcp_manager.get_servers().values():
            for tool in server.tools:
                if tool.name in selected_names:
                    tools.append(tool)
        return tools

    @Slot(str, dict)
    def _on_tool_call_started(self, tool_name: str, arguments: dict) -> None:
        """工具调用开始"""
        self._add_message("系统", f"🔧 调用工具: {tool_name}", is_user=False)

    @Slot(str, str, bool)
    def _on_tool_call_result(self, tool_name: str, result: str, is_error: bool) -> None:
        """工具调用结果"""
        status = "❌" if is_error else "✅"
        self._add_message("系统", f"{status} {tool_name}: {result[:200]}{'...' if len(result) > 200 else ''}", is_user=False)

    @Slot(str)
    def _on_chunk_received(self, chunk: str) -> None:
        """收到内容片段"""
        self._current_response += chunk
        target_item = None
        if self._thinking_item:
            # 更新思考中项的内容
            data = self._thinking_item.data(Qt.ItemDataRole.UserRole)
            widget = data.get("widget") if data else None
            if widget and isinstance(widget, MessageItemWidget):
                widget.update_content(self._current_response)
            self._thinking_item.setData(Qt.ItemDataRole.UserRole, {
                "sender": "AI",
                "content": self._current_response,
                "is_user": False,
                "widget": widget
            })
            target_item = self._thinking_item
            self._thinking_item = None
        else:
            for i in range(self.message_list.count() - 1, -1, -1):
                item = self.message_list.item(i)
                data = item.data(Qt.ItemDataRole.UserRole)
                if data and not data.get("is_user", False) and not data.get("thinking", False):
                    widget = data.get("widget")
                    if widget and isinstance(widget, MessageItemWidget):
                        widget.update_content(self._current_response)
                    item.setData(Qt.ItemDataRole.UserRole, {
                        "sender": "AI",
                        "content": self._current_response,
                        "is_user": False,
                        "widget": widget
                    })
                    target_item = item
                    break
        # 更新 QListWidgetItem 的大小提示
        if target_item:
            widget = target_item.data(Qt.ItemDataRole.UserRole).get("widget")
            if widget:
                # 强制更新 widget 高度后再设置 size hint
                widget._update_height()
                target_item.setSizeHint(widget.sizeHint())
        self.message_list.scrollToBottom()

    @Slot()
    def _on_stream_finished(self) -> None:
        """流式响应完成"""
        if self._current_response:
            self._messages.append({"role": "assistant", "content": self._current_response})
        self._worker = None

    @Slot(str)
    def _on_error(self, error: str) -> None:
        """发生错误"""
        self._hide_thinking()
        self._add_message("错误", error, is_user=False)

    def set_current_note(self, title: str, content: str) -> None:
        """设置当前笔记内容"""
        self._current_note_title = title
        self._current_note_content = content
        self._use_note_context = True
        self.eye_btn.setChecked(True)

        if title:
            self.current_file_label.setText(f"📄 {title}")
            self.current_file_label.setStyleSheet("""
                QLabel {
                    color: #5A4A3A;
                    font-size: 12px;
                }
            """)
        else:
            self.current_file_label.setText("📄 未选择笔记")
            self.current_file_label.setStyleSheet("""
                QLabel {
                    color: #8B7B6B;
                    font-size: 12px;
                }
            """)

    def reload_client(self) -> None:
        """重新加载客户端"""
        self._load_client()
        self._load_model_list()

    def _show_message_context_menu(self, pos: QPoint) -> None:
        """显示消息右键菜单"""
        item = self.message_list.itemAt(pos)
        if not item:
            return

        # 获取消息数据
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data or not isinstance(data, dict):
            return

        # 跳过思考中的消息
        if data.get("thinking"):
            return

        content = data.get("content", "")
        if not content:
            return

        # 创建菜单
        menu = QMenu(self)
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

        # 复制内容动作
        copy_action = QAction("复制内容", self)
        copy_action.triggered.connect(lambda: self._copy_message_content(content))
        menu.addAction(copy_action)

        menu.exec(self.message_list.mapToGlobal(pos))

    def _copy_message_content(self, content: str) -> None:
        """复制消息内容到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(content)

    def cleanup(self) -> None:
        """清理资源"""
        if self._worker is not None:
            self._worker.requestInterruption()
            if not self._worker.wait(2000):
                self._worker.terminate()
                self._worker.wait()
            self._worker = None

        if self._model_worker is not None:
            self._model_worker.requestInterruption()
            if not self._model_worker.wait(2000):
                self._model_worker.terminate()
                self._model_worker.wait()
            self._model_worker = None
