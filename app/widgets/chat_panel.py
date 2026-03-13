"""AI 对话面板模块

提供 SKILL 生成、笔记问答和通用对话功能。
支持流式输出和思考状态显示。
"""

from typing import Any

from PySide6.QtCore import Qt, QThread, Signal, Slot, QPoint
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QListView,
)

from ..ai.client import create_client
from ..core.config import get_config


class NoBorderComboBox(QComboBox):
    """无边框下拉框 - 解决 Windows 平台下拉列表黑边问题"""

    def __init__(self, parent=None):
        super().__init__(parent)

    def showPopup(self) -> None:
        """显示下拉列表时移除容器边框"""
        super().showPopup()

        # 获取下拉列表容器窗口
        popup = self.findChild(QWidget, "qt_combobox_popup")
        if popup:
            # 设置无边框窗口标志，移除 Windows 系统黑边
            popup.setWindowFlags(
                popup.windowFlags() |
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.NoDropShadowWindowHint
            )
            popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # 同时处理 QFrame 子控件
        frames = self.findChildren(QFrame)
        for frame in frames:
            frame.setLineWidth(0)
            frame.setMidLineWidth(0)
            frame.setFrameShape(QFrame.Shape.NoFrame)

    def paintEvent(self, event):
        """自定义绘制事件，绘制下拉箭头"""
        super().paintEvent(event)

        # 绘制下拉箭头
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 计算箭头位置（右侧区域）
        arrow_x = self.width() - 14
        arrow_y = self.height() // 2
        arrow_size = 5

        # 设置颜色
        color = QColor(0x4A, 0x3F, 0x35)  # #4A3F35
        painter.setPen(QPen(color, 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # 绘制 V 形箭头
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


class StreamChatWorker(QThread):
    """流式 AI 聊天工作线程"""

    chunk_received = Signal(str)  # 收到内容片段
    thinking_started = Signal()  # 开始思考
    thinking_ended = Signal()  # 思考结束
    finished_with_error = Signal(str)  # 完成但出错

    def __init__(self, client: Any, messages: list[dict[str, str]], use_stream: bool = True):
        super().__init__()
        self.client = client
        self.messages = messages
        self.use_stream = use_stream

    def run(self) -> None:
        """运行聊天请求"""
        try:
            if self.use_stream:
                self.thinking_started.emit()
                full_response = ""
                for chunk in self.client.chat_stream(self.messages):
                    full_response += chunk
                    self.chunk_received.emit(chunk)
                self.thinking_ended.emit()
            else:
                self.thinking_started.emit()
                response = self.client.chat(self.messages)
                self.thinking_ended.emit()
                self.chunk_received.emit(response)
        except Exception as e:
            self.finished_with_error.emit(str(e))


class ChatPanel(QWidget):
    """AI 对话面板"""

    generate_skill_requested = Signal()

    MODE_SKILL = "生成 SKILL"
    MODE_QA = "笔记问答"
    MODE_CHAT = "通用对话"

    def __init__(self):
        super().__init__()
        self.setObjectName("chat_panel")  # 设置对象名称用于样式匹配

        self._client: Any = None
        self._messages: list[dict[str, str]] = []
        self._worker: StreamChatWorker | None = None
        self._current_note_content: str = ""
        self._current_note_title: str = ""
        self._current_response: str = ""  # 当前正在生成的响应
        self._thinking_item: QListWidgetItem | None = None  # 思考中提示项

        self._init_ui()
        self._connect_signals()
        self._load_client()

    def _init_ui(self) -> None:
        """初始化界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # 模式选择
        mode_layout = QHBoxLayout()
        mode_label = QLabel("模式:")
        mode_layout.addWidget(mode_label)

        self.mode_combo = NoBorderComboBox()
        # 创建 QListView 并直接设置样式（Windows 平台需要）
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
        self.mode_combo.addItems([self.MODE_SKILL, self.MODE_QA, self.MODE_CHAT])
        # 扁平简约风格样式（直角紧凑）
        # 注意：QComboBox QAbstractItemView 的 border 设置为 none 以去除 Windows 上的黑边
        self.mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #FFFEF9;
                border: 1px solid #E8DFD5;
                border-radius: 0;
                padding: 2px 6px;
                padding-right: 18px;
                color: #4A3F35;
                min-width: 100px;
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
        mode_layout.addWidget(self.mode_combo)

        layout.addLayout(mode_layout)

        # 消息列表
        self.message_list = QListWidget()
        layout.addWidget(self.message_list, 1)

        # 输入区域
        self.input_edit = QTextEdit()
        self.input_edit.setMaximumHeight(100)
        self.input_edit.setPlaceholderText("输入消息...")
        layout.addWidget(self.input_edit)

        # 按钮区域
        button_layout = QHBoxLayout()

        self.send_button = QPushButton("发送")
        button_layout.addWidget(self.send_button)

        self.clear_button = QPushButton("清空")
        button_layout.addWidget(self.clear_button)

        layout.addLayout(button_layout)

    def _connect_signals(self) -> None:
        """连接信号"""
        self.send_button.clicked.connect(self._on_send)
        self.clear_button.clicked.connect(self._on_clear)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)

    def _load_client(self) -> None:
        """加载 AI 客户端"""
        config = get_config()
        provider = config.ai_provider
        ai_config = config.get_ai_config(provider)

        try:
            self._client = create_client(provider, ai_config)
        except Exception:
            self._client = None

    def _on_mode_changed(self, mode: str) -> None:
        """模式改变"""
        self._messages = []
        self.message_list.clear()

        if mode == self.MODE_SKILL:
            self.input_edit.setPlaceholderText("点击发送按钮生成 SKILL.md...")
        elif mode == self.MODE_QA:
            if self._current_note_title:
                self.input_edit.setPlaceholderText(f"关于「{self._current_note_title}」提问...")
            else:
                self.input_edit.setPlaceholderText("请先选择一篇笔记...")
        else:
            self.input_edit.setPlaceholderText("开始对话...")

    @Slot()
    def _on_send(self) -> None:
        """发送消息"""
        mode = self.mode_combo.currentText()

        if mode == self.MODE_SKILL:
            self.generate_skill_requested.emit()
            return

        user_input = self.input_edit.toPlainText().strip()
        if not user_input:
            return

        # 显示用户消息
        self._add_message("用户", user_input, is_user=True)
        self.input_edit.clear()

        # 添加到消息历史
        self._messages.append({"role": "user", "content": user_input})

        # 发送到 AI（流式）
        self._send_to_ai_stream()

    @Slot()
    def _on_clear(self) -> None:
        """清空对话"""
        self._messages = []
        self.message_list.clear()

    def _add_message(self, sender: str, content: str, is_user: bool = False) -> QListWidgetItem:
        """添加消息到列表"""
        item = QListWidgetItem()

        prefix = "👤 " if is_user else "🤖 "
        display_text = f"{prefix}{sender}:\n{content}"

        item.setText(display_text)
        item.setData(Qt.ItemDataRole.UserRole, {"sender": sender, "content": content, "is_user": is_user})

        self.message_list.addItem(item)
        self.message_list.scrollToBottom()
        return item

    def _show_thinking(self) -> None:
        """显示思考中状态"""
        self._thinking_item = QListWidgetItem("🤖 AI: ⋯ 思考中 ⋯")
        self._thinking_item.setData(Qt.ItemDataRole.UserRole, {"thinking": True})
        self.message_list.addItem(self._thinking_item)
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

        self.send_button.setEnabled(False)
        self._current_response = ""

        # 显示思考中状态
        self._show_thinking()

        # 构建消息
        messages = self._messages.copy()
        if self.mode_combo.currentText() == self.MODE_QA and self._current_note_content:
            context = f"""当前笔记：「{self._current_note_title}」

笔记内容：
{self._current_note_content}

---
请基于以上笔记内容回答用户的问题。"""
            messages = [{"role": "system", "content": context}] + messages

        self._worker = StreamChatWorker(self._client, messages, use_stream=True)
        self._worker.thinking_started.connect(lambda: None)  # 已在上面显示
        self._worker.thinking_ended.connect(self._hide_thinking)
        self._worker.chunk_received.connect(self._on_chunk_received)
        self._worker.finished_with_error.connect(self._on_error)
        self._worker.finished.connect(self._on_stream_finished)
        self._worker.start()

    @Slot(str)
    def _on_chunk_received(self, chunk: str) -> None:
        """收到内容片段"""
        self._current_response += chunk

        # 更新或创建 AI 消息项
        if self._thinking_item:
            # 将思考项转换为响应项
            self._thinking_item.setText(f"🤖 AI:\n{self._current_response}")
            self._thinking_item.setData(Qt.ItemDataRole.UserRole, {
                "sender": "AI",
                "content": self._current_response,
                "is_user": False
            })
            self._thinking_item = None  # 不再是思考项
        else:
            # 更新最后一个 AI 消息
            for i in range(self.message_list.count() - 1, -1, -1):
                item = self.message_list.item(i)
                data = item.data(Qt.ItemDataRole.UserRole)
                if data and not data.get("is_user", False) and not data.get("thinking", False):
                    item.setText(f"🤖 AI:\n{self._current_response}")
                    item.setData(Qt.ItemDataRole.UserRole, {
                        "sender": "AI",
                        "content": self._current_response,
                        "is_user": False
                    })
                    break

        self.message_list.scrollToBottom()

    @Slot()
    def _on_stream_finished(self) -> None:
        """流式响应完成"""
        self.send_button.setEnabled(True)

        # 将完整响应添加到消息历史
        if self._current_response:
            self._messages.append({"role": "assistant", "content": self._current_response})

        self._worker = None

    @Slot(str)
    def _on_error(self, error: str) -> None:
        """发生错误"""
        self._hide_thinking()
        self._add_message("错误", error, is_user=False)
        self.send_button.setEnabled(True)

    def generate_skill(self, note_content: str) -> None:
        """生成 SKILL.md"""
        if self._client is None or not self._client.validate_config():
            self._add_message("系统", "请先配置 AI 设置", is_user=False)
            return

        self._add_message("用户", "生成 SKILL.md", is_user=True)
        self._show_thinking()

        prompt = f"""请分析以下笔记内容，生成一个结构化的 SKILL 描述。

笔记内容：
{note_content}

请以 YAML 格式返回，包含以下字段：
- name: 技能名称（英文 kebab-case）
- description: 简短描述
- parameters: 参数列表（如有）
- returns: 返回值描述（如有）
"""

        messages = [{"role": "user", "content": prompt}]
        self._current_response = ""

        self._worker = StreamChatWorker(self._client, messages, use_stream=True)
        self._worker.thinking_ended.connect(self._hide_thinking)
        self._worker.chunk_received.connect(self._on_chunk_received)
        self._worker.finished_with_error.connect(self._on_error)
        self._worker.finished.connect(self._on_stream_finished)
        self._worker.start()

    def set_current_note(self, title: str, content: str) -> None:
        """设置当前笔记内容"""
        self._current_note_title = title
        self._current_note_content = content

        if self.mode_combo.currentText() == self.MODE_QA:
            if title:
                self.input_edit.setPlaceholderText(f"关于「{title}」提问...")
            else:
                self.input_edit.setPlaceholderText("请先选择一篇笔记...")

    def reload_client(self) -> None:
        """重新加载客户端"""
        self._load_client()

    def cleanup(self) -> None:
        """清理资源，停止正在运行的工作线程"""
        if self._worker is not None:
            # 请求线程停止
            self._worker.requestInterruption()
            # 等待线程结束（最多等待 2 秒）
            if not self._worker.wait(2000):
                # 如果线程没有响应，强制终止
                self._worker.terminate()
                self._worker.wait()
            self._worker = None