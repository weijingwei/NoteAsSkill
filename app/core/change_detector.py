"""变化检测器模块

负责检测文件夹内容变化，判断是否需要更新 SKILL.md。
"""

import hashlib
from pathlib import Path

from .note_manager import Folder, get_note_manager


class ChangeDetector:
    """变化检测器"""

    def __init__(self):
        """初始化检测器"""
        self.note_manager = get_note_manager()
        self.folder_skills_path = self.note_manager.notebook_path / ".folder_skills"

    def compute_children_hash(self, folder: Folder) -> str:
        """计算子项内容 hash

        用于检测文件夹内容是否变化。

        Args:
            folder: 文件夹对象

        Returns:
            子项内容的 hash 值
        """
        hash_data = []

        # 收集子笔记信息
        child_notes = self._get_child_notes(folder.name)
        for note in child_notes:
            skill_path = self.note_manager._get_skill_file(note.id)
            if skill_path.exists():
                # 使用文件修改时间和内容
                mtime = skill_path.stat().st_mtime
                hash_data.append(f"note:{note.id}:{mtime}")
            else:
                hash_data.append(f"note:{note.id}:empty")

        # 收集子文件夹信息
        child_folders = self._get_child_folders(folder.name)
        for f in child_folders:
            hash_data.append(f"folder:{f.name}:{f.children_hash}")

        # 排序保证一致性
        hash_data.sort()

        # 计算 hash
        combined = "|".join(hash_data)
        return hashlib.md5(combined.encode()).hexdigest()[:16]

    def has_changes(self, folder: Folder) -> bool:
        """检测文件夹是否有变化

        Args:
            folder: 文件夹对象

        Returns:
            是否有变化
        """
        current_hash = self.compute_children_hash(folder)
        return current_hash != folder.children_hash

    def _get_child_notes(self, folder_name: str) -> list:
        """获取直接子笔记"""
        notes = self.note_manager.list_notes()
        return [n for n in notes if n.folder == folder_name]

    def _get_child_folders(self, folder_name: str) -> list[Folder]:
        """获取直接子文件夹"""
        folders = self.note_manager.list_folders()
        return [f for f in folders if f.parent == folder_name]


# 全局实例
_change_detector: ChangeDetector | None = None


def get_change_detector() -> ChangeDetector:
    """获取全局变化检测器实例"""
    global _change_detector
    if _change_detector is None:
        _change_detector = ChangeDetector()
    return _change_detector