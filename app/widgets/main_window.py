"""主窗口模块

实现三列布局的主窗口界面。
"""

from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings, Qt, Slot, QThread, Signal, QPoint, QTimer
from PySide6.QtGui import QAction, QFont, QIcon, QKeySequence, QPixmap, QPainter, QPolygon, QBrush, QColor
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..core.config import get_config, get_version
from ..core.note_manager import Note, get_note_manager
from ..core.folder_skill_updater import get_folder_skill_updater
from .chat_panel import ChatPanel
from .editor import Editor
from .sidebar import Sidebar
from .settings_dialog import SettingsDialog
from .notification_bar import NotificationBar


class ArrowButton(QPushButton):
    """自定义箭头按钮 - 使用 QPainter 绘制三角形，确保跨平台可靠性"""

    def __init__(self, direction: str = "right", parent=None):
        """
        Args:
            direction: "right" 或 "left"
        """
        super().__init__("", parent)
        self.direction = direction
        self.setFixedSize(24, 48)
        self._apply_style()

    def _apply_style(self):
        """应用样式"""
        if self.direction == "right":
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #D4A574, stop:1 #C49564);
                    border: none;
                    border-radius: 12px;
                    border-top-left-radius: 0;
                    border-bottom-left-radius: 0;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #C49564, stop:1 #B48554);
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #C49564, stop:1 #D4A574);
                    border: none;
                    border-radius: 12px;
                    border-top-right-radius: 0;
                    border-bottom-right-radius: 0;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #B48554, stop:1 #C49564);
                }
            """)

    def paintEvent(self, event):
        """绘制按钮和三角形箭头"""
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制白色三角形箭头
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor("#FFFEF9")))

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2  # 按钮中心点

        # 箭头尺寸参数
        arrow_height = 8  # 三角形半高
        arrow_width = 8   # 三角形宽度
        base_offset = arrow_width // 2  # 底边距中心的偏移（统一值）

        if self.direction == "right":
            # 右箭头 >: 底边在左，尖端在右
            points = [
                QPoint(cx - base_offset, cy - arrow_height),  # 底边上方
                QPoint(cx + base_offset, cy),                  # 尖端
                QPoint(cx - base_offset, cy + arrow_height),  # 底边下方
            ]
        else:
            # 左箭头 <: 底边在右，尖端在左
            points = [
                QPoint(cx + base_offset, cy - arrow_height),  # 底边上方
                QPoint(cx - base_offset, cy),                  # 尖端
                QPoint(cx + base_offset, cy + arrow_height),  # 底边下方
            ]

        painter.drawPolygon(QPolygon(points))


def create_arrow_icon(direction: str, size: int = 16, color: str = "#4A3F35") -> QIcon:
    """
    创建箭头图标，用于工具栏 QAction

    Args:
        direction: "right" 或 "left"
        size: 图标尺寸
        color: 箭头颜色

    Returns:
        QIcon 对象
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(color)))

    margin = 2
    arrow_width = size - margin * 2
    arrow_height = size - margin * 2

    if direction == "right":
        # 右箭头 >
        points = [
            QPoint(margin, margin),
            QPoint(margin + arrow_width, size // 2),
            QPoint(margin, size - margin),
        ]
    else:
        # 左箭头 <
        points = [
            QPoint(margin + arrow_width, margin),
            QPoint(margin, size // 2),
            QPoint(margin + arrow_width, size - margin),
        ]

    painter.drawPolygon(QPolygon(points))
    painter.end()

    return QIcon(pixmap)


class SkillGeneratorWorker(QThread):
    """SKILL.md 生成工作线程"""

    finished = Signal(bool, str)  # (success, message)

    def __init__(self, note_id: str, content: str, skill_path: Path):
        super().__init__()
        self.note_id = note_id
        self.content = content
        self.skill_path = skill_path

    def run(self) -> None:
        """运行生成任务"""
        try:
            from ..core.skill_generator import get_skill_generator
            from ..ai.client import create_client

            skill_generator = get_skill_generator()

            # 设置 AI 客户端
            config = get_config()
            try:
                ai_config = config.get_ai_config()
                ai_client = create_client(config.ai_provider, ai_config)
                skill_generator.set_ai_client(ai_client)
            except Exception:
                pass

            # 生成
            success = skill_generator.generate_and_save(
                self.note_id, self.content, self.skill_path
            )

            if success:
                self.finished.emit(True, "SKILL.md 已生成")
            else:
                self.finished.emit(False, "生成失败")

        except Exception as e:
            self.finished.emit(False, f"生成失败: {str(e)}")


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()

        self.setWindowTitle("NoteAsSkill - 笔技")
        self.setMinimumSize(1200, 800)
        self.setMouseTracking(True)  # 启用鼠标追踪，用于边缘检测

        # 加载设置
        self.settings = QSettings("NoteAsSkill", "NoteAsSkill")
        self._restore_geometry()

        # 生成器工作线程
        self._generator_worker: SkillGeneratorWorker | None = None

        # 初始化组件
        self._init_ui()
        self._set_window_icon()
        self._init_menu()
        self._init_statusbar()
        self._connect_signals()
        self._init_folder_skill_updater()

        # 当前笔记
        self._current_note: Note | None = None
        # 已保存的内容（用于检测未保存的更改）
        self._saved_content: str = ""

        # 自动保存定时器（防抖）
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._on_save)

    def _init_folder_skill_updater(self) -> None:
        """初始化文件夹 SKILL 更新器"""
        self._folder_skill_updater = get_folder_skill_updater()

        # 连接信号
        self._folder_skill_updater.update_finished.connect(self._on_folder_skill_updated)
        self._folder_skill_updater.update_error.connect(self._on_folder_skill_error)

    def _restore_geometry(self) -> None:
        """恢复窗口几何信息"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)

    def _set_window_icon(self) -> None:
        """设置窗口图标"""
        # 尝试加载SVG图标
        icon_path = Path(__file__).parent.parent.parent / "assets" / "icon.svg"

        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        else:
            # 创建一个简单的默认图标
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.GlobalColor.transparent)
            from PySide6.QtGui import QPainter, QColor, QFont
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # 绘制背景圆
            painter.setBrush(QColor("#F5EDE4"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(2, 2, 60, 60)

            # 绘制笔记本
            painter.setBrush(QColor("#FFFEF9"))
            painter.setPen(QColor("#E8DFD5"))
            painter.drawRoundedRect(12, 14, 28, 36, 2, 2)
            painter.drawRoundedRect(24, 14, 28, 36, 2, 2)

            # 绘制书脊
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#D4A574"))
            painter.drawRect(22, 14, 4, 36)

            # 绘制星芒
            painter.setBrush(QColor("#F5C778"))
            painter.setPen(QColor("#D4A574"))
            painter.drawEllipse(46, 20, 8, 8)

            # 绘制光芒
            pen = painter.pen()
            pen.setWidth(2)
            pen.setColor(QColor("#D4A574"))
            painter.setPen(pen)
            painter.drawLine(50, 14, 50, 10)
            painter.drawLine(50, 34, 50, 38)
            painter.drawLine(42, 24, 38, 24)
            painter.drawLine(58, 24, 62, 24)

            painter.end()
            self.setWindowIcon(QIcon(pixmap))

    def _init_ui(self) -> None:
        """初始化界面"""
        # 主容器
        self.central_widget = QWidget()
        self.central_widget.setMouseTracking(True)  # 启用鼠标追踪
        self.setCentralWidget(self.central_widget)

        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部提示条
        self.notification_bar = NotificationBar(self)
        main_layout.addWidget(self.notification_bar)

        # 三列分割器
        self.splitter = QSplitter(Qt.Horizontal)

        # 左侧：笔记列表（包含工具栏）
        self.sidebar_container = QWidget()
        self.sidebar_container.setObjectName("sidebar_container")  # 设置对象名称用于样式
        self.sidebar_container.setMinimumWidth(220)  # 设置最小宽度，确保工具栏显示完整
        # 设置容器样式，防止意外滚动条
        self.sidebar_container.setStyleSheet("""
            #sidebar_container {
                background-color: transparent;
            }
        """)
        sidebar_layout = QVBoxLayout(self.sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # 工具栏（放在侧边栏上部）
        self.sidebar_toolbar = QToolBar()
        self.sidebar_toolbar.setMovable(False)
        self.sidebar_toolbar.setFixedHeight(36)
        sidebar_layout.addWidget(self.sidebar_toolbar)

        # 添加展开/关闭侧边栏按钮
        self.toggle_sidebar_btn = QAction(create_arrow_icon("left"), "", self)
        self.toggle_sidebar_btn.setToolTip("收起侧边栏")
        self.toggle_sidebar_btn.triggered.connect(self._toggle_sidebar)
        self.sidebar_toolbar.addAction(self.toggle_sidebar_btn)

        # 添加工具栏按钮
        new_action = QAction("新建", self)
        new_action.setToolTip("新建笔记")
        new_action.triggered.connect(self._on_new_note)
        self.sidebar_toolbar.addAction(new_action)

        save_action = QAction("保存", self)
        save_action.setToolTip("保存当前笔记")
        save_action.triggered.connect(self._on_save)
        self.sidebar_toolbar.addAction(save_action)

        delete_action = QAction("删除", self)
        delete_action.setToolTip("删除当前笔记")
        delete_action.triggered.connect(self._on_delete_note)
        self.sidebar_toolbar.addAction(delete_action)

        # 同步按钮
        sync_action = QAction("同步", self)
        sync_action.setToolTip("同步笔记到 Git 仓库")
        sync_action.triggered.connect(self._on_git_sync)
        self.sidebar_toolbar.addAction(sync_action)

        # 侧边栏
        self.sidebar = Sidebar()
        sidebar_layout.addWidget(self.sidebar)

        self.splitter.addWidget(self.sidebar_container)

        # 中间：编辑器
        self.editor = Editor()
        self.editor.setMinimumWidth(300)  # 设置最小宽度
        self.splitter.addWidget(self.editor)

        # 右侧：AI 对话
        self.chat_container = QWidget()
        self.chat_container.setObjectName("chat_container")  # 设置对象名称用于样式
        self.chat_container.setMinimumWidth(250)  # 设置最小宽度
        # 明确禁用 chat_container 的滚动条
        self.chat_container.setStyleSheet("""
            #chat_container {
                background-color: transparent;
            }
        """)
        chat_container_layout = QVBoxLayout(self.chat_container)
        chat_container_layout.setContentsMargins(0, 0, 0, 0)
        chat_container_layout.setSpacing(0)

        # 右侧工具栏（包含展开/关闭按钮）
        chat_toolbar = QToolBar()
        chat_toolbar.setMovable(False)
        chat_toolbar.setFixedHeight(36)
        # 添加一个 spacer 将按钮推到右侧
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        chat_toolbar.addWidget(spacer)
        self.toggle_chat_btn = QAction(create_arrow_icon("right"), "收起", self)
        self.toggle_chat_btn.setToolTip("收起 AI 对话")
        self.toggle_chat_btn.triggered.connect(self._toggle_chat_panel)
        chat_toolbar.addAction(self.toggle_chat_btn)
        chat_container_layout.addWidget(chat_toolbar)

        self.chat_panel = ChatPanel()
        chat_container_layout.addWidget(self.chat_panel)

        self.splitter.addWidget(self.chat_container)

        # 设置分割比例
        self.splitter.setSizes([250, 600, 350])

        main_layout.addWidget(self.splitter)

        # 左侧浮动展开按钮（当sidebar隐藏时显示）
        self.left_expand_btn = ArrowButton("right", self)
        self.left_expand_btn.setToolTip("展开侧边栏")
        self.left_expand_btn.clicked.connect(self._toggle_sidebar)
        # 添加阴影效果
        left_shadow = QGraphicsDropShadowEffect()
        left_shadow.setBlurRadius(8)
        left_shadow.setColor(Qt.GlobalColor.darkGray)
        left_shadow.setOffset(2, 0)
        self.left_expand_btn.setGraphicsEffect(left_shadow)
        self.left_expand_btn.hide()

        # 右侧浮动展开按钮（当chat面板隐藏时显示）
        self.right_expand_btn = ArrowButton("left", self)
        self.right_expand_btn.setToolTip("展开 AI 对话")
        self.right_expand_btn.clicked.connect(self._toggle_chat_panel)
        # 添加阴影效果
        right_shadow = QGraphicsDropShadowEffect()
        right_shadow.setBlurRadius(8)
        right_shadow.setColor(Qt.GlobalColor.darkGray)
        right_shadow.setOffset(-2, 0)
        self.right_expand_btn.setGraphicsEffect(right_shadow)
        self.right_expand_btn.hide()

        # 记录浮动按钮是否应该可见
        self._left_btn_should_show = False
        self._right_btn_should_show = False

        # 应用统一样式
        self._apply_style()

    def _apply_style(self) -> None:
        """应用统一样式 - Editorial Warm 设计风格"""
        self.setStyleSheet("""
            /* ========================================
               NoteAsSkill - Editorial Warm Theme
               温暖的编辑风格，如同精致的纸质笔记本
               ======================================== */

            /* 主窗口 - 温暖的象牙白背景 */
            QMainWindow {
                background-color: #F5EDE4;
            }

            /* 分割器 - 优雅的分隔线 */
            QSplitter {
                background-color: transparent;
            }
            QSplitter::handle {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #E8DFD5, stop:0.5 #D4C4B0, stop:1 #E8DFD5);
                width: 2px;
            }
            QSplitter::handle:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #D4A574, stop:0.5 #C4956A, stop:1 #D4A574);
            }

            /* 侧边栏 - 温暖的米色卡片 */
            #sidebar {
                background-color: #FBF7F2;
                border-right: 1px solid #E8DFD5;
            }

            /* AI 对话面板 - 温暖的米色卡片 */
            #chat_panel {
                background-color: #FBF7F2;
                border-left: 1px solid #E8DFD5;
            }

            /* 列表 - 纸张质感 */
            QListWidget {
                background-color: #FFFEF9;
                border: 1px solid #E8DFD5;
                border-radius: 12px;
                padding: 6px;
                font-family: 'Segoe UI', 'SF Pro Text', sans-serif;
            }
            QListWidget::item {
                padding: 6px 12px;
                border-radius: 6px;
                margin: 2px 2px;
                color: #4A3F35;
                font-size: 13px;
                border: 1px solid transparent;
            }
            QListWidget::item:selected {
                background-color: #FDF6ED;
                color: #8B5A2B;
                border: 1px solid #D4A574;
                font-weight: 500;
            }
            QListWidget::item:hover:!selected {
                background-color: #FDF8F0;
                border: 1px solid #E8D5C0;
            }

            /* 树形控件 - 文件夹列表 */
            QTreeWidget {
                background-color: #FFFEF9;
                border: 1px solid #E8DFD5;
                border-radius: 12px;
                padding: 6px;
            }
            QTreeWidget::item {
                padding: 4px 6px;
                border-radius: 4px;
                color: #4A3F35;
            }
            QTreeWidget::item:selected {
                background-color: #FDF6ED;
                color: #8B5A2B;
                border: 1px solid #D4A574;
            }
            QTreeWidget::item:hover:!selected {
                background-color: #FDF8F0;
            }
            QTreeWidget::branch {
                background-color: transparent;
            }
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                background-color: transparent;
            }
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {
                background-color: transparent;
            }
            QListWidget::item:selected {
                background-color: #FDF6ED;
                color: #8B5A2B;
                border: 1px solid #D4A574;
                font-weight: 500;
            }
            QListWidget::item:hover:!selected {
                background-color: #FDF8F0;
                border: 1px solid #E8D5C0;
            }

            /* 输入框 - 精致的书写区域 */
            QLineEdit {
                background-color: #FFFEF9;
                border: 2px solid #E8DFD5;
                border-radius: 10px;
                padding: 10px 16px;
                font-size: 14px;
                color: #3D3428;
                selection-background-color: #D4A574;
                selection-color: white;
            }
            QLineEdit:focus {
                border-color: #D4A574;
                background-color: #FFFDF8;
            }
            QLineEdit:hover {
                border-color: #D4C4B0;
            }

            /* 按钮 - 温暖的琥珀色调 */
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #D4A574, stop:1 #C49564);
                color: #FFFEF9;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 600;
                letter-spacing: 0.3px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #C49564, stop:1 #B48554);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #B48554, stop:1 #A47544);
            }
            QPushButton:disabled {
                background: #D5C8B8;
                color: #A09585;
            }

            /* 文本编辑 - 书写纸张 */
            QTextEdit {
                background-color: #FFFEF9;
                border: 2px solid #E8DFD5;
                border-radius: 12px;
                padding: 12px 16px;
                font-size: 14px;
                color: #3D3428;
                line-height: 1.6;
                selection-background-color: #D4A574;
                selection-color: white;
            }
            QTextEdit:focus {
                border-color: #D4A574;
                background-color: #FFFDF8;
            }

            /* 下拉框 - 优雅的选择器 */
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
            QComboBox::down-arrow {
                image: url(assets/dropdown-arrow.svg);
                width: 16px;
                height: 16px;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFEF9;
                border: 2px solid #D4A574;
                border-radius: 8px;
                padding: 4px;
                selection-background-color: #FDF6ED;
                selection-color: #8B5A2B;
                outline: none;
                background: #FFFEF9;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 10px;
                border-radius: 4px;
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

            /* 标签 - 温暖的文字 */
            QLabel {
                color: #5A4A3A;
                font-size: 14px;
                font-family: 'Segoe UI', 'SF Pro Text', sans-serif;
            }

            /* 菜单栏 - 精致的顶部导航 */
            QMenuBar {
                background-color: #FBF7F2;
                border-bottom: 1px solid #E8DFD5;
                padding: 2px 8px;
                font-size: 13px;
            }
            QMenuBar::item {
                padding: 4px 12px;
                border-radius: 0;
                color: #5A4A3A;
            }
            QMenuBar::item:selected {
                background-color: #FDF6ED;
                color: #8B5A2B;
            }
            QMenuBar::item:pressed {
                background-color: #FDF6ED;
            }

            /* 菜单 - 优雅的浮层 */
            QMenu {
                background-color: #FFFEF9;
                border: 2px solid #E8DFD5;
                border-radius: 0;
                padding: 4px;
                margin: 0px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 0;
                color: #3D3428;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #FDF6ED;
                color: #8B5A2B;
            }
            QMenu::item:disabled {
                color: #B0A090;
            }
            QMenu::separator {
                height: 1px;
                background: #E8DFD5;
                margin: 8px 12px;
            }
            QMenu::indicator {
                width: 16px;
                height: 16px;
                margin-left: 6px;
            }
            QMenu::right-arrow {
                width: 12px;
                height: 12px;
                margin-right: 8px;
            }
            QMenu::scroller {
                background-color: #FFFEF9;
            }

            /* 工具栏 - 紧凑的工具区 */
            QToolBar {
                background-color: #FBF7F2;
                border-bottom: 1px solid #E8DFD5;
                padding: 2px 4px;
                spacing: 2px;
                min-height: 32px;
            }
            QToolBar QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 2px 6px;
                color: #5A4A3A;
                font-size: 12px;
                font-weight: 500;
                min-height: 22px;
            }
            QToolBar QToolButton:hover {
                background-color: #FDF6ED;
                border-color: #E8D5C0;
                color: #8B5A2B;
            }
            QToolBar QToolButton:pressed {
                background-color: #FDF6ED;
                border-color: #D4A574;
            }

            /* 状态栏 - 安静的底部信息 */
            QStatusBar {
                background-color: #FBF7F2;
                border-top: 1px solid #E8DFD5;
                color: #8B7B6B;
                font-size: 12px;
                padding: 6px 16px;
                font-style: italic;
            }

            /* 滚动条 - 优雅的滚动体验 */
            QScrollBar:vertical {
                background-color: #F5EDE4;
                width: 12px;
                border-radius: 6px;
                margin: 4px 2px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #D5C8B8, stop:1 #C5B8A8);
                border-radius: 5px;
                min-height: 40px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #D4A574, stop:1 #C49564);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }

            QScrollBar:horizontal {
                background-color: #F5EDE4;
                height: 12px;
                border-radius: 6px;
                margin: 2px 4px;
            }
            QScrollBar::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #D5C8B8, stop:1 #C5B8A8);
                border-radius: 5px;
                min-width: 40px;
            }
            QScrollBar::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #D4A574, stop:1 #C49564);
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }

            /* 复选框 */
            QCheckBox {
                color: #3D3428;
                font-size: 14px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border-radius: 6px;
                border: 2px solid #D5C8B8;
                background-color: #FFFEF9;
            }
            QCheckBox::indicator:checked {
                background-color: #D4A574;
                border-color: #D4A574;
                image: url(assets/checkmark.svg);
            }
            QCheckBox::indicator:hover {
                border-color: #D4A574;
            }

            /* 数字输入框 */
            QSpinBox {
                background-color: #FFFEF9;
                border: 2px solid #E8DFD5;
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 14px;
                color: #3D3428;
            }
            QSpinBox:focus {
                border-color: #D4A574;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                background-color: #F5EDE4;
                border: none;
                width: 24px;
                border-radius: 4px;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #E8D5C0;
            }

            /* 分组框 */
            QGroupBox {
                color: #5A4A3A;
                font-size: 14px;
                font-weight: 600;
                border: 2px solid #E8DFD5;
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 16px;
                background-color: #FFFEF9;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 16px;
                padding: 0 8px;
                background-color: #FFFEF9;
            }

            /* 标签页 */
            QTabWidget::pane {
                border: 2px solid #E8DFD5;
                border-radius: 12px;
                background-color: #FFFEF9;
            }
            QTabBar::tab {
                background-color: #F5EDE4;
                color: #5A4A3A;
                padding: 10px 20px;
                margin-right: 4px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            QTabBar::tab:selected {
                background-color: #FFFEF9;
                color: #8B5A2B;
                font-weight: 600;
            }
            QTabBar::tab:hover:!selected {
                background-color: #FBF7F2;
            }

            /* 对话框 */
            QDialog {
                background-color: #FBF7F2;
            }

            /* 提示框 */
            QToolTip {
                background-color: #3D3428;
                color: #FFFEF9;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }
        """)

    def _init_menu(self) -> None:
        """初始化菜单"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = QMenu("文件(&F)", self)
        menubar.addMenu(file_menu)

        new_action = QAction("新建笔记(&N)", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self._on_new_note)
        file_menu.addAction(new_action)

        save_action = QAction("保存(&S)", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 编辑菜单
        edit_menu = QMenu("编辑(&E)", self)
        menubar.addMenu(edit_menu)

        delete_action = QAction("删除笔记(&D)", self)
        delete_action.setShortcut(QKeySequence.Delete)
        delete_action.triggered.connect(self._on_delete_note)
        edit_menu.addAction(delete_action)

        # 视图菜单
        view_menu = QMenu("视图(&V)", self)
        menubar.addMenu(view_menu)

        toggle_sidebar = QAction("切换侧边栏(&S)", self)
        toggle_sidebar.setShortcut(QKeySequence("Ctrl+B"))
        toggle_sidebar.triggered.connect(self._toggle_sidebar)
        view_menu.addAction(toggle_sidebar)

        toggle_chat = QAction("切换 AI 对话(&A)", self)
        toggle_chat.setShortcut(QKeySequence("Ctrl+J"))
        toggle_chat.triggered.connect(self._toggle_chat_panel)
        view_menu.addAction(toggle_chat)

        # 设置菜单
        settings_menu = QMenu("设置(&S)", self)
        menubar.addMenu(settings_menu)

        settings_action = QAction("偏好设置(&P)...", self)
        settings_action.setShortcut(QKeySequence.Preferences)
        settings_action.triggered.connect(self._on_settings)
        settings_menu.addAction(settings_action)

        # 帮助菜单
        help_menu = QMenu("帮助(&H)", self)
        menubar.addMenu(help_menu)

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _init_statusbar(self) -> None:
        """初始化状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("就绪")

        # 添加版本号到右下角
        self.version_label = QLabel(get_version())
        self.version_label.setStyleSheet("""
            QLabel {
                color: #A09080;
                font-size: 11px;
                padding-right: 8px;
            }
        """)
        self.statusbar.addPermanentWidget(self.version_label)

    def _connect_signals(self) -> None:
        """连接信号"""
        # 侧边栏信号
        self.sidebar.note_selected.connect(self._on_note_selected)
        self.sidebar.note_created.connect(self._on_note_created)
        self.sidebar.note_deleted.connect(self._on_note_deleted)
        self.sidebar.note_moved.connect(self._on_note_moved)

        # 编辑器信号
        self.editor.content_changed.connect(self._on_content_changed)
        self.editor.save_requested.connect(self._on_save)

        # AI 对话信号
        self.chat_panel.generate_skill_requested.connect(self._on_generate_skill)

    @Slot()
    def _on_new_note(self) -> None:
        """新建笔记"""
        self.sidebar.create_new_note()

    @Slot()
    def _on_save(self) -> None:
        """保存笔记"""
        if self._current_note is None:
            return

        content = self.editor.get_content()

        note_manager = get_note_manager()
        note_manager.update_note(self._current_note.id, content=content)

        # 更新已保存内容
        self._saved_content = content

        self.statusbar.showMessage("已保存", 3000)

        # 根据配置决定是否自动生成 SKILL.md
        config = get_config()
        if config.auto_generate_skill:
            self._generate_skill_md_async(self._current_note.id, content)

    def _has_unsaved_changes(self) -> bool:
        """检查当前笔记是否有未保存的更改"""
        if self._current_note is None:
            return False
        current_content = self.editor.get_content()
        return current_content != self._saved_content

    def _prompt_unsaved_changes(self) -> bool:
        """提示用户保存未保存的更改

        Returns:
            True 表示可以继续操作（已保存或放弃），False 表示取消操作
        """
        reply = QMessageBox.question(
            self,
            "未保存的更改",
            "当前笔记有未保存的更改，是否保存？",
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Cancel:
            return False
        elif reply == QMessageBox.StandardButton.Save:
            self._on_save()
        return True

    def _generate_skill_md_async(self, note_id: str, content: str) -> None:
        """异步生成 SKILL.md"""
        note_manager = get_note_manager()
        skill_path = note_manager.skills_path / note_id / "SKILL.md"

        # 显示进度提示
        self.notification_bar.show_progress("正在生成 SKILL.md...")

        # 创建工作线程
        self._generator_worker = SkillGeneratorWorker(note_id, content, skill_path)
        self._generator_worker.finished.connect(self._on_skill_generated)
        self._generator_worker.start()

    @Slot(bool, str)
    def _on_skill_generated(self, success: bool, message: str) -> None:
        """SKILL.md 生成完成回调"""
        if success:
            self.notification_bar.show_success(message)

            # 触发文件夹 SKILL 更新（延迟模式）
            if self._current_note and self._current_note.folder:
                self._folder_skill_updater.mark_folder_dirty(
                    self._current_note.folder,
                    self._folder_skill_updater.MODE_DELAYED
                )
        else:
            self.notification_bar.show_error(message)

        self._generator_worker = None

    @Slot()
    def _on_delete_note(self) -> None:
        """删除笔记"""
        if self._current_note is None:
            return

        # 保存文件夹信息（删除前）
        folder_name = self._current_note.folder

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除笔记「{self._current_note.title}」吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            note_manager = get_note_manager()
            note_manager.delete_note(self._current_note.id)
            self._current_note = None
            self.editor.clear()
            self.sidebar.refresh()

            # 触发文件夹 SKILL 更新（立即模式）
            if folder_name:
                self._folder_skill_updater.mark_folder_dirty(
                    folder_name,
                    self._folder_skill_updater.MODE_IMMEDIATE
                )

    @Slot(Note)
    def _on_note_selected(self, note: Note) -> None:
        """笔记被选中"""
        # 检查是否有未保存的内容
        if self._current_note and self._has_unsaved_changes():
            if not self._prompt_unsaved_changes():
                # 用户取消操作，恢复侧边栏选中状态
                self.sidebar.restore_note_selection(self._current_note.id)
                return

        self._current_note = note

        note_manager = get_note_manager()
        content = note_manager.get_note_content(note.id)
        self.editor.set_content(content, note.title, note.id)

        # 记录已保存的内容
        self._saved_content = content

        # 更新 AI 对话面板的笔记内容
        self.chat_panel.set_current_note(note.title, content)

        self.statusbar.showMessage(f"已打开: {note.title}")

    @Slot(Note)
    def _on_note_created(self, note: Note) -> None:
        """笔记被创建"""
        self._current_note = note
        self.editor.set_content("", note.title, note.id)

        # 新笔记的已保存内容为空
        self._saved_content = ""

        # 更新 AI 对话面板
        self.chat_panel.set_current_note(note.title, "")

        self.statusbar.showMessage(f"已创建: {note.title}")

    @Slot(str)
    def _on_note_deleted(self, note_id: str) -> None:
        """笔记被删除"""
        if self._current_note and self._current_note.id == note_id:
            self._current_note = None
            self._saved_content = ""
            self.editor.clear()

    @Slot(str, str, str)
    def _on_note_moved(self, note_id: str, old_folder: str, new_folder: str) -> None:
        """笔记被移动"""
        # 触发两个文件夹的 SKILL.md 更新（延迟模式，避免阻塞）
        if old_folder:
            self._folder_skill_updater.mark_folder_dirty(
                old_folder,
                self._folder_skill_updater.MODE_DELAYED
            )
        if new_folder and new_folder != old_folder:
            self._folder_skill_updater.mark_folder_dirty(
                new_folder,
                self._folder_skill_updater.MODE_DELAYED
            )

        self.statusbar.showMessage(f"笔记已移动到「{new_folder or '根目录'}」", 3000)

    @Slot()
    def _on_content_changed(self) -> None:
        """内容改变 - 使用定时器防抖保存"""
        config = get_config()
        if config.auto_save:
            # 重置定时器，实现防抖
            interval = config.auto_save_interval * 1000  # 转换为毫秒
            self._save_timer.start(interval)

    @Slot()
    def _on_generate_skill(self) -> None:
        """生成 SKILL.md"""
        if self._current_note is None:
            return

        content = self.editor.get_content()
        self.chat_panel.generate_skill(content)

    @Slot()
    def _on_settings(self) -> None:
        """打开设置对话框"""
        dialog = SettingsDialog(self)
        dialog.exec()

    @Slot()
    def _on_git_sync(self) -> None:
        """同步笔记到 Git 仓库"""
        config = get_config()

        if not config.git_enabled:
            self.notification_bar.show_error("Git 同步未启用，请在设置中配置")
            return

        if not config.git_remote_url:
            self.notification_bar.show_error("未配置 Git 远程仓库地址")
            return

        from ..core.git_sync import get_git_sync_manager

        sync_manager = get_git_sync_manager()

        if sync_manager.is_syncing():
            self.notification_bar.show_progress("正在同步中...")
            return

        self.notification_bar.show_progress("正在同步笔记...")

        sync_manager.sync(
            on_progress=lambda msg: self.notification_bar.show_progress(msg),
            on_success=lambda msg: self.notification_bar.show_success(msg),
            on_error=lambda msg: self.notification_bar.show_error(msg),
        )

    def _startup_git_pull(self) -> None:
        """启动时自动拉取远程更改"""
        config = get_config()

        # 检查是否启用启动时自动拉取
        if not config.git_enabled or not config.git_auto_sync:
            return

        if not config.git_remote_url:
            return

        from ..core.git_sync import get_git_sync_manager

        sync_manager = get_git_sync_manager()

        if sync_manager.is_syncing():
            return

        sync_manager.pull(
            on_progress=lambda msg: self.notification_bar.show_progress(msg),
            on_success=lambda msg: self.notification_bar.show_success(msg),
            on_error=lambda msg: self.notification_bar.show_error(msg),
        )

    @Slot()
    def _on_about(self) -> None:
        """关于对话框"""
        version = get_version()
        QMessageBox.about(
            self,
            "关于 NoteAsSkill",
            f"""<h3>NoteAsSkill - 笔技</h3>
            <p>版本: {version}</p>
            <p>与 AI 共享你的心得。</p>
            <p>只需专注于编辑笔记内容，系统自动处理 SKILL.md 生成。</p>
            """,
        )

    @Slot()
    def _toggle_sidebar(self) -> None:
        """切换侧边栏显示"""
        if self.sidebar_container.isVisible():
            self.sidebar_container.hide()
            self.toggle_sidebar_btn.setIcon(create_arrow_icon("right"))
            self.toggle_sidebar_btn.setToolTip("展开侧边栏")
            self._left_btn_should_show = True
            # 立即显示浮动展开按钮，用户无需移动鼠标到边缘
            self._update_floating_buttons()
            self.left_expand_btn.show()
        else:
            self.sidebar_container.show()
            self.toggle_sidebar_btn.setIcon(create_arrow_icon("left"))
            self.toggle_sidebar_btn.setToolTip("收起侧边栏")
            self._left_btn_should_show = False
            self.left_expand_btn.hide()

    @Slot()
    def _toggle_chat_panel(self) -> None:
        """切换 AI 对话面板显示"""
        if self.chat_container.isVisible():
            self.chat_container.hide()
            self.toggle_chat_btn.setIcon(create_arrow_icon("left"))
            self.toggle_chat_btn.setToolTip("展开 AI 对话")
            self._right_btn_should_show = True
            # 立即显示浮动展开按钮
            self._update_floating_buttons()
            self.right_expand_btn.show()
        else:
            self.chat_container.show()
            self.toggle_chat_btn.setIcon(create_arrow_icon("right"))
            self.toggle_chat_btn.setToolTip("收起 AI 对话")
            self._right_btn_should_show = False
            self.right_expand_btn.hide()

    def _update_floating_buttons(self) -> None:
        """更新浮动按钮位置"""
        splitter_geo = self.splitter.geometry()
        btn_height = self.left_expand_btn.height()
        # 将按钮放在约 1/3 处，视觉上更舒适
        y_pos = splitter_geo.top() + splitter_geo.height() // 3 - btn_height // 2

        # 左侧按钮
        self.left_expand_btn.move(0, y_pos)

        # 右侧按钮
        right_x = self.width() - self.right_expand_btn.width()
        self.right_expand_btn.move(right_x, y_pos)

    def resizeEvent(self, event: Any) -> None:
        """窗口大小改变事件"""
        super().resizeEvent(event)
        self._update_floating_buttons()

    def mouseMoveEvent(self, event: Any) -> None:
        """鼠标移动事件 - 更新浮动按钮位置"""
        super().mouseMoveEvent(event)
        # 只在需要时更新按钮位置，不再控制显示/隐藏
        if self._left_btn_should_show or self._right_btn_should_show:
            self._update_floating_buttons()

    def leaveEvent(self, event: Any) -> None:
        """鼠标离开窗口事件"""
        super().leaveEvent(event)
        # 不再隐藏按钮，让它们保持可见

    @Slot(str)
    def _on_folder_skill_updated(self, folder_name: str) -> None:
        """文件夹 SKILL 更新完成"""
        self.statusbar.showMessage(f"文件夹「{folder_name}」概要已更新", 3000)

    @Slot(str, str)
    def _on_folder_skill_error(self, folder_name: str, error: str) -> None:
        """文件夹 SKILL 更新错误"""
        self.notification_bar.show_error(f"更新文件夹「{folder_name}」概要失败: {error}")

    def closeEvent(self, event: Any) -> None:
        """窗口关闭事件"""
        # 保存几何信息
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())

        # 保存当前笔记（如果定时器活跃，停止并立即保存）
        if self._current_note:
            if self._save_timer.isActive():
                self._save_timer.stop()
            self._on_save()

        # 停止 SkillGeneratorWorker 线程
        if self._generator_worker is not None:
            self._generator_worker.requestInterruption()
            if not self._generator_worker.wait(2000):
                self._generator_worker.terminate()
                self._generator_worker.wait()
            self._generator_worker = None

        # 停止 ChatPanel 中的工作线程
        self.chat_panel.cleanup()

        # 停止 FolderSkillUpdater 的定时器
        if hasattr(self, '_folder_skill_updater'):
            self._folder_skill_updater.update_timer.stop()

        event.accept()


def run_app() -> None:
    """运行应用"""
    import sys

    app = QApplication(sys.argv)
    app.setApplicationName("NoteAsSkill")
    app.setOrganizationName("NoteAsSkill")

    # 设置应用样式
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    # 启动后 500ms 执行自动拉取
    QTimer.singleShot(500, window._startup_git_pull)

    sys.exit(app.exec())