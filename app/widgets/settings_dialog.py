"""设置对话框模块

提供 AI 配置、界面偏好设置和 Git 同步配置界面。
"""

from PySide6.QtCore import Slot
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
)

from ..core.config import get_config


class NoBorderComboBox(QComboBox):
    """无边框下拉框 - 解决 Windows 平台下拉列表黑边问题"""

    def showPopup(self) -> None:
        """显示下拉列表时移除容器边框"""
        super().showPopup()
        # 查找下拉框容器并移除边框
        popup = self.findChild(QFrame)
        if popup:
            popup.setLineWidth(0)
            popup.setFrameShape(QFrame.Shape.NoFrame)


class SettingsDialog(QDialog):
    """设置对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("设置")
        self.setMinimumSize(500, 450)

        self._init_ui()
        self._load_settings()

    def _init_ui(self) -> None:
        """初始化界面"""
        layout = QVBoxLayout(self)

        # 标签页
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # AI 设置标签页
        ai_tab = self._create_ai_tab()
        self.tab_widget.addTab(ai_tab, "AI 设置")

        # 编辑器设置标签页
        editor_tab = self._create_editor_tab()
        self.tab_widget.addTab(editor_tab, "编辑器")

        # Git 同步标签页
        git_tab = self._create_git_tab()
        self.tab_widget.addTab(git_tab, "Git 同步")

        # 按钮
        button_layout = QVBoxLayout()

        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self._on_save)
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

    def _create_ai_tab(self) -> QWidget:
        """创建 AI 设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 提供商选择
        provider_group = QGroupBox("AI 提供商")
        provider_layout = QVBoxLayout(provider_group)

        self.provider_combo = NoBorderComboBox()
        # 创建 QListView 并直接设置样式（Windows 平台需要）
        provider_view = QListView()
        provider_view.setStyleSheet("""
            QListView {
                background-color: #FFFEF9;
                border: 1px solid #E8DFD5;
                border-radius: 0;
                padding: 4px;
                outline: none;
            }
            QListView::item {
                padding: 4px 8px;
                min-height: 24px;
                background-color: #FFFEF9;
                border-radius: 0;
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
        self.provider_combo.addItems(["openai", "anthropic", "ollama"])
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        provider_layout.addWidget(self.provider_combo)

        layout.addWidget(provider_group)

        # API 配置
        api_group = QGroupBox("API 配置")
        api_layout = QFormLayout(api_group)

        self.base_url_input = QLineEdit()
        self.base_url_input.setPlaceholderText("API Base URL")
        api_layout.addRow("Base URL:", self.base_url_input)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("API Key")
        api_layout.addRow("API Key:", self.api_key_input)

        self.model_combo = NoBorderComboBox()
        # 创建 QListView 并直接设置样式（Windows 平台需要）
        model_view = QListView()
        model_view.setStyleSheet("""
            QListView {
                background-color: #FFFEF9;
                border: 1px solid #E8DFD5;
                border-radius: 0;
                padding: 4px;
                outline: none;
            }
            QListView::item {
                padding: 4px 8px;
                min-height: 24px;
                background-color: #FFFEF9;
                border-radius: 0;
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
        api_layout.addRow("模型:", self.model_combo)

        layout.addWidget(api_group)

        # 预设模型
        self._model_presets = {
            "openai": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            "anthropic": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
            "ollama": ["llama2", "llama3", "mistral", "codellama"],
        }

        return widget

    def _create_editor_tab(self) -> QWidget:
        """创建编辑器设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 外观设置
        appearance_group = QGroupBox("外观")
        appearance_layout = QFormLayout(appearance_group)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 24)
        self.font_size_spin.setValue(14)
        appearance_layout.addRow("字体大小:", self.font_size_spin)

        layout.addWidget(appearance_group)

        # 自动保存设置
        autosave_group = QGroupBox("自动保存")
        autosave_layout = QFormLayout(autosave_group)

        self.autosave_interval_spin = QSpinBox()
        self.autosave_interval_spin.setRange(5, 300)
        self.autosave_interval_spin.setValue(30)
        self.autosave_interval_spin.setSuffix(" 秒")
        autosave_layout.addRow("保存间隔:", self.autosave_interval_spin)

        layout.addWidget(autosave_group)

        # SKILL.md 设置
        skill_group = QGroupBox("SKILL.md 生成")
        skill_layout = QFormLayout(skill_group)

        self.auto_generate_skill_checkbox = QCheckBox("保存时自动生成 SKILL.md")
        self.auto_generate_skill_checkbox.setChecked(True)
        skill_layout.addRow(self.auto_generate_skill_checkbox)

        layout.addWidget(skill_group)

        layout.addStretch()

        return widget

    def _create_git_tab(self) -> QWidget:
        """创建 Git 同步标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 启用设置
        enable_group = QGroupBox("Git 同步")
        enable_layout = QVBoxLayout(enable_group)

        self.git_enabled_checkbox = QCheckBox("启用 Git 同步")
        enable_layout.addWidget(self.git_enabled_checkbox)

        layout.addWidget(enable_group)

        # 远程仓库配置
        remote_group = QGroupBox("远程仓库")
        remote_layout = QFormLayout(remote_group)

        self.git_url_input = QLineEdit()
        self.git_url_input.setPlaceholderText("git@github.com:user/repo.git 或 https://github.com/user/repo.git")
        remote_layout.addRow("仓库地址:", self.git_url_input)

        self.git_branch_input = QLineEdit()
        self.git_branch_input.setPlaceholderText("main")
        remote_layout.addRow("分支:", self.git_branch_input)

        layout.addWidget(remote_group)

        # 同步设置
        sync_group = QGroupBox("同步设置")
        sync_layout = QFormLayout(sync_group)

        self.git_auto_sync_checkbox = QCheckBox("启动时自动拉取")
        sync_layout.addRow(self.git_auto_sync_checkbox)

        self.git_commit_msg_input = QLineEdit()
        self.git_commit_msg_input.setPlaceholderText("更新笔记")
        sync_layout.addRow("提交信息:", self.git_commit_msg_input)

        layout.addWidget(sync_group)

        # 提示
        hint_label = QLabel("提示: 笔记内容将同步到指定的 Git 仓库，而非项目本身。")
        hint_label.setStyleSheet("color: #8B7B6B; font-style: italic;")
        layout.addWidget(hint_label)

        layout.addStretch()

        return widget

    def _load_settings(self) -> None:
        """加载设置"""
        config = get_config()

        # AI 设置
        self.provider_combo.setCurrentText(config.ai_provider)

        ai_config = config.get_ai_config()
        self.base_url_input.setText(ai_config.get("base_url", ""))
        self.api_key_input.setText(ai_config.get("api_key", ""))
        self.model_combo.setCurrentText(ai_config.get("model", ""))

        # 编辑器设置
        self.font_size_spin.setValue(config.editor_font_size)
        self.autosave_interval_spin.setValue(config.auto_save_interval)
        self.auto_generate_skill_checkbox.setChecked(config.auto_generate_skill)

        # Git 设置
        self.git_enabled_checkbox.setChecked(config.git_enabled)
        self.git_url_input.setText(config.git_remote_url)
        self.git_branch_input.setText(config.git_branch)
        self.git_auto_sync_checkbox.setChecked(config.git_auto_sync)
        self.git_commit_msg_input.setText(config.git_commit_message)

    def _on_provider_changed(self, provider: str) -> None:
        """提供商改变"""
        # 更新模型列表
        self.model_combo.clear()
        self.model_combo.addItems(self._model_presets.get(provider, []))

        # 更新 base_url
        default_urls = {
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com",
            "ollama": "http://localhost:11434",
        }
        self.base_url_input.setText(default_urls.get(provider, ""))

        # Ollama 不需要 API Key
        self.api_key_input.setEnabled(provider != "ollama")

    @Slot()
    def _on_save(self) -> None:
        """保存设置"""
        config = get_config()

        # AI 设置
        provider = self.provider_combo.currentText()
        config.ai_provider = provider

        ai_config = {
            "base_url": self.base_url_input.text(),
            "api_key": self.api_key_input.text(),
            "model": self.model_combo.currentText(),
        }
        config.set_ai_config(provider, ai_config)

        # 编辑器设置
        config.editor_font_size = self.font_size_spin.value()
        config.auto_save_interval = self.autosave_interval_spin.value()
        config.auto_generate_skill = self.auto_generate_skill_checkbox.isChecked()

        # Git 设置
        config.git_enabled = self.git_enabled_checkbox.isChecked()
        config.git_remote_url = self.git_url_input.text()
        config.git_branch = self.git_branch_input.text() or "main"
        config.git_auto_sync = self.git_auto_sync_checkbox.isChecked()
        config.git_commit_message = self.git_commit_msg_input.text() or "更新笔记"

        # 保存到文件
        config.save()

        self.accept()