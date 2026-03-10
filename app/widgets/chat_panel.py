"""AI 对话面板模块

提供 SKILL 生成、笔记问答和通用对话功能。
"""

from typing import Any

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..ai.client import create_client
from ..core.config import get_config


class ChatWorker(QThread):
    """AI 聊天工作线程"""

    response_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, client: Any, messages: list[dict[str, str]]):
        super().__init__()
        self.client = client
        self.messages = messages

    def run(self) -> None:
        """运行聊天请求"""
        try:
            response = self.client.chat(self.messages)
            self.response_ready.emit(response)
        except Exception as e:
            self.error_occurred.emit(str(e))


class ChatPanel(QWidget):
    """AI 对话面板"""

    generate_skill_requested = Signal()

    MODE_SKILL = "生成 SKILL"
    MODE_QA = "笔记问答"
    MODE_CHAT = "通用对话"

    def __init__(self):
        super().__init__()

        self._client: Any = None
        self._messages: list[dict[str, str]] = []
        self._worker: ChatWorker | None = None

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

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([self.MODE_SKILL, self.MODE_QA, self.MODE_CHAT])
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
            self.input_edit.setPlaceholderText("输入关于当前笔记的问题...")
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

        # 发送到 AI
        self._send_to_ai()

    @Slot()
    def _on_clear(self) -> None:
        """清空对话"""
        self._messages = []
        self.message_list.clear()

    def _add_message(self, sender: str, content: str, is_user: bool = False) -> None:
        """添加消息到列表"""
        item = QListWidgetItem()

        # 格式化消息
        prefix = "👤 " if is_user else "🤖 "
        display_text = f"{prefix}{sender}:\n{content}"

        item.setText(display_text)
        item.setData(Qt.ItemDataRole.UserRole, {"sender": sender, "content": content, "is_user": is_user})

        self.message_list.addItem(item)
        self.message_list.scrollToBottom()

    def _send_to_ai(self) -> None:
        """发送消息到 AI"""
        if self._client is None:
            self._add_message("系统", "请先配置 AI 设置", is_user=False)
            return

        if not self._client.validate_config():
            self._add_message("系统", "AI 配置无效，请检查 API Key", is_user=False)
            return

        self.send_button.setEnabled(False)

        self._worker = ChatWorker(self._client, self._messages)
        self._worker.response_ready.connect(self._on_response)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    @Slot(str)
    def _on_response(self, response: str) -> None:
        """收到响应"""
        self._add_message("AI", response, is_user=False)
        self._messages.append({"role": "assistant", "content": response})

    @Slot(str)
    def _on_error(self, error: str) -> None:
        """发生错误"""
        self._add_message("错误", error, is_user=False)

    @Slot()
    def _on_finished(self) -> None:
        """请求完成"""
        self.send_button.setEnabled(True)

    def generate_skill(self, note_content: str) -> None:
        """生成 SKILL.md"""
        if self._client is None or not self._client.validate_config():
            self._add_message("系统", "请先配置 AI 设置", is_user=False)
            return

        self._add_message("用户", "生成 SKILL.md", is_user=True)

        # 构建提示
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

        self.send_button.setEnabled(False)

        self._worker = ChatWorker(self._client, messages)
        self._worker.response_ready.connect(self._on_skill_response)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    @Slot(str)
    def _on_skill_response(self, response: str) -> None:
        """收到 SKILL 响应"""
        self._add_message("AI", f"生成的 SKILL:\n\n{response}", is_user=False)

    def reload_client(self) -> None:
        """重新加载客户端"""
        self._load_client()