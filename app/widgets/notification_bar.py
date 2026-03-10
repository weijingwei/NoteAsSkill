"""提示条组件

显示在窗口顶部的提示条，支持不同状态。
"""

from PySide6.QtCore import QTimer, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class NotificationBar(QWidget):
    """顶部提示条"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._init_ui()
        self._auto_hide_timer = QTimer()
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide)

    def _init_ui(self) -> None:
        """初始化界面"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)

        # 设置固定高度
        self.setFixedHeight(36)

        # 图标和文字
        self.icon_label = QLabel()
        self.icon_label.setFixedWidth(20)
        self.message_label = QLabel()
        self.message_label.setWordWrap(False)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.message_label, 1)

        # 关闭按钮
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(24, 24)
        self.close_button.setFlat(True)
        self.close_button.clicked.connect(self.hide)
        layout.addWidget(self.close_button)

        # 默认隐藏
        self.hide()

    def show_info(self, message: str, auto_hide: int = 0) -> None:
        """显示信息提示

        Args:
            message: 消息内容
            auto_hide: 自动隐藏时间（毫秒），0 表示不自动隐藏
        """
        self._show("ℹ️", message, "#E3F2FD", "#1565C0", auto_hide)

    def show_progress(self, message: str) -> None:
        """显示进度提示"""
        self._show("🔄", message, "#FFF8E1", "#F57C00", 0)

    def show_success(self, message: str, auto_hide: int = 3000) -> None:
        """显示成功提示"""
        self._show("✓", message, "#E8F5E9", "#2E7D32", auto_hide)

    def show_error(self, message: str, auto_hide: int = 5000) -> None:
        """显示错误提示"""
        self._show("✗", message, "#FFEBEE", "#C62828", auto_hide)

    def _show(self, icon: str, message: str, bg_color: str, text_color: str, auto_hide: int) -> None:
        """显示提示"""
        self._auto_hide_timer.stop()

        self.icon_label.setText(icon)
        self.message_label.setText(message)

        # 设置样式
        self.setStyleSheet(f"""
            NotificationBar {{
                background-color: {bg_color};
                border-bottom: 1px solid {text_color};
            }}
            QLabel {{
                color: {text_color};
                font-size: 14px;
            }}
            QPushButton {{
                color: {text_color};
                font-size: 18px;
                font-weight: bold;
                border: none;
            }}
            QPushButton:hover {{
                background-color: rgba(0, 0, 0, 0.1);
                border-radius: 12px;
            }}
        """)

        self.show()

        if auto_hide > 0:
            self._auto_hide_timer.start(auto_hide)

    def update_message(self, message: str) -> None:
        """更新消息内容"""
        self.message_label.setText(message)