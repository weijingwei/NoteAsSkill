"""主窗口模块

实现三列布局的主窗口界面。
"""

from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings, Qt, Slot, QThread, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
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

        self.setWindowTitle("NoteAsSkill - 笔记即技能")
        self.setMinimumSize(1200, 800)

        # 加载设置
        self.settings = QSettings("NoteAsSkill", "NoteAsSkill")
        self._restore_geometry()

        # 生成器工作线程
        self._generator_worker: SkillGeneratorWorker | None = None

        # 初始化组件
        self._init_ui()
        self._init_menu()
        self._init_toolbar()
        self._init_statusbar()
        self._connect_signals()

        # 当前笔记
        self._current_note: Note | None = None

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

        # 左侧：笔记列表
        self.sidebar = Sidebar()
        self.splitter.addWidget(self.sidebar)

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
        """应用统一样式"""
        self.setStyleSheet("""
            /* 主窗口 */
            QMainWindow {
                background-color: #f5f5f5;
            }

            /* 分割器 */
            QSplitter::handle {
                background-color: #e0e0e0;
                width: 1px;
            }
            QSplitter::handle:hover {
                background-color: #1976D2;
            }

            /* 侧边栏 */
            Sidebar {
                background-color: #fafafa;
                border-right: 1px solid #e0e0e0;
            }

            /* AI 对话面板 */
            ChatPanel {
                background-color: #fafafa;
                border-left: 1px solid #e0e0e0;
            }

            /* 列表 */
            QListWidget {
                background-color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-radius: 4px;
                margin: 2px 0;
            }
            QListWidget::item:selected {
                background-color: #E3F2FD;
                color: #1976D2;
            }
            QListWidget::item:hover:!selected {
                background-color: #f5f5f5;
            }

            /* 输入框 */
            QLineEdit {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #1976D2;
            }

            /* 按钮 */
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }

            /* 文本编辑 */
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
            }
            QTextEdit:focus {
                border-color: #1976D2;
            }

            /* 下拉框 */
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QComboBox:focus {
                border-color: #1976D2;
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }

            /* 标签 */
            QLabel {
                color: #424242;
                font-size: 14px;
            }

            /* 菜单栏 */
            QMenuBar {
                background-color: #ffffff;
                border-bottom: 1px solid #e0e0e0;
                padding: 4px;
            }
            QMenuBar::item {
                padding: 6px 12px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #E3F2FD;
            }

            /* 菜单 */
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 0;
            }
            QMenu::item {
                padding: 8px 24px;
            }
            QMenu::item:selected {
                background-color: #E3F2FD;
            }

            /* 工具栏 */
            QToolBar {
                background-color: #ffffff;
                border-bottom: 1px solid #e0e0e0;
                padding: 4px 8px;
                spacing: 8px;
            }
            QToolBar QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                color: #424242;
            }
            QToolBar QToolButton:hover {
                background-color: #E3F2FD;
                color: #1976D2;
            }

            /* 状态栏 */
            QStatusBar {
                background-color: #ffffff;
                border-top: 1px solid #e0e0e0;
                color: #757575;
                font-size: 13px;
                padding: 4px 12px;
            }

            /* 滚动条 */
            QScrollBar:vertical {
                background-color: #f5f5f5;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #BDBDBD;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #9E9E9E;
            }

            QScrollBar:horizontal {
                background-color: #f5f5f5;
                height: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:horizontal {
                background-color: #BDBDBD;
                border-radius: 5px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #9E9E9E;
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

    def _init_toolbar(self) -> None:
        """初始化工具栏"""
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # 新建笔记
        new_action = QAction("新建", self)
        new_action.setToolTip("新建笔记")
        new_action.triggered.connect(self._on_new_note)
        toolbar.addAction(new_action)

        # 保存
        save_action = QAction("保存", self)
        save_action.setToolTip("保存当前笔记")
        save_action.triggered.connect(self._on_save)
        toolbar.addAction(save_action)

        toolbar.addSeparator()

        # 删除
        delete_action = QAction("删除", self)
        delete_action.setToolTip("删除当前笔记")
        delete_action.triggered.connect(self._on_delete_note)
        toolbar.addAction(delete_action)

    def _init_statusbar(self) -> None:
        """初始化状态栏"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        self.statusbar.showMessage("就绪")

    def _connect_signals(self) -> None:
        """连接信号"""
        # 侧边栏信号
        self.sidebar.note_selected.connect(self._on_note_selected)
        self.sidebar.note_created.connect(self._on_note_created)
        self.sidebar.note_deleted.connect(self._on_note_deleted)

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
        else:
            self.notification_bar.show_error(message)

        self._generator_worker = None

    @Slot()
    def _on_delete_note(self) -> None:
        """删除笔记"""
        if self._current_note is None:
            return

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

    @Slot(Note)
    def _on_note_selected(self, note: Note) -> None:
        """笔记被选中"""
        self._current_note = note

        note_manager = get_note_manager()
        content = note_manager.get_note_content(note.id)
        self.editor.set_content(content, note.title)

        self.statusbar.showMessage(f"已打开: {note.title}")

    @Slot(Note)
    def _on_note_created(self, note: Note) -> None:
        """笔记被创建"""
        self._current_note = note
        self.editor.set_content("", note.title)
        self.statusbar.showMessage(f"已创建: {note.title}")

    @Slot(str)
    def _on_note_deleted(self, note_id: str) -> None:
        """笔记被删除"""
        if self._current_note and self._current_note.id == note_id:
            self._current_note = None
            self.editor.clear()

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