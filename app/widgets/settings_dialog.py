"""设置对话框模块

提供 AI 配置、界面偏好设置、Git 同步配置和 MCP 工具配置界面。
"""

import json
import re
from pathlib import Path
from typing import Any

from PySide6.QtCore import Slot, Qt, QPoint, QTimer, QThread, Signal, QSize
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen, QTextCharFormat, QFont, QSyntaxHighlighter, QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QLabel,
    QListView,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QScrollArea,
    QPlainTextEdit,
    QApplication,
)

from ..core.config import get_config
from ..core.system_config import get_system_config_instance
from ..mcp.client import validate_mcp_server_config, test_mcp_server_connection, parse_mcp_config
from .common import NoBorderComboBox


class JsonHighlighter(QSyntaxHighlighter):
    """JSON 语法高亮器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_formats()

    def _init_formats(self):
        self.key_format = QTextCharFormat()
        self.key_format.setForeground(QColor("#8B5A2B"))
        self.key_format.setFontWeight(QFont.Weight.Bold)

        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#2E8B57"))

        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor("#4169E1"))

        self.boolean_format = QTextCharFormat()
        self.boolean_format.setForeground(QColor("#D4A574"))

        self.null_format = QTextCharFormat()
        self.null_format.setForeground(QColor("#808080"))

        self.bracket_format = QTextCharFormat()
        self.bracket_format.setForeground(QColor("#4A3F35"))

    def highlightBlock(self, text: str) -> None:
        patterns = [
            (r'"[^"\\]*(?:\\.[^"\\]*)*"\s*:', self.key_format),
            (r'"[^"\\]*(?:\\.[^"\\]*)*"', self.string_format),
            (r'\b-?\d+\.?\d*\b', self.number_format),
            (r'\b(true|false)\b', self.boolean_format),
            (r'\bnull\b', self.null_format),
            (r'[\[\]{}]', self.bracket_format),
        ]

        for pattern, fmt in patterns:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


class MCPServerTestWorker(QThread):
    """MCP 服务器测试工作线程"""
    finished = Signal(bool, str, list)

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self._sys_config = get_system_config_instance()

    def run(self) -> None:
        success, message, tools = test_mcp_server_connection(
            self.config, 
            timeout=self._sys_config.mcp_connection_timeout
        )
        self.finished.emit(success, message, tools)


class MCPServerListItem(QWidget):
    """MCP 服务器列表项"""

    delete_requested = Signal(str)
    edit_requested = Signal(str)

    def __init__(self, name: str, config: dict, parent=None):
        super().__init__(parent)
        self.server_name = name
        self.config = config
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        name_label = QLabel(self.server_name)
        name_label.setStyleSheet("font-weight: bold; color: #3D3428; font-size: 13px;")
        layout.addWidget(name_label, 1)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        edit_btn = QPushButton()
        edit_btn.setFixedSize(24, 24)
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #E8DFD5;
            }
        """)
        edit_icon_path = Path(__file__).parent.parent.parent / "assets" / "edit.svg"
        if edit_icon_path.exists():
            edit_btn.setIcon(QIcon(str(edit_icon_path)))
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.server_name))
        btn_layout.addWidget(edit_btn)

        delete_btn = QPushButton()
        delete_btn.setFixedSize(24, 24)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #FADBD8;
            }
        """)
        delete_icon_path = Path(__file__).parent.parent.parent / "assets" / "delete.svg"
        if delete_icon_path.exists():
            delete_btn.setIcon(QIcon(str(delete_icon_path)))
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.server_name))
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)


class AddMCPDialog(QDialog):
    """添加/编辑 MCP 对话框"""

    def __init__(self, server_name: str = None, server_config: dict = None, parent=None):
        super().__init__(parent)
        self._server_name = server_name
        self._server_config = server_config
        self._test_worker: MCPServerTestWorker | None = None
        self._result_name: str | None = None
        self._result_config: dict | None = None

        self.setWindowTitle("添加 MCP" if server_name is None else f"编辑 MCP: {server_name}")
        self.setMinimumSize(500, 450)
        self.setStyleSheet("""
            QDialog {
                background-color: #FBF7F2;
            }
        """)

        self._init_ui()
        self._load_data()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        config_label = QLabel("配置 JSON:")
        config_label.setStyleSheet("font-size: 14px; color: #3D3428;")
        layout.addWidget(config_label)

        self.json_editor = QPlainTextEdit()
        self.json_editor.setPlaceholderText('在此输入 JSON 配置...')
        self.json_editor.setMinimumHeight(180)
        self.json_editor.setStyleSheet("""
            QPlainTextEdit {
                background-color: #FFFEF9;
                border: 2px solid #E8DFD5;
                border-radius: 8px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 13px;
                color: #3D3428;
            }
            QPlainTextEdit:focus {
                border-color: #D4A574;
            }
        """)
        self.json_highlighter = JsonHighlighter(self.json_editor.document())
        layout.addWidget(self.json_editor)

        example_label = QLabel(
            '支持的配置格式:\n'
            '格式1: {"server-name": {"command": "npx", "args": ["-y", "server"]}}\n'
            '格式2: {"mcpServers": {"server-name": {...}}}'
        )
        example_label.setStyleSheet("""
            QLabel {
                background-color: #F5EDE4;
                border: 1px solid #E8DFD5;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                color: #5A4A3A;
            }
        """)
        layout.addWidget(example_label)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("""
            QLabel {
                background-color: #FDECEA;
                border: 1px solid #F5B7B1;
                border-radius: 6px;
                padding: 8px;
                color: #C0392B;
                font-size: 12px;
            }
        """)
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.test_btn = QPushButton("测试连接")
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5EDE4;
                color: #5A4A3A;
                border: 1px solid #E8DFD5;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #E8DFD5;
            }
        """)
        self.test_btn.clicked.connect(self._on_test_connection)
        btn_layout.addWidget(self.test_btn)

        btn_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5EDE4;
                color: #5A4A3A;
                border: 1px solid #E8DFD5;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #E8DFD5;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.add_btn = QPushButton("添加" if self._server_name is None else "保存")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #D4A574, stop:1 #C49564);
                color: #FFFEF9;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #C49564, stop:1 #B48554);
            }
        """)
        self.add_btn.clicked.connect(self._on_add)
        btn_layout.addWidget(self.add_btn)

        layout.addLayout(btn_layout)

    def _load_data(self) -> None:
        if self._server_name:
            json_data = {self._server_name: self._server_config}
            json_str = json.dumps(json_data, indent=2, ensure_ascii=False)
            self.json_editor.setPlainText(json_str)
        else:
            self.json_editor.setPlainText('{\n  "server-name": {\n    "command": "",\n    "args": []\n  }\n}')

    def _on_test_connection(self) -> None:
        json_str = self.json_editor.toPlainText().strip()

        if not json_str:
            self._show_error("请输入 JSON 配置")
            return

        is_valid, servers, error = parse_mcp_config(json_str)
        if not is_valid:
            self._show_error(error)
            return

        if len(servers) == 0:
            self._show_error("配置中未找到服务器定义")
            return

        if len(servers) == 0:
            self._show_error("配置中未找到服务器定义")
            return

        if len(servers) > 1:
            server_names = list(servers.keys())
            self._show_error(f"配置中包含多个服务器: {', '.join(server_names)}\n请只配置一个服务器")
            return

        server_name = list(servers.keys())[0]
        server_config = servers[server_name]

        is_valid, error = validate_mcp_server_config(server_config)
        if not is_valid:
            self._show_error(f"配置验证失败: {error}")
            return

        self.test_btn.setEnabled(False)
        self.test_btn.setText("测试中...")
        self.error_label.hide()

        self._test_worker = MCPServerTestWorker(server_config, self)
        self._test_worker.finished.connect(self._on_test_finished)
        self._test_worker.start()

    def _on_test_finished(self, success: bool, message: str, tools: list) -> None:
        self.test_btn.setEnabled(True)
        self.test_btn.setText("测试连接")

        if success:
            tools_info = f"\n\n发现的工具: {', '.join(tools) if tools else '无'}"
            self._show_success(f"✓ {message}{tools_info}")
        else:
            self._show_error(f"✗ {message}")

        if self._test_worker:
            self._test_worker.deleteLater()
            self._test_worker = None

    def _on_add(self) -> None:
        json_str = self.json_editor.toPlainText().strip()

        if not json_str:
            self._show_error("请输入 JSON 配置")
            return

        is_valid, servers, error = parse_mcp_config(json_str)
        if not is_valid:
            self._show_error(error)
            return

        if len(servers) == 0:
            self._show_error("配置中未找到服务器定义")
            return

        if len(servers) > 1:
            server_names = list(servers.keys())
            self._show_error(f"配置中包含多个服务器: {', '.join(server_names)}\n请只配置一个服务器")
            return

        server_name = list(servers.keys())[0]
        server_config = servers[server_name]

        is_valid, error = validate_mcp_server_config(server_config)
        if not is_valid:
            self._show_error(f"配置验证失败: {error}")
            return

        # 重名验证
        existing_config = get_config()
        if self._server_name is None:
            # 添加模式：检查是否已存在
            if server_name in existing_config.mcp_servers:
                self._show_error(f"MCP 名称「{server_name}」已存在，请使用其他名称")
                return
        else:
            # 编辑模式：如果改名了，检查新名称是否已存在
            if server_name != self._server_name and server_name in existing_config.mcp_servers:
                self._show_error(f"MCP 名称「{server_name}」已存在，请使用其他名称")
                return

        self._result_name = server_name
        self._result_config = server_config
        self.accept()

    def get_result(self) -> tuple[str | None, dict | None]:
        return self._result_name, self._result_config

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setStyleSheet("""
            QLabel {
                background-color: #FDECEA;
                border: 1px solid #F5B7B1;
                border-radius: 6px;
                padding: 8px;
                color: #C0392B;
                font-size: 12px;
            }
        """)
        self.error_label.show()

    def _show_success(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setStyleSheet("""
            QLabel {
                background-color: #E8F5E9;
                border: 1px solid #A5D6A7;
                border-radius: 6px;
                padding: 8px;
                color: #2E7D32;
                font-size: 12px;
            }
        """)
        self.error_label.show()


class MCPConfigWidget(QWidget):
    """MCP 配置组件"""

    config_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._load_config()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        enable_group = QGroupBox("MCP 设置")
        enable_layout = QVBoxLayout(enable_group)

        self.mcp_enabled_checkbox = QCheckBox("启用 MCP (Model Context Protocol)")
        self.mcp_enabled_checkbox.setChecked(False)
        self.mcp_enabled_checkbox.stateChanged.connect(self._on_enabled_changed)
        enable_layout.addWidget(self.mcp_enabled_checkbox)

        layout.addWidget(enable_group)

        servers_group = QGroupBox("已配置的 MCP")
        servers_layout = QVBoxLayout(servers_group)

        self.servers_list = QListWidget()
        self.servers_list.setMinimumHeight(180)
        self.servers_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.servers_list.setStyleSheet("""
            QListWidget {
                background-color: #FFFEF9;
                border: 1px solid #E8DFD5;
                border-radius: 8px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 3px;
                border-radius: 4px;
                min-height: 32px;
            }
            QListWidget::item:selected {
                background-color: #FDF6ED;
            }
        """)
        servers_layout.addWidget(self.servers_list)

        add_btn_layout = QHBoxLayout()
        self.add_server_btn = QPushButton("+ 添加新 MCP")
        self.add_server_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #D4A574, stop:1 #C49564);
                color: #FFFEF9;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #C49564, stop:1 #B48554);
            }
        """)
        self.add_server_btn.clicked.connect(self._on_add_server)
        add_btn_layout.addStretch()
        add_btn_layout.addWidget(self.add_server_btn)
        servers_layout.addLayout(add_btn_layout)

        layout.addWidget(servers_group)
        layout.addStretch()

    def _load_config(self) -> None:
        config = get_config()
        self.mcp_enabled_checkbox.setChecked(config.mcp_enabled)
        self._refresh_servers_list()

    def _refresh_servers_list(self) -> None:
        self.servers_list.clear()
        config = get_config()
        servers = config.mcp_servers

        for name, server_config in servers.items():
            item = QListWidgetItem(self.servers_list)
            widget = MCPServerListItem(name, server_config)
            widget.delete_requested.connect(self._on_delete_server)
            widget.edit_requested.connect(self._on_edit_server)
            item.setSizeHint(QSize(widget.sizeHint().width(), 40))
            self.servers_list.setItemWidget(item, widget)

    def _on_enabled_changed(self) -> None:
        config = get_config()
        config.mcp_enabled = self.mcp_enabled_checkbox.isChecked()
        config.save()
        self.config_changed.emit()

    def _on_add_server(self) -> None:
        dialog = AddMCPDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, config_data = dialog.get_result()
            if name and config_data:
                app_config = get_config()
                app_config.set_mcp_server(name, config_data)
                app_config.save()
                self._refresh_servers_list()
                self.config_changed.emit()
                QMessageBox.information(
                    self,
                    "添加成功",
                    f"MCP「{name}」已添加。\n\n提示: 重启应用后生效。",
                )

    def _on_edit_server(self, name: str) -> None:
        config = get_config()
        server_config = config.get_mcp_server(name)
        if server_config:
            dialog = AddMCPDialog(server_name=name, server_config=server_config, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_name, new_config = dialog.get_result()
                if new_name and new_config:
                    app_config = get_config()
                    if new_name != name:
                        app_config.remove_mcp_server(name)
                    app_config.set_mcp_server(new_name, new_config)
                    app_config.save()
                    self._refresh_servers_list()
                    self.config_changed.emit()
                    QMessageBox.information(
                        self,
                        "保存成功",
                        f"MCP「{new_name}」已更新。\n\n提示: 重启应用后生效。",
                    )

    def _on_delete_server(self, name: str) -> None:
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除 MCP「{name}」吗？\n\n此操作无法撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            config = get_config()
            config.remove_mcp_server(name)
            config.save()
            self._refresh_servers_list()
            self.config_changed.emit()


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("设置")
        self.setMinimumSize(600, 550)

        self.setStyleSheet("""
            QDialog {
                background-color: #FBF7F2;
            }
            QComboBox {
                background-color: #FFFEF9;
                border: 2px solid #E8DFD5;
                border-radius: 8px;
                padding: 6px 12px;
                padding-right: 28px;
                font-size: 13px;
                color: #3D3428;
                min-width: 80px;
            }
            QComboBox:focus {
                border-color: #D4A574;
            }
            QComboBox:hover {
                border-color: #D4C4B0;
            }
            QComboBox:on {
                border-color: #D4A574;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
                subcontrol-position: center right;
                background: transparent;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFEF9;
                border: 2px solid #D4A574;
                border-radius: 0px;
                padding: 0px;
                selection-background-color: #FDF6ED;
                selection-color: #8B5A2B;
                outline: none;
                background: #FFFEF9;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 10px;
                border-radius: 0px;
                color: #3D3428;
                background: transparent;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #FDF8F0;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #FDF6ED;
                color: #8B5A2B;
            }
        """)

        self._init_ui()
        self._load_settings()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        ai_tab = self._create_ai_tab()
        self.tab_widget.addTab(ai_tab, "AI 设置")

        editor_tab = self._create_editor_tab()
        self.tab_widget.addTab(editor_tab, "编辑器")

        git_tab = self._create_git_tab()
        self.tab_widget.addTab(git_tab, "Git 同步")

        mcp_tab = self._create_mcp_tab()
        self.tab_widget.addTab(mcp_tab, "MCP 工具")

        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #D4A574, stop:1 #C49564);
                color: #FFFEF9;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #C49564, stop:1 #B48554);
            }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _create_ai_tab(self) -> QWidget:
        """创建 AI 设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        provider_group = QGroupBox("AI 提供商")
        provider_layout = QVBoxLayout(provider_group)

        self.provider_combo = NoBorderComboBox()
        provider_view = QListView()
        provider_view.setStyleSheet("""
            QListView {
                background-color: #FFFEF9;
                border: none;
                padding: 0px;
                outline: none;
            }
            QListView::item {
                padding: 6px 10px;
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
        self.provider_combo.setView(provider_view)
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        provider_layout.addWidget(self.provider_combo)

        layout.addWidget(provider_group)

        api_group = QGroupBox("API 配置")
        api_layout = QFormLayout(api_group)

        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("API Base URL")
        self.base_url_input.textChanged.connect(self._on_ai_config_changed)
        api_layout.addRow("Base URL:", self.base_url_input)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("API Key")
        self.api_key_input.textChanged.connect(self._on_ai_config_changed)
        api_layout.addRow("API Key:", self.api_key_input)

        self.model_combo = NoBorderComboBox()
        model_view = QListView()
        model_view.setStyleSheet("""
            QListView {
                background-color: #FFFEF9;
                border: none;
                padding: 0px;
                outline: none;
            }
            QListView::item {
                padding: 6px 10px;
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
        self.model_combo.setView(model_view)
        self.model_combo.setEditable(True)
        self.model_combo.currentTextChanged.connect(self._on_ai_config_changed)
        api_layout.addRow("模型:", self.model_combo)

        layout.addWidget(api_group)

        self._model_presets = {
            "openai": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            "anthropic": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
            "ollama": ["llama2", "llama3", "mistral", "codellama"],
        }

        layout.addStretch()

        self._save_ai_btn = QPushButton("保存 AI 设置")
        self._save_ai_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #D4A574, stop:1 #C49564);
                color: #FFFEF9;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #C49564, stop:1 #B48554);
            }
        """)
        self._save_ai_btn.clicked.connect(self._save_ai_settings)
        layout.addWidget(self._save_ai_btn)

        return widget

    def _create_editor_tab(self) -> QWidget:
        """创建编辑器设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        appearance_group = QGroupBox("外观")
        appearance_layout = QFormLayout(appearance_group)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 24)
        self.font_size_spin.setValue(14)
        self.font_size_spin.valueChanged.connect(self._on_editor_config_changed)
        appearance_layout.addRow("字体大小:", self.font_size_spin)

        layout.addWidget(appearance_group)

        autosave_group = QGroupBox("自动保存")
        autosave_layout = QFormLayout(autosave_group)

        self.autosave_interval_spin = QSpinBox()
        self.autosave_interval_spin.setRange(5, 300)
        self.autosave_interval_spin.setValue(30)
        self.autosave_interval_spin.setSuffix(" 秒")
        self.autosave_interval_spin.valueChanged.connect(self._on_editor_config_changed)
        autosave_layout.addRow("保存间隔:", self.autosave_interval_spin)

        layout.addWidget(autosave_group)

        skill_group = QGroupBox("SKILL.md 生成")
        skill_layout = QFormLayout(skill_group)

        self.auto_generate_skill_checkbox = QCheckBox("保存时自动生成 SKILL.md")
        self.auto_generate_skill_checkbox.setChecked(True)
        self.auto_generate_skill_checkbox.stateChanged.connect(self._on_editor_config_changed)
        skill_layout.addRow(self.auto_generate_skill_checkbox)

        layout.addWidget(skill_group)

        layout.addStretch()

        self._save_editor_btn = QPushButton("保存编辑器设置")
        self._save_editor_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #D4A574, stop:1 #C49564);
                color: #FFFEF9;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #C49564, stop:1 #B48554);
            }
        """)
        self._save_editor_btn.clicked.connect(self._save_editor_settings)
        layout.addWidget(self._save_editor_btn)

        return widget

    def _create_git_tab(self) -> QWidget:
        """创建 Git 同步标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        enable_group = QGroupBox("Git 同步")
        enable_layout = QVBoxLayout(enable_group)

        self.git_enabled_checkbox = QCheckBox("启用 Git 同步")
        self.git_enabled_checkbox.stateChanged.connect(self._on_git_config_changed)
        enable_layout.addWidget(self.git_enabled_checkbox)

        layout.addWidget(enable_group)

        remote_group = QGroupBox("远程仓库")
        remote_layout = QFormLayout(remote_group)

        self.git_url_input = QLineEdit()
        self.git_url_input.setPlaceholderText("git@github.com:user/repo.git 或 https://github.com/user/repo.git")
        self.git_url_input.textChanged.connect(self._on_git_config_changed)
        remote_layout.addRow("仓库地址:", self.git_url_input)

        self.git_branch_input = QLineEdit()
        self.git_branch_input.setPlaceholderText("main")
        self.git_branch_input.textChanged.connect(self._on_git_config_changed)
        remote_layout.addRow("分支:", self.git_branch_input)

        layout.addWidget(remote_group)

        sync_group = QGroupBox("同步设置")
        sync_layout = QFormLayout(sync_group)

        self.git_auto_sync_checkbox = QCheckBox("启动时自动拉取")
        self.git_auto_sync_checkbox.stateChanged.connect(self._on_git_config_changed)
        sync_layout.addRow(self.git_auto_sync_checkbox)

        self.git_commit_msg_input = QLineEdit()
        self.git_commit_msg_input.setPlaceholderText("更新笔记")
        self.git_commit_msg_input.textChanged.connect(self._on_git_config_changed)
        sync_layout.addRow("提交信息:", self.git_commit_msg_input)

        layout.addWidget(sync_group)

        hint_label = QLabel("提示: 笔记内容将同步到指定的 Git 仓库，而非项目本身。")
        hint_label.setStyleSheet("color: #8B7B6B; font-style: italic;")
        layout.addWidget(hint_label)

        layout.addStretch()

        self._save_git_btn = QPushButton("保存 Git 设置")
        self._save_git_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #D4A574, stop:1 #C49564);
                color: #FFFEF9;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #C49564, stop:1 #B48554);
            }
        """)
        self._save_git_btn.clicked.connect(self._save_git_settings)
        layout.addWidget(self._save_git_btn)

        return widget

    def _create_mcp_tab(self) -> QWidget:
        """创建 MCP 工具配置标签页"""
        self.mcp_config_widget = MCPConfigWidget()
        return self.mcp_config_widget

    def _load_settings(self) -> None:
        """加载设置"""
        config = get_config()

        self.provider_combo.addItems(["openai", "anthropic", "ollama"])
        self.provider_combo.setCurrentText(config.ai_provider)

        ai_config = config.get_ai_config()
        self.base_url_input.setText(ai_config.get("base_url", ""))
        self.api_key_input.setText(ai_config.get("api_key", ""))
        self.model_combo.setCurrentText(ai_config.get("model", ""))

        self.font_size_spin.setValue(config.editor_font_size)
        self.autosave_interval_spin.setValue(config.auto_save_interval)
        self.auto_generate_skill_checkbox.setChecked(config.auto_generate_skill)

        self.git_enabled_checkbox.setChecked(config.git_enabled)
        self.git_url_input.setText(config.git_remote_url)
        self.git_branch_input.setText(config.git_branch)
        self.git_auto_sync_checkbox.setChecked(config.git_auto_sync)
        self.git_commit_msg_input.setText(config.git_commit_message)

    def _on_provider_changed(self, provider: str) -> None:
        """提供商改变"""
        self.model_combo.clear()
        self.model_combo.addItems(self._model_presets.get(provider, []))

        default_urls = {
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com",
            "ollama": "http://localhost:11434",
        }
        self.base_url_input.setText(default_urls.get(provider, ""))

        self.api_key_input.setEnabled(provider != "ollama")

    def _on_ai_config_changed(self) -> None:
        pass

    def _on_editor_config_changed(self) -> None:
        pass

    def _on_git_config_changed(self) -> None:
        pass

    def _save_ai_settings(self) -> None:
        config = get_config()
        provider = self.provider_combo.currentText()
        config.ai_provider = provider

        ai_config = {
            "base_url": self.base_url_input.text(),
            "api_key": self.api_key_input.text(),
            "model": self.model_combo.currentText(),
        }
        config.set_ai_config(provider, ai_config)
        config.save()

        QMessageBox.information(self, "保存成功", "AI 设置已保存。")

    def _save_editor_settings(self) -> None:
        config = get_config()
        config.editor_font_size = self.font_size_spin.value()
        config.auto_save_interval = self.autosave_interval_spin.value()
        config.auto_generate_skill = self.auto_generate_skill_checkbox.isChecked()
        config.save()

        QMessageBox.information(self, "保存成功", "编辑器设置已保存。")

    def _save_git_settings(self) -> None:
        config = get_config()
        config.git_enabled = self.git_enabled_checkbox.isChecked()
        config.git_remote_url = self.git_url_input.text()
        config.git_branch = self.git_branch_input.text() or "main"
        config.git_auto_sync = self.git_auto_sync_checkbox.isChecked()
        config.git_commit_message = self.git_commit_msg_input.text() or "更新笔记"
        config.save()

        QMessageBox.information(self, "保存成功", "Git 设置已保存。")
