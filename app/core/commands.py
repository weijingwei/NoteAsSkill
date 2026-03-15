"""命令模式模块

将操作封装为命令对象，支持队列处理、撤销重做等功能。

设计模式：命令模式 (Command Pattern)
- 将操作封装为对象
- 支持撤销、重做
- 支持队列处理

优势：
- 解耦：调用者和执行者分离
- 可扩展：新增命令只需实现 Command 接口
- 可组合：支持宏命令和批处理

使用方式：
    # 创建命令
    cmd = UpdateFolderSkillCommand("my-folder")
    
    # 执行命令
    result = cmd.execute()
    
    # 使用命令队列
    queue = CommandQueue()
    queue.add(cmd)
    queue.execute_all()
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Optional


class CommandType(Enum):
    """命令类型枚举"""
    UPDATE_FOLDER_SKILL = auto()
    UPDATE_NOTE = auto()
    GENERATE_SKILL = auto()
    MOVE_NOTE = auto()
    DELETE_NOTE = auto()


@dataclass
class CommandResult:
    """命令执行结果
    
    封装命令执行后的状态和信息。
    """
    success: bool
    message: str = ""
    data: Any = None
    timestamp: datetime = field(default_factory=datetime.now)


class Command(ABC):
    """命令基类
    
    定义所有命令的公共接口。
    子类必须实现 execute() 和 undo() 方法。
    
    设计模式：命令模式中的抽象命令 (Command) 角色
    """
    
    def __init__(self, command_type: CommandType):
        self.type = command_type
        self._executed = False
        self._result: Optional[CommandResult] = None
        self.created_at = datetime.now()
    
    @abstractmethod
    def execute(self) -> CommandResult:
        """执行命令
        
        Returns:
            执行结果
        """
        pass
    
    @abstractmethod
    def undo(self) -> CommandResult:
        """撤销命令
        
        Returns:
            撤销结果
        """
        pass
    
    @property
    def executed(self) -> bool:
        """是否已执行"""
        return self._executed
    
    @property
    def result(self) -> Optional[CommandResult]:
        """执行结果"""
        return self._result


class UpdateFolderSkillCommand(Command):
    """更新文件夹 SKILL 命令
    
    用于触发文件夹 SKILL.md 的更新操作。
    """
    
    def __init__(self, folder_name: str, immediate: bool = False):
        super().__init__(CommandType.UPDATE_FOLDER_SKILL)
        self.folder_name = folder_name
        self.immediate = immediate
        self._previous_content: Optional[str] = None
        self._previous_hash: Optional[str] = None
    
    def execute(self) -> CommandResult:
        from .folder_skill_generator import get_folder_skill_generator
        from .note_manager import get_note_manager
        from .change_detector import get_change_detector
        
        try:
            note_manager = get_note_manager()
            folder = note_manager.get_folder(self.folder_name)
            
            if folder is None:
                return CommandResult(False, f"文件夹不存在: {self.folder_name}")
            
            generator = get_folder_skill_generator()
            content = generator.generate_folder_skill(folder)
            skill_hash = generator.save_folder_skill(folder, content)
            
            detector = get_change_detector()
            self._previous_hash = folder.skill_hash
            folder.skill_hash = skill_hash
            folder.children_hash = detector.compute_children_hash(folder)
            folder.pending_update = False
            note_manager._save_index()
            
            self._executed = True
            self._result = CommandResult(
                True, 
                f"文件夹 {self.folder_name} SKILL 已更新",
                {"skill_hash": skill_hash}
            )
            return self._result
            
        except Exception as e:
            self._result = CommandResult(False, f"更新失败: {str(e)}")
            return self._result
    
    def undo(self) -> CommandResult:
        if not self._executed or not self._previous_hash:
            return CommandResult(False, "无法撤销：命令未执行或无历史记录")
        
        try:
            from .note_manager import get_note_manager
            
            note_manager = get_note_manager()
            folder = note_manager.get_folder(self.folder_name)
            
            if folder is None:
                return CommandResult(False, f"文件夹不存在: {self.folder_name}")
            
            folder.skill_hash = self._previous_hash
            note_manager._save_index()
            
            return CommandResult(True, f"已撤销文件夹 {self.folder_name} 的更新")
            
        except Exception as e:
            return CommandResult(False, f"撤销失败: {str(e)}")


class GenerateSkillCommand(Command):
    """生成 SKILL 命令
    
    用于触发笔记 SKILL.md 的生成操作。
    """
    
    def __init__(self, note_id: str, note_content: str, skill_path: str):
        super().__init__(CommandType.GENERATE_SKILL)
        self.note_id = note_id
        self.note_content = note_content
        self.skill_path = skill_path
        self._previous_content: Optional[str] = None
    
    def execute(self) -> CommandResult:
        from pathlib import Path
        from .skill_generator import get_skill_generator
        from .config import get_config
        from ..ai.factory import AIClientFactory
        
        try:
            skill_path = Path(self.skill_path)
            
            if skill_path.exists():
                self._previous_content = skill_path.read_text(encoding="utf-8")
            
            generator = get_skill_generator()
            
            config = get_config()
            if config.ai_provider and AIClientFactory.is_provider_supported(config.ai_provider):
                try:
                    ai_config = config.get_ai_config()
                    ai_client = AIClientFactory.create(config.ai_provider, ai_config)
                    generator.set_ai_client(ai_client)
                except Exception:
                    pass
            
            success = generator.generate_and_save(
                self.note_id, self.note_content, skill_path
            )
            
            if success:
                self._executed = True
                self._result = CommandResult(True, f"SKILL.md 已生成")
            else:
                self._result = CommandResult(False, "SKILL.md 生成失败")
            
            return self._result
            
        except Exception as e:
            self._result = CommandResult(False, f"生成失败: {str(e)}")
            return self._result
    
    def undo(self) -> CommandResult:
        from pathlib import Path
        
        if not self._executed:
            return CommandResult(False, "无法撤销：命令未执行")
        
        try:
            skill_path = Path(self.skill_path)
            
            if self._previous_content is not None:
                skill_path.write_text(self._previous_content, encoding="utf-8")
                return CommandResult(True, "已撤销 SKILL.md 生成")
            else:
                if skill_path.exists():
                    skill_path.unlink()
                return CommandResult(True, "已删除生成的 SKILL.md")
                
        except Exception as e:
            return CommandResult(False, f"撤销失败: {str(e)}")


class CommandQueue:
    """命令队列
    
    管理命令的执行、排队和批量处理。
    支持优先级和依赖关系。
    
    设计模式：命令模式中的调用者 (Invoker) 角色
    """
    
    def __init__(self, max_size: int = 100):
        self._queue: list[Command] = []
        self._history: list[Command] = []
        self._max_size = max_size
    
    def add(self, command: Command) -> None:
        """添加命令到队列
        
        Args:
            command: 要添加的命令
        """
        if len(self._queue) >= self._max_size:
            self._queue.pop(0)
        self._queue.append(command)
    
    def execute_next(self) -> Optional[CommandResult]:
        """执行下一个命令
        
        Returns:
            执行结果，如果队列为空则返回 None
        """
        if not self._queue:
            return None
        
        command = self._queue.pop(0)
        result = command.execute()
        
        if command.executed:
            self._history.append(command)
            if len(self._history) > self._max_size:
                self._history.pop(0)
        
        return result
    
    def execute_all(self) -> list[CommandResult]:
        """执行所有命令
        
        Returns:
            所有执行结果的列表
        """
        results = []
        while self._queue:
            result = self.execute_next()
            if result:
                results.append(result)
        return results
    
    def clear(self) -> None:
        """清空队列"""
        self._queue.clear()
    
    def undo_last(self) -> Optional[CommandResult]:
        """撤销最后一个执行的命令
        
        Returns:
            撤销结果，如果没有可撤销的命令则返回 None
        """
        if not self._history:
            return None
        
        command = self._history.pop()
        return command.undo()
    
    @property
    def pending_count(self) -> int:
        """待执行命令数量"""
        return len(self._queue)
    
    @property
    def has_pending(self) -> bool:
        """是否有待执行的命令"""
        return len(self._queue) > 0
    
    @property
    def history_count(self) -> int:
        """历史命令数量"""
        return len(self._history)
