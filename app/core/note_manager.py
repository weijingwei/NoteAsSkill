"""笔记管理模块

负责笔记的 CRUD 操作、文件夹管理和标签管理。
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import json
import re
import shutil


@dataclass
class Note:
    """笔记数据类"""

    id: str
    title: str
    path: Path
    folder: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "title": self.title,
            "path": str(self.path),
            "folder": self.folder,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Note":
        """从字典创建"""
        return cls(
            id=data["id"],
            title=data["title"],
            path=Path(data["path"]),
            folder=data.get("folder", ""),
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )


@dataclass
class Folder:
    """文件夹数据类"""

    name: str
    path: Path
    parent: str = ""
    # 渐进式披露相关属性
    skill_hash: str = ""           # SKILL.md 文件的 hash 标识
    children_hash: str = ""        # 子项内容 hash（用于检测变化）
    pending_update: bool = False   # 是否有待更新

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "path": str(self.path),
            "parent": self.parent,
            "skill_hash": self.skill_hash,
            "children_hash": self.children_hash,
            "pending_update": self.pending_update,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Folder":
        """从字典创建"""
        return cls(
            name=data["name"],
            path=Path(data["path"]),
            parent=data.get("parent", ""),
            skill_hash=data.get("skill_hash", ""),
            children_hash=data.get("children_hash", ""),
            pending_update=data.get("pending_update", False),
        )


class NoteManager:
    """笔记管理器"""

    def __init__(self, notebook_path: Path | None = None):
        """初始化笔记管理器

        Args:
            notebook_path: 笔记本根目录，默认为 notebook/
        """
        if notebook_path is None:
            self.notebook_path = Path(__file__).parent.parent.parent / "notebook"
        else:
            self.notebook_path = Path(notebook_path)

        self.skills_path = self.notebook_path / "skills"
        self.templates_path = self.notebook_path / "templates"
        self.index_path = self.notebook_path / ".index.json"

        self._notes: dict[str, Note] = {}
        self._folders: dict[str, Folder] = {}
        self._tags: set[str] = set()

        self._ensure_directories()
        self._load_index()

    def _ensure_directories(self) -> None:
        """确保必要目录存在"""
        self.skills_path.mkdir(parents=True, exist_ok=True)
        self.templates_path.mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> None:
        """加载索引文件"""
        if self.index_path.exists():
            with open(self.index_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for note_data in data.get("notes", []):
                note = Note.from_dict(note_data)
                self._notes[note.id] = note

            for folder_data in data.get("folders", []):
                folder = Folder.from_dict(folder_data)
                self._folders[folder.name] = folder

            self._tags = set(data.get("tags", []))

    def _save_index(self) -> None:
        """保存索引文件"""
        data = {
            "notes": [note.to_dict() for note in self._notes.values()],
            "folders": [folder.to_dict() for folder in self._folders.values()],
            "tags": list(self._tags),
        }

        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _slugify(text: str) -> str:
        """将文本转换为 URL 友好的 slug"""
        text = text.lower()
        text = re.sub(r"[^\w\u4e00-\u9fff-]", "-", text)
        text = re.sub(r"-+", "-", text)
        text = text.strip("-")
        return text or "untitled"

    def _get_note_path(self, note_id: str) -> Path:
        """获取笔记目录路径"""
        return self.skills_path / note_id

    def _get_note_file(self, note_id: str) -> Path:
        """获取笔记文件路径"""
        return self._get_note_path(note_id) / "note.md"

    def _get_skill_file(self, note_id: str) -> Path:
        """获取 SKILL.md 文件路径"""
        return self._get_note_path(note_id) / "SKILL.md"

    def _get_attachments_path(self, note_id: str) -> Path:
        """获取附件目录路径"""
        return self._get_note_path(note_id) / "attachments"

    # ==================== 笔记操作 ====================

    def create_note(
        self,
        title: str,
        content: str = "",
        folder: str = "",
        tags: list[str] | None = None,
    ) -> Note:
        """创建新笔记"""
        base_id = self._slugify(title)
        note_id = base_id
        counter = 1
        while note_id in self._notes:
            note_id = f"{base_id}-{counter}"
            counter += 1

        note_path = self._get_note_path(note_id)
        note_path.mkdir(parents=True, exist_ok=True)

        attachments_path = self._get_attachments_path(note_id)
        attachments_path.mkdir(exist_ok=True)

        if not content:
            template_path = self.templates_path / "default.md"
            if template_path.exists():
                with open(template_path, "r", encoding="utf-8") as f:
                    content = f.read()

        note_file = self._get_note_file(note_id)
        with open(note_file, "w", encoding="utf-8") as f:
            f.write(content)

        skill_file = self._get_skill_file(note_id)
        skill_file.touch()

        now = datetime.now()
        note = Note(
            id=note_id,
            title=title,
            path=note_path,
            folder=folder,
            tags=tags or [],
            created_at=now,
            updated_at=now,
        )

        self._notes[note_id] = note
        for tag in note.tags:
            self._tags.add(tag)
        self._save_index()

        return note

    def get_note(self, note_id: str) -> Note | None:
        """获取笔记"""
        return self._notes.get(note_id)

    def get_note_content(self, note_id: str) -> str:
        """获取笔记内容"""
        note_file = self._get_note_file(note_id)
        if note_file.exists():
            with open(note_file, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def update_note(
        self,
        note_id: str,
        title: str | None = None,
        content: str | None = None,
        folder: str | None = None,
        tags: list[str] | None = None,
    ) -> Note | None:
        """更新笔记"""
        note = self._notes.get(note_id)
        if note is None:
            return None

        if content is not None:
            note_file = self._get_note_file(note_id)
            with open(note_file, "w", encoding="utf-8") as f:
                f.write(content)

        if title is not None:
            note.title = title
        if folder is not None:
            note.folder = folder
        if tags is not None:
            for old_tag in note.tags:
                if old_tag not in tags:
                    if not any(
                        old_tag in n.tags
                        for n in self._notes.values()
                        if n.id != note_id
                    ):
                        self._tags.discard(old_tag)
            for new_tag in tags:
                self._tags.add(new_tag)
            note.tags = tags

        note.updated_at = datetime.now()
        self._save_index()

        return note

    def delete_note(self, note_id: str) -> bool:
        """删除笔记"""
        note = self._notes.get(note_id)
        if note is None:
            return False

        note_path = self._get_note_path(note_id)
        if note_path.exists():
            shutil.rmtree(note_path)

        for tag in note.tags:
            if not any(
                tag in n.tags for n in self._notes.values() if n.id != note_id
            ):
                self._tags.discard(tag)

        del self._notes[note_id]
        self._save_index()

        return True

    def list_notes(
        self,
        folder: str | None = None,
        tags: list[str] | None = None,
    ) -> list[Note]:
        """列出笔记"""
        notes = list(self._notes.values())

        if folder is not None:
            notes = [n for n in notes if n.folder == folder]

        if tags:
            notes = [n for n in notes if any(tag in n.tags for tag in tags)]

        notes.sort(key=lambda n: n.updated_at, reverse=True)
        return notes

    def search_notes(self, query: str) -> list[Note]:
        """搜索笔记"""
        query = query.lower()
        results = []

        for note in self._notes.values():
            if query in note.title.lower():
                results.append(note)
                continue

            content = self.get_note_content(note.id)
            if query in content.lower():
                results.append(note)
                continue

            if any(query in tag.lower() for tag in note.tags):
                results.append(note)

        return results

    # ==================== 文件夹操作 ====================

    def create_folder(self, name: str, parent: str = "") -> Folder:
        """创建文件夹"""
        folder = Folder(
            name=name,
            path=self.skills_path / name,
            parent=parent,
        )

        self._folders[name] = folder
        self._save_index()

        return folder

    def get_folder(self, name: str) -> Folder | None:
        """获取文件夹"""
        return self._folders.get(name)

    def delete_folder(self, name: str, delete_notes: bool = False) -> bool:
        """删除文件夹"""
        folder = self._folders.get(name)
        if folder is None:
            return False

        notes_in_folder = [n for n in self._notes.values() if n.folder == name]

        if delete_notes:
            for note in notes_in_folder:
                self.delete_note(note.id)
        else:
            for note in notes_in_folder:
                note.folder = ""
            self._save_index()

        del self._folders[name]
        self._save_index()

        return True

    def list_folders(self) -> list[Folder]:
        """列出所有文件夹"""
        return list(self._folders.values())

    def rename_folder(self, old_name: str, new_name: str) -> bool:
        """重命名文件夹"""
        folder = self._folders.get(old_name)
        if folder is None or new_name in self._folders:
            return False

        folder.name = new_name

        for note in self._notes.values():
            if note.folder == old_name:
                note.folder = new_name

        del self._folders[old_name]
        self._folders[new_name] = folder
        self._save_index()

        return True

    # ==================== 标签操作 ====================

    def list_tags(self) -> list[str]:
        """列出所有标签"""
        return list(self._tags)

    def add_tag_to_note(self, note_id: str, tag: str) -> bool:
        """为笔记添加标签"""
        note = self._notes.get(note_id)
        if note is None:
            return False

        if tag not in note.tags:
            note.tags.append(tag)
            self._tags.add(tag)
            note.updated_at = datetime.now()
            self._save_index()

        return True

    def remove_tag_from_note(self, note_id: str, tag: str) -> bool:
        """从笔记移除标签"""
        note = self._notes.get(note_id)
        if note is None or tag not in note.tags:
            return False

        note.tags.remove(tag)
        note.updated_at = datetime.now()

        if not any(tag in n.tags for n in self._notes.values()):
            self._tags.discard(tag)

        self._save_index()
        return True

    def get_notes_by_tag(self, tag: str) -> list[Note]:
        """获取带有指定标签的所有笔记"""
        return [n for n in self._notes.values() if tag in n.tags]


# 全局实例
_note_manager: NoteManager | None = None


def get_note_manager() -> NoteManager:
    """获取全局笔记管理器实例"""
    global _note_manager
    if _note_manager is None:
        _note_manager = NoteManager()
    return _note_manager