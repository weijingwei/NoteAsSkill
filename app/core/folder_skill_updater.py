"""文件夹 SKILL 更新器模块

负责管理文件夹 SKILL.md 的更新，支持延迟更新和级联更新。
"""

from typing import Any
from PySide6.QtCore import QObject, QTimer, Signal

from .config import get_config
from .change_detector import get_change_detector
from .folder_skill_generator import get_folder_skill_generator
from .note_manager import Folder, get_note_manager
from ..ai.client import create_client


class FolderSkillUpdater(QObject):
    """文件夹 SKILL 更新器

    支持两种更新模式：
    - MODE_IMMEDIATE: 立即更新（删除、移动等确定性操作）
    - MODE_DELAYED: 延迟更新（编辑等可能连续的操作）
    """

    MODE_IMMEDIATE = "immediate"
    MODE_DELAYED = "delayed"

    # 信号
    update_started = Signal(str)      # 开始更新 (folder_name)
    update_finished = Signal(str)     # 更新完成 (folder_name)
    update_error = Signal(str, str)   # 更新错误 (folder_name, error)

    def __init__(self):
        """初始化更新器"""
        super().__init__()

        self.update_queue: list[str] = []  # 待更新队列
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self._process_batch)

        self._ai_client: Any = None
        self._is_updating = False

    def set_ai_client(self, client: Any) -> None:
        """设置 AI 客户端"""
        self._ai_client = client

    def _load_ai_client(self) -> None:
        """加载 AI 客户端"""
        if self._ai_client is not None:
            return

        config = get_config()
        try:
            ai_config = config.get_ai_config()
            self._ai_client = create_client(config.ai_provider, ai_config)
        except Exception:
            self._ai_client = None

    def mark_folder_dirty(self, folder_name: str, mode: str = None) -> None:
        """标记文件夹为脏（需要更新）

        Args:
            folder_name: 文件夹名称
            mode: 更新模式，默认使用配置的延迟时间
        """
        config = get_config()

        if not config.folder_skill_enabled or not config.folder_skill_auto_update:
            return

        if mode is None:
            mode = self.MODE_DELAYED

        note_manager = get_note_manager()
        folder = note_manager.get_folder(folder_name)

        if folder is None:
            return

        folder.pending_update = True

        if mode == self.MODE_IMMEDIATE:
            # 立即更新
            self._update_folder_skill(folder_name)
        else:
            # 延迟更新（防抖）
            self._schedule_update(folder_name)

    def _schedule_update(self, folder_name: str) -> None:
        """调度延迟更新

        Args:
            folder_name: 文件夹名称
        """
        # 添加到队列（去重）
        if folder_name not in self.update_queue:
            self.update_queue.append(folder_name)

        # 重置定时器（防抖）
        config = get_config()
        delay = config.folder_skill_update_delay * 1000  # 转换为毫秒

        self.update_timer.start(delay)

    def _process_batch(self) -> None:
        """批量处理更新队列"""
        if self._is_updating:
            # 如果正在更新，稍后重试
            self.update_timer.start(5000)
            return

        if not self.update_queue:
            return

        # 取出第一个
        folder_name = self.update_queue.pop(0)
        self._update_folder_skill(folder_name)

        # 如果还有待处理的，继续调度
        if self.update_queue:
            self.update_timer.start(2000)  # 2秒后继续

    def _update_folder_skill(self, folder_name: str) -> None:
        """更新单个文件夹的 SKILL.md

        由下往上级联更新：先更新当前文件夹，再更新父文件夹。

        Args:
            folder_name: 文件夹名称
        """
        if self._is_updating:
            return

        self._is_updating = True
        self.update_started.emit(folder_name)

        try:
            note_manager = get_note_manager()
            folder = note_manager.get_folder(folder_name)

            if folder is None:
                return

            # 检查是否真的有变化
            change_detector = get_change_detector()
            if not change_detector.has_changes(folder):
                folder.pending_update = False
                return

            # 加载 AI 客户端
            self._load_ai_client()

            # 生成 SKILL.md
            generator = get_folder_skill_generator()
            if self._ai_client:
                generator.set_ai_client(self._ai_client)

            content = generator.generate_folder_skill(folder)
            skill_hash = generator.save_folder_skill(folder, content)

            # 更新文件夹元数据
            folder.skill_hash = skill_hash
            folder.children_hash = change_detector.compute_children_hash(folder)
            folder.pending_update = False

            note_manager._save_index()

            self.update_finished.emit(folder_name)

            # 递归更新父文件夹（由下往上）
            if folder.parent:
                # 父文件夹使用延迟模式，避免频繁更新
                self._schedule_update(folder.parent)

        except Exception as e:
            self.update_error.emit(folder_name, str(e))

        finally:
            self._is_updating = False

    def refresh_folder_skill_immediate(self, folder_name: str) -> None:
        """立即刷新文件夹 SKILL（手动触发）

        Args:
            folder_name: 文件夹名称
        """
        self._update_folder_skill(folder_name)

    def refresh_all_folder_skills(self) -> None:
        """刷新所有文件夹 SKILL"""
        note_manager = get_note_manager()
        folders = note_manager.list_folders()

        for folder in folders:
            self._schedule_update(folder.name)

    def get_pending_count(self) -> int:
        """获取待更新数量"""
        return len(self.update_queue)


# 全局实例
_folder_skill_updater: FolderSkillUpdater | None = None


def get_folder_skill_updater() -> FolderSkillUpdater:
    """获取全局文件夹 SKILL 更新器实例"""
    global _folder_skill_updater
    if _folder_skill_updater is None:
        _folder_skill_updater = FolderSkillUpdater()
    return _folder_skill_updater