"""主窗口模块

实现三列布局的主窗口界面。
"""

from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings, Qt, Slot, QThread, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..core.config import get_config
from ..core.note_manager import Note, get_note_manager
from ..core.folder_skill_updater import get_folder_skill_updater
from .chat_panel import ChatPanel
from .editor import Editor
from .sidebar import Sidebar
from .settings_dialog import SettingsDialog
from .notification_bar import NotificationBar


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

        self.setWindowTitle("NoteAsSkil - 笔技")
        self.setMinimumSize(1200, 800)

        # 加载设置
        self.settings = QSettings("NoteAsSkill", "NoteAsSkill")
        self._restore_geometry()

        # 生成器工作线程
        self._generator_worker: SkillGeneratorWorker | None = None

        # 初始化组件
        self._init_ui()
        self._init_menu()
        self._init_statusbar()
        self._connect_signals()
        self._init_folder_skill_updater()

        # 当前笔记
        self._current_note: Note | None = None

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

    def _init_ui(self) -> None:
        """初始化界面"""
        # 主容器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部提示条
        self.notification_bar = NotificationBar(self)
        main_layout.addWidget(self.notification_bar)

        # 三列分割器
        self.splitter = QSplitter(Qt.Horizontal)

        # 左侧：笔记列表（包含工具栏）
        sidebar_container = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_container)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # 工具栏（放在侧边栏上部）
        self.sidebar_toolbar = QToolBar()
        self.sidebar_toolbar.setMovable(False)
        self.sidebar_toolbar.setIconSize(self.sidebar_toolbar.iconSize())
        sidebar_layout.addWidget(self.sidebar_toolbar)

        # 添加工具栏按钮
        new_action = QAction("新建", self)
        new_action.setToolTip("新建笔记")
        new_action.triggered.connect(self._on_new_note)
        self.sidebar_toolbar.addAction(new_action)

        save_action = QAction("保存", self)
        save_action.setToolTip("保存当前笔记")
        save_action.triggered.connect(self._on_save)
        self.sidebar_toolbar.addAction(save_action)

        self.sidebar_toolbar.addSeparator()

        delete_action = QAction("删除", self)
        delete_action.setToolTip("删除当前笔记")
        delete_action.triggered.connect(self._on_delete_note)
        self.sidebar_toolbar.addAction(delete_action)

        self.sidebar_toolbar.addSeparator()

        # 同步按钮
        sync_action = QAction("同步", self)
        sync_action.setToolTip("同步笔记到 Git 仓库")
        sync_action.triggered.connect(self._on_git_sync)
        self.sidebar_toolbar.addAction(sync_action)

        # 侧边栏
        self.sidebar = Sidebar()
        sidebar_layout.addWidget(self.sidebar)

        self.splitter.addWidget(sidebar_container)

        # 中间：编辑器
        self.editor = Editor()
        self.splitter.addWidget(self.editor)

        # 右侧：AI 对话
        self.chat_panel = ChatPanel()
        self.splitter.addWidget(self.chat_panel)

        # 设置分割比例
        self.splitter.setSizes([250, 600, 350])

        main_layout.addWidget(self.splitter)

        # 应用统一样式
        self._apply_style()

    def _apply_style(self) -> None:
        """应用统一样式 - Editorial Warm 设计风格"""
        self.setStyleSheet("""
            /* ========================================
               NoteAsSkil - Editorial Warm Theme
               温暖的编辑风格，如同精致的纸质笔记本
               ======================================== */

            /* 主窗口 - 温暖的象牙白背景 */
            QMainWindow {
                background-color: #F5EDE4;
            }

            /* 分割器 - 优雅的分隔线 */
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
            Sidebar {
                background-color: #FBF7F2;
                border-right: 1px solid #E8DFD5;
            }

            /* AI 对话面板 - 温暖的米色卡片 */
            ChatPanel {
                background-color: #FBF7F2;
                border-left: 1px solid #E8DFD5;
            }

            /* 列表 - 纸张质感 */
            QListWidget {
                background-color: #FFFEF9;
                border: 1px solid #E8DFD5;
                border-radius: 12px;
                padding: 8px;
                font-family: 'Segoe UI', 'SF Pro Text', sans-serif;
            }
            QListWidget::item {
                padding: 12px 16px;
                border-radius: 8px;
                margin: 4px 4px;
                color: #4A3F35;
                font-size: 14px;
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
                border-radius: 10px;
                padding: 10px 16px;
                font-size: 14px;
                color: #3D3428;
            }
            QComboBox:focus {
                border-color: #D4A574;
            }
            QComboBox:hover {
                border-color: #D4C4B0;
            }
            QComboBox::drop-down {
                border: none;
                width: 32px;
                padding-right: 8px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #8B5A2B;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFEF9;
                border: 2px solid #D4A574;
                border-radius: 10px;
                padding: 8px;
                selection-background-color: #FDF6ED;
                selection-color: #8B5A2B;
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
                padding: 6px 8px;
                font-size: 13px;
            }
            QMenuBar::item {
                padding: 8px 14px;
                border-radius: 6px;
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
                border-radius: 12px;
                padding: 8px;
            }
            QMenu::item {
                padding: 10px 24px;
                border-radius: 6px;
                color: #3D3428;
            }
            QMenu::item:selected {
                background-color: #FDF6ED;
                color: #8B5A2B;
            }
            QMenu::separator {
                height: 1px;
                background: #E8DFD5;
                margin: 8px 12px;
            }

            /* 工具栏 - 紧凑的工具区 */
            QToolBar {
                background-color: #FBF7F2;
                border-bottom: 1px solid #E8DFD5;
                padding: 2px 8px;
                spacing: 4px;
                min-height: 32px;
            }
            QToolBar QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                padding: 4px 10px;
                color: #5A4A3A;
                font-size: 12px;
                font-weight: 500;
                min-height: 24px;
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
        file_menu = menubar.addMenu("文件(&F)")

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
        edit_menu = menubar.addMenu("编辑(&E)")

        delete_action = QAction("删除笔记(&D)", self)
        delete_action.setShortcut(QKeySequence.Delete)
        delete_action.triggered.connect(self._on_delete_note)
        edit_menu.addAction(delete_action)

        # 视图菜单
        view_menu = menubar.addMenu("视图(&V)")

        toggle_sidebar = QAction("切换侧边栏(&S)", self)
        toggle_sidebar.setShortcut(QKeySequence("Ctrl+B"))
        toggle_sidebar.triggered.connect(self._toggle_sidebar)
        view_menu.addAction(toggle_sidebar)

        toggle_chat = QAction("切换 AI 对话(&A)", self)
        toggle_chat.setShortcut(QKeySequence("Ctrl+J"))
        toggle_chat.triggered.connect(self._toggle_chat_panel)
        view_menu.addAction(toggle_chat)

        # 设置菜单
        settings_menu = menubar.addMenu("设置(&S)")

        settings_action = QAction("偏好设置(&P)...", self)
        settings_action.setShortcut(QKeySequence.Preferences)
        settings_action.triggered.connect(self._on_settings)
        settings_menu.addAction(settings_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助(&H)")

        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _init_statusbar(self) -> None:
        """初始化状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("就绪")

        # 添加版本号到右下角
        self.version_label = QLabel("v0.1.3")
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

        self.statusbar.showMessage("已保存", 3000)

        # 根据配置决定是否自动生成 SKILL.md
        config = get_config()
        if config.auto_generate_skill:
            self._generate_skill_md_async(self._current_note.id, content)

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
        self._current_note = note

        note_manager = get_note_manager()
        content = note_manager.get_note_content(note.id)
        self.editor.set_content(content, note.title)

        # 更新 AI 对话面板的笔记内容
        self.chat_panel.set_current_note(note.title, content)

        self.statusbar.showMessage(f"已打开: {note.title}")

    @Slot(Note)
    def _on_note_created(self, note: Note) -> None:
        """笔记被创建"""
        self._current_note = note
        self.editor.set_content("", note.title)

        # 更新 AI 对话面板
        self.chat_panel.set_current_note(note.title, "")

        self.statusbar.showMessage(f"已创建: {note.title}")

    @Slot(str)
    def _on_note_deleted(self, note_id: str) -> None:
        """笔记被删除"""
        if self._current_note and self._current_note.id == note_id:
            self._current_note = None
            self.editor.clear()

    @Slot(str, str, str)
    def _on_note_moved(self, note_id: str, old_folder: str, new_folder: str) -> None:
        """笔记被移动"""
        self.notification_bar.show_progress(f"正在移动笔记...")

        # 触发两个文件夹的 SKILL.md 更新（立即模式）
        if old_folder:
            self._folder_skill_updater.mark_folder_dirty(
                old_folder,
                self._folder_skill_updater.MODE_IMMEDIATE
            )
        if new_folder and new_folder != old_folder:
            self._folder_skill_updater.mark_folder_dirty(
                new_folder,
                self._folder_skill_updater.MODE_IMMEDIATE
            )

        self.notification_bar.show_success(f"笔记已移动到「{new_folder or '根目录'}」")

    @Slot()
    def _on_content_changed(self) -> None:
        """内容改变"""
        config = get_config()
        if config.auto_save:
            self._on_save()

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

    @Slot()
    def _on_about(self) -> None:
        """关于对话框"""
        QMessageBox.about(
            self,
            "关于 NoteAsSkill",
            """<h3>NoteAsSkill - 笔记即技能</h3>
            <p>版本: 0.1.0</p>
            <p>每篇笔记自动成为一个 Claude Code Skill。</p>
            <p>用户只需专注于编辑笔记内容，系统自动处理 SKILL.md 生成。</p>
            """,
        )

    @Slot()
    def _toggle_sidebar(self) -> None:
        """切换侧边栏显示"""
        self.sidebar.setVisible(not self.sidebar.isVisible())

    @Slot()
    def _toggle_chat_panel(self) -> None:
        """切换 AI 对话面板显示"""
        self.chat_panel.setVisible(not self.chat_panel.isVisible())

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

        # 保存当前笔记
        if self._current_note:
            self._on_save()

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

    sys.exit(app.exec())