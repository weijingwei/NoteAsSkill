"""文件夹 SKILL 生成器模块

负责生成文件夹级别的 SKILL.md，聚合子项摘要信息。
支持三种生成模式：simple（纯规则）、ai（AI生成）、hybrid（混合）。
"""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .config import get_config
from .note_manager import Folder, Note, get_note_manager


@dataclass
class NoteSummary:
    """笔记摘要"""
    id: str
    title: str
    description: str = ""


@dataclass
class FolderSummary:
    """文件夹摘要"""
    name: str
    description: str = ""
    skill_hash: str = ""


class FolderSkillGenerator:
    """文件夹 SKILL 生成器"""

    def __init__(self):
        """初始化生成器"""
        self._ai_client: Any = None
        self.note_manager = get_note_manager()
        self.folder_skills_path = self.note_manager.notebook_path / ".folder_skills"
        self.folder_skills_path.mkdir(parents=True, exist_ok=True)

    def set_ai_client(self, client: Any) -> None:
        """设置 AI 客户端"""
        self._ai_client = client

    def generate_folder_skill(self, folder: Folder) -> str:
        """生成文件夹 SKILL.md 内容

        Args:
            folder: 文件夹对象

        Returns:
            SKILL.md 内容
        """
        # 收集子项
        child_notes = self._get_child_notes(folder.name)
        child_folders = self._get_child_folders(folder.name)

        # 提取摘要
        note_summaries = [self._extract_note_summary(note) for note in child_notes]
        folder_summaries = [self._extract_folder_summary(f) for f in child_folders]

        # 根据模式生成
        config = get_config()
        mode = config.folder_skill_generation_mode

        if mode == "simple":
            return self._generate_simple(folder, note_summaries, folder_summaries)
        elif mode == "ai":
            return self._generate_with_ai(folder, note_summaries, folder_summaries)
        else:  # hybrid
            return self._generate_hybrid(folder, note_summaries, folder_summaries)

    def _get_child_notes(self, folder_name: str) -> list[Note]:
        """获取直接子笔记"""
        notes = self.note_manager.list_notes()
        return [n for n in notes if n.folder == folder_name]

    def _get_child_folders(self, folder_name: str) -> list[Folder]:
        """获取直接子文件夹"""
        folders = self.note_manager.list_folders()
        return [f for f in folders if f.parent == folder_name]

    def _extract_note_summary(self, note: Note) -> NoteSummary:
        """从笔记 SKILL.md 提取摘要"""
        skill_path = self.note_manager._get_skill_file(note.id)

        description = ""
        if skill_path.exists():
            try:
                with open(skill_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # 解析 YAML front matter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        front_matter = yaml.safe_load(parts[1])
                        if front_matter:
                            description = front_matter.get("description", "")[:200]
            except Exception:
                pass

        return NoteSummary(
            id=note.id,
            title=note.title,
            description=description,
        )

    def _extract_folder_summary(self, folder: Folder) -> FolderSummary:
        """从子文件夹 SKILL.md 提取摘要"""
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
                                description = front_matter.get("description", "")[:200]
                except Exception:
                    pass

        return FolderSummary(
            name=folder.name,
            description=description,
            skill_hash=folder.skill_hash,
        )

    def _generate_simple(
        self,
        folder: Folder,
        note_summaries: list[NoteSummary],
        folder_summaries: list[FolderSummary],
    ) -> str:
        """简单模式：纯规则聚合"""
        front_matter = {
            "name": f"folder-{folder.name}",
            "type": "folder",
            "children": {
                "notes": [
                    {"id": s.id, "title": s.title, "summary": s.description}
                    for s in note_summaries
                ],
                "folders": [
                    {"name": s.name, "summary": s.description}
                    for s in folder_summaries
                ],
            },
        }

        content = "---\n"
        content += yaml.dump(front_matter, allow_unicode=True, default_flow_style=False)
        content += "---\n\n"

        # 子笔记列表
        if note_summaries:
            content += "## 子笔记\n"
            for s in note_summaries:
                content += f"- [{s.title}](../skills/{s.id}/)"
                if s.description:
                    content += f" - {s.description}"
                content += "\n"
            content += "\n"

        # 子文件夹列表
        if folder_summaries:
            content += "## 子文件夹\n"
            for s in folder_summaries:
                content += f"- [{s.name}](./{s.name}/)"
                if s.description:
                    content += f" - {s.description}"
                content += "\n"

        return content

    def _generate_with_ai(
        self,
        folder: Folder,
        note_summaries: list[NoteSummary],
        folder_summaries: list[FolderSummary],
    ) -> str:
        """AI 模式：AI 生成所有内容"""
        # 先生成基础结构
        base_content = self._generate_simple(folder, note_summaries, folder_summaries)

        # 如果没有 AI 客户端，返回基础内容
        if not self._ai_client:
            return base_content

        # 构建 AI 提示
        prompt = self._build_ai_prompt(folder, note_summaries, folder_summaries)

        try:
            ai_description = self._ai_client.chat([
                {"role": "user", "content": prompt}
            ])
        except Exception:
            ai_description = ""

        # 将 AI 描述插入到 front matter
        if ai_description:
            front_matter = {
                "name": f"folder-{folder.name}",
                "type": "folder",
                "description": ai_description.strip(),
                "children": {
                    "notes": [
                        {"id": s.id, "title": s.title, "summary": s.description}
                        for s in note_summaries
                    ],
                    "folders": [
                        {"name": s.name, "summary": s.description}
                        for s in folder_summaries
                    ],
                },
            }

            content = "---\n"
            content += yaml.dump(front_matter, allow_unicode=True, default_flow_style=False)
            content += "---\n\n"
            content += f"## 概述\n\n{ai_description.strip()}\n\n"

            if note_summaries:
                content += "## 子笔记\n"
                for s in note_summaries:
                    content += f"- [{s.title}](../skills/{s.id}/)"
                    if s.description:
                        content += f" - {s.description}"
                    content += "\n"
                content += "\n"

            if folder_summaries:
                content += "## 子文件夹\n"
                for s in folder_summaries:
                    content += f"- [{s.name}](./{s.name}/)"
                    if s.description:
                        content += f" - {s.description}"
                    content += "\n"

            return content

        return base_content

    def _generate_hybrid(
        self,
        folder: Folder,
        note_summaries: list[NoteSummary],
        folder_summaries: list[FolderSummary],
    ) -> str:
        """混合模式：基础结构用规则，概要描述用 AI"""
        # 先生成基础结构
        base_content = self._generate_simple(folder, note_summaries, folder_summaries)

        # 如果没有子项，直接返回
        if not note_summaries and not folder_summaries:
            return base_content

        # 如果没有 AI 客户端，返回基础内容
        if not self._ai_client:
            return base_content

        # 构建 AI 提示
        prompt = self._build_ai_prompt(folder, note_summaries, folder_summaries)

        try:
            ai_description = self._ai_client.chat([
                {"role": "user", "content": prompt}
            ])
        except Exception:
            ai_description = ""

        # 将 AI 描述插入
        if ai_description:
            front_matter = {
                "name": f"folder-{folder.name}",
                "type": "folder",
                "description": ai_description.strip(),
                "children": {
                    "notes": [
                        {"id": s.id, "title": s.title, "summary": s.description}
                        for s in note_summaries
                    ],
                    "folders": [
                        {"name": s.name, "summary": s.description}
                        for s in folder_summaries
                    ],
                },
            }

            content = "---\n"
            content += yaml.dump(front_matter, allow_unicode=True, default_flow_style=False)
            content += "---\n\n"
            content += f"## 概述\n\n{ai_description.strip()}\n\n"

            if note_summaries:
                content += "## 子笔记\n"
                for s in note_summaries:
                    content += f"- [{s.title}](../skills/{s.id}/)"
                    if s.description:
                        content += f" - {s.description}"
                    content += "\n"
                content += "\n"

            if folder_summaries:
                content += "## 子文件夹\n"
                for s in folder_summaries:
                    content += f"- [{s.name}](./{s.name}/)"
                    if s.description:
                        content += f" - {s.description}"
                    content += "\n"

            return content

        return base_content

    def _build_ai_prompt(
        self,
        folder: Folder,
        note_summaries: list[NoteSummary],
        folder_summaries: list[FolderSummary],
    ) -> str:
        """构建 AI 提示"""
        prompt = f"这是一个名为「{folder.name}」的文件夹，包含以下内容：\n\n"

        if note_summaries:
            prompt += "笔记：\n"
            for s in note_summaries:
                prompt += f"- {s.title}"
                if s.description:
                    prompt += f"：{s.description}"
                prompt += "\n"
            prompt += "\n"

        if folder_summaries:
            prompt += "子文件夹：\n"
            for s in folder_summaries:
                prompt += f"- {s.name}"
                if s.description:
                    prompt += f"：{s.description}"
                prompt += "\n"
            prompt += "\n"

        prompt += "请生成一段 100-200 字的概要描述，说明这个文件夹的主题和内容组织。只返回描述文字，不要其他内容。"

        return prompt

    def save_folder_skill(self, folder: Folder, content: str) -> str:
        """保存文件夹 SKILL.md

        Args:
            folder: 文件夹对象
            content: SKILL.md 内容

        Returns:
            skill_hash
        """
        # 计算 hash
        skill_hash = hashlib.md5(folder.name.encode()).hexdigest()[:16]
        skill_path = self.folder_skills_path / f"{skill_hash}.md"

        with open(skill_path, "w", encoding="utf-8") as f:
            f.write(content)

        return skill_hash

    def get_folder_skill_path(self, folder: Folder) -> Path:
        """获取文件夹 SKILL.md 路径"""
        skill_hash = folder.skill_hash or hashlib.md5(folder.name.encode()).hexdigest()[:16]
        return self.folder_skills_path / f"{skill_hash}.md"


# 全局实例
_folder_skill_generator: FolderSkillGenerator | None = None


def get_folder_skill_generator() -> FolderSkillGenerator:
    """获取全局文件夹 SKILL 生成器实例"""
    global _folder_skill_generator
    if _folder_skill_generator is None:
        _folder_skill_generator = FolderSkillGenerator()
    return _folder_skill_generator