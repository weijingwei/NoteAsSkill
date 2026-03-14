"""核心模块"""

from .config import Config, get_config
from .note_manager import NoteManager, Note, Folder, get_note_manager
from .skill_generator import SkillGenerator, get_skill_generator
from .attachment_handler import AttachmentHandler

__all__ = [
    "Config",
    "get_config",
    "NoteManager",
    "Note",
    "Folder",
    "get_note_manager",
    "SkillGenerator",
    "get_skill_generator",
    "AttachmentHandler",
]