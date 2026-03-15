"""文件夹 SKILL 生成器模块

负责生成文件夹级别的 SKILL.md，聚合子项摘要信息。
支持三种生成模式：simple（纯规则）、ai（AI生成）、hybrid（混合）。

设计模式：策略模式 (Strategy Pattern)
- 将生成算法封装在策略类中
- 支持运行时切换生成策略
- 新增策略无需修改现有代码

使用方式：
    # 获取生成器实例
    generator = get_folder_skill_generator()
    
    # 设置 AI 客户端（可选）
    generator.set_ai_client(ai_client)
    
    # 生成 SKILL.md
    content = generator.generate_folder_skill(folder)
    
    # 保存
    skill_hash = generator.save_folder_skill(folder, content)
"""
import hashlib
from pathlib import Path
from typing import Any

import yaml

from .config import get_config
from .note_manager import Folder, Note, get_note_manager
from .folder_skill_strategies import (
    NoteSummary,
    FolderSummary,
    FolderSkillStrategyFactory,
)
from .singleton import SingletonMeta


class FolderSkillGenerator(metaclass=SingletonMeta):
    """文件夹 SKILL 生成器
    
    使用策略模式生成文件夹级别的 SKILL.md。
    根据配置选择不同的生成策略。
    
    设计模式：策略模式
    - FolderSkillStrategyFactory 提供策略实例
    - 支持运行时切换策略
    - 新增策略只需注册到工厂
    """
    
    def __init__(self):
        """初始化生成器"""
        self._ai_client: Any = None
        self.note_manager = get_note_manager()
        self.folder_skills_path = self.note_manager.notebook_path / ".folder_skills"
        self.folder_skills_path.mkdir(parents=True, exist_ok=True)

    def set_ai_client(self, client: Any) -> None:
        """设置 AI 客户端
        
        Args:
            client: AI 客户端实例
        """
        self._ai_client = client

    def generate_folder_skill(self, folder: Folder) -> str:
        """生成文件夹 SKILL.md 内容
        
        根据配置选择生成策略，聚合子项信息生成 SKILL.md。
        
        Args:
            folder: 文件夹对象
            
        Returns:
            SKILL.md 内容
        """
        note_summaries = self._get_child_notes(folder.name)
        folder_summaries = self._get_child_folders(folder.name)
        
        note_summaries_data = [
            self._extract_note_summary(note) for note in note_summaries
        ]
        folder_summaries_data = [
            self._extract_folder_summary(f) for f in folder_summaries
        ]
        
        config = get_config()
        mode = config.folder_skill_generation_mode
        
        strategy = FolderSkillStrategyFactory.get(mode)
        
        return strategy.generate(
            folder.name,
            note_summaries_data,
            folder_summaries_data,
            self._ai_client
        )

    def _get_child_notes(self, folder_name: str) -> list[Note]:
        """获取直接子笔记
        
        Args:
            folder_name: 文件夹名称
            
        Returns:
            子笔记列表
        """
        notes = self.note_manager.list_notes()
        return [n for n in notes if n.folder == folder_name]

    def _get_child_folders(self, folder_name: str) -> list[Folder]:
        """获取直接子文件夹
        
        Args:
            folder_name: 文件夹名称
            
        Returns:
            子文件夹列表
        """
        folders = self.note_manager.list_folders()
        return [f for f in folders if f.parent == folder_name]

    def _extract_note_summary(self, note: Note) -> NoteSummary:
        """从笔记 SKILL.md 提取摘要
        
        Args:
            note: 笔记对象
            
        Returns:
            笔记摘要
        """
        skill_path = self.note_manager._get_skill_file(note.id)

        description = ""
        if skill_path.exists():
            try:
                with open(skill_path, "r", encoding="utf-8") as f:
                    content = f.read()

                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        front_matter = yaml.safe_load(parts[1])
                        if front_matter:
                            desc = front_matter.get("description", "")
                            if desc:
                                description = desc[:200]
            except Exception:
                pass

        return NoteSummary(
            id=note.id,
            title=note.title,
            description=description,
        )

    def _extract_folder_summary(self, folder: Folder) -> FolderSummary:
        """从子文件夹 SKILL.md 提取摘要
        
        Args:
            folder: 文件夹对象
            
        Returns:
            文件夹摘要
        """
        description = ""

        if folder.skill_hash:
            skill_path = self.folder_skills_path / f"{folder.skill_hash}.md"
            if skill_path.exists():
                try:
                    with open(skill_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    if content.startswith("---"):
                        parts = content.split("---", 2)
                        if len(parts) >= 3:
                            front_matter = yaml.safe_load(parts[1])
                            if front_matter:
                                desc = front_matter.get("description", "")
                                if desc:
                                    description = desc[:200]
                except Exception:
                    pass

        return FolderSummary(
            name=folder.name,
            description=description,
            skill_hash=folder.skill_hash,
        )

    def save_folder_skill(self, folder: Folder, content: str) -> str:
        """保存文件夹 SKILL.md
        
        Args:
            folder: 文件夹对象
            content: SKILL.md 内容
            
        Returns:
            skill_hash
        """
        skill_hash = hashlib.md5(folder.name.encode()).hexdigest()[:16]
        skill_path = self.folder_skills_path / f"{skill_hash}.md"

        with open(skill_path, "w", encoding="utf-8") as f:
            f.write(content)

        return skill_hash

    def get_folder_skill_path(self, folder: Folder) -> Path:
        """获取文件夹 SKILL.md 路径
        
        Args:
            folder: 文件夹对象
            
        Returns:
            SKILL.md 文件路径
        """
        skill_hash = folder.skill_hash or hashlib.md5(folder.name.encode()).hexdigest()[:16]
        return self.folder_skills_path / f"{skill_hash}.md"


def get_folder_skill_generator() -> FolderSkillGenerator:
    """获取全局文件夹 SKILL 生成器实例
    
    使用单例模式，返回唯一的生成器实例。
    
    Returns:
        FolderSkillGenerator 实例
    """
    return FolderSkillGenerator()
